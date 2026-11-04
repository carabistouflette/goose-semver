# Contract

Experimental pure-Goose SemVer 2.0.0 library. No I/O, private native code, external runtime dependencies,
regular expressions, recursion, integer conversion, or implicit coercion.

## Versions

`parse(text) -> (Version, Error)` strictly accepts `major.minor.patch`, optional
`-prerelease`, optional `+build`. Maximum 4096 bytes, inclusive. Core numbers and
numeric prerelease identifiers have no leading zeroes. Identifiers are nonempty
ASCII alphanumerics/hyphens separated by dots. Build numeric zeroes are allowed.
No whitespace, `v` prefix, omitted components, NUL or non-ASCII bytes.

`Version { major, minor, patch, prerelease, build }` owns all five fields as
`u8[]`. Decimal text permits arbitrary magnitude within the input limit.
Fields are inspectable; comparison/matching/formatting require successfully
parsed values whose fields have not been modified. Failure returns an empty,
invalid Version; discard it. `Error { kind, offset }` is allocation-free;
`ErrorKind.None` means success. Offsets are zero-based bytes. Exceeding the enclosing parse input limit uses
0; an oversized version target in a requirement uses the target start in the
whole requirement. EOF errors may use text length. Error kinds: None, TooLong, Syntax,
LeadingZero, TooManyComparators.

`compare(a, b) -> i64` returns -1, 0, 1 for SemVer precedence, ignoring build
metadata. Numeric components compare by length then ASCII; numeric prerelease
identifiers sort before nonnumeric, releases after prereleases. No copying or
allocation. `format(version) -> u8[>..]` returns the exact accepted spelling.

## Requirements

`parse_requirement(text) -> (Requirement, Error)` owns comparator targets.
Maximum 16384 bytes and 32 comparators inclusive. Grammar:

    requirement = ws ("*" | comparator (ws "," ws comparator)*) ws
    comparator  = ["=" | ">" | ">=" | "<" | "<=" | "^" | "~"] ws version
    ws          = zero or more ASCII space or tab

Versions must be full strict versions, with the same 4096-byte limit. A bare
version means exact precedence equality. Build metadata is accepted and ignored.
No partial versions, embedded wildcards, OR, hyphen ranges, implicit caret,
newlines, empty requirements, or trailing commas. `*` stands alone.
Errors from target parsing are relative to the whole requirement.

`matches(requirement, version) -> bool` applies every comparator (AND). It does
not parse or allocate. Contradictory requirements are valid and match nothing.
Prereleases only match when at least one comparator explicitly names a prerelease
with the same major/minor/patch; all comparators must still pass. `*` therefore
matches releases only. This prerelease policy is a library requirement convention,
not part of SemVer 2.0.0.

Caret matches versions >= its target while preserving the leftmost nonzero core
component and all components before it: ^1.2.3 <2.0.0; ^0.2.3 <0.3.0;
^0.0.3 <0.0.4. ^0.0.0 preserves the exact core. Tilde preserves major and minor
and requires >= target. Implementations compare prefixes, never increment.

`Requirement { valid: bool = false, comparators: Comparator[] }` tracks successful
parsing. A valid empty comparator array means `*`. `Comparator { op: Op, version: Version }`. These fields are inspectable but
must not be mutated. On error the returned requirement is invalid: `matches` returns false for it
and for default-constructed requirements. Failed/default candidate versions
(empty major) also match nothing. Callers must still check Error to
distinguish bad requirements from legitimate nonmatches.

Parsing is O(input bytes), owned storage O(input bytes + comparator count).
Comparison is O(bytes examined); matching O(total target bytes + comparator count
* candidate bytes), bounded by the limits above for parsed values. No exact
allocator budget or recovery from Goose runtime allocation failure is promised.

Sources: https://semver.org/spec/v2.0.0.html (versions and precedence);
https://docs.rs/semver/1.0.28/semver/struct.VersionReq.html (prerelease eligibility
convention only). This requirement grammar is deliberately smaller and differs
from Cargo/npm; no compatibility claim is made.

Only the types/constants and functions listed above are supported. Namespace-visible
helpers (including cursor/identifier functions) are implementation details and
assume internal invariants; do not call them directly.
