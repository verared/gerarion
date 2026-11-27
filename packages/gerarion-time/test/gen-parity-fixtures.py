# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Genera recibos GST v2 reales (firmados por gerarion) para paridad JS.

Requiere el paquete `gerarion` importable (rama v3.3.0+ con gst.v2 y
`cryptography>=47` para ML-DSA). Salida: un único JSON en stdout con las
3 variantes híbridas (ML-DSA-44/65/87): sobre firmado, message_hex
(domino || JCS) y claves públicas.
"""
import json
import sys

from gerarion.gst.adapters import Ed25519Signer, HybridSigner, MlDsaSigner  # noqa: E402
from gerarion.gst.envelope import GST_V2_DOMAIN, create_v2  # noqa: E402
from gerarion.gst.jcs import dumps_bytes  # noqa: E402

STAMP = "2031DY-03-08-T-09:30:00-SC-TCJ+0"
EVENT_HASH = "sha256:" + "ab" * 32


def main() -> None:
    variants = {}
    for param in ("ML-DSA-44", "ML-DSA-65", "ML-DSA-87"):
        signer = HybridSigner(
            classical=Ed25519Signer(b"E" * 32),
            pqc=MlDsaSigner(param, seed=b"S" * 32),
        )
        env = create_v2(
            STAMP,
            signer,
            event_hash=EVENT_HASH,
            kid="k1",
            issuer="gerarion-parity-test",
            seq=0,
        )
        payload = {k: v for k, v in env.items() if k != "sigs"}
        variants[param] = {
            "envelope": env,
            "message_hex": (GST_V2_DOMAIN + dumps_bytes(payload)).hex(),
            "pqc_alg": signer.alg,
            "ed_pub_hex": signer.public_key_hex,
            "pqc_pub_hex": signer.public_key_pqc_hex,
            "issuer": "gerarion-parity-test",
        }
    print(json.dumps({"stamp": STAMP, "event_hash": EVENT_HASH, "variants": variants}))


if __name__ == "__main__":
    main()
