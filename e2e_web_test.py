# -*- coding: utf-8 -*-
"""Prueba E2E del portal web Gerarion con Playwright (Chromium headless).

Estructura esperada (web-ux): (1) traductor de fechas, (2) conversiones
rápidas plegadas, (3) reloj "Ahora en Gerarion", (4) calendario del mes,
(5) distancia entre fechas, (6) verificación en el navegador.
"""
import re
import sys

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8123/index.html"
results = []
EXTERNAL = []  # peticiones de red que no sean localhost (debe quedar vacía)


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), "-", name, ("| " + extra if extra and not cond else ""))


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on(
        "request",
        lambda r: EXTERNAL.append(r.url) if "localhost" not in r.url else None,
    )
    page.goto(BASE)
    page.wait_for_timeout(600)

    # 1. Sin errores de JS al cargar
    check("carga sin errores JS", not errors, "; ".join(errors[:3]))

    # 1b. Cero peticiones externas (sin CDN, sin analítica, sin fuentes remotas)
    check("cero peticiones externas", not EXTERNAL, "; ".join(EXTERNAL[:3]))

    # 2. Self-test de vectores en el navegador
    page.eval_on_selector("#verificacion details", "el => el.setAttribute('open', 'open')")
    st = page.text_content("#selftest") or ""
    check("self-test: 22 vectores pasan", "22 pasan, 0 fallan" in st, st[:120])

    # 3. El traductor es la primera sección de <main>
    first_section = page.evaluate("document.querySelector('main section').id") if page.evaluate(
        "document.querySelector('main section')"
    ) else ""
    check("traductor es la primera sección", first_section == "traductor", first_section)

    # 3b. Reloj: formato canónico completo (por defecto TCJ+0/UTC)
    clock = page.text_content("#now-gero") or ""
    check(
        "reloj: formato AAAAYY-MM-DD-X-HH:MM:SS-CC-TCJ+0",
        re.match(r"^\d{4}(DY|AY)-\d{2}-\d{2}-[SLMATVB]-\d{2}:\d{2}:\d{2}-(SC|LC)-TCJ\+0$",
                 clock.strip() if clock else "") is not None,
        repr(clock),
    )
    details = page.text_content("#now-details") or ""
    check("reloj: detalles (día, semana, mes, ciclo)",
          all(k in details for k in ("día", "ciclo")), repr(details))

    # 4. Conversiones rápidas: abrir el details y usar ambos formularios
    page.locator("#conversiones > summary").click()
    page.wait_for_timeout(150)

    page.fill("#greg-date", "2026-03-17")
    page.click("#form-greg button[type=submit]")
    out = page.text_content("#output-greg") or ""
    check("greg->gero: 2026-03-17 => 2031DY-01-01-S", "2031DY-01-01-S" in out, out)
    check("greg->gero: nombre del día Soludyia", "Soludyia" in out, out)

    page.fill("#greg-date", "2030-03-14")
    page.click("#form-greg button[type=submit]")
    out2 = page.text_content("#output-greg") or ""
    check("greg->gero: 2030-03-14 => 2034DY-00-07-M (Tempalum GT)",
          "2034DY-00-07-M" in out2 and "Nuvivid III" in out2, out2)

    page.fill("#gero-ts", "2031DY-03-08-T-09:30:00-SC-TCJ+0")
    page.click("#form-gero button[type=submit]")
    out3 = page.text_content("#output-gero") or ""
    check("gero->greg: vector regla 7 canónico", "2031DY-03-08-T-09:30:00-SC-TCJ+0" in out3, out3)
    check("gero->greg: gregoriano 2026-05-23", "2026-05-23" in out3, out3)

    page.fill("#gero-ts", "2031DY-03-08-B-09:30:00-SC-TCJ+0")
    page.click("#form-gero button[type=submit]")
    out4 = page.text_content("#output-gero") or ""
    check("gero->greg: letra incorrecta => weekday_corrected",
          "weekday_corrected" in out4 and "-T-" in out4, out4)

    page.fill("#gero-ts", "2031DY-13-08-T")
    page.click("#form-gero button[type=submit]")
    out5 = page.text_content("#output-gero") or ""
    cls = page.get_attribute("#output-gero", "class") or ""
    check("gero->greg: inválido => error con clase .error",
          "Sello inválido" in out5 and "error" in cls, out5 + " | class=" + cls)

    page.fill("#gero-ts", "2031DY-00-07-T")
    page.click("#form-gero button[type=submit]")
    out6 = page.text_content("#output-gero") or ""
    check("gero->greg: Tempalum día 7 en año no-GT => GERO_ETEMPALUM",
          "GERO_ETEMPALUM" in out6, out6)

    # 5. Traductor universal: 12000AY -> cuadrícula de 10
    page.fill("#gero-ts", "12000AY-01-01-S")
    page.click("#form-gero button[type=submit]")
    tiles = page.locator("#rosetta-grid .cal-tile").count()
    check("rosetta: cuadrícula de 10 calendarios", tiles == 10, f"tiles={tiles}")
    grid_text = page.text_content("#rosetta-grid") or ""
    check("rosetta: 12000AY-01-01-S en la tarjeta GUS", "12000AY-01-01-S" in grid_text, grid_text[:200])
    check("rosetta: gregoriano de 12000AY-01-01 = -12005-03-21", "-12005-03-21" in grid_text, grid_text[:300])
    check("rosetta: maya presente (cuenta larga)", ".0." in grid_text, grid_text[:200])

    # 6. Presets de 1 clic
    page.click("#presets button:has-text('Nuvivid VII')")
    page.wait_for_timeout(150)
    grid_text = page.text_content("#rosetta-grid") or ""
    check("preset Nuvivid VII: tarjeta GUS = 0001AY-00-11-B", "0001AY-00-11-B" in grid_text, grid_text[:200])

    page.click("#presets button:has-text('Cruxyphi')")
    page.wait_for_timeout(150)
    grid_text = page.text_content("#rosetta-grid") or ""
    check("preset Cruxyphi: tarjeta GUS = 2031DY-01-12-T", "2031DY-01-12-T" in grid_text, grid_text[:200])

    # 7. Calculadora de intervalos cruzando eras AY -> DY
    page.fill("#int-a", "0001AY-00-11-B")
    page.fill("#int-b", "2031DY-01-01-S")
    page.click("#form-int button[type=submit]")
    out7 = page.text_content("#output-int") or ""
    check("intervalos AY->DY: 741.805 días", "741.805" in out7.replace("\u202f", ".") or "741805" in out7, out7)
    check("intervalos AY->DY: semanas exactas (741805/7)", "105.97" in out7 or "10597" in out7.replace(".", ""), out7)
    check("intervalos AY->DY: segundos SI", "64.091.952.000" in out7 or "64091952000" in out7, out7)

    # 8. Traductor universal: maya directa
    page.click("#uni-modes button:has-text('Maya')")
    page.fill("#uni-in", "13.0.14.1.19")
    page.click("#form-uni button[type=submit]")
    grid_text = page.text_content("#rosetta-grid") or ""
    check("traductor maya: 13.0.14.1.19 -> cuadrícula", "day_index 742049" in (page.text_content("#rosetta-status") or ""), grid_text[:300])

    # 8b. Mensaje de error con formato esperado (nunca "Error" a secas)
    page.fill("#uni-in", "basura@@@")
    page.click("#form-uni button[type=submit]")
    err_txt = page.text_content("#rosetta-status") or ""
    check("error de entrada incluye formato esperado y ejemplo",
          "Formato esperado" in err_txt and "ej.:" in err_txt, err_txt)

    # 9. Enlace compartible: round-trip de #cal=...&d=...
    page.click("#uni-modes button:has-text('Gregoriano')")
    page.fill("#uni-in", "2026-05-23")
    page.click("#form-uni button[type=submit]")
    page.wait_for_timeout(150)
    share_hash = page.evaluate("location.hash")
    check("enlace compartible: hash escrito al traducir",
          share_hash.startswith("#cal=greg&d=2026-05-23"), share_hash)
    page2 = browser.new_page()
    page2.goto(BASE + "#cal=greg&d=2026-05-23")
    page2.wait_for_timeout(400)
    grid2 = page2.text_content("#rosetta-grid") or ""
    check("enlace compartible: round-trip reproduce el resultado", "2031DY-03-08-T" in grid2, grid2[:200])
    page2.close()

    # 10. Detalles plegables: abiertos/cerrados con teclado; métricas vivas
    summary = page.locator("#conversiones > summary")
    d0 = page.get_attribute("#conversiones", "open") is not None
    summary.press("Enter")
    d1 = page.get_attribute("#conversiones", "open") is not None
    summary.press("Enter")
    d2 = page.get_attribute("#conversiones", "open") is not None
    check("details: abre y cierra con teclado (Enter)", (d1 != d0) and (d2 == d0),
          f"estado inicial={d0}, tras 1er Enter={d1}, tras 2º Enter={d2}")
    di_now = (page.text_content("#now-dayindex") or "").strip()
    check("métricas técnicas se actualizan con el bloque cerrado", re.match(r"^-?\d+$", di_now) is not None, repr(di_now))

    # 11. Tema: el toggle alterna data-theme (claro reforzado <-> estándar)
    page.click("#theme-toggle")
    theme = page.get_attribute("html", "data-theme") or ""
    check("tema: toggle alterna a claro", theme == "light", repr(theme))
    page.click("#theme-toggle")
    theme = page.get_attribute("html", "data-theme") or ""
    check("tema: toggle vuelve a estándar", theme == "", repr(theme))

    # 12. Copiar reloj: toast de confirmación
    page.click("#now-copy")
    page.wait_for_timeout(250)
    toast_visible = page.locator(".toast.show").count() > 0
    toast_text = (page.text_content(".toast") or "") if toast_visible else ""
    check("copiar reloj en vivo: toast de confirmación", toast_visible and "Copiado" in toast_text,
          f"toast_visible={toast_visible}, texto={toast_text!r}")

    browser.close()

fails = [r for r in results if not r[1]]
print("\n=> %d checks, %d fallan" % (len(results), len(fails)))
sys.exit(1 if fails or errors or EXTERNAL else 0)
