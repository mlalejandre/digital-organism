from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, Tuple

from config import (
    LLAMA_SERVER_BIN,
    LLM_BASE_URL,
    LLM_MODEL,
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
)
from llm_client import LLMClient


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
    return subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout, check=False)


def is_remote_health_ok() -> bool:
    url = f"http://{SERVER_IP}:{SERVER_PORT_4090}/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status in (200, 204)
    except Exception:
        return False


def start_remote_server_if_needed() -> None:
    if is_remote_health_ok():
        return

    if not SERVER_AUTOSTART:
        raise RuntimeError(f"llama-server no está corriendo en {SERVER_IP}:{SERVER_PORT_4090} y SERVER_AUTOSTART=0")

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
          -np 1 \
          -ctk q8_0 -ctv q8_0 \
          --threads {REMOTE_THREADS} \
          > '{REMOTE_LOG_FILE}' 2>&1 < /dev/null &
        echo $! > '{REMOTE_PID_FILE}'
    """
    res = run_ssh(remote_launch_cmd, timeout=10)
    if res.returncode != 0:
        raise RuntimeError(f"Error al iniciar llama-server remoto: {res.stderr.strip()}")

    deadline = time.time() + SERVER_HEALTH_TIMEOUT_S
    while time.time() < deadline:
        if is_remote_health_ok():
            return
        time.sleep(2)

    raise RuntimeError(f"La RTX 4090 en {SERVER_IP}:{SERVER_PORT_4090} no respondió a tiempo.")


def consultar_gpu_4090(system_prompt: str, user_prompt: str, on_token: Any = None) -> Tuple[str, str, dict]:
    """Envía la inferencia directamente a la RTX 4090 mediante LLMClient."""
    start_remote_server_if_needed()
    client = LLMClient(model_name=LLM_MODEL)
    return client.chat(system_prompt, user_prompt, on_token=on_token)
