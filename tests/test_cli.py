# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Tests del CLI (superficie de uso mínimo, sin dependencias)."""

from __future__ import annotations

import json

from gerarion import cli


def test_convert_greg_to_gero(capsys):
    assert cli.main(["convert", "2026-05-23"]) == 0
    out = capsys.readouterr().out
    assert "2031DY-03-08-T" in out
    assert "Trustdyia" in out


def test_convert_gero_to_greg(capsys):
    assert cli.main(["convert", "2031DY-03-08-T"]) == 0
    out = capsys.readouterr().out
    assert "2026-05-23" in out


def test_normalize(capsys):
    assert cli.main(["normalize", "2031dy-3-8-t"]) == 0
    assert capsys.readouterr().out.strip() == "2031DY-03-08-T"


def test_keygen_sign_verify(tmp_path, capsys):
    key = tmp_path / "key.json"
    assert cli.main(["keygen", "--height", "2", "--out", str(key)]) == 0
    key_data = json.loads(key.read_text())
    assert len(key_data["public_key"]) == 64  # 32 bytes hex

    gst_file = tmp_path / "gst.json"
    capsys.readouterr()
    assert cli.main(["sign", "2031DY-03-08-T", "--key", str(key)]) == 0
    gst_file.write_text(capsys.readouterr().out, encoding="utf-8")

    assert cli.main(["verify", str(gst_file)]) == 0


def test_verify_detects_tampering(tmp_path, capsys):
    key = tmp_path / "key.json"
    cli.main(["keygen", "--height", "2", "--out", str(key)])
    capsys.readouterr()
    assert cli.main(["sign", "2031DY-03-08-T", "--key", str(key)]) == 0
    gst_file = tmp_path / "gst.json"
    gst_file.write_text(capsys.readouterr().out, encoding="utf-8")

    doc = json.loads(gst_file.read_text())
    doc["ins"] += 3600  # +1 hora: falsificación trivialmente detectada
    gst_file.write_text(json.dumps(doc))

    assert cli.main(["verify", str(gst_file)]) == 1
