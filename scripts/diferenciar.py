#!/usr/bin/env python3
"""
scripts/diferenciar.py - Inductor de Diferenciación Terminal (Célula Madre -> Especialista).
Configura el planner, el estado biológico y arranca el bucle evolutivo.
"""

import sys
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
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
        print("Uso: python3 scripts/diferenciar.py <nombre_especialidad> <descripcion_mision>")
        sys.exit(1)
        
    esp = sys.argv[1].strip()
    mis = " ".join(sys.argv[2:]).strip()
    inducir_especializacion(mis, esp)
