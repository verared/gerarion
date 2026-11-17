"""Marca temporal Geroriana firmada (GST, *Gerarion Signed Timestamp*).

Una hora que no se puede falsificar barato combina tres capas:

    1. Valor canónico  — el instante en formato GUS (convertible, verificable)
    2. Firma           — hash-only en la referencia (post-cuántica por diseño)
    3. Notarización    — inclusión en el log diario del notario (objetividad)

Formato de documento GST (JSON), versión 2:

    {
      "v": 2,
      "ctx": "GUS2-TS",
      "alg": "WOTS16-MERKLE-REF-SHA256",   // interoperable con ML-DSA / SLH-DSA
      "ts":  "2031DY-03-08-T-09:30:00-SC-TCJ+0",
      "ins": 64097688600,                   // instante continuo (segundos)
      "day": 741871,                        // índice de día absoluto
      "sig": {"leaf": ..., "sig": [...], "path": [...]},
      "pub": <hex llave pública del árbol>,
      "anchor": { "day": ..., "index": ..., "proof": [...], "root": ... }
    }

Definición de "imposible de falsificar" que GUS 2.1 sostiene:

    Falsificar una GST válida exige (a) romper la resistencia de preimagen de
    SHA-256, o (b) alterar simultáneamente el log de TODOS los notarios
    independientes que anclaron ese día, sin que ninguna réplica externa
    detecte la divergencia. El coste (a) es 2^256 operaciones; el coste (b)
    crece con el número de réplicas y no se reduce con tiempo ni con dinero.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Optional

from . import adapters as _adapters
from . import calendar as cal
from . import format as fmt
from . import hashots

ALG_REFERENCE = "WOTS16-MERKLE-REF-SHA256"
SPEC_VERSION = 2


@dataclass
class GtsDocument:
    ts: str
    instant: int
    day: int
    alg: str
    pub: str
    sig: dict
    anchor: Optional[dict] = None
    v: int = SPEC_VERSION
    ctx: str = fmt.CANONICAL_CTX

    def to_json(self) -> str:
        data = asdict(self)
        data["ins"] = data.pop("instant")
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, raw: str) -> "GtsDocument":
        data = json.loads(raw)
        return cls(
            ts=data["ts"],
            instant=int(data["ins"]),
            day=int(data["day"]),
            alg=data["alg"],
            pub=data["pub"],
            sig=data["sig"],
            anchor=data.get("anchor"),
            v=int(data.get("v", 2)),
            ctx=data.get("ctx", fmt.CANONICAL_CTX),
        )


def create(raw_or_parsed, signer) -> GtsDocument:
    """Crea una GST a partir de una entrada de tiempo o un ParsedTimestamp.

    `signer` acepta la interfaz de adaptadores (SigningAdapter) o un
    hashots.WotsMerkleSigner (se envuelve automáticamente).
    """
    adapter = _adapters.make_adapter(signer)
    if isinstance(raw_or_parsed, str):
        parsed = fmt.parse(raw_or_parsed)
    else:
        parsed = raw_or_parsed
    canon = fmt.to_canonical(parsed)
    date = cal.from_gerarion(parsed.year, parsed.month, parsed.day)
    instant = cal.instant_from_parts(date.day_index, parsed.hour, parsed.minute, parsed.second)
    message = fmt.canonical_bytes(canon, instant)
    sig = adapter.sign_payload(message)
    return GtsDocument(
        ts=canon,
        instant=instant,
        day=date.day_index,
        alg=adapter.alg,
        pub=adapter.public_key_hex,
        sig=sig,
    )


def verify(doc: GtsDocument) -> dict:
    """Verificación completa: coherencia interna y validez de la firma.

    Devuelve {"ok": bool, "errors": [...], "flags": [...]}.
    """
    errors: list = []
    try:
        parsed = fmt.parse(doc.ts)
    except Exception as exc:  # noqa: BLE001 - superficie de errores del formato
        return {"ok": False, "errors": [f"formato: {exc}"], "flags": []}
    date = cal.from_gerarion(parsed.year, parsed.month, parsed.day)
    instant = cal.instant_from_parts(date.day_index, parsed.hour, parsed.minute, parsed.second)
    if instant != doc.instant:
        errors.append("instante divergente del formato canónico")
    if date.day_index != doc.day:
        errors.append("índice de día divergente del formato canónico")
    if doc.alg != ALG_REFERENCE:
        # Despacho por algoritmo: SLH-DSA (FIPS 205) se verifica vía adaptador;
        # otros esquemas requieren su biblioteca.
        message = fmt.canonical_bytes(doc.ts, doc.instant, doc.ctx)
        if not isinstance(doc.sig, str):
            errors.append("firma de tipo incompatible con el algoritmo")
            return {"ok": False, "errors": errors, "flags": parsed.flags}
        try:
            ok = _adapters.SlhDsaSigner.verify(doc.pub, message, doc.sig, doc.alg)
        except ImportError:
            return {
                "ok": False,
                "errors": [f"algoritmo {doc.alg} requiere el paquete PyPI 'slh-dsa'"],
                "flags": parsed.flags,
            }
        except Exception as exc:  # noqa: BLE001 - llave/firma malformada
            return {"ok": False, "errors": [f"firma inválida: {exc}"], "flags": parsed.flags}
        if not ok:
            errors.append("firma SLH-DSA inválida")
        return {"ok": not errors, "errors": errors, "flags": parsed.flags}
    message = fmt.canonical_bytes(doc.ts, doc.instant, doc.ctx)
    digest = hashots.digest_message(message)
    if not hashots.WotsMerkleSigner.verify(bytes.fromhex(doc.pub), digest, doc.sig):
        errors.append("firma inválida")
    return {"ok": not errors, "errors": errors, "flags": parsed.flags}


def notarize(doc: GtsDocument, notary) -> GtsDocument:
    """Añade el anclaje del notario a una GST firmada.

    La marca entra en la cola del día en curso del notario; tras `seal_day`,
    `notary.inclusion_proof(day, doc.anchor["leaf_index"])` completa el
    anclaje verificable.
    """
    payload = fmt.canonical_bytes(doc.ts, doc.instant, doc.ctx)
    leaf_index = notary.append(payload)
    doc.anchor = {
        "leaf_index": leaf_index,
        "sealed": False,
    }
    return doc


def verify_anchor(doc: GtsDocument, notary) -> dict:
    """Verifica el anclaje de una GST contra el log sellado del notario."""
    from .notary import verify_inclusion

    if not doc.anchor:
        return {"ok": False, "errors": ["sin anclaje de notario"]}
    if not doc.anchor.get("sealed"):
        return {"ok": False, "errors": ["anclaje pendiente de sellado diario"]}
    if "proof" not in doc.anchor or "root" not in doc.anchor:
        return {"ok": False, "errors": ["anclaje incompleto"]}
    payload = fmt.canonical_bytes(doc.ts, doc.instant, doc.ctx)
    leaf = bytes.fromhex(hashlib.sha256(b"\x00" + payload).hexdigest())
    ok = verify_inclusion(
        leaf,
        doc.anchor["proof"],
        doc.anchor.get("leaf_index", 0),
        bytes.fromhex(doc.anchor["root"]),
    )
    return {"ok": ok, "errors": [] if ok else ["la marca no está incluida en la raíz"]}
