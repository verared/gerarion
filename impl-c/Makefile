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

LIBSRC = gus.c china_table.c gerarion_calendars.c
LIBHDR = gus.h china_table.h gerarion_calendars.h gerarion.h

.PHONY: all conformance audit fuzz clean test install pkgconfig

all: gus-conformance gus-cli lib$(NAME).a lib$(NAME).so.$(MAJOR)

# --- binarios de verificación ------------------------------------------------

gus-conformance: conformance.c gus.c $(LIBHDR)
	$(CC) $(CFLAGS) -o $@ conformance.c gus.c

# motor multi-calendario: runner de conformancia extendido
gus-conformance-cal: conformance.c gus.c $(LIBSRC) $(LIBHDR)
	$(CC) $(CFLAGS) -o $@ conformance.c gus.c china_table.c gerarion_calendars.c

gus-cli: gus-cli.c gus.c $(LIBHDR)
	$(CC) $(CFLAGS) -o $@ gus-cli.c gus.c

# --- librería portable --------------------------------------------------------

lib$(NAME).a: $(LIBSRC) $(LIBHDR)
	$(CC) $(CFLAGS) -c gus.c -o gus.a.o
	$(CC) $(CFLAGS) -c china_table.c -o china_table.a.o
	$(CC) $(CFLAGS) -c gerarion_calendars.c -o gerarion_calendars.a.o
	ar rcs $@ gus.a.o china_table.a.o gerarion_calendars.a.o
	rm -f gus.a.o china_table.a.o gerarion_calendars.a.o

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
SO_LDFLAGS = -shared -install_name @rpath/lib$(NAME).$(MAJOR).dylib
else
SO_LDFLAGS = -shared -Wl,-soname,$(SONAME)
endif

lib$(NAME).so.$(MAJOR): $(LIBSRC) $(LIBHDR)
	$(CC) $(CFLAGS) $(PICFLAGS) $(SO_LDFLAGS) \
		-o $@ gus.c china_table.c gerarion_calendars.c

lib$(NAME).dylib: $(LIBSRC) $(LIBHDR)
	$(CC) $(CFLAGS) $(PICFLAGS) -dynamiclib \
		-install_name $(LIBDIR)/lib$(NAME).dylib -o $@ gus.c china_table.c gerarion_calendars.c

# Auditoría adversarial: ASan + UBSan (sin recover) sobre el runner de
# conformancia y el harness de estrés; incluye el motor multi-calendario.
SANFLAGS = -fsanitize=address,undefined -fno-sanitize-recover=all
audit: gus-audit-stress cal-audit
	ASAN_OPTIONS=halt_on_error=1 ./gus-audit-stress \
		../vectors/gus-normative-003.json \
		../vectors/gus-3339-negative-001.json \
		../vectors/gus-regression-001.json \
		../vectors/gus-quickverify-001.json

gus-audit-stress: audit_stress.c conformance.c gus.c $(LIBHDR)
	$(CC) -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic $(SANFLAGS) -o $@ audit_stress.c gus.c

cal-audit: cal_audit_stress.c $(LIBSRC) $(LIBHDR)
	$(CC) -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic $(SANFLAGS) -o $@ cal_audit_stress.c gus.c china_table.c gerarion_calendars.c
	ASAN_OPTIONS=halt_on_error=1 ./cal-audit

conformance: gus-conformance
	./gus-conformance ../vectors/gus-normative-003.json ../vectors/gus-3339-negative-001.json ../vectors/gus-regression-001.json ../vectors/gus-quickverify-001.json

fuzz: gus-cli
	python3 ../tools/fuzz_diff.py

# --- instalación con PREFIX configurable --------------------------------------

gerarion.pc: gerarion.pc.in
	sed -e 's|@PREFIX@|$(PREFIX)|g' -e 's|@VERSION@|$(MAJOR).$(MINOR).$(PATCH)|g' \
		gerarion.pc.in > gerarion.pc

pkgconfig: gerarion.pc

install: lib$(NAME).a lib$(NAME).so.$(MAJOR) gerarion.pc
	install -d $(DESTDIR)$(INCLUDEDIR)/gerarion $(DESTDIR)$(LIBDIR) $(DESTDIR)$(PKGCONFDIR)
	install -m 644 gus.h china_table.h gerarion_calendars.h gerarion.h $(DESTDIR)$(INCLUDEDIR)/gerarion/
	install -m 644 lib$(NAME).a $(DESTDIR)$(LIBDIR)/
	install -m 755 lib$(NAME).so.$(MAJOR) $(DESTDIR)$(LIBDIR)/
	ln -sf lib$(NAME).so.$(MAJOR) $(DESTDIR)$(LIBDIR)/lib$(NAME).so
	install -m 644 gerarion.pc $(DESTDIR)$(PKGCONFDIR)/

test: conformance fuzz

clean:
	rm -f gus-conformance gus-cli gus-audit-stress cal-audit \
		lib$(NAME).a lib$(NAME).so.$(MAJOR) lib$(NAME).dylib gerarion.pc \
		gus-conformance-cal gus-conformance-cal.o
