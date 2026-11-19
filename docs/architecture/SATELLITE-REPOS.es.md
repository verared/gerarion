# Arquitectura de repositorios satélite `verared/gt-*`

Versión: 1.0.0 · Línea base: `v3.2.0` · Licencia: CC-BY-4.0 ·
Mantenida por: verared contributors

## 1. Modelo general

`verared/gerarion` es la **suite de referencia completa**: contiene las
8 especificaciones normativas, los vectores CC0, los núcleos de
referencia en las tres plataformas y la batería de verificación. Los
repositorios satélite `verared/gt-*` (Gerarion Time) son **productos
derivados de un solo dominio**: adoptan un único problema, sin arrastrar
el resto de la suite.

```
verared/gerarion          (fuente de verdad: specs + vectores + núcleos + batería)
   │  python3 tools/export_module.py --module <gt-*> --out <dir>
   ▼
verared/gt-core      gt-tcj      gt-gus      gt-calendar
        gt-gts       gt-gst      gt-interop
        gt-tslr*     gt-gcerts*  (* experimentales, estructuras iniciales)
```

## 2. Módulos y dependencias

| Módulo | Dominio | Depende de | Estado |
|---|---|---|---|
| `gt-core` | TCJ + GUS (núcleo MCU/bare-metal) | — | Estable |
| `gt-tcj` | Escala atómica TCJ, puente TAI − UTC | gt-core | Estable |
| `gt-gus` | Sintaxis canónica 32/29, quick_verify | — | Estable |
| `gt-calendar` | AY/DY + 10 calendarios (GUTI-1) | gt-core | Estable |
| `gt-gts` | Máquina de estados §6.3 + Roughtime | gt-core (Roughtime: +gt-interop, reexports: gt-gst) | Estable (núcleo) |
| `gt-gst` | GST v2, JCS RFC 8785, híbrido, ReplayGuard, notario | gt-core (Roughtime-side legacy: deprecated/) | Estable |
| `gt-interop` | RFC 3339, ISO 8601, Unix, RFC 3161 | gt-core + gt-tcj | Estable (3339) |
| `gt-tslr` | Tiempo Solar Local Real | gt-core | EXPERIMENTAL |
| `gt-gcerts` | Validez temporal de certificados | gt-core + gt-gst | EXPERIMENTAL |

La verdad exacta de dependencias vive en el código
(`tools/export_module.py`, atributo `deps` + `external_roots`) y se
repite en el README que recibe cada export.

## 3. Reglas del sistema

1. **Rutas relativas intactas.** Cada export conserva la estructura de
   directorios del repositorio base (`docs/specs/`, `impl-c/`,
   `src/gerarion/`, `web/engine/`, `vectors/`). Dos o más satélites se
   combinan en un árbol sin conflictos de rutas.
2. **Solo lectura en origen.** Exportar no altera `verared/gerarion`
   (invariante verificado: `tests/test_export_module.py`). Los satélites
   **nunca editan** los archivos exportados: se regeneran desde un tag.
3. **Fuente de verdad única.** Las especificaciones, los vectores CC0 y
   la batería completa viven SOLO en `verared/gerarion`. Un satélite
   declara la línea base (`v3.2.0` o superior) y la reproduce con sus
   propios runners donde aplique.
4. **Compatibilidad legal.** Cada export es un proyecto REUSE 3.3
   completo: `LICENSE`, `LICENSES/`, `NOTICE` y `REUSE.toml` cubren el
   100 % de sus archivos (`reuse lint` 100 %). Los textos vía `LICENSES/`
   solo se incluyen si el módulo los usa.
5. **Vectores por módulo.** Cada export lleva sus vectores CC0
   (`gus-normative-003.json` para los núcleos, `guti-calendars-001.json`
   para el motor de calendarios, `gus-3339-*` para INTEROP), con opción
   `--no-large-vectors` para distribuciones ligeras.

## 4. Flujo operativo

### 4.1 Exportar

```bash
python3 tools/export_module.py --all --out /tmp/gt --verify
# o un módulo concreto:
python3 tools/export_module.py --module gt-core --out /tmp/gt --verify
```

`--verify` ejecuta `reuse lint` dentro de cada export y, para
`gt-core`, compila el núcleo standalone con
`-std=gnu11 -Wall -Wextra -Werror` y corre su humo (el guardia interno
congelado usa `__int128`, extensión GNU: la ±pedantic estricta ISO
queda cubierta por la batería audit del repositorio base; GCC/Clang
compilan sin avisos en este modo). Falla con
código 2 ante cualquier error.

### 4.2 Publicar un satélite

```bash
python3 tools/export_module.py --module gt-core --out /tmp/gt --verify
cd /tmp/gt/gt-core
git init && git add -A && git commit -m "gt-core v3.2.0 (generado desde verared/gerarion)"
git remote add origin git@github.com:verared/gt-core.git
git push -u origin main
gh repo create verared/gt-core --public --source . --push  # alternativa
```

Recomendación operativa: crear el remoto como **plantilla del release
vigente** y proteger `main` del satélite; cualquier cambio va primero
al repositorio base y se regenera.

### 4.3 Consumir (integradores)

Un integrador solo necesita el dominio de su producto:

```bash
git clone https://github.com/verared/gt-core   # núcleo MCU en C11
make -C gt-core/impl-c smoke                   # núcleo standalone verificable
```

o, para aplicaciones que combinan dominios, clonar los módulos
necesarios en el mismo árbol (las rutas relativas coinciden) o añadir
los paquetes Python por extras (`pip install gerarion[gst,gts]`).

### 4.4 Actualizar un satélite

```bash
# en verared/gerarion, con un tag nuevo (>= v3.2.0):
python3 tools/export_module.py --module gt-core --out /tmp/gt --verify
# en el clon del satélite:
git pull --rebase          # nunca ediciones manuales desde la última export
# sobrescribir con la export nueva:
rsync -a --delete /tmp/gt/gt-core/ ~/src/gt-core/
git diff --stat            # la única diferencia esperada: código nuevo del tag
```

## 5. Contenido de cada export

Cada paquete incluye, además del código y docs del dominio:

| Pieza | Origen |
|---|---|
| `LICENSE`, `NOTICE`, `LICENSES/` | copiados de la raíz de `verared/gerarion` |
| `REUSE.toml` | generado por la herramienta, con anotaciones override y cobertura 100 % |
| `README.md` / `README.es.md` | generados: problema único, estado, dependencias, uso offline, contrato de sincronización |
| `impl-c/Makefile` (solo gt-core) | generado: `libgerarion-core.a`/`.so` + `gerarion-core.pc` + humo standalone, sin malloc |
| `src/`, `tests/`, `vectors/` (solo módulos experimentales) | generados |

## 6. Certificación de cierre

- `reuse lint` del repositorio base: **100 %** (obligatorio en cada PR).
- `reuse lint` de cada export: **100 %** (garantizado por la
  herramienta y probado en `tests/test_export_module.py`).
- Los satélites heredan el estado normativo del dominio: un módulo
  Estable expone aritmética congelada; un módulo EXPERIMENTAL empieza
  siempre marcado como tal (`EXPERIMENTAL` en README y spec).
