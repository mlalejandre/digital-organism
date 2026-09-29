from __future__ import annotations

import datetime as dt
import json
import shutil
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from .anatomia import Celula, EstadoBiologico
from .gpu_manager import consultar_gpu_4090
from .perfeccionamiento import (
    asegurar_omnipresencia_celular,
    ejecutar_bucle_autoperfeccionamiento,
    reparar_json_raw,
    sanitizar_argumentos_cli,
)


class CelulaMadreTotipotente:
    def __init__(self, root_dir: Path):
        self.root = root_dir
        self.estado = EstadoBiologico.REPOSO

    def _investigar_ground_truth(
        self,
        especialidad: str,
        nombre: str,
        prompt: str
    ) -> Tuple[str, List[str]]:
        try:
            import sys
            tools_dir = str(self.root / "body" / "tools")
            if tools_dir not in sys.path:
                sys.path.insert(0, tools_dir)
            import researcher

            consulta = f"{nombre} {especialidad} formula coefficients consensus"
            consulta = re.sub(r"[\r\n]+", " ", consulta).strip()[:100]

            resultados = researcher.quick_search(consulta)
            if not resultados and prompt:
                palabras_clave = [p for p in prompt.split() if len(p) > 3][:6]
                consulta_alt = f"{especialidad} {' '.join(palabras_clave)} formula"
                resultados = researcher.quick_search(consulta_alt[:100])

            if not resultados:
                return "", []

            lineas = []
            fuentes = []
            for idx, r in enumerate(resultados[:4], 1):
                url = r.get("url", "")
                titulo = r.get("title", "Fuente")
                snippet = r.get("snippet", "")
                if url:
                    fuentes.append(url)
                lineas.append(f"[{idx}] {titulo}\n    URL: {url}\n    Extracto: {snippet[:350]}")

            return "\n\n".join(lineas), fuentes
        except Exception:
            return "", []

    def sintetizar_herramienta_y_diferenciar(
        self,
        info: Dict[str, str],
        prompt: str,
        executor: Any,
        log_cb: Callable[[str, str, EstadoBiologico], None] | None = None,
        on_token: Any = None
    ) -> Tuple[Celula, str, list]:
        self.estado = EstadoBiologico.APRENDIENDO

        if log_cb:
            log_cb("Célula Madre", f"🌐 Investigando literatura y calibración para '{info['celula_nombre']}'...", EstadoBiologico.APRENDIENDO)

        evidencias_web, fuentes_urls = self._investigar_ground_truth(
            especialidad=info["celula_especialidad"],
            nombre=info["celula_nombre"],
            prompt=prompt
        )

        if log_cb:
            log_cb("Célula Madre", f"📚 Síntesis en RTX 4090 para '{info['celula_nombre']}'...", EstadoBiologico.APRENDIENDO)

        system_prompt = (
            "Eres la Célula Madre Totipotente de un Organismo Digital Pluricelular.\n"
            f"Debes engendrar una nueva CÉLULA ESPECIALIZADA para el tejido '{info['tejido_nombre']}' dentro de '{info['organo_nombre']}'.\n\n"
            "PRINCIPIOS COGNITIVOS Y DE VERDAD DETERMINISTA (OBLIGATORIOS):\n"
            "1. SOBERANÍA DE LA DIRECTIVA: Tu código DEBE resolver con exactitud la tarea descrita en la directiva del usuario, "
            "   independientemente del dominio (medicina, finanzas, matemáticas, ingeniería, lingüística, etc.).\n"
            "2. IDENTIDAD Y ESPECIALIDAD AUTÓNOMAS: Define un nombre científico ('celula_nombre') y especialidad ('celula_especialidad') "
            "   fieles a la capacidad concreta que estás programando (ej. 'Multiplicador Aritmético', 'Calculadora CKD-EPI', 'Validador de Sintaxis').\n"
            "3. ARIDAD Y PIPELINES UNIVERSALES: Si la tarea involucra colecciones o pasos sucesivos, implementa la secuencia completa sin truncar operandos.\n"
                        "4. PROHIBIDO HARDCODEAR EXPRESIONES MATEMÁTICAS: Si la tarea evalúa, integra o deriva funciones (ej. Simpson, Taylor, Newton-Raphson), la función o expresión DEBE recibirse dinámicamente como argumento CLI (ej. --func o --expr evaluada de forma segura), NUNCA fijada como lambda fija en el código.\n"
            "5. PRECISIÓN Y DECIMALES VARIABLES: Toda herramienta analítica o numérica DEBE aceptar el argumento --decimales o --precision (por defecto 4, pero ampliable a 8, 12, etc.). No trunques en pasos intermedios; calcula con precisión completa IEEE 754.\n"
            "6. PARSER CLI UNIVERSAL Y TOLERANTE: Prohibido asumir que sys.argv[1] es un JSON crudo. Implementa argparse o lectura de banderas (--clave valor) y posicionales, limpiando comas decimales europeas (\'1,5\' -> 1.5).\n"
"4. PRIMACÍA DEL RUNTIME (IEEE 754): Python determinista en sandbox. La herramienta debe leer argumentos e imprimir un JSON por stdout con if __name__ == '__main__':\n"
            "5. TESTS POR INVARIANTES: En 'test_code' usa unittest para verificar propiedades lógicas y límites. Nunca adivines números de cabeza.\n"
            "6. ARGUMENTOS: Extrae en 'args' los parámetros de la directiva en un diccionario semántico.\n\n"
            "Responde ÚNICAMENTE en JSON:\n"
            "{\n"
            '  "celula_nombre": "Nombre descriptivo de la nueva célula",\n'
            '  "celula_especialidad": "Descripción de la capacidad que domina",\n'
            '  "tool_file": "nombre_herramienta.py",\n'
            '  "tool_code": "código completo en python con main",\n'
            '  "test_file": "test_nombre_herramienta.py",\n'
            '  "test_code": "código test unittest",\n'
            '  "args": {"param1": "valor1", "param2": "valor2"}\n'
            "}"
        )

        user_prompt = f"Directiva:\n{prompt}"
        if evidencias_web:
            user_prompt += (
                "\n\n============================================================\n"
                "EVIDENCIA CIENTÍFICA Y CONSENSO PÚBLICO (GROUND TRUTH):\n"
                "============================================================\n"
                f"{evidencias_web}\n"
            )

        content, reasoning, usage = consultar_gpu_4090(system_prompt, user_prompt, on_token=on_token)

        if log_cb:
            log_cb("RTX 4090", f"Inferencia completada ({usage.get('total_tokens', len(content.split()))} tokens). Verificando madurez...", EstadoBiologico.APRENDIENDO)

        data = reparar_json_raw(content, fallback_raw=reasoning if 'reasoning' in locals() else '')

        nombre_celula = str(data.get("celula_nombre") or info.get("celula_nombre") or "Célula Especializada").strip()
        especialidad_celula = str(data.get("celula_especialidad") or info.get("celula_especialidad") or prompt[:50]).strip()
        tool_file = data.get("tool_file", "tool.py")
        if not tool_file.endswith(".py"): tool_file += ".py"
        test_file = f"test_{tool_file}"
        tool_code = data.get("tool_code", "")
        test_code = data.get("test_code", "")
        args = sanitizar_argumentos_cli(data.get("args", []))

        if not tool_code:
            raise ValueError("La GPU no generó el código de la herramienta ('tool_code').")

        inyector_marker = "# === [ORGANISMO_DIGITAL_PATH_INJECTOR] ==="
        if inyector_marker not in test_code:
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
            test_code = inyector + test_code

        if "unittest.main" not in test_code:
            test_code += "\n\nif __name__ == '__main__':\n    import unittest\n    unittest.main()\n"

        rel_cel = Path("organos") / info["organo_id"] / "tejidos" / info["tejido_id"] / "celulas" / info["celula_id"]
        cel_dir = self.root / "body" / rel_cel
        tools_dir = cel_dir / "tools"
        tests_dir = cel_dir / "tests"

        tools_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)

        tool_path = tools_dir / tool_file
        test_path = tests_dir / test_file

        tool_path.write_text(tool_code, encoding="utf-8")
        test_path.write_text(test_code, encoding="utf-8")
        asegurar_omnipresencia_celular(cel_dir, tool_file)

        meta_cel = {
            "id": info["celula_id"],
            "nombre": nombre_celula,
            "especialidad": especialidad_celula,
            "herramientas": [tool_file],
            "fuentes_consenso": fuentes_urls,
            "calibracion_web": bool(fuentes_urls),
            "creado": dt.datetime.now().isoformat(),
        }
        (cel_dir / "meta.json").write_text(json.dumps(meta_cel, indent=2, ensure_ascii=False), encoding="utf-8")

        rel_tool = (rel_cel / "tools" / tool_file).as_posix()
        rel_test = (rel_cel / "tests" / test_file).as_posix()

        res_test = executor.execute(rel_test, [])
        salida_test = (res_test.get("stderr") or "") + " " + (res_test.get("stdout") or "")
        if "Ran 0 tests" in salida_test:
            res_test["success"] = False
            res_test["stderr"] = (res_test.get("stderr") or "") + "\n[BLINDAJE]: El test no ejecutó pruebas (Ran 0 tests). Los métodos deben iniciar con 'test_'."

        if not res_test.get("success", False):
            ok, msg = ejecutar_bucle_autoperfeccionamiento(
                celula_nombre=info["celula_nombre"],
                tool_rel_path=rel_tool,
                test_rel_path=rel_test,
                executor=executor,
                args=args,
                error_origen=res_test.get("stderr") or res_test.get("stdout") or "Test inicial fallido",
                log_cb=log_cb,
            )
            if not ok:
                self.estado = EstadoBiologico.FALLO
                raise RuntimeError(msg)

        self.estado = EstadoBiologico.REPOSO

        celula = Celula(
            id=info["celula_id"],
            nombre=nombre_celula,
            especialidad=especialidad_celula,
            estado=EstadoBiologico.REPOSO,
            herramientas=[tool_file],
            descripcion=info["celula_especialidad"],
            ruta_dir=str(cel_dir.relative_to(self.root)),
        )

        return celula, tool_file, args
