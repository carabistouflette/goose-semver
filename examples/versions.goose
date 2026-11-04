// SPDX-License-Identifier: Apache-2.0
import semver from "..";
import std;

fn main() {
    let version, error = semver::parse("1.4.2+build.7");
    if error.kind != semver::ErrorKind.None { print("invalid version at byte ", error.offset); return; }
    let requirement, req_error = semver::parse_requirement("^1.2.0, <1.5.0");
    if req_error.kind != semver::ErrorKind.None { print("invalid requirement at byte ", req_error.offset); return; }
    print(semver::format(version), " matches: ", semver::matches(requirement, version));
}
