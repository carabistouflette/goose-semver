// SPDX-License-Identifier: Apache-2.0
import semver from "..";
import std;
import os;

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
    print("checksum\t", checksum);
}
