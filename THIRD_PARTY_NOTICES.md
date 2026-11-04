# Third-party notices

The library and its original tests, examples and tooling are licensed under
Apache-2.0; see [LICENSE](LICENSE). No third-party parser or runtime source is
vendored here. The test-only native fuzz host and driver adapt the Apache-2.0
[goose-toml](https://github.com/carabistouflette/goose-toml) assertion-bridge pattern;
its SPDX attribution is retained. These are test tooling, not runtime dependencies.

The separately fetched [Goose compiler and standard library](https://github.com/aardappel/goose)
use Apache-2.0 for Goose code and are pinned by `GOOSE_REVISION`. Upstream
third-party components, including TinyCC, retain their own licenses and COPYING
files. Preserve the applicable upstream licenses and notices when distributing
compiler code, bundled third-party code or a generated runtime. Compiler build output
and source caches are ignored and are not published in this repository.

Version syntax and precedence follow the [SemVer 2.0.0 specification](https://semver.org/spec/v2.0.0.html).
The independent Python oracle implements that grammar and numeric semantics;
it does not vendor a third-party parser. Requirement prerelease eligibility is
informed by the documented [Rust semver convention](https://docs.rs/semver/1.0.28/semver/struct.VersionReq.html),
with a deliberately smaller, independently implemented requirement grammar.
There is no Cargo/npm compatibility claim.

GitHub Actions references are pinned by commit in `.github/workflows/ci.yml`;
they run in CI and are not runtime dependencies or vendored source. Optional
sanitizer tooling and system C/C++ compilers retain their respective licenses.

Optional competitive benchmark adapters fetch Rust `semver` 1.0.28
(Apache-2.0 OR MIT) and npm `semver` 7.8.6 (ISC) through checked-in lockfiles.
Their source caches and binaries are ignored, not vendored or required by the
library. Preserve their upstream licenses if distributing benchmark dependencies.
