#!/usr/bin/env python3
"""
tools/self_healing_loop.py - Bucle de verificación de integridad y autorreparación.
Valida la sintaxis (verify_all.py) y corre todos los tests en tools/tests/.
Agnóstico al directorio desde el que se invoque.
"""
import os
import sys
import subprocess
from pathlib import Path

# Localizar la raíz de 'body' independientemente de dónde se invoque el comando
TOOLS_DIR = Path(__file__).resolve().parent
BODY_DIR = TOOLS_DIR.parent

def run_self_healing():
    print("[HEALING] 1. Verificando sintaxis de todas las herramientas...")
    verify_script = TOOLS_DIR / "verify_all.py"
    
    res_syntax = subprocess.run(
        [sys.executable, str(verify_script)],
        cwd=str(BODY_DIR),
        capture_output=True,
        text=True
    )
    if res_syntax.returncode != 0:
        print("[HEALING] ❌ Error de sintaxis detectado:")
        print(res_syntax.stdout or res_syntax.stderr)
        return 1
    print("[HEALING] ✅ Sintaxis correcta en todos los scripts.")

    print("[HEALING] 2. Ejecutando batería de tests unitarios en tools/tests/...")
    print(f"[HEALING]    # [PARCHE-FIXES-V1:self_healing_note] "
          "(pruebas de red saltadas salvo RUN_NETWORK_TESTS=1)")
    tests_dir = TOOLS_DIR / "tests"
    failed = []
    
    if tests_dir.exists():
        for test_file in sorted(tests_dir.glob("test_*.py")):
            res_test = subprocess.run(
                [sys.executable, str(test_file)],
                cwd=str(BODY_DIR),
                capture_output=True,
                text=True
            )
            if res_test.returncode == 0:
                print(f"  [OK] {test_file.name}")
            else:
                print(f"  [FAIL] {test_file.name}")
                failed.append((test_file.name, res_test.stderr or res_test.stdout))
                
    if failed:
        print(f"\n[HEALING] ⚠️ Fallaron {len(failed)} tests. Requiere corrección:")
        for name, err in failed:
            print(f"--- {name} ---\n{err[:400]}\n")
        return 1
        
    print("\n[HEALING] ✨ Sistema 100% íntegro y verificado.")
    return 0

if __name__ == "__main__":
    sys.exit(run_self_healing())