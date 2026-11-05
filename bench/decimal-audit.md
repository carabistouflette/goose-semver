# One-byte decimal comparison audit

> Historical measurement: this report predates v0.1.1. Its timings and validation
> apply only to the recorded sources, not current main or v0.1.1.
> See the [benchmark index](README.md) for current results and reproduction.

The only production change compares equal-length one-byte decimal components directly after length checks; longer components retain the existing arbitrary-magnitude path. There is no representation, allocation, grammar, ownership or resource-limit change.

Reference core: `20204c513ccd991a68d2bb294186da7ff5be3c08`. Candidate core SHA-256: `6da6de08dc5a20bfa5a2e41d03bb9e82f80d305c43b6df3ceafbd7c19164260d`. This run measured a dirty checkout based on `20204c513ccd991a68d2bb294186da7ff5be3c08`; exact source hashes were captured before build and verified unchanged afterward. The published candidate core commit `f0215a2ad2ff9a15adabc9dda494ef63bc06c79c` contains those measured bytes. The driver also verified the supplied Goose executable hash remained unchanged; its configured revision pin is not independently verified by the driver.

[Complete raw rounds, ranges, sources and executable hashes](results/2026-11-04-decimal-competitors.json) · [Method](competitors/README.md)

Nine shuffled process-order rounds, 200,000 operations per fixture, 64 rotating rows per fixture (2,048 range-cache-miss rows), all per-row outcomes and aggregate checksums verified. The one-byte control repeats nine adjacent unordered numeric pairs with alternating comparison directions; its 64 rows are not distinct inputs. Native opaque observation overhead is included, never subtracted. Rust semver 1.0.28 and npm semver 7.8.6 are lockfile-pinned.

| Fixture | Goose before | Goose after | Rust | npm |
| --- | ---: | ---: | ---: | ---: |
| parse_release | 35.87 | 36.32 | 27.00 | 272.56 |
| parse_pre_short | 52.52 | 52.39 | 73.49 | 1045.55 |
| parse_pre_long | 99.58 | 100.30 | 360.76 | 1868.45 |
| parse_build_long | 79.62 | 80.10 | 477.81 | 1092.75 |
| parse_invalid | 28.88 | 28.78 | 30.51 | 6508.57 |
| compare_release | 12.06 | 11.14 | 5.04 | 21.60 |
| compare_onebyte_core | 11.04 | 5.89 | 4.99 | 20.13 |
| compare_multidigit_core | 22.94 | 21.95 | 5.02 | 19.76 |
| compare_multidigit_equal | 14.39 | 14.66 | 5.90 | 17.68 |
| compare_pre | 13.60 | 10.96 | 28.10 | 66.22 |
| compare_equal_build | 15.94 | 12.91 | 6.17 | 50.22 |
| compare_long_pre_early | 13.43 | 11.17 | 89.20 | 255.56 |
| compare_long_pre_late | 132.27 | 124.57 | 96.60 | 332.15 |
| requirement_exact_warm | 95.54 | 96.40 | 54.59 | 744.58 |
| requirement_caret_warm | 96.45 | 97.82 | 53.86 | 700.79 |
| requirement_and_warm | 131.70 | 131.44 | 73.93 | 1039.76 |
| match_release | 20.59 | 15.92 | 8.22 | 205.50 |
| match_prerelease | 41.81 | 34.73 | 39.44 | 252.43 |
| match_reject | 12.59 | 12.18 | 6.20 | 225.51 |
| match_many | 222.25 | 193.44 | 85.45 | 1534.32 |
| requirement_caret_miss | 91.80 | 89.67 | 54.83 | 13856.11 |

Values are median nanoseconds per operation, lower is better. All fixtures, including regressions, are retained. The explicit one-byte control and release/prerelease matching improve. All-multi-digit equality is slightly slower; npm also has a lower median on the all-multi-digit unequal-core control. Small gaps are not treated as statistically significant or intrinsic function costs. The candidate does not universally outperform Rust or npm.

## Every observed process range

