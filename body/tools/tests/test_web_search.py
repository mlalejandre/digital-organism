# [PARCHE-FIXES-V1:nettest_web_search]
import os

_RUN_NETWORK_TESTS = os.getenv("RUN_NETWORK_TESTS", "0").strip().lower() not in ("0", "false", "no", "")

import subprocess, json, sys
def test():
    if not _RUN_NETWORK_TESTS:
        print("SKIP: prueba de red desactivada por defecto ""(exporta RUN_NETWORK_TESTS=1 para ejecutarla).")
        return True
    res = subprocess.run([sys.executable, "tools/web_search.py", "creatinina sérica"], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAIL: {res.stderr.strip()}"); return False
    try:
        out = json.loads(res.stdout)
        if out.get("results"):
            print("OK: Búsqueda exitosa y contenido no vacío."); return True
        print("FAIL: Sin resultados."); return False
    except: print("FAIL: JSON inválido."); return False
if __name__ == "__main__":
    sys.exit(0 if test() else 1)