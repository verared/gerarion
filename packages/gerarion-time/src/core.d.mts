// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
/**
 * Declaración tipada del núcleo determinista GUS/TCJ.
 *
 * La implementación (`core.mjs`) NUNCA se duplica a mano: el build la
 * copia verbatim desde `web/engine/core.mjs` (fuente única de verdad).
 * Este archivo solo declara su superficie pública para consumidores TS.
 */

export declare const ORIGIN_JDN: 1719313;
export declare const SOLAR_DELTA_UD: 1242190;
export declare const MONTH_BLOCK_DAYS: 360;
export declare const SECS_PER_DAY: 86400;
export declare const NANOS_MAX: 999999999;

export declare const WEEKDAYS: readonly string[];

export interface GerarionDate {
  year: number;
  month: number;
  day: number;
  dayIndex: number;
  weekdayIndex?: number;
  weekday?: string;
  abbr: string;
  cycle?: string;
  hour?: number;
  minute?: number;
  second?: number;
  offset?: number;
  offsetSeconds?: number;
  flags?: string[];
  [k: string]: unknown;
}

export interface ParsedStamp extends GerarionDate {
  nanos?: number;
  instant?: bigint;
}

export declare class GeroError extends Error {
  readonly code?: string;
}

export declare function isGranTempalum(year: number): boolean;
export declare function yearLength(year: number): number;
export declare function tempalumDays(year: number): number;
export declare function jdn(year: number, month: number, day: number): number;
export declare function jdnToGregorian(j: number): GerarionDate;
export declare function dayIndexFromGregorian(
  year: number,
  month: number,
  day: number,
): number;
export declare function gregorianFromDayIndex(dayIndex: number): GerarionDate;
export declare function yearStartDayIndex(year: number): number;
export declare function toGerarion(dayIndex: number): GerarionDate;
export declare function fromGerarion(
  year: number,
  month: number,
  day: number,
): GerarionDate;
export declare function normalize(raw: string): string;
export declare function parse(
  raw: string,
  opts?: { strictWeekday?: boolean },
): ParsedStamp;
export declare function quickVerify(raw: string): boolean;
export declare function validateNanos(nanos: number): number;
export declare function nanosFromFraction(digits: string | number): number;
export declare function instantFromParts(
  dayIndex: number | bigint,
  hour?: number,
  minute?: number,
  second?: number,
  offsetSeconds?: number,
): bigint;
export declare function instantParts(instant: bigint | number): GerarionDate & {
  instant: bigint;
};
export declare function partsFromInstant(
  instant: bigint | number,
  offsetSeconds?: number,
): GerarionDate;
export declare function cycleOf(hour: number): "SC" | "LC";
export declare function formatOffset(offsetSeconds: number): string;
export declare function canonicalOf(d: GerarionDate): string;
export declare function compactOf(d: GerarionDate): string;
export declare function tempalumName(date: GerarionDate): string | null;
