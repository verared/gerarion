# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Command-line interface del sistema Gerarion.

    gero convert 2026-05-23            gregoriano -> gerarion
    gero convert 2031DY-03-08-T        gerarion -> gregoriano
    gero normalize <ts>
    gero keygen --height 8
    gero sign <ts> --key key.json
    gero verify <gst.json>
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

from .core import calendar as cal
from .core import format as fmt
from .gst import envelope as gts
try:
    from .deprecated import hashots
except ImportError:  # instalación sin el subpaquete deprecated
    hashots = None
from .core.calendar import GeroError


def cmd_convert(args) -> int:
    arg = args.date
    is_gerarion = "DY" in arg.upper() or "AY" in arg.upper()
    if is_gerarion:
        parsed = fmt.parse(arg)
        date = cal.from_gerarion(parsed.year, parsed.month, parsed.day)
        gy, gm, gd = cal.gregorian_from_day_index(date.day_index)
        print(
            f"{arg} -> {gy:04d}-{gm:02d}-{gd:02d} gregoriano | "
            f"{date.canonical()} | día {date.day_index} | {date.weekday[0]}"
        )
    else:
        parts = [int(p) for p in arg.replace("/", "-").split("-")]
        di = cal.day_index_from_gregorian(parts[0], parts[1], parts[2])
        date = cal.to_gerarion(di)
        print(
            f"{arg} -> {date.canonical()} | {date.weekday[0]} | "
            f"mes {date.month} ({cal.MONTHS[date.month][0]}) | día {date.day_index}"
        )
    return 0


def cmd_normalize(args) -> int:
    parsed = fmt.parse(args.ts)
    print(fmt.to_canonical(parsed))
    if parsed.flags:
        print("flags:", ", ".join(parsed.flags), file=sys.stderr)
    return 0


def _load_key(path: str) -> hashots.WotsMerkleSigner:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return hashots.WotsMerkleSigner(seed=bytes.fromhex(data["seed"]), height=data["height"])

def cmd_keygen(args) -> int:
    seed = secrets.token_bytes(32)
    signer = hashots.WotsMerkleSigner(seed=seed, height=args.height)
    Path(args.out).write_text(
        json.dumps(
            {
                "seed": seed.hex(),
                "height": args.height,
                "public_key": signer.public_key.hex(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"clave generada ({args.out}) pub={signer.public_key.hex()}")
    return 0


def cmd_sign(args) -> int:
    signer = _load_key(args.key)
    doc = gts.create(args.ts, signer)
    print(doc.to_json())
    return 0


def cmd_verify(args) -> int:
    doc = gts.GtsDocument.from_json(Path(args.file).read_text(encoding="utf-8"))
    result = gts.verify(doc)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="gero", description="Sistema Gerarion GUS v2")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("convert", help="convierte fechas en ambas direcciones")
    p.add_argument("date")
    p.set_defaults(func=cmd_convert)

    p = sub.add_parser("normalize", help="normaliza una marca temporal")
    p.add_argument("ts")
    p.set_defaults(func=cmd_normalize)

    p = sub.add_parser("keygen", help="genera par de claves hash-only")
    p.add_argument("--height", type=int, default=8)
    p.add_argument("--out", default="key.json")
    p.set_defaults(func=cmd_keygen)

    p = sub.add_parser("sign", help="firma una marca temporal")
    p.add_argument("ts")
    p.add_argument("--key", default="key.json")
    p.set_defaults(func=cmd_sign)

    p = sub.add_parser("verify", help="verifica una GST")
    p.add_argument("file")
    p.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except GeroError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
