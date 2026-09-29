#!/usr/bin/env python3
"""
scripts/desdiferenciar.py - Inductor de Desdiferenciación a Célula Madre (Factores de Yamanaka).
Archiva el especialista en un .tar.gz y regresa la Célula Madre a la Iteración 0 virginal.
"""

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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
