#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare Goose and pinned Rust semver 1.0.28 with the independent model.py.

This tests their shared domain, not Rust's broader requirement grammar. Every
requirement uses explicit operators and complete versions, comma conjunctions
with ASCII spaces, or a standalone star. Core numbers fit u64; numeric prerelease
identifiers need not. Goose's documented resource limits apply to every case.
No third-party Python packages, shell execution or network access are used.
"""

import argparse
import collections
import itertools
import random
import subprocess

from model import (COMPARATOR_LIMIT, REQUIREMENT_LIMIT, SEED, VERSION_LIMIT,
                   expected_response, mutate, parse_requirement, parse_version)

BATCH_CASES = 1024
BATCH_BYTES = 4 * 1024 * 1024
U64_MAX = (1 << 64) - 1
OPERATORS = (b"=", b">", b">=", b"<", b"<=", b"^", b"~")
PRES = (b"", b"0", b"1", b"9", b"10", b"A", b"a", b"-", b"01a",
        b"alpha", b"alpha.0", b"alpha.1", b"alpha.1.0", b"alpha.beta",
        b"rc.1", b"9" * 20, b"1" + b"0" * 20, b"9" * 127,
        b"1" + b"0" * 127, b"a." * 30 + b"z")
CORES = ((0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 2, 3), (1, 2, 3),
         (U64_MAX, 0, 0), (0, U64_MAX, 0), (0, 0, U64_MAX))


def version(core, pre=b"", build=b""):
    result = b".".join(str(part).encode("ascii") for part in core)
    return result + (b"-" + pre if pre else b"") + (b"+" + build if build else b"")


def neighbors(core):
    """Boundary-adjacent cores, including resetting less significant fields."""
    result = {core}
    for at, value in enumerate(core):
        for delta in (-1, 1):
            if 0 <= value + delta <= U64_MAX:
                changed = list(core)
                changed[at] += delta
                result.add(tuple(changed))
                result.add(tuple(changed[:at + 1] + [0] * (2 - at)))
    return sorted(result)


def generated_version(rng):
    def number():
        return rng.choice((0, 1, 2, 9, 10, 99, U64_MAX - 1, U64_MAX,
                           rng.getrandbits(64)))

    core = rng.choice(CORES) if rng.randrange(2) else tuple(number() for _ in range(3))
    pre = rng.choice(PRES)
    if pre and rng.randrange(3) == 0:
        pre += b"." + rng.choice(PRES[1:15])
    build = rng.choice((b"", b"001", b"build.00", b"SHA-123", b"--"))
    return version(core, pre, build)


def cases(seed):
    # Dense products force comparisons beyond the core, cover numeric magnitude
    # and list prefixes, and prove that build metadata does not change precedence.
    for core in CORES:
        versions = [version(core, pre) for pre in PRES]
        for source in versions:
            yield "P", (source,)
        for left, right in itertools.product(versions, repeat=2):
            yield "C", (left, right)
            yield "C", (left + b"+001", right + b"+other.00")
            for op in OPERATORS:
                yield "M", (op + left, right)

    # Caret/tilde boundaries, including zero-major and u64 maximum values.
    # A prerelease on an upper bound can make that core eligible, while a caret
    # or tilde comparator must still enforce its own allowed core prefix.
    for core in CORES:
        for target_pre in (b"", b"0", b"alpha.1"):
            target = version(core, target_pre)
            for candidate_core in neighbors(core):
                for candidate_pre in (b"", b"0", b"alpha", b"beta"):
                    candidate = version(candidate_core, candidate_pre)
                    for op in OPERATORS:
                        yield "M", (op + target, candidate)
            for other_core in neighbors(core):
                upper = version(other_core, b"alpha")
                for candidate_pre in (b"0", b"alpha", b"beta", b""):
                    candidate = version(other_core, candidate_pre)
                    for op in (b">=", b"^", b"~"):
                        for first, second in ((op + target, b"<" + upper),
                                              (b"<" + upper, op + target)):
                            yield "M", (first + b", " + second, candidate)

    # Eligibility requires one same-core prerelease comparator, then every
    # comparator still has to pass. Vary its position and nearby core identities.
    gates = (b">=1.0.0, <2.0.0-alpha", b"<2.0.0-alpha, >=1.0.0",
             b">=1.2.3-alpha, <2.0.0", b">=1.2.3, <=1.2.3-beta",
             b">=1.2.3-alpha, >1.2.3-beta", b"^1.2.3, <2.0.0-alpha",
             b"~1.2.3, <1.3.0-alpha", b"^0.0.0-alpha, <0.0.1-alpha",
             b"^0.2.3-alpha, <0.3.0-alpha", b"*")
    for requirement in gates:
        for core in ((0, 0, 0), (0, 0, 1), (0, 2, 3), (0, 3, 0),
                     (1, 0, 0), (1, 2, 3), (1, 2, 4), (1, 3, 0), (2, 0, 0)):
            for pre in PRES:
                yield "M", (requirement, version(core, pre))

    # Exercise exact resource edges without crossing either implementation's
    # documented common domain. Long numeric prereleases must not become u64.
    for length in (15, 16, 17, 31, 32, 33, 127, 128, 129,
                   VERSION_LIMIT - 1, VERSION_LIMIT):
        for atom in (b"9", b"a"):
            left = b"1.2.3-" + atom * (length - 6)
            right = left[:-1] + (b"8" if atom == b"9" else b"b")
            yield "P", (left,)
            yield "C", (left, right)
            yield "C", (right, left)
            for op in OPERATORS:
                yield "M", (op + left, right)
    for count in (1, COMPARATOR_LIMIT - 1, COMPARATOR_LIMIT):
        for position in (0, count - 1):
            parts = [b">=0.0.0"] * count
            parts[position] = b">=1.2.3-alpha"
            for candidate in (b"1.2.3-alpha", b"1.2.3-beta", b"1.2.4-alpha", b"1.2.4"):
                yield "M", (b", ".join(parts), candidate)
    for length in (REQUIREMENT_LIMIT - 1, REQUIREMENT_LIMIT):
        for requirement in (b"*", b"=1.2.3", b">=1.2.3-alpha, <2.0.0"):
            for source in (b" " * (length - len(requirement)) + requirement,
                           requirement + b" " * (length - len(requirement))):
                for candidate in (b"1.2.3", b"1.2.3-beta"):
                    yield "M", (source, candidate)

    invalid = (b"", b"1", b"1.2", b"01.2.3", b"1.02.3", b"1.2.03",
               b"1.2.3-01", b"1.2.3-", b"1.2.3+", b"1.2.3-a..b",
               b"1.2.3\0", b"1.2.3\n", b"1.2.3-\xff", b"v1.2.3")
    for source in invalid:
        yield "P", (source,)
        yield "C", (source, b"1.2.3")
        yield "C", (b"1.2.3", source)
        yield "M", (b"*", source)

    rng = random.Random(seed)
    for _ in range(4000):
        left, right = generated_version(rng), generated_version(rng)
        # Most comparisons share a core so the identifier comparator is reached.
        if rng.randrange(4):
            core = parse_version(left)[0]
            right = version(core, rng.choice(PRES), b"random.001")
        yield "P", (left,)
        yield "C", (left, right)
        yield "C", (right, left)
        target = rng.choice((left, right))
        requirement = rng.choice(OPERATORS) + rng.choice((b"", b" ", b"  ")) + target
        if rng.randrange(2):
            for _ in range(rng.randrange(1, 4)):
                requirement += rng.choice((b",", b", ", b" ,  "))
                requirement += rng.choice(OPERATORS) + generated_version(rng)
        requirement = rng.choice((b"", b" ")) + requirement + rng.choice((b"", b" "))
        yield "M", (requirement, rng.choice((left, right, generated_version(rng))))
        edited = mutate(rng, left)
        parsed = parse_version(edited)
        # A mutation may turn a near-maximum core into a valid Goose-only value.
        if parsed is None or max(parsed[0]) <= U64_MAX:
            yield "P", (edited,)


def protocol(operation, fields):
    return operation + "\t" + "\t".join(field.hex() for field in fields) + "\n"


def validate_domain(operation, fields):
    """Guard the generator itself against accidental grammar/domain drift."""
    versions = fields[1:] if operation == "M" else fields
    for source in versions:
        if len(source) > VERSION_LIMIT:
            raise AssertionError("generator exceeded version limit")
        parsed = parse_version(source)
        if parsed is not None and max(parsed[0]) > U64_MAX:
            raise AssertionError("generator exceeded Rust core range")
    if operation == "M":
        requirement = fields[0]
        parsed = parse_requirement(requirement)
        if parsed is None or len(requirement) > REQUIREMENT_LIMIT:
            raise AssertionError("generator emitted invalid requirement")
        if len(parsed) > COMPARATOR_LIMIT or b"\t" in requirement:
            raise AssertionError("generator exceeded common requirement grammar")
        if requirement.strip(b" ") != b"*":
            for part in requirement.split(b","):
                part = part.strip(b" ")
                if not part.startswith(OPERATORS):
                    raise AssertionError("generator emitted implicit requirement")
        if any(max(target[0]) > U64_MAX for _op, target in parsed):
            raise AssertionError("generator exceeded Rust requirement core range")


def run_batch(binaries, batch, first_index, seed):
    expected = [expected_response(operation, fields) for operation, fields in batch]
    payload = "".join(protocol(operation, fields) for operation, fields in batch)
    for name, binary in binaries:
        try:
            result = subprocess.run([binary], input=payload, capture_output=True,
                                    text=True, timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise SystemExit(f"seed={seed} {name} batch starts at case={first_index}: {error}") from error
        if result.returncode:
            raise SystemExit(f"seed={seed} {name} batch starts at case={first_index}: "
                             f"exit={result.returncode}; stderr={result.stderr[-4000:]!r}")
        actual = result.stdout.splitlines()
        if len(actual) != len(expected):
            raise SystemExit(f"seed={seed} {name} batch starts at case={first_index}: "
                             f"got {len(actual)} responses, expected {len(expected)}; "
                             f"stderr={result.stderr[-1000:]!r}")
        for offset, (wanted, got) in enumerate(zip(expected, actual)):
            if wanted != got:
                raise SystemExit(f"seed={seed} case={first_index + offset} {name}: "
                                 f"model expected={wanted!r}, actual={got!r}\n" +
                                 protocol(*batch[offset]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("goose_oracle")
    parser.add_argument("rust_oracle")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    binaries = (("Goose", args.goose_oracle), ("Rust semver 1.0.28", args.rust_oracle))
    batch, size, total, batches = [], 0, 0, 0
    counts = collections.Counter()
    for case in cases(args.seed):
        validate_domain(*case)
        case_size = len(protocol(*case))
        if case_size > BATCH_BYTES:
            raise AssertionError("single case exceeds batch byte limit")
        if batch and (len(batch) == BATCH_CASES or size + case_size > BATCH_BYTES):
            run_batch(binaries, batch, total, args.seed)
            total += len(batch)
            batches += 1
            batch, size = [], 0
        batch.append(case)
        size += case_size
        counts[case[0]] += 1
    if batch:
        run_batch(binaries, batch, total, args.seed)
        total += len(batch)
        batches += 1
    print(f"Goose and Rust semver 1.0.28 each matched model.py: {total} shared-domain cases "
          f"(P={counts['P']}, C={counts['C']}, M={counts['M']}) in {batches} bounded batches; "
          f"seed={args.seed}")


if __name__ == "__main__":
    main()
