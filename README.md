# goose-semver

Strict Semantic Versioning 2.0.0 parsing, ordering, and explicit version
requirements for [Goose](https://github.com/aardappel/goose).
Apache-2.0. Experimental v0.1.1 interface; see the [changelog](CHANGELOG.md).

Pure Goose, with no runtime dependencies beyond the standard library. Parsed
values own their strings. Decimal text comparison handles numbers larger than
machine integers without overflow. Parsing is bounded and linear; comparison
and matching do not allocate.

```goose
import semver from "../goose-semver";
import std;

fn main() {
    let version, error = semver::parse("1.4.2+build.7");
    if error.kind != semver::ErrorKind.None { print("bad version at ", error.offset); return; }
    let requirement, req_error = semver::parse_requirement("^1.2.3, <2.0.0");
    if req_error.kind != semver::ErrorKind.None { print("bad requirement at ", req_error.offset); return; }
    print(semver::matches(requirement, version)); // true
}
```

Declare the package in the application's root source. The example above assumes
a neighboring checkout. Remote dependencies can use
`import semver from "carabistouflette/goose-semver@<full-commit>";`; replace
`<full-commit>` with a reviewed published commit. The [v0.1.1 release](https://github.com/carabistouflette/goose-semver/releases/tag/v0.1.1)
fixes consumer-overload interference in v0.1.0; full commits are recommended for reproducibility.

- `parse(text)` returns `(Version, Error)`; check `error.kind == ErrorKind.None`.
- `compare(a, b)` returns -1, 0, or 1, ignoring build metadata.
- `format(version)` returns the exact accepted version spelling.
- `parse_requirement(text)` returns `(Requirement, Error)`.
- `matches(requirement, version)` applies all comparators; failed/default
  requirements and failed/default candidate versions match nothing.

Versions require all three core components, with no `v` prefix or whitespace.
Requirement operators are `=`, `>`, `>=`, `<`, `<=`, `^`, and `~`; a bare full
version is exact. Commas mean AND. `*` stands alone and accepts releases only.
Prereleases require an explicit prerelease comparator with the same core.
Partial versions, OR, and embedded wildcards are excluded. This is an explicit
small grammar, without Cargo/npm compatibility claims.

Git tag normalization is explicit application policy. The
[tag-candidate example and real-tag fixtures](docs/tag-policy.md) show optional
single lowercase `v` handling without weakening the parser or reinterpreting Git refs.

Input limits are **4096 bytes per version**, **16384 bytes per requirement**,
and **32 comparators**. Fields are inspectable but must remain unmodified after
successful parsing. See [the contract](docs/api.md) for ownership, errors,
requirement semantics, complexity, and exact limits.

## Development

```sh
git clone https://github.com/carabistouflette/goose-semver.git
cd goose-semver
make setup
make check test
make security
make differential # optional: requires Rust/Cargo; uses locked Rust semver 1.0.28
make fuzz
make sanitize SANITIZER_CC=gcc
make sanitize SANITIZER_CC=clang
make bench
```

The validated platform is Linux x86-64 with GCC and Clang. The implementation
uses Goose and its standard library only; other platforms have not been validated.

Setup needs Git, CMake 3.27+, C/C++20 compilers, and Make. Tests and benchmarks
need Python 3.11+. The pinned compiler is in `GOOSE_REVISION`; an existing matching
compiler can be selected with `GOOSE=/absolute/path/to/goose`. Linux in-process
execution needs libc development headers. Sanitizers require Linux GCC or Clang
with AddressSanitizer/UndefinedBehaviorSanitizer runtimes. `make fuzz` also needs
Clang/libFuzzer and Linux protected-page APIs; its native host is test-only.

Public behavior tests run through Goose's in-process runner, optimized native
code, and debug native code with bounds-check elimination disabled. They cover
strict byte grammar, precedence examples, arbitrary-magnitude integers,
prerelease eligibility, source ownership, offsets and exact resource limits.
The deterministic Python oracle checks generated versions, comparison,
requirements and matches against optimized and debug builds; hostile cases
include arbitrary bytes and oversized inputs. Targeted exhaustive neighborhoods
exercise grammar-boundary edits and every byte around scalar/SIMD block and tail
boundaries. Generated checks also verify exact formatting and failure-state invariants. Sanitizers instrument the generated
program and runtime in debug and optimized builds and run public tests plus
hostile oracle cases. The independent suites also run through the in-process/TinyCC backend, whose
scanner fallback differs from native builds. `make fuzz` checks protected-page,
read-only input slices and runs a coverage-guided mutation campaign; its assertion
bridge is self-tested to retain exact failure inputs. Seeds, logs and crash
artifacts stay under `.build/fuzz`. Run with `FUZZ_RUNS`, `FUZZ_SECONDS` and
`FUZZ_SEED` to change the bounded campaign. It checks metamorphic invariants,
complementing the independent oracle. A reused writable corpus changes mutation
sequences. The driver fingerprints project inputs and compiler executables
before compilation and checks them again before writing a successful summary;
it rejects results if these change during the campaign. Executable hashes identify
the supplied tools; the requested compiler revision is not independently verified
by this driver. Starting a campaign removes any previous success summary, so a
failed run cannot leave stale success evidence beside fresh logs.
These checks supplement each other; they do not prove exhaustive
correctness.

The [weekly fuzz workflow](.github/workflows/fuzz.yml) runs two date-derived seeds
on Mondays at 03:37 UTC (GitHub scheduling may be delayed), with five-minute or
five-million-execution bounds per campaign. Manual runs can override the base
seed and bounds (up to 600 seconds per campaign). Summaries record the actual seed/count; logs, reusable corpus and
exact failure inputs are retained as GitHub artifacts for 14 days.
Uploads explicitly include hidden files only within the fixed report, corpus and
crash-input allowlist. Successful campaigns require nonempty summary, run and
self-test reports; early setup/compiler failures without evidence skip empty
uploads and keep their original failure in the job logs.

The optional `make differential` campaign also checks Goose and lockfile-pinned
Rust semver 1.0.28 independently against the Python model. Its default 59,176 seeded cases
cover shared explicit/full-version requirement grammar, numeric core boundaries,
long numeric prereleases, build metadata and prerelease eligibility. It excludes
known grammar/range differences rather than treating Rust as the specification.
Cases stream in batches capped at 1,024 cases and 4 MiB, with reproducible hex
diagnostics on disagreement. This target needs Rust/Cargo and may download the
locked test dependency; it adds no library runtime dependency.

[Rust/npm comparison](bench/decimal-audit.md) · [Benchmark method and measured results](bench/README.md) · [Contributing](CONTRIBUTING.md) ·
[Security](SECURITY.md) · [Third-party notices](THIRD_PARTY_NOTICES.md) · [Apache-2.0](LICENSE)
