// SPDX-License-Identifier: Apache-2.0
// A consumer's unrelated root overloads must not replace library snapshots.
import semver from "..";
import std;

fn owned(text: const u8[:]) -> u8[>..] {
    var out: u8[>..] = []; out.append(text); return out;
}
fn copy(value: const semver::Version&) -> semver::Version {
    return semver::Version { major: owned("99"), minor: owned("0"), patch: owned("0"), prerelease: [], build: [] };
}
fn copy(value: const semver::Comparator[:]) -> semver::Comparator[] { return []; }
fn str(value: const u8[:]) -> u8[>..] { return owned("caller string"); }
fn str(a: const u8[:], b: const u8[:], c: const u8[:], d: const u8[:], e: const u8[:]) -> u8[>..] { return owned("caller format"); }
fn min(a: i64, b: i64) -> i64 { return 9999; }
fn main() {
    var source = owned("=1.2.3-alpha.1+build.7, <2.0.0");
    let requirement, error = semver::parse_requirement(source);
    assert(error.kind == semver::ErrorKind.None);
    source.clear(); source.append("overwritten input storage");
    assert(requirement.valid && requirement.comparators.len == 2);
    for comparator, index in requirement.comparators {
        if index == 0 { assert(semver::format(comparator.version) == "1.2.3-alpha.1+build.7"); }
        if index == 1 { assert(semver::format(comparator.version) == "2.0.0"); }
    }
    let candidate, candidate_error = semver::parse("1.2.3-alpha.1+different");
    assert(candidate_error.kind == semver::ErrorKind.None);
    assert(semver::matches(requirement, candidate));
    let other, other_error = semver::parse("1.2.4");
    assert(other_error.kind == semver::ErrorKind.None);
    assert(!semver::matches(requirement, other));
    let wide, wide_error = semver::parse("12.34.56-rc.1+build.7");
    assert(wide_error.kind == semver::ErrorKind.None);
    assert(semver::format(wide) == "12.34.56-rc.1+build.7");
    print("caller overload regression passed");
}
