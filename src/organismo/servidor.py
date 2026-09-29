from __future__ import annotations

import json
import socket
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .motor import OrganismoDigital

ORGANISMO_GLOBAL: OrganismoDigital | None = None
WEB_DIR: Path | None = None


class OrganismoHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/index.html"):
            index_path = WEB_DIR / "index.html"
            if index_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(index_path.read_bytes())
                return

        if parsed.path == "/api/estado":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            if ORGANISMO_GLOBAL:
                datos = ORGANISMO_GLOBAL.obtener_estado_completo()
                self.wfile.write(json.dumps(datos, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/diagnostico":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=diagnostico_organismo.json")
            self.end_headers()
            if ORGANISMO_GLOBAL:
                diag = ORGANISMO_GLOBAL.obtener_diagnostico_completo()
                self.wfile.write(json.dumps(diag, indent=2, ensure_ascii=False).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/prompt":
            if ORGANISMO_GLOBAL and ORGANISMO_GLOBAL.esta_ocupado():
                self.send_response(409)  # 409 Conflict / Busy
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "ocupado",
                    "error": "El organismo está procesando otra directiva biológica. Espera a que vuelva a reposo."
                }).encode("utf-8"))
                return

            l = int(self.headers.get("Content-Length", 0))
            try:
                p = json.loads(self.rfile.read(l).decode("utf-8")).get("prompt", "").strip()
            except Exception:
                p = ""

            if not p:
                self.send_response(400)
                self.end_headers()
                return

            threading.Thread(target=lambda: ORGANISMO_GLOBAL.procesar_prompt(p), daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"status": "procesando"}')
            return

        if parsed.path == "/api/remodelar":
            if ORGANISMO_GLOBAL and ORGANISMO_GLOBAL.esta_ocupado():
                self.send_response(409)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "ocupado",
                    "error": "El organismo está procesando otra directiva. Espera a que vuelva a reposo."
                }).encode("utf-8"))
                return

            threading.Thread(target=lambda: ORGANISMO_GLOBAL.remodelar_anatomia(), daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"status": "remodelando"}')
            return

        if parsed.path == "/api/tabula_rasa":
            if ORGANISMO_GLOBAL and ORGANISMO_GLOBAL.esta_ocupado():
                self.send_response(409)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "ocupado",
                    "error": "El organismo está ocupado. Espera a que vuelva a reposo."
                }).encode("utf-8"))
                return

            threading.Thread(target=lambda: ORGANISMO_GLOBAL.reiniciar_tabula_rasa(), daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"status": "reseteando_tabula_rasa"}')
            return

        if parsed.path == "/api/reset":
            if ORGANISMO_GLOBAL:
                ORGANISMO_GLOBAL._poner_en_reposo()
                ORGANISMO_GLOBAL._safe_release_lock()
                ORGANISMO_GLOBAL.ultimo_resultado = "Organismo Digital en reposo basal."
            self.send_response(200)
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()


def encontrar_puerto_libre(puerto_base: int = 8888) -> int:
    for p in range(puerto_base, puerto_base + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return puerto_base


def iniciar_servidor(organismo: OrganismoDigital, web_dir: Path, puerto: int = 8888) -> int:
    global ORGANISMO_GLOBAL, WEB_DIR
    ORGANISMO_GLOBAL = organismo
    WEB_DIR = web_dir

    p_libre = encontrar_puerto_libre(puerto)
    httpd = ThreadingHTTPServer(("0.0.0.0", p_libre), OrganismoHandler)
    
    print(f"\n🌐 SERVIDOR SEGURO DEL ORGANISMO DIGITAL EN LÍNEA:")
    print(f"   ➜ Abre este enlace: http://localhost:{p_libre}")
    print(f"   ➜ Sandboxing: {'Docker Activo 🛡️' if organismo.executor.docker_available else 'Host Contingente ⚠️'}")
    print(f"   (Presiona Ctrl + C para detener)\n")
    
    import webbrowser
    try:
        webbrowser.open(f"http://localhost:{p_libre}")
    except Exception:
        pass

    httpd.serve_forever()
    return p_libre
