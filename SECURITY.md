# Security policy

This library is experimental. Fixes target the latest main; older release lines
have no support commitment yet.

Report suspected vulnerabilities through [GitHub private reporting](https://github.com/carabistouflette/goose-semver/security/advisories/new).
Include a minimal input, affected commit, Goose revision, platform and observed
behavior. Do not include credentials or production data. Public CI logs and
failure artifacts can expose inputs; use local reproduction for sensitive reports.

## Input contract

Parsers accept untrusted byte slices and enforce strict ASCII grammar: at most
4,096 bytes per version, 16,384 bytes per requirement and 32 comparators.
They use bounded linear scans without recursion or integer conversion. Results
own their bytes. Parsing and matching perform no I/O or user callbacks.

Check returned errors. Failed/default requirements and candidate versions match
nothing. Comparison and formatting require successfully parsed, unmodified
versions. Fabricated or mutated objects and implementation helpers are outside
the [supported API](docs/api.md).

Limits bound work and logical storage, not an exact allocator budget. Recovery
from Goose runtime allocation failure is not promised. The pinned Goose compiler
and standard library are part of the trust boundary. The library vendors no
native scanner; it uses the standard library's bounded scanner.

[Tests](docs/testing.md) include independent models, byte-boundary inputs,
protected slices, sanitizers and fuzzing. They improve confidence but do not
prove the absence of bugs.
