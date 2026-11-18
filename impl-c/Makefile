# impl-c Makefile — núcleo GUS en C11 (segunda implementación independiente)

CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -pedantic

.PHONY: all conformance fuzz clean test

all: gus-conformance gus-cli

gus-conformance: conformance.c gus.c gus.h
	$(CC) $(CFLAGS) -o $@ conformance.c gus.c

gus-cli: gus-cli.c gus.c gus.h
	$(CC) $(CFLAGS) -o $@ gus-cli.c gus.c

conformance: gus-conformance
	./gus-conformance ../vectors/gus-normative-002.json ../vectors/gus-3339-negative-001.json ../vectors/gus-regression-001.json ../vectors/gus-quickverify-001.json

fuzz: gus-cli
	python3 ../tools/fuzz_diff.py

test: conformance fuzz

clean:
	rm -f gus-conformance gus-cli
