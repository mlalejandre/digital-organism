#!/usr/bin/env python3
"""Verify syntax of all Python files in tools/ directory."""
import os
import ast
import sys
from pathlib import Path

def verify_all():
    tools_dir = Path(__file__).resolve().parent
    errors = []
        
    for file in sorted(tools_dir.glob("*.py")):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            print(f"[OK] {file.name}")
        except SyntaxError as e:
            errors.append(f"{file.name}: {e}")
            print(f"[ERROR] {file.name}: {e}")

    if errors:
        print(f"\nTotal errors: {len(errors)}")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("\nAll files syntax verified successfully.")
        return True

if __name__ == '__main__':
    is_clean = verify_all()
    sys.exit(0 if is_clean else 1)