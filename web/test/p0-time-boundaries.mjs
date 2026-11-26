// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
import assert from 'node:assert/strict';
import test from 'node:test';
import { canonicalOf, compactOf, instantFromParts, instantParts, parse } from '../engine/core.mjs';
import { instantFromUnix, taiMinusUTCChecked, taiUtcTableInfo, unixFromInstant } from '../engine/tcj-tai.mjs';

test('negative instants use the previous civil day', () => {
  for (const value of [-86401n, -86400n, -1n, 0n, 1n]) {
    const { dayIndex, hour, minute, second } = instantParts(value);
    assert.equal(instantFromParts(dayIndex, hour, minute, second), value);
  }
  assert.equal(instantParts(-1n).dayIndex, -1);
});

test('constructor enforces signed int64 after offset adjustment', () => {
  const hi = (1n << 63n) - 1n;
  const lo = -(1n << 63n);
  for (const [value, accepted] of [[hi, true], [lo, true], [hi + 1n, false], [lo - 1n, false]]) {
    const remainder = Number((value % 86400n + 86400n) % 86400n);
    const day = (value - BigInt(remainder)) / 86400n - 1n;
    const build = () => instantFromParts(day, Math.floor(remainder / 3600), Math.floor(remainder / 60) % 60, remainder % 60, -86400);
    if (accepted) assert.equal(build(), value);
    else assert.throws(build, /GERO_ERANGE/);
  }
});

test('both spellings round-trip at ±24 hours but reject nonzero minutes at the limit', () => {
  const base = '2031DY-03-08-T-09:30:00-SC-TCJ';
  for (const sign of ['+', '-']) {
    const d = parse(base + sign + '24');
    assert.equal(d.offsetSeconds, sign === '+' ? 86400 : -86400);
    assert.equal(canonicalOf(parse(compactOf(d))), base + sign + '24');
    assert.throws(() => parse(base + sign + '24:01'), /GERO_EINVAL/);
    assert.throws(() => parse(compactOf(d) + '01'), /GERO_EINVAL/);
  }
});

test('TAI table horizon and positive leap-second gap are explicit', () => {
  const boundary = Date.UTC(2027, 4, 1) / 1000;
  assert.equal(taiUtcTableInfo().validUntilUnix, boundary);
  assert.equal(taiMinusUTCChecked(boundary).extrapolated, false);
  assert.equal(taiMinusUTCChecked(boundary + 1).extrapolated, true);
  const before = instantFromUnix(1483228799n);
  const after = instantFromUnix(1483228800n);
  assert.equal(after - before, 2n);
  assert.equal(unixFromInstant(before), 1483228799n);
  assert.equal(unixFromInstant(after), 1483228800n);
  assert.throws(() => unixFromInstant(before + 1n), /GERO_E3339/);
});
