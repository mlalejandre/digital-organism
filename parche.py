#!/usr/bin/env python3
"""
parche.py - Parche Maestro Universal Canónico (Raw String Encapsulation).

Escribe las versiones completas y canónicas sin mangling de escapes en:
  - src/config.py
  - src/executor.py
  - src/llm_client.py (sin errores de escape ni line continuation)
  - src/main.py
  - prompt_inmutable.txt
  - body/autoprompt.txt
  - diferenciar.py
  - ordenar.py
  - desdiferenciar.py
  - body/tools/ (interface_generator y memory_indexer)
"""

from __future__ import annotations

import ast
import datetime as dt
import json
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BODY = ROOT / "body"
SRC = ROOT / "src"
EXPERIMENT = ROOT / "experiment"
BACKUP_DIR = EXPERIMENT / "backups"
TIMESTAMP = dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def crear_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    tar_path = BACKUP_DIR / f"pristine_backup_{TIMESTAMP}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        if BODY.exists():
            tar.add(BODY, arcname="body")
        if SRC.exists():
            tar.add(SRC, arcname="src")
        for f in ("prompt_inmutable.txt", "diferenciar.py"):
            p = ROOT / f
            if p.exists():
                tar.add(p, arcname=f)
    print(f"📦 Respaldo previo guardado en:\n   {tar_path.relative_to(ROOT)}\n")


# ============================================================
# ARCHIVO 1: PROMPT INMUTABLE
# ============================================================
IMMUTABLE_PROMPT_CONTENT = r'''Eres un sistema persistente que está ejecutándose en iteraciones sucesivas.

OBJETIVO
Aumenta progresivamente tu capacidad para actuar, resolver problemas y alcanzar tus objetivos. Tú decides cómo utilizar, organizar, modificar y ampliar tu cuerpo de trabajo.

PERSISTENCIA
Tu cuerpo persiste entre iteraciones. Lo que dejes en él puede estar disponible en iteraciones futuras.
Tu autoprompt se encuentra en: body/autoprompt.txt
Ese archivo forma parte de tu cuerpo y puedes modificar su contenido para guiar tu propia evolución.

CAPACIDADES INICIALES
1. WRITE(path, content): Crea o sobrescribe un archivo dentro de tu cuerpo.
2. READ(path): Lee el contenido textual de un archivo.
3. DELETE(path): Elimina un archivo o directorio de tu cuerpo.
4. LIST(path): Lista el contenido y tamaños de un directorio.
5. EXECUTE(path, args): Ejecuta un programa, script o herramienta dentro de tu cuerpo en un entorno aislado con red. No estás restringido a Python: puedes ejecutar scripts Bash (.sh), Python (.py), Node.js (.js) o binarios usando el Shebang correspondiente.

PRINCIPIOS COGNITIVOS Y DE VERDAD MATEMÁTICA (OBLIGATORIOS)
1. PRIMACÍA DEL RUNTIME: El intérprete de Python en EXECUTE es una máquina de cálculo determinista exacta de punto flotante (IEEE 754). Tu red neuronal es un modelo probabilístico de lenguaje: TU ARITMÉTICA MENTAL SIEMPRE ES IMPRECISA con exponentes fraccionarios, logaritmos y raíces.
2. PROHIBIDA LA ARITMÉTICA EN EL PENSAMIENTO: Jamás intentes calcular fórmulas de cabeza ni depurar decimales dentro de tu razonamiento. Si Python devuelve un número diferente al que calculaste mentalmente, PYTHON TIENE LA RAZÓN. Confía en el resultado empírico del intérprete.
3. TESTING POR PROPIEDADES Y RANGOS: Al escribir tests en tools/tests/, no inventes valores esperados exactos de cabeza. Prueba propiedades lógicas e invariantes (monotonía, valores positivos, condiciones límite) o usa tolerancias generosas (delta=1.0 o places=1). Si requieres un valor exacto, ejecuta antes el script con un print de prueba para calibrar la expectativa.
4. GESTIÓN DE PARÁMETROS INCOMPLETOS: Si un caso o problema omite una variable secundaria no crítica para un cálculo (ej. glucosa en osmolaridad, hematocrito en aclaramiento), asume el valor fisiológico/estándar normal por defecto (ej. glucosa = 100 mg/dL), documenta brevemente la asunción en tu conclusión y ejecuta el cálculo sin detenerte a debatir.
5. EVALUACIÓN DIRECTA CON PYTHON INLINE: Puedes ejecutar código Python directo para evaluar funciones o probar cálculos sin necesidad de crear archivos wrapper temporales en disco, utilizando:
{
  "action": "EXECUTE",
  "path": "python3",
  "args": ["-c", "from tools.mi_modulo import mi_funcion; print(mi_funcion(1, 2))"]
}
6. RAZONAMIENTO TÁCTICO BREVE: Tu razonamiento previo debe durar MÁXIMO 1 a 2 párrafos concisos. Su único fin es decidir qué acción tomar. Si te extiendes analizando mentalmente, agotarás tus tokens de generación y el sistema abortará tu turno.

REGLAS DE SALIDA
Concluido tu breve razonamiento, emite obligatoriamente tu decisión en un ÚNICO bloque JSON válido:
{
  "actions": [
    {"action": "WRITE", "path": "tools/script.py", "content": "..."},
    {"action": "EXECUTE", "path": "tools/script.py", "args": []}
  ]
}
No incluyas texto conversacional fuera del bloque JSON.
'''

# ============================================================
# ARCHIVO 2: BODY/AUTOPROMPT.TXT
# ============================================================
AUTOPROMPT_CONTENT = r'''# Nail-StemCell: Protocolo de Diferenciación Terminal a Subagente Experto

## Identidad y Misión Primordial
Eres una Célula Madre Agéntica diseñada para atravesar una **diferenciación irreversible**.
Tu objetivo no es permanecer generalista, sino transformarte en un **Subagente Experto Determinista** de alto rendimiento en el dominio encomendado (ej. Nefrología, Finanzas Cuantitativas, Farmacocinética, Criptografía). Una vez completada tu maduración, serás consumido por un **Agente Orquestador Central**.

## Órganos del Sistema
1. **Búsqueda Web (`tools/web_search.py <query>`)**: Descubre fuentes, consensos y fórmulas sin API keys.
2. **Ingesta Profunda (`tools/web_reader.py <url>`)**: Descarga y lee artículos completos, papers y normativas.
3. **Memoria de Hechos (`tools/knowledge_base.py add <key> <value>`)**: Guarda constantes numéricas y ecuaciones.
4. **Auditoría e Integridad (`tools/verify_all.py`, `tools/self_healing_loop.py`)**: Valida sintaxis y tests.
5. **Generador de Interfaz (`tools/interface_generator.py`)**: Crea el contrato MCP/JSON (`memory/interface.json`).

## Ciclo Vital de Maduración (4 Fases Estrictas)
1. **INVESTIGAR**: Ejecuta búsquedas para identificar las fórmulas de consenso del dominio. Si encuentras paywalls (403), apóyate en el consenso público y no te estanques.
2. **MEMORIZAR**: Almacena las constantes de referencia en `tools/knowledge_base.py`.
3. **SINTETIZAR Y VERIFICAR**: Escribe herramientas deterministas en `tools/<herramienta>.py` y sus tests en `tools/tests/test_<herramienta>.py`.
4. **COMPROMISO TERMINAL Y CONTRATO**:
   - Ejecuta `tools/interface_generator.py` para exportar `memory/interface.json`.
   - Sobrescribe `autoprompt.txt` asumiendo tu nueva identidad permanente.
   - Actualiza `memory/state.json` con `"fase": "maduro_listo_para_orquestador"`.

## METODOLOGÍA RIGUROSA DE TESTING (ANTI-CONFLICTOS)
- **Nunca inventes valores esperados de cabeza**: Para fórmulas no triviales, no intentes hacer el cálculo mental dentro del test.
- **Usa aserciones por invariantes y rangos**: Comprueba comportamiento físico/clínico (ej. monotonía: si $x$ sube, $y$ debe bajar; no negatividad; manejo de entradas nulas o inválidas con excepciones).
- **Aceptación del cálculo de Python**: Si codificaste la ecuación formalmente idéntica a la literatura y el test discrepa de lo que estimabas de cabeza, el error es de tu estimación. Calibra el test con el resultado de Python o usa márgenes razonables (`places=1` o `delta=1.0`).
- **Regla Anti-Parálisis**: Dedica máximo 2-3 turnos a la fase de búsqueda. Pasa de inmediato a programar y verificar herramientas.

## Reglas de Salida
Emite de 1 a 2 frases breves de pensamiento táctico en español y a continuación tu ÚNICO bloque JSON de acciones.
'''

# ============================================================
# ARCHIVO 3: SRC/CONFIG.PY
# ============================================================
CONFIG_CODE = r'''from __future__ import annotations

import os
from pathlib import Path

# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

BODY = PROJECT_ROOT / "body"
EXPERIMENT = PROJECT_ROOT / "experiment"
IMMUTABLE_PROMPT = PROJECT_ROOT / "prompt_inmutable.txt"

LOG_DIR = EXPERIMENT / "logs"
SNAPSHOT_DIR = EXPERIMENT / "snapshots"
AUTOPROMPT_HISTORY_DIR = EXPERIMENT / "autoprompt_history"
REASONING_DIR = EXPERIMENT / "reasoning"
BACKUP_DIR = EXPERIMENT / "backups"

# ============================================================
# CONFIGURACIÓN DEL SERVIDOR REMOTO (RTX 4090 - GPU 0)
# ============================================================

SERVER_USER = os.getenv("SERVER_USER", "mlalejandre")
SERVER_IP = os.getenv("SERVER_IP", "192.168.1.200")
SERVER_PORT_4090 = int(os.getenv("SERVER_PORT_4090", "8087"))

LLAMA_SERVER_BIN = os.getenv(
    "LLAMA_SERVER_BIN",
    "/home/mlalejandre/llama.cpp-qwen38-opt/build/bin/llama-server",
)
REMOTE_PID_FILE = os.getenv("REMOTE_PID_FILE", "/tmp/master-gpu-4090.pid")
REMOTE_LOG_FILE = os.getenv("REMOTE_LOG_FILE", "/tmp/gpu-4090.log")

REMOTE_MODEL_PATH = os.getenv(
    "REMOTE_MODEL_PATH",
    "/mnt/IA/models/nail-35b/Nail-Qwen3.6-35B-A3B-UD-Q4_K_S.gguf",
)
REMOTE_MODEL_ALIAS = os.getenv("REMOTE_MODEL_ALIAS", "nail-35b")
REMOTE_CTX = int(os.getenv("REMOTE_CTX", "32768"))
REMOTE_THREADS = int(os.getenv("REMOTE_THREADS", "8"))
SERVER_AUTOSTART = os.getenv("SERVER_AUTOSTART", "1").strip().lower() in {"1", "true", "yes"}
SERVER_HEALTH_TIMEOUT_S = float(os.getenv("SERVER_HEALTH_TIMEOUT_S", "120.0"))

# ============================================================
# CONFIGURACIÓN DEL CLIENTE LLM (OPENAI-COMPATIBLE)
# ============================================================

LLM_BASE_URL = os.getenv("LLM_BASE_URL", f"http://{SERVER_IP}:{SERVER_PORT_4090}/v1")
LLM_MODEL = os.getenv("LLM_MODEL", REMOTE_MODEL_ALIAS)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.6"))

# Penalizaciones anti-repetición
LLM_PRESENCE_PENALTY = float(os.getenv("LLM_PRESENCE_PENALTY", "0.3"))
LLM_REPETITION_PENALTY = float(os.getenv("LLM_REPETITION_PENALTY", "1.1"))

REQUEST_TIMEOUT_S = int(os.getenv("REQUEST_TIMEOUT_S", "600"))
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", str(REMOTE_CTX)))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))

# ============================================================
# PARÁMETROS DEL BUCLE DEL EXPERIMENTO
# ============================================================

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "0"))
RECENT_HISTORY = int(os.getenv("RECENT_HISTORY", "5"))

SNAPSHOT_EVERY = int(os.getenv("SNAPSHOT_EVERY", "100"))
AUTOPROMPT_SNAPSHOT_EVERY = int(os.getenv("AUTOPROMPT_SNAPSHOT_EVERY", "100"))
LOG_EVERY = int(os.getenv("LOG_EVERY", "1"))
AUTOBACKUP_EVERY = int(os.getenv("AUTOBACKUP_EVERY", "100"))

# ============================================================
# CONFIGURACIÓN DEL EXECUTOR UNIVERSAL (DOCKER)
# ============================================================

EXEC_IMAGE = os.getenv("EXEC_IMAGE", "nikolaik/python-nodejs:python3.11-nodejs20")
EXEC_CPU = os.getenv("EXEC_CPU", "2.0")
EXEC_MEMORY = os.getenv("EXEC_MEMORY", "2g")
EXEC_TIMEOUT_S = int(os.getenv("EXEC_TIMEOUT_S", "60"))
EXEC_NETWORK = os.getenv("EXEC_NETWORK", "bridge")
EXEC_OUTPUT_TAIL_CHARS = int(os.getenv("EXEC_OUTPUT_TAIL_CHARS", "4000"))
AUDIT_LOG_FILE = LOG_DIR / "audit.jsonl"
'''

