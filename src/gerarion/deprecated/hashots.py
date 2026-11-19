# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Firma hash pura de referencia (Winternitz OTS + árbol Merkle, SHA-256).

ADVERTENCIA DE ALCANCE: es una *implementación de referencia educativa*,
**SOLO para pruebas y generación de vectores**; la producción usa SLH-DSA
(FIPS 205) u otro esquema normalizado con biblioteca auditada. Ninguna
implementación criptográfica propia debe desplegarse en producción. Este
módulo define la *semántica* que cualquiera de esos esquemas debe cumplir
frente a la interfaz de `gts.py`.

Propiedades (todas hash-only, sin asunción de logaritmos discretos):

  - Resistencia cuántica por construcción: el peor ataque conocido a una
    firma de este tipo es Grover sobre SHA-256 → seguridad >= 2^128 contra
    el precomputo de preimágenes de la llave pública del árbol.
  - Claves de un solo uso (WOTS): cada hoja del árbol firma exactamente un
    mensaje. La disciplina de estado es responsabilidad del portador: el
    contador `_leaves_used` vive en memoria, por lo que dos instancias
    creadas de la misma semilla pueden firmar la misma hoja. Para estado
    persistente entre procesos existe `LeafLedger` (archivo + fcntl).
  - Árbol Merkle: la llave pública es un único valor de 32 bytes que respalda
    2^h firmas de un solo uso.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import List

N = 32          # bytes de hash (SHA-256)
W = 16          # Winternitz: dígitos de 4 bits
U = (8 * N) // 4  # dígitos del digest: 64
V = 3           # dígitos del checksum (max csum = U*(W-1) = 960 < 16^3)
P = U + V       # elementos de la firma: 67


def _h(*parts: bytes) -> bytes:
    digest = hashlib.sha256()
    for p in parts:
        digest.update(len(p).to_bytes(4, "big") + p)
    return digest.digest()


def _chain(seed: bytes, start: int, steps: int, index: int) -> bytes:
    """Iteración Winternitz: aplicar la función de cadena `steps` veces."""
    tmp = seed
    for i in range(start, start + steps):
        tmp = _h(b"F", tmp, i.to_bytes(4, "big"), index.to_bytes(4, "big"))
    return tmp


def _encode_message(digest: bytes) -> List[int]:
    """Descompone un digest en U dígitos base-W + V dígitos de checksum."""
    value = int.from_bytes(digest, "big")
    out: List[int] = []
    for _ in range(U):
        out.append(value % W)
        value //= W
    csum = sum(W - 1 - c for c in out)   # <= 960, cabe en V dígitos
    for _ in range(V):
        out.append(csum % W)
        csum //= W
    return out


def wots_pubkey_from_seed(seed: bytes) -> bytes:
    """Llave pública WOTS (cadena completa, P elementos) para una semilla."""
    out = bytearray()
    for i in range(P):
        out += _chain(seed, 0, W - 1, i)
    return bytes(out)


