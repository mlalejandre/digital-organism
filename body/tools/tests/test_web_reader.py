# [PARCHE-FIXES-V1:nettest_web_reader]
import os

_RUN_NETWORK_TESTS = os.getenv("RUN_NETWORK_TESTS", "0").strip().lower() not in ("0", "false", "no", "")

import sys
import json
import subprocess

def test():
    if not _RUN_NETWORK_TESTS:
        print("SKIP: prueba de red desactivada por defecto ""(exporta RUN_NETWORK_TESTS=1 para ejecutarla).")
        return True
    # Prueba con un endpoint seguro de Wikipedia
    url = "https://es.wikipedia.org/wiki/Nefrona"
    cmd = [sys.executable, "tools/web_reader.py", url, "1000"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAIL: {res.stderr}")
        return False
    try:
        data = json.loads(res.stdout)
        if data.get("success") and len(data.get("text", "")) > 50:
            print("OK: Lectura profunda de web exitosa.")
            return True
        print("FAIL: Contenido vacío o fallido.")
        return False
    except Exception as e:
        print(f"FAIL: Error JSON: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if test() else 1)