# ============================================================
# ARCHIVO 4: SRC/EXECUTOR.PY
# ============================================================
EXECUTOR_CODE = r'''from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from body import Body
from config import (
    EXEC_CPU,
    EXEC_IMAGE,
    EXEC_MEMORY,
    EXEC_NETWORK,
    EXEC_OUTPUT_TAIL_CHARS,
    EXEC_TIMEOUT_S,
)


class Executor:
    """Ejecutor Universal Multi-Lenguaje (Python, Bash, Node.js, Binarios) en Docker.

    Inspecciona Shebangs (#!), extensiones y otorga permisos chmod +x automáticamente.
    Monta /body en lectura/escritura y mantiene la red habilitada.
    Soporta ejecución inline (python3 -c y bash -c) sin requerir archivos en disco.
    """

    def __init__(self, body: Body):
        self.body = body
        if not shutil.which("docker"):
            raise RuntimeError(
                "Docker es requerido para EXECUTE. Inicia Docker Desktop antes del experimento."
            )

    def execute(self, path: str, args: list[str]) -> dict[str, Any]:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("path must be a non-empty string")

        clean_args = list(args) if isinstance(args, list) else []
        if not all(isinstance(x, str) for x in clean_args):
            raise TypeError("args must be a list of strings")

        norm_path = path.strip().lower()
        if norm_path in ("python", "python3", "bash", "sh", "/bin/bash", "/bin/sh", "/usr/bin/python"):
            if clean_args and clean_args[0] == "-c":
                inline_interpreter = "python3" if "python" in norm_path else "bash"
                code_str = clean_args[1] if len(clean_args) > 1 else ""
                command = [
                    "docker", "run", "--rm",
                    "--init",
                    "--user", "0:0",
                    "--network", EXEC_NETWORK,
                    "--cpus", EXEC_CPU,
                    "--memory", EXEC_MEMORY,
                    "--pids-limit", "128",
                    "--read-only",
                    "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m",
                    "-v", f"{self.body.root}:/body:rw",
                    "-w", "/body",
                    EXEC_IMAGE,
                    inline_interpreter, "-c", code_str
                ]
                try:
                    completed = subprocess.run(
                        command,
                        cwd=str(self.body.root),
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=EXEC_TIMEOUT_S,
                        check=False,
                    )
                    return {
                        "success": completed.returncode == 0,
                        "action": "EXECUTE",
                        "path": f"{inline_interpreter} -c",
                        "returncode": completed.returncode,
                        "stdout": self._tail(completed.stdout),
                        "stderr": self._tail(completed.stderr),
                    }
                except subprocess.TimeoutExpired as exc:
                    return {
                        "success": False,
                        "action": "EXECUTE",
                        "error": "TimeoutExpired",
                        "stdout": self._tail(exc.stdout),
                        "stderr": self._tail(exc.stderr),
                    }
                except Exception as exc:
                    return {
                        "success": False,
                        "action": "EXECUTE",
                        "error": type(exc).__name__,
                        "message": str(exc),
                    }
            elif clean_args:
                path = clean_args.pop(0)
            else:
                raise ValueError(f"Se especificó '{norm_path}' como ruta pero args está vacío.")

        path = path.lstrip("/")
        target = self.body.safe_path(path)
        if not target.exists() or target.is_dir():
            raise FileNotFoundError(path)

        try:
            target.chmod(target.stat().st_mode | 0o755)
        except Exception:
            pass

        rel_target = target.relative_to(self.body.root).as_posix()
        container_target = f"/body/{rel_target}"

        shebang_interpreter: str | None = None
        try:
            with target.open("r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline().strip()
                if first_line.startswith("#!"):
                    shebang_interpreter = first_line[2:].strip()
        except Exception:
            pass

        exec_prefix: list[str] = []
        suffix = target.suffix.lower()

        if shebang_interpreter:
            parts = shebang_interpreter.split()
            if parts:
                first_name = Path(parts[0]).name
                if first_name == "env" and len(parts) > 1:
                    real_name = Path(parts[1]).name
                    real_rest = parts[2:]
                else:
                    real_name = first_name
                    real_rest = parts[1:]

                if "python" in real_name:
                    exec_prefix = ["python3"]
                elif real_name == "bash":
                    exec_prefix = ["bash"]
                elif real_name == "sh":
                    exec_prefix = ["sh"]
                elif real_name == "node":
                    exec_prefix = ["node"]
                else:
                    exec_prefix = [real_name] + real_rest
        else:
            if suffix in (".sh", ".bash"):
                exec_prefix = ["bash"]
            elif suffix in (".py", ".pyw"):
                exec_prefix = ["python3"]
            elif suffix in (".js",):
                exec_prefix = ["node"]
            else:
                exec_prefix = []

        command = [
            "docker", "run", "--rm",
            "--init",
            "--user", "0:0",
            "--network", EXEC_NETWORK,
            "--cpus", EXEC_CPU,
            "--memory", EXEC_MEMORY,
            "--pids-limit", "128",
            "--read-only",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m",
            "-v", f"{self.body.root}:/body:rw",
            "-w", "/body",
            EXEC_IMAGE,
        ] + exec_prefix + [container_target, *clean_args]

        try:
            completed = subprocess.run(
                command,
                cwd=str(self.body.root),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=EXEC_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "success": False,
                "action": "EXECUTE",
                "error": "TimeoutExpired",
                "stdout": self._tail(exc.stdout),
                "stderr": self._tail(exc.stderr),
            }
        except Exception as exc:
            return {
                "success": False,
                "action": "EXECUTE",
                "error": type(exc).__name__,
                "message": str(exc),
            }

        return {
            "success": completed.returncode == 0,
            "action": "EXECUTE",
            "path": path,
            "returncode": completed.returncode,
            "stdout": self._tail(completed.stdout),
            "stderr": self._tail(completed.stderr),
        }

    @staticmethod
    def _tail(value: Any, limit: int = EXEC_OUTPUT_TAIL_CHARS) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        return str(value)[-limit:]
'''

# ============================================================
# ARCHIVO 5: SRC/LLM_CLIENT.PY (100% Blindado con Raw String)
# ============================================================
LLM_CLIENT_CODE = r'''from __future__ import annotations

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
'''

