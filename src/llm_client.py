from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from config import (
    LLM_BASE_URL,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_PRESENCE_PENALTY,
    LLM_REPETITION_PENALTY,
    LLM_TEMPERATURE,
    REQUEST_TIMEOUT_S,
)

ALLOWED_ACTIONS = {"WRITE", "READ", "DELETE", "LIST", "EXECUTE"}


def _clean_special_tokens(text: str) -> str:
    cleaned = re.sub(r"<[|][^|>]+(?:[|]>)?", "", text)
    return cleaned.strip()


def _detect_loop_ngrams(text: str) -> bool:
    """Detecta bucles repetitivos patológicos (3 repeticiones consecutivas exactas)."""
    for w in (80, 160):
        if len(text) >= w * 3:
            c1 = text[-w:]
            c2 = text[-2 * w : -w]
            c3 = text[-3 * w : -2 * w]
            if c1 == c2 == c3:
                return True
    return False


def _extract_actions_from_obj(obj: Any) -> list[dict[str, Any]]:
    """Extrae acciones válidas soportando {"actions": [...]} o {"action": ...}."""
    actions: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        if "actions" in obj and isinstance(obj["actions"], list):
            for item in obj["actions"]:
                if isinstance(item, dict) and item.get("action") in ALLOWED_ACTIONS:
                    actions.append(item)
        elif obj.get("action") in ALLOWED_ACTIONS:
            actions.append(obj)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict) and item.get("action") in ALLOWED_ACTIONS:
                actions.append(item)
    return actions


def _repair_unclosed_json(text: str) -> list[dict[str, Any]]:
    """Cierra comillas, llaves y corchetes abiertos si la generación se cortó por tokens."""
    start = text.find("{")
    if start == -1:
        return []
    candidate = text[start:].strip()

    in_string = False
    escape = False
    for ch in candidate:
        if escape:
            escape = False
            continue
        if ch == chr(92):
            escape = True
            continue
        if ch == '"':
            in_string = not in_string

    repaired = candidate
    if in_string:
        repaired += '"'

    open_braces = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")
    repaired += ("]" * max(0, open_brackets)) + ("}" * max(0, open_braces))

    try:
        obj = json.loads(repaired, strict=False)
        return _extract_actions_from_obj(obj)
    except Exception:
        return []


def _find_json_actions(text: str) -> list[dict[str, Any]]:
    """Encuentra y analiza bloques JSON válidos en el texto."""
    results: list[dict[str, Any]] = []
    pos = 0
    length = len(text)

    while pos < length:
        start = text.find("{", pos)
        if start == -1:
            break

        depth = 0
        in_string = False
        escape = False
        end = -1

        for i in range(start, length):
            char = text[i]
            if escape:
                escape = False
                continue
            if char == chr(92):
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if not in_string:
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break

        if end != -1:
            snippet = text[start : end + 1]
            obj = None
            try:
                obj = json.loads(snippet, strict=False)
            except Exception:
                try:
                    fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', snippet)
                    obj = json.loads(fixed, strict=False)
                except Exception:
                    pass

            if obj:
                extracted = _extract_actions_from_obj(obj)
                if extracted:
                    results.extend(extracted)
            pos = end + 1
        else:
            pos = start + 1

    return results


def _rescue_conversational_action(text: str) -> list[dict[str, Any]]:
    """Rescata intenciones expresadas en lenguaje natural si falla el JSON."""
    rescued: list[dict[str, Any]] = []

    exec_calls = re.findall(r'EXECUTE\(\s*["\']([^"\']+)["\'](?:\s*,\s*(\[[^\]]*\]))?\s*\)', text)
    if exec_calls:
        target_path, raw_args = exec_calls[-1]
        args_list: list[str] = []
        if raw_args:
            try:
                args_list = json.loads(raw_args, strict=False)
            except Exception:
                args_list = re.findall(r'["\']([^"\']+)["\']', raw_args)
        rescued.append({
            "action": "EXECUTE",
            "path": target_path.strip(),
            "args": args_list,
        })
        return rescued

    path_matches = list(re.finditer(r"Path:\s*`?([a-zA-Z0-9_\-\./ ]+\.[a-zA-Z0-9]+)`?", text, re.IGNORECASE))
    if path_matches:
        last_path_m = path_matches[-1]
        path = last_path_m.group(1).strip()
        sub = text[last_path_m.end() :]
        c_match = re.search(r"Content:\s*`+([\s\S]*?)`+", sub, re.IGNORECASE)
        if c_match:
            content = c_match.group(1).strip().replace("\\n", "\n")
            rescued.append({"action": "WRITE", "path": path, "content": content})
            return rescued

    read_matches = re.findall(r"Action:\s*READ\s+[`\"']?([a-zA-Z0-9_\-\./]+)[`\"']?", text, re.IGNORECASE)
    if read_matches:
        rescued.append({"action": "READ", "path": read_matches[-1].strip()})
        return rescued

    return rescued


