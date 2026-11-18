#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Puente OpenTimestamps: ancla las raíces diarias del notario GUS en Bitcoin.

El notario GUS es la cadena de confianza primaria; este puente es evidencia
secundaria (véase docs/notary-runbook.md §7): sella el hash del día
(`day_root`) usando el cliente OpenTimestamps (`ots`) si está instalado.

Uso:
    python3 tools/ots_bridge.py stamp <day_root.hex> <dir-salida>
    python3 tools/ots_bridge.py verify <archivo.ots> <day_root.hex>

Sin `ots` instalado imprime la instrucción de instalación y sale 2 (los
puentes son opcionales: su ausencia no invalida la cadena GUS).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys


def _ots() -> str | None:
    return shutil.which("ots")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    cmd = sys.argv[1]

    if not _ots():
        print("ots no está instalado. Puente OPCIONAL: ")
        print("  pip install opentimestamps-client")
        print("Documentación: https://opentimestamps.org")
        return 2

    if cmd == "stamp":
        root_hex, out_dir = sys.argv[2], sys.argv[3]
        try:
            bytes.fromhex(root_hex)
        except ValueError:
            print("day_root inválido (se esperaba hex 64)")
            return 2
        os.makedirs(out_dir, exist_ok=True)
        # OTS sella el SHA-256 del contenido de un archivo: escribimos un
        # archivo-evidencia que contiene el day_root y sellamos ése. El .ots
        # prueba que "day_root n" existía antes del momento del sello.
        path = os.path.join(out_dir, f"day-{root_hex[:16]}.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"GUS2-DAYROOT {root_hex}\n")
        print(f"archivo-evidencia: {path}")
        r = subprocess.run(["ots", "stamp", path], check=False)
        return r.returncode

    if cmd == "verify":
        ots_path, _root_hex = sys.argv[2], sys.argv[3]
        r = subprocess.run(["ots", "verify", ots_path], check=False)
        return r.returncode

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
