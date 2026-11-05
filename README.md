# goose-semver

Parse, compare and match [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)
versions in [Goose](https://github.com/aardappel/goose).
The library uses only the Goose standard library and returns owned values.
Licensed under [Apache-2.0](LICENSE).

## Quickstart

With the pinned Goose compiler already installed:

```sh
git clone https://github.com/carabistouflette/goose-semver.git
cd goose-semver
git checkout 2311ae69a7edacb545f284b02e345be07dd2fb05
goose run examples/versions.goose
```

This prints `1.4.2+build.7 matches: true`. If you need a compiler, run `make setup`
in the checkout, then use `.toolchain/goose/build/goose` in place of `goose`.
Setup needs Git, CMake 3.27+, Make and C/C++20 compilers; it builds the revision
in [GOOSE_REVISION](GOOSE_REVISION).

The example imports a neighboring library checkout. In your application's root
source you can instead pin a remote import:

```goose
import semver from "carabistouflette/goose-semver@2311ae69a7edacb545f284b02e345be07dd2fb05";
```

[examples/versions.goose](examples/versions.goose) shows error handling and matching:

```goose
let version, error = semver::parse("1.4.2+build.7");
// Check error.kind == semver::ErrorKind.None before using version.
let requirement, req_error = semver::parse_requirement("^1.2.0, <1.5.0");
// Check req_error.kind too.
print(semver::matches(requirement, version)); // true
```

## API and limits

- `parse(text)` returns `(Version, Error)`.
- `compare(a, b)` returns -1, 0 or 1 for precedence; build metadata is ignored.
- `format(version)` returns the accepted spelling.
- `parse_requirement(text)` returns `(Requirement, Error)`.
- `matches(requirement, version)` applies every comparator (AND).

Always check returned errors. Parsed fields are inspectable, but must not be
modified before comparison, formatting or matching. Failed/default requirements
and failed/default candidate versions match nothing. Numeric components use
owned decimal text, so they are not limited to machine integers.

Versions require all three core components, without whitespace or a `v` prefix.
Requirements support full versions with `= > >= < <= ^ ~`, comma AND, and a
standalone `*`. A bare full version is exact. Prereleases need an explicit
prerelease comparator with the same core; `*` accepts releases only. Requirement
whitespace is ASCII space or tab. Partial versions, OR and embedded wildcards
are unsupported. This is not Cargo/npm grammar compatibility.

Limits are **4,096 bytes per version**, **16,384 bytes per requirement** and
**32 comparators**. Error offsets count bytes. See the [API contract](docs/api.md)
for ownership, exact errors, complexity and requirement semantics.
The [tag example](docs/tag-policy.md) shows how an application can explicitly
handle a single lowercase `v` on enumerated Git tags.

## Support and releases

The latest release is experimental [v0.1.1](https://github.com/carabistouflette/goose-semver/releases/tag/v0.1.1),
at the full commit used above. It fixes caller-overload bugs in v0.1.0 without
changing the API or limits. Main adds documentation and benchmark updates; its
library source and compiler pin are unchanged from v0.1.1. Existing tags stay fixed.
See the [changelog](CHANGELOG.md).

Validated on Linux x86-64 with the pinned Goose compiler, GCC and Clang. Other
platforms are untested. Allocation failure is governed by the Goose runtime;
there is no recovery guarantee.

## Development and measurements

Run `make check test GOOSE=/absolute/path/to/goose` with the pinned compiler.
Python 3.11+ is required. See [testing](docs/testing.md) for the model, sanitizer,
fuzz and differential commands and their requirements.

[Benchmark results and method](bench/README.md) report complete workloads,
including slower results and shared-machine limitations. They do not establish
a universal ranking or application-level speedup.

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) ·
[Third-party notices](THIRD_PARTY_NOTICES.md)
