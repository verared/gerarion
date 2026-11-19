# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Pruebas de integración cruzada de los 9 repositorios satélite ensamblados.

Verifica:
1. Integridad byte a byte de EXPORT-MANIFEST.json en los 9 satélites y
   determinismo absoluto con el mismo --source-commit.
2. Detección de manipulación/archivos faltantes/sobrantes en --verify-existing.
3. Ensamblado limpio de los 7 satélites de código (gt-core + gt-gus + gt-tcj +
   gt-calendar + gt-gts + gt-gst + gt-interop) en un directorio aislado fuera
   de verared/gerarion, ejecutando integración real en C11, Python y JavaScript.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "export_module.py"
CODE_SATELLITES = (
    "gt-core",
    "gt-gus",
    "gt-tcj",
    "gt-calendar",
    "gt-gts",
    "gt-gst",
    "gt-interop",
)
ALL_SATELLITES = (
    "gt-calendar",
    "gt-core",
    "gt-gcerts",
    "gt-gst",
    "gt-gts",
    "gt-gus",
    "gt-interop",
    "gt-tcj",
    "gt-tslr",
)
FIXED_COMMIT = "0123456789abcdef0123456789abcdef01234567"

try:
    import reuse  # noqa: F401
    REUSE_AVAILABLE = True
except ImportError:
    REUSE_AVAILABLE = False

needs_reuse = pytest.mark.skipif(
    not REUSE_AVAILABLE, reason="reuse no instalado en este entorno"
)


