# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Pruebas de tools/export_module.py: exportación a los satélites gt-*.

Cada test exporta a un directorio temporal (pytest tmp_path) y valida:
- existencia de todos los archivos esperados y de los metadatos;
- `reuse lint` al 100 % en cada export (subproceso, misma suite que usa
  `--verify`);
- compilación autónoma de gt-core fuera del árbol de verared/gerarion;
- ausencia de importaciones rotas inesperadas (referencias huérfanas).

Ejecutar: PYTHONPATH=src pytest tests/test_export_module.py -q
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

try:
    import reuse  # noqa: F401
    REUSE_AVAILABLE = True
except ImportError:
    REUSE_AVAILABLE = False

needs_reuse = pytest.mark.skipif(
    not REUSE_AVAILABLE, reason="reuse no instalado en este entorno"
)

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import export_module as em  # noqa: E402

ALL_MODULES = sorted(em.MODULES)
LARGE = "vectors/guti-calendars-001.json"

pytestmark = pytest.mark.filterwarnings(
    "ignore::DeprecationWarning:gerarion.*",
)


def _run_tool(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "tools" / "export_module.py"), *args],
        capture_output=True, text=True, cwd=REPO,
    )


def _reuse_lint(path: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    return subprocess.run(
        [sys.executable, "-m", "reuse", "lint"],
        cwd=path, capture_output=True, text=True, env=env,
    )


# ---------------------------------------------------------------------------
# export single: gt-core
# ---------------------------------------------------------------------------


def test_gt_core_export_expected_files(tmp_path: Path) -> None:
    out = tmp_path
    rc = _run_tool("--module", "gt-core", "--out", str(out))
    assert rc.returncode == 0, rc.stderr
    export = out / "gt-core"
    expected = [
        "LICENSE", "NOTICE", "REUSE.toml", "README.md", "README.es.md",
        "EXPORT-MANIFEST.json",
        "LICENSES/MIT.txt", "LICENSES/Apache-2.0.txt",
        "LICENSES/CC-BY-4.0.txt", "LICENSES/CC0-1.0.txt",
        "impl-c/Makefile", "impl-c/gerarion-core.pc.in",
        "impl-c/smoke.c", "impl-c/core/gus_core.h", "impl-c/core/gus_core.c",
        "src/gerarion/core/calendar.py", "src/gerarion/core/format.py",
        "web/engine/core.mjs",
        "vectors/gus-normative-003.json",
        "vectors/gus-quickverify-001.json",
        "vectors/gus-regression-001.json",
        "docs/specs/TCJ.es.md", "docs/specs/TCJ.en.md",
        "docs/specs/GUS.es.md", "docs/specs/GUS.en.md",
    ]
    for rel in expected:
        assert (export / rel).is_file(), f"falta {rel}"


@needs_reuse
def test_gt_core_reuse_lint_100(tmp_path: Path) -> None:
    out = tmp_path / "sat"
    rc = _run_tool("--module", "gt-core", "--out", str(out))
    assert rc.returncode == 0, rc.stderr
    lint = _reuse_lint(out / "gt-core")
    assert lint.returncode == 0, lint.stdout + lint.stderr
    assert "not compliant" not in lint.stdout


def test_gt_core_compiles_standalone(tmp_path: Path) -> None:
    """El núcleo compila y corre su humo FUERA del árbol de gerarion."""
    out = tmp_path / "sat"
    rc = _run_tool("--module", "gt-core", "--out", str(out))
    assert rc.returncode == 0, rc.stderr
    build = subprocess.run(
        ["make", "smoke",
         "CFLAGS=-std=gnu11 -O2 -Wall -Wextra -Werror"],
        cwd=out / "gt-core" / "impl-c", capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    assert "2031DY-01-01-S" in build.stdout


def test_gt_core_no_unresolved_references(tmp_path: Path) -> None:
    out = tmp_path
    _run_tool("--module", "gt-core", "--out", str(out))
    code_dir = out / "gt-core"
    # standalone: los archivos de código de GT-core no deben importar nada externo
    broken = [r for r in em._external_import_roots(code_dir)
              if not r.startswith("..") and "/" not in r]
    assert broken == [], f"referencias huérfanas inesperadas: {broken}"
    # 100% standalone: sin Makefile/no-dinámica en gus_core.c
    src = (code_dir / "impl-c" / "core" / "gus_core.c").read_text()
    assert "malloc" not in src, "el núcleo MCU no debe usar malloc"
    assert "pthread" not in src
    assert "time.h" not in src, "el núcleo standalone no debe usar el reloj del SO"


# ---------------------------------------------------------------------------
# los 9 módulos: export + reuse lint al 100 %
# ---------------------------------------------------------------------------


@needs_reuse
def test_all_modules_export_and_reuse_lint(tmp_path: Path) -> None:
    rc = _run_tool("--all", "--out", str(tmp_path))
    assert rc.returncode == 0, rc.stderr
    assert sorted(p.name for p in tmp_path.iterdir()) == ALL_MODULES
    for name in ALL_MODULES:
        lint = _reuse_lint(tmp_path / name)
        assert lint.returncode == 0, (name, lint.stdout, lint.stderr)
        assert "not compliant" not in lint.stdout


@pytest.mark.parametrize("name", ALL_MODULES)
def test_module_metadata_present(tmp_path: Path, name: str) -> None:
    rc = _run_tool("--module", name, "--out", str(tmp_path))
    assert rc.returncode == 0, rc.stderr
    export = tmp_path / name
    assert (export / "REUSE.toml").is_file()
    assert (export / "EXPORT-MANIFEST.json").is_file()
    manifest = json.loads((export / "EXPORT-MANIFEST.json").read_text())
    assert manifest["schema"] == "gerarion-export-manifest/1"
    assert manifest["module"] == name
    assert manifest["version"] == em.GERARION_VERSION
    assert manifest["source_repo"] == "verared/gerarion"
    assert manifest["source_tag"] == f"v{em.GERARION_VERSION}"
    assert "EXPORT-MANIFEST.json" not in manifest["files"]
    for readme in ("README.md", "README.es.md"):
        text = (export / readme).read_text()
        assert f"verared/{name}" in text
        assert em.GERARION_VERSION in text
        assert "verared/gerarion" in text
        assert "EXPORT-MANIFEST.json" in text
        assert "COMPATIBILITY.md" in text
    spec_doc = em.MODULES[name].docs[0]
    assert (export / spec_doc).is_file()


# ---------------------------------------------------------------------------
# dependencias declaradas vs referencias reales
# ---------------------------------------------------------------------------


def test_unexpected_orphan_references(tmp_path: Path) -> None:
    """Las referencias que no resuelven dentro del export deben estar
    declaradas como dependencias (roots externos esperados del módulo)."""
    rc = _run_tool("--all", "--out", str(tmp_path))
    assert rc.returncode == 0, rc.stderr
    for name in ALL_MODULES:
        export = tmp_path / name
        spec = em.MODULES[name]
        missing = set(em._external_import_roots(export))
        unexpected = {m for m in missing if m not in spec.external_roots}
        assert not unexpected, (name, sorted(missing), spec.external_roots)


def test_experimental_scaffolds(tmp_path: Path) -> None:
    for name in ("gt-tslr", "gt-gcerts"):
        rc = _run_tool("--module", name, "--out", str(tmp_path))
        assert rc.returncode == 0, rc.stderr
        export = tmp_path / name
        for sub in ("src", "tests", "vectors"):
            assert (export / sub / ".gitkeep").is_file()
        readme = (export / "README.md").read_text()
        assert "EXPERIMENTAL" in readme
        # sin implementación todavía: src queda vacío salvo el andamiaje
        assert [p for p in (export / "src").iterdir() if p.name != ".gitkeep"] == []


# ---------------------------------------------------------------------------
# vectores grandes
# ---------------------------------------------------------------------------


def test_no_large_vectors_flag(tmp_path: Path) -> None:
    rc = _run_tool("--module", "gt-calendar", "--out", str(tmp_path),
                   "--no-large-vectors")
    assert rc.returncode == 0, rc.stderr
    assert not (tmp_path / "gt-calendar" / LARGE).exists()

    rc = _run_tool("--module", "gt-calendar", "--out", str(tmp_path))
    assert rc.returncode == 0, rc.stderr
    assert (tmp_path / "gt-calendar" / LARGE).is_file()


# ---------------------------------------------------------------------------
# determinismo y tamaño del export
# ---------------------------------------------------------------------------


def test_export_is_deterministic(tmp_path: Path) -> None:
    out1, out2 = tmp_path / "a", tmp_path / "b"
    assert _run_tool("--module", "gt-core", "--out", str(out1)).returncode == 0
    assert _run_tool("--module", "gt-core", "--out", str(out2)).returncode == 0
    f1 = sorted(str(p.relative_to(out1 / "gt-core"))
                for p in (out1 / "gt-core").rglob("*") if p.is_file())
    f2 = sorted(str(p.relative_to(out2 / "gt-core"))
                for p in (out2 / "gt-core").rglob("*") if p.is_file())
    assert f1 == f2
    assert (out1 / "gt-core" / "REUSE.toml").read_bytes() == \
        (out2 / "gt-core" / "REUSE.toml").read_bytes()


def test_frozen_sources_untouched_by_export(tmp_path: Path) -> None:
    """Exportar NO altera el repositorio base (invariante de solo lectura)."""
    before = {
        p: p.stat().st_mtime_ns
        for p in list((REPO / "impl-c").rglob("*.c"))
        + list((REPO / "src" / "gerarion").rglob("*.py"))
        + [REPO / "vectors" / "gus-normative-003.json"]
    }
    _run_tool("--module", "gt-core", "--out", str(tmp_path))
    after = {
        p: p.stat().st_mtime_ns
        for p in list((REPO / "impl-c").rglob("*.c"))
        + list((REPO / "src" / "gerarion").rglob("*.py"))
        + [REPO / "vectors" / "gus-normative-003.json"]
    }
    assert before == after
