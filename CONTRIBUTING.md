# Contributing

Keep the API small and explicit. Applications own I/O. Preserve strict grammar,
owned results, bounded work and byte-offset errors. Discuss requirement grammar
changes before widening it; [docs/api.md](docs/api.md) is the contract.

Use focused branches and Conventional Commits (`feat:`, `fix:`, `test:`, `perf:`,
`docs:`, `chore:`), with one coherent change and an imperative subject.
Do not commit builds, compiler caches, credentials or private notes.

For behavior changes, add a public API regression and run:

```sh
make format
make check test security
make sanitize SANITIZER_CC=gcc
make sanitize SANITIZER_CC=clang
git diff --check
```

See [testing](docs/testing.md) for setup and optional compiler overrides.
Run `make differential` for version/requirement semantic changes. It needs
Rust/Cargo and the locked test dependency. Compiler changes require a reviewed
full upstream commit in `GOOSE_REVISION` and full validation.

For performance changes, run the [benchmark methods](bench/README.md), keep
slower results visible, and retain raw samples, source/compiler identities,
flags and machine details. CI checks execution, without timing thresholds.
Profile before adding complexity.

Request independent correctness/security and performance/quality reviews for
behavior changes, fix concrete findings and keep CI green. Before 1.0 the API is
experimental; releases require independent review. Report suspected
vulnerabilities [privately](SECURITY.md).
