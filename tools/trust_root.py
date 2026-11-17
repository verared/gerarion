#!/usr/bin/env python3
"""Trust root del clúster notarial GUS: creación, firma y verificación.

El trust root es el archivo arrancable único desde el que los consumidores
aceptan un quórum: lista de réplicas (nombre, URL, llave pública SLH-DSA),
umbral k, versión GUS y fecha GUS de emisión. Lo firma la clave de ceremonia
(SLH-DSA, FIPS 205). Sin este archivo no hay despliegue; con dos trust roots
divergentes el despliegue está dividido (ver runbook §6).

Uso:
    PYTHONPATH=src python3 tools/trust_root.py create <ceremonia.pem> <out.json>  # interactivo
    PYTHONPATH=src python3 tools/trust_root.py verify <out.json> <pub_hex>
    PYTHONPATH=src python3 tools/trust_root.py keygen <archivo-digest>            # digest 96 bytes p/ 128f

En producción la clave de ceremonia se genera en la ceremonia (RNG del SO) y
su llave pública se graba en dos canales físicos antes de firmar nada. Aquí
`keygen` imprime un digest usable con SlhDsaSigner(digest=...) SOLO para
pruebas de laboratorio.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone

import slhdsa

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gerarion.adapters import SlhDsaSigner  # noqa: E402

SCHEMA = "gus-trust-root-1"


def build_document(replicas: list, threshold: int, gus_version: str,
                   previous_root: str | None = None) -> dict:
    days = os.environ.get("GUS_TRUST_GUS_DAY")  # opcional: día GUS de emisión
    return {
        "schema": SCHEMA,
        "gus_version": gus_version,
        "threshold": threshold,
        "replicas": replicas,
        "previous_trust_root": previous_root,
        "issued_gus_day": days,
        "issued_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "alg": "SLH-DSA-SHA2-128F",
    }


def canonical_for_signing(doc: dict) -> bytes:
    payload = {k: v for k, v in doc.items() if k not in ("signature", "ceremony_pub")}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return blob.encode("utf-8")


def main() -> int:  # noqa: C901 - herramienta CLI con tres subcomandos
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if len(sys.argv) < 3 and cmd != "keygen":
        print(__doc__)
        return 2

    if cmd == "keygen":
        # El digest completo de un par SLH-DSA real ES la clave privada
        # materializada: 96 bytes (pub 32 + sec 64, FIPS 205, SHA2-128f).
        # Un hash arbitrario no sirve: validate_secretkey rechaza un
        # secreto cuyos campos seed/root no son consistentes entre sí.
        kp = slhdsa.KeyPair.gen(slhdsa.sha2_128f)
        print(kp.digest().hex())
        return 0

    if cmd == "create":
        specs_path, out_path, ceremony_digest = sys.argv[2:5]
        with open(specs_path, encoding="utf-8") as fh:
            specs = json.load(fh)
        replicas = [
            {"name": r["name"], "url": r["url"], "pub": r["pub"]} for r in specs["replicas"]
        ]
        signer = SlhDsaSigner("SLH-DSA-SHA2-128F", digest=bytes.fromhex(ceremony_digest))
        doc = build_document(replicas, specs["threshold"], specs["gus_version"],
                             specs.get("previous_trust_root"))
        message = canonical_for_signing(doc)
        doc["signature"] = signer.sign_payload(message)
        doc["ceremony_pub"] = signer.public_key_hex
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        # el trust root firmado se ancla a sí mismo por hash; registrar SHA-256
        print(f"trust root firmada: {out_path}")
        print(f"sha256: {hashlib.sha256(open(out_path, 'rb').read()).hexdigest()}")
        return 0

    if cmd == "verify":
        # Modelo de confianza: la clave de ceremonia se FIJA POR POLÍTICA
        # (canal externo al documento). Verificar con la clave incluida en el
        # propio documento no prova nada (S2). Sin --trust-key / GUS_TRUST_KEY:
        # fallo explícito GERO_ETRUSTKEY.
        import argparse

        vp = argparse.ArgumentParser(prog="trust_root.py verify")
        vp.add_argument("path")
        vp.add_argument("--trust-key", default=None,
                        help="hex de la clave de ceremonia fijada por política")
        va = vp.parse_args(sys.argv[2:])
        trust_hex = va.trust_key or os.environ.get("GUS_TRUST_KEY")
        if not trust_hex:
            print("GERO_ETRUSTKEY: falta la clave de confianza fijada por política "
                  "(--trust-key <pub_hex> o GUS_TRUST_KEY); la clave embebida en el "
                  "documento no es evidencia de confianza",
                  file=sys.stderr)
            return 2
        with open(va.path, encoding="utf-8") as fh:
            doc = json.load(fh)
        embedded = (doc.get("ceremony_pub") or "").strip().lower()
        trust_norm = trust_hex.strip().lower()
        if not hmac.compare_digest(embedded, trust_norm):
            print("GERO_ETRUSTKEY_MISMATCH: la clave embebida en el documento no es "
                  "la clave de confianza fijada por política → documento rechazado",
                  file=sys.stderr)
            return 1
        message = canonical_for_signing(doc)
        ok = SlhDsaSigner.verify(trust_norm, message, doc["signature"], "SLH-DSA-SHA2-128F")
        print("VERIFICADA (contra la clave de confianza de política)" if ok
              else "FALLIDA: firma inválida para la clave de confianza de política")
        return 0 if ok else 1

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
