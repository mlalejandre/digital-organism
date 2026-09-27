from __future__ import annotations

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