def parse_actions(content: str, reasoning: str = "") -> list[dict[str, Any]]:
    clean_content = _clean_special_tokens(content).strip()
    clean_reasoning = _clean_special_tokens(reasoning).strip()

    if clean_content:
        m = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_content)
        for block in reversed(m):
            actions = _find_json_actions(block)
            if actions:
                return actions

        actions = _find_json_actions(clean_content)
        if actions:
            return actions

        rescued = _rescue_conversational_action(clean_content)
        if rescued:
            return rescued

    if clean_reasoning:
        m = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_reasoning)
        for block in reversed(m):
            actions = _find_json_actions(block)
            filtered = [a for a in actions if a.get("path") not in ("<ruta>", "ruta")]
            if filtered:
                return filtered

        actions = _find_json_actions(clean_reasoning)
        filtered = [a for a in actions if a.get("path") not in ("<ruta>", "ruta")]
        if filtered:
            return filtered

        rescued = _rescue_conversational_action(clean_reasoning)
        filtered = [a for a in rescued if a.get("path") not in ("<ruta>", "ruta")]
        if filtered:
            return filtered

    repaired_c = _repair_unclosed_json(clean_content)
    if repaired_c:
        return repaired_c

    repaired_r = _repair_unclosed_json(clean_reasoning)
    if repaired_r:
        return repaired_r

    snippet_c = (clean_content[:200] + "...") if len(clean_content) > 200 else clean_content
    snippet_r = (clean_reasoning[-300:] + "...") if len(clean_reasoning) > 300 else clean_reasoning
    raise ValueError(
        f"No se encontró ninguna acción JSON válida.\n"
        f"Contenido: {snippet_c!r}\n"
        f"Razonamiento final: {snippet_r!r}"
    )


class LLMClient:
    def __init__(self, model_name: str | None = None) -> None:
        self.url = LLM_BASE_URL.rstrip("/") + "/chat/completions"
        self.model = model_name or LLM_MODEL

    def chat(
        self,
        system_text: str,
        user_text: str,
        on_token: Any = None,
    ) -> tuple[str, str, dict[str, Any]]:

        use_json_mode = os.getenv("LLM_JSON_MODE", "0").strip().lower() not in {"0", "false", "no"}

        def build_payload(json_mode: bool) -> dict:
            payload = {
                "model": self.model,
                "temperature": LLM_TEMPERATURE,
                "presence_penalty": LLM_PRESENCE_PENALTY,
                "repetition_penalty": LLM_REPETITION_PENALTY,
                "max_tokens": LLM_MAX_TOKENS,
                "stream": True,
                "messages": [
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": user_text},
                ],
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            return payload

        def open_stream(json_mode: bool):
            data = json.dumps(build_payload(json_mode)).encode("utf-8")
            req = urllib.request.Request(
                self.url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            return urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S)

        try:
            response = open_stream(use_json_mode)
        except urllib.error.HTTPError as exc:
            if use_json_mode and exc.code in (400, 404, 422):
                response = open_stream(False)
            else:
                raise

        reasoning_chunks: list[str] = []
        content_chunks: list[str] = []
        usage: dict[str, Any] = {}

        is_thinking = False
        has_content = False

        with response:
            while True:
                raw_line = response.readline()
                if not raw_line:
                    break

                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                except Exception:
                    continue

                if "usage" in chunk and chunk["usage"]:
                    usage = chunk["usage"]

                choices = chunk.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})

                r_text = delta.get("reasoning_content") or delta.get("reasoning") or ""
                if r_text:
                    if on_token:
                        try:
                            on_token("reasoning", r_text)
                        except Exception:
                            pass
                    if not is_thinking:
                        print("\n🧠 [Razonamiento de NAIL (RTX 4090)]:\n", end="", flush=True)
                        is_thinking = True
                    print(r_text, end="", flush=True)
                    reasoning_chunks.append(r_text)

                    current_thought = "".join(reasoning_chunks)
                    if len(reasoning_chunks) % 5 == 0 and _detect_loop_ngrams(current_thought):
                        print("\n⚡ [Detector Anti-Bucle]: Ciclo patológico 3x detectado. Procediendo a acción...", flush=True)
                        break

                c_text = delta.get("content") or ""
                if c_text:
                    if on_token:
                        try:
                            on_token("content", c_text)
                        except Exception:
                            pass
                    if is_thinking and not has_content:
                        print("\n\n💡 [Respuesta final / Acción]:\n", end="", flush=True)
                        is_thinking = False
                    elif not has_content and not is_thinking:
                        print("\n💡 [Respuesta final / Acción]:\n", end="", flush=True)
                    has_content = True
                    print(c_text, end="", flush=True)
                    content_chunks.append(c_text)

        print("", flush=True)

        full_content = "".join(content_chunks).strip()
        full_reasoning = "".join(reasoning_chunks).strip()

        if "<think>" in full_content and "</think>" in full_content:
            parts = full_content.split("</think>", 1)
            thought = parts[0].replace("<think>", "").strip()
            answer = parts[1].strip()
            if not full_reasoning:
                full_reasoning = thought
            full_content = answer
        elif "<think>" in full_content and not full_reasoning:
            full_reasoning = full_content.replace("<think>", "").strip()
            full_content = ""

        if not full_content and full_reasoning:
            try:
                rescued_actions = parse_actions("", full_reasoning)
                full_content = json.dumps({"actions": rescued_actions})
                print(f"⚡ [Auto-Rescate Exitoso]: {len(rescued_actions)} acción(es) recuperada(s) del razonamiento.", flush=True)
            except Exception:
                pass

        return full_content, full_reasoning, usage
