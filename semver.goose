// SPDX-License-Identifier: Apache-2.0
import std;
namespace semver;

const MAX_VERSION_BYTES = 4096;
const MAX_REQUIREMENT_BYTES = 16384;
const MAX_COMPARATORS = 32;

enum ErrorKind { None, TooLong, Syntax, LeadingZero, TooManyComparators }
struct Error { kind: ErrorKind = ErrorKind.None, offset: i64 = 0 }
struct Version { major: u8[], minor: u8[], patch: u8[], prerelease: u8[], build: u8[] }
enum Op { Equal, Greater, GreaterEqual, Less, LessEqual, Caret, Tilde }
struct Comparator { op: Op, version: Version }
struct Requirement { comparators: Comparator[], valid: bool = false }

fn digit(c: u8) -> bool { c >= '0' && c <= '9' }
fn identifier_byte(c: u8) -> bool {
    digit(c) || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '-'
}
fn numeric(text: const u8[:]) -> bool {
    for c in text { if !digit(c) { return false; } }
    true
}
fn core(text: const u8[:], at: i64&) -> Error {
    let start = at;
    while at < text.len && digit(text[at]) { at += 1; }
    if at == start { return Error { ErrorKind.Syntax, at }; }
    if at - start > 1 && text[start] == '0' { return Error { ErrorKind.LeadingZero, start }; }
    Error { .. }
}
fn identifiers(text: const u8[:], at: i64&, prerelease: bool) -> Error {
    while true {
        let start = at;
        var only_digits = true;
        while at < text.len && identifier_byte(text[at]) {
            if !digit(text[at]) { only_digits = false; }
            at += 1;
        }
        if at == start { return Error { ErrorKind.Syntax, at }; }
        if prerelease && only_digits && at - start > 1 && text[start] == '0' {
            return Error { ErrorKind.LeadingZero, start };
        }
        if at == text.len || text[at] != '.' { break; }
        at += 1;
    }
    Error { .. }
}

// Validate before copying. Returned fields own their bytes, including suffixes.
fn parse(text: const u8[:]) -> Version, Error {
    let empty = Version { .. };
    if text.len > MAX_VERSION_BYTES { return empty, Error { ErrorKind.TooLong, 0 }; }
    var at = 0;
    let major_error = core(text, at);
    if major_error.kind != ErrorKind.None { return empty, major_error; }
    let major_end = at;
    if at == text.len || text[at] != '.' { return empty, Error { ErrorKind.Syntax, at }; }
    at += 1;
    let minor_start = at;
    let minor_error = core(text, at);
    if minor_error.kind != ErrorKind.None { return empty, minor_error; }
    let minor_end = at;
    if at == text.len || text[at] != '.' { return empty, Error { ErrorKind.Syntax, at }; }
    at += 1;
    let patch_start = at;
    let patch_error = core(text, at);
    if patch_error.kind != ErrorKind.None { return empty, patch_error; }
    let patch_end = at;
    var pre_start = at;
    var pre_end = at;
    if at < text.len && text[at] == '-' {
        at += 1;
        pre_start = at;
        let error = identifiers(text, at, true);
        if error.kind != ErrorKind.None { return empty, error; }
        pre_end = at;
    }
    var build_start = at;
    if at < text.len && text[at] == '+' {
        at += 1;
        build_start = at;
        let error = identifiers(text, at, false);
        if error.kind != ErrorKind.None { return empty, error; }
    }
    else { build_start = text.len; }
    if at != text.len { return empty, Error { ErrorKind.Syntax, at }; }
    return Version {
        str(text[..major_end]), str(text[minor_start..minor_end]),
        str(text[patch_start..patch_end]), str(text[pre_start..pre_end]),
        str(text[build_start..]),
    }, Error { .. };
}