| Fixture | Goose before min–max | Goose after min–max | Rust min–max | npm min–max |
| --- | ---: | ---: | ---: | ---: |
| parse_release | 34.06–71.72 | 32.50–72.12 | 26.01–43.97 | 256.10–565.18 |
| parse_pre_short | 48.66–123.79 | 48.62–102.08 | 69.62–147.25 | 1021.19–2093.68 |
| parse_pre_long | 94.98–209.30 | 94.42–205.15 | 335.08–714.87 | 1817.38–3734.96 |
| parse_build_long | 75.39–294.72 | 78.45–158.70 | 451.88–953.00 | 1043.91–2170.05 |
| parse_invalid | 26.47–59.23 | 26.97–60.21 | 27.71–57.90 | 6325.66–13612.71 |
| compare_release | 11.67–22.10 | 10.94–22.51 | 4.78–5.56 | 18.91–24.36 |
| compare_onebyte_core | 10.39–11.18 | 5.69–6.50 | 4.71–5.03 | 18.34–21.02 |
| compare_multidigit_core | 21.23–44.14 | 19.87–46.20 | 4.70–5.06 | 18.65–49.25 |
| compare_multidigit_equal | 13.23–26.75 | 13.66–40.38 | 5.47–6.95 | 16.67–51.74 |
| compare_pre | 12.46–18.73 | 10.38–12.10 | 26.06–44.22 | 57.03–126.70 |
| compare_equal_build | 15.07–21.68 | 12.24–20.57 | 5.47–11.74 | 14.31–62.00 |
| compare_long_pre_early | 12.39–27.97 | 10.48–25.86 | 80.55–175.72 | 236.34–524.83 |
| compare_long_pre_late | 127.03–262.02 | 117.94–247.59 | 90.94–200.18 | 322.29–705.81 |
| requirement_exact_warm | 94.30–196.38 | 92.21–190.86 | 51.16–97.99 | 714.75–791.48 |
| requirement_caret_warm | 92.52–195.93 | 93.10–190.86 | 50.83–105.61 | 659.57–822.00 |
| requirement_and_warm | 127.58–275.88 | 127.91–270.28 | 70.47–146.12 | 985.20–1182.44 |
| match_release | 19.01–36.83 | 15.06–31.38 | 7.57–8.45 | 197.00–431.71 |
| match_prerelease | 39.84–88.01 | 33.05–78.21 | 37.64–68.49 | 230.95–521.66 |
| match_reject | 12.40–27.59 | 11.64–26.29 | 5.86–6.62 | 208.83–450.11 |
| match_many | 212.72–456.30 | 188.92–409.73 | 83.05–167.91 | 1410.31–3334.42 |
| requirement_caret_miss | 86.32–194.79 | 86.40–191.31 | 49.97–102.94 | 13623.97–26777.10 |

## Environment and limits

Intel(R) Core(TM) Ultra 7 258V; affinity CPU 2; Linux-7.2.11-arch1-1-x86_64-with-glibc2.44. gcc (GCC) 16.2.1 20260810; rustc 1.101.0-nightly (822182db4 2026-10-13); Node v26.13.0. Goose uses GCC -O2 with separate barrier TU/no LTO; Rust uses release opt3/thin LTO/one codegen unit. No exclusive-host isolation or CPU-native tuning is claimed. Other heavy local semver checks were deferred until timing finished. Frequency, allocator, caches and shared-host activity can affect samples.

The new controls extend the previous 18-fixture shared corpus to 21 fixtures and 3,328 rows. Inputs remain within shared strict ASCII/full-version/numeric limits. Comparisons and matches are preparsed. npm range caching and Node JIT warmup remain enabled as documented. Historical reports retain their original corpus and source identity.

Reproduce with `make bench-compare COMPARE_ITERATIONS=200000 COMPARE_ROUNDS=9 COMPARE_FLAGS="--cpu 2 --reference 20204c5"` using the published candidate core and matching toolchain. This measures public operations with differing representations and observation overhead, not a universal ranking or cold-start/allocation result.


## Correctness and security validation

Public API tests passed through in-process, optimized and debug/no-BCE builds. The independent Python property/hostile suites and 147,582 targeted cases passed on native optimized/debug, TinyCC, and GCC/Clang ASan/UBSan debug/optimized paths. Both Goose and pinned Rust independently matched the model on 59,176 shared-domain cases. Read-only protected-page checks passed 47,120 cases. A new-seed (271828182) Clang/libFuzzer+ASan/UBSan campaign completed 969,112 runs in 61 seconds, with a reused writable corpus; the source/compiler fingerprint and assertion-artifact self-test passed. Two independent reviewers found no blocking issue. These checks do not prove absence of defects.
