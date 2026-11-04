# Security policy

This library is experimental. Security fixes target the latest `main`; no older
release line has a support commitment yet.

Report suspected vulnerabilities through [GitHub private vulnerability
reporting](https://github.com/carabistouflette/goose-semver/security/advisories/new).
Include a minimal input, affected commit, Goose revision, platform and observed
behavior. Keep exploit details private until a fix is available. Do not include
credentials or sensitive production data.

## Contract and limits

`parse` and `parse_requirement` accept untrusted byte slices. They enforce strict
ASCII grammar and limits of 4096 bytes per version, 16384 bytes per requirement
and 32 comparators. Parsing performs bounded linear work without recursion or
integer conversion. Results own their bytes. No network, file, process,
cryptographic or user-supplied callback operations occur during parsing/matching.
Immutable scanner tables and Goose's bounded standard-library scanner accelerate
long identifiers; no private native kernel or platform-specific code is vendored.

Check returned errors. Failed/default requirements and failed/default candidate
versions match nothing. `compare` and `format` require successfully parsed,
unmodified versions. Public fields are inspectable; manually fabricated or
mutated values and namespace-visible implementation helpers are outside the
supported contract. Limits bound work and logical storage; they do not promise
an exact allocator budget or recovery from Goose runtime allocation failure.

Tests combine public behavior, independent Python integer/regex oracles,
targeted exhaustive byte-edit neighborhoods, seeded mutations, roundtrip and
failure-state invariants, SIMD block/tail boundary cases and GCC/Clang ASan/UBSan
runs. These improve confidence but do not prove the absence of bugs. The pinned
Goose compiler and standard-library runtime are part of the trust boundary.
