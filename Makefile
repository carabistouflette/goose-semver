GOOSE ?= .toolchain/goose/build/goose
CC ?= gcc
SANITIZER_CC ?= gcc
BENCH_CC ?= gcc
BENCH_ITERATIONS ?= 10000
FUZZ_CC ?= clang
FUZZ_RUNS ?= 100000
FUZZ_SECONDS ?= 30
FUZZ_SEED ?= 20261104
COMPARE_ITERATIONS ?= 100000
COMPARE_ROUNDS ?= 9
.NOTPARALLEL:
.PHONY: setup format check test property security sanitize bench jit-security fuzz
setup:
	./scripts/setup-goose.sh
format:
	"$(GOOSE)" format semver.goose tests examples bench
check:
	"$(GOOSE)" format --check semver.goose tests examples bench
	"$(GOOSE)" check tests/api.goose
	"$(GOOSE)" check tests/fuzz.goose
	"$(GOOSE)" check tests/oracle.goose
	"$(GOOSE)" check examples/versions.goose
	"$(GOOSE)" check bench/bench.goose
test:
	mkdir -p .build
	"$(GOOSE)" run tests/api.goose
	"$(GOOSE)" build tests/api.goose --cc "$(CC)" -O2 -o .build/api
	./.build/api
	"$(GOOSE)" build tests/api.goose --cc "$(CC)" --debug --no-bce -o .build/api-debug
	./.build/api-debug
	"$(GOOSE)" run examples/versions.goose
property:
	mkdir -p .build
	"$(GOOSE)" build tests/oracle.goose --cc "$(CC)" -O2 -o .build/oracle
	python3 tests/model.py .build/oracle
	"$(GOOSE)" build tests/oracle.goose --cc "$(CC)" --debug --no-bce -o .build/oracle-debug
	python3 tests/model.py .build/oracle-debug
jit-security:
	GOOSE="$(abspath $(GOOSE))" python3 tests/model.py scripts/jit-oracle.sh --security
	GOOSE="$(abspath $(GOOSE))" python3 tests/exhaustive.py scripts/jit-oracle.sh
security: property jit-security
	python3 tests/exhaustive.py .build/oracle
	python3 tests/exhaustive.py .build/oracle-debug
	python3 tests/model.py .build/oracle --security
	python3 tests/model.py .build/oracle-debug --security
sanitize:
	mkdir -p .build
	SANITIZER_CC="$(SANITIZER_CC)" "$(GOOSE)" build tests/api.goose --cc "$(abspath scripts/sanitizer-cc.sh)" --standalone --debug --no-bce -o .build/api-sanitize
	ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 ./.build/api-sanitize
	SANITIZER_CC="$(SANITIZER_CC)" "$(GOOSE)" build tests/oracle.goose --cc "$(abspath scripts/sanitizer-cc.sh)" --standalone --debug --no-bce -o .build/oracle-sanitize
	ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 python3 tests/model.py .build/oracle-sanitize --security
	ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 python3 tests/exhaustive.py .build/oracle-sanitize
	SANITIZER_CC="$(SANITIZER_CC)" "$(GOOSE)" build tests/api.goose --cc "$(abspath scripts/sanitizer-cc.sh)" --standalone -O2 --no-bce -o .build/api-sanitize-optimized
	ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 ./.build/api-sanitize-optimized
	SANITIZER_CC="$(SANITIZER_CC)" "$(GOOSE)" build tests/oracle.goose --cc "$(abspath scripts/sanitizer-cc.sh)" --standalone -O2 --no-bce -o .build/oracle-sanitize-optimized
	ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 python3 tests/model.py .build/oracle-sanitize-optimized --security
	ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 python3 tests/exhaustive.py .build/oracle-sanitize-optimized
bench:
	mkdir -p .build
	"$(GOOSE)" build bench/bench.goose --cc "$(BENCH_CC)" -O2 -o .build/bench
	BENCH_CC="$(BENCH_CC)" python3 scripts/benchmark.py .build/bench $(BENCH_ITERATIONS)

fuzz:
	python3 scripts/fuzz.py --goose "$(abspath $(GOOSE))" --cc "$(FUZZ_CC)" --runs $(FUZZ_RUNS) --seconds $(FUZZ_SECONDS) --seed $(FUZZ_SEED)

.PHONY: bench-compare differential
bench-compare:
	python3 bench/competitors/run.py --goose "$(abspath $(GOOSE))" --cc "$(BENCH_CC)" --iterations $(COMPARE_ITERATIONS) --rounds $(COMPARE_ROUNDS) $(COMPARE_FLAGS)
differential:
	mkdir -p .build
	"$(GOOSE)" build tests/oracle.goose --cc "$(CC)" -O2 -o .build/oracle
	python3 tests/rust_differential.py .build/oracle "$$(python3 bench/competitors/rust_build.py --bin oracle)"
