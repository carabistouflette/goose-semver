# Requirement token scanner audit

Measured candidate `33abbfb4de59276e707eec7eabbfa2a6834ce356` against `7f95a8af8c84a439fe250dc8fa86ada638ea3037` with the identical 25-fixture harness, pinned Goose compiler and GCC `-O2`.

Nine counterbalanced pairs, one warm process per binary, 100,000 iterations per fixture, CPU 1 affinity on Intel(R) Core(TM) Ultra 7 258V. This is a shared host, without exclusive isolation. Every checksum passed. The checkout was clean during measurement. Binary/source hashes, all samples and caller-supplied build provenance are in the [raw record](results/2026-11-04-token-scan.json).

The only production change uses the existing bounded standard byte-set scanner to find comma, ASCII space or tab after a short scalar prefix. It preserves newline/NUL rejection, ownership, offsets and input/comparator limits. No eligibility prepass or representation change was added.

| Fixture | Before ns/op | After ns/op | After/before | Paired ratio range |
| --- | ---: | ---: | ---: | ---: |
| parse_short | 57.0 | 57.6 | 1.011 | 0.883–1.092 |
| parse_long | 818.0 | 785.8 | 0.961 | 0.853–1.076 |
| requirement_short | 96.8 | 93.0 | 0.961 | 0.880–1.148 |
| requirement_many | 1756.5 | 1742.9 | 0.992 | 0.919–1.089 |
| requirement_long | 3814.5 | 1401.0 | 0.367 | 0.358–0.421 |
| compare_long_equal | 77.7 | 74.9 | 0.964 | 0.899–1.040 |
| match_prerelease | 34.9 | 34.9 | 1.001 | 0.808–1.077 |
| compare_short_equal | 10.6 | 9.6 | 0.911 | 0.828–1.205 |
| compare_short_different | 52.7 | 52.3 | 0.992 | 0.809–1.098 |
| compare_long_late_difference | 864.4 | 853.3 | 0.987 | 0.904–1.110 |
| compare_long_early_difference | 8.3 | 7.9 | 0.956 | 0.932–1.141 |
| compare_many_identifiers | 7788.0 | 7667.3 | 0.985 | 0.931–1.206 |
| compare_large_core | 262.6 | 263.1 | 1.002 | 0.957–1.271 |
| match_many_success | 574.7 | 551.6 | 0.960 | 0.894–1.310 |
| match_many_early_failure | 8.0 | 8.0 | 0.993 | 0.776–1.415 |
| reject_long | 502.0 | 483.1 | 0.962 | 0.876–1.141 |
| parse_release | 19.5 | 18.9 | 0.970 | 0.899–1.070 |
| parse_long_core | 464.0 | 456.0 | 0.983 | 0.897–1.184 |
| parse_numeric_prerelease | 764.5 | 724.7 | 0.948 | 0.867–1.131 |
| reject_zero_core | 2.5 | 2.5 | 0.987 | 0.884–1.240 |
| compare_numeric_prerelease_early | 974.7 | 969.3 | 0.994 | 0.710–1.409 |
| compare_numeric_prerelease_late | 1330.2 | 1316.5 | 0.990 | 0.895–1.298 |
| match_release | 20.1 | 20.7 | 1.032 | 0.947–1.443 |
| compare_numeric_identifiers | 7541.2 | 7450.3 | 0.988 | 0.932–1.144 |
| requirement_long_many | 10459.4 | 3555.4 | 0.340 | 0.313–0.406 |

Long-target requirements show a consistent reduction across pairs. Small changes elsewhere overlap substantial host noise and are not claimed as improvements; all regressions and ranges remain above. These timings do not establish universal rankings, cold latency or allocation counts. The [Rust/npm comparison](competitor-results.md) remains a separately identified historical measurement of its recorded source revision.

Validation: public API tests through in-process, optimized and debug/no-BCE builds; 59,176 shared-domain cases against both pinned Rust semver and the independent Python model; 147,282 targeted cases per tested backend; hostile/property suites; GCC and Clang ASan/UBSan in debug and optimized builds; 47,120 read-only protected-page checks; and 500,000 coverage-guided fuzz runs. Independent security and performance reviewers found no blocking defect. These checks do not prove absence of bugs.

Reproduce using the paired command in [bench/README.md](README.md), substituting baseline revision `7f95a8a`, and using this measured commit for the candidate. Keep the current benchmark source identical for both builds.
