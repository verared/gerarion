# -*- coding: utf-8 -*-
"""Prueba E2E del calculador web Gerarion con Playwright (Chromium headless)."""
import re
import sys

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8123/index.html"
results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), "-", name, ("| " + extra if extra and not cond else ""))


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE)
    page.wait_for_timeout(600)

    # 1. Sin errores de JS al cargar
    check("carga sin errores JS", not errors, "; ".join(errors[:3]))

    # 2. Self-test de vectores en el navegador
    st = page.text_content("#selftest") or ""
    check("self-test: 22 vectores pasan", "22 pasan, 0 fallan" in st, st[:120])

    # 3. Rel vivo: formato canónico completo
    clock = page.text_content("#now-gero") or ""
    check(
        "reloj vivo: formato AAAAYY-MM-DD-X-HH:MM:SS-CC-TCJ+0",
        re.match(r"^\d{4}(DY|AY)-\d{2}-\d{2}-[SLMATVB]-\d{2}:\d{2}:\d{2}-(SC|LC)-TCJ\+0$",
                 clock.strip() if clock else "") is not None,
        repr(clock),
    )
    details = page.text_content("#now-details") or ""
    check("reloj vivo: detalles (día, semana, mes, ciclo)",
          all(k in details for k in ("día", "ciclo")), repr(details))

    # 4. Gregoriano -> Gerarion: ancla de errata E-01 (2026-03-17 = 2031DY-01-01-S)
    page.fill("#greg-date", "2026-03-17")
    page.click("#form-greg button[type=submit]")
    out = page.text_content("#output-greg") or ""
    check("greg->gero: 2026-03-17 => 2031DY-01-01-S", "2031DY-01-01-S" in out, out)
    check("greg->gero: nombre del día Soludyia", "Soludyia" in out, out)

    # 4b. Tempalum de Gran Tempalum: 2030-03-14 = 2034DY-00-07-M (Nuvivid III)
    page.fill("#greg-date", "2030-03-14")
    page.click("#form-greg button[type=submit]")
    out2 = page.text_content("#output-greg") or ""
    check("greg->gero: 2030-03-14 => 2034DY-00-07-M (Tempalum GT)",
          "2034DY-00-07-M" in out2 and "Nuvivid III" in out2, out2)

    # 5. Gerarion -> Gregoriano: vector completo regla 7
    page.fill("#gero-ts", "2031DY-03-08-T-09:30:00-SC-TCJ+0")
    page.click("#form-gero button[type=submit]")
    out3 = page.text_content("#output-gero") or ""
    check("gero->greg: vector regla 7 canónico", "2031DY-03-08-T-09:30:00-SC-TCJ+0" in out3, out3)
    check("gero->greg: gregoriano 2026-05-23", "2026-05-23" in out3, out3)

    # 5b. Letra de día equivocada => flag weekday_corrected
    page.fill("#gero-ts", "2031DY-03-08-B-09:30:00-SC-TCJ+0")
    page.click("#form-gero button[type=submit]")
    out4 = page.text_content("#output-gero") or ""
    check("gero->greg: letra incorrecta => nota weekday_corrected",
          "weekday_corrected" in out4 and "-T-" in out4, out4)

    # 5c. Sello inválido => mensaje de error con clase .error
    page.fill("#gero-ts", "2031DY-13-08-T")
    page.click("#form-gero button[type=submit]")
    out5 = page.text_content("#output-gero") or ""
    cls = page.get_attribute("#output-gero", "class") or ""
    check("gero->greg: inválido => error visible con clase .error",
          "Sello inválido" in out5 and "error" in cls, out5 + " | class=" + cls)

    # 5d. Tempalum en año no-GT => error GERO_ETEMPALUM
    page.fill("#gero-ts", "2031DY-00-07-T")
    page.click("#form-gero button[type=submit]")
    out6 = page.text_content("#output-gero") or ""
    check("gero->greg: Tempalum día 7 en año no-GT => GERO_ETEMPALUM",
          "GERO_ETEMPALUM" in out6, out6)

    browser.close()

fails = [r for r in results if not r[1]]
print("\n=> %d checks, %d fallan" % (len(results), len(fails)))
sys.exit(1 if fails or errors else 0)
