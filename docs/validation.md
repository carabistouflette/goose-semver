# Documentation and example checks

The documentation audit uses public v0.1.1,
`2311ae69a7edacb545f284b02e345be07dd2fb05`, as its behavior reference.
Main's library source, examples, compiler pin and benchmark adapters are
byte-for-byte equal to that release. Only the benchmark driver adds an optional
prepare/reuse phase; it does not change the timed operations or inputs.
[Source hashes and historical report identities](validation.json) record the
checked files. This is source equality, not a claim that independently compiled
binaries must be identical.

## Reader documentation

The audit covers every maintained Markdown file: the README, API and Git-tag
guides; contribution, security, license notices and changelog; the benchmark
index and competitor method; and the five historical benchmark reports.
The README now has a pinned quickstart, API summary, support and limits.
Detailed test/fuzz behavior is in [testing.md](testing.md). The API guide retains
ownership, byte errors, prerelease rules and the exact resource bounds.
Third-party notices were checked and remain unchanged. License terms are unchanged.

The historical reports retain their full tables and raw artifacts. All 654
printed numeric table values were checked against their recorded medians,
ratios and ranges, allowing only the displayed rounding. They are explicitly
labeled as measurements of older sources. Their dates do not establish
currentness. No historical raw report was rewritten.

## Executed examples and tests

A fresh public HTTPS clone at v0.1.1 and the documentation checkout both passed
`make check test GOOSE=/absolute/path/to/goose`. The reused compiler's clean Git
source matches the full revision in `GOOSE_REVISION`. This runs the examples in-process and checks the public API and caller-overload
cases in-process and in native optimized/debug builds. It does not claim a new compiler bootstrap or a new full fuzz campaign.

The pinned quickstart prints:

```text
1.4.2+build.7 matches: true
```

The tag example prints two true and two false results and asserts that malformed
prefixes remain invalid. The example sources are unchanged from the release.
The README full-SHA remote import also ran successfully with the same output.
Relative Markdown links were checked. The preparation-manifest mismatch test
rejects a changed compiler selection before any benchmark executable runs.

## Performance scope

The [v0.1.1 comparison](../bench/v0.1.1-results.md) completed all nine rounds
with every checksum passing, in one 135.322-second invocation. No artifact was
rebuilt for timing and no retry was run. All current medians and observed ranges
are retained. The [benchmark index](../bench/README.md) separates current and historical
measurements. Compiler executable/source identities, lockfiles, corpus, adapter
binaries and installed Node dependency hashes are retained in the preparation
record. The reused compiler was not rebuilt or independently attested.
Results do not measure cold starts or allocation counts and do not promise
universal performance, compatibility with Cargo/npm grammar, or bug-free code.
Only Linux x86-64 with the pinned Goose compiler, GCC and Clang is validated.
Other platforms remain untested; runtime allocation-failure recovery is not promised.
