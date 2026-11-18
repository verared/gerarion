# Gerarion · Atlas del tiempo

**Rediseño funcional del portal de calendarios, preparado el 18 de noviembre de 2026.** La vista inicial es el calendario mensual Gerarion. La entrega es independiente del sitio publicado y de la rama de trabajo donde se integre.

## Actualización TCJ · cambios respecto de la primera entrega

La cabecera arranca en **TCJ+0 · Jerusalén**. El selector mundial agrupa **regiones con la misma hora civil en una sola fila** (Santiago y Coyhaique comparten línea con Buenos Aires) y muestra etiquetas **redondeadas a horas enteras: `TCJ−5`, no `TCJ−5:20:37`**, para facilitar la lectura al público general.

- El reloj regional **conserva los segundos exactos**: la redondez es de la etiqueta, no del cálculo. `zoneDelta()` expone el desfase civil preciso por instante y `deltaLabel()` solo redondea para la presentación.
- El meridiano se calcula con `instantFromUnix` e `instantParts` del núcleo. No se cambia el nombre de un reloj civil para simular TCJ.
- Para una región: **diferencia = desplazamiento civil IANA − (TAI−UTC del núcleo + 8400 s)**. La lectura regional suma esa diferencia exacta al instante canónico. UTC solo interviene en el adaptador numérico de interoperabilidad; no es una escala seleccionable ni la referencia de «Hoy».
- Ejemplo verificable a las **17:20:37 TCJ+0 del 18-11-2026 gregoriano**: Santiago y Buenos Aires leen **12:00:00**, diferencia **−05:20:37** (etiqueta `TCJ−5`). En julio de 2026 Santiago lee `TCJ−6` y Buenos Aires `TCJ−5`; por ello no se fuerza una misma fila y su hora real se muestra con segundos.
- La escritura `TCJ−5:20:37` en el selector se interpreta como búsqueda de desfase; el sello canónico sigue emiténdose en **TCJ+0**, nunca con el desfase regional redondeado como si fuera un offset normativo.
- La lista geográfica usa `zone.tab` e `iso3166.tab` de **IANA tzdb 2026f**. Las reglas estacionales se consultan en el `Intl/ICU` instalado en el navegador, sin red. Bouvet y Heard/McDonald figuran **«Sin asignación»**, sin inventarles un horario. Las regiones que no reconoce el navegador se identifican como «No disponible».
- El traductor muestra **origen ↔ Gerarion ↔ destino**. Se puede introducir un sello con hora en el centro, conservado al cambiar de origen, destino o ciudad. «Invertir ruta» comprueba que la conversión inversa no varíe el JDN. La tabla general continúa en «Todas las equivalencias».

### Archivos tocados en esta actualización

| Archivo | Cambio respecto del rediseño anterior |
|---|---|
| `web/zonas-tcj.mjs` **(nuevo)** | Catálogo local de jurisdicciones y regiones, **agrupación por desfase civil exacto** (`zoneGroups`), etiquetas a horas enteras (`deltaLabel`) y lectura del observador desde el instante GUS. |
| `web/atlas.mjs` | `todayJdn` y el reloj pasan a TCJ; `interpret` fija Gerarion como intérprete entre ambos extremos. |
| `web/app.js` | Selector mundial con búsqueda y teclado, preferencias locales, comparación de relojes, día observado, traductor reversible y enlaces que recuerdan ruta y región. |
| `web/index.html` | Estructura semántica; el control de la cabecera muestra hora, diferencia TCJ y ciudad; abre el directorio. |
| `web/style.css` | Sistema visual del atlas: tres columnas del puente, selector, lámina y disposición móvil. |
| `web/CREDITOS.txt` **(nuevo)** | Procedencia y condiciones de los datos geográficos y las fuentes. |
| `tests/atlas.test.mjs` **(nuevo)** | 40 regresiones del adaptador: medianoche TCJ, cruces de día regionales, agrupaciones estacionales, fracciones de hora, cobertura y traducciones reversibles. |
| `e2e_web_test.py` | Prueba los controles reales del selector, la ruta, borradores, enlaces, pausas y el calendario del observador (53 comprobaciones). |
| `tools/exportar.mjs` **(nuevo)** | Regenera el HTML autónomo a partir de las fuentes. |
| `REDISENO.md` | Esta explicación, inventario e instrucciones de integración. |

`Gerarion.html` (copia portátil) **se regenera** con el exportador; no se edita a mano. No se tocaron el núcleo normativo (`web/gerarion.mjs`), los algoritmos de calendarios (`web/calendars.mjs`) ni sus suites, o los perfiles de conformidad.

