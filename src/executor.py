from __future__ import annotations

import os
import shutil
import subprocess
import sys
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
    """Ejecutor Universal Multi-Lenguaje con Aislamiento en Docker y Sandboxing.
    Garantiza contención de rutas dentro de /body tanto para tools/ como para organos/.
    """

    def __init__(self, body: Body, require_docker: bool = False):
        self.body = body
        self.require_docker = require_docker
        self.docker_available = self._comprobar_docker()

    def _comprobar_docker(self) -> bool:
        if not shutil.which("docker"):
            return False
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=False,
            )
            return res.returncode == 0
        except Exception:
            return False

    def execute(self, path: str, args: list[str]) -> dict[str, Any]:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("path must be a non-empty string")

        clean_args = list(args) if isinstance(args, list) else []
        if not all(isinstance(x, str) for x in clean_args):
            raise TypeError("args must be a list of strings")

        norm_path = path.strip().lower()

        # Evaluación inline directa
        if norm_path in ("python", "python3", "bash", "sh", "/bin/bash", "/bin/sh", "/usr/bin/python"):
            if clean_args and clean_args[0] == "-c":
                inline_interpreter = "python3" if "python" in norm_path else "bash"
                code_str = clean_args[1] if len(clean_args) > 1 else ""
                return self._run_inline(inline_interpreter, code_str)
            elif clean_args:
                path = clean_args.pop(0)
            else:
                raise ValueError(f"Se especificó '{norm_path}' como ruta pero args está vacío.")

        path = path.lstrip("/")
        target = self.body.safe_path(path)
        if not target.exists() or target.is_dir():
            raise FileNotFoundError(f"Archivo no encontrado en body: {path}")

        try:
            target.chmod(target.stat().st_mode | 0o755)
        except Exception:
            pass

        rel_target = target.relative_to(self.body.root).as_posix()
        container_target = f"/body/{rel_target}"

        # Detección de intérprete por shebang o extensión
        shebang_interpreter = self._detectar_shebang(target)
        exec_prefix: list[str] = []
        suffix = target.suffix.lower()

        if shebang_interpreter:
            parts = shebang_interpreter.split()
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

        # 1. EJECUCIÓN EN DOCKER (SANDBOX PRINCIPAL)
        if self.docker_available:
            # Directorio de trabajo dentro del contenedor: el directorio del script
            container_workdir = f"/body/{Path(rel_target).parent.as_posix()}"
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
                "-w", container_workdir,
                "-e", f"PYTHONPATH=/body:/body/tools:{container_workdir}:{Path(container_workdir).parent.as_posix()}:{Path(container_workdir).parent.as_posix()}/tools",
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
                return {
                    "success": completed.returncode == 0,
                    "action": "EXECUTE",
                    "sandbox": "docker",
                    "path": path,
                    "returncode": completed.returncode,
                    "stdout": self._tail(completed.stdout),
                    "stderr": self._tail(completed.stderr),
                }
            except subprocess.TimeoutExpired as exc:
                return {
                    "success": False,
                    "action": "EXECUTE",
                    "sandbox": "docker",
                    "error": "TimeoutExpired",
                    "stdout": self._tail(exc.stdout),
                    "stderr": self._tail(exc.stderr),
                }
            except Exception as exc:
                return {
                    "success": False,
                    "action": "EXECUTE",
                    "sandbox": "docker",
                    "error": type(exc).__name__,
                    "message": str(exc),
                }

        # 2. CONTINGENCIA SEGURA (SI DOCKER ESTÁ APAGADO EN DEV)
        if self.require_docker:
            raise RuntimeError("Docker sandbox es estrictamente requerido pero el daemon no está activo.")

        env = os.environ.copy()
        script_dir = str(target.parent)
        env["PYTHONPATH"] = script_dir + (os.pathsep + env.get("PYTHONPATH", "") if "PYTHONPATH" in env else "")

        cmd_local = (exec_prefix or [sys.executable]) + [str(target), *clean_args]
        try:
            completed = subprocess.run(
                cmd_local,
                cwd=script_dir,
                capture_output=True,
                text=True,
                timeout=EXEC_TIMEOUT_S,
                env=env,
            )
            return {
                "success": completed.returncode == 0,
                "action": "EXECUTE",
                "sandbox": "host_fallback",
                "path": path,
                "returncode": completed.returncode,
                "stdout": self._tail(completed.stdout),
                "stderr": self._tail(completed.stderr),
            }
        except Exception as exc:
            return {
                "success": False,
                "action": "EXECUTE",
                "sandbox": "host_fallback",
                "error": type(exc).__name__,
                "message": str(exc),
            }

    def _run_inline(self, interpreter: str, code_str: str) -> dict[str, Any]:
        if self.docker_available:
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
                interpreter, "-c", code_str
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
                    "path": f"{interpreter} -c",
                    "sandbox": "docker",
                    "returncode": completed.returncode,
                    "stdout": self._tail(completed.stdout),
                    "stderr": self._tail(completed.stderr),
                }
            except Exception as exc:
                return {"success": False, "action": "EXECUTE", "error": str(exc)}
        else:
            completed = subprocess.run(
                [sys.executable if interpreter == "python3" else "bash", "-c", code_str],
                cwd=str(self.body.root),
                capture_output=True,
                text=True,
                timeout=EXEC_TIMEOUT_S,
            )
            return {
                "success": completed.returncode == 0,
                "action": "EXECUTE",
                "path": f"{interpreter} -c",
                "sandbox": "host_fallback",
                "returncode": completed.returncode,
                "stdout": self._tail(completed.stdout),
                "stderr": self._tail(completed.stderr),
            }

    def _detectar_shebang(self, target: Path) -> str | None:
        try:
            with target.open("r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline().strip()
                if first_line.startswith("#!"):
                    return first_line[2:].strip()
        except Exception:
            pass
        return None

    @staticmethod
    def _tail(value: Any, limit: int = EXEC_OUTPUT_TAIL_CHARS) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        return str(value)[-limit:]
