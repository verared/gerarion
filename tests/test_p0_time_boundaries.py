# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
from datetime import datetime, timezone

import pytest

from gerarion.core.calendar import instant_from_parts, instant_parts
from gerarion.gts.clock import ClockAnchorStore, ClockReading, ClockState, TrustedClock
from gerarion.tcj import tai


def test_negative_second_roundtrip():
    date, hour, minute, second = instant_parts(-1)
    assert date.day_index == -1
    assert (hour, minute, second) == (23, 59, 59)
    assert instant_from_parts(date.day_index, hour, minute, second) == -1


def test_holdover_cannot_extend_last_verified_horizon(tmp_path):
    ns = 1_000_000_000
    path = str(tmp_path / 'clock.json')
    clock = TrustedClock(store=ClockAnchorStore(path))

    def reading(dt_ns, authenticated=False):
        elapsed, nanos = divmod(dt_ns, ns)
        return ClockReading(instant=100_000 + elapsed, nanos=nanos, source_id='fixture',
                            uncertainty_ns=1 if authenticated else -1,
                            monotonic_ns=ns + dt_ns, authenticated=authenticated)

    assert clock.classify(reading(0, True)).state is ClockState.VERIFIED
    assert clock.classify(reading(3500 * ns)).state is ClockState.HOLDOVER
    clock = TrustedClock(store=ClockAnchorStore(path))
    assert clock.classify(reading(3600 * ns)).state is ClockState.HOLDOVER
    assert clock.classify(reading(3600 * ns + 1)).state is ClockState.UNVERIFIED
    assert clock.classify(reading(7000 * ns)).state is ClockState.UNVERIFIED


def test_tai_inverse_has_no_unix_label_for_positive_leap_second():
    boundary = int(datetime(2027, 5, 1, tzinfo=timezone.utc).timestamp())
    assert tai.tai_utc_table_info()['valid_until_unix'] == boundary
    assert tai.tai_minus_utc_checked(boundary) == (37, False)
    assert tai.tai_minus_utc_checked(boundary + 1) == (37, True)
    before = tai.instant_from_unix(1_483_228_799)
    after = tai.instant_from_unix(1_483_228_800)
    assert after - before == 2
    assert tai.unix_from_instant(before) == 1_483_228_799
    assert tai.unix_from_instant(after) == 1_483_228_800
    with pytest.raises(ValueError, match='GERO_E3339'):
        tai.unix_from_instant(before + 1)
