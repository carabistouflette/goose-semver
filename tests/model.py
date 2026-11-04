#!/usr/bin/env python3
"""Deterministic differential checks against an independent bytes/integers oracle.

The program under test implements the line protocol documented in oracle.goose.
No third-party package, shell execution, or network access is used.
"""

import argparse
import functools
import random
import re
import subprocess
import sys

SEED = 20261104
VERSION_LIMIT = 4096
REQUIREMENT_LIMIT = 16384
COMPARATOR_LIMIT = 32
VERSION_RE = re.compile(
    rb"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    rb"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    rb"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
)
COMPARATOR_RE = re.compile(rb"(>=|<=|=|>|<|\^|~)?[ \t]*(.+)")


def parse_version(source):
    if len(source) > VERSION_LIMIT:
        return None
    match = VERSION_RE.fullmatch(source)
    if match is None:
        return None
    major, minor, patch, pre, _build = match.groups()
    identifiers = tuple(pre.split(b".")) if pre else ()
    if any(part.isdigit() and len(part) > 1 and part.startswith(b"0")
           for part in identifiers):
        return None
    return (int(major), int(minor), int(patch)), identifiers


def sign(number):
    return (number > 0) - (number < 0)


def compare_versions(left, right):
    left_core, left_pre = left
    right_core, right_pre = right
    if left_core != right_core:
        return sign((left_core > right_core) - (left_core < right_core))
    if not left_pre or not right_pre:
        return sign(bool(right_pre) - bool(left_pre))
    for a, b in zip(left_pre, right_pre):
        if a == b:
            continue
        an, bn = a.isdigit(), b.isdigit()
        if an != bn:
            return -1 if an else 1
        if an:
            return sign(int(a) - int(b))
        return -1 if a < b else 1
    return sign(len(left_pre) - len(right_pre))


def parse_requirement(source):
    if len(source) > REQUIREMENT_LIMIT:
        return None
    source = source.strip(b" \t")
    if source == b"*":
        return []
    parts = source.split(b",")
    if len(parts) > COMPARATOR_LIMIT:
        return None
    result = []
    for part in parts:
        match = COMPARATOR_RE.fullmatch(part.strip(b" \t"))
        if match is None:
            return None
        op, text = match.groups()
        version = parse_version(text)
        if version is None:
            return None
        result.append((op or b"=", version))
    return result


def requirement_matches(requirement, version):
    core, pre = version
    eligible = not pre or any(target[1] and target[0] == core
                              for _op, target in requirement)
    if not eligible:
        return False
    for op, target in requirement:
        order = compare_versions(version, target)
        if op == b"=" and order != 0:
            return False
        if op == b">" and order <= 0:
            return False
        if op == b">=" and order < 0:
            return False
        if op == b"<" and order >= 0:
            return False
        if op == b"<=" and order > 0:
            return False
        if op in (b"^", b"~"):
            major, minor, patch = target[0]
            if op == b"~":
                upper = major, minor + 1, 0
            elif major:
                upper = major + 1, 0, 0
            elif minor:
                upper = 0, minor + 1, 0
            else:
                upper = 0, 0, patch + 1
            if order < 0 or core >= upper:
                return False
    return True


def expected_response(operation, fields):
    if operation == "P":
        return "1" if parse_version(fields[0]) is not None else "0"
    if operation == "C":
        left, right = map(parse_version, fields)
        if left is None or right is None:
            return "E"
        return str(compare_versions(left, right))
    requirement = parse_requirement(fields[0])
    version = parse_version(fields[1])
    if requirement is None or version is None:
        return "E"
    return "1" if requirement_matches(requirement, version) else "0"


