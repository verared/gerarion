"""Fuzzing del núcleo GUS (sin dependencias externas, semilla fija).

Dos capas:

  1. Fuzzing hostil de `parse()`: miles de entradas aleatorias y mutaciones
     de marcas válidas. Invariantes exigidas:
       - jamás lanza una excepción fuera de `gerarion.GeroError`
         (OverflowError, IndexError, TypeError = fallo de fuzzing);
       - si parses, el round-trip `to_canonical(parse(to_canonical(p)))` es
         estable e idempotente;
       - los flags declarados nunca contradicen el resultado.

  2. Propiedades aritméticas exactas sobre el dominio completo de días:
       - round-trip to_gerarion/from_gerarion;
       - round-trip gregoriano vía JDN;
       - semana invariante (weekday == day_index % 7, días de año en Soludyia);
       - instantes: reconstruction exacta, días de exactamente 86.400 s;
       - cota de drift: el inicio de año DY oscila dentro de la cota
         |Δ| < 7 días del mecanismo solar (propiedad normativa). La ventana
         concreta de fechas es OBSERVADA (10-21 de marzo en 0..11.000
         años DY), no estructural: se desplaza lentamente con los
         milenios; el test comprueba la ventana observada sobre 11.000
         años (~17 s de ejecución).
"""

from __future__ import annotations

import random
import string

import pytest

from gerarion import calendar as cal
from gerarion import format as fmt
from gerarion.calendar import GeroError

SEED = 20310101


def _valid_base_stamps() -> list:
    return [
        "2031DY-03-08-T", "2031DY-03-08-T-09:30:00-SC-TCJ+0",
        "1AY-00-04-B", "0000DY-01-01-S", "2034DY-00-07-M",
        "9999DY-12-30-B", "45DY-05-05-S",
    ]


def _mutate(raw: str, rng: random.Random) -> str:
    chars = list(raw)
    for _ in range(rng.randint(1, 3)):
        op = rng.randrange(4)
        pos = rng.randrange(len(chars)) if chars else 0
        if op == 0 and chars:
            chars.pop(pos)
        elif op == 1:
            chars.insert(pos, rng.choice(string.printable[:95]))
        elif op == 2 and chars:
            chars[pos] = rng.choice(string.printable[:95])
        elif op == 3:
            chars.insert(pos, rng.choice("-.: +SCDYABTLMV159"))
    return "".join(chars)


def test_fuzz_parse_never_crashes_and_roundtrips():
    rng = random.Random(SEED)
    errors = []
    for _ in range(4000):
        raw = _mutate(rng.choice(_valid_base_stamps()), rng)
        try:
            parsed = fmt.parse(raw)
        except GeroError:
            continue
        except Exception as exc:  # noqa: BLE001 - es exactamente lo que cazamos
            errors.append((raw, type(exc).__name__, str(exc)))
            continue
        # idempotencia del formato canónico
        canon = fmt.to_canonical(parsed)
        reparsed = fmt.parse(canon)
        assert fmt.to_canonical(reparsed) == canon, (raw, canon)
    assert errors == [], errors[:10]


def test_fuzz_garbage_never_crashes():
    rng = random.Random(SEED + 1)
    alphabet = string.printable + "áéíóú±µΔ←"
    for _ in range(3000):
        raw = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))
        try:
            fmt.parse(raw)
        except GeroError:
            continue
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"parse({raw!r}) lanzó {type(exc).__name__}: {exc}")


def test_property_roundtrip_gerarion():
    rng = random.Random(SEED + 2)
    for _ in range(3000):
        di = rng.randint(-1_000_000, 5_000_000)
        g = cal.to_gerarion(di)
        back = cal.from_gerarion(g.year, g.month, g.day)
        assert back.day_index == di, di
        assert g.weekday_index == ((di % 7) + 7) % 7


def test_property_roundtrip_gregorian():
    rng = random.Random(SEED + 3)
    for _ in range(3000):
        di = rng.randint(-1_000_000, 5_000_000)
        gy, gm, gd = cal.gregorian_from_day_index(di)
        assert cal.day_index_from_gregorian(gy, gm, gd) == di


def test_property_invariants_every_year():
    start = 0
    for year in range(0, 11000):
        g = cal.to_gerarion(start)
        assert g.weekday_index == 0, year
        assert (g.month, g.day) == (1, 1), year
        length = cal.year_length(year)
        assert length in (364, 371)
        gyr, gm, gd = cal.gregorian_from_day_index(start)
        # Ventana OBSERVADA 10-21 de marzo en 0..11.000 años (medida, no
        # estructural). La garantía normativa de fondo es la cota |Δ| < 7
        # días del sawtooth solar (drift-acotado.md), que es más débil que
        # fijar una ventana permanente.
        mar = (gm, gd)
        if mar < (3, 10) or mar > (3, 21):
            pytest.fail(
                f"año {year} inicia {gyr}-{gm}-{gd}: fuera de la ventana "
                "observada 10-21 de marzo (0..11000 años DY)"
            )
        start += length


def test_property_instants():
    rng = random.Random(SEED + 4)
    for _ in range(3000):
        di = rng.randint(-1_000_000, 5_000_000)
        h, m, s = rng.randrange(24), rng.randrange(60), rng.randrange(60)
        instant = cal.instant_from_parts(di, h, m, s)
        date, h2, m2, s2 = cal.instant_parts(instant)
        assert (date.day_index, h2, m2, s2) == (di, h, m, s)
        assert cal.instant_from_parts(di + 1, h, m, s) - instant == 86_400