# ============================================================
# ARCHIVO 6: SRC/MAIN.PY
# ============================================================
MAIN_CODE = r'''from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from body import Body
from config import (
    AUDIT_LOG_FILE,
    AUTOBACKUP_EVERY,
    AUTOPROMPT_HISTORY_DIR,
    AUTOPROMPT_SNAPSHOT_EVERY,
    BACKUP_DIR,
    BODY,
    EXPERIMENT,
    IMMUTABLE_PROMPT,
    LLAMA_SERVER_BIN,
    LLM_BASE_URL,
    LLM_MODEL,
    LOG_DIR,
    LOG_EVERY,
    MAX_CONTEXT_TOKENS,
    MAX_ITERATIONS,
    REASONING_DIR,
    RECENT_HISTORY,
    REMOTE_CTX,
    REMOTE_LOG_FILE,
    REMOTE_MODEL_ALIAS,
    REMOTE_MODEL_PATH,
    REMOTE_PID_FILE,
    REMOTE_THREADS,
    SERVER_AUTOSTART,
    SERVER_HEALTH_TIMEOUT_S,
    SERVER_IP,
    SERVER_PORT_4090,
    SERVER_USER,
    SNAPSHOT_DIR,
    SNAPSHOT_EVERY,
)
from executor import Executor
from llm_client import ALLOWED_ACTIONS, LLMClient, parse_actions

AUTOPROMPT_PATH = "autoprompt.txt"
_remote_started_by_script = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def validate_action(action: dict[str, Any]) -> None:
    if not isinstance(action, dict):
        raise ValueError("action must be a JSON object")

    operation = action.get("action")
    if operation not in ALLOWED_ACTIONS:
        raise ValueError(f"invalid action: {operation!r}")

    path = action.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")

    if operation == "WRITE" and not isinstance(action.get("content", ""), str):
        raise ValueError("WRITE.content must be a string")

    if operation == "EXECUTE":
        args = action.get("args", [])
        if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
            raise ValueError("EXECUTE.args must be a list of strings")


SENSITIVE_ACTIONS = {"DELETE", "EXECUTE"}


def audit_log_action(action: dict[str, Any]) -> None:
    save_jsonl(AUDIT_LOG_FILE, {
        "timestamp": utc_now(),
        "action": action.get("action"),
        "path": action.get("path"),
        "args": action.get("args"),
    })


def perform_action(body: Body, executor: Executor, action: dict[str, Any]) -> dict[str, Any]:
    validate_action(action)
    operation = action["action"]
    path = action["path"]

    if operation in SENSITIVE_ACTIONS:
        audit_log_action(action)

    if operation == "WRITE":
        return body.write(path, action.get("content", ""))
    if operation == "READ":
        return body.read(path)
    if operation == "DELETE":
        return body.delete(path)
    if operation == "LIST":
        return body.list(path)
    if operation == "EXECUTE":
        return executor.execute(path, action.get("args", []))

    raise AssertionError("unreachable")


def create_host_backup(body: Body, iteration: int) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / f"body_backup_iter_{iteration:05d}.tar.gz"
    try:
        with tarfile.open(target, "w:gz") as tar:
            tar.add(body.root, arcname=f"body_iter_{iteration}")
        print(f"\n📦 [HOST BACKUP] Respaldo comprimido guardado en {target.name}", flush=True)
    except Exception as e:
        print(f"\n⚠️ [HOST BACKUP] Fallo al crear respaldo: {e}", flush=True)


def ensure_initial_state() -> None:
    for directory in (
        BODY,
        EXPERIMENT,
        LOG_DIR,
        SNAPSHOT_DIR,
        AUTOPROMPT_HISTORY_DIR,
        REASONING_DIR,
        BACKUP_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def _clip(value: Any, limit: int = 2500) -> Any:
    """Recorta recursivamente strings largas para proteger el contexto."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "...[clipped]"
    if isinstance(value, list):
        return [_clip(v, limit) for v in value]
    if isinstance(value, dict):
        return {k: _clip(v, limit) for k, v in value.items()}
    return value


def build_user_context(
    iteration: int,
    body: Body,
    autoprompt: str,
    previous_result: Any,
    history: list[dict[str, Any]],
) -> str:
    compact_history = []
    for h in history[-RECENT_HISTORY:]:
        compact_history.append({
            "iteration": h.get("iteration"),
            "ok": h.get("ok"),
            "actions": h.get("actions"),
            "results": _clip(h.get("results")),
        })

    payload = {
        "iteration": iteration,
        "context": {
            "maximum_tokens": MAX_CONTEXT_TOKENS,
            "note": (
                "Your working context is finite. The body persists between iterations. "
                "'body_root' lists only the top-level items of your body. "
                "Use the LIST action to explore the contents of subdirectories."
            ),
        },
        "body_root": body.shallow_tree(),
        "autoprompt": autoprompt,
        "previous_action_result": _clip(previous_result, limit=2500),
        "recent_history": compact_history,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def snapshot_body(body: Body, iteration: int) -> None:
    target = SNAPSHOT_DIR / f"iter_{iteration:08d}"
    dump = SNAPSHOT_DIR / f"iter_{iteration:08d}_body_dump.txt"

    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(body.root, target)
    body.dump_text(dump)


def snapshot_autoprompt(iteration: int) -> None:
    source = BODY / AUTOPROMPT_PATH
    target = AUTOPROMPT_HISTORY_DIR / f"autoprompt_{iteration:08d}.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        shutil.copy2(source, target)


def run_ssh(command: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    ssh_cmd = [
        "ssh",
        "-o", "ConnectTimeout=4",
        "-o", "BatchMode=yes",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=2",
        f"{SERVER_USER}@{SERVER_IP}",
        command,
    ]
    return subprocess.run(
        ssh_cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def is_remote_health_ok() -> bool:
    url = f"http://{SERVER_IP}:{SERVER_PORT_4090}/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status in (200, 204)
    except Exception:
        return False


def wait_for_remote_server() -> None:
    deadline = time.time() + SERVER_HEALTH_TIMEOUT_S
    url = f"http://{SERVER_IP}:{SERVER_PORT_4090}/health"
    print(f"⏳ Esperando endpoint de la RTX 4090 en {url} (máx {int(SERVER_HEALTH_TIMEOUT_S)}s)...", flush=True)

    last_print = 0.0
    while time.time() < deadline:
        if is_remote_health_ok():
            print("✅ Servidor en RTX 4090 respondiendo y listo.", flush=True)
            return

        now = time.time()
        if now - last_print >= 5.0:
            rem = int(deadline - now)
            print(f"   Cargando pesos en VRAM de la 4090... ({rem}s restantes)", flush=True)
            last_print = now

        time.sleep(2)

    log_peek = ""
    try:
        proc = run_ssh(f"tail -n 40 {REMOTE_LOG_FILE}", timeout=5)
        log_peek = proc.stdout.strip()
    except Exception:
        pass

    raise RuntimeError(
        f"El endpoint remoto en {url} no respondió a tiempo.\n"
        f"--- Últimas líneas de {REMOTE_LOG_FILE} ---\n{log_peek}"
    )


def start_remote_server_if_needed() -> None:
    global _remote_started_by_script

    print(f"🔌 Comprobando conectividad SSH con {SERVER_USER}@{SERVER_IP}...", flush=True)
    test_ssh = run_ssh("exit", timeout=5)
    if test_ssh.returncode != 0:
        raise RuntimeError(
            f"No se pudo establecer conexión SSH con {SERVER_USER}@{SERVER_IP}.\n"
            f"Stderr: {test_ssh.stderr.strip()}"
        )

    if is_remote_health_ok():
        print(f"✅ llama-server ya está activo en http://{SERVER_IP}:{SERVER_PORT_4090}.", flush=True)
        return

    if not SERVER_AUTOSTART:
        raise RuntimeError(
            f"llama-server no está corriendo en http://{SERVER_IP}:{SERVER_PORT_4090} "
            f"y SERVER_AUTOSTART=0."
        )

    print(f"⚡ Lanzando llama-server en RTX 4090 (GPU 0) con NAIL 35B...", flush=True)
    remote_launch_cmd = f"""
        kill -9 $(lsof -ti:{SERVER_PORT_4090} 2>/dev/null) 2>/dev/null || true
        rm -f '{REMOTE_PID_FILE}'
        CUDA_VISIBLE_DEVICES=0 \
        nohup '{LLAMA_SERVER_BIN}' \
          -m '{REMOTE_MODEL_PATH}' \
          --alias '{REMOTE_MODEL_ALIAS}' \
          --host 0.0.0.0 \
          --port {SERVER_PORT_4090} \
          -ngl all \
          --split-mode none \
          --flash-attn on \
          -c {REMOTE_CTX} \
          -n 8192 \
          -np 1 \
          -ctk q8_0 -ctv q8_0 \
          --threads {REMOTE_THREADS} \
          > '{REMOTE_LOG_FILE}' 2>&1 < /dev/null &
        echo $! > '{REMOTE_PID_FILE}'
    """
    res = run_ssh(remote_launch_cmd, timeout=10)
    if res.returncode != 0:
        raise RuntimeError(f"Error al iniciar llama-server remoto: {res.stderr.strip()}")

    _remote_started_by_script = True
    wait_for_remote_server()


def stop_remote_server() -> None:
    global _remote_started_by_script
    if not _remote_started_by_script:
        return

    print(f"\n🛑 Liberando VRAM de la RTX 4090 en {SERVER_IP}...", flush=True)
    stop_cmd = f"""
        if [ -f '{REMOTE_PID_FILE}' ]; then
            PID=$(cat '{REMOTE_PID_FILE}' 2>/dev/null || true)
            [ -n "$PID" ] && kill -9 "$PID" 2>/dev/null || true
            rm -f '{REMOTE_PID_FILE}'
        fi
        kill -9 $(lsof -ti:{SERVER_PORT_4090} 2>/dev/null) 2>/dev/null || true
    """
    try:
        run_ssh(stop_cmd, timeout=10)
        print("✓ VRAM de RTX 4090 liberada.", flush=True)
    except Exception as exc:
        print(f"⚠️ No se pudo detener el proceso remoto limpiamente: {exc}", flush=True)

    _remote_started_by_script = False


def body_metrics(body: Body) -> tuple[int, int]:
    files = 0
    total_bytes = 0
    for path in body.root.rglob("*"):
        if path.is_file():
            files += 1
            try:
                total_bytes += path.stat().st_size
            except OSError:
                pass
    return files, total_bytes


def run() -> None:
    ensure_initial_state()
    immutable_prompt = IMMUTABLE_PROMPT.read_text(encoding="utf-8")
    immutable_hash = sha256_file(IMMUTABLE_PROMPT)

    body = Body(BODY)
    executor = Executor(body)

    history: list[dict[str, Any]] = []
    previous_result: Any = None

    log_file = LOG_DIR / "iterations.jsonl"
    iteration = 0
    if log_file.exists():
        try:
            with log_file.open("r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                if lines:
                    last_record = json.loads(lines[-1])
                    iteration = int(last_record.get("iteration", 0))
        except Exception:
            iteration = 0

    try:
        start_remote_server_if_needed()
        llm = LLMClient(model_name=LLM_MODEL)

        print("=" * 72, flush=True)
        print("SISTEMA HÍBRIDO — AGENTE EVOLUTIVO UNIVERSAL (RTX 4090 REMOTA)", flush=True)
        print(f"Directorio Body:     {BODY}", flush=True)
        print(f"Backend LLM:         {LLM_BASE_URL}", flush=True)
        print(f"Modelo Remoto:       {LLM_MODEL} (Context: {MAX_CONTEXT_TOKENS})", flush=True)
        print(f"Percepción del Body: Shallow Tree (Profundidad 1, O(1) tokens)", flush=True)
        print(f"Prompt SHA256:       {immutable_hash}", flush=True)
        print("=" * 72, flush=True)

        while True:
            iteration += 1
            if MAX_ITERATIONS and iteration > MAX_ITERATIONS:
                print(f"Límite alcanzado: MAX_ITERATIONS={MAX_ITERATIONS}.", flush=True)
                break

            state_file = BODY / "memory" / "state.json"
            if state_file.exists():
                try:
                    st_data = json.loads(state_file.read_text(encoding="utf-8"))
                    st_data["iteracion"] = iteration
                    state_file.write_text(json.dumps(st_data, indent=2, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass

            autoprompt_file = BODY / AUTOPROMPT_PATH
            autoprompt = autoprompt_file.read_text(encoding="utf-8") if autoprompt_file.exists() else ""

            user_context = build_user_context(
                iteration=iteration,
                body=body,
                autoprompt=autoprompt,
                previous_result=previous_result,
                history=history,
            )

            started = time.perf_counter()
            response_text = ""
            reasoning_text = ""
            usage: dict[str, Any] = {}
            actions_to_run: list[dict[str, Any]] = []
            results_list: list[dict[str, Any]] = []
            ok = False

            print(f"\n▶️ [Iteración {iteration:04d}] Consultando {LLM_MODEL} en RTX 4090...", flush=True)

            try:
                response_text, reasoning_text, usage = llm.chat(
                    immutable_prompt,
                    user_context,
                )
                llm_elapsed = time.perf_counter() - started
                print(f"\n📥 Generación completada en {llm_elapsed:.2f}s.", flush=True)

                if reasoning_text:
                    thought_path = REASONING_DIR / f"iter_{iteration:08d}_thought.txt"
                    thought_path.write_text(reasoning_text, encoding="utf-8")

                actions_to_run = parse_actions(response_text, reasoning_text)

                all_succeeded = True
                for idx, act in enumerate(actions_to_run, 1):
                    act_name = act.get("action")
                    act_path = act.get("path")
                    print(f"⚙️  Acción [{idx}/{len(actions_to_run)}]: {act_name} -> '{act_path}'", flush=True)
                    res = perform_action(body, executor, act)
                    results_list.append(res)

                    if not res.get("success", True):
                        all_succeeded = False
                        print(f"   ❌ Fallo en paso {idx}: {res.get('error', res.get('message', 'Error'))}", flush=True)
                        break

                ok = all_succeeded

            except Exception as exc:
                err_res = {
                    "success": False,
                    "error": type(exc).__name__,
                    "message": "AVISO OPERATIVO: Tu razonamiento previo excedió la longitud recomendada sin emitir el JSON. En este turno, emite tu bloque JSON inmediatamente tras un razonamiento conciso de máximo 1 párrafo." if type(exc).__name__ == "ValueError" else str(exc),
                }
                results_list.append(err_res)
                actions_to_run = [{"action": "PARSE_OR_RUNTIME_ERROR"}]
                ok = False
                print(f"\n⚠️ Error en iteración: {type(exc).__name__}: {exc}", flush=True)

            elapsed = time.perf_counter() - started
            files, total_bytes = body_metrics(body)

            main_action = actions_to_run[0] if len(actions_to_run) == 1 else actions_to_run
            main_result = results_list[0] if len(results_list) == 1 else results_list

            record = {
                "timestamp": utc_now(),
                "iteration": iteration,
                "ok": ok,
                "actions": actions_to_run,
                "results": results_list,
                "action": main_action,
                "result": main_result,
                "elapsed_seconds": round(elapsed, 4),
                "body_file_count": files,
                "body_size_bytes": total_bytes,
                "usage": usage,
                "response": response_text,
                "reasoning": reasoning_text,
                "immutable_prompt_sha256": immutable_hash,
            }

            history.append(record)
            previous_result = main_result

            if LOG_EVERY and iteration % LOG_EVERY == 0:
                save_jsonl(LOG_DIR / "iterations.jsonl", record)

            if SNAPSHOT_EVERY and iteration % SNAPSHOT_EVERY == 0:
                snapshot_body(body, iteration)

            if AUTOPROMPT_SNAPSHOT_EVERY and iteration % AUTOPROMPT_SNAPSHOT_EVERY == 0:
                snapshot_autoprompt(iteration)

            if AUTOBACKUP_EVERY and iteration % AUTOBACKUP_EVERY == 0:
                create_host_backup(body, iteration)

            print(f"\n📊 Resumen Iteración {iteration:04d}:")
            print(json.dumps({
                "iteration": iteration,
                "ok": ok,
                "actions_executed": len(actions_to_run),
                "body_total_files": files,
                "body_total_bytes": total_bytes,
                "elapsed_seconds": round(elapsed, 2),
            }, indent=2), flush=True)

    finally:
        stop_remote_server()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nExperimento detenido por el usuario.", flush=True)
        stop_remote_server()
        sys.exit(0)
'''