def _run_exporter(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True, text=True, cwd=REPO,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assemble_code_satellites(export_root: Path, assembled_dir: Path) -> None:
    """Combina los 7 satélites de código en un árbol limpio, sin tocar el repo."""
    for mod in CODE_SATELLITES:
        mod_dir = export_root / mod
        for sub in ("impl-c", "src", "web", "vectors"):
            src_sub = mod_dir / sub
            if src_sub.is_dir():
                shutil.copytree(src_sub, assembled_dir / sub, dirs_exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Integridad del manifiesto y determinismo de los 9 satélites
# ---------------------------------------------------------------------------


def test_all_nine_manifests_integrity_and_reproducibility(tmp_path: Path) -> None:
    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"

    rc_a = _run_exporter("--all", "--out", str(out_a), "--no-large-vectors",
                         "--source-commit", FIXED_COMMIT)
    assert rc_a.returncode == 0, rc_a.stderr + rc_a.stdout
    rc_b = _run_exporter("--all", "--out", str(out_b), "--no-large-vectors",
                         "--source-commit", FIXED_COMMIT)
    assert rc_b.returncode == 0, rc_b.stderr + rc_b.stdout

    assert sorted(p.name for p in out_a.iterdir()) == list(ALL_SATELLITES)

    for name in ALL_SATELLITES:
        dir_a = out_a / name
        dir_b = out_b / name
        man_a = json.loads((dir_a / "EXPORT-MANIFEST.json").read_text(encoding="utf-8"))
        man_b = json.loads((dir_b / "EXPORT-MANIFEST.json").read_text(encoding="utf-8"))
        assert man_a == man_b, f"export no determinista en {name}"
        assert (dir_a / "EXPORT-MANIFEST.json").read_bytes() == (
            dir_b / "EXPORT-MANIFEST.json"
        ).read_bytes()
        assert man_a["schema"] == "gerarion-export-manifest/1"
        assert man_a["module"] == name
        assert man_a["source_repo"] == "verared/gerarion"
        assert man_a["source_commit"] == FIXED_COMMIT
        assert "EXPORT-MANIFEST.json" not in man_a["files"]

        # Verificar cada archivo byte a byte en disco
        disk_files = sorted(
            p.relative_to(dir_a).as_posix()
            for p in dir_a.rglob("*")
            if p.is_file() and p.name != "EXPORT-MANIFEST.json"
        )
        assert disk_files == sorted(man_a["files"].keys())
        for rel, expected_hash in man_a["files"].items():
            assert _sha256(dir_a / rel) == expected_hash
            assert (dir_a / rel).read_bytes() == (dir_b / rel).read_bytes()


@needs_reuse
def test_verify_existing_detects_tampering_and_extra_files(tmp_path: Path) -> None:
    rc = _run_exporter("--module", "gt-core", "--out", str(tmp_path),
                       "--source-commit", FIXED_COMMIT)
    assert rc.returncode == 0, rc.stderr
    sat = tmp_path / "gt-core"

    ok = _run_exporter("--verify-existing", str(sat))
    assert ok.returncode == 0, ok.stdout + ok.stderr

    # Archivo sobrante debe fallar
    extra = sat / "intruder.txt"
    extra.write_text("tamper\n", encoding="utf-8")
    bad_extra = _run_exporter("--verify-existing", str(sat))
    assert bad_extra.returncode != 0
    extra.unlink()

    # Modificación de un byte debe fallar
    readme = sat / "README.md"
    orig = readme.read_bytes()
    readme.write_bytes(orig + b"\n")
    bad_hash = _run_exporter("--verify-existing", str(sat))
    assert bad_hash.returncode != 0
    readme.write_bytes(orig)

    # Restaurado vuelve a pasar
    ok2 = _run_exporter("--verify-existing", str(sat))
    assert ok2.returncode == 0, ok2.stdout + ok2.stderr


# ---------------------------------------------------------------------------
# 2. Integración cruzada ensamblada: C11, Python y JavaScript
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def assembled_workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("sat_assembly")
    exported = root / "exported"
    assembled = root / "assembled"
    rc = _run_exporter("--all", "--out", str(exported), "--no-large-vectors",
                       "--source-commit", FIXED_COMMIT)
    assert rc.returncode == 0, rc.stderr + rc.stdout
    _assemble_code_satellites(exported, assembled)
    return assembled


def test_assembled_c11_integration(assembled_workspace: Path) -> None:
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("compilador C no disponible")

    driver = assembled_workspace / "c11_integration.c"
    driver.write_text(textwrap.dedent("""\
        #include <assert.h>
        #include <stdio.h>
        #include <string.h>

        #include "impl-c/core/gus_core.h"
        #include "impl-c/tai/gus_tai.h"
        #include "impl-c/clock/gus_clock.h"
        #include "impl-c/calendars/gerarion_calendars.h"

        int main(void) {
            /* 1. Parseo de sello GUS desde gt-core */
            GusParsed parsed;
            assert(gus_parse("2031DY-03-08-T-09:30:00-SC-TCJ+0", true, &parsed) == GUS_OK);
            assert(parsed.has_time == 1);
            long long di = parsed.date.day_index;
            assert(di == 741871);

            /* 2. Conversión TCJ/TAI desde gt-tcj */
            GusTaiTableInfo info = gus_tai_table_info();
            assert(strcmp(info.table_version, "IERS-C-2026.1") == 0);
            int extrapolated = -1;
            int offset = gus_tai_minus_utc_checked(1779528600LL, &extrapolated);
            assert(offset == 37);
            assert(extrapolated == 0);

            /* 3. Traducción entre calendarios desde gt-calendar */
            GerarionCalDate greg;
            assert(gerarion_cal_from_day_index(di, GER_CAL_GREG, &greg) == GUS_OK);
            assert(greg.f[0] == 2026 && greg.f[1] == 5 && greg.f[2] == 23);
            long long di_roundtrip = 0;
            assert(gerarion_cal_to_day_index(GER_CAL_GREG, &greg, &di_roundtrip) == GUS_OK);
            assert(di_roundtrip == di);

            /* 4. Máquina de estados de reloj desde gt-gts (VERIFIED + rollback sub-segundo) */
            GusClockPolicy pol = {
                .max_uncertainty_ns = 10000000LL,
                .max_holdover_s = 60,
                .drift_ppm = 50,
                .strict = 1,
                .require_authenticated = 1
            };
            GusClockReading anchor = {
                .seconds = 64097654400LL,
                .nanos = 500000000U,
                .state = GUS_CLOCK_VERIFIED,
                .source_id = "gnss-1",
                .uncertainty_ns = 1000000LL,
                .monotonic_ns = 1000000000LL,
                .authenticated = 1
            };
            GusClockReading good = {
                .seconds = 64097654400LL,
                .nanos = 600000000U,
                .state = GUS_CLOCK_UNVERIFIED,
                .source_id = "gnss-1",
                .uncertainty_ns = 1000000LL,
                .monotonic_ns = 1100000000LL,
                .authenticated = 1
            };
            assert(gus_clock_classify(&good, &pol, &anchor) == GUS_CLOCK_VERIFIED);

            /* Retroceso sub-segundo (mismo segundo, nanos menores) -> REJECTED */
            GusClockReading rollback = good;
            rollback.nanos = 499999999U;
            assert(gus_clock_classify(&rollback, &pol, &anchor) == GUS_CLOCK_REJECTED);

            printf("C11_SATELLITE_INTEGRATION_OK\\n");
            return 0;
        }
    """), encoding="utf-8")

    binary = assembled_workspace / "c11_integration.bin"
    sources = [
        str(driver),
        str(assembled_workspace / "impl-c" / "core" / "gus_core.c"),
        str(assembled_workspace / "impl-c" / "tai" / "gus_tai.c"),
        str(assembled_workspace / "impl-c" / "clock" / "gus_clock.c"),
        str(assembled_workspace / "impl-c" / "calendars" / "gerarion_calendars.c"),
        str(assembled_workspace / "impl-c" / "calendars" / "china_table.c"),
    ]
    comp = subprocess.run(
        [cc, "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror",
         f"-I{assembled_workspace}", *sources, "-o", str(binary)],
        capture_output=True, text=True, cwd=assembled_workspace,
    )
    assert comp.returncode == 0, comp.stdout + comp.stderr

    run = subprocess.run([str(binary)], capture_output=True, text=True,
                         cwd=assembled_workspace)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "C11_SATELLITE_INTEGRATION_OK" in run.stdout


def test_assembled_python_integration(assembled_workspace: Path) -> None:
    script = textwrap.dedent("""\
        import os
        import sys
        from pathlib import Path

        assembled_src = Path(os.environ["ASSEMBLED_SRC"]).resolve()
        repo_root = Path(os.environ["FORBIDDEN_REPO"]).resolve()

        # Bloquear explícitamente el repo principal en sys.path
        sys.path = [
            p for p in sys.path
            if not (p and Path(p).resolve().is_relative_to(repo_root))
        ]
        sys.path.insert(0, str(assembled_src))

        from gerarion.core import calendar as core_cal, format as core_fmt
        from gerarion.tcj import tai as tcj_tai
        from gerarion import calendars as multi_cal
        from gerarion.gts import clock as gts_clock
        from gerarion.gst import (
            envelope as gst_env,
            jcs as gst_jcs,
            adapters as gst_adapters,
            trust as gst_trust,
            replay as gst_replay,
            v2 as gst_v2,
        )
        from gerarion.interop import profiles as interop_profiles

        # Confirmar que TODOS los módulos cargaron desde assembled_src
        for mod in (core_cal, core_fmt, tcj_tai, multi_cal, gts_clock,
                    gst_env, gst_jcs, gst_adapters, gst_trust, gst_replay,
                    gst_v2, interop_profiles):
            mod_path = Path(mod.__file__).resolve()
            assert mod_path.is_relative_to(assembled_src), f"cargado fuera de satélites: {mod_path}"

        # 1. core: crear instante y sello canónico
        di = core_cal.day_index_from_gregorian(2026, 5, 23)
        gd = core_cal.to_gerarion(di)
        assert gd.canonical() == "2031DY-03-08-T"
        ins = core_cal.instant_from_parts(di, 9, 30, 0)
        parsed = core_fmt.parse("2031DY-03-08-T-09:30:00-SC-TCJ+0")
        parsed_gd = core_cal.from_gerarion(parsed.year, parsed.month, parsed.day)
        assert core_cal.instant_from_parts(
            parsed_gd.day_index, parsed.hour, parsed.minute, parsed.second
        ) == ins

        # 2. tcj: consultar tabla TAI-UTC y conversión Unix <-> instant
        assert tcj_tai.tai_minus_utc(1779528600) == 37
        assert tcj_tai.unix_from_instant(tcj_tai.instant_from_unix(1779528600)) == 1779528600

        # 3. calendars: traducir entre calendarios
        greg = multi_cal.from_day_index(di, "greg")
        assert greg.fields == (2026, 5, 23)
        assert multi_cal.to_day_index("greg", {"year": 2026, "month": 5, "day": 23}) == di

        # 4. gts: evaluar reloj (VERIFIED + rechazo rollback sub-segundo)
        pol = gts_clock.ClockPolicy(max_uncertainty_ns=10_000_000, strict=True, require_authenticated=True)
        tc = gts_clock.TrustedClock(policy=pol)
        r1 = tc.classify(gts_clock.ClockReading(
            instant=ins, nanos=500_000_000, source_id="gnss-1",
            uncertainty_ns=1_000_000, monotonic_ns=1_000_000_000, authenticated=True,
        ))
        assert r1.state == gts_clock.ClockState.VERIFIED
        r2 = tc.classify(gts_clock.ClockReading(
            instant=ins, nanos=499_999_999, source_id="gnss-1",
            uncertainty_ns=1_000_000, monotonic_ns=1_100_000_000, authenticated=True,
        ))
        assert r2.state == gts_clock.ClockState.REJECTED

        # 5. gst: rechazo de enteros > 2^53-1 en JCS
        jcs_rejected = False
        try:
            gst_jcs.dumps({"n": (1 << 53)})
        except gst_jcs.JcsError:
            jcs_rejected = True
        assert jcs_rejected, "JCS debe rechazar enteros > 2^53 - 1"

        # 5b. gst: emitir y verificar sobre GST v2 + rechazo de replay
        # (usa HybridSigner cuando cryptography>=47 con ML-DSA está disponible, como en CI;
        # en entornos stdlib puros sin cryptography, valida ReplayGuard y gst_v2_message)
        has_mldsa = False
        try:
            import cryptography.hazmat.primitives.asymmetric.mldsa  # noqa: F401
            has_mldsa = True
        except Exception:
            has_mldsa = False

        guard = gst_env.ReplayGuard()
        if has_mldsa:
            signer = gst_adapters.HybridSigner(
                seed_classical=bytes(range(32)),
                seed_pqc=bytes(range(32, 64)),
            )
            attacker = gst_adapters.HybridSigner(
                seed_classical=bytes(range(64, 96)),
                seed_pqc=bytes(range(96, 128)),
            )
            registry = gst_v2.KeyRegistry()
            registry.register_signer(issuer="sat-test", kid="sat-k1", signer=signer)
            sqlite_store = gst_v2.SQLiteReplayStore(":memory:")

            env = gst_v2.create(
                parsed, signer, event_hash="sha256:" + "ab" * 32,
                kid="sat-k1", issuer="sat-test", seq=1,
            )
            res1 = gst_v2.verify(dict(env), trust_store=registry, replay_store=sqlite_store)
            assert res1.overall_trusted is True
            assert res1.identity.key_status == "ACTIVE"
            assert res1.identity.replay_status == "OK"
            assert res1.temporal.clock_state == "UNKNOWN"

            # Replay exacto rechazado por SQLiteReplayStore
            res_replay = gst_v2.verify(dict(env), trust_store=registry, replay_store=sqlite_store)
            assert res_replay.overall_trusted is False
            assert res_replay.identity.replay_status == "REPLAY"

            # Clave autofirmada suplantando issuer/kid rechazada por KeyRegistry
            spoof = gst_v2.create(
                parsed, attacker, event_hash="sha256:" + "ab" * 32,
                kid="sat-k1", issuer="sat-test", seq=2,
            )
            res_spoof = gst_v2.verify(dict(spoof), trust_store=registry, replay_store=sqlite_store)
            assert res_spoof.crypto.valid is True
            assert res_spoof.identity.valid is False
            assert res_spoof.identity.key_status == "MISMATCH"
            assert res_spoof.overall_trusted is False
            sqlite_store.close()
        else:
            # Validación estructural GST v2 + ReplayGuard sin dependencia externa
            msg = gst_env.gst_v2_message({"gst_version": "2.0", "ins": ins, "seq": 1})
            assert msg.startswith(gst_env.GST_V2_DOMAIN)
            ok_g1, _ = guard.check_and_record("sat-k1", "nonce-1", 1, ins)
            assert ok_g1 is True
            ok_g2, reason_g2 = guard.check_and_record("sat-k1", "nonce-1", 1, ins)
            assert ok_g2 is False and "replay" in reason_g2

        # 6. interop: convertir a RFC 3339 y vuelta
        rfc = interop_profiles.instant_to_rfc3339(ins)
        assert rfc.endswith("Z")
        assert interop_profiles.instant_from_rfc3339(rfc) == ins

        print("PYTHON_SATELLITE_INTEGRATION_OK")
    """)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(assembled_workspace / "src")
    env["ASSEMBLED_SRC"] = str(assembled_workspace / "src")
    env["FORBIDDEN_REPO"] = str(REPO)
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=assembled_workspace, env=env, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PYTHON_SATELLITE_INTEGRATION_OK" in proc.stdout


def test_assembled_js_integration(assembled_workspace: Path) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")

    mjs = assembled_workspace / "js_integration.mjs"
    mjs.write_text(textwrap.dedent("""\
        import assert from "node:assert/strict";
        import { dayIndexFromGregorian, toGerarion, instantFromParts } from "./web/engine/core.mjs";
        import { taiMinusUTC, instantFromUnix, unixFromInstant, taiUtcTableInfo } from "./web/engine/tcj-tai.mjs";
        import { gutiFromDayIndex, gutiToDayIndex } from "./web/engine/guti.mjs";

        const di = dayIndexFromGregorian(2026, 5, 23);
        assert.equal(di, 741871);
        const gd = toGerarion(di);
        assert.equal(gd.year, 2031);
        assert.equal(gd.month, 3);
        assert.equal(gd.day, 8);
        assert.equal(gd.weekday, "Trustdyia");

        const ins = instantFromParts(di, 9, 30, 0);
        assert.equal(ins, BigInt(di) * 86400n + 9n * 3600n + 30n * 60n);

        assert.equal(taiUtcTableInfo().tableVersion, "IERS-C-2026.1");
        assert.equal(taiMinusUTC(1779528600), 37);
        assert.equal(unixFromInstant(instantFromUnix(1779528600)), 1779528600n);

        const greg = gutiFromDayIndex(di, "greg");
        assert.deepEqual(greg.fields, { year: 2026, month: 5, day: 23 });
        assert.equal(gutiToDayIndex("greg", greg.fields), di);

        console.log("JS_SATELLITE_INTEGRATION_OK");
    """), encoding="utf-8")

    proc = subprocess.run(
        [node, str(mjs)],
        cwd=assembled_workspace, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "JS_SATELLITE_INTEGRATION_OK" in proc.stdout
