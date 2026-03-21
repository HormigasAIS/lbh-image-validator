#!/usr/bin/env python3
"""
HormigasAIS Slack Bot — /lbh-check
Recibe comandos Slack y valida imagenes con lbh_sello.py
CLHQ / HormigasAIS 2026
"""

import hashlib, json, os, time, urllib.request, tempfile
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hormiga_slack import hormiga_slack, inicializar
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

SECRET_KEY  = os.environ.get("LBH_SECRET", "hormigasais-soberano-2026")
SLACK_TOKEN = os.environ.get("SLACK_VERIFY_TOKEN", "")
PORT        = 5000
LOG_FILE    = os.path.expanduser("~/hormigasais-lab/logs/guardia_nocturna.log")
VALIDATOR   = os.path.expanduser(
    "~/hormigasais-lab/lbh-image-validator/lbh_sello.py")

def log(msg):
    ts    = time.strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{ts}] LBH {msg}"
    print(linea)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(linea + "\n")

def notificar_webhook(resultado, url, user):
    """Envía resultado al canal #lbh-validations via webhook"""
    import urllib.request, json, os
    webhook = os.environ.get("SLACK_WEBHOOK", "")
    if not webhook:
        return
    icon = "✅" if resultado["estado"] == "VALIDADO" else "⚠️"
    texto = (f"{icon} *{resultado['estado']}* | "
             f"`{url[:50]}` | @{user}")
    try:
        data = json.dumps({"text": texto}).encode()
        req = urllib.request.Request(
            webhook,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        log(f"webhook error: {e}")

def descargar_imagen(url):
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "HormigasAIS-Validator/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(data)
        tmp.close()
        return tmp.name
    except Exception as e:
        log(f"error descarga: {e}")
        return None

def verificar_imagen(ruta):
    manifest_path = ruta + ".manifest.json"
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        return {
            "estado":      "VALIDADO",
            "propietario": manifest.get("propietario", "?"),
            "licencia":    manifest.get("licencia", "?"),
            "version":     manifest.get("version_lbh", "1.1"),
            "hash":        manifest.get("sha256", "")[:16] + "..."
        }
    else:
        with open(ruta, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        return {
            "estado":  "SIN_SELLO",
            "hash":    sha[:16] + "...",
            "mensaje": "Imagen sin sello LBH. Usa lbh_sello.py firmar"
        }

def slack_response(resultado, url):
    if resultado["estado"] == "VALIDADO":
        icon  = "✅"
        texto = (f"*Propietario:* {resultado['propietario']}\n"
                 f"*Licencia:* {resultado['licencia']}\n"
                 f"*Hash:* `{resultado['hash']}`\n"
                 f"*Version LBH:* {resultado['version']}")
    else:
        icon  = "⚠️"
        texto = (f"*Hash:* `{resultado['hash']}`\n"
                 f"*Mensaje:* {resultado.get('mensaje', '')}")

    return json.dumps({
        "response_type": "in_channel",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (f"{icon} *LBH Image Validator*\n"
                             f"URL: `{url[:60]}`\n"
                             f"Estado: *{resultado['estado']}*")
                }
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": texto}
            },
            {
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": ("HormigasAIS · DOI: 10.5281/zenodo.17767205 · "
                             "CLHQ · San Miguel, El Salvador")
                }]
            }
        ]
    })

class SlackHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, json.dumps({
                "status": "ok",
                "node":   "HormigasAIS-Validator",
                "port":   PORT,
                "version": "1.0"
            }))
        else:
            self._respond(404, "not found")

    def do_POST(self):
        if self.path != "/validate":
            self._respond(404, "not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length).decode()
        params = parse_qs(body)

        token  = params.get("token",     [""])[0]
        texto  = params.get("text",      [""])[0].strip()
        user   = params.get("user_name", ["?"])[0]

        log(f"/lbh-check de @{user} url={texto[:40]}")

        if SLACK_TOKEN and token != SLACK_TOKEN:
            self._respond(403, "token invalido")
            return

        # Slack envuelve URLs en <https://...> — limpiar
        texto = texto.strip("<>").split("|")[0]
        if not texto or not texto.startswith("http"):
            self._respond(200, json.dumps({
                "response_type": "ephemeral",
                "text": (
                    "Uso: `/lbh-check https://url-imagen.png`\n"
                    "Ejemplo: `/lbh-check https://ejemplo.com/logo.png`"
                )
            }))
            return

        log(f"descargando imagen: {texto[:40]}")
        ruta = descargar_imagen(texto)

        if not ruta:
            self._respond(200, json.dumps({
                "response_type": "ephemeral",
                "text": "No pude descargar la imagen. Verifica la URL."
            }))
            return

        resultado = verificar_imagen(ruta)
        log(f"resultado: {resultado['estado']}")
        notificar_webhook(resultado, texto, user)

        try:
            os.unlink(ruta)
        except Exception:
            pass

        feromona = hormiga_slack.procesar_validacion(texto, resultado, user)
        if feromona:
            respuesta = hormiga_slack.respuesta_slack(feromona, resultado, texto)
        else:
            respuesta = slack_response(resultado, texto)
        self._respond(200, respuesta, content_type="application/json")

    def _respond(self, code, body, content_type="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        if isinstance(body, str):
            body = body.encode()
        self.wfile.write(body)

def main():
    inicializar()
    log(f"HormigasAIS Slack Bot iniciando en :{PORT}")
    log(f"  POST /validate  — comando /lbh-check")
    log(f"  GET  /health    — estado del nodo")
    log(f"  token: {'configurado' if SLACK_TOKEN else 'sin configurar'}")
    server = HTTPServer(("0.0.0.0", PORT), SlackHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Bot detenido")

if __name__ == "__main__":
    main()
