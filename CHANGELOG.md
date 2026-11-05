# Changelog

## Unreleased

- Shorten the quickstart and separate testing details from the main guide.
- Clarify benchmark source versions and retain older results as historical.

## 0.1.1 — 2026-11-04

- Fix consumer root `copy` overloads replacing owned requirement snapshots:
  parsed targets could change, or comparator arrays could become empty.
- Avoid analogous root `str` and concrete `min` overload interference in owned
  byte copies, formatting and scanner bounds. Member-array builtins retain owned
  storage without changing the public API, grammar or limits.
- Add consumer-overload regressions through in-process, native/debug and
  GCC/Clang sanitizer builds, including source-mutation ownership checks.
- Make hidden-file inclusion explicit on narrowly allowlisted fuzz uploads.
  Require all three completed-campaign reports; retain available partial failure
  evidence and skip empty uploads after early failures. Previously downloaded
  v0.1.0 workflow artifacts were independently verified complete; this is
  configuration hardening, not a claim of historical evidence loss.

## 0.1.0 — 2026-11-04

First experimental release under Apache-2.0, validated on Linux x86-64 with the
compiler revision in [GOOSE_REVISION](GOOSE_REVISION), GCC and Clang.

- Strict SemVer 2.0.0 parsing, exact formatting and build-independent precedence.
- Owned decimal text supports arbitrary-magnitude numeric components within
  the 4,096-byte version limit, without machine-integer conversion.
- Explicit full-version requirements: equality, inequalities, caret, tilde,
  standalone star and comma conjunctions; same-core prerelease eligibility.
- Bounded 16,384-byte requirements and 32 comparators, byte-offset errors,
  empty failure results and fail-closed matching for failed/default objects.
- Allocation-free comparison and matching; measured optimizations retain
  validation, ownership and fallback paths. [Complete measurements](bench/decimal-audit.md)
  include competing implementations, regressions and limitations.
- Independent model/Rust differential tests, hostile byte neighborhoods,
  protected-page tests, GCC/Clang sanitizers and coverage-guided fuzzing.
- Offline real Git-tag snapshots and an explicit consumer-policy example.
- Weekly two-seed fuzz campaigns with retained evidence and failure inputs.

The interface is experimental. Requirement syntax deliberately differs from
Cargo/npm; registry resolution and tag selection policy belong to consumers.
See [the complete API contract](docs/api.md) and [tag policy](docs/tag-policy.md).
