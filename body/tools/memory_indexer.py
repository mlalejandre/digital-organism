"""Memory Indexer: Scans the memory directory and creates an index of files with metadata."""
# [PARCHE-FIXES-V1:memory_indexer]
import os
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any


def current_iteration() -> int:
    """Lee la iteración actual desde memory/state.json, compatible tanto con el
    host como dentro del contenedor Docker efímero."""
    state_path = Path(__file__).resolve().parent.parent / "memory" / "state.json"
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return int(data.get("iteracion", data.get("iteration", 0)))
        except Exception:
            pass
    return 0

def index_memory() -> None:
    memory_dir: str = "memory"
    index: Dict[str, Any] = {
        "timestamp": datetime.datetime.now().isoformat(),
        "iteration": current_iteration(),
        "files": []
    }
    
    if not os.path.exists(memory_dir):
        print(f"ERROR: '{memory_dir}' directory not found")
        return

    try:
        for filename in os.listdir(memory_dir):
            filepath: str = os.path.join(memory_dir, filename)
            if os.path.isfile(filepath):
                size: int = os.path.getsize(filepath)
                index["files"].append({
                    "name": filename,
                    "size": size,
                    "path": filepath
                })
    except PermissionError as e:
        print(f"PERMISSION ERROR: {e}")
        return
    
    # Write index
    index_path: str = os.path.join(memory_dir, "index.json")
    try:
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)
        print(f"Indexed {len(index['files'])} files in {memory_dir}/")
        print(json.dumps(index, indent=2))
    except IOError as e:
        print(f"IO ERROR: Could not write index file: {e}")

if __name__ == "__main__":
    index_memory()
