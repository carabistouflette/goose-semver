// SPDX-License-Identifier: Apache-2.0
// Test-only exported entry points for the libFuzzer host. Each invocation owns
// its temporary values; nothing from the input or parsed output is retained.
import semver from "..";
import std;

fn checked_version(source: const u8[:]) -> semver::Version, semver::Error {
    let version, error = semver::parse(source);
    assert(error.offset >= 0 && error.offset <= source.len);
    if error.kind != semver::ErrorKind.None {
        assert(version.major.len == 0 && version.minor.len == 0 && version.patch.len == 0);
        assert(version.prerelease.len == 0 && version.build.len == 0);
    } else {
        assert(semver::format(version) == source);
        assert(semver::compare(version, version) == 0);
    }
    return copy(version), error;
}
fn checked_requirement(source: const u8[:]) -> semver::Requirement, semver::Error {
    let requirement, error = semver::parse_requirement(source);
    assert(error.offset >= 0 && error.offset <= source.len);
    let candidate, candidate_error = semver::parse("1.2.3");
    assert(candidate_error.kind == semver::ErrorKind.None);
    if error.kind != semver::ErrorKind.None {
        assert(!requirement.valid && requirement.comparators.len == 0);
        assert(!semver::matches(requirement, candidate));
    } else {
        assert(requirement.valid && requirement.comparators.len <= semver::MAX_COMPARATORS);
        for comparator in requirement.comparators {
            let spelling = semver::format(comparator.version);
            let target, target_error = checked_version(spelling);
            assert(target_error.kind == semver::ErrorKind.None);
            assert(semver::compare(target, comparator.version) == 0);
        }
        let empty = semver::Version { .. };
        assert(!semver::matches(requirement, empty));
    }
    return copy(requirement), error;
}
fn version_invariants(source: const u8[:]) {
    let version, error = checked_version(source);
    if error.kind != semver::ErrorKind.None { return; }
    let roundtrip = semver::format(version);
    let again, again_error = checked_version(roundtrip);
    assert(again_error.kind == semver::ErrorKind.None);
    assert(semver::compare(version, again) == 0);
    let exact, exact_error = checked_requirement(str("=", roundtrip));
    assert(exact_error.kind == semver::ErrorKind.None && semver::matches(exact, version));
    let any, any_error = semver::parse_requirement("*");
    assert(any_error.kind == semver::ErrorKind.None);
    assert(semver::matches(any, version) == (version.prerelease.len == 0));
    let empty = semver::Requirement { .. };
    assert(!semver::matches(empty, version));
    // Add known build metadata without modifying a parsed value's fields.
    var alternate = str(version.major, ".", version.minor, ".", version.patch);
    if version.prerelease.len > 0 { alternate.push('-'); alternate.append(version.prerelease); }
    alternate.append("+fuzz.001");
    if alternate.len <= semver::MAX_VERSION_BYTES {
        let with_build, with_error = checked_version(alternate);
        assert(with_error.kind == semver::ErrorKind.None);
        assert(semver::compare(version, with_build) == 0);
        assert(semver::matches(exact, with_build));
    }
}
fn pair_invariants(left: const u8[:], right: const u8[:]) {
    let a, ae = checked_version(left);
    let b, be = checked_version(right);
    if ae.kind == semver::ErrorKind.None && be.kind == semver::ErrorKind.None {
        let ab = semver::compare(a, b);
        let ba = semver::compare(b, a);
        assert(ab >= -1 && ab <= 1 && ab == -ba);
        let exact, ee = checked_requirement(str("=", left));
        assert(ee.kind == semver::ErrorKind.None);
        // Exact requirements name their own prerelease core explicitly.
        assert(semver::matches(exact, b) == (ab == 0));
    }
    let requirement, re = checked_requirement(left);
    if re.kind == semver::ErrorKind.None && be.kind == semver::ErrorKind.None {
        let matched = semver::matches(requirement, b);
        if requirement.comparators.len == 0 {
            assert(matched == (b.prerelease.len == 0));
        }
        // Every matched prerelease needs explicit same-core admission.
        if matched {
            var admitted = b.prerelease.len == 0;
            for comparator in requirement.comparators {
                if comparator.version.prerelease.len > 0 &&
                   comparator.version.major == b.major && comparator.version.minor == b.minor && comparator.version.patch == b.patch {
                    admitted = true;
                }
            }
            assert(admitted);
        }
    }
}
fn triple_invariants(left: const u8[:], middle: const u8[:], right: const u8[:]) {
    let a, ae = checked_version(left);
    let b, be = checked_version(middle);
    let c, ce = checked_version(right);
    if ae.kind != semver::ErrorKind.None || be.kind != semver::ErrorKind.None || ce.kind != semver::ErrorKind.None { return; }
    let ab = semver::compare(a, b);
    let bc = semver::compare(b, c);
    let ac = semver::compare(a, c);
    if ab <= 0 && bc <= 0 { assert(ac <= 0); }
    if ab >= 0 && bc >= 0 { assert(ac >= 0); }
}
export fn fuzz_check(source: const u8[:]) -> i64 {
    version_invariants(source);
    let requirement, error = checked_requirement(source);
    let first = find(source, "\0");
    if first < 0 { return 0; }
    let left = source[..first];
    let tail = source[first + 1..];
    let second = find(tail, "\0");
    if second < 0 {
        pair_invariants(left, tail);
    } else {
        let middle = tail[..second];
        let right = tail[second + 1..];
        pair_invariants(left, middle);
        pair_invariants(middle, right);
        triple_invariants(left, middle, right);
    }
    return 0;
}
// The driver must prove assertion failures save the exact triggering bytes.
export fn fuzz_assertion_probe(value: i64) { assert(value != 0); }
fn main() {}