## Abrirlo

- **Desde las fuentes:** en la carpeta del repositorio, ejecutar `python3 -m http.server 8000 --directory web` y abrir `http://localhost:8000`. No hace falta npm, compilar ni instalar un framework para usar la web.
- **Con doble clic:** el archivo generado por `npm exec --yes --package=esbuild@0.28.2 -- node tools/exportar.mjs` funciona sin servidor ni conexión.

## Decisiones de diseño

1. **El día es el punto de entrada.** La portada muestra la fecha legible y su sello canónico. La cuadrícula, la ficha técnica y las equivalencias comparten una única selección JDN.
2. **Dos calendarios en una cuadrícula.** El número principal pertenece al sistema elegido; la línea inferior muestra la correspondencia. «Hoy» parte del día TCJ+0 en la región elegida; cambiar de región no mueve una fecha escogida manualmente.
3. **Jerarquía editorial.** Papel marfil, tinta carbón y terracota de selección. Newsreader identifica fechas y títulos; DM Sans, acciones y etiquetas; la monoespaciada del sistema conserva sellos y números técnicos. La lámina de la esfera armilar es decorativa.
4. **Una herramienta por tarea.** Traducción, reloj, intervalos, hitos, referencia y verificación tienen vistas separadas; la navegación conserva la fecha.
5. **Lectura accesible.** Menú adaptable, teclado completo, foco visible, contraste reforzado, errores en los campos y respeto a la preferencia de movimiento reducido. Las etiquetas de desfase a horas enteras (`TCJ±H`) son parte de esa simplificación.

## Qué se puede probar

- **Calendario:** cambiar de mes, seleccionar días de meses vecinos, «Hoy», y «Ir a una fecha» con `/`. Las flechas del teclado avanzan por día o por semana. Las fechas especiales (Nuvivid, Cruxyphi) se marcan y se explican en la ficha.
- **Traductor:** ruta Origen ↔ Gerarion ↔ Destino con las diez variantes externas como extremos. Cada resultado incluye su método o límite de cobertura. Una fecha civil imposible no se transforma silenciosamente en otra fecha.
- **Selector mundial:** búsqueda por país, ciudad o desfase; navegación por teclado; agrupación por hora civil exacta con etiqueta `TCJ±H`; meridiano canónico aparte; territorios sin regla propios se muestran sin hora inventada.
- **Enlaces:** la edición servida conserva ambos extremos, día, ubicación, vista y, cuando procede, el sello con hora. Lee también los enlaces originales `#cal=…&d=…`. El HTML portátil comparte un enlace compatible con la fecha del portal, no una ruta local.
- **Reloj:** referencia TCJ+0, comparación entre Jerusalén, Santiago y Buenos Aires, pausa que conserva el instante, y formatos de intercambio (RFC 3339, Unix, NTP) que no reemplazan la coordenada GUS.
- **Intervalos:** dos sistemas con detección automática, cruce AY/DY, orden inverso, semanas y segundos convencionales.
- **Biblioteca:** seis hitos del portal, referencia de formatos, límites de precisión y el resultado real de `tests.mjs` en el navegador.

## Inventario completo

Las rutas son relativas a la raíz del repositorio.

### Archivos nuevos del proyecto — 8

| Archivo | Justificación |
|---|---|
| `web/atlas.mjs` | Adaptador independiente del DOM: equivalencias, validación, cuadrícula, límites de mes/era y lecturas de reloj. Evita introducir decisiones visuales en el núcleo normativo y permite probarlas por separado. |
| `web/zonas-tcj.mjs` | Índice IANA por país y región, agrupación por hora civil exacta, desfases civiles con segundos y lectura del observador en coordenadas TCJ. |
| `web/assets/atlas.svg` | Hoja de símbolos vectoriales: emblema, favicon, iconos de controles y distintivos de calendarios, reutilizables a cualquier escala sin instalar una biblioteca de iconos. |
| `web/assets/esfera-armilar.webp` | Lámina original generada para esta edición, tratada como grabado de tinta con fondo transparente. Decorativa; los datos no dependen de la imagen. |
| `web/fonts/newsreader-latin.woff2` | Serif local (OFL) para títulos y fechas; jerarquía editorial sin peticiones externas. |
| `web/fonts/dm-sans-latin.woff2` | Sans local (OFL) para botones, avisos y datos secundarios. |
| `web/CREDITOS.txt` | Autoría, procedencia del grabado y las fuentes, y textos de MIT, Apache 2.0, SIL OFL y el carácter de dominio público del índice IANA. |
| `tests/atlas.test.mjs` | 40 pruebas del adaptador, sin dependencias externas. Protegen las conversiones inversas, la validación, Tempalum, cruces de era, índices, NTP y la relación entre días civiles y TCJ. |
| `tools/exportar.mjs` | Regenera el HTML autónomo; incrusta fuentes, vectores, lámina y licencias, y calcula el hash de su CSP. Solo para exportar. |
| `REDISENO.md` | Este documento. |

