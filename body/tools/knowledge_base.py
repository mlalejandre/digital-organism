#!/usr/bin/env python3
# [PARCHE-FIXES-V1:knowledge_base_lock]
import sys
import json
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import file_lock  # noqa: E402

KB_PATH = "memory/knowledge.json"

def load_kb():
    if not os.path.exists(KB_PATH):
        return {"entries": []}
    with open(KB_PATH, 'r') as f:
        return json.load(f)

def save_kb(kb):
    with open(KB_PATH, 'w') as f:
        json.dump(kb, f, indent=2)

def main():
    if len(sys.argv) < 2:
        print("Usage: knowledge_base.py <command> [args...]")
        sys.exit(1)

    cmd = sys.argv[1]
    # Todo el ciclo lectura-modificación-escritura ocurre bajo lock para
    # evitar condiciones de carrera si varios procesos tocan knowledge.json.
    lock_ctx = file_lock(KB_PATH) if cmd in ("add", "clear") else None
    if lock_ctx is not None:
        lock_ctx.__enter__()
    kb = load_kb()

    if cmd == "add":
        if len(sys.argv) < 4:
            print("Usage: knowledge_base.py add <key> <value>")
            sys.exit(1)
        key = sys.argv[2]
        value = sys.argv[3]
        for entry in kb["entries"]:
            if entry["key"] == key:
                entry["value"] = value
                save_kb(kb)
                print(f"Updated: {key}")
                return
        kb["entries"].append({"key": key, "value": value})
        save_kb(kb)
        print(f"Stored: {key} = {value}")

    elif cmd == "get":
        if len(sys.argv) < 3:
            print("Usage: knowledge_base.py get <key>")
            sys.exit(1)
        key = sys.argv[2]
        for entry in kb["entries"]:
            if entry["key"] == key:
                print(entry["value"])
                return
        print("Not found")

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: knowledge_base.py search <query>")
            sys.exit(1)
        query = sys.argv[2].lower()
        results = []
        for entry in kb["entries"]:
            if query in entry["key"].lower() or query in entry["value"].lower():
                results.append(f"{entry['key']}: {entry['value']}")
        if results:
            print("\n".join(results))
        else:
            print("No matches")

    elif cmd == "list":
        if not kb["entries"]:
            print("Empty")
        else:
            for entry in kb["entries"]:
                print(f"{entry['key']}: {entry['value']}")

    elif cmd == "clear":
        kb["entries"] = []
        save_kb(kb)
        print("Cleared")

    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    # [PARCHE-FIXES-V1:knowledge_base_lock] liberar el lock adquirido en main(), si aplica.
    try:
        main()
    finally:
        pass  # el lock se libera automáticamente al terminar el proceso
