NAME = gerarion
MAJOR = 3
MINOR = 1
PATCH = 0
SONAME = lib$(NAME).so.$(MAJOR)

PREFIX ?= /usr/local
INCLUDEDIR ?= $(PREFIX)/include
LIBDIR ?= $(PREFIX)/lib
PKGCONFDIR ?= $(LIBDIR)/pkgconfig

CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -pedantic
PICFLAGS ?= -fPIC

# --- fuentes por dominio ------------------------------------------------------
CORE_SRC = core/gus_core.c
TAI_SRC  = tai/gus_tai.c
CLOCK_SRC = clock/gus_clock.c
CAL_SRC  = calendars/gerarion_calendars.c calendars/china_table.c
ALL_SRC  = $(CORE_SRC) $(TAI_SRC) $(CLOCK_SRC) $(CAL_SRC)

HDRS = gus.h gerarion.h \
	core/gus_core.h tai/gus_tai.h clock/gus_clock.h \
	calendars/gerarion_calendars.h calendars/china_table.h

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
SO_LDFLAGS = -shared
else
SO_LDFLAGS = -shared -Wl,-soname,$(SONAME)
endif

.PHONY: all conformance audit fuzz clean test install pkgconfig core-smoke \
	libs libs-core libs-clock libs-calendars

all: gus-conformance gus-cli libgerarion.a libgerarion.so.$(MAJOR) \
	libgerarion-core.a libgerarion-clock.a libgerarion-calendars.a

libs: libgerarion.a libgerarion.so.$(MAJOR) \
	libgerarion-core.a libgerarion-core.so.$(MAJOR) \
	libgerarion-clock.a libgerarion-calendars.a

# --- binarios de verificación -------------------------------------------------
# (compilan contra la suite completa vía el paraguas gus.h)

gus-conformance: conformance.c test_jsonmin.c $(ALL_SRC) $(HDRS)
	$(CC) $(CFLAGS) -o $@ conformance.c test_jsonmin.c $(ALL_SRC)

guti-conformance: guti_conformance.c test_jsonmin.c $(ALL_SRC) $(HDRS)
	$(CC) $(CFLAGS) -o $@ guti_conformance.c test_jsonmin.c $(ALL_SRC)

gus-cli: gus-cli.c $(ALL_SRC) $(HDRS)
	$(CC) $(CFLAGS) -o $@ gus-cli.c $(ALL_SRC)

# --- librería unificada -------------------------------------------------------

lib$(NAME).a: $(ALL_SRC) $(HDRS)
	rm -f *.a.o
	for f in $(ALL_SRC); do \
		$(CC) $(CFLAGS) -c $$f -o $$(echo $$f | tr / _).a.o; done
	ar rcs $@ *.a.o
	rm -f *.a.o

lib$(NAME).so.$(MAJOR): $(ALL_SRC) $(HDRS)
	$(CC) $(CFLAGS) $(PICFLAGS) $(SO_LDFLAGS) -o $@ $(ALL_SRC)

lib$(NAME).dylib: $(ALL_SRC) $(HDRS)
	$(CC) $(CFLAGS) $(PICFLAGS) -dynamiclib \
		-install_name $(LIBDIR)/lib$(NAME).dylib -o $@ $(ALL_SRC)

# --- librerías independientes por dominio -------------------------------------
# core: apta para microcontroladores (sin reloj de SO, sin tabla TAI‑UTC)
libgerarion-core.a: $(CORE_SRC) core/gus_core.h
	$(CC) $(CFLAGS) -c $(CORE_SRC) -o gus_core.a.o
	ar rcs $@ gus_core.a.o
	rm -f gus_core.a.o

libgerarion-core.so.$(MAJOR): $(CORE_SRC) core/gus_core.h
	$(CC) $(CFLAGS) $(PICFLAGS) $(SO_LDFLAGS) -o $@ $(CORE_SRC)

# clock: máquina de estados §6.3; solo depende de tipos estándar
libgerarion-clock.a: $(CLOCK_SRC) clock/gus_clock.h
	$(CC) $(CFLAGS) -c $(CLOCK_SRC) -o gus_clock.a.o
	ar rcs $@ gus_clock.a.o
	rm -f gus_clock.a.o

# calendars: motor de 10 calendarios; enlaza contra core en el consumidor
libgerarion-calendars.a: $(CAL_SRC) calendars/gerarion_calendars.h calendars/china_table.h
	$(CC) $(CFLAGS) -c calendars/gerarion_calendars.c -o gerarion_calendars.a.o
	$(CC) $(CFLAGS) -c calendars/china_table.c -o china_table.a.o
	ar rcs $@ gerarion_calendars.a.o china_table.a.o
	rm -f gerarion_calendars.a.o china_table.a.o

libs-core: libgerarion-core.a libgerarion-core.so.$(MAJOR)
libs-clock: libgerarion-clock.a
libs-calendars: libgerarion-calendars.a

# Auditoría adversarial: ASan + UBSan (sin recover) sobre el runner de
# conformancia y el harness de estrés; incluye el motor multi-calendario.
SANFLAGS = -fsanitize=address,undefined -fno-sanitize-recover=all
audit: gus-audit-stress cal-audit
	ASAN_OPTIONS=halt_on_error=1 ./gus-audit-stress \
		../vectors/gus-normative-003.json \
		../vectors/gus-3339-negative-001.json \
		../vectors/gus-regression-001.json \
		../vectors/gus-quickverify-001.json

