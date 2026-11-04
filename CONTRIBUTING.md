# Contributing

Keep the interface small, pure, explicit and dependency-free. Applications own
I/O. Prefer linear scans and shared validation over special fast paths. Preserve
strict grammar, owned results, bounded work and byte-offset errors. Discuss
requirement grammar changes before broadening it; docs/api.md is the contract.

Use focused branches and Conventional Commits with imperative subjects and one
coherent change: feat:, fix:, test:, perf:, docs:, chore:. Commit verified
milestones regularly. Before 1.0 the interface is experimental; release only
after independent review.

For behavior changes add public-interface regressions. Run make format,
make check test property security sanitize, and git diff --check. Run make
differential when changing version/requirement semantics; the latter
needs the lockfile-pinned Rust test dependency. Run make bench
for performance changes; preserve validation and ownership, report every fixture
and retain raw samples, compiler revision, flags and hardware. CI checks benchmark
execution without timing thresholds. Profile before adding optimizations.
Request independent correctness/security and performance/quality reviews, fix
actionable findings, and keep CI passing. Compiler changes require a reviewed
full upstream commit in GOOSE_REVISION and full validation. Never commit compiler
output, credentials or private workspace notes. Report vulnerabilities privately
through GitHub security advisories when available.
