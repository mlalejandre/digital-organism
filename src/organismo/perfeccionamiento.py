from __future__ import annotations

import json
import shutil
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from .anatomia import EstadoBiologico
from .gpu_manager import consultar_gpu_4090


def sanitizar_argumentos_cli(args: Any) -> list[str]:
    """
    Protocolo Universal de CLI para Sandbox:
    Convierte de forma determinista diccionarios o listas en argumentos CLI
    de banderas y valores (--clave valor), preservando números y tipos.
    """
    limpios: list[str] = []
    if isinstance(args, dict):
        for k, v in args.items():
            flag = f"--{str(k).lstrip('-')}"
            limpios.append(flag)
            if isinstance(v, (dict, list)):
                limpios.append(json.dumps(v, ensure_ascii=False))
            elif v is not None:
                limpios.append(str(v).strip())
    elif isinstance(args, list):
        for a in args:
            if isinstance(a, dict):
                for k, v in a.items():
                    limpios.append(f"--{str(k).lstrip('-')}")
                    if isinstance(v, (dict, list)):
                        limpios.append(json.dumps(v, ensure_ascii=False))
                    elif v is not None:
                        limpios.append(str(v).strip())
            elif isinstance(a, list):
                limpios.append(json.dumps(a, ensure_ascii=False))
            elif a is not None:
                limpios.append(str(a).strip())
    elif args is not None:
        limpios.append(str(args).strip())
    return limpios


def asegurar_omnipresencia_celular(cel_dir: Path, tool_file: str) -> None:
    """
    Sustrato Inmune: Garantiza que la herramienta esté presente en todos los
    puntos de vista espaciales de la célula (tools/, tests/ y raíz celular).
    """
    tools_dir = cel_dir / "tools"
    tests_dir = cel_dir / "tests"
    tool_src = tools_dir / tool_file

    if not tool_src.exists():
        return

    destinos = [
        (cel_dir / tool_file, Path("tools") / tool_file),
        (tests_dir / tool_file, Path("..") / "tools" / tool_file),
    ]

    for dest_path, rel_target in destinos:
        try:
            if dest_path.is_symlink() or dest_path.exists():
                dest_path.unlink()
            dest_path.symlink_to(rel_target)
        except (OSError, NotImplementedError, AttributeError):
            try:
                shutil.copy2(tool_src, dest_path)
            except Exception:
                pass


def reparar_json_raw(raw: str, fallback_raw: str = "") -> dict:
    """
    Parser resiliente: busca el JSON en raw y, si está vacío o truncado,
    lo rescata del razonamiento de la GPU (fallback_raw) cerrando llaves abiertas.
    """
    texto = raw.strip() if raw and raw.strip() else (fallback_raw.strip() if fallback_raw else "")
    if not texto:
        raise ValueError("No se encontró texto en la respuesta de la GPU.")

    start = texto.find("{")
    if start == -1:
        if fallback_raw and texto != fallback_raw.strip():
            return reparar_json_raw(fallback_raw)
        raise ValueError("No se encontró bloque JSON en la respuesta de la GPU.")

    end = texto.rfind("}")
    if end == -1 or end < start:
        candidate = texto[start:].strip()
        if candidate.count('"') % 2 != 0:
            candidate += '"'
        open_braces = candidate.count("{") - candidate.count("}")
        open_brackets = candidate.count("[") - candidate.count("]")
        candidate += ("]" * max(0, open_brackets)) + ("}" * max(0, open_braces))
        snippet = candidate
    else:
        snippet = texto[start : end + 1]

    try:
        return json.loads(snippet, strict=False)
    except Exception:
        pass

    try:
        candidate = snippet.replace('\\\\', '\\')
        return json.loads(candidate, strict=False)
    except Exception:
        pass

    if fallback_raw and texto != fallback_raw.strip():
        return reparar_json_raw(fallback_raw)

    raise ValueError("No se pudo reparar el JSON de la GPU.")


