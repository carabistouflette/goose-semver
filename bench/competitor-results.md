# Rust and npm comparison

> Historical measurement: this report predates v0.1.1. Its timings and validation
> apply only to the recorded sources, not current main or v0.1.1.
> See the [benchmark index](README.md) for current results and reproduction.

Measured source: `efcfc45197a47b52357531550141e34489aa186d`; previous Goose core:
`b7dc3aaee7395483e5f56757f3886551634df27d`. Both Goose binaries used the same harness for that run.
Exact dependencies: Rust `semver` **1.0.28**, npm `semver` **7.8.6** (locked).

On this machine and corpus, Goose has lower process medians in **18/18**
npm fixtures and **6/18** Rust fixtures. Rust remains faster on the other
**12**. This is a fixture count, not an overall ranking, significance test
or claim that all applications become faster. The invalid-input result is close:
Goose samples span 25.68–30.02 ns and Rust 27.56–31.85 ns, so those ranges overlap.

[Raw rounds, ranges, hashes and compatibility probes](results/2026-11-04-competitors.json)
· [Reproduction and method](competitors/README.md)

## All fixtures

Nanoseconds per operation; lower is better. Values are process medians from nine
randomized rounds, with 200,000 operations per fixture and 64 input variants
(2,048 for the range-cache-miss fixture). All fixtures and regressions are kept.

| Fixture | Goose before | Goose after | Rust semver | npm semver |
| --- | ---: | ---: | ---: | ---: |
| parse_release | 84.1 | 33.6 | 26.1 | 258.0 |
| parse_pre_short | 96.6 | 52.6 | 71.6 | 983.7 |
| parse_pre_long | 140.0 | 94.5 | 347.6 | 1725.5 |
| parse_build_long | 119.0 | 75.3 | 466.0 | 1029.8 |
| parse_invalid | 44.1 | 27.2 | 29.4 | 6336.6 |
| compare_release | 12.4 | 12.1 | 5.2 | 19.3 |
| compare_pre | 30.2 | 13.3 | 27.4 | 61.3 |
| compare_equal_build | 38.5 | 15.2 | 5.6 | 41.6 |
| compare_long_pre_early | 83.4 | 12.5 | 87.6 | 240.0 |
| compare_long_pre_late | 334.0 | 126.7 | 94.5 | 315.0 |
| requirement_exact_warm | 164.2 | 91.6 | 50.6 | 731.5 |
| requirement_caret_warm | 159.3 | 94.1 | 50.1 | 660.8 |
| requirement_and_warm | 256.0 | 127.1 | 71.2 | 999.6 |
| match_release | 21.6 | 20.0 | 7.6 | 197.0 |
| match_prerelease | 60.9 | 40.5 | 36.9 | 244.4 |
| match_reject | 13.1 | 12.4 | 5.8 | 226.4 |
| match_many | 208.9 | 216.8 | 83.9 | 1526.4 |
| requirement_caret_miss | 151.3 | 88.8 | 51.1 | 13526.9 |

Long suffix parsing and differing nonnumeric prerelease heads are strengths of
this implementation. Rust retains advantages on several numeric-core, requirement
and pre-parsed operations. Small differences may overlap normal shared-host
variation; all per-engine sample ranges are retained in the raw record.

## What changed

- Construct empty failure results only when a parse actually fails; successful parses avoid an extra result copy.
- Inline validated core parsing and the main parser where measurements justified it.
- Copy a one-byte decimal core directly while retaining owned strings and arbitrary-magnitude fallback.
- Skip equal 16-byte lexical blocks using the standard bounded equality implementation.
- Decide differing nonnumeric identifier heads directly; digit-leading identifiers still receive full numeric classification.
- Keep every validation rule, resource limit, error offset and ownership guarantee.

## Environment and overhead

CPU: Intel(R) Core(TM) Ultra 7 258V; affinity CPU 1.
Platform: Linux-7.2.11-arch1-1-x86_64-with-glibc2.44.
Goose compiler: `eadca409f68210893f366e60d0c2f0dc29a339be`; gcc (GCC) 16.2.1 20260810.
Rust: rustc 1.101.0-nightly (822182db4 2026-10-13); Node: v26.13.0.
Goose flags: gcc -O2, separate barrier TU, no LTO. Rust: Cargo release opt3, thin LTO, codegen-units1.

No CPU-native tuning is requested. GNU C and LLVM/Rust optimize differently.
Rust has numeric cores and can inline short suffix storage; Goose owns decimal
core text and all suffix bytes. Node may retain immutable input strings and its
allocation/GC behavior is included. These are public-operation comparisons, not
claims that their representations, grammars or memory management are identical.

Goose crosses test-only opaque C barriers to prevent folding: input index, full
owned output (all five version fields or comparator bytes), and full Error bytes.
Compare/match results cross a scalar barrier. Rust uses inline `black_box`; Node
stores parse objects in an observable global sink. These scaffolds differ.
Separate Goose barrier-only snapshots: scalar 1.80 ns, version/error
18.50 ns, requirement/error 15.61 ns per iteration.
They are included in operation timings and are **not subtracted**. Controls do not
capture every lookup or variable-size output walk. Tiny nanosecond differences
should not be treated as isolated intrinsic library costs.

## Security and correctness

- 122,191 targeted cases pass through TinyCC, optimized/debug native, and GCC/Clang ASan/UBSan modes.
- Independent property and hostile-input oracles pass; 47,120 read-only protected-page checks pass.
- A 500,000-execution Clang/libFuzzer+ASan/UBSan campaign passed for this core source.
- Added strict-prefix, every-nonnumeric-leading-byte, and one-/multi-byte core ownership regressions.
- Independent implementation and benchmark reviewers found no remaining blocking defect.

These checks do not prove exhaustive correctness. Benchmark inputs stay in a
verified shared subset; incompatible behavior is recorded separately, never
counted as a performance win. See the method for numeric/length limits, npm cache
behavior, Node JIT warmup and reproducible commands.

The separate [CPU3 shared-core series](results/2026-11-04-competitors-cpu3-contended.json)
is retained as a secondary experiment. Another fuzzing process was observed on
CPU3 after that run, alongside elevated timings. The primary run moved to CPU1;
its results are still shared-host measurements, not exclusive isolation.