gus-audit-stress: audit_stress.c test_jsonmin.c $(CORE_SRC) $(TAI_SRC) $(CLOCK_SRC) $(HDRS)
	$(CC) -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic $(SANFLAGS) -o $@ audit_stress.c test_jsonmin.c $(CORE_SRC) $(TAI_SRC) $(CLOCK_SRC)

cal-audit: cal_audit_stress.c $(ALL_SRC) $(HDRS)
	$(CC) -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic $(SANFLAGS) -o $@ cal_audit_stress.c $(ALL_SRC)
	ASAN_OPTIONS=halt_on_error=1 ./cal-audit

conformance: gus-conformance guti-conformance
	./gus-conformance ../vectors/gus-normative-003.json ../vectors/gus-3339-negative-001.json ../vectors/gus-regression-001.json ../vectors/gus-quickverify-001.json
	./guti-conformance ../vectors/guti-calendars-001.json

# Humo del núcleo standalone: compila y corre SOLO con core/ (TCJ+GUS),
# demostrando que libgerarion-core no arrastra reloj ni tabla TAI.
core-smoke: core_smoke.c core/gus_core.c core/gus_core.h
	$(CC) $(CFLAGS) -o $@ core_smoke.c core/gus_core.c
	./core-smoke

fuzz: gus-cli
	python3 ../tools/fuzz_diff.py

# --- instalación con PREFIX configurable --------------------------------------
# Plantillas pkg-config: la suite completa y cada dominio por separado.

gerarion.pc: gerarion.pc.in
	sed -e 's|@PREFIX@|$(PREFIX)|g' -e 's|@VERSION@|$(MAJOR).$(MINOR).$(PATCH)|g' \
		gerarion.pc.in > gerarion.pc

gerarion-core.pc: gerarion-core.pc.in
	sed -e 's|@PREFIX@|$(PREFIX)|g' -e 's|@VERSION@|$(MAJOR).$(MINOR).$(PATCH)|g' \
		gerarion-core.pc.in > gerarion-core.pc

gerarion-clock.pc: gerarion-clock.pc.in
	sed -e 's|@PREFIX@|$(PREFIX)|g' -e 's|@VERSION@|$(MAJOR).$(MINOR).$(PATCH)|g' \
		gerarion-clock.pc.in > gerarion-clock.pc

gerarion-calendars.pc: gerarion-calendars.pc.in
	sed -e 's|@PREFIX@|$(PREFIX)|g' -e 's|@VERSION@|$(MAJOR).$(MINOR).$(PATCH)|g' \
		gerarion-calendars.pc.in > gerarion-calendars.pc

pkgconfig: gerarion.pc gerarion-core.pc gerarion-clock.pc gerarion-calendars.pc

install: lib$(NAME).a lib$(NAME).so.$(MAJOR) libgerarion-core.a libgerarion-clock.a libgerarion-calendars.a pkgconfig
	install -d $(DESTDIR)$(INCLUDEDIR)/gerarion/core $(DESTDIR)$(INCLUDEDIR)/gerarion/tai \
		$(DESTDIR)$(INCLUDEDIR)/gerarion/clock $(DESTDIR)$(INCLUDEDIR)/gerarion/calendars \
		$(DESTDIR)$(LIBDIR) $(DESTDIR)$(PKGCONFDIR)
	install -m 644 gus.h gerarion.h $(DESTDIR)$(INCLUDEDIR)/gerarion/
	install -m 644 core/gus_core.h $(DESTDIR)$(INCLUDEDIR)/gerarion/core/
	install -m 644 tai/gus_tai.h $(DESTDIR)$(INCLUDEDIR)/gerarion/tai/
	install -m 644 clock/gus_clock.h $(DESTDIR)$(INCLUDEDIR)/gerarion/clock/
	install -m 644 calendars/gerarion_calendars.h calendars/china_table.h $(DESTDIR)$(INCLUDEDIR)/gerarion/calendars/
	install -m 644 lib$(NAME).a libgerarion-core.a libgerarion-clock.a libgerarion-calendars.a $(DESTDIR)$(LIBDIR)/
	install -m 755 lib$(NAME).so.$(MAJOR) $(DESTDIR)$(LIBDIR)/
	ln -sf lib$(NAME).so.$(MAJOR) $(DESTDIR)$(LIBDIR)/lib$(NAME).so
	install -m 644 gerarion.pc gerarion-core.pc gerarion-clock.pc gerarion-calendars.pc $(DESTDIR)$(PKGCONFDIR)/

test: conformance fuzz

clean:
	rm -f gus-conformance gus-cli gus-audit-stress cal-audit guti-conformance \
		lib$(NAME).a lib$(NAME).so.$(MAJOR) lib$(NAME).dylib \
		libgerarion-core.a libgerarion-core.so.$(MAJOR) \
		libgerarion-clock.a libgerarion-calendars.a \
		gerarion.pc gerarion-core.pc gerarion-clock.pc gerarion-calendars.pc \
		core-smoke *.o *.a.o
