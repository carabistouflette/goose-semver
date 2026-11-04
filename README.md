# goose-semver

Strict Semantic Versioning 2.0.0 parsing, ordering, and explicit version
requirements for [Goose](https://github.com/aardappel/goose).
Apache-2.0. Experimental interface; no release yet.

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

Declare the package in the application's root source. This checkout is a local
standalone Git repository; no public remote has been configured. Once published,
Goose can import its repository at a full commit hash.

- `parse(text)` returns `(Version, Error)`; check `error.kind == ErrorKind.None`.
- `compare(a, b)` returns -1, 0, or 1, ignoring build metadata.
- `format(version)` returns the exact accepted version spelling.
- `parse_requirement(text)` returns `(Requirement, Error)`.
- `matches(requirement, version)` applies all comparators; failed/default
  requirements match nothing.

Versions require all three core components, with no `v` prefix or whitespace.
Requirement operators are `=`, `>`, `>=`, `<`, `<=`, `^`, and `~`; a bare full
version is exact. Commas mean AND. `*` stands alone and accepts releases only.
Prereleases require an explicit prerelease comparator with the same core.
Partial versions, OR, and embedded wildcards are excluded. This is an explicit
small grammar, without Cargo/npm compatibility claims.

Input limits are **4096 bytes per version**, **16384 bytes per requirement**,
and **32 comparators**. Fields are inspectable but must remain unmodified after
successful parsing. See [the contract](docs/api.md) for ownership, errors,
requirement semantics, complexity, and exact limits.

## Development

```sh
make setup
make format check test
make property security
make sanitize SANITIZER_CC=gcc
make sanitize SANITIZER_CC=clang
make bench
```

Setup needs Git, CMake 3.27+, C/C++20 compilers, and Make. Tests and benchmarks
need Python 3.11+. The pinned compiler is in `GOOSE_REVISION`; an existing matching
compiler can be selected with `GOOSE=/absolute/path/to/goose`. Linux in-process
execution needs libc development headers. Sanitizers require Linux GCC or Clang
with AddressSanitizer/UndefinedBehaviorSanitizer runtimes.

Public behavior tests run through Goose's in-process runner, optimized native
code, and debug native code with bounds-check elimination disabled. They cover
strict byte grammar, precedence examples, arbitrary-magnitude integers,
prerelease eligibility, source ownership, offsets and exact resource limits.
The deterministic Python oracle checks generated versions, comparison,
requirements and matches against optimized and debug builds; hostile cases
include arbitrary bytes and oversized inputs. Sanitizers instrument the generated
program and runtime in debug and optimized builds and run public tests plus
hostile oracle cases. These checks supplement each other; they do not prove
exhaustive correctness.

[Benchmark method](bench/README.md) · [Contributing](CONTRIBUTING.md) ·
[Apache-2.0](LICENSE)
