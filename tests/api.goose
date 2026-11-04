// SPDX-License-Identifier: Apache-2.0
import semver from "..";
import std;

fn version(source: const u8[:]) -> semver::Version {
    let value, error = semver::parse(source);
    if error.kind != semver::ErrorKind.None { print("unexpected version rejection: ", source, " at ", error.offset); }
    assert(error.kind == semver::ErrorKind.None);
    assert(semver::format(value) == source);
    value
}
fn invalid(source: const u8[:]) {
    let value, error = semver::parse(source);
    if error.kind == semver::ErrorKind.None { print("unexpected version acceptance: ", source); }
    assert(error.kind != semver::ErrorKind.None);
    assert(error.offset >= 0 && error.offset <= source.len);
    assert(value.major.len == 0 && value.minor.len == 0 && value.patch.len == 0);
    assert(value.prerelease.len == 0 && value.build.len == 0);
}
fn requirement(source: const u8[:]) -> semver::Requirement {
    let value, error = semver::parse_requirement(source);
    if error.kind != semver::ErrorKind.None { print("unexpected requirement rejection: ", source, " at ", error.offset); }
    assert(error.kind == semver::ErrorKind.None);
    assert(value.valid);
    value
}
fn invalid_requirement(source: const u8[:]) {
    let value, error = semver::parse_requirement(source);
    if error.kind == semver::ErrorKind.None { print("unexpected requirement acceptance: ", source); }
    assert(error.kind != semver::ErrorKind.None);
    assert(error.offset >= 0 && error.offset <= source.len);
    assert(value.comparators.len == 0 && !value.valid);
    let candidate = version("1.2.3");
    assert(!semver::matches(value, candidate));
}
fn matching(req: const u8[:], candidate: const u8[:], expected: bool) {
    let r = requirement(req);
    let v = version(candidate);
    if semver::matches(r, v) != expected { print("matching disagreement: ", req, " versus ", candidate); }
    assert(semver::matches(r, v) == expected);
}
fn ordered(a: const u8[:], b: const u8[:], expected: i64) {
    let va = version(a);
    let vb = version(b);
    assert(semver::compare(va, vb) == expected);
    assert(semver::compare(vb, va) == -expected);
    assert(semver::compare(va, va) == 0);
}
fn parsing() {
    for source in ["0.0.0", "1.2.3", "999999999999999999999999999999999999.0.0", "1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-0.3.7", "1.0.0-x.7.z.92", "1.0.0-x-y-z.--", "1.2.3--", "1.2.3+001", "1.2.3-01a", "1.2.3-00-", "1.2.3+abc.01.-", "1.2.3-alpha.99999999999999999999999999999+00.abc"] {
        let v = version(source);
    }
    let v = version("123.45.6-alpha.7+build.08");
    assert(v.major == "123" && v.minor == "45" && v.patch == "6");
    assert(v.prerelease == "alpha.7" && v.build == "build.08");
    for source in ["", "1", "1.2", "1.2.3.4", "01.2.3", "1.02.3", "1.2.03", "+1.2.3", "-1.2.3", "v1.2.3", "=1.2.3", " 1.2.3", "1.2.3 ", "1.2.3\n", "1.2.3-", "1.2.3+", "1.2.3-a.", "1.2.3-.a", "1.2.3-a..b", "1.2.3+a.", "1.2.3+.a", "1.2.3+a..b", "1.2.3-01", "1.2.3-a.00", "1.2.3-1.02", "1.2.3+a+b", "1.2.3-a_b", "1.2.3+a_b", "1.2.3-é", "1.2.3+😀", "1.2.3\0", "1.2.3-\xff", "1.2.3-\x7f", "1.2.3-\x1b"] {
        invalid(source);
    }
    // Every byte outside the identifier alphabet is rejected in both suffixes.
    for n in 256 {
        let c = n as! u8;
        if (c >= '0' && c <= '9') || (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || c == '-' { continue; }
        var pre = str("1.2.3-"); pre.push(c);
        var build = str("1.2.3+"); build.push(c);
        invalid(pre); invalid(build);
    }
}
fn precedence() {
    let ascending = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0", "2.0.0", "2.1.0", "2.1.1"];
    for a, i in ascending {
        for b, j in ascending {
            ordered(a, b, if i < j { -1 } else if i > j { 1 } else { 0 });
        }
    }
    ordered("1.2.3+one", "1.2.3+two", 0);
    ordered("1.2.3-alpha+one", "1.2.3-alpha+two", 0);
    ordered("1.2.3-9", "1.2.3-10", -1);
    ordered("1.2.3-9999999999999999999999999999999999", "1.2.3-10000000000000000000000000000000000", -1);
    ordered("1.2.3-9999999999999999999999999999999999", "1.2.3--", -1);
    ordered("1.2.3-A", "1.2.3-a", -1);
    ordered("1.2.3-a", "1.2.3-a.0", -1);
    ordered("9.0.0", "10.0.0", -1);
    ordered("1.9.0", "1.10.0", -1);
    ordered("1.0.9", "1.0.10", -1);
    ordered("99999999999999999999999999999999999999.0.0", "100000000000000000000000000000000000000.0.0", -1);
}
fn requirements() {
    let empty = semver::Requirement { .. };
    let release = version("1.2.3");
    assert(!semver::matches(empty, release));
    for r in ["*", " \t* \t", "1.2.3", "=1.2.3", " =\t1.2.3\t", ">1.2.3", ">=1.2.3", "<1.2.3", "<=1.2.3", "^1.2.3", "~1.2.3", ">= 1.2.3, < 2.0.0", "\t>=\t1.2.3 \t,\t <2.0.0\t"] { let value = requirement(r); }
    for r in ["", " ", "\t", "\n*", "*\n", "1", "1.2", "^1", "~1.2", "1.*", "1.2.x", "*.*", "*,1.2.3", "1.2.3,*", "1.2.3 || 2.0.0", "1.2.3 - 2.0.0", ">=1.2.3 <2.0.0", ">=1.2.3,", ",1.2.3", "1.2.3,,2.0.0", "==1.2.3", "=>1.2.3", "=<1.2.3", "!1.2.3", "!=1.2.3", ">", "^", "~", "=", "1.2.3\0", ">=1.2.03", ">=1.2.3-01", "1.2.3,\n2.0.0"] { invalid_requirement(r); }
    matching("*", "999999999999999999999999.0.0+meta", true);
    matching("*", "0.0.0-alpha", false);
    matching("1.2.3", "1.2.3+different", true);
    matching("1.2.3+ignored", "1.2.3", true);
    matching("1.2.3", "1.2.4", false);
    matching(">1.2.3", "1.2.3", false);
    matching(">1.2.3", "1.2.4", true);
    matching(">=1.2.3", "1.2.3", true);
    matching("<1.2.3", "1.2.3", false);
    matching("<1.2.3", "1.2.2", true);
    matching("<=1.2.3", "1.2.3+meta", true);
    matching(">=1.2.3, <2.0.0", "1.9.9", true);
    matching(">=1.2.3, <2.0.0", "2.0.0", false);
    matching(">=2.0.0, <1.0.0", "1.5.0", false);
    matching("^1.2.3", "1.9.9", true);
    matching("^1.2.3", "1.2.2", false);
    matching("^1.2.3", "2.0.0", false);
    matching("^0.2.3", "0.2.99", true);
    matching("^0.2.3", "0.3.0", false);
    matching("^0.0.3", "0.0.3+build", true);
    matching("^0.0.3", "0.0.4", false);
    matching("^0.0.0", "0.0.0", true);
    matching("^0.0.0", "0.0.1", false);
    matching("~1.2.3", "1.2.99999", true);
    matching("~1.2.3", "1.3.0", false);
    matching("~1.2.3", "1.2.2", false);
    matching("~0.0.0", "0.0.1", true);
    matching("~0.0.0-alpha", "0.0.0-0", false);
    matching("~0.0.0-alpha", "0.0.0-alpha.0", true);
    matching("~0.0.0-alpha", "0.0.0-beta", true);
    matching("~0.0.0-alpha", "0.0.0", true);
    matching("~0.0.0-alpha", "0.0.1", true);
    matching("~0.0.0-alpha", "0.0.1-alpha", false);
    matching("~0.0.0-alpha", "0.1.0", false);
    matching("^999999999999999999999999.2.3", "999999999999999999999999.999.0", true);
    matching("~1.999999999999999999999999.3", "1.999999999999999999999999.999999999999999999999999", true);
    // A prerelease comparator grants eligibility only for exactly its core.
    matching(">=1.2.3-alpha, <2.0.0", "1.2.3-beta", true);
    matching(">=1.2.3-alpha, <2.0.0", "1.2.3", true);
    matching(">=1.2.3-alpha, <2.0.0", "1.2.4-alpha", false);
    matching(">=1.2.3-alpha, <2.0.0", "1.2.3-0", false);
    matching("^1.2.3-alpha", "1.2.3-beta", true);
    matching("^1.2.3-alpha", "1.3.0-alpha", false);
    matching("^0.0.0-alpha", "0.0.0-beta", true);
    matching("^0.0.0-alpha", "0.0.0", true);
    matching("^0.0.0-alpha", "0.0.1", false);
    matching("~1.2.3-alpha", "1.2.3-beta", true);
    matching("~1.2.3-alpha", "1.2.4-beta", false);
    matching("=1.2.3-alpha", "1.2.3-alpha+meta", true);
    matching(">=1.2.3, <=1.2.3-alpha", "1.2.3-alpha", false);
    matching(">=1.0.0, <2.0.0-alpha", "2.0.0-0", true);
    matching("<2.0.0", "1.9.0-alpha", false);
}
// Returning across the source scope proves that successful values own storage.
fn scoped_version() -> semver::Version {
    var source = str("12.34.56-alpha.7+build.8");
    let value, error = semver::parse(source);
    assert(error.kind == semver::ErrorKind.None);
    value
}
fn scoped_requirement() -> semver::Requirement {
    var source = str(">=12.34.56-alpha.7, <13.0.0");
    let value, error = semver::parse_requirement(source);
    assert(error.kind == semver::ErrorKind.None);
    value
}
fn ownership() {
    let scoped_v = scoped_version();
    let scoped_r = scoped_requirement();
    assert(semver::format(scoped_v) == "12.34.56-alpha.7+build.8");
    assert(semver::matches(scoped_r, scoped_v));
    var source = str("12.34.56-alpha.7+build.8");
    let v, ve = semver::parse(source);
    assert(ve.kind == semver::ErrorKind.None);
    source.clear(); source.append("overwritten version storage");
    assert(semver::format(v) == "12.34.56-alpha.7+build.8");
    var req_source = str(">=12.34.56-alpha.7, <13.0.0");
    let r, re = semver::parse_requirement(req_source);
    assert(re.kind == semver::ErrorKind.None);
    req_source.clear(); req_source.append("overwritten requirement storage");
    assert(semver::matches(r, v));
    assert(r.comparators.len == 2);
    for comparator, index in r.comparators {
        if index == 0 { assert(comparator.version.prerelease == "alpha.7"); }
        if index == 1 { assert(comparator.version.major == "13"); }
    }
}
fn limits() {
    var large = str("1.2.3+");
    for i in 4090 { large.push('a'); }
    assert(large.len == semver::MAX_VERSION_BYTES);
    let v = version(large);
    let maximum_target = requirement(str(">= ", large));
    assert(semver::matches(maximum_target, v));
    large.push('a');
    let excess, error = semver::parse(large);
    assert(error.kind == semver::ErrorKind.TooLong && error.offset == 0);
    let oversized_target, target_error = semver::parse_requirement(str(">= ", large));
    assert(target_error.kind == semver::ErrorKind.TooLong && target_error.offset == 3);
    assert(!oversized_target.valid);
    large.clear(); large.append("1.2.3-");
    for i in 4090 { large.push('9'); }
    let pre = version(large);
    large.clear();
    for i in 4092 { large.push('9'); }
    large.append(".0.0");
    assert(large.len == semver::MAX_VERSION_BYTES);
    let core = version(large);
    var req = str("*");
    for i in 16383 { req.push(' '); }
    assert(req.len == semver::MAX_REQUIREMENT_BYTES);
    let any = requirement(req);
    req.push(' ');
    let too_large, re = semver::parse_requirement(req);
    assert(re.kind == semver::ErrorKind.TooLong && re.offset == 0);
    req.clear();
    for i in 32 { if i > 0 { req.push(','); } req.append("1.2.3"); }
    let many = requirement(req);
    assert(many.comparators.len == semver::MAX_COMPARATORS);
    req.append(",1.2.3");
    let too_many, me = semver::parse_requirement(req);
    assert(me.kind == semver::ErrorKind.TooManyComparators);
    // Invalid later input cannot expose a partially accepted prefix.
    invalid_requirement("1.2.3,>1.2.03");
    let bad, be = semver::parse_requirement("  >=1.2.3, <2.0.0?");
    assert(be.kind == semver::ErrorKind.Syntax && be.offset == 17);
    let zero, ze = semver::parse_requirement("  >=1.2.3, <2.01.0");
    assert(ze.kind == semver::ErrorKind.LeadingZero && ze.offset == 14);
    let missing, ee = semver::parse("1.2.");
    assert(ee.kind == semver::ErrorKind.Syntax && ee.offset == 4);
}
fn main() {
    parsing(); precedence(); requirements(); ownership(); limits();
    print("semver public API tests passed");
}