fn lexical(a: const u8[:], b: const u8[:]) -> i64 {
    let count = if a.len < b.len { a.len } else { b.len };
    for i in count {
        if a[i] < b[i] { return -1; }
        if a[i] > b[i] { return 1; }
    }
    if a.len < b.len { return -1; }
    if a.len > b.len { return 1; }
    0
}
fn decimal(a: const u8[:], b: const u8[:]) -> i64 {
    if a.len < b.len { return -1; }
    if a.len > b.len { return 1; }
    lexical(a, b)
}
fn same_core(a: Version&, b: Version&) -> bool {
    a.major == b.major && a.minor == b.minor && a.patch == b.patch
}
fn prerelease_compare(a: const u8[:], b: const u8[:]) -> i64 {
    if a.len == 0 { return if b.len == 0 { 0 } else { 1 }; }
    if b.len == 0 { return -1; }
    var left = 0;
    var right = 0;
    while left < a.len && right < b.len {
        var left_end = left;
        var right_end = right;
        while left_end < a.len && a[left_end] != '.' { left_end += 1; }
        while right_end < b.len && b[right_end] != '.' { right_end += 1; }
        let x = a[left..left_end];
        let y = b[right..right_end];
        // Identical identifiers need neither classification nor a second scan.
        if x != y {
            let xn = numeric(x);
            let yn = numeric(y);
            if xn != yn { return if xn { -1 } else { 1 }; }
            let order = if xn { decimal(x, y) } else { lexical(x, y) };
            if order != 0 { return order; }
        }
        left = left_end;
        right = right_end;
        if left < a.len { left += 1; }
        if right < b.len { right += 1; }
    }
    if left < a.len { return 1; }
    if right < b.len { return -1; }
    0
}
// Parsed, unmodified values only. Build metadata does not affect precedence.
fn compare(a: Version&, b: Version&) -> i64 {
    let major = decimal(a.major, b.major);
    if major != 0 { return major; }
    let minor = decimal(a.minor, b.minor);
    if minor != 0 { return minor; }
    let patch = decimal(a.patch, b.patch);
    if patch != 0 { return patch; }
    prerelease_compare(a.prerelease, b.prerelease)
}
fn format(version: Version&) -> u8[>..] {
    var out = str(version.major, ".", version.minor, ".", version.patch);
    if version.prerelease.len > 0 { out.push('-'); out.append(version.prerelease); }
    if version.build.len > 0 { out.push('+'); out.append(version.build); }
    out
}
fn whitespace(c: u8) -> bool { c == ' ' || c == '\t' }
fn skip_space(text: const u8[:], at: i64&) {
    while at < text.len && whitespace(text[at]) { at += 1; }
}
fn parse_requirement(text: const u8[:]) -> Requirement, Error {
    let empty = Requirement { .. };
    if text.len > MAX_REQUIREMENT_BYTES { return empty, Error { ErrorKind.TooLong, 0 }; }
    var at = 0;
    skip_space(text, at);
    if at < text.len && text[at] == '*' {
        at += 1;
        skip_space(text, at);
        if at == text.len { return Requirement { comparators: [], valid: true }, Error { .. }; }
        return empty, Error { ErrorKind.Syntax, at };
    }
    var comparators: Comparator[>..] = [];
    while true {
        if comparators.len == MAX_COMPARATORS { return empty, Error { ErrorKind.TooManyComparators, at }; }
        var op = Op.Equal;
        if at < text.len {
            let c = text[at];
            if c == '=' || c == '>' || c == '<' || c == '^' || c == '~' {
                at += 1;
                if c == '>' { op = Op.Greater; }
                if c == '<' { op = Op.Less; }
                if c == '^' { op = Op.Caret; }
                if c == '~' { op = Op.Tilde; }
                if (c == '>' || c == '<') && at < text.len && text[at] == '=' {
                    at += 1;
                    op = if c == '>' { Op.GreaterEqual } else { Op.LessEqual };
                }
            }
        }
        skip_space(text, at);
        let start = at;
        while at < text.len && text[at] != ',' && !whitespace(text[at]) { at += 1; }
        let version, error = parse(text[start..at]);
        if error.kind != ErrorKind.None {
            return empty, Error { error.kind, start + error.offset };
        }
        comparators.push(Comparator { op, copy(version) });
        skip_space(text, at);
        if at == text.len { break; }
        if text[at] != ',' { return empty, Error { ErrorKind.Syntax, at }; }
        at += 1;
        skip_space(text, at);
    }
    return Requirement { comparators: copy(comparators), valid: true }, Error { .. };
}
fn comparator_matches(comparator: Comparator&, version: Version&) -> bool {
    let target .= comparator.version;
    let order = compare(version, target);
    if comparator.op == Op.Equal { return order == 0; }
    if comparator.op == Op.Greater { return order > 0; }
    if comparator.op == Op.GreaterEqual { return order >= 0; }
    if comparator.op == Op.Less { return order < 0; }
    if comparator.op == Op.LessEqual { return order <= 0; }
    if order < 0 || version.major != target.major { return false; }
    if comparator.op == Op.Tilde || target.major == "0" {
        if version.minor != target.minor { return false; }
    }
    if comparator.op == Op.Caret && target.major == "0" && target.minor == "0" {
        return version.patch == target.patch;
    }
    true
}
fn matches(requirement: Requirement&, version: Version&) -> bool {
    if !requirement.valid || version.major.len == 0 { return false; }
    var eligible = version.prerelease.len == 0;
    for comparator in requirement.comparators {
        if !comparator_matches(comparator, version) { return false; }
        if comparator.version.prerelease.len > 0 && same_core(comparator.version, version) { eligible = true; }
    }
    eligible
}
