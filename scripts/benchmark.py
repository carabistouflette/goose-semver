#!/usr/bin/env python3
"""Record warmed process samples without asserting machine-specific timings."""
import json
import os
import platform
import statistics
import subprocess
import sys
from pathlib import Path

binary = str(Path(sys.argv[1]).resolve())
iterations = int(sys.argv[2])
if not 1 <= iterations <= 10_000_000:
    raise SystemExit("iterations must be in 1..10000000")
cpu = None
if hasattr(os, "sched_getaffinity"):
    allowed = os.sched_getaffinity(0)
    cpu = int(os.environ.get("BENCH_CPU", min(allowed)))
    if cpu not in allowed:
        raise SystemExit("BENCH_CPU must be an allowed CPU")
    os.sched_setaffinity(0, {cpu})
fixtures = ["parse_short", "parse_long", "requirement_short", "requirement_many",
            "requirement_long", "compare_long_equal", "match_prerelease", "compare_short_equal", "compare_short_different",
            "compare_long_late_difference", "compare_long_early_difference",
            "compare_many_identifiers", "compare_large_core", "match_many_success",
            "match_many_early_failure", "reject_long", "parse_release", "parse_long_core",
            "parse_numeric_prerelease", "reject_zero_core", "compare_numeric_prerelease_early", "compare_numeric_prerelease_late",
            "match_release", "compare_numeric_identifiers", "requirement_long_many"]
samples = {name: [] for name in fixtures}
for sample in range(8):
    result = subprocess.run([binary, str(iterations)], capture_output=True,
                            text=True, check=True, timeout=120)
    rows = [line.split("\t") for line in result.stdout.splitlines()]
    assert [row[0] for row in rows] == fixtures + ["checksum"], result.stdout
    assert int(rows[-1][1]) == iterations * 12327, result.stdout
    for name, elapsed, count in rows[:-1]:
        assert int(count) == iterations and int(elapsed) >= 0
        if sample:
            samples[name].append(int(elapsed))

def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()

report = {
    "platform": platform.platform(), "machine": platform.machine(),
    "cpu": next((line.split(":", 1)[1].strip() for line in
                 Path("/proc/cpuinfo").read_text().splitlines()
                 if line.startswith("model name")), "unknown") if Path("/proc/cpuinfo").exists() else platform.processor(),
    "affinity_cpu": cpu, "iterations": iterations, "warmup_processes": 1,
    "compiler_revision": Path("GOOSE_REVISION").read_text().strip(),
    "cc": os.environ.get("BENCH_CC", "gcc"),
    "cc_version": subprocess.check_output([os.environ.get("BENCH_CC", "gcc"), "--version"], text=True).splitlines()[0],
    "flags": "goose build -O2", "source_revision": git("rev-parse", "HEAD"),
    "dirty": bool(git("status", "--porcelain")), "raw_ns": samples,
    "median_ns_per_operation": {k: statistics.median(v) / iterations for k, v in samples.items()},
    "scope": "Warm process medians; per-iteration parse storage is scoped; not cold latency, allocation counts, or a universal ranking.",
}
Path(".build/benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
for name, value in report["median_ns_per_operation"].items():
    print(f"{name}: {value:.1f} ns/op")
print("Raw samples and metadata: .build/benchmark.json")
