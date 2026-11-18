# impl-c Makefile — núcleo GUS en C11 (segunda implementación independiente)

CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -pedantic

.PHONY: all conformance audit fuzz clean test

all: gus-conformance gus-cli

gus-conformance: conformance.c gus.c gus.h
	$(CC) $(CFLAGS) -o $@ conformance.c gus.c

gus-cli: gus-cli.c gus.c gus.h
	$(CC) $(CFLAGS) -o $@ gus-cli.c gus.c

# Auditoría adversarial: ASan + UBSan (sin recover) sobre el runner de
# conformancia y el harness de estrés. Requiere clang/gcc con sanitizadores.
SANFLAGS = -fsanitize=address,undefined -fno-sanitize-recover=all
audit: gus-audit-stress
	# Nota: detect_leaks no está disponible con ASan en macOS; en Linux CI
	# exportar ASAN_OPTIONS=detect_leaks=1 para verificar además 0 fugas.
	ASAN_OPTIONS=halt_on_error=1 ./gus-audit-stress \
		../vectors/gus-normative-003.json \
		../vectors/gus-3339-negative-001.json \
		../vectors/gus-regression-001.json \
		../vectors/gus-quickverify-001.json

gus-audit-stress: audit_stress.c conformance.c gus.c gus.h
	$(CC) -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic $(SANFLAGS) -o $@ audit_stress.c gus.c

conformance: gus-conformance
	./gus-conformance ../vectors/gus-normative-003.json ../vectors/gus-3339-negative-001.json ../vectors/gus-regression-001.json ../vectors/gus-quickverify-001.json

fuzz: gus-cli
	python3 ../tools/fuzz_diff.py

test: conformance fuzz

clean:
	rm -f gus-conformance gus-cli gus-audit-stress
