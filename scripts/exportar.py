import os
from pathlib import Path

def exportar():
    root = Path(__file__).resolve().parent.parent
    output = root / "estado_proyecto.txt"
    ignore = {".git", ".venv", "venv", "__pycache__", "backups", "snapshots"}
    
    lines = ["=" * 60, f"ÁRBOL DEL PROYECTO: {root}", "=" * 60]
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore]
        rel = os.path.relpath(dirpath, root)
        lvl = 0 if rel == "." else rel.count(os.sep) + 1
        indent = "    " * lvl
        lines.append(f"{indent}📁 {os.path.basename(dirpath)}/")
        for f in sorted(filenames):
            if f not in ignore and not f.endswith(".tar.gz"):
                lines.append(f"{indent}    📄 {f}")
                
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Estado exportado en: {output}")

if __name__ == "__main__":
    exportar()
