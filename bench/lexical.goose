// SPDX-License-Identifier: Apache-2.0
// Lexical comparison fixtures for 1..4092-digit components.
//
// One line per fixture on stdout, tab separated:
//   fixture  digits  position  total_ns  iterations  checksum
// Outcomes are asserted before timing; the checksum makes a changed result
// observable. The driver (lexical_compare.py) writes every observation to disk
// immediately and pairs the two binaries round by round.
import semver from "..";
import std;
import os;

fn digits(count: i64, first: u8, fill: u8) -> u8[>..] {
    var out: u8[>..] = [];
    out.push(first);
    for i in count - 1 { out.push(fill); }
    out
}

fn with_byte(component: const u8[:], at: i64, value: u8) -> u8[>..] {
    var out: u8[>..] = [];
    out.append(component);
    out[at] = value;
    out
}

fn version_text(component: const u8[:]) -> u8[>..] {
    var out: u8[>..] = [];
    out.append("0.0.");
    out.append(component);
    out
}

fn measure(name: const u8[:], count: i64, position: const u8[:],
           a: semver::Version&, b: semver::Version&, iterations: i64, checksum: i64&) {
    let start = clock_ns();
    // compare+2 maps -1/0/1 to 1/2/3, so the sum distinguishes all three
    // outcomes instead of collapsing every non-equal result to zero.
    for i in iterations { checksum += semver::compare(a, b) + 2; }
    print(name, "\t", count, "\t", position, "\t", clock_ns() - start, "\t", iterations, "\t", checksum);
}

fn main() {
    let argv = args();
    var base_iterations: i64 = 200000;
    if argv.len > 1 {
        let count, ok = parse_int(argv[1]);
        assert(ok && count > 0 && count <= 100000000);
        base_iterations = count;
    }
    // Long components cost proportionally more per operation, so the largest
    // fixture runs fewer iterations. The real count is printed and recorded.
    for count in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 16, 17, 31, 32, 33, 4092] {
        let iterations = if count <= 33 { base_iterations } else { base_iterations / 64 };
        let base = digits(count, '1', '0');
        let base_text = version_text(base);
        let equal_a, ea = semver::parse(base_text);
        let equal_b, eb = semver::parse(base_text);
        assert(ea.kind == semver::ErrorKind.None && eb.kind == semver::ErrorKind.None);
        assert(semver::compare(equal_a, equal_b) == 0);
        var checksum: i64 = 0;
        measure("equal", count, "none", equal_a, equal_b, iterations, checksum);

        let first_text = version_text(digits(count, '2', '0'));
        let first_b, fb = semver::parse(first_text);
        assert(fb.kind == semver::ErrorKind.None);
        assert(semver::compare(equal_a, first_b) == -1);
        measure("first", count, "start", equal_a, first_b, iterations, checksum);

        // Components that differ near the start are the realistic case for long
        // identifiers, so measure byte 1 and byte 2 separately from byte 0.
        if count >= 5 {
            let early1_text = version_text(with_byte(base, 1, '1'));
            let early1_b, e1 = semver::parse(early1_text);
            assert(e1.kind == semver::ErrorKind.None);
            assert(semver::compare(equal_a, early1_b) == -1);
            measure("early1", count, "byte1", equal_a, early1_b, iterations, checksum);
        }
        if count >= 7 {
            let early2_text = version_text(with_byte(base, 2, '1'));
            let early2_b, e2 = semver::parse(early2_text);
            assert(e2.kind == semver::ErrorKind.None);
            assert(semver::compare(equal_a, early2_b) == -1);
            measure("early2", count, "byte2", equal_a, early2_b, iterations, checksum);
        }
        if count >= 3 {
            let middle_text = version_text(with_byte(base, count / 2, '1'));
            let middle_b, mb = semver::parse(middle_text);
            assert(mb.kind == semver::ErrorKind.None);
            assert(semver::compare(equal_a, middle_b) == -1);
            measure("middle", count, "middle", equal_a, middle_b, iterations, checksum);
        }
        if count >= 2 {
            let last_text = version_text(with_byte(base, count - 1, '1'));
            let last_b, lb = semver::parse(last_text);
            assert(lb.kind == semver::ErrorKind.None);
            assert(semver::compare(equal_a, last_b) == -1);
            measure("last", count, "end", equal_a, last_b, iterations, checksum);
        }
    }
}