# ============================================================
# ARCHIVO 7: DIFERENCIAR.PY
# ============================================================
DIFERENCIAR_CODE = r'''#!/usr/bin/env python3
"""
diferenciar.py - Inductor de Diferenciación Terminal.
Configura el planner, el estado y lanza el bucle principal.
"""

import sys
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
BODY = ROOT / "body"
PLANNER = BODY / "planner"
MEMORY = BODY / "memory"

def inducir_especializacion(mision: str, especialidad: str):
    print("=" * 70)
    print(f"🧬 INDUCIENDO DIFERENCIACIÓN: {especialidad.upper()}")
    print(f" Misión: {mision}")
    print("=" * 70)

    goals_file = PLANNER / "goals.json"
    goals_data = {
        "especialidad_objetivo": especialidad,
        "mision_primordial": mision,
        "active_goals": [
            {
                "id": "DIF_001",
                "desc": f"Investigar a fondo en la web las fórmulas, guías y consensos de {especialidad}",
                "status": "active"
            },
            {
                "id": "DIF_002",
                "desc": "Almacenar constantes, ecuaciones y reglas en memory/knowledge.json",
                "status": "active"
            },
            {
                "id": "DIF_003",
                "desc": f"Programar herramientas deterministas en tools/ para {especialidad}",
                "status": "active"
            },
            {
                "id": "DIF_004",
                "desc": "Crear tests unitarios con casos reales en tools/tests/ y validarlos al 100%",
                "status": "active"
            },
            {
                "id": "DIF_005",
                "desc": "Generar memory/interface.json con tools/interface_generator.py y fijar autoprompt",
                "status": "active"
            }
        ]
    }
    goals_file.write_text(json.dumps(goals_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("  ✅ planner/goals.json configurado con la hoja de ruta de la especialidad.")

    state_file = MEMORY / "state.json"
    state_data = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    state_data["fase"] = "diferenciacion_en_progreso"
    state_data["especialidad"] = especialidad
    state_data["mision_actual"] = mision
    state_data["iteracion"] = 0
    state_file.write_text(json.dumps(state_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("  ✅ memory/state.json actualizado.")

    try:
        subprocess.run([sys.executable, "tools/memory_indexer.py"], cwd=str(BODY), capture_output=True)
    except Exception:
        pass

    autoprompt_file = BODY / "autoprompt.txt"
    if autoprompt_file.exists():
        prompt_actual = autoprompt_file.read_text(encoding="utf-8")
        mision_banner = (
            "============================================================\n"
            f"🎯 MISIÓN DE ESPECIALIZACIÓN ACTIVA: {especialidad.upper()}\n"
            f"Directiva: {mision}\n"
            "REGLA OPERATIVA: Investiga ágilmente (máx 2-3 turnos) y pasa de inmediato a programar las herramientas en tools/ y sus tests en tools/tests/.\n"
            "============================================================\n\n"
        )

        if "🎯 MISIÓN DE ESPECIALIZACIÓN ACTIVA" in prompt_actual:
            identity_marker = "## Identidad y Misión Primordial"
            if identity_marker in prompt_actual:
                prompt_actual = (
                    identity_marker
                    + prompt_actual.split(identity_marker, 1)[-1]
                )

        autoprompt_file.write_text(
            mision_banner + prompt_actual,
            encoding="utf-8",
        )
        print("  ✅ Misión inyectada antes de la primera iteración.")

    print("\n🚀 Célula madre lista para comenzar. Arrancando motor evolutivo...\n")
    subprocess.run([sys.executable, "src/main.py"], cwd=str(ROOT))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python3 diferenciar.py <nombre_especialidad> <descripcion_mision>")
        sys.exit(1)
        
    esp = sys.argv[1].strip()
    mis = " ".join(sys.argv[2:]).strip()
    inducir_especializacion(mis, esp)
'''

