# Benchmarks

Run `make bench BENCH_ITERATIONS=10000`. The target builds with the pinned Goose
compiler, GCC and `-O2`. Override `BENCH_CC` explicitly to select another compiler.

Fixtures cover short and maximal-length version parsing, short requirements,
32-comparator requirements, maximal-length targets, equal long prerelease
comparison and prerelease matching. Input construction is outside timing.
Parsing includes owned-result construction; each iteration's values expire at
its end. Comparison/matching reuse parsed values. A verified checksum keeps
results observable, but compiler optimization and hardware still affect results.

The Python harness pins execution to one allowed CPU on supported systems,
warms one process and records seven process samples. `.build/benchmark.json`
contains every raw total, per-operation medians, iteration count, source revision
and dirty state, pinned compiler revision, C compiler version, build flags,
hardware and affinity. Generated reports stay ignored. No timing threshold is
used in CI. Warm-process measurements do not establish cold latency, allocation
counts or a universal ranking.

For a meaningful before/after comparison, use the same benchmark source, compiler
revision, compiler flags and machine for both implementations. Interleave runs
and inspect all raw samples; scheduler noise and CPU frequency changes can affect
small differences. Profile before replacing simple bounded copies with a more
complex representation.
