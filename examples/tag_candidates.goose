// SPDX-License-Identifier: Apache-2.0
import semver from "..";
import std;

// Application policy for tag candidates only. Ordinary refs stay exact in a
// package manager; the library itself always rejects a v prefix.
fn tag_candidate(tag: const u8[:]) -> semver::Version, semver::Error {
    let version, error = semver::parse(if tag.len > 0 && tag[0] == 'v' { tag[1..] } else { tag });
    return version, error;
}
fn main() {
    let requirement, error = semver::parse_requirement("^7.8.5");
    assert(error.kind == semver::ErrorKind.None);
    for tag in ["v7.8.5", "v7.8.6", "1.0.28", "v2.0.0-beta"] {
        let version, parse_error = tag_candidate(tag);
        assert(parse_error.kind == semver::ErrorKind.None);
        print(tag, " matches: ", semver::matches(requirement, version));
    }
    for tag in ["vv7.8.6", "V7.8.6", "release-7.8.6", "main"] {
        let version, parse_error = tag_candidate(tag);
        assert(parse_error.kind != semver::ErrorKind.None);
    }
    let strict, strict_error = semver::parse("v7.8.6");
    assert(strict_error.kind != semver::ErrorKind.None);
}
