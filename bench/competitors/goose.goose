// SPDX-License-Identifier: Apache-2.0
// Test-only C barriers force inputs/results observable; no product native code.
import semver from "../..";
import std;
import os;
extern fn opaque(value: i64) -> i64 = "semver_bench_opaque";
extern fn escape_version(a: const u8[:], b: const u8[:], c: const u8[:], d: const u8[:], e: const u8[:]) = "semver_bench_version";
extern fn escape_bytes(a: const u8[:]) = "semver_bench_bytes";
struct Row { left: const u8[:], right: const u8[:], expected: i64 }
fn parsed(source: const u8[:]) -> semver::Version {
    let v, e = semver::parse(source); assert(e.kind == semver::ErrorKind.None); copy(v)
}
fn required(source: const u8[:]) -> semver::Requirement {
    let r, e = semver::parse_requirement(source); assert(e.kind == semver::ErrorKind.None); copy(r)
}
fn timed<F>(count: i64, iterations: i64) -> i64, i64 {
    var index = 0;
    var checksum: i64 = 0;
    let start = clock_ns();
    for i in iterations {
        checksum += F(opaque(index));
        index += 1; if index == count { index = 0; }
    }
    return clock_ns() - start, checksum;
}
fn report(name: const u8[:], rows: Row[:], iterations: i64, elapsed: i64, checksum: i64) {
    var expected: i64 = 0;
    let cycles = iterations / rows.len;
    let remainder = iterations % rows.len;
    for row, j in rows { let extra = if j < remainder { 1 } else { 0 }; expected += row.expected * (cycles + extra); }
    assert(checksum == expected);
    print(name, "\t", elapsed, "\t", iterations, "\t", checksum);
}
fn measure(op: const u8[:], name: const u8[:], rows: Row[:], iterations: i64) {
    var versions:     semver::Version[>..]        = [];
    var version_refs: (semver::Version&)[>..]     = [];
    var other:        semver::Version[>..]        = [];
    var other_refs:   (semver::Version&)[>..]     = [];
    var requirements: semver::Requirement[>..]    = [];
    var req_refs:     (semver::Requirement&)[>..] = [];
    if op == "compare" || op == "match" {
        for row in rows {
            let b .= other.push(parsed(row.right)); other_refs.push(b);
            if op == "compare" { let a .= versions.push(parsed(row.left)); version_refs.push(a); }
            else { let r .= requirements.push(required(row.left)); req_refs.push(r); }
        }
    }
    if op == "parse" {
        for row in rows { let v, e = semver::parse(row.left); assert((if e.kind == semver::ErrorKind.None { 1 } else { 0 }) == row.expected); }
        let elapsed, checksum = timed(rows.len, iterations) { at =>
            let v, e = semver::parse(rows[at].left);
            escape_version(v.major, v.minor, v.patch, v.prerelease, v.build);
            escape_bytes(bytes_of([e]));
            if e.kind == semver::ErrorKind.None { 1 } else { 0 }
        };
        report(name, rows, iterations, elapsed, checksum);
    } else if op == "requirement" {
        for row in rows { let r, e = semver::parse_requirement(row.left); assert((if e.kind == semver::ErrorKind.None { 1 } else { 0 }) == row.expected); }
        let elapsed, checksum = timed(rows.len, iterations) { at =>
            let r, e = semver::parse_requirement(rows[at].left);
            escape_bytes(bytes_of(r.comparators));
            escape_bytes(bytes_of([e]));
            if e.kind == semver::ErrorKind.None { 1 } else { 0 }
        };
        report(name, rows, iterations, elapsed, checksum);
    } else if op == "compare" {
        for row, at in rows { assert(semver::compare(version_refs[at], other_refs[at]) == row.expected); }
        let elapsed, checksum = timed(rows.len, iterations) { at => opaque(semver::compare(version_refs[at], other_refs[at])) };
        report(name, rows, iterations, elapsed, checksum);
    } else {
        assert(op == "match");
        for row, at in rows { assert((if semver::matches(req_refs[at], other_refs[at]) { 1 } else { 0 }) == row.expected); }
        let elapsed, checksum = timed(rows.len, iterations) { at => opaque(if semver::matches(req_refs[at], other_refs[at]) { 1 } else { 0 }) };
        report(name, rows, iterations, elapsed, checksum);
    }
}
export fn bench_run(path: const u8[:], iterations: i64) {
    assert(iterations > 0 && iterations <= 10000000);
    var source: u8[>..]     = []; assert(read_file(path, source));
    var rows:   Row[>..]    = [];
    var op:     const u8[:] = source[..0]; var name: const u8[:] = source[..0];
    for line in split(source, "\n") {
        if line.len == 0 { continue; }
        let fields = split(line, "\t"); assert(fields.len == 5);
        if rows.len > 0 && fields[1] != name { measure(op, name, rows, iterations); rows.clear(); }
        op = fields[0]; name = fields[1];
        let expected, ok = parse_int(fields[4]); assert(ok);
        rows.push(Row { fields[2], fields[3], expected });
    }
    if rows.len > 0 { measure(op, name, rows, iterations); }
}
export fn bench_controls(iterations: i64) {
    let texts = ["1", "2", "3", "4"];
    let scalar_ns, scalar_sum = timed(4, iterations) { at => opaque(1) };
    let version_ns, version_sum = timed(4, iterations) { at =>
        let t = texts[at]; escape_version(t, t, t, t, t); escape_bytes(bytes_of([semver::Error { .. }])); 1
    };
    let bytes_ns, bytes_sum = timed(4, iterations) { at => escape_bytes(texts[at]); escape_bytes(bytes_of([semver::Error { .. }])); 1 };
    assert(scalar_sum == iterations && version_sum == iterations && bytes_sum == iterations);
    print("scalar\t", scalar_ns, "\t", iterations, "\t", scalar_sum);
    print("version\t", version_ns, "\t", iterations, "\t", version_sum);
    print("requirement\t", bytes_ns, "\t", iterations, "\t", bytes_sum);
}
fn main() {}
