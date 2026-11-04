# Numeric scanning and security audit

Reviewed implementation: `e7e6282f42e3252bb088d83aefe9e01a7181357a`. The baseline is the previous implementation
`15ab97ba445993b91cc7983325cb3f8f78ba44ae` (same production source as published `e5c5092`).
Both binaries use the same expanded **25-fixture benchmark source**; the candidate
checkout was clean during measurement.

CPU: Intel(R) Core(TM) Ultra 7 258V, affinity CPU 3; Linux-7.2.11-arch1-1-x86_64-with-glibc2.44.
Goose: `eadca409f68210893f366e60d0c2f0dc29a339be`. gcc (GCC) 16.2.1 20260810, `goose build -O2`.
Nine counterbalanced pairs, one warmup per binary, 30,000 iterations per fixture;
seed 20261104. [Raw timings, source/binary hashes and ranges](results/2026-11-04-numeric.json).

The change reuses the bounded standard-library byte scanner for numeric cores
and numeric prerelease classification. Obvious leading-zero cores fail before
scanning the rest. Matching skips further eligibility lookups once eligibility
is established; every comparator still participates in the AND result.

## Measurements

Nanoseconds per operation (process medians). Ratio = candidate / baseline;
below 1 is faster for this run. All fixtures, including slower/noisy cases, are
reported. Shared-host scheduling and compiler/code layout affect small differences;
these warm measurements do not establish universal rankings or cold latency.

| Fixture | Baseline ns/op | Candidate ns/op | Ratio | Paired min–max |
| --- | ---: | ---: | ---: | ---: |
| parse_short | 91.6 | 93.0 | 1.015 | 0.951–1.080 |
| parse_long | 919.0 | 929.1 | 1.011 | 0.919–1.085 |
| requirement_short | 212.4 | 215.3 | 1.014 | 0.906–1.108 |
| requirement_many | 3364.0 | 3373.6 | 1.003 | 0.973–1.078 |
| requirement_long | 3907.9 | 3971.5 | 1.016 | 0.972–1.089 |
| compare_long_equal | 78.6 | 78.3 | 0.997 | 0.968–1.072 |
| match_prerelease | 258.6 | 260.2 | 1.006 | 0.978–1.061 |
| compare_short_equal | 37.6 | 41.0 | 1.089 | 0.990–1.202 |
| compare_short_different | 45.0 | 48.1 | 1.069 | 0.976–1.210 |
| compare_long_late_difference | 4905.0 | 4903.6 | 1.000 | 0.954–1.325 |
| compare_long_early_difference | 451.7 | 439.8 | 0.974 | 0.911–1.122 |
| compare_many_identifiers | 7709.6 | 7408.5 | 0.961 | 0.903–1.144 |
| compare_large_core | 3530.4 | 3523.7 | 0.998 | 0.960–1.094 |
| match_many_success | 559.1 | 546.8 | 0.978 | 0.934–1.103 |
| match_many_early_failure | 8.6 | 6.9 | 0.807 | 0.617–1.787 |
| reject_long | 495.4 | 511.2 | 1.032 | 0.940–1.085 |
| parse_release | 69.3 | 69.0 | 0.995 | 0.819–1.101 |
| parse_long_core | 3181.3 | 703.6 | 0.221 | 0.207–0.255 |
| parse_numeric_prerelease | 866.0 | 909.4 | 1.050 | 0.937–1.143 |
| reject_zero_core | 2681.9 | 9.5 | 0.004 | 0.003–0.004 |
| compare_numeric_prerelease_early | 4192.9 | 979.0 | 0.233 | 0.228–0.252 |
| compare_numeric_prerelease_late | 9191.6 | 4594.3 | 0.500 | 0.471–0.548 |
| match_release | 31.8 | 19.2 | 0.603 | 0.530–0.675 |
| compare_numeric_identifiers | 7120.8 | 7038.5 | 0.988 | 0.954–1.016 |
| requirement_long_many | 11007.5 | 10949.2 | 0.995 | 0.914–1.028 |

Long numeric-core parsing and early/late numeric prerelease comparisons improve
in this sample. The early-difference numeric fixture changes the first digit;
the late-difference fixture changes the last digit. Scalar lexical comparison
still determines late differences. Small short-prerelease and parsing differences
remain visible above; these measurements do not imply every path became faster.

## Security validation

- Independent oracle and targeted suites pass on TinyCC as well as native builds.
- 116,573 targeted cases per backend include every-byte edits around numeric and identifier scanner boundaries.
- 9,959 independent property cases and 11,184 hostile cases pass.
- GCC and Clang ASan/UBSan pass in debug and optimized modes.
- 47,120 protected-page/read-only input checks pass, including numeric cores and raw digit tails.
- 500,000 coverage-guided executions pass under Clang ASan/UBSan, using 329 initial seeds and a 20,481-byte envelope.
- The envelope permits a maximal 16,384-byte requirement plus NUL plus a maximal 4,096-byte candidate.
- A deliberate assertion self-test verifies Goose failures retain the exact triggering fuzz input.
- Independent source, performance and test-infrastructure reviewers found no remaining blocking defect.

[Fuzz summary and tested-source provenance](results/2026-11-04-security.json).
The longer campaign ran before commit; its tested source hash matches the
reviewed committed core. Coverage counters include generated runtime and test
code and are not a percentage. A reused writable corpus changes mutation
sequences. Cases overlap; no exhaustive-all-input or bug-free claim is made.

Reproduce the benchmark using [the paired method](README.md), with baseline
`15ab97b`. Run security tests with `make security`, the sanitizer matrix with
`make sanitize SANITIZER_CC=gcc` and `make sanitize SANITIZER_CC=clang`, and a
bounded fuzz campaign with `make fuzz FUZZ_RUNS=500000 FUZZ_SECONDS=90`.
Fuzz failures are saved under `.build/fuzz/artifacts`; replay one with
`.build/fuzz/semver-fuzzer .build/fuzz/artifacts/<artifact>`. Review potential
vulnerabilities privately before publishing triggering inputs.
