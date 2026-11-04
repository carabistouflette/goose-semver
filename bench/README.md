# Benchmarks

[Competitive Rust/npm results](competitor-results.md) · [Reproduce the comparison](competitors/README.md)

Run `make bench BENCH_ITERATIONS=10000`. It builds with the pinned Goose compiler,
GCC and `-O2`; override `BENCH_CC` to select another compiler. `BENCH_CPU` can
select an allowed CPU explicitly; otherwise the first allowed CPU is used.

The twenty-five fixtures cover short and maximal-length version parsing, short,
32-comparator and long-target requirements; equal, early/late-differing and
many-identifier prereleases; large numeric cores; many-comparator success and
early failure; and late rejection of a maximal-length version, numeric-core parsing, long numeric
prerelease comparison at both ends, early leading-zero rejection, release matching
and repeated long targets. Short equality
uses separately parsed values. Inputs are constructed outside timing. Parsing
includes owned-result construction; each iteration's values expire at its end.
Comparison/matching reuse parsed values. A verified checksum keeps results
observable, but compiler optimization and hardware still affect measurements.

The single-binary harness warms one process and records seven process samples.
`.build/benchmark.json` retains every raw total, per-operation medians, iteration
count, source revision/dirty state, compiler revision/version, flags, hardware
and affinity. Generated builds stay ignored. There is no CI timing threshold.

## Before/after measurements

[Latest requirement-token audit](token-audit.md), [numeric/security audit](numeric-audit.md) and [original snapshot](results.md) include every fixture and raw paired samples.
These are internal before/after measurements on one machine and workload corpus.
They do not establish cold latency, allocation counts or a universal ranking.

Build the original parser with the **current benchmark source**, then the current
parser with the same Goose/C compiler and flags. From this checkout after setup:

```sh
mkdir -p .build/baseline-source/bench
git show 15ab97b:semver.goose > .build/baseline-source/semver.goose
cp bench/bench.goose .build/baseline-source/bench/bench.goose
.toolchain/goose/build/goose build .build/baseline-source/bench/bench.goose --cc gcc -O2 -o .build/baseline
.toolchain/goose/build/goose build bench/bench.goose --cc gcc -O2 -o .build/candidate
python3 scripts/compare-bench.py .build/baseline .build/candidate 30000 --baseline-revision 15ab97b
```

Optionally set `BENCH_CPU` before the final command. The comparison harness pins
the process and its children to that CPU, warms both binaries and runs nine
counterbalanced pairs with a fixed random seed. It validates identical fixtures,
counts and checksums. `.build/comparison.json` records every raw pair, paired
ratios and range, medians, source/binary hashes, revisions, compiler information
and hardware. Artifact names omit private filesystem paths. Build provenance is
caller-supplied; binary hashes identify exactly what was measured.

All fixtures, including regressions and wide variation, must remain visible.
Scheduler load and CPU frequency can affect small differences even with affinity;
inspect paired ranges rather than treating each median as a precise guarantee.
Profile before replacing simple bounded copies with a more complex representation.

The original 16-fixture snapshot used the benchmark/harness from `deb55af`.
Use that revision to reproduce its exact fixture set; the current harness validates
the expanded 25-fixture checksum and compares against the previous numeric implementation.
