#!/usr/bin/env python3
"""
aprendizaje/entrenador_adversarial.py - Entrenador Inmunitario Autónomo del Organismo Digital.

Ciclo cerrado de auto-aprendizaje:
1. Ejecuta auditorías adversariales para detectar debilidades.
2. Si un reto falla, lo inyecta como un estímulo de corrección guiada al organismo.
3. El organismo activa su bucle de auto-perfeccionamiento en Docker y auto-repara la célula.
4. Repite hasta alcanzar 0.0% de fragilidad de forma 100% autónoma.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

API_BASE = "http://localhost:8888/api"
ROOT = Path(__file__).resolve().parent.parent


def peticion_post(endpoint: str, data: dict | None = None) -> tuple[int, dict]:
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data or {}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except Exception as e:
        return 0, {"error": str(e)}


def esperar_reposo(timeout_s: int = 300) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{API_BASE}/estado", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("organismo_estado") == "reposo":
                    return True
                if data.get("organismo_estado") == "fallo":
                    return False
        except Exception:
            pass
        time.sleep(2)
    return False


def ejecutar_auditoria() -> tuple[list[dict], Path | None]:
    cmd = [sys.executable, str(ROOT / "aprendizaje" / "auditor_matematico.py"), "--muestras", "1"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)

    dir_auditoria = ROOT / "logs" / "auditoria"
    if not dir_auditoria.exists():
        return [], None

    jsonl_files = sorted(dir_auditoria.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not jsonl_files:
        return [], None

    fallos = []
    with jsonl_files[0].open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                if not item.get("ok", False):
                    fallos.append(item)

    return fallos, jsonl_files[0]


def inmunizar_fallo(fallo: dict):
    prompt_original = fallo.get("prompt", "")
    tema = fallo.get("tema", "")
    faltantes = fallo.get("faltantes", [])

    print(f"\n💉 INYECTANDO ANTÍGENO DE ENTRENAMIENTO: '{tema}'")
    print(f"   Directiva: \"{prompt_original[:80]}...\"")
    print(f"   Valores que faltaron: {faltantes}")

    # Estímulo de auto-corrección metacognitiva
    estimulo = (
        f"{prompt_original}\n\n"
        f"[CONTROL DE CALIDAD DETERMINISTA]: En la evaluación previa, la célula ejecutada falló porque "
        f"faltaron los valores: {faltantes}. Asegura que la herramienta admita parámetros dinámicos, "
        f"no contenga funciones matemáticas fijas en código duro y respete la precisión solicitada."
    )

    esperar_reposo(20)
    peticion_post("reset")
    time.sleep(2)

    status, _ = peticion_post("prompt", {"prompt": estimulo})
    if status == 200:
        print("   ⏳ Organismo procesando y auto-perfeccionando célula en Docker...")
        if esperar_reposo(360):
            print("   ✨ Ciclo de auto-reparación completado.")
        else:
            print("   ⚠️ Tiempo de espera excedido en ciclo de auto-reparación.")
    else:
        print(f"   ⚠️ Error HTTP {status} al inyectar estímulo.")


def entrenar(max_rondas: int = 3):
    print("=" * 72)
    print("🧬 ENTRENADOR ADVERSARIAL INMUNITARIO DEL ORGANISMO DIGITAL")
    print("=" * 72)

    for ronda in range(1, max_rondas + 1):
        print(f"\n⚔️  RONDA [{ronda}/{max_rondas}]: Ejecutando auditoría de estrés...")
        fallos, _ = ejecutar_auditoria()

        if not fallos:
            print("\n🎉 ¡ORGANISMO 100% INMUNE! 0.0% de fragilidad alcanzado de forma autónoma.")
            return

        print(f"\n⚠️ Se detectaron {len(fallos)} fallos de fragilidad. Iniciando inmunización autónoma...")
        for f in fallos:
            inmunizar_fallo(f)

        print("\n🧹 Disparando Homeostasis Tisular con Memoria Inmunológica...")
        peticion_post("remodelar")
        esperar_reposo(200)

    print("\n🏁 Entrenamiento finalizado. Ejecuta una auditoría final para verificar el estado.")


if __name__ == "__main__":
    entrenar()
