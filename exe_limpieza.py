#!/usr/bin/env python3
"""
limpieza.py - Purga segura de archivos temporales, backups viejos y residuos.
No elimina código fuente, ni configuración, ni células activas.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Extensiones y patrones a auditar
PATRONES_TEMPORALES = [
    "*.bak",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
]


def recopilar_candidatos(keep_last_backup: bool = True) -> tuple[list[Path], int]:
    archivos_a_borrar: list[Path] = []

    # 1. Archivos .bak, .DS_Store, .pyc en todo el proyecto
    for patron in PATRONES_TEMPORALES:
        for f in ROOT.rglob(patron):
            # No tocar nada dentro de .git o .venv si existieran
            if any(p in f.parts for p in (".git", ".venv", "venv")):
                continue
            archivos_a_borrar.append(f)

    # 2. Carpetas __pycache__
    for d in ROOT.rglob("__pycache__"):
        if any(p in d.parts for p in (".git", ".venv", "venv")):
            continue
        archivos_a_borrar.append(d)

    # 3. Trazas de razonamiento CoT viejas en experiment/reasoning/
    dir_reasoning = ROOT / "experiment" / "reasoning"
    if dir_reasoning.exists():
        for f in dir_reasoning.glob("*.txt"):
            archivos_a_borrar.append(f)

    # 4. Volcado completo temporal si existe
    dump_completo = ROOT / "proyecto_completo.txt"
    if dump_completo.exists():
        archivos_a_borrar.append(dump_completo)

    # 5. Backups antiguos en experiment/backups/
    dir_backups = ROOT / "experiment" / "backups"
    if dir_backups.exists():
        todos_backups = sorted(
            [f for f in dir_backups.iterdir() if f.is_file() and f.name != ".gitkeep"],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        if keep_last_backup and todos_backups:
            # Conservar el más reciente por seguridad y marcar el resto para borrado
            mas_reciente = todos_backups[0]
            for b in todos_backups[1:]:
                archivos_a_borrar.append(b)
        else:
            archivos_a_borrar.extend(todos_backups)

    # Calcular bytes totales
    total_bytes = 0
    for p in archivos_a_borrar:
        try:
            if p.is_file():
                total_bytes += p.stat().st_size
            elif p.is_dir():
                total_bytes += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        except OSError:
            pass

    return archivos_a_borrar, total_bytes


def formatear_tamano(bytes_cant: int) -> str:
    for unidad in ["B", "KB", "MB", "GB"]:
        if bytes_cant < 1024.0:
            return f"{bytes_cant:.2f} {unidad}"
        bytes_cant /= 1024.0
    return f"{bytes_cant:.2f} TB"


def main():
    parser = argparse.ArgumentParser(description="Limpiador seguro de backups y residuos de Organismo Digital.")
    parser.add_argument("-y", "--yes", action="store_true", help="Confirmar borrado sin preguntar.")
    parser.add_argument("--dry-run", action="store_true", help="Solo listar los archivos que se borrarían.")
    parser.add_argument("--delete-all-backups", action="store_true", help="Borrar absolutamente todos los backups (sin conservar el último).")
    args = parser.parse_args()

    print("=" * 72)
    print("🧹 AUDITORÍA Y LIMPIEZA DEL PROYECTO")
    print("=" * 72)

    keep_last = not args.delete_all_backups
    candidatos, total_bytes = recopilar_candidatos(keep_last_backup=keep_last)

    if not candidatos:
        print("✨ El proyecto ya está completamente limpio. No hay residuos temporales.")
        return 0

    print(f"\nSe encontraron {len(candidatos)} elementos prescindibles:")
    print(f"Espacio total a liberar: {formatear_tamano(total_bytes)}\n")

    # Categorizar para informar
    baks = [f for f in candidatos if f.suffix == ".bak"]
    backups = [f for f in candidatos if "experiment/backups" in f.as_posix()]
    reasoning = [f for f in candidatos if "experiment/reasoning" in f.as_posix()]
    caches = [f for f in candidatos if f.name == "__pycache__" or f.suffix in (".pyc", ".pyo")]
    otros = [f for f in candidatos if f not in baks + backups + reasoning + caches]

    if baks:
        print(f"  • Archivos .bak de parches anteriores: {len(baks)}")
    if backups:
        print(f"  • Archivos comprimidos de backups viejos (.tar.gz): {len(backups)} ({'conservando el último' if keep_last else 'todos'})")
    if reasoning:
        print(f"  • Trazas temporales de razonamiento CoT: {len(reasoning)}")
    if caches:
        print(f"  • Carpetas __pycache__ y bytecode: {len(caches)}")
    if otros:
        print(f"  • Archivos del sistema y volcados (.DS_Store, proyecto_completo.txt): {len(otros)}")

    if args.dry_run:
        print("\n[DRY RUN] Detalle de elementos que se eliminarían:")
        for c in candidatos:
            print(f"   ➜ {c.relative_to(ROOT)}")
        print("\nOperación en modo simulación. No se borró ningún archivo.")
        return 0

    if not args.yes:
        resp = input(f"\n¿Deseas eliminar estos {len(candidatos)} elementos y liberar {formatear_tamano(total_bytes)}? (Escribe 'SI'): ").strip().upper()
        if resp != "SI":
            print("Operación cancelada. No se modificó nada.")
            return 0

    print("\nEliminando elementos...")
    borrados = 0
    for item in candidatos:
        try:
            if item.is_dir():
                shutil.rmtree(item)
            elif item.exists():
                item.unlink()
            borrados += 1
        except Exception as e:
            print(f"  ⚠️ Error al borrar {item.name}: {e}")

    print("\n" + "=" * 72)
    print("✨ LIMPIEZA FINALIZADA CON ÉXITO")
    print("=" * 72)
    print(f"  ➜ Elementos eliminados: {borrados}")
    print(f"  ➜ Espacio recuperado: {formatear_tamano(total_bytes)}")
    print("  ➜ Código fuente, configuración y células activas permanecen intactos.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())