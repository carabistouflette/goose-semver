#!/usr/bin/env python3
"""Measure identical benchmark binaries in paired, counterbalanced process runs.

Build both with the same benchmark source, Goose revision, C compiler and flags.
The caller is responsible for associating binaries with source revisions; hashes
identify the measured executables. Timings describe this machine and corpus.
"""
import argparse
import hashlib
import json
import os
import platform
import random
import statistics
import subprocess
from pathlib import Path


SEED = 20261104
PAIRS = 9
EXPECTED_CHECKSUM = 4133


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def measure(binary, iterations, expected_fixtures):
    result = subprocess.run([str(binary), str(iterations)], capture_output=True,
                            text=True, check=True, timeout=120)
    rows = [line.split("\t") for line in result.stdout.splitlines()]
    if not rows or len(rows[-1]) != 2 or rows[-1][0] != "checksum":
        raise ValueError(f"{binary}: missing final checksum row")
    if int(rows[-1][1]) != iterations * EXPECTED_CHECKSUM:
        raise ValueError(f"{binary}: incorrect benchmark checksum: {rows[-1][1]}")
    samples = {}
    for row in rows[:-1]:
        if len(row) != 3:
            raise ValueError(f"{binary}: malformed timing row: {row!r}")
        name, elapsed, count = row
        if not name or name in samples or name == "checksum":
            raise ValueError(f"{binary}: invalid/duplicate fixture: {name!r}")
        ns = int(elapsed)
        if int(count) != iterations or ns <= 0:
            raise ValueError(f"{binary}: incorrect count or nonpositive timing: {row!r}")
        samples[name] = ns
    fixtures = list(samples)
    if not fixtures or (expected_fixtures is not None and fixtures != expected_fixtures):
        raise ValueError(f"{binary}: fixture list differs: {fixtures!r}")
    return samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("iterations", type=int, nargs="?", default=10000)
    parser.add_argument("--baseline-revision", default="unknown")
    args = parser.parse_args()
    if not 1 <= args.iterations <= 10_000_000:
        parser.error("iterations must be in 1..10000000")
    binaries = {"baseline": args.baseline.resolve(), "candidate": args.candidate.resolve()}
    root = Path(__file__).resolve().parent.parent
    pinned_cpu = None
    if hasattr(os, "sched_getaffinity"):
        allowed = os.sched_getaffinity(0)
        pinned_cpu = int(os.environ.get("BENCH_CPU", min(allowed)))
        if pinned_cpu not in allowed:
            parser.error("BENCH_CPU must be an allowed CPU")
        os.sched_setaffinity(0, {pinned_cpu})
    fixtures = None
    for binary in binaries.values():
        warm = measure(binary, args.iterations, fixtures)
        fixtures = list(warm)
    # Counterbalance nine pairs (five AB and four BA), then randomize their order.
    orders = [["baseline", "candidate"], ["candidate", "baseline"]] * (PAIRS // 2)
    orders += [["baseline", "candidate"]]
    random.Random(SEED).shuffle(orders)
    raw = []
    for order in orders:
        pair = {"order": order}
        for label in order:
            pair[label] = measure(binaries[label], args.iterations, fixtures)
        raw.append(pair)
    summary = {}
    for fixture in fixtures:
        baseline = [pair["baseline"][fixture] for pair in raw]
        candidate = [pair["candidate"][fixture] for pair in raw]
        ratios = [b / a for a, b in zip(baseline, candidate)]
        summary[fixture] = {
            "baseline_median_ns_per_op": statistics.median(baseline) / args.iterations,
            "candidate_median_ns_per_op": statistics.median(candidate) / args.iterations,
            "ratio_of_medians": statistics.median(candidate) / statistics.median(baseline),
            "paired_ratios": ratios,
            "paired_ratio_median": statistics.median(ratios),
            "paired_ratio_min": min(ratios),
            "paired_ratio_max": max(ratios),
        }
    compiler = os.environ.get("BENCH_CC", "gcc")
    cpuinfo = Path("/proc/cpuinfo")
    cpu = platform.processor()
    if cpuinfo.exists():
        cpu = next((line.split(":", 1)[1].strip() for line in cpuinfo.read_text().splitlines()
                    if line.startswith("model name")), cpu)
    report = {
        "seed": SEED, "pairs": PAIRS, "warmup_processes_per_binary": 1,
        "iterations": args.iterations, "checksum_per_iteration": EXPECTED_CHECKSUM,
        "platform": platform.platform(), "cpu": cpu, "affinity_cpu": pinned_cpu,
        "goose_revision": (root / "GOOSE_REVISION").read_text().strip(),
        "cc": compiler,
        "cc_version": subprocess.check_output([compiler, "--version"], text=True).splitlines()[0],
        "flags": "goose build -O2",
        "benchmark_source_sha256": hashlib.sha256((root / "bench/bench.goose").read_bytes()).hexdigest(),
        "candidate_core_sha256": hashlib.sha256((root / "semver.goose").read_bytes()).hexdigest(),
        "baseline_revision": args.baseline_revision,
        "candidate_revision": git(root, "rev-parse", "HEAD"),
        "candidate_dirty": bool(git(root, "status", "--porcelain")),
        "binaries": {label: {"artifact": binary.name,
                              "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}
                     for label, binary in binaries.items()},
        "raw_pairs_total_ns": raw, "fixtures": summary,
        "scope": "Paired warmed process timings on this machine and corpus; ratios are candidate/baseline. Source/compiler metadata describe caller-supplied build provenance and the current checkout, not verified binary provenance.",
    }
    output = root / ".build" / "comparison.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    for fixture, values in summary.items():
        print(f"{fixture}: {values['ratio_of_medians']:.3f}x candidate/baseline "
              f"(paired min/max {values['paired_ratio_min']:.3f}–{values['paired_ratio_max']:.3f})")
    print(f"Raw pairs and metadata: {output}")


if __name__ == "__main__":
    main()
