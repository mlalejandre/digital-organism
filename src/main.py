from __future__ import annotations

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
