#!/usr/bin/env python3
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
