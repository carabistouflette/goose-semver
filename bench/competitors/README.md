# Reproducing competitive benchmarks

The optional harness compares this library with exact, lockfile-pinned Rust
`semver` **1.0.28** and npm `semver` **7.8.6**. It does not add runtime dependencies
to the Goose library or vendor third-party implementations.

Requires the pinned Goose compiler, GNU-compatible C compiler, Rust/Cargo and
Node/npm. The exact tested runtime/compiler versions appear in the raw report.
From a normal full-history clone after `make setup`:

```sh
make bench-compare COMPARE_ITERATIONS=200000 COMPARE_ROUNDS=9 \
  COMPARE_FLAGS='--cpu 1 --reference b7dc3aa'
```

The driver explicitly selects rustc's native host target and consumes Cargo's
JSON executable artifact for the named adapter. Inherited `CARGO_BUILD_TARGET`
or `build.target` cannot silently select a stale native binary. Cross compilation
is outside this harness. `make differential` uses the same build helper for its
separate Rust semantic oracle.

Omit `--reference` for a three-engine run; it adds the older Goose implementation
using the **same current harness**. Reference names are resolved to full commits.
On a shallow clone, fetch the reference history before using that option.
`npm ci --ignore-scripts` and `cargo build --locked` enforce lockfile versions.
All generated source, dependency caches and binaries remain ignored under
`.build/competitors`, `node_modules` or Cargo's external target directory.

## Comparable workloads

`corpus.py` generates 18 fixtures and 3,136 rows. Most fixtures rotate 64 variants;
the range-cache-miss fixture rotates 2,048 distinct constraints. Unequal
comparisons alternate directions. Every adapter validates each row before timing
and validates the full timed checksum afterward.

The common corpus uses ASCII full versions, at most 256 bytes (currently 208),
and safe-integer **core and numeric prerelease** components. Requirements use
explicit operators/full versions and AND only. npm receives comma-to-space
conjunction normalization before timing. No loose parser option is enabled;
that does not imply the libraries have identical rejection grammars.

- **Parse:** complete result construction and observation occur inside timing.
  Native owned results are dropped per iteration. Node allocation/GC behavior
  is measured as it occurs; its last result remains reachable through the sink.
  Invalid examples are rejected by every engine. Goose owns all decimal
  core/suffix bytes. Rust stores numeric cores and can inline short suffixes.
  Node uses numbers and may retain immutable input strings; allocation/GC belongs
  to its measured behavior.
- **Comparison:** both versions are parsed before timing. Rust uses
  [`cmp_precedence`](https://docs.rs/semver/1.0.28/semver/struct.Version.html#method.cmp_precedence),
  which ignores build metadata, rather than ordinary `Ord`.
- **Requirement parse:** native libraries parse on every call. npm's default
  [range cache](https://github.com/npm/node-semver/blob/v7.8.6/classes/range.js)
  remains enabled. `*_warm` rotates 64 keys; `*_miss` rotates 2,048 genuinely
  different caret constraints, exceeding its 1,000-entry LRU. The latter is a
  steady-state cache-miss workload, **not cold start**. Build tags do not provide
  distinct keys because npm strips them before caching.
- **Match:** both requirement and candidate are parsed before timing. npm tests
  the prepared `SemVer`, avoiding accidental candidate reparsing. Broader grammar
  and internal simplification remain differences between the implementations.

## Preventing folded-away work

Goose uses test-only C helpers in a **separate translation unit without LTO**.
The index is opaque; all five version fields or all comparator bytes, plus the
complete error bytes, escape to native consumers. Comparison/matching scalar
results escape too. This adds two external calls for comparison/matching and
three for parsing. Rust uses inline `std::hint::black_box`; Node parse objects
escape through an observable global sink. Those scaffolds are different.

The Goose barrier-only control loops are reported separately and are **never
subtracted**. They do not model every table lookup or output-size walk; small
nanosecond gaps should not be read as intrinsic function costs. Native result
materialization/drop stays timed. Node warms the **same operation-specific loop**
that is subsequently timed with at least 200,000 operations per fixture, rounded
to complete corpus passes. This avoids a cold timed callsite or polymorphic
per-operation dispatcher penalizing V8.

## Measurement and provenance

Each engine gets a warm process, then nine randomized process-order rounds.
Timed children inherit the selected single-CPU affinity. A clock is read only
before and after each loop. Setup, TSV parsing, normalization, preparsing,
validation, output formatting and Node warmup are excluded from clock intervals.

Goose uses its default `-O2` and GCC `-O2`; the separate barrier object prevents
cross-TU folding. Rust uses release opt-level 3, thin LTO and one codegen unit.
No CPU-native tuning is requested. Compiler pipelines differ; flags/runtime
versions and hashes identify the measured configuration.

The driver clears relevant Rust/Node option overrides, explicitly sets empty
Rust flags, and controls the release optimization profile. It hashes the supplied
Goose compiler executable and checks that it stays unchanged. The requested
`GOOSE_REVISION` pin is recorded separately: the driver does not infer the compiler's
source revision from an arbitrary `--goose` path. It snapshots source
hashes and Git state **before** building, resolves reference commits, then aborts
if Git HEAD or a measured source changes before completion. Reports retain the
corpus hash, dependency/source/binary hashes, versions, affinity, every raw round,
all fixture medians/min/max, barrier controls and separate compatibility probes.
No private filesystem paths are written to the published raw report.

[Primary results](../competitor-results.md) retain every fixture and regression.
A CPU3 series with suspected shared-core contention is also retained separately;
the primary run moved to CPU1 after another fuzzing process was observed on CPU3.
Neither experiment claims exclusive host isolation. Scheduler load, frequency,
compiler decisions, allocators, V8/GC and caches can affect results. There are no
CI timing thresholds or claims of universal rankings, cold latency or allocation
counts. CI validates adapter execution and checksums with a small timed count.

## Non-ranked compatibility probes

`capabilities.py` records outcomes that deliberately differ; these rows never
contribute to performance rankings. In the pinned versions:

| Input/operation | Goose | Rust | npm |
| --- | --- | --- | --- |
| Parse `v1.2.3` | reject | reject | accept |
| Parse surrounding spaces | reject | reject | accept |
| Compare numeric prereleases `9007199254740992` and `9007199254740993` | -1 | -1 | 0 |
| Parse core `18446744073709551616` | accept | reject | reject |
| Parse a 257-byte version | accept | accept | reject |

The npm numeric comparison result can be reproduced from its pinned
[identifier implementation](https://github.com/npm/node-semver/blob/v7.8.6/internal/identifiers.js),
which converts numeric identifiers to JavaScript numbers. Rust's core range is
[`u64`](https://docs.rs/semver/1.0.28/semver/struct.Version.html#syntax); Goose uses
owned decimal text within its 4,096-byte version limit. These differences explain
why benchmarking unsupported inputs as though every parser did equal work would
be misleading. They are not used to relax Goose's validation or capability.
