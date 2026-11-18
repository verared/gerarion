# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Adaptadores de algoritmos de firma para GST.

Registro de algoritmos con una interfaz común:

    signer.alg              -> nombre canónico del algoritmo (campo `alg` del GST)
    signer.public_key_hex   -> llave pública serializada
    signer.sign_payload(m)  -> firma serializable como JSON (dict o str)

Algoritmos disponibles:

    WOTS16-MERKLE-REF-SHA256   referencia educativa hash-only (hashots.py),
                               sin dependencias, incluida por defecto.
    SLH-DSA-SHA2-128F          FIPS 205 vía el paquete PyPI `slh-dsa`
                               (implementación pura de referencia del estándar).
    SLH-DSA-SHA2-128S          idem, firma pequeña / firma lenta.
    ML-DSA-44/-65/-87          FIPS 204 vía el paquete PyPI `cryptography`
                               (>= 47, extra `pqc`): adaptador opcional;
                               firma pura con contexto GUS2-TS.

Regla del proyecto: *producción exige bibliotecas auditadas*. El esquema de
referencia WOTS valida la semántica y genera vectores; el despliegue real usa
SLH-DSA o ML-DSA (o LMS/XMSS desplegados con auditoría). El despacho por `alg`
hace que coexistan y sean verificables con el mismo documento GST. La firma
híbrida (Ed25519 + ML-DSA en el mismo documento) queda como objetivo del plan
post-cuántico (docs/spec/threat-model.md §G6); no está implementada
en esta versión.
"""

from __future__ import annotations

import os
from typing import Optional

from . import hashots
from .format import CANONICAL_CTX

# ---------------------------------------------------------------------------
# Interfaz común
# ---------------------------------------------------------------------------


class SigningAdapter:
    alg: str = ""
    public_key_hex: str = ""

    def sign_payload(self, message: bytes):
        raise NotImplementedError


class HashRefSigner(SigningAdapter):
    """Adaptador del firmante hash-only de referencia (hashots.py).

    DEPRECATED para uso real: es una construcción educativa sin auditoría;
    ver `make_adapter`: está deshabilitado por defecto.
    """

    def __init__(self, signer: hashots.WotsMerkleSigner):
        self._signer = signer
        self.alg = "WOTS16-MERKLE-REF-SHA256"
        self.public_key_hex = signer.public_key.hex()

    def sign_payload(self, message: bytes) -> dict:
        return self._signer.sign(hashots.digest_message(message))


class SlhDsaSigner(SigningAdapter):
    """Adaptador SLH-DSA (FIPS 205) vía el paquete PyPI `slh-dsa`.

    Firma en modo "puro" de la especificación final (no el borrador inicial).
    La semilla determinista (digest de 6n bytes) permite reproducir claves en
    tests; en producción, `digest=None` genera claves aleatorias.
    """

    PARAM_ALIASES = {
        "SLH-DSA-SHA2-128F": (128, "f"),
        "SLH-DSA-SHA2-128S": (128, "s"),
    }
    CTX = CANONICAL_CTX.encode("utf-8")

    def __init__(self, param_name: str = "SLH-DSA-SHA2-128F", digest: Optional[bytes] = None):
        if param_name not in self.PARAM_ALIASES:
            raise ValueError(
                f"Parámetro desconocido: {param_name}. Disponibles: {sorted(self.PARAM_ALIASES)}"
            )
        try:
            import slhdsa
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise ImportError(
                "SLH-DSA requiere el paquete PyPI 'slh-dsa' (pip install slh-dsa)"
            ) from exc
        cat, speed = self.PARAM_ALIASES[param_name]
        param = getattr(slhdsa, f"sha2_{cat}{speed}")
        if digest is not None:
            digest_len = 6 * param.n
            if len(digest) != digest_len:
                raise ValueError(f"digest requiere {digest_len} bytes para {param_name}")
            kp = slhdsa.KeyPair.from_digest(digest, param)
        else:
            kp = slhdsa.KeyPair.gen(param)
        self._kp = kp
        self.alg = param_name
        self.public_key_hex = kp.pub.digest().hex()

    def sign_payload(self, message: bytes) -> str:
        sig = self._kp.sign_pure(message, ctx=self.CTX)
        return sig.hex()

    @staticmethod
    def verify(pub_hex: str, message: bytes, signature_hex: str, param_name: str) -> bool:
        try:
            import slhdsa
        except ImportError:  # pragma: no cover
            raise ImportError("verificación SLH-DSA requiere el paquete 'slh-dsa'")
        if param_name not in SlhDsaSigner.PARAM_ALIASES:
            return False
        cat, speed = SlhDsaSigner.PARAM_ALIASES[param_name]
        param = getattr(slhdsa, f"sha2_{cat}{speed}")
        try:
            pub = slhdsa.PublicKey.from_digest(bytes.fromhex(pub_hex), param)
        except Exception:  # noqa: BLE001 - llave malformada = firma inválida
            return False
        try:
            return pub.verify_pure(message, bytes.fromhex(signature_hex), ctx=SlhDsaSigner.CTX)
        except Exception:  # noqa: BLE001 - firma malformada = inválida
            return False


class MlDsaSigner(SigningAdapter):
    """Adaptador ML-DSA (FIPS 204) vía el paquete `cryptography` (>= 47).

    Firma "pura" (pure ML-DSA) con el contexto de dominio canónico GUS2-TS,
    obligatorio tanto al firmar como al verificar. La semilla opcional
    (32 bytes) permite reproducir claves deterministas en tests vía
    `from_seed_bytes`; en producción, `seed=None` genera claves aleatorias.
    """

    PARAM_ALIASES = {
        "ML-DSA-44": "MLDSA44PrivateKey",
        "ML-DSA-65": "MLDSA65PrivateKey",
        "ML-DSA-87": "MLDSA87PrivateKey",
    }
    CTX = CANONICAL_CTX.encode("utf-8")

    def __init__(self, param_name: str = "ML-DSA-65", seed: Optional[bytes] = None):
        if param_name not in self.PARAM_ALIASES:
            raise ValueError(
                f"Parámetro desconocido: {param_name}. Disponibles: {sorted(self.PARAM_ALIASES)}"
            )
        try:
            from cryptography.hazmat.primitives.asymmetric import mldsa
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise ImportError(
                "ML-DSA requiere el paquete 'cryptography' (>= 47): "
                "pip install 'gerarion[pqc]' (o 'pip install cryptography>=47')"
            ) from exc
        self._cls = getattr(mldsa, self.PARAM_ALIASES[param_name])
        self._mldsa = mldsa
        if seed is not None:
            if len(seed) != 32:
                raise ValueError("la semilla ML-DSA requiere exactamente 32 bytes")
            self._kp = self._cls.from_seed_bytes(seed)
        else:
            self._kp = self._cls.generate()
        self.alg = param_name
        self.public_key_hex = self._kp.public_key().public_bytes_raw().hex()

    def sign_payload(self, message: bytes) -> str:
        return self._kp.sign(message, self.CTX).hex()

    @staticmethod
    def verify(pub_hex: str, message: bytes, signature_hex: str, param_name: str) -> bool:
        try:
            from cryptography.hazmat.primitives.asymmetric import mldsa
        except ImportError:  # pragma: no cover
            raise ImportError("verificación ML-DSA requiere el paquete 'cryptography' (>= 47)")
        param = MlDsaSigner.PARAM_ALIASES.get(param_name)
        if param is None:
            return False
        try:
            pub = getattr(mldsa, param.replace("PrivateKey", "PublicKey")).from_public_bytes(
                bytes.fromhex(pub_hex)
            )
        except Exception:  # noqa: BLE001 - llave malformada = firma inválida
            return False
        try:
            pub.verify(bytes.fromhex(signature_hex), message, MlDsaSigner.CTX)
            return True
        except Exception:  # noqa: BLE001 - firma malformada = inválida
            return False


# ---------------------------------------------------------------------------
# Despacho
# ---------------------------------------------------------------------------


def _insecure_ref_allowed(explicit: Optional[bool]) -> bool:
    if explicit is not None:
        return explicit
    return os.environ.get("GUS_ALLOW_INSECURE_REF") == "1"


def make_adapter(signer, *, allow_insecure_ref: Optional[bool] = None) -> SigningAdapter:
    """Envuelve cualquier firmante en la interfaz común.

    El firmante hash-only de referencia (WOTS16-MERKLE-REF-SHA256) está
    DEPRECADO y deshabilitado por defecto: es una construcción educativa sin
    auditoría y NO debe asumirse resistente a un atacante activo; los tests
    del paquete lo habilitan explícitamente (o GUS_ALLOW_INSECURE_REF=1).
    Producción: SLH-DSA (FIPS 205) vía el adaptadorSlhDsaSigner.
    """
    if isinstance(signer, SigningAdapter):
        return signer
    if isinstance(signer, hashots.WotsMerkleSigner):
        if not _insecure_ref_allowed(allow_insecure_ref):
            raise ValueError(
                "GERO_EINSECURE: el firmante hash-only de referencia "
                "(WOTS16-MERKLE-REF-SHA256) está deprecado y deshabilitado por "
                "defecto (solo pruebas/referencia, sin auditoría). Para usarlo "
                "en laboratorio pasa allow_insecure_ref=True o exporta "
                "GUS_ALLOW_INSECURE_REF=1. Producción: SLH-DSA (FIPS 205)."
            )
        return HashRefSigner(signer)
    raise TypeError(f"firmante no soportado: {type(signer).__name__}")
