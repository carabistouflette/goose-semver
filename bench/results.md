# Measured results

A later [numeric/security audit](numeric-audit.md) records the current 25-fixture
comparison. This original 16-fixture snapshot retains its measured source provenance.

Measured on 2026-11-04: original parser `23ed238a77e6476b3706b280d6807629ddcecfe9` against candidate
`deb55af08689d53058ce114c2072a4393232b410` using the same expanded benchmark source.
The candidate checkout was clean. Core implementation: `f35ef9f`.

CPU: Intel(R) Core(TM) Ultra 7 258V; affinity CPU 3.
Platform: Linux-7.2.11-arch1-1-x86_64-with-glibc2.44.
Goose: `eadca409f68210893f366e60d0c2f0dc29a339be`. C compiler: gcc (GCC) 16.2.1 20260810.
Flags: `goose build -O2`. Each process uses 30,000 iterations per fixture;
one warmup per binary, 9 counterbalanced process pairs; seed 20261104.

[Raw pairs, hashes and metadata](results/2026-11-04.json) · [Reproduction commands](README.md)

Numbers are nanoseconds per operation (process medians). Ratio is candidate /
baseline: below 1 is faster on this run. Every fixture and paired ratio range is
reported, including regressions. These are warm measurements on a shared machine;
they do not establish cold latency, allocation counts, or a universal ranking.

| Fixture | Baseline ns/op | Candidate ns/op | Ratio | Paired min–max |
| --- | ---: | ---: | ---: | ---: |
| parse_short | 89.4 | 94.0 | 1.052 | 0.938–1.163 |
| parse_long | 8348.1 | 924.2 | 0.111 | 0.107–0.119 |
| requirement_short | 211.9 | 209.6 | 0.989 | 0.894–1.204 |
| requirement_many | 3230.3 | 3401.2 | 1.053 | 0.922–1.254 |
| requirement_long | 11800.2 | 4000.8 | 0.339 | 0.319–0.440 |
| compare_long_equal | 4900.6 | 77.2 | 0.016 | 0.014–0.017 |
| match_prerelease | 1817.4 | 256.8 | 0.141 | 0.124–0.154 |
| compare_short_equal | 37.8 | 39.9 | 1.056 | 0.957–1.244 |
| compare_short_different | 41.2 | 44.8 | 1.089 | 1.039–1.274 |
| compare_long_late_difference | 9076.6 | 4931.5 | 0.543 | 0.508–0.587 |
| compare_long_early_difference | 3627.9 | 431.9 | 0.119 | 0.111–0.128 |
| compare_many_identifiers | 8244.9 | 7594.6 | 0.921 | 0.885–1.005 |
| compare_large_core | 3495.4 | 3831.3 | 1.096 | 1.003–1.159 |
| match_many_success | 1043.5 | 570.6 | 0.547 | 0.479–0.656 |
| match_many_early_failure | 372.5 | 8.5 | 0.023 | 0.018–0.033 |
| reject_long | 5307.1 | 505.9 | 0.095 | 0.091–0.108 |

The bounded standard-library scanner primarily improves long identifiers,
prerelease comparisons and late invalid-input rejection. Putting the validity flag before variable-sized data
improves early requirement rejection. Short unequal prerelease comparisons and
large numeric-core comparison are slower in this sample; the latter code path
is algorithmically unchanged, so layout, compiler decisions and scheduling can
affect the measurement. Small differences should not be treated as guarantees.

The source and binary hashes in the raw record identify the measured artifacts.
The baseline uses the original core with the current benchmark source; this is
an internal before/after experiment, not a comparison with another library.

## Validation on this implementation

- Public tests: in-process, optimized native and debug native execution.
- Independent oracle: 9,959 property cases and 11,184 hostile cases on optimized/debug builds.
- Targeted exhaustive neighborhoods: 90,461 cases, including every-byte scanner boundary edits.
- GCC and Clang ASan/UBSan: public, hostile and targeted suites in debug/optimized builds.
- Additional seeded mutation sweeps: 138,461 cases each, seeds 219 (optimized) and 828 (Clang optimized ASan/UBSan).
- Fresh standalone clone: check/test with the exact pinned existing compiler.
- Independent adversarial and performance reviews: no remaining blocking findings.

Counts describe executed cases and include overlap; they are not unique-input or
exhaustive-all-input claims. No sanitizer findings were observed in these runs.