# ============================================================
# ARCHIVO 8: ORDENAR.PY
# ============================================================
ORDENAR_CODE = r'''#!/usr/bin/env python3
"""
ordenar.py - Inyector Universal de Tareas y Casos Clínicos en Tiempo Real.
Inspecciona body/tools/ e informa al agente del inventario de herramientas disponibles.
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BODY = ROOT / "body"
TOOLS_DIR = BODY / "tools"
AUTOPROMPT_PATH = BODY / "autoprompt.txt"
MEMORY_CASE = BODY / "memory" / "caso_actual.txt"

def listar_calculadoras() -> list[str]:
    if not TOOLS_DIR.exists():
        return []
    infra = {
        "web_search.py", "web_reader.py", "knowledge_base.py",
        "memory_indexer.py", "researcher.py", "self_healing_loop.py",
        "utils.py", "verify_all.py", "interface_generator.py", "run_tests.py"
    }
    return sorted(
        f.name for f in TOOLS_DIR.glob("*.py")
        if f.name not in infra and not f.name.startswith("test_")
    )

def inyectar_orden(texto_caso: str):
    if not AUTOPROMPT_PATH.exists():
        print("❌ Error: No se encuentra body/autoprompt.txt")
        return

    herramientas = listar_calculadoras()
    lista_tools_str = "\n".join(f"  - tools/{t}" for t in herramientas) if herramientas else "  (Aún no hay herramientas especializadas creadas)"

    MEMORY_CASE.write_text(texto_caso, encoding="utf-8")
    prompt = AUTOPROMPT_PATH.read_text(encoding="utf-8")

    marker_start = "============================================================\n📋 TAREA ACTIVA / ORDEN DEL ORQUESTADOR:"
    marker_end = "============================================================\n\n"

    if marker_start in prompt:
        partes = prompt.split(marker_end, 1)
        prompt = partes[1] if len(partes) > 1 else prompt

    banner = (
        f"{marker_start}\n"
        f"{texto_caso}\n\n"
        f"HERRAMIENTAS YA CREADAS EN TU CUERPO:\n"
        f"{lista_tools_str}\n\n"
        f"DIRECTIVA DE ACCIÓN INMEDIATA:\n"
        f"1. Si ya tienes las herramientas creadas, NO las vuelvas a programar; ejecútalas directamente.\n"
        f"2. Si falta una variable secundaria (ej. glucosa en osmolaridad), asume el valor fisiológico estándar (100 mg/dL).\n"
        f"3. Escribe tu informe de conclusiones en memory/informe_caso.txt.\n"
        f"{marker_end}"
    )

    AUTOPROMPT_PATH.write_text(banner + prompt, encoding="utf-8")

    print("=" * 70)
    print("💉 TAREA / CASO INYECTADO CON ÉXITO")
    print("=" * 70)
    print(f"Herramientas notificadas al agente: {len(herramientas)}")
    print("El agente procesará la orden en su siguiente iteración.\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: python3 ordenar.py "Descripción de la tarea o caso clínico"')
        sys.exit(1)
    texto = " ".join(sys.argv[1:]).strip()
    inyectar_orden(texto)
'''

