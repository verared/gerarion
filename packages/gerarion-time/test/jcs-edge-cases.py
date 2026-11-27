# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Casos borde JCS compartidos por los tests de paridad Python↔JS.

Cada caso es un texto JSON de entrada; la canonicalización de referencia
la produce gerarion.gst.jcs (Python) y el test JS la recomputa con
src/jcs.ts comparando bytes.
"""
import json

CASES = [
    # (nombre, texto JSON de entrada compartido)
    ("neg_zero", "-0.0"),
    ("max_safe_int", "9007199254740991"),
    ("min_safe_int", "-9007199254740991"),
    ("float_1e-7", "1e-7"),
    ("float_1e21", "1e21"),
    ("float_precision", "0.1"),
    ("string_controls", json.dumps("a\u0001b\tc\nd\fe\"f\\g")),
    ("string_unicode", json.dumps("é中𝄞😀")),
    ("nested", json.dumps({"a": [1, {"b": None}, "x"], "c": True, "d": None})),
]

out = []
for name, input_text in CASES:
    value = json.loads(input_text)
    from gerarion.gst.jcs import dumps  # noqa: E402
    canonical = dumps(value)
    out.append({"name": name, "input": input_text, "canonical_hex": canonical.encode("utf-8").hex()})
print(json.dumps(out))
