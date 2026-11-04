// SPDX-License-Identifier: Apache-2.0
import semver from "..";
import std;
import os;

fn compare_case(name: const u8[:], a: semver::Version&, b: semver::Version&, iterations: i64, offset: i64, checksum: i64&) {
    let start = clock_ns();
    for i in iterations { checksum += semver::compare(a, b) + offset; }
    print(name, "\t", clock_ns() - start, "\t", iterations);
}
fn match_case(name: const u8[:], r: semver::Requirement&, v: semver::Version&, iterations: i64, checksum: i64&) {
    let start = clock_ns();
    for i in iterations { if semver::matches(r, v) { checksum += 1; } }
    print(name, "\t", clock_ns() - start, "\t", iterations);
}
fn main() {
    let argv = args();
    var iterations: i64 = 10000;
    if argv.len > 1 {
        let count, ok = parse_int(argv[1]);
        assert(ok && count > 0 && count <= 10000000);
        iterations = count;
    }
    var large = str("1.2.3-");
    for i in 4079 { large.push('z'); }
    large.append("+build.1234");
    assert(large.len == 4096);
    var many: u8[>..] = [];
    for i in 32 { if i > 0 { many.push(','); } many.append(">=1.2.3"); }
    let short = "1.2.3-alpha.1+build.42";
    var checksum: i64 = 0;
    for source, name in [short, large] {
        let start = clock_ns();
        for i in iterations {
            let version, error = semver::parse(source);
            assert(error.kind == semver::ErrorKind.None);
            checksum += version.prerelease.len;
        }
        print(if name == 0 { "parse_short" } else { "parse_long" }, "\t", clock_ns() - start, "\t", iterations);
    }
    for source, name in ["^1.2.3, <2.0.0", many, large] {
        let start = clock_ns();
        for i in iterations {
            let requirement, error = semver::parse_requirement(source);
            assert(error.kind == semver::ErrorKind.None);
            checksum += requirement.comparators.len;
        }
        print(if name == 0 { "requirement_short" } else if name == 1 { "requirement_many" } else { "requirement_long" }, "\t", clock_ns() - start, "\t", iterations);
    }
    let a, ae = semver::parse(large);
    let b, be = semver::parse(large);
    let r, re = semver::parse_requirement("^1.2.3-alpha");
    assert(ae.kind == semver::ErrorKind.None && be.kind == semver::ErrorKind.None && re.kind == semver::ErrorKind.None);
    let start_compare = clock_ns();
    for i in iterations { checksum += semver::compare(a, b) + 1; }
    print("compare_long_equal\t", clock_ns() - start_compare, "\t", iterations);
    let start_match = clock_ns();
    for i in iterations { if semver::matches(r, a) { checksum += 1; } }
    print("match_prerelease\t", clock_ns() - start_match, "\t", iterations);
    let small_a, sea = semver::parse("1.2.3-alpha.1");
    let small_equal, seq = semver::parse("1.2.3-alpha.1");
    assert(seq.kind == semver::ErrorKind.None);
    let small_b, seb = semver::parse("1.2.3-alpha.2");
    var late_text = str("1.2.3-");
    for i in 4078 { late_text.push('z'); }
    late_text.append("y+build.1234");
    let late, le = semver::parse(late_text);
    var early_text = str("1.2.3-");
    for i in 4079 { early_text.push('y'); }
    early_text.append("+build.1234");
    let early, ee = semver::parse(early_text);
    var dots_text = str("1.2.3-");
    for i in 1000 { dots_text.append("a."); }
    dots_text.push('a');
    let dots_a, da = semver::parse(dots_text);
    dots_text[dots_text.len - 1] = 'b';
    let dots_b, db = semver::parse(dots_text);
    var core_text: u8[>..] = [];
    for i in 4092 { core_text.push('9'); }
    core_text.append(".0.0");
    let core_a, ca = semver::parse(core_text);
    let core_b, cb = semver::parse(core_text);
    assert(sea.kind == semver::ErrorKind.None && seb.kind == semver::ErrorKind.None);
    assert(le.kind == semver::ErrorKind.None && ee.kind == semver::ErrorKind.None);
    assert(da.kind == semver::ErrorKind.None && db.kind == semver::ErrorKind.None);
    assert(ca.kind == semver::ErrorKind.None && cb.kind == semver::ErrorKind.None);
    compare_case("compare_short_equal", small_a, small_equal, iterations, 1, checksum);
    compare_case("compare_short_different", small_a, small_b, iterations, 2, checksum);
    compare_case("compare_long_late_difference", a, late, iterations, 1, checksum);
    compare_case("compare_long_early_difference", a, early, iterations, 1, checksum);
    compare_case("compare_many_identifiers", dots_a, dots_b, iterations, 2, checksum);
    compare_case("compare_large_core", core_a, core_b, iterations, 1, checksum);
    let many_req, mre = semver::parse_requirement(many);
    let release, rle = semver::parse("1.2.3");
    let below, ble = semver::parse("0.0.0");
    assert(mre.kind == semver::ErrorKind.None && rle.kind == semver::ErrorKind.None && ble.kind == semver::ErrorKind.None);
    match_case("match_many_success", many_req, release, iterations, checksum);
    match_case("match_many_early_failure", many_req, below, iterations, checksum);
    var invalid_text = str(large);
    invalid_text[invalid_text.len - 1] = '?';
    let start_invalid = clock_ns();
    for i in iterations {
        let invalid, error = semver::parse(invalid_text);
        if error.kind != semver::ErrorKind.None { checksum += 1; }
    }
    print("reject_long\t", clock_ns() - start_invalid, "\t", iterations);
    print("checksum\t", checksum);
}
