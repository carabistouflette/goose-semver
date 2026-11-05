# Testing

Use the compiler revision in [GOOSE_REVISION](../GOOSE_REVISION).
From the repository root, `make setup` builds it under `.toolchain/goose`.
To reuse a matching installed compiler, add `GOOSE=/absolute/path/to/goose` to
any Make command below. Python 3.11+ is needed for the test drivers.

```sh
make check test
make security
make differential
make sanitize SANITIZER_CC=gcc
make sanitize SANITIZER_CC=clang
make fuzz FUZZ_RUNS=100000 FUZZ_SECONDS=30 FUZZ_SEED=20261104
```

`check` verifies formatting, types and fuzz-report handling. `test` runs the API,
caller-overload regressions and examples through the in-process runner and native
optimized/debug builds. `security` adds the independent Python model, hostile
inputs and targeted byte/scanner-boundary edits. These checks overlap; case
counts do not mean exhaustive coverage.

`differential` needs Rust/Cargo and may download lockfile-pinned Rust semver
1.0.28. Both libraries are checked against the Python model on their shared
full-version grammar and numeric domain. Known grammar/range differences are
excluded rather than treating Rust as the specification.

Sanitizers need Linux GCC or Clang with ASan/UBSan runtimes. They instrument
native debug/no-BCE and optimized builds. In-process tests separately exercise
the standard scanner's TinyCC fallback. Linux in-process execution needs libc
development headers.

## Fuzzing

`make fuzz` needs Clang/libFuzzer and Linux protected-page APIs. Its native host
is test-only. It checks read-only protected slices and metamorphic invariants;
it complements the independent model. The assertion-to-crash bridge is tested
before the mutation campaign. Changing `FUZZ_RUNS`, `FUZZ_SECONDS` or `FUZZ_SEED`
changes its bounds or seed. Reusing a writable corpus changes the mutation stream.

Reports, logs, reusable corpus and exact failures stay under `.build/fuzz`.
The driver hashes project inputs and compiler executables before building and
checks them again before writing a success report. It records executable hashes,
but does not independently prove that an arbitrary supplied compiler was built
from the requested revision. A new run removes the old success summary first.

The [weekly workflow](../.github/workflows/fuzz.yml) uses two date-derived seeds
on Mondays at 03:37 UTC; GitHub may delay scheduling. Each campaign is bounded by
five minutes or five million executions. Manual runs can override the base seed
and bounds, up to 600 seconds. Artifacts are retained for 14 days. Uploads include
hidden files only in the fixed report/corpus/failure paths. Completed campaigns
require nonempty summary, run and self-test reports. Early failures retain any
available files; failures before any report skip an empty upload.

Tests and fuzz campaigns improve confidence; they do not prove absence of bugs.
Use [private reporting](../SECURITY.md) for sensitive failures, since public CI
logs and artifacts can expose their inputs.
