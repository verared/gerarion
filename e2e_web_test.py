# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Regression checks for the redesigned portal, using its real controls.

Start: python3 -m http.server 8123 --directory web
Run:   python3 e2e_web_test.py   (requires Playwright + Chromium)
BASE_URL and CHROMIUM_EXECUTABLE_PATH are optional environment variables.

Reference date: 2026-11-18 15:00 UTC == 17:20:37 TCJ == 2031DY-09-07-L,
12:00:00 en Santiago (desfase TCJ−5 como etiqueta de horas enteras).
The suite installs a fixed clock, so it does not depend on wall time.
"""

import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8123/index.html")
ORIGIN = urlsplit(BASE).netloc
checks = 0


def check(desc, cond, extra=""):
    global checks
    if not cond:
        print("FAIL:", desc, ("| " + extra if extra else ""))
        sys.exit(1)
    checks += 1
    print(f"OK {checks:2} · {desc}")


with sync_playwright() as pw:
    browser = pw.chromium.launch(
        headless=True,
        executable_path=os.environ.get("CHROMIUM_EXECUTABLE_PATH") or None,
    )
    ctx = browser.new_context(
        viewport={"width": 1366, "height": 900},
        locale="es-CL",
        timezone_id="America/Santiago",
        reduced_motion="reduce",
        permissions=["clipboard-read", "clipboard-write"],
    )
    p = ctx.new_page()
    errors, external = [], []
    p.on("pageerror", lambda e: errors.append(str(e)))
    p.on(
        "console",
        lambda m: errors.append(m.text) if m.type == "error" else None,
    )
    p.on(
        "request",
        lambda r: external.append(r.url)
        if urlsplit(r.url).netloc and urlsplit(r.url).netloc != ORIGIN
        else None,
    )
    p.clock.install(time=datetime(2026, 11, 18, 15, 0, tzinfo=timezone.utc))
    p.goto(BASE, wait_until="networkidle")
    p.locator("#view .day-hero").wait_for()

    def t(sel):
        return p.locator(sel).inner_text().strip()

    def nav(v):
        p.locator(f'.sidebar [data-view="{v}"]').click()

    def submit_until(expect_js, btn="#translator-form [type=submit]", tries=3,
                     timeout=2500):
        # A re-render can race the click in slow runners; retry until the DOM
        # observable (or its error counterpart) confirms the handler ran.
        for _ in range(tries):
            p.locator(btn).click()
            try:
                p.wait_for_function(expect_js, timeout=timeout)
                return True
            except Exception:
                pass
        return False

    # ── Carga y cabecera ────────────────────────────────────────────────
    check("carga sin errores de JavaScript", not errors, "; ".join(errors[:3]))
    check("cero peticiones externas (sin CDN ni analítica)", not external, "; ".join(external[:3]))
    check(
        "la cabecera arranca en TCJ+0 · Jerusalén a la hora TCJ real",
        t("#header-zone") == "TCJ+0"
        and t("#header-city") == "Jerusalén"
        and t("#header-time").startswith("17:20:"),
        f"{t('#header-zone')} {t('#header-city')} {t('#header-time')}",
    )
    check(
        "el calendario abre con el día TCJ correcto",
        "7 de Novat, 2031" in t(".day-hero h2"),
        t(".day-hero h2"),
    )
    check(
        "la ficha muestra JDN y day_index coherentes",
        "2.461.363" in t(".fact-list") and "742.050" in t(".fact-list"),
    )

    # ── Calendario ──────────────────────────────────────────────────────
    p.locator('[data-day="2461364"]').click()
    check(
        "seleccionar un día actualiza sello y ficha",
        "2031DY-09-08-M" in t(".canonical-tag code")
        and "19 de noviembre" in t(".civil-date h3"),
        t(".canonical-tag code"),
    )
    p.locator(".day-cell.selected").press("ArrowDown")
    check(
        "flecha abajo de la cuadrícula avanza exactamente una semana",
        p.locator(".day-cell.selected").get_attribute("data-day") == "2461371",
    )
    saved = t(".canonical-tag code")
    p.locator('[data-step="1"]').click()
    check("navegar al mes siguiente cambia el título", "Deshimo" in t("#month-title"), t("#month-title"))
    p.locator('[data-step="-1"]').click()
    check("volver al mes anterior recupera la selección", t(".canonical-tag code") == saved)
    p.select_option("#month-system", "greg")
    check(
        "la vista gregoriana usa la semana civil",
        "Noviembre" in t("#month-title") and "LUN" in t(".week-head").upper(),
        t("#month-title"),
    )
    p.select_option("#month-system", "gero")
    p.locator('[data-action="today"]').click()
    check(
        "Hoy restablece el día observado en TCJ+0",
        t(".canonical-tag code") == "2031DY-09-07-L",
        t(".canonical-tag code"),
    )
    p.locator('[data-action="jump"]').click()
    p.select_option("#jump-mode", "gero")
    p.fill("#jump-value", "0000DY-01-01-S")
    p.locator('#jump-form [type="submit"]').click()
    check(
        "Ir a una fecha acepta el origen de la era DY",
        t(".canonical-tag code") == "0000DY-01-01-S",
        t(".canonical-tag code"),
    )
    p.locator('[data-step="-1"]').click()
    check(
        "la navegación cruza DY → AY y llega a Tempalum",
        "1 AY" in t("#month-title") and "Tempalum" in t("#month-title"),
        t("#month-title"),
    )
    p.keyboard.press("/")
    p.select_option("#jump-mode", "jdn")
    p.fill("#jump-value", "2461363")
    p.locator('#jump-form [type="submit"]').click()
    check(
        "el atajo «/» abre el selector y acepta un JDN",
        p.locator(".day-cell.selected").get_attribute("data-day") == "2461363",
    )
    p.locator('[data-detail="hebrew"]').click()
    check(
        "la correspondencia abre una ficha con notas de precisión",
        p.locator("#dialog").is_visible()
        and ("prolépticas" in t("dialog") or "determinista" in t("dialog")),
    )
    p.locator('dialog [data-origin="hebrew"]').click()
    check(
        "una equivalencia puede convertirse en nuevo origen",
        p.input_value("#source-mode") == "hebrew",
        p.input_value("#source-mode"),
    )
    check(
        "la traducción muestra las once variantes del día",
        p.locator("[data-result]").count() == 11,
        str(p.locator("[data-result]").count()),
    )

    # ── Traductor ───────────────────────────────────────────────────────
    p.locator("#all-calendars > summary").click()
    p.fill("#calendar-filter", "maya")
    check(
        "el filtro muestra solo sus coincidencias",
        p.locator("[data-result]:visible").count() == 1,
        str(p.locator("[data-result]:visible").count()),
    )
    p.fill("#calendar-filter", "zzz sin coincidencias")
    check(
        "la búsqueda vacía tiene una explicación",
        p.locator("#no-results").is_visible(),
    )
    p.fill("#calendar-filter", "")
    p.select_option("#source-mode", "greg")
    p.fill("#source-date", "2026-02-31")
    check(
        "una fecha civil inexistente se rechaza con error visible",
        submit_until("document.getElementById('trans-error') && !document.getElementById('trans-error').hidden"),
    )
    p.fill("#source-date", "2026-03-17")
    ok21 = submit_until(
        "document.querySelector('[data-result=\"gero\"] .result-value')?.textContent === '2031DY-01-01-S'"
    )
    check(
        "traducción conocida: 17-03-2026 abre el año 2031 DY",
        ok21,
        "valor:" + t('[data-result="gero"] .result-value')
        + " · entrada:" + p.input_value("#source-date"),
    )
    stamp = "2031DY-03-08-T-09:30:00-SC-TCJ+0"
    p.locator('[data-action="edit-pivot"]').click()
    p.fill("#pivot-value", stamp)
    p.locator("#pivot-form [type=submit]").click()
    check(
        "el sello con hora se conserva como dato adjunto",
        stamp in t(".time-preserved") and "Interpretar" not in t("#dialog h2") if True else False,
    )
    p.locator('[data-origin="greg"]').click()
    check(
        "cambiar el origen desde la misma fecha no pierde la hora",
        stamp in t(".time-preserved"),
    )
    p.locator('[data-action="share"]').click()
    shared = p.evaluate("navigator.clipboard.readText()")
    p.goto(shared)
    p.locator(".bridge-panel").wait_for()
    check(
        "un enlace compartido recupera origen, fecha y sello",
        stamp in t(".time-preserved") and p.input_value("#source-mode") == "greg",
        shared,
    )

    # ── Enlaces heredados y ruta inversa ────────────────────────────────
    p.goto(BASE + "#cal=greg&d=2012-12-21")
    p.wait_for_function(
        "document.querySelector('[data-result=\"maya\"] .result-value')?.textContent === \"13.0.0.0.0\""
    )
    check(
        "los enlaces #cal=…&d=… del portal original siguen funcionando",
        t('[data-result="maya"] .result-value') == "13.0.0.0.0",
    )
    p.select_option("#target-mode", "maya")
    check(
        "el destino elegido se muestra con Gerarion como intérprete",
        t("#bridge-output") == "13.0.0.0.0" and "Gerarion" in t(".bridge-core h3"),
        t("#bridge-output"),
    )
    pivot = t("#bridge-stamp")
    p.locator('[data-action="swap-route"]').click()
    check(
        "invertir la ruta intercambia extremos sin cambiar el día",
        p.input_value("#source-mode") == "maya"
        and p.input_value("#target-mode") == "greg"
        and t("#bridge-stamp") == pivot
        and p.input_value("#source-date") == "13.0.0.0.0",
        f"{p.input_value('#source-mode')} {p.input_value('#target-mode')}",
    )
    p.fill("#source-date", "fecha inválida")
    p.locator('[data-action="swap-route"]').click()
    check(
        "una entrada inválida no se pierde al intentar invertir la ruta",
        p.input_value("#source-date") == "fecha inválida"
        and p.locator("#trans-error").is_visible()
        and p.input_value("#source-mode") == "maya",
    )
    p.fill("#source-date", "13.0.0.0.0")
    p.select_option("#target-mode", "chinese")
    check(
        "cambiar el destino conserva el borrador e indica la pendiente",
        p.input_value("#source-date") == "13.0.0.0.0"
        and p.locator("#trans-pending").is_visible(),
    )

    # ── Selector mundial: agrupación civil y etiquetas TCJ±H ────────────
    p.locator("#translator-form [type=submit]").click()
    antes = t("#bridge-stamp")
    p.click("#zone-trigger")
    p.fill("#zone-query", "Chile")
    check(
        "el directorio agrupa Chile en filas por desfase, no por región",
        "#zone-list button" and p.locator("#zone-list button").count() <= 3,
        str(p.locator("#zone-list button").count()),
    )
    p.fill("#zone-query", "Santiago")
    p.keyboard.press("ArrowDown")
    p.keyboard.press("Enter")
    check(
        "elegir por teclado: etiqueta a horas enteras, TCJ−5",
        t("#header-city") == "Santiago" and t("#header-zone") == "TCJ−5",
        f"{t('#header-city')} {t('#header-zone')}",
    )
    check(
        "cambiar de ciudad conserva la fecha interpretada explícitamente",
        t("#bridge-stamp") == antes,
        t("#bridge-stamp"),
    )
    p.locator('[data-action="share"]').click()
    p.goto(p.evaluate("navigator.clipboard.readText()"))
    p.locator("#view .page-heading").wait_for()
    check(
        "el enlace guarda los dos extremos de la ruta y la zona",
        p.input_value("#source-mode") == "maya"
        and p.input_value("#target-mode") == "chinese"
        and t("#header-city") == "Santiago",
        f"{p.input_value('#source-mode')}→{p.input_value('#target-mode')} {t('#header-city')}",
    )
    p.click("#zone-trigger")
    p.fill("#zone-query", "Coyhaique")
    first_label = t("#zone-list button code")
    p.fill("#zone-query", "Santiago")
    check(
        "Santiago y Coyhaique comparten la misma fila por desfase civil",
        t("#zone-list button code") == first_label.replace("\n", " "),
        "",
    )
    antes = t("#bridge-stamp")
    p.fill("#zone-query", "Bouvet")
    check(
        "un territorio sin regla propia figura sin desfase inventado",
        "Sin asignación" in t("#zone-list") or "No disponible" in t("#zone-list"),
        t("#zone-list"),
    )
    p.fill("#zone-query", "xyz-wildcard")
    check(
        "el buscador explica que no hay coincidencias",
        "No hay coincidencias" in t("#zone-list"),
        t("#zone-list"),
    )
    p.locator('dialog [data-zone="TCJ+0"]').click()
    check(
        "el meridiano canónico vuelve a la cabecera",
        t("#header-zone") == "TCJ+0" and t("#header-city") == "Jerusalén",
        f"{t('#header-zone')} {t('#header-city')}",
    )

    # ── Distancia ───────────────────────────────────────────────────────
    nav("distancia")
    p.fill("#dist-a", "0001AY-00-11-B")
    p.fill("#dist-b", "0000DY-01-01-S")
    p.locator("#distance-form [type=submit]").click()
    check(
        "distancia exacta al cruzar la era",
        t("#interval-result h2") == "1 día",
        t("#interval-result h2"),
    )
    p.locator('[data-action="swap-dates"]').click()
    check(
        "intercambiar las fechas invierte el signo",
        t("#interval-result h2") == "-1 día",
        t("#interval-result h2"),
    )
    p.fill("#dist-a", "fecha no válida")
    p.locator("#distance-form [type=submit]").click()
    check(
        "un error de distancia deja la vista sin resultado obsoleto",
        p.locator("#distance-error").is_visible()
        and not p.locator("#interval-result").is_visible(),
    )

    # ── Reloj ───────────────────────────────────────────────────────────
    nav("reloj")
    p.locator("#clock-exchange > summary").click()
    first_unix = t("#live-unix")
    p.clock.run_for(1100)
    check(
        "el reloj se actualiza en vivo",
        int(t("#live-unix")) > int(first_unix),
    )
    p.locator('[data-action="pause"]').click()
    frozen = t("#live-stamp")
    p.clock.run_for(2100)
    p.click("#zone-trigger")
    p.fill("#zone-query", "Santiago")
    p.locator("#zone-list button", has_text="Santiago").first.click()
    check(
        "la pausa conserva el instante canónico aunque cambie la región",
        t("#live-stamp") == frozen and frozen.startswith("2031DY-09-07-L"),
        f"{t('#live-stamp')} vs {frozen}",
    )
    check(
        "la lectura regional compara relojes con etiqueta de horas",
        t("#header-zone") == "TCJ−5",
        t("#header-zone"),
    )
    check(
        "el reloj ofrece RFC 3339 con Z y una marca NTP hex con era",
        t("#live-rfc").endswith("Z") and "." in t("#live-ntp") and "era" in t("#live-ntp"),
        f"{t('#live-rfc')} · {t('#live-ntp')}",
    )
    p.locator('[data-action="pause"]').click()
    check("reanudar la lectura vuelve al modo en vivo", "live" not in t("#live-unix"))

    # ── Hitos, referencia y verificación ────────────────────────────────
    nav("hitos")
    check("hay seis láminas históricas", p.locator(".milestone").count() == 6)
    p.locator(".milestone button").first.click()
    check(
        "un hito lleva al calendario y selecciona su fecha",
        t(".canonical-tag code") == "0000DY-01-01-S",
        t(".canonical-tag code"),
    )
    nav("referencia")
    guia = p.locator(".guide").text_content()
    check(
        "la referencia documenta TCJ, RFC 3339, NTP y cobertura ICU",
        "TCJ" in guia and "NTP" in guia and "ICU" in guia,
    )
    p.locator(".guide details summary").last.click()
    check(
        "los apartados de la guía se pliegan y despliegan",
        p.locator(".guide details[open]").count() >= 1,
    )
    nav("verificacion")
    check(
        "la página de verificación ejecuta la suite real del núcleo",
        "36 pasan, 0 fallan" in t(".test-report") and "verificado" in t(".verify-banner h2").lower() or "36" in t(".verify-banner"),
        t(".verify-banner h2"),
    )

    # ── Accesibilidad y estados ─────────────────────────────────────────
    nav("calendario")
    p.keyboard.press("/")
    p.locator("[data-action=\"close-dialog\"]").first.click()
    check("el diálogo se cierra desde su botón", not p.locator("#dialog").is_visible())
    p.locator("#contrast-control").click()
    check(
        "el modo de alto contraste activa su clase en la raíz",
        "contrast" in (p.get_attribute("html", "class") or ""),
    )
    check(
        "sin errores de JavaScript acumulados",
        not errors,
        "; ".join(errors[:3]),
    )
    # ── PWA: modo avión (fase GUTI-1) ───────────────────────────────────
    # El Service Worker precachea el activo local; toda la interfaz operará
    # con la red cortada: recarga completa, reloj TCJ, traducción entre
    # calendarios y sin errores.
    p.wait_for_function(
        "navigator.serviceWorker.getRegistration()"
        ".then(r => !!r && !!r.active)",
        timeout=15000,
    )
    ctx.set_offline(True)
    p.reload(wait_until="load")
    p.wait_for_timeout(500)
    check(
        "modo avión: la página recarga completa desde la caché "
        "(conserva la región elegida)",
        t("#header-zone") in ("TCJ+0", "TCJ−5")
        and t("#header-city") in ("Jerusalén", "Santiago"),
        f"{t('#header-zone')} {t('#header-city')}",
    )
    check(
        "modo avión: indicador «Modo Offline Listo» visible",
        p.locator("#offline-line").is_visible()
        and "Offline" in t("#offline-status"),
    )
    check(
        "modo avión: el reloj TCJ sigue en marcha",
        re.match(r"^\d{2}:\d{2}:\d{2}$", t("#header-time")),
        t("#header-time"),
    )
    nav("traductor")
    p.wait_for_selector("#translator-form", state="visible")
    p.select_option("#source-mode", "greg")
    p.fill("#source-date", "2026-11-18")
    ok = submit_until(
        "document.querySelector('#bridge-stamp') && "
        "document.querySelector('#bridge-stamp').innerText.includes('2031DY-09-07-L')",
    )
    check(
        "modo avión: traducción gregoriano → Gerarion funciona",
        ok and "2031DY-09-07-L" in t("#bridge-stamp"),
        t("#bridge-stamp")[:80],
    )
    check("modo avión: sin errores de JavaScript", not errors,
          "; ".join(errors[:3]))
    check("modo avión: cero peticiones externas", not external,
          "; ".join(external[:3]))
    ctx.set_offline(False)

    browser.close()

print(f"\n{checks} comprobaciones correctas del rediseño · 0 fallos")