def ejecutar_bucle_autoperfeccionamiento(
    celula_nombre: str,
    tool_rel_path: str,
    test_rel_path: str,
    executor: Any,
    args: list,
    error_origen: str,
    log_cb: Callable[[str, str, EstadoBiologico], None] | None = None,
    max_ciclos: int = 4,
    on_token: Any = None,
) -> Tuple[bool, str]:
    """Bucle autónomo de perfeccionamiento ejecutado 100% dentro del sandbox Executor."""
    body_root = executor.body.root
    tool_path = body_root / tool_rel_path
    test_path = body_root / test_rel_path

    if log_cb:
        log_cb(celula_nombre, f"⚠️ Discrepancia: {error_origen[:80]}...", EstadoBiologico.APRENDIENDO)
        log_cb(celula_nombre, "🔄 Activando Bucle Autónomo de Autorreparación en Sandbox...", EstadoBiologico.APRENDIENDO)

    error_actual = error_origen
    args_actuales = sanitizar_argumentos_cli(args)

    for ciclo in range(1, max_ciclos + 1):
        if log_cb:
            log_cb(celula_nombre, f"🔧 Ciclo [{ciclo}/{max_ciclos}]: Consultando RTX 4090 para corregir código...", EstadoBiologico.APRENDIENDO)

        tool_code_actual = tool_path.read_text(encoding="utf-8") if tool_path.exists() else ""
        test_code_actual = test_path.read_text(encoding="utf-8") if test_path.exists() else ""

        system_prompt = (
            "Eres el Sistema Autónomo de Autorreparación y Perfeccionamiento Celular.\n"
            f"La célula '{celula_nombre}' está en perfeccionamiento evolutivo por este error:\n"
            f"ERROR:\n{error_actual}\n\n"
            f"ARGUMENTOS:\n{args_actuales}\n\n"
            f"CÓDIGO HERRAMIENTA ({tool_path.name}):\n{tool_code_actual}\n\n"
            f"CÓDIGO TEST ({test_path.name}):\n{test_code_actual}\n\n"
            "INSTRUCCIONES DE PERFECCIONAMIENTO DETERMINISTA (IEEE 754):\n"
            "1. PARSER SEGURO: Acepta banderas '--clave valor' o argumentos posicionales numéricos. Limpia comas decimales ('1,5' -> 1.5).\n"
            "2. ARIDAD ARBITRARIA: Si se reciben N números (ej. MCD/MCM de 3 valores), procesa todos mediante listas o functools.reduce, jamás limites el cálculo a 2 operandos.\n"
            "3. PIPELINES ENCADENADOS: Si hay operaciones compuestas (descuento e IVA sucesivos), aplica todas las fases en el orden exacto.\n"
            "4. EN EL TEST: Verifica propiedades e invariantes lógicas. NUNCA inventes números esperados de cabeza con assertEqual.\n"
            "5. 'args': Devuelve un diccionario o lista con los argumentos limpios y correctos para ejecutar la herramienta.\n"
            "6. FUNCIONES Y EXPRESIONES DINÁMICAS: Si la herramienta evalúa funciones (integrales, raíces, derivadas), jamás dejes funciones lambda fijas en el código. Haz que acepte la función por parámetro (ej. --func o --expr).\n"
            "7. PRECISIÓN Y DECIMALES: Acepta siempre --decimales o --precision configurables y no redondees prematuramente.\n"
            "8. COHERENCIA DE FACTORES Y PORCENTAJES: Si la directiva pide porcentajes (%), calcula e incluye el valor en % (multiplicado por 100). Si pide factores primos de N números, asegúrate de que la salida incluya tanto la lista de factores primos base únicos como la expresión factorizada.\n\n"
            "Responde ÚNICAMENTE en JSON válido:\n"
            "{\n"
            '  "tool_code": "código corregido",\n'
            '  "test_code": "código test corregido",\n'
            '  "args": {"param1": "valor1", "param2": "valor2"}\n'
            "}"
        )

        try:
            content, _, _ = consultar_gpu_4090(system_prompt, "Repara y perfecciona el código de la célula.", on_token=on_token)
            data = reparar_json_raw(content)

            nuevo_tool = data.get("tool_code", tool_code_actual)
            nuevo_test = data.get("test_code", test_code_actual)
            nuevos_args = sanitizar_argumentos_cli(data.get("args", args_actuales))

            inyector_marker = "# === [ORGANISMO_DIGITAL_PATH_INJECTOR] ==="
            if inyector_marker not in nuevo_test:
                inyector = (
                    f"{inyector_marker}\n"
                    "import sys, os\n"
                    "from pathlib import Path\n"
                    "_cur = Path(__file__).resolve()\n"
                    "_cel_dir = _cur.parent.parent\n"
                    "_tools_dir = str(_cel_dir / 'tools')\n"
                    "_cel_str = str(_cel_dir)\n"
                    "for _p in (_tools_dir, _cel_str):\n"
                    "    if _p not in sys.path:\n"
                    "        sys.path.insert(0, _p)\n"
                    "# =========================================\n\n"
                )
                nuevo_test = inyector + nuevo_test

            if "unittest.main" not in nuevo_test:
                nuevo_test += "\n\nif __name__ == '__main__':\n    import unittest\n    unittest.main()\n"

            tool_path.write_text(nuevo_tool, encoding="utf-8")
            test_path.write_text(nuevo_test, encoding="utf-8")
            asegurar_omnipresencia_celular(tool_path.parent.parent, tool_path.name)

            if log_cb:
                log_cb(celula_nombre, f"🧪 Ciclo [{ciclo}/{max_ciclos}]: Validando tests unitarios en Sandbox...", EstadoBiologico.APRENDIENDO)

            res_test = executor.execute(test_rel_path, [])
            salida_test = (res_test.get("stderr") or "") + " " + (res_test.get("stdout") or "")
            if "Ran 0 tests" in salida_test:
                res_test["success"] = False
                res_test["stderr"] = (res_test.get("stderr") or "") + "\n[BLINDAJE]: El test no ejecutó pruebas (Ran 0 tests). Los métodos deben iniciar con 'test_'."

            if not res_test.get("success", False):
                error_actual = res_test.get("stderr") or res_test.get("stdout") or "Test fallido"
                continue

            if log_cb:
                log_cb(celula_nombre, f"⚙️ Ciclo [{ciclo}/{max_ciclos}]: Tests al 100%. Reintentando cálculo...", EstadoBiologico.APRENDIENDO)

            res_run = executor.execute(tool_rel_path, nuevos_args)
            salida_check = (res_run.get("stdout") or "").strip()
            es_error = not res_run.get("success", False)

            if not es_error:
                try:
                    out_j = json.loads(salida_check)
                    if "error" in out_j:
                        es_error = True
                        error_actual = str(out_j["error"])
                except Exception:
                    pass

            if not es_error and salida_check:
                if log_cb:
                    log_cb(celula_nombre, "✨ Autorreparación completada con éxito en Sandbox.", EstadoBiologico.REPOSO)
                return True, salida_check

            error_actual = res_run.get("stderr") or salida_check or error_actual

        except Exception as exc:
            error_actual = str(exc)

    return False, f"Fallo tras {max_ciclos} ciclos de perfeccionamiento: {error_actual}"
