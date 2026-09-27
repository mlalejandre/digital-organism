from __future__ import annotations

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