def generated_version(rng):
    def number():
        if rng.randrange(8):
            return str(rng.choice([0, 1, 2, 3, 9, 10, 99, 100, 65535]))
        return str(rng.randrange(1, 10)) + "".join(
            rng.choice("0123456789") for _ in range(rng.choice([19, 40, 127])))

    source = ".".join(number() for _ in range(3))
    if rng.randrange(2):
        source += "-" + ".".join(rng.choice([
            "0", "1", "9", "10", "alpha", "beta", "rc", "01a", "-", "--",
            "A", "a", "1-2", number()
        ]) for _ in range(rng.randrange(1, 6)))
    if rng.randrange(3) == 0:
        source += "+" + ".".join(rng.choice([
            "001", "build", "0", "SHA-123", "--", number()
        ]) for _ in range(rng.randrange(1, 4)))
    return source.encode("ascii")


def mutate(rng, value):
    at = rng.randrange(len(value) + 1)
    replacement = rng.choice([b"", b"0", b".", b"-", b"+", b" ", b"\t",
                              b"\n", b"\r", b"\0", b"\xff", b"v", b"_", b"=", b","])
    removed = rng.randrange(3)
    return value[:at] + replacement + value[at + removed:]


def cases(security):
    rng = random.Random(SEED)
    generated = [generated_version(rng) for _ in range(600)]
    fixed = [b"0.0.0", b"1.2.3", b"1.2.3-alpha", b"1.2.3-alpha.1",
             b"1.2.3+001", b"1.2.3-01a", b"1.2.3--", b"1.2.3-0",
             b"1.2.3-00", b"", b"v1.2.3", b"1.2", b"1.2.3\n",
             b"1.2.3-", b"1.2.3+", b"1.2.3-a..b", b"1.2.3-\xff",
             b"01.2.3", b"1.02.3", b"1.2.03", b"1.2.3+00"]
    for prefix in (b"", b"1.2.3-", b"1.2.3+"):
        for length in (VERSION_LIMIT - 1, VERSION_LIMIT, VERSION_LIMIT + 1):
            if prefix:
                fixed.append(prefix + b"1" * (length - len(prefix)))
            else:
                fixed.append(b"1" * (length - 4) + b".0.0")
    for source in fixed + generated:
        yield "P", (source,)
    for _ in range(2400):
        yield "P", (mutate(rng, rng.choice(generated)),)
    valid = [v for v in fixed + generated if parse_version(v) is not None]
    for _ in range(1000):
        a, b = rng.choice(valid), rng.choice(valid)
        yield "C", (a, b)
        yield "C", (b, a)
        yield "C", (a, a)
    # Each sorted triple checks actual pairwise ordering and transitive closure.
    for _ in range(120):
        triple = sorted(rng.sample(valid, 3), key=functools.cmp_to_key(
            lambda a, b: compare_versions(parse_version(a), parse_version(b))))
        yield "C", (triple[0], triple[1])
        yield "C", (triple[1], triple[2])
        yield "C", (triple[0], triple[2])
    requirements = [b"*", b"=1.2.3", b"^0.0.0", b"^0.0.0-alpha", b"~0.0.0-alpha",
                    b">=1.2.3-alpha, <2.0.0", b">1.2.3, <1.2.3", b"^1.2.3",
                    b"~1.2.3", b"^0.2.3", b"^0.0.3", b"", b" ", b"*,1.2.3",
                    b"1.2", b"1.*", b"1.2.3 || 2.0.0", b"1.2.3,", b"==1.2.3",
                    b">=1.2.3 <2.0.0", b"1.2.3\n", b"1.2.3\0"]
    for count in (31, 32, 33):
        requirements.append(b",".join([b">=0.0.0"] * count))
    for length in (REQUIREMENT_LIMIT - 1, REQUIREMENT_LIMIT, REQUIREMENT_LIMIT + 1):
        requirements.append(b" " * (length - 1) + b"*")
    prereleases = [b"0.0.0-alpha", b"0.0.0-alpha.1", b"0.0.0", b"0.0.1-alpha",
                   b"0.0.1", b"0.2.3-alpha", b"0.2.3", b"0.2.4", b"0.3.0-alpha",
                   b"1.2.3-alpha", b"1.2.3-beta", b"1.2.3", b"1.2.4-alpha",
                   b"1.2.4", b"1.3.0", b"2.0.0-alpha", b"2.0.0"]
    for req in requirements:
        for candidate in prereleases:
            yield "M", (req, candidate)
    operators = [b"", b"=", b">", b">=", b"<", b"<=", b"^", b"~"]
    for _ in range(1500):
        target = rng.choice(valid)
        req = b" \t" + rng.choice(operators) + rng.choice([b"", b" ", b"\t"]) + target
        if rng.randrange(3) == 0:
            req += b", " + rng.choice(operators) + rng.choice(valid)
        if rng.randrange(4) == 0:
            req = mutate(rng, req)
        candidate = rng.choice([target, rng.choice(valid), rng.choice(prereleases)])
        yield "M", (req, candidate)
    # Invalid versions must produce E for either comparison operand and matching.
    for source in [b"", b"1", b"1.2.3\0", b"1.2.3-01", b"\xff"]:
        yield "C", (source, b"1.2.3")
        yield "C", (b"1.2.3", source)
        yield "M", (b"*", source)
    if not security:
        return
    # Large hostile inputs remain small in number so the batched protocol is bounded.
    for source in [b"1" * (1024 * 1024 + 1), b"1.2.3-" + b"a." * 2048,
                   b"1.2.3-" + b"0" * 4090, b"1.2.3+" + b"a" * 4090,
                   b"1.2.3-" + b"a." * 2044 + b"a", b"1.2.3+" + b"0." * 2044 + b"0"]:
        yield "P", (source,)
    for _ in range(1200):
        source = rng.randbytes(rng.randrange(0, 5000))
        yield "P", (source,)
    for size in (4090, 4091, 4092):
        target = b"1.2.3-" + b"a" * size
        for count in (1, 3, 4, 5):
            req = b",".join([b">=" + target] * count)
            yield "M", (req, b"1.2.3")
    for count in (32, 33, 4096):
        yield "M", (b",".join([b">=0.0.0"] * count), b"1.2.3")
    huge = b"9" * 4090
    yield "C", (huge + b".0.0", b"1" + b"0" * 4089 + b".0.0")
    yield "C", (b"1.2.3-" + b"9" * 4090, b"1.2.3-" + b"1" + b"0" * 4089)
    yield "M", (b"^" + huge + b".0.0", huge + b".0.1")
    yield "M", (b"~0." + b"9" * 4088 + b".0", b"0." + b"9" * 4088 + b".1")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary")
    parser.add_argument("--security", action="store_true")
    args = parser.parse_args()
    test_cases = list(cases(args.security))
    expected = [expected_response(operation, fields) for operation, fields in test_cases]
    payload = "".join(operation + "\t" + "\t".join(field.hex() for field in fields) + "\n"
                      for operation, fields in test_cases)
    completed = subprocess.run([args.binary], input=payload, text=True,
                               capture_output=True, timeout=60, check=False)
    if completed.returncode:
        raise SystemExit(f"oracle process exited {completed.returncode}: {completed.stderr[-4000:]}")
    actual = completed.stdout.splitlines()
    if len(actual) != len(expected):
        raise SystemExit(f"response count: got {len(actual)}, expected {len(expected)}; "
                         f"stderr={completed.stderr[-1000:]!r}")
    for index, (wanted, got) in enumerate(zip(expected, actual)):
        if wanted != got:
            operation, fields = test_cases[index]
            # A full failing case is reproducible even for binary/large inputs.
            protocol = operation + "\t" + "\t".join(field.hex() for field in fields)
            raise SystemExit(f"seed={SEED} case={index}: expected {wanted}, got {got!r}\n{protocol}")
    print(f"{'security' if args.security else 'property'}: {len(test_cases)} cases passed; seed={SEED}")


if __name__ == "__main__":
    main()