### Archivos existentes modificados — 4

| Archivo | Cambio |
|---|---|
| `web/index.html` | Estructura semántica nueva, navegación, cabecera TCJ, diálogo accesible y recursos exclusivamente locales. |
| `web/style.css` | Sistema visual completo: tipografía, calendario de doble lectura, vistas de herramientas, adaptación, contraste e impresión. |
| `web/app.js` | Control de las siete vistas, día seleccionado, enlaces, teclado, portapapeles, reloj y validación. El reloj usa la conversión Unix → instante del propio núcleo. |
| `e2e_web_test.py` | Adaptada a los controles reales del nuevo diseño; comprueba resultados, no etiquetas de la interfaz sustituida. |

### Archivos originales reutilizados sin modificar — 5

| Archivo | Por qué se conserva |
|---|---|
| `web/gerarion.mjs` | Fuente de verdad de fechas, eras, ciclos, instant, TAI/TCJ y perfil RFC 3339. |
| `web/calendars.mjs` | Algoritmos y tablas originales, incluido el soporte Intl/ICU. |
| `web/tests.mjs` | Las comprobaciones integradas del núcleo que se ejecutan en la página. |
| `web/calendars.test.mjs` | Suite original de calendarios, reproducible con Node. |
| `web/LICENSE` | Declaración original de licenciamiento dual; textos íntegros también en `CREDITOS.txt`. |

## Comprobaciones realizadas

| Grupo | Resultado |
|---|---:|
| Núcleo original, `web/tests.mjs` | 36/36 |
| Calendarios originales, `web/calendars.test.mjs` | 42/42 |
| Adaptador del atlas, `tests/atlas.test.mjs` | 40/40 |
| Flujos reales de Chromium, `e2e_web_test.py` | 53/53 |

**171 comprobaciones correctas.** En los flujos de navegador no hubo errores JavaScript ni solicitudes HTTP externas. La edición portátil abre desde `file://` con una sola petición (el propio documento) y fuentes funcionando desde su embebido.

### Reproducir pruebas

Desde la raíz del repositorio, con Node 20+:

```bash
node web/tests.mjs
node web/calendars.test.mjs
node --test tests/atlas.test.mjs
```

Pruebas de navegador (Playwright solo se instala en desarrollo):

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
python3 -m http.server 8123 --directory web
python3 e2e_web_test.py
```

Las pruebas usan una fecha de referencia fija (18 de noviembre de 2026, 15:00 UTC); **la aplicación usa la hora real del dispositivo**.

### Regenerar el HTML portátil

```bash
npm exec --yes --package=esbuild@0.28.2 -- node tools/exportar.mjs Gerarion.html
```

Cambiar las fuentes en `web/`, no en el archivo generado.

## Integración sin sustituir el proyecto normativo

1. Trabajar en una rama y copiar los archivos respetando sus rutas. No borrar el resto de `web/`, `tests/`, `tools/`, `vectors/`, los perfiles ni los workflows originales.
2. Revisar los cuatro archivos modificados y los diez nuevos. La copia portátil no necesita integrarse si solo se publica el sitio modular.
3. Ejecutar las baterías anteriores y las que ya tenga el repositorio. Este paquete no sustituye los vectores normativos originales.
4. Publicar `web/` mediante el flujo de Pages existente tras revisar y aprobar los cambios; todos los recursos usan rutas relativas para funcionar bajo `/gerarion/`.

## Límites que la interfaz hace explícitos

UTC es una escala de tiempo, RFC 3339 un formato y NTP un protocolo. **El rediseño no afirma certificación de sincronización NTP.** La etiqueta `TCJ±H` es una aproximación presentacional del desfase civil exacto, que se calcula con segundos para el instante consultado. La precisión del reloj depende del dispositivo; la conversión TAI−UTC depende de tabla del núcleo GUS. Las lecturas históricas probables, las aproximaciones de ICU y los límites de las tablas bahá’íes se indican en las fichas correspondientes.
