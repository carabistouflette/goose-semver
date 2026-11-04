#!/usr/bin/env python3
"""Targeted exhaustive byte edits and grammar products, plus seeded mutations.

This exhausts the explicitly enumerated finite neighborhoods below, not all
SemVer inputs. Expected results come from model.py's independent Python oracle.
Cases stream through bounded batches; the binary accepts oracle.goose's hex
protocol. No external dependencies, shell execution or network access.
"""

import argparse
import itertools
import random
import subprocess

from model import (COMPARATOR_LIMIT, REQUIREMENT_LIMIT, SEED, VERSION_LIMIT,
                   expected_response, generated_version, mutate)

BATCH_CASES = 1024
BATCH_BYTES = 4 * 1024 * 1024


def byte_edits(source):
    """Every one-byte insertion/substitution, deletion and prefix truncation."""
    for at in range(len(source) + 1):
        yield source[:at]
        for value in range(256):
            byte = bytes([value])
            yield source[:at] + byte + source[at:]
            if at < len(source) and source[at] != value:
                yield source[:at] + byte + source[at + 1:]
        if at < len(source):
            yield source[:at] + source[at + 1:]


def cases(seed, random_cases):
    # Every byte, including delimiter-looking bytes, NUL, controls and non-ASCII,
    # at every position in representative complete versions and requirements.
    for source in (b"0.0.0", b"10.20.30-01a+001", b"1.2.3-alpha.0+build.01"):
        for edited in byte_edits(source):
            yield "P", (edited,)
    for source in (b"*", b" >=1.2.3-alpha.1, <2.0.0 "):
        for edited in byte_edits(source):
            yield "M", (edited, b"1.2.3-beta")

    # Exhaustive small core-token product includes invalid leading zeroes,
    # missing fields, signs and alphabetic tokens.
    core_tokens = (b"", b"0", b"1", b"9", b"10", b"00", b"01", b"-", b"a")
    for parts in itertools.product(core_tokens, repeat=3):
        yield "P", (b".".join(parts),)
    pres = (b"", b"-0", b"-00", b"-01a", b"--", b"-a", b"-a.0", b"-a.00",
            b"-0.a", b"-a..b", b"-a.", b"-.a", b"-", b"-A")
    builds = (b"", b"+0", b"+00", b"+a", b"+a.00", b"+a..b", b"+a.", b"+", b"++a")
    for core in itertools.product((b"0", b"1", b"9", b"10"), repeat=3):
        for pre, build in itertools.product(pres, builds):
            yield "P", (b".".join(core) + pre + build,)

    # Same-core ordering reaches identifier classification and list-prefix rules.
    atoms = (b"0", b"1", b"2", b"9", b"10", b"01a", b"A", b"a", b"-", b"a-", b"alpha")
    pres = list(atoms) + [a + b"." + b for a, b in itertools.product(atoms, repeat=2)]
    versions = [b"1.2.3"] + [b"1.2.3-" + pre for pre in pres]
    for a, b in itertools.product(versions, repeat=2):
        yield "C", (a, b)
    for a in versions:
        yield "C", (a, a + b"+001")
        yield "M", (b"=" + a + b"+ignored", a + b"+other")

    # Enumerate operator/whitespace/target boundaries; only ASCII space and tab
    # count as whitespace, and all versions must remain complete.
    operators = (b"", b"=", b">", b">=", b"<", b"<=", b"^", b"~", b"==", b"=>", b"!=")
    spaces = (b"", b" ", b"\t", b" \t", b"\n", b"\r")
    targets = (b"0.0.0", b"0.0.0-alpha", b"0.1.0", b"1.2.3", b"1.2.3-alpha",
               b"1.2", b"1.2.3-01", b"1.2.3+00")
    for op, space, target in itertools.product(operators, spaces, targets):
        req = op + space + target
        for candidate in (b"0.0.0", b"0.0.0-beta", b"0.0.1", b"0.1.1",
                          b"1.2.3", b"1.2.3-alpha", b"1.2.3-beta", b"1.2.4"):
            yield "M", (req, candidate)
        for comma in (b",", b", ", b"\t,\t", b" ", b",,", b",\n"):
            yield "M", (req + comma + b"<2.0.0", b"1.2.3-beta")

    # Exact resource edges and successful prefixes followed by rejected input.
    candidates = (b"0.0.0", b"1.2.3", b"1.2.3-alpha", b"2.0.0-alpha")
    for count in (0, 1, COMPARATOR_LIMIT - 1, COMPARATOR_LIMIT, COMPARATOR_LIMIT + 1):
        req = b",".join([b">=0.0.0"] * count)
        for end in (b"", b",", b",bad", b",*", b",<2.0.0-alpha"):
            for candidate in candidates:
                yield "M", (req + end, candidate)
    # Admission can come from any comparator, including the last legal slot;
    # a stable-only conjunction excludes the same otherwise satisfying input.
    stable = [b">=0.0.0"] * (COMPARATOR_LIMIT - 1)
    for targets in (stable + [b"<1.2.3-z"], [b"<1.2.3-z"] + stable,
                    stable + [b"<2.0.0"]):
        yield "M", (b",".join(targets), b"1.2.3-a")
    for size in (VERSION_LIMIT - 1, VERSION_LIMIT, VERSION_LIMIT + 1):
        target = b"1.2.3-" + b"a" * (size - 6)
        yield "P", (target,)
        for op in (b"", b"=", b">= ", b"^", b"~"):
            for start in (b"", b">=0.0.0, "):
                yield "M", (start + op + target, b"1.2.3")
        for count in (3, 4):
            yield "M", (b",".join([b">=" + target] * count), b"1.2.3")
    for size in (REQUIREMENT_LIMIT - 1, REQUIREMENT_LIMIT, REQUIREMENT_LIMIT + 1):
        for suffix in (b"*", b"=1.2.3", b"=1.2.3,", b"=1.2.3, =1.2.3"):
            yield "M", (b" " * (size - len(suffix)) + suffix, b"1.2.3")

    # Put every byte on both sides of scalar/SIMD block and tail boundaries.
    # Valid prefixes force the identifier scanner to reach the edited byte.
    for length in (15, 16, 17, 31, 32, 33, 63, 64, 65, 127):
        for at in sorted({0, length - 1, max(0, length - 16), min(16, length - 1)}):
            for byte in range(256):
                payload = b"a" * at + bytes([byte]) + b"a" * (length - at - 1)
                for prefix in (b"1.2.3-", b"12.3.45+"):
                    yield "P", (prefix + payload,)
    # Requirement-token scanning has different delimiters from identifier
    # scanning. Shift the token start and put every byte around block edges;
    # only comma, SP and TAB may end a target (LF/CR/NUL remain invalid bytes).
    for length in (15, 16, 17, 31, 32, 33, 63, 64, 65, 127):
        target = b"1.2.3-" + b"a" * (length - 6)
        for prefix in (b"=", b">=0.0.0, <= "):
            for at in sorted({15, 16, 17, 31, 32, 33, length}):
                if at > length:
                    continue
                for byte in range(256):
                    edited = target[:at] + bytes([byte]) + target[at:]
                    yield "M", (prefix + edited + b", <2.0.0", b"1.2.3-a")
    for length in (15, 16, 17, 31, 32, 33, 63, 64, 65, 127):
        for tail in (b"", b"a", b"-", b".a", b"+001", b"?", b"\0", b"\xff"):
            yield "P", (b"1.2.3-0" + b"0" * length + tail,)
    # Force the digit scanner through its scalar prefix, SIMD tail and first
    # nondigit; all-byte noise at the start would usually miss these paths.
    for length in (15, 16, 17, 31, 32, 33, 63, 64, 65, 127):
        for at in sorted({0, length - 1, max(0, length - 16), min(16, length - 1)}):
            for byte in range(256):
                digits = b"9" * at + bytes([byte]) + b"9" * (length - at - 1)
                yield "P", (digits + b".0.0",)
                yield "P", (b"1.2.3-0" + digits,)
                yield "C", (b"1.2.3-" + digits, b"1.2.3-" + b"9" * length)
    # Every valid nonnumeric first byte, including case and hyphen, exercises
    # the first-byte ordering proof. Digits remain on the general classifier.
    letters = b"-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    for a in letters:
        for b in letters:
            left = b"1.2.3-" + bytes([a]) + b".1"
            right = b"1.2.3-" + bytes([b]) + b".2"
            yield "C", (left, right)
            yield "C", (right, left)
    # Seeded multi-byte edits reach combinations beyond the exhaustive one-byte
    # neighborhoods, while retaining valid prefixes frequently.
    rng = random.Random(seed)
    for _ in range(random_cases):
        source = generated_version(rng)
        for _ in range(rng.randrange(1, 5)):
            source = mutate(rng, source)
        if rng.randrange(2):
            yield "P", (source,)
        else:
            req = rng.choice(operators[:8]) + source
            if rng.randrange(2):
                req += rng.choice((b",", b", ", b"\t,\t")) + rng.choice(operators[:8]) + generated_version(rng)
            yield "M", (req, generated_version(rng))


def protocol(operation, fields):
    return operation + "\t" + "\t".join(field.hex() for field in fields) + "\n"


def run_batch(binary, batch, first_index, seed):
    expected = [expected_response(operation, fields) for operation, fields in batch]
    payload = "".join(protocol(operation, fields) for operation, fields in batch)
    result = subprocess.run([binary], input=payload, capture_output=True,
                            text=True, timeout=60, check=False)
    if result.returncode:
        raise SystemExit(f"seed={seed} batch starts at case={first_index}: "
                         f"oracle exited {result.returncode}; stderr={result.stderr[-4000:]!r}")
    actual = result.stdout.splitlines()
    if len(actual) != len(expected):
        raise SystemExit(f"seed={seed} batch starts at case={first_index}: "
                         f"got {len(actual)} responses, expected {len(expected)}; "
                         f"stderr={result.stderr[-1000:]!r}")
    for offset, (wanted, got) in enumerate(zip(expected, actual)):
        if wanted != got:
            operation, fields = batch[offset]
            raise SystemExit(f"seed={seed} case={first_index + offset}: "
                             f"expected {wanted}, got {got!r}\n" + protocol(operation, fields))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", nargs="?")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--random-cases", type=int, default=2000)
    parser.add_argument("--count", action="store_true", help="count generated cases without running a binary")
    args = parser.parse_args()
    if args.random_cases < 0 or args.random_cases > 1_000_000:
        parser.error("--random-cases must be in 0..1000000")
    if not args.count and not args.binary:
        parser.error("binary is required unless --count is used")
    batch = []
    size = 0
    total = 0
    batches = 0
    for case in cases(args.seed, args.random_cases):
        if args.count:
            total += 1
            continue
        case_size = len(protocol(*case))
        if batch and (len(batch) == BATCH_CASES or size + case_size > BATCH_BYTES):
            run_batch(args.binary, batch, total, args.seed)
            total += len(batch)
            batches += 1
            batch = []
            size = 0
        batch.append(case)
        size += case_size
    if batch:
        run_batch(args.binary, batch, total, args.seed)
        total += len(batch)
        batches += 1
    if args.count:
        print(f"targeted cases: {total}; seed={args.seed}")
    else:
        print(f"targeted exhaustive neighborhoods: {total} cases passed in {batches} bounded batches; seed={args.seed}")


if __name__ == "__main__":
    main()
