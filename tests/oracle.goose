// SPDX-License-Identifier: Apache-2.0
// Test-only batched hex protocol keeps arbitrary bytes out of line delimiters.
import semver from "..";
import std;
import os;

fn nibble(c: u8) -> u8 {
    if c >= '0' && c <= '9' { return c - '0'; }
    assert(c >= 'a' && c <= 'f');
    c - 'a' + 10
}
fn decode(text: const u8[:]) -> u8[>..] {
    assert(text.len % 2 == 0);
    var out: u8[>..] = [];
    var at = 0;
    while at < text.len {
        out.push(nibble(text[at]) * 16 + nibble(text[at + 1]));
        at += 2;
    }
    out
}
fn checked_parse(text: const u8[:]) -> semver::Version, semver::Error {
    let version, error = semver::parse(text);
    assert(error.offset >= 0 && error.offset <= text.len);
    if error.kind == semver::ErrorKind.None { assert(semver::format(version) == text); }
    else {
        assert(version.major.len == 0 && version.minor.len == 0 && version.patch.len == 0);
        assert(version.prerelease.len == 0 && version.build.len == 0);
    }
    return copy(version), error;
}
fn main() {
    while true {
        var line: u8[>..] = [];
        if !read_line(line) { break; }
        assert(line.len >= 2 && line[1] == '\t');
        if line[0] == 'P' {
            let input = decode(line[2..]);
            let version, error = checked_parse(input);
            print(if error.kind == semver::ErrorKind.None { 1 } else { 0 });
        } else {
            let separator = find(line[2..], "\t") + 2;
            assert(separator >= 2);
            let left = decode(line[2..separator]);
            let right = decode(line[separator + 1..]);
            let b, be = checked_parse(right);
            if line[0] == 'C' {
                let a, ae = checked_parse(left);
                if ae.kind != semver::ErrorKind.None || be.kind != semver::ErrorKind.None { print("E"); }
                else { print(semver::compare(a, b)); }
            } else {
                assert(line[0] == 'M');
                let r, re = semver::parse_requirement(left);
                assert(re.offset >= 0 && re.offset <= left.len);
                if re.kind == semver::ErrorKind.None { assert(r.valid); }
                else { assert(!r.valid && r.comparators.len == 0); assert(!semver::matches(r, b)); }
                if re.kind != semver::ErrorKind.None || be.kind != semver::ErrorKind.None { print("E"); }
                else { print(if semver::matches(r, b) { 1 } else { 0 }); }
            }
        }
    }
}
