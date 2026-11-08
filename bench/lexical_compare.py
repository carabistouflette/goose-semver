#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Paired lexical-comparison driver: two binaries, one instrument, raw on disk.

Every observation is appended and flushed immediately, so an interrupted run
still leaves the samples it collected. Rounds alternate binary order to cancel
drift.

The run is only reported as valid when all of these hold:
  * both binaries produced the same, non-empty set of fixture keys;
  * each (fixture, binary) has exactly one observation per expected round;
  * each fixture's checksum is identical across every round and both binaries;
  * the SHA-256 of both binaries, the harness and this driver are unchanged
    between the start and the end of the run.

A binary that omits a fixture, emits nothing, or changes a result therefore
fails the run instead of passing quietly. A manifest with sources, compiler and
flags is written next to the raw file.

Usage:
  lexical_compare.py --old BIN --new BIN --rounds 21 --iterations 200000 \
      --out RAW.tsv [--cpu N] [--compiler TEXT] [--flags TEXT]
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

FIELDS = ("round", "order", "binary", "fixture", "digits", "position",
          "iterations", "total_ns", "ns_per_op", "checksum")
HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(HERE, "lexical.goose")
DRIVER = os.path.abspath(__file__)


def digest(path):
    with open(path, "rb") as source:
        return hashlib.sha256(source.read()).hexdigest()


def fingerprints(binaries):
    paths = list(binaries) + [HARNESS, DRIVER]
    return {os.path.basename(p): digest(p) for p in paths}


def run(binary, iterations, cpu):
    command = [binary, str(iterations)]
    if cpu is not None:
        command = ["taskset", "-c", str(cpu)] + command
    env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    if result.returncode:
        sys.stderr.write(result.stderr)
        raise SystemExit(f"{binary} failed with {result.returncode}")
    rows = []
    for line in result.stdout.strip().splitlines():
        fields = line.split("\t")
        if len(fields) != 6:
            raise SystemExit(f"unexpected line: {line!r}")
        fixture, digits, position, total_ns, iters, checksum = fields
        rows.append({
            "fixture": fixture, "digits": int(digits), "position": position,
            "iterations": int(iters), "total_ns": int(total_ns),
            "ns_per_op": int(total_ns) / int(iters), "checksum": int(checksum),
        })
    if not rows:
        raise SystemExit(f"{binary} produced no observations")
    return rows


def validate(path, rounds):
    """Return (fixtures, problems). Empty problems means the run is usable."""
    problems = []
    seen = {}
    checks = {}
    with open(path, encoding="utf-8") as source:
        header = source.readline().rstrip("\n").split("\t")
        if tuple(header) != FIELDS:
            problems.append(f"unexpected header: {header}")
        for line in source:
            fields = line.rstrip("\n").split("\t")
            if len(fields) != len(FIELDS):
                problems.append(f"short line: {line!r}")
                continue
            row = dict(zip(FIELDS, fields))
            key = (row["fixture"], row["digits"], row["position"])
            slot = (key, row["binary"], int(row["round"]))
            if slot in seen:
                problems.append(f"duplicate observation: {slot}")
            seen[slot] = True
            checks.setdefault(key, set()).add(row["checksum"])

    keys = {k for k in checks}
    if not keys:
        problems.append("no fixtures observed")
    for key in sorted(keys):
        if len(checks[key]) != 1:
            problems.append(f"checksum varies for {key}: {sorted(checks[key])}")
    for binary in ("old", "new"):
        for key in sorted(keys):
            for round_index in range(1, rounds + 1):
                if (key, binary, round_index) not in seen:
                    problems.append(f"missing {binary} {key} round {round_index}")
    for key in sorted(keys):
        old = {r for (k, b, r) in seen if k == key and b == "old"}
        new = {r for (k, b, r) in seen if k == key and b == "new"}
        if old != new:
            problems.append(f"round sets differ for {key}: {sorted(old)} vs {sorted(new)}")
    return keys, problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    parser.add_argument("--rounds", type=int, default=21)
    parser.add_argument("--iterations", type=int, default=200000)
    parser.add_argument("--out", required=True)
    parser.add_argument("--cpu", type=int, default=None)
    parser.add_argument("--compiler", default="")
    parser.add_argument("--flags", default="")
    args = parser.parse_args()

    before = fingerprints([args.old, args.new])
    manifest = {
        "rounds": args.rounds, "iterations": args.iterations, "cpu": args.cpu,
        "compiler": args.compiler, "flags": args.flags,
        "fingerprints_before": before, "raw": args.out,
    }
    manifest_path = os.path.splitext(args.out)[0] + ".manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as sink:
        json.dump(manifest, sink, indent=2)

    started = time.time()
    with open(args.out, "w", encoding="utf-8") as sink:
        sink.write("\t".join(FIELDS) + "\n")
        sink.flush()
        for round_index in range(1, args.rounds + 1):
            # Alternate which binary runs first so a monotonic drift in the
            # machine does not favour one side.
            order = ("old", "new") if round_index % 2 else ("new", "old")
            for position, label in enumerate(order):
                binary = args.old if label == "old" else args.new
                for row in run(binary, args.iterations, args.cpu):
                    row.update(round=round_index, order=position, binary=label)
                    sink.write("\t".join(str(row[f]) for f in FIELDS) + "\n")
                    sink.flush()
    elapsed = time.time() - started

    after = fingerprints([args.old, args.new])
    changed = {k: (before[k], after[k]) for k in before if before[k] != after[k]}
    keys, problems = validate(args.out, args.rounds)
    if changed:
        problems.append(f"fingerprints changed during the run: {changed}")

    manifest.update(fingerprints_after=after, elapsed_seconds=round(elapsed, 3),
                    fixtures=len(keys), problems=problems)
    with open(manifest_path, "w", encoding="utf-8") as sink:
        json.dump(manifest, sink, indent=2)

    print(json.dumps({"rounds": args.rounds, "iterations": args.iterations,
                      "cpu": args.cpu, "elapsed_seconds": round(elapsed, 3),
                      "fixtures": len(keys), "problems": len(problems),
                      "raw": args.out, "manifest": manifest_path}, indent=2))
    if problems:
        for problem in problems[:20]:
            print(f"  {problem}", file=sys.stderr)
        raise SystemExit("run invalid: see problems above")


if __name__ == "__main__":
    main()
