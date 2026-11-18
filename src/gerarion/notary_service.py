# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Servicio HTTP del notario diario GUS (réplica) — stdlib puro.

Una réplica de producción del notario multi-réplica (src/gerarion/
notary_cluster.py) puesta de pie sobre http.server, sin dependencias.

Endpoints:

    GET  /health                 estado de la réplica y día GUS actual
    POST /receive                {"payload_hex": ".."} -> {"leaf_index": n}
    POST /seal                   {"day": n} -> publicación de la réplica
    GET  /publications           todas las raíces publicadas
    GET  /export                 log completo (JSON del DayNotary)
    GET  /proof?day=n&leaf=i     prueba de inclusión Merkle

Configuración por variables de entorno:

    GUS_NOTARY_NAME    nombre de la réplica (obligatorio)
    GUS_NOTARY_STATE   ruta del archivo de estado persistente
    GUS_NOTARY_PORT    puerto de escucha (por defecto 8080)
    GUS_NOTARY_BIND    interfaz (por defecto 127.0.0.1)

Seguridad operacional: el servicio es un nodo interno. En producción debe
ir detrás de TLS (reverse proxy), con autenticación de quien empuja marcas
y monitoreo de divergencias entre réplicas (ver docs/notary-runbook.md).
"""

from __future__ import annotations

import datetime
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gerarion import calendar as cal  # noqa: E402
from gerarion import notary as nty  # noqa: E402
from gerarion import notary_cluster as ncl  # noqa: E402

STATE = os.environ.get("GUS_NOTARY_STATE", "")
REPLICA = os.environ.get("GUS_NOTARY_NAME", "replica-local")


def current_day_index() -> int:
    """Día GUS actual (medianoche prevaleciente) desde el reloj UTC del host."""
    today = datetime.datetime.now(datetime.timezone.utc).date()
    return cal.day_index_from_gregorian(today.year, today.month, today.day)


class NotaryState:
    """Estado persistente en un único archivo JSON."""

    def __init__(self, path: str):
        self.path = path
        self.notary = nty.DayNotary()
        self.current_day = current_day_index()
        if path and os.path.exists(path):
            self.load()

    def load(self) -> None:
        with open(self.path, encoding="utf-8") as fh:
            data = json.load(fh)
        self.notary = nty.DayNotary.import_json(json.dumps(data))
        self.current_day = data.get("current_day", current_day_index())

    def save(self) -> None:
        if not self.path:
            return
        tmp = self.path + ".tmp"
        data = json.loads(self.notary.export())
        data["current_day"] = self.current_day
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, self.path)


STATE_OBJ: NotaryState | None = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # noqa: A002 - firma del stdlib
        sys.stderr.write("[%s] %s\n" % (REPLICA, fmt % args))

    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - API del stdlib
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/health":
            self._send(200, {
                "ok": True,
                "replica": REPLICA,
                "current_day": STATE_OBJ.current_day,
                "pending": STATE_OBJ.notary.pending_count,
                "previous_root": STATE_OBJ.notary.previous_root.hex()
                if STATE_OBJ.notary.previous_root else "",
                "chain_head_valid": STATE_OBJ.notary.verify_chain(),
            })
        elif parsed.path == "/publications":
            replica = ncl.NotaryReplica(REPLICA)
            replica.notary = STATE_OBJ.notary
            self._send(200, {"publications": replica.publish_history()})
        elif parsed.path == "/export":
            body = STATE_OBJ.notary.export().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == "/proof":
            day = int(qs.get("day", ["-1"])[0])
            leaf = int(qs.get("leaf", ["-1"])[0])
            try:
                proof = STATE_OBJ.notary.inclusion_proof(day, leaf)
            except KeyError as exc:
                self._send(404, {"ok": False, "error": str(exc)})
                return
            self._send(200, {"ok": True, **proof})
        else:
            self._send(404, {"ok": False, "error": "endpoint desconocido"})

    def do_POST(self):  # noqa: N802 - API del stdlib
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, {"ok": False, "error": "JSON inválido"})
            return

        if parsed.path == "/receive":
            payload_hex = data.get("payload_hex", "")
            try:
                payload = bytes.fromhex(payload_hex)
            except ValueError:
                self._send(400, {"ok": False, "error": "payload_hex inválido"})
                return
            index = STATE_OBJ.notary.append(payload)
            STATE_OBJ.save()
            self._send(200, {"ok": True, "leaf_index": index,
                             "current_day": STATE_OBJ.current_day})
        elif parsed.path == "/seal":
            day = int(data.get("day", STATE_OBJ.current_day))
            try:
                rec = STATE_OBJ.notary.seal_day(day)
            except ValueError as exc:
                self._send(409, {"ok": False, "error": str(exc)})
                return
            STATE_OBJ.save()
            self._send(200, {
                "ok": True,
                "publication": ncl.ReplicaPublication(
                    replica=REPLICA, day=day, tree_root=rec["tree_root"],
                    prev_root=rec["prev_root"], day_root=rec["day_root"],
                ).to_dict(),
            })
        else:
            self._send(404, {"ok": False, "error": "endpoint desconocido"})


def main() -> None:
    global STATE_OBJ
    STATE_OBJ = NotaryState(STATE)
    port = int(os.environ.get("GUS_NOTARY_PORT", "8080"))
    bind = os.environ.get("GUS_NOTARY_BIND", "127.0.0.1")
    server = ThreadingHTTPServer((bind, port), Handler)
    print(f"notario GUS {REPLICA} escuchando en {bind}:{port} "
          f"(día actual {STATE_OBJ.current_day})", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
