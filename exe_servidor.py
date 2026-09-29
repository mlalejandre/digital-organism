#!/usr/bin/env python3
"""
servidor.py - Servidor HTTP Oficial del Organismo Digital.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from organismo.motor import OrganismoDigital
from organismo.servidor import iniciar_servidor

def main():
    print("=" * 72)
    print("🧬 INICIANDO SERVIDOR DEL ORGANISMO DIGITAL")
    print("=" * 72)

    organismo = OrganismoDigital(ROOT)
    web_dir = ROOT / "web"

    # Usa el puerto 8888 para no chocar con llama-ui (8080)
    iniciar_servidor(organismo, web_dir, puerto=8888)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
