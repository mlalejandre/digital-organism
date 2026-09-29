#!/usr/bin/env python3
"""
scripts/resetear_organismo.py - Reset del Organismo Digital a Tabula Rasa Inicial.
Purga todas las células diferenciadas, tejidos y órganos, devolviendo
el organismo a su estado de Célula Madre Totipotente virgen.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BODY = ROOT / "body"
ORGANOS = BODY / "organos"
MEMORY = BODY / "memory"
PLANNER = BODY / "planner"
EXPERIMENT = ROOT / "experiment"
BACKUPS = EXPERIMENT / "backups"
TIMESTAMP = dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def crear_backup_previo() -> Path | None:
    """Archiva el cuerpo actual antes del reseteo."""
    try:
        BACKUPS.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUPS / f"organismo_pre_reset_{TIMESTAMP}.tar.gz"
        with tarfile.open(backup_path, "w:gz") as tar:
            if BODY.exists():
                tar.add(BODY, arcname="body")
        print(f"📦 Respaldo de seguridad creado en:\n   ➜ {backup_path.relative_to(ROOT)}")
        return backup_path
    except Exception as e:
        print(f"⚠️ Aviso: No se pudo generar el respaldo: {e}")
        return None


def purgar_organos():
    """Elimina todos los órganos, tejidos y células diferenciadas."""
    total_celulas = 0
    total_tejidos = 0
    total_organos = 0

    if ORGANOS.exists():
        for org in list(ORGANOS.iterdir()):
            if org.is_dir():
                total_organos += 1
                tej_dir = org / "tejidos"
                if tej_dir.exists():
                    for tej in tej_dir.iterdir():
                        if tej.is_dir():
                            total_tejidos += 1
                            cel_dir = tej / "celulas"
                            if cel_dir.exists():
                                for cel in cel_dir.iterdir():
                                    if cel.is_dir():
                                        total_celulas += 1
                shutil.rmtree(org)
    
    ORGANOS.mkdir(parents=True, exist_ok=True)
    print(f"🗑️  Anatomía eliminada: {total_organos} órganos, {total_tejidos} tejidos y {total_celulas} células.")


def resetear_memoria():
    """Restaura los registros de memoria al estado virginal."""
    MEMORY.mkdir(parents=True, exist_ok=True)

    state_initial = {
        "identidad": "celula_madre_totipotente",
        "fase": "tabula_rasa",
        "estado": "reposo",
        "organos_activos": [],
        "iteracion": 0,
        "ultima_modificacion": dt.datetime.now().isoformat(),
    }
    (MEMORY / "state.json").write_text(json.dumps(state_initial, indent=2, ensure_ascii=False), encoding="utf-8")
    (MEMORY / "knowledge.json").write_text(json.dumps({"entries": []}, indent=2), encoding="utf-8")

    for extra in ("interface.json", "informe_caso.txt", "caso_actual.txt"):
        f = MEMORY / extra
        if f.exists():
            f.unlink()

    res_dir = MEMORY / "research"
    if res_dir.exists():
        shutil.rmtree(res_dir)

    print("🧠 Memoria restaurada: state.json y knowledge.json reiniciados a Célula Madre virgen.")


def resetear_planner():
    """Restaura la hoja de ruta primordial del organismo."""
    PLANNER.mkdir(parents=True, exist_ok=True)
    goals = {
        "objetivo_primordial": "Organismo Digital: Morfogénesis Autónoma y Computación Determinista",
        "estado": "tabula_rasa",
        "active_goals": [
            {
                "id": "BIO_001",
                "desc": "Mantener Célula Madre Totipotente lista para recibir directivas",
                "status": "active",
            },
            {
                "id": "BIO_002",
                "desc": "Inducir morfogénesis de órganos y tejidos bajo demanda usando la RTX 4090",
                "status": "standby",
            },
            {
                "id": "BIO_003",
                "desc": "Validar herramientas con tests unitarios deterministas (IEEE 754)",
                "status": "standby",
            },
        ],
    }
    (PLANNER / "goals.json").write_text(json.dumps(goals, indent=2, ensure_ascii=False), encoding="utf-8")
    print("📋 Planner reiniciado con las metas primordiales de morfogénesis.")


def limpiar_logs_experimento():
    """Limpia los logs de telemetría de iteraciones anteriores."""
    logs_dir = EXPERIMENT / "logs"
    reasoning_dir = EXPERIMENT / "reasoning"
    for d in (logs_dir, reasoning_dir):
        if d.exists():
            for f in d.iterdir():
                if f.is_file():
                    f.unlink()
    print("🧹 Logs y trazas de razonamiento de experiment/ limpiados.")


def main():
    parser = argparse.ArgumentParser(description="Resetea el Organismo Digital a Tabula Rasa.")
    parser.add_argument("-f", "--force", action="store_true", help="Resetear sin pedir confirmación.")
    parser.add_argument("--no-backup", action="store_true", help="Omitir la creación del archivo de respaldo.")
    args = parser.parse_args()

    print("=" * 72)
    print("🧬 RESETEO TOTAL DEL ORGANISMO DIGITAL (TABULA RASA)")
    print("=" * 72)

    if not args.force:
        resp = input("⚠️  ¿Seguro que deseas purgar todos los órganos, tejidos y células? (Escribe 'SI'): ").strip().upper()
        if resp != "SI":
            print("Operación cancelada. El organismo permanece intacto.")
            return 0

    print("\nIniciando secuencia de reseteo...\n")

    if not args.no_backup:
        crear_backup_previo()

    purgar_organos()
    resetear_memoria()
    resetear_planner()
    limpiar_logs_experimento()

    print("\n" + "=" * 72)
    print("✨ ORGANISMO RESETEADO AL ESTADO DE INICIO")
    print("   ➜ 0 Órganos")
    print("   ➜ 0 Tejidos")
    print("   ➜ 0 Células diferenciadas")
    print("   ➜ Célula Madre Totipotente lista para empezar de cero.")
    print("=" * 72)
    print("\nPuedes reiniciar el servidor ahora con:")
    print("  python3 servidor.py\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
