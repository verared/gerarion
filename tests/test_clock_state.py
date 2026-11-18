# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Pruebas de la máquina de estados de confianza de reloj (spec §6.3).

Cubre: VERIFIED → HOLDOVER → UNVERIFIED → REJECTED, separación estricta
entre medición de duraciones (monotónico) y tiempo absoluto, ancla
persistida (anti-rollback entre procesos) y metadatos de la tabla
TAI − UTC versionada.
"""

import pytest

from gerarion.clock import (
    ClockAnchorStore,
    ClockPolicy,
    ClockReading,
    ClockState,
    TrustedClock,
)
from gerarion import tai


def reading(instant, *, nanos=0, state=ClockState.UNVERIFIED, source_id="gps",
            uncertainty_ns=-1, monotonic_ns=0):
    return ClockReading(instant=instant, nanos=nanos, state=state,
                        source_id=source_id, uncertainty_ns=uncertainty_ns,
                        monotonic_ns=monotonic_ns)


def test_lectura_con_cota_valida_es_verified():
    clock = TrustedClock()
    r = clock.classify(reading(1_000_000_000, uncertainty_ns=500_000,
                               monotonic_ns=10**9))
    assert r.state == ClockState.VERIFIED
    assert clock.store.anchor.state == ClockState.VERIFIED


def test_lectura_fuera_de_la_cota_sin_ancla_es_unverified():
    clock = TrustedClock()
    r = clock.classify(reading(1_000_000_000, uncertainty_ns=-1,
                               monotonic_ns=10**9))
    assert r.state == ClockState.UNVERIFIED


def test_lectura_fuera_de_cota_en_estricto_es_rejected():
    clock = TrustedClock(policy=ClockPolicy(strict=True))
    r = clock.classify(reading(1_000_000_000, uncertainty_ns=-1,
                               monotonic_ns=10**9))
    assert r.state == ClockState.REJECTED


def test_holdover_extrapolado_dentro_de_ventana():
    clock = TrustedClock()
    ancla = clock.classify(reading(1_000_000_000, uncertainty_ns=100_000,
                                   monotonic_ns=10**9))
    assert ancla.state == ClockState.VERIFIED
    # Fuente perdida (cota desconocida) pero reloj monotónico avanza 60 s
    # y la lectura local es coherente con la extrapolación del ancla.
    r = clock.classify(reading(1_000_000_060, uncertainty_ns=-1,
                               monotonic_ns=10**9 + 60_000_000_000))
    assert r.state == ClockState.HOLDOVER
    assert r.source_id.endswith("+holdover")
    # La incertidumbre crece respecto del ancla (deriva declarada)…
    assert r.uncertainty_ns > ancla.uncertainty_ns


def test_holdover_con_reloj_local_descuadrado_es_unverified():
    clock = TrustedClock()
    clock.classify(reading(1_000_000_000, uncertainty_ns=100_000,
                           monotonic_ns=10**9))
    # Lectura 5 años por encima de la extrapolación: incoherente.
    r = clock.classify(reading(1_000_000_000 + 5 * 365 * 86400,
                               uncertainty_ns=-1,
                               monotonic_ns=10**9 + 60_000_000_000))
    assert r.state == ClockState.UNVERIFIED


def test_holdover_mas_alla_de_la_ventana_es_unverified():
    clock = TrustedClock(ClockPolicy(max_holdover_s=3600))
    clock.classify(reading(1_000_000_000, uncertainty_ns=100_000,
                           monotonic_ns=10**9))
    r = clock.classify(reading(1_000_390_000, uncertainty_ns=-1,
                               monotonic_ns=10**9 + 390_000 * 10**9))
    assert r.state == ClockState.UNVERIFIED


def test_rollback_reloj_rechazado():
    clock = TrustedClock()
    clock.classify(reading(1_000_000_000, uncertainty_ns=100_000,
                           monotonic_ns=10**9))
    r = clock.classify(reading(999_000_000, uncertainty_ns=100_000,
                               monotonic_ns=2 * 10**9))
    assert r.state == ClockState.REJECTED


def test_ciclo_completo_verified_holdover_unverified_rejected():
    clock = TrustedClock(ClockPolicy(max_holdover_s=3600))
    # 1) VERIFIED
    r1 = clock.classify(reading(1_000_000_000, uncertainty_ns=100_000,
                                monotonic_ns=10**9))
    assert r1.state == ClockState.VERIFIED
    # 2) HOLDOVER (60 s, coherente)
    r2 = clock.classify(reading(1_000_000_060, monotonic_ns=10**9 + 60_000_000_000))
    assert r2.state == ClockState.HOLDOVER
    # 3) UNVERIFIED (ventana agotada, incoherencia con la extrapolación)
    r3 = clock.classify(reading(1_060_000_000, monotonic_ns=10**9 + 61_000_000_000))
    assert r3.state == ClockState.UNVERIFIED
    # 4) REJECTED (retroceso sobre la línea de tiempo absoluta)
    r4 = clock.classify(reading(999_999_999, uncertainty_ns=100_000,
                                monotonic_ns=10**9 + 62_000_000_000))
    assert r4.state == ClockState.REJECTED


def test_ancla_persistida_habilita_holdover_y_detecta_rollback(tmp_path):
    path = str(tmp_path / "ancla.json")
    clock = TrustedClock(store=ClockAnchorStore(path))
    clock.classify(reading(1_000_000_000, uncertainty_ns=100_000,
                           monotonic_ns=10**9))
    # Proceso "nuevo": carga del archivo.
    clock2 = TrustedClock(store=ClockAnchorStore(path))
    assert clock2.store.anchor is not None
    r = clock2.classify(reading(1_000_000_060, monotonic_ns=10**9 + 60_000_000_000))
    assert r.state == ClockState.HOLDOVER
    r2 = clock2.classify(reading(500_000_000, uncertainty_ns=100_000,
                                 monotonic_ns=10**9 + 61_000_000_000))
    assert r2.state == ClockState.REJECTED


def test_carga_no_eleva_calidad_de_lectura(tmp_path):
    path = str(tmp_path / "ancla.json")
    clock = TrustedClock(store=ClockAnchorStore(path))
    clock.classify(reading(1_000_000_000, uncertainty_ns=100_000,
                           monotonic_ns=10**9))
    clock2 = TrustedClock(store=ClockAnchorStore(path))
    # Sin cota y sin avance monotónico coherente nunca sale VERIFIED.
    r = clock2.classify(reading(1_000_000_000, monotonic_ns=10**9))
    assert r.state != ClockState.VERIFIED


def test_nanos_invalidos_en_lectura_rechazados():
    with pytest.raises(Exception):
        ClockReading(instant=1_000_000_000, nanos=1_000_000_000)
    with pytest.raises(Exception):
        ClockReading(instant=1_000_000_000, nanos=-1)


def test_monotonico_no_es_etiqueta_absoluta():
    """elapsed_ns mide duraciones con el monotónico, nunca restando sellos."""
    assert TrustedClock.elapsed_ns(TrustedClock.elapsed_ns(0) * -1) >= 0
    with pytest.raises(Exception):
        reading("no-int")


def test_lectura_del_so_nunca_verified_por_defecto():
    clock = TrustedClock()
    r = clock.classify(TrustedClock.now_reading("so-wall"))
    assert r.state != ClockState.VERIFIED


def test_tai_utc_tabla_metadatos():
    info = tai.tai_utc_table_info()
    assert info["table_version"] == "IERS-C-2026.1"
    assert info["valid_until_unix"] == 1_799_808_000
    assert info["smear_policy"] == "reject"


def test_tai_utc_coherente_con_tabla_y_vigencia():
    base, extra = tai.tai_minus_utc_checked(1_700_000_000)
    assert base == tai.tai_minus_utc(1_700_000_000) and extra is False
    _, extra2 = tai.tai_minus_utc_checked(tai.TAI_UTC_VALID_UNTIL_UNIX)
    assert extra2 is False
    _, extra3 = tai.tai_minus_utc_checked(tai.TAI_UTC_VALID_UNTIL_UNIX + 1)
    assert extra3 is True