class WotsMerkleSigner:
    """Firmante Merkle de un solo nivel: 2^height firmas de un solo uso."""

    def __init__(self, seed: bytes, height: int = 8):
        if height < 1 or height > 16:
            raise ValueError("height fuera de rango 1..16")
        self.seed = seed
        self.height = height
        self.leaves = 1 << height
        self._leaves_used = 0
        self._pub_leaf: List[bytes] = [
            wots_pubkey_from_seed(_h(b"K", seed, i.to_bytes(4, "big")))
            for i in range(self.leaves)
        ]
        self.public_key = self._build_tree(self._pub_leaf)[(0, self.height)]

    # -- árbol ------------------------------------------------------------
    @staticmethod
    def _build_tree(leaves: List[bytes]) -> dict:
        """Nodos {(índice, altura): valor}, altura 0 = hoja."""
        nodes: dict = {}
        level = leaves
        for i, leaf in enumerate(level):
            nodes[(i, 0)] = leaf
        h = 1
        while len(level) > 1:
            level = [_h(b"T", level[i], level[i + 1]) for i in range(0, len(level), 2)]
            for i, node in enumerate(level):
                nodes[(i, h)] = node
            h += 1
        return nodes

    # -- firma ------------------------------------------------------------
    def sign(self, message_digest: bytes) -> dict:
        """Firma un digest de 32 bytes. Cada hoja solo puede usarse una vez."""
        if self._leaves_used >= self.leaves:
            raise RuntimeError("Árbol de firmas agotado: re-key requerida")
        leaf_index = self._leaves_used
        self._leaves_used += 1
        return self.sign_at(leaf_index, message_digest)

    def sign_at(self, leaf_index: int, message_digest: bytes) -> dict:
        """Firma con una hoja concreta (para recrear logs deterministas)."""
        key_seed = _h(b"K", self.seed, leaf_index.to_bytes(4, "big"))
        coeffs = _encode_message(message_digest)
        sig_elements = [_chain(key_seed, 0, c, i) for i, c in enumerate(coeffs)]
        nodes = self._build_tree(self._pub_leaf)
        path = []
        idx = leaf_index
        for h in range(self.height):
            sib = idx ^ 1
            path.append(nodes[(sib, h)].hex())
            idx //= 2
        return {
            "leaf": leaf_index,
            "sig": [s.hex() for s in sig_elements],
            "path": path,
        }

    # -- verificación (estática; no requiere semilla privada) --------------
    @staticmethod
    def verify(public_key: bytes, message_digest: bytes, signature: dict) -> bool:
        if len(message_digest) != N:
            return False
        leaf_index = int(signature["leaf"])
        sig_elements = [bytes.fromhex(x) for x in signature["sig"]]
        if len(sig_elements) != P:
            return False
        coeffs = _encode_message(message_digest)
        recomputed = bytearray()
        for i, (elem, c) in enumerate(zip(sig_elements, coeffs)):
            recomputed += _chain(elem, c, W - 1 - c, i)
        leaf = bytes(recomputed)
        node = leaf
        for h, sib_hex in enumerate(signature["path"]):
            sib = bytes.fromhex(sib_hex)
            if (leaf_index >> h) & 1:
                node = _h(b"T", sib, node)
            else:
                node = _h(b"T", node, sib)
        return hmac.compare_digest(node, public_key)


def digest_message(message: bytes) -> bytes:
    return hashlib.sha256(message).digest()


class LeafLedger:
    """Estado de hojas persistente con bloqueo de archivo (solo stdlib).

    SOLO pruebas/referencia; producción = SLH-DSA. Resuelve el hueco de dos
    instancias en memoria que firmarían la misma hoja: el índice de la
    siguiente hoja se asigna bajo exclusión mútua (`fcntl.flock`) desde un
    archivo JSON compartido, así que dos procesos de la misma semilla jamás
    reciben el mismo índice mientras compartan el ledger.

    Uso con `WotsMerkleSigner`:

        ledger = LeafLedger("hojas.json")
        idx = ledger.allocate(signer.leaves)
        sig = signer.sign_at(idx, digest)

    El archivo NO guarda material criptográfico: solo {"next": índice}.
    """

    def __init__(self, path: str):
        import fcntl
        import json
        import os
        self._fcntl = fcntl
        self._json = json
        self._os = os
        self.path = str(path)

    def _started(self):
        existed = self._os.path.exists(self.path)
        self._fd = self._os.open(self.path, self._os.O_RDWR | self._os.O_CREAT, 0o600)
        self._fcntl.flock(self._fd, self._fcntl.LOCK_EX)
        return existed

    def _state(self, existed: bool) -> dict:
        if not existed:
            return {"next": 0}
        self._os.lseek(self._fd, 0, 0)
        raw = b""
        while True:
            chunk = self._os.read(self._fd, 4096)
            if not chunk:
                break
            raw += chunk
        if not raw.strip():
            return {"next": 0}
        st = self._json.loads(raw.decode("utf-8"))
        if not isinstance(st.get("next"), int) or st["next"] < 0:
            raise ValueError(f"ledger corrupto: {self.path}")
        return st

    def allocate(self, total_leaves: int) -> int:
        """Reserva la siguiente hoja bajo bloqueo; RuntimeError si agotado."""
        existed = self._started()
        try:
            st = self._state(existed)
            idx = st["next"]
            if idx >= total_leaves:
                raise RuntimeError(
                    f"ledger agotado ({idx}/{total_leaves}): re-key requerida"
                )
            st["next"] = idx + 1
            payload = self._json.dumps(st).encode("utf-8")
            self._os.lseek(self._fd, 0, 0)
            self._os.ftruncate(self._fd, 0)
            self._os.lseek(self._fd, 0, 0)
            self._os.write(self._fd, payload)
            self._os.fsync(self._fd)
            return idx
        finally:
            self._fcntl.flock(self._fd, self._fcntl.LOCK_UN)
            self._os.close(self._fd)
