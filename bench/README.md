# Benchmarks

The benchmark results describe specific inputs on one shared Linux machine.
They are not an overall ranking or a prediction of application performance.
Comparison and matching reuse parsed values. Parsing includes result creation
and disposal. Full methods, source identities, raw samples and slower results
are retained in each report.

## Released baseline

[v0.1.1 results](v0.1.1-results.md) measure the library at
`2311ae69a7edacb545f284b02e345be07dd2fb05` on 21 shared-domain fixtures with
Rust semver 1.0.28 and npm semver 7.8.6. Every median and observed range is shown.
The checked source bridge covers current main's unchanged library, compiler pin,
corpus, timed adapters and dependency locks. Older reports below measure sources
from before v0.1.1's copy/formatting/scanner fixes and remain historical.

This branch changes lexical comparison. The historical source bridge does not
extend those measurements to the changed comparison path. The focused
[lexical method](lexical-method.md) describes its paired driver, interpretation
limits and required disclosure of slower fixtures.

## Reproduce

With the pinned Goose compiler and the tools described in
[the comparison method](competitors/README.md):

```sh
make bench-compare COMPARE_ITERATIONS=200000 COMPARE_ROUNDS=9 \
  COMPARE_FLAGS='--cpu 2'
```

Choose a CPU allowed by your process affinity. Add `GOOSE=/absolute/path/to/goose`
if using an installed matching compiler. This runs Goose, lockfile-pinned Rust
semver 1.0.28 and npm semver 7.8.6 on the same 21 fixtures. Every row is validated
before timing, and every aggregate checksum is checked afterward.
`.build/competitors/results.json` contains all nine shuffled rounds, medians,
min/max, source/binary hashes, compiler versions and machine details. Run from a
clean checkout and preserve that report. CI's small counts only check execution;
they are not performance results.

For the separate 25-fixture Goose-only harness:

```sh
make bench BENCH_ITERATIONS=10000
```

It builds with GCC `-O2` by default (`BENCH_CC` overrides it), warms one process
and records seven process samples in `.build/benchmark.json`. Use `BENCH_CPU` to
choose an allowed CPU. Inputs are built outside timing; parsed comparison/match
inputs are reused. Short equality uses separately parsed values. Checksums keep
results observable, but compiler optimization and scheduling still affect them.

For before/after experiments, build both library revisions with an identical
benchmark source, Goose compiler and C flags. For example, to reproduce the
historical numeric comparison, check out `e7e6282f42e3252bb088d83aefe9e01a7181357a`
and follow [its report](numeric-audit.md). The pair driver is
`scripts/compare-bench.py`: it warms each binary, checks fixture/count/checksum
agreement and records nine counterbalanced pairs in `.build/comparison.json`.
Caller-supplied build descriptions are not proof of source identity; retain the
source and binary hashes too.

At that historical candidate checkout, its exact paired build can be reconstructed
with these commands after compiler setup:

```sh
mkdir -p .build/baseline-source/bench
git show 15ab97ba445993b91cc7983325cb3f8f78ba44ae:semver.goose > .build/baseline-source/semver.goose
cp bench/bench.goose .build/baseline-source/bench/bench.goose
.toolchain/goose/build/goose build .build/baseline-source/bench/bench.goose --cc gcc -O2 -o .build/baseline
.toolchain/goose/build/goose build bench/bench.goose --cc gcc -O2 -o .build/candidate
python3 scripts/compare-bench.py .build/baseline .build/candidate 30000 --baseline-revision 15ab97ba445993b91cc7983325cb3f8f78ba44ae
```

These historical commands are provided for reproduction, not executed as part
of the documentation refresh. They do not remeasure the current release.


## Historical reports

These are results for the recorded earlier sources, not v0.1.1 or current main.
Raw reports are preserved unchanged, including noisy and slower results.

| Report | Scope |
| --- | --- |
| [Decimal comparison](decimal-audit.md) | 21 competitive fixtures, before the v0.1.1 fixes |
| [Rust/npm comparison](competitor-results.md) | Earlier 18-fixture competitive corpus |
| [Requirement scanner](token-audit.md) | 25 paired Goose-only fixtures |
| [Numeric scanner](numeric-audit.md) | 25 paired Goose-only fixtures |
| [Original parser](results.md) | Original 16-fixture paired snapshot |

The retained CPU3 competitive run had suspected shared-core contention. No run
claims exclusive host isolation. Affinity does not remove frequency, allocator,
GC or scheduling effects. No cold-start latency or allocation counts were measured.