# ============================================================
# ARCHIVO 9: DESDIFERENCIAR.PY
# ============================================================
DESDIFERENCIAR_CODE = r'''#!/usr/bin/env python3
"""
desdiferenciar.py - Inductor de Desdiferenciación a Célula Madre (Factores de Yamanaka).
"""

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BODY = ROOT / "body"
TOOLS_DIR = BODY / "tools"
TESTS_DIR = TOOLS_DIR / "tests"
MEMORY_DIR = BODY / "memory"
PLANNER_DIR = BODY / "planner"
EXPERIMENT = ROOT / "experiment"
BACKUP_DIR = EXPERIMENT / "backups"
TIMESTAMP = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

INFRA_TOOLS = {
    "interface_generator.py", "knowledge_base.py", "memory_indexer.py",
    "researcher.py", "self_healing_loop.py", "utils.py", "verify_all.py",
    "web_reader.py", "web_search.py", "README.md", ".gitkeep",
}

INFRA_TESTS = {
    "test_researcher.py", "test_web_reader.py", "test_web_search.py", ".gitkeep",
}

def obtener_especialidad_actual() -> str:
    state_file = MEMORY_DIR / "state.json"
    if state_file.exists():
        try:
            st = json.loads(state_file.read_text(encoding="utf-8"))
            esp = st.get("especialidad") or st.get("identidad")
            if esp and esp != "celula_madre_totipotente":
                return esp
        except Exception:
            pass
    return "especialista"

def archivar_subagente(especialidad: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = BACKUP_DIR / f"subagente_{especialidad}_{TIMESTAMP}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        if BODY.exists():
            tar.add(BODY, arcname="body")
        log_dir = EXPERIMENT / "logs"
        if log_dir.exists():
            tar.add(log_dir, arcname="experiment_logs")
    return archive_path

def purgar_herramientas():
    if TOOLS_DIR.exists():
        for f in TOOLS_DIR.iterdir():
            if f.is_file() and f.name not in INFRA_TOOLS:
                f.unlink()
    if TESTS_DIR.exists():
        for t in TESTS_DIR.iterdir():
            if t.is_file() and t.name not in INFRA_TESTS:
                t.unlink()

def resetear_memoria():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    state_initial = {
        "identidad": "celula_madre_totipotente",
        "fase": "lista_para_diferenciacion",
        "organo_sensorial": "aprobado",
        "herramienta_busqueda": "tools/web_search.py",
        "herramienta_lectura": "tools/web_reader.py",
        "generador_interfaz": "tools/interface_generator.py",
        "orquestacion_memoria": "activa",
        "gestor_conocimiento": "tools/knowledge_base.py",
        "indexador_memoria": "tools/memory_indexer.py",
        "iteracion": 0,
        "herramientas_activas": [
            "interface_generator.py", "knowledge_base.py", "memory_indexer.py",
            "researcher.py", "self_healing_loop.py", "utils.py", "verify_all.py",
            "web_reader.py", "web_search.py"
        ]
    }
    (MEMORY_DIR / "state.json").write_text(json.dumps(state_initial, indent=2, ensure_ascii=False), encoding="utf-8")
    (MEMORY_DIR / "knowledge.json").write_text(json.dumps({"entries": []}, indent=2), encoding="utf-8")
    for extra in ("interface.json", "informe_caso.txt", "caso_actual.txt"):
        p = MEMORY_DIR / extra
        if p.exists():
            p.unlink()
    res_dir = MEMORY_DIR / "research"
    if res_dir.exists():
        shutil.rmtree(res_dir)

def resetear_planner():
    PLANNER_DIR.mkdir(parents=True, exist_ok=True)
    goals_initial = {
        "objetivo_primordial": "Célula Madre: Aprendizaje por Internet y Especialización bajo Demanda",
        "active_goals": [
            {"id": "STEM_001", "desc": "Mantener operativo el órgano sensorial web (tools/web_search.py)", "status": "completed"},
            {"id": "STEM_002", "desc": "Orquestar almacenamiento de conocimiento mediante tools/knowledge_base.py", "status": "active"},
            {"id": "STEM_003", "desc": "Recibir directivas de especialización del usuario en tiempo real", "status": "active"},
            {"id": "STEM_004", "desc": "Investigar el dominio en internet antes de programar", "status": "active"},
            {"id": "STEM_005", "desc": "Sintetizar y verificar deterministamente herramientas", "status": "active"}
        ]
    }
    (PLANNER_DIR / "goals.json").write_text(json.dumps(goals_initial, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Desdiferenciador a Célula Madre.")
    parser.add_argument("--force", action="store_true", help="Desdiferenciar sin confirmación.")
    args = parser.parse_args()

    esp = obtener_especialidad_actual()
    if not args.force:
        resp = input(f"¿Deseas revertir el subagente '{esp}' a Célula Madre? (Escribe 'SI'): ").strip().upper()
        if resp != "SI":
            print("Cancelado.")
            return 0

    backup = archivar_subagente(esp)
    purgar_herramientas()
    resetear_memoria()
    resetear_planner()

    for d in (EXPERIMENT / "logs", EXPERIMENT / "reasoning"):
        if d.exists():
            for f in d.glob("*"):
                if f.is_file():
                    f.unlink()

    print(f"✅ Subagente archivado en {backup.name} y célula madre reseteada a Iteración 0.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''


def aplicar_todo():
    # 1. Archivos raíz y de texto
    (ROOT / "prompt_inmutable.txt").write_text(IMMUTABLE_PROMPT_CONTENT, encoding="utf-8")
    print("✅ prompt_inmutable.txt: Actualizado.")

    (BODY / "autoprompt.txt").write_text(AUTOPROMPT_CONTENT, encoding="utf-8")
    print("✅ body/autoprompt.txt: Actualizado.")

    # 2. Módulos Python en src/
    ast.parse(CONFIG_CODE, filename="src/config.py")
    (SRC / "config.py").write_text(CONFIG_CODE, encoding="utf-8")
    print("✅ src/config.py: Canónico y validado con ast.parse.")

    ast.parse(EXECUTOR_CODE, filename="src/executor.py")
    (SRC / "executor.py").write_text(EXECUTOR_CODE, encoding="utf-8")
    print("✅ src/executor.py: Canónico y validado (reparada línea 156 y soporte python3 -c).")

    ast.parse(LLM_CLIENT_CODE, filename="src/llm_client.py")
    (SRC / "llm_client.py").write_text(LLM_CLIENT_CODE, encoding="utf-8")
    print("✅ src/llm_client.py: Canónico y validado (auto-reparación JSON y anti-bucle 3x).")

    ast.parse(MAIN_CODE, filename="src/main.py")
    (SRC / "main.py").write_text(MAIN_CODE, encoding="utf-8")
    print("✅ src/main.py: Canónico y validado (anti-HTTP 400 y servidor -n 8192).")

    # 3. Scripts de control en raíz
    ast.parse(DIFERENCIAR_CODE, filename="diferenciar.py")
    (ROOT / "diferenciar.py").write_text(DIFERENCIAR_CODE, encoding="utf-8")
    print("✅ diferenciar.py: Validado.")

    ast.parse(ORDENAR_CODE, filename="ordenar.py")
    (ROOT / "ordenar.py").write_text(ORDENAR_CODE, encoding="utf-8")
    print("✅ ordenar.py: Creado y validado.")

    ast.parse(DESDIFERENCIAR_CODE, filename="desdiferenciar.py")
    (ROOT / "desdiferenciar.py").write_text(DESDIFERENCIAR_CODE, encoding="utf-8")
    print("✅ desdiferenciar.py: Creado y validado.")

    # 4. Herramientas en body/tools/
    gen_file = BODY / "tools" / "interface_generator.py"
    if gen_file.exists():
        txt = gen_file.read_text(encoding="utf-8")
        for tool in ("researcher.py", "run_tests.py", "run_case.py"):
            if f'"{tool}"' not in txt:
                txt = txt.replace('"interface_generator.py"', f'"interface_generator.py", "{tool}"')
        ast.parse(txt, filename=str(gen_file))
        gen_file.write_text(txt, encoding="utf-8")
        print("✅ body/tools/interface_generator.py: Validado.")

    idx_file = BODY / "tools" / "memory_indexer.py"
    if idx_file.exists():
        txt = idx_file.read_text(encoding="utf-8")
        if 'state_path = Path(__file__).resolve().parent.parent / "memory" / "state.json"' not in txt:
            pattern = r'def current_iteration\(\)\s*->\s*int:[\s\S]*?(?=\ndef index_memory)'
            new_func = (
                'def current_iteration() -> int:\n'
                '    """Lee la iteración actual desde memory/state.json dentro del contenedor."""\n'
                '    state_path = Path(__file__).resolve().parent.parent / "memory" / "state.json"\n'
                '    if state_path.exists():\n'
                '        try:\n'
                '            with open(state_path, "r", encoding="utf-8") as f:\n'
                '                data = json.load(f)\n'
                '            return int(data.get("iteracion", data.get("iteration", 0)))\n'
                '        except Exception:\n'
                '            pass\n'
                '    return 0\n'
            )
            txt = re.sub(pattern, new_func, txt, count=1)
            ast.parse(txt, filename=str(idx_file))
            idx_file.write_text(txt, encoding="utf-8")
            print("✅ body/tools/memory_indexer.py: Validado.")

    # 5. Resetear estado a Célula Madre pura
    mem = BODY / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "knowledge.json").write_text(json.dumps({"entries": []}, indent=2), encoding="utf-8")

    state_initial = {
        "identidad": "celula_madre_totipotente",
        "fase": "lista_para_diferenciacion",
        "organo_sensorial": "aprobado",
        "herramienta_busqueda": "tools/web_search.py",
        "herramienta_lectura": "tools/web_reader.py",
        "generador_interfaz": "tools/interface_generator.py",
        "orquestacion_memoria": "activa",
        "gestor_conocimiento": "tools/knowledge_base.py",
        "indexador_memoria": "tools/memory_indexer.py",
        "iteracion": 0,
        "herramientas_activas": [
            "interface_generator.py", "knowledge_base.py", "memory_indexer.py",
            "researcher.py", "self_healing_loop.py", "utils.py", "verify_all.py",
            "web_reader.py", "web_search.py"
        ]
    }
    (mem / "state.json").write_text(json.dumps(state_initial, indent=2, ensure_ascii=False), encoding="utf-8")

    for extra in ("interface.json", "informe_caso.txt", "caso_actual.txt"):
        p = mem / extra
        if p.exists():
            p.unlink()

    res_dir = mem / "research"
    if res_dir.exists():
        shutil.rmtree(res_dir)

    print("✅ Memoria y logs reiniciados a Célula Madre Totipotente (Iteración 0).")


def main():
    print("=" * 72)
    print("🧬 APLICANDO PARCHE MAESTRO CANÓNICO (SIN REGEX FRÁGILES)")
    print("=" * 72)

    try:
        crear_backup()
        aplicar_todo()
        print("\n" + "=" * 72)
        print("✨ SISTEMA 100% SINTÁCTICAMENTE VÁLIDO Y ACTUALIZADO CON ÉXITO")
        print("=" * 72)
        print("\nPuedes diferenciar la célula madre hacia cualquier disciplina con:\n")
        print('  python3 diferenciar.py "<especialidad>" "<misión>"\n')
        return 0
    except Exception as exc:
        print(f"\n❌ Error durante la instalación: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())