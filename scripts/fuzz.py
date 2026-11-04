#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build a bounded coverage-guided Clang/libFuzzer + ASan/UBSan campaign.

Checks metamorphic parsing, ordering and matching invariants, not an independent
complete semantic oracle. Input is tested raw as a version and requirement;
NUL-separated pairs/triples additionally exercise ordering and requirement matches.
Compiler output, writable corpus, logs and exact crash artifacts stay in .build/fuzz.
The native-host/assertion-bridge pattern is adapted from Apache-2.0 goose-toml.
"""
import argparse
import hashlib
import json
import platform
import re
import resource
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_INPUT_BYTES = 16384 + 1 + 4096


def fingerprint(goose, cc):
    """Identify the actual campaign inputs before building and after running."""
    files = ['semver.goose', 'GOOSE_REVISION', 'scripts/fuzz.py',
             'tests/fuzz.goose', 'tests/fuzz.c', 'tests/guarded.c']
    compiler = shutil.which(cc)
    if compiler is None:
        raise RuntimeError('C compiler not found: ' + cc)
    return {
        'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
        'sources_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files},
        'goose_executable_sha256': hashlib.sha256(Path(goose).read_bytes()).hexdigest(),
        'cc_executable_sha256': hashlib.sha256(Path(compiler).resolve().read_bytes()).hexdigest(),
    }


def seeds():
    """Focused corpus includes paths ordinary byte mutations rarely construct."""
    versions = [b"0.0.0", b"1.2.3", b"1.2.3+001", b"1.2.3-alpha", b"1.2.3-alpha.1",
                b"1.2.3-0", b"1.2.3-01a", b"1.2.3--", b"1.2.3-00", b"1.2.3-a.",
                b"1.2.3\0", b"v1.2.3", b"01.2.3", b"", b"\xff"]
    yield from versions
    for size in (15, 16, 17, 31, 32, 33, 63, 64, 65, 127, 4090, 4091):
        for prefix in (b"1.2.3-", b"12.3.45+"):
            for suffix in (b"", b"?", b"\xff", b".0", b"+001"):
                yield prefix + b"a" * size + suffix
        yield b"1.2.3-" + b"0" * size
        yield b"1.2.3-" + b"0" * size + b"a"
    for size in (4091, 4092, 4093):
        yield b"9" * size + b".0.0"
    requirements = [b"*", b" \t*\t ", b"^0.0.0", b"^0.0.0-alpha", b"~0.0.0-alpha",
                    b">=1.2.3-alpha, <2.0.0", b"^1.2.3", b"~1.2.3", b"1.2.3,",
                    b"=1.2.3", b"^0.2.3", b"^0.0.3", b"<2.0.0-alpha", b"1.2.3,*"]
    yield from requirements
    for count in (31, 32, 33):
        yield b",".join([b">=0.0.0"] * count)
    # Four long comparator targets fit just below the whole-requirement limit.
    long_target = b"1.2.3-" + b"a" * 4086
    for count in (3, 4):
        yield b",".join([b">=" + long_target] * count)
    yield b",".join([b">=" + long_target] * 4) + b" " * 5
    for size in (16383, 16384, 16385):
        yield b"*" + b" " * (size - 1)
    pair_versions = [b"1.2.3-alpha", b"1.2.3-alpha.1", b"1.2.3-beta", b"1.2.3", b"2.0.0"]
    for a in pair_versions:
        for b in pair_versions:
            yield a + b"\0" + b
    for requirement in requirements:
        for candidate in pair_versions + [b"0.0.0-alpha", b"0.0.0", b"0.0.1"]:
            yield requirement + b"\0" + candidate
    # The host envelope must fit a maximal requirement plus maximal candidate.
    maximal_candidate = b"1.2.3+" + b"z" * 4090
    base_requirement = b">=1.2.3, <2.0.0"
    yield base_requirement.ljust(16384, b" ") + b"\0" + maximal_candidate
    wide_target = b"9" * 480 + b".0.0"
    wide_requirement = b",".join([b">=" + wide_target] * 32)
    wide_candidate = wide_target + b"+" + b"z" * (4095 - len(wide_target))
    yield wide_requirement.ljust(16384, b" ") + b"\0" + wide_candidate
    yield b"1.2.3-alpha\0" + b"1.2.3-beta\0" + b"1.2.3"
    yield b"1.2.3-9\0" + b"1.2.3-10\0" + b"1.2.3-a"
    huge = b"9" * 4092 + b".0.0"
    yield huge + b"\0" + huge + b"\0" + huge
    yield b"1.2.3-" + b"a." * 1000 + b"a"
    yield b"1.2.3-" + b"9" * 4090 + b"\0" + b"1.2.3-a"


def run(command, *, log=None, timeout=120):
    return subprocess.run(command, cwd=ROOT, check=True, timeout=timeout,
                          stdout=log, stderr=subprocess.STDOUT if log else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goose", type=Path, default=ROOT / ".toolchain/goose/build/goose")
    parser.add_argument("--cc", default="clang")
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--runs", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=20261104)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600 or not 1 <= args.runs <= 100000000 or not 1 <= args.seed < 2**32:
        parser.error("seconds must be 1..3600, runs 1..100000000, seed 1..4294967295")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    work = ROOT / ".build/fuzz"
    summary_path = work / "summary.json"
    # Fresh logs must never be mistaken for a previous successful campaign.
    summary_path.unlink(missing_ok=True)
    all_seeds = sorted(set(seeds()))
    seed_manifest = hashlib.sha256("".join(hashlib.sha256(data).hexdigest() for data in all_seeds).encode()).hexdigest()
    initial = work / ("seeds-" + seed_manifest[:16])
    corpus = work / "corpus"
    artifacts = work / "artifacts"
    for directory in (initial, corpus, artifacts):
        directory.mkdir(parents=True, exist_ok=True)
    seed_count = 0
    for data in all_seeds:
        if len(data) > MAX_INPUT_BYTES:
            raise RuntimeError("initial seed exceeds the campaign input bound")
        (initial / hashlib.sha256(data).hexdigest()).write_bytes(data)
        seed_count += 1
    dictionary = work / "semver.dict"
    dictionary.write_text('\n'.join(json.dumps(value) for value in
                          ["0.0.0", "1.2.3", "alpha", "beta", "rc.1", "+001", "^", "~", ">=", "<=", ", ", "*"]) + '\n"\\x00"\n')
    goose = str(args.goose.resolve())
    provenance = fingerprint(goose, args.cc)
    run([goose, "tests/fuzz.goose", "--standalone", "--debug", "--no-bce",
         "--header", str(work / "semver-fuzz.h"), "-o", str(work / "semver-fuzz.c")])
    instrument = ["-O1", "-g", "-fsanitize=fuzzer-no-link,address,undefined",
                  "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"]
    run([args.cc, *instrument, "-D_Exit=goose_fuzz_exit", "-c",
         str(work / "semver-fuzz.c"), "-o", str(work / "semver-fuzz.o")])
    guarded = [args.cc, "-O1", "-g", "-fsanitize=address,undefined",
               "-fno-sanitize-recover=all", "-fno-omit-frame-pointer",
               "-fsanitize=fuzzer-no-link", str(work / "semver-fuzz.o"),
               "tests/guarded.c", "-I" + str(work), "-lm", "-ldl", "-lpthread",
               "-o", str(work / "guarded")]
    run(guarded)
    run([str(work / "guarded")], timeout=60)
    link = [args.cc, "-O1", "-g", "-fsanitize=fuzzer,address,undefined",
            "-fno-sanitize-recover=all", "-fno-omit-frame-pointer",
            str(work / "semver-fuzz.o"), "tests/fuzz.c", "-I" + str(work),
            "-lm", "-ldl", "-lpthread"]
    run([*link, "-o", str(work / "semver-fuzzer")])
    run([*link, "-DGOOSE_FUZZ_SELF_TEST=1", "-o", str(work / "self-test")])
    # The self-test must exercise Goose's own failed assertion path. A sanitizer
    # smoke test alone would not prove _Exit becomes a saved libFuzzer artifact.
    probe = work / "self-test-seeds"
    probe.mkdir(exist_ok=True)
    expected = b"libFuzzer Goose assertion bridge probe"
    (probe / "input").write_bytes(expected)
    crash = work / "self-test-crash"
    crash.unlink(missing_ok=True)
    with (work / "self-test.log").open("wb") as log:
        result = subprocess.run([str(work / "self-test"), str(probe), "-runs=10", "-seed=1",
                                 "-exact_artifact_path=" + str(crash)], cwd=ROOT,
                                stdout=log, stderr=subprocess.STDOUT, timeout=30)
    probe_log = (work / "self-test.log").read_text(errors="replace")
    if result.returncode == 0 or not crash.is_file() or crash.read_bytes() != expected or "assert failed" not in probe_log:
        raise RuntimeError("Goose assertion-artifact self-test failed; inspect .build/fuzz/self-test.log")
    print("Verified Goose assertions preserve exact triggering input", flush=True)
    command = [str(work / "semver-fuzzer"), str(corpus), str(initial),
               "-dict=" + str(dictionary), "-max_len=" + str(MAX_INPUT_BYTES),
               "-max_total_time=" + str(args.seconds), "-runs=" + str(args.runs),
               "-seed=" + str(args.seed), "-timeout=5", "-rss_limit_mb=1024",
               "-artifact_prefix=" + str(artifacts) + "/"]
    print(f"Fuzzing with {seed_count} initial seeds; log: .build/fuzz/run.log", flush=True)
    with (work / "run.log").open("wb") as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                timeout=args.seconds + 120)
    log_text = (work / "run.log").read_text(errors="replace")
    if result.returncode:
        print(log_text[-12000:])
        raise SystemExit(result.returncode if result.returncode > 0 else 1)
    finished = re.findall(r"^Done (\d+) runs in (\d+) second\(s\)", log_text, re.MULTILINE)
    if not finished or int(finished[-1][0]) < 1:
        raise RuntimeError("libFuzzer returned without a valid execution summary; inspect .build/fuzz/run.log")
    done = [line for line in log_text.splitlines() if "DONE" in line]
    if fingerprint(goose, args.cc) != provenance:
        raise RuntimeError('Source or compiler changed during build/fuzzing; discard this campaign evidence')
    report = {"goose_revision": (ROOT / "GOOSE_REVISION").read_text().strip(),
              **provenance,
              "source_sha256": provenance['sources_sha256']['semver.goose'],
              "compiler_revision_verified_by_driver": False,
              "cc": args.cc,
              "cc_version": subprocess.check_output([args.cc, "--version"], text=True).splitlines()[0],
              "platform": platform.platform(), "seed": args.seed, "requested_runs": args.runs,
              "max_seconds": args.seconds, "max_input_bytes": MAX_INPUT_BYTES,
              "initial_seeds": seed_count, "seed_manifest_sha256": seed_manifest, "completed_runs": int(finished[-1][0]),
              "elapsed_seconds": int(finished[-1][1]), "coverage_summary": done[-1] if done else "",
              "scope": "Coverage-guided mutations and metamorphic invariants; not a complete independent semantic oracle. Reused writable corpus changes mutation sequences."}
    summary_path.write_text(json.dumps(report, indent=2) + "\n")
    for line in done:
        print(line)
    print(finished[-1][0] + " runs completed; summary: .build/fuzz/summary.json")


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, RuntimeError) as error:
        raise SystemExit(str(error)) from error
