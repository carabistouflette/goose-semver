#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Offline real-tag snapshots, strict parsing, and explicit consumer policy."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary')
    args = parser.parse_args()
    fixtures = json.loads(Path(__file__).with_name('tag-fixtures.json').read_text())
    cases = []

    def add(operation, fields, expected):
        line = operation + '\t' + '\t'.join(value.encode().hex() for value in fields)
        cases.append((line, str(expected)))

    for item in fixtures['tags']:
        tag = item['tag']
        # This is consumer policy, never a relaxation of semver::parse.
        normalized = tag[1:] if tag.startswith('v') else tag
        assert normalized == item['version']
        add('P', [tag], 0 if tag.startswith('v') else 1)
        add('P', [normalized], 1)
    for tag in fixtures['rejected_tag_candidates']:
        add('P', [tag[1:] if tag.startswith('v') else tag], 0)
    for left, right, order in fixtures['comparisons']:
        add('C', [left, right], order)
        add('C', [right, left], -order)
    for requirement, version, matched in fixtures['requirements']:
        add('M', [requirement, version], int(matched))
    result = subprocess.run([args.binary], input=''.join(line + '\n' for line, _ in cases),
                            text=True, capture_output=True, timeout=30, check=True)
    actual = result.stdout.splitlines()
    if actual != [expected for _, expected in cases]:
        for index, (line, expected) in enumerate(cases):
            got = actual[index] if index < len(actual) else '<missing>'
            if got != expected:
                raise SystemExit(f'case {index}: expected {expected}, got {got!r}\n{line}')
        raise SystemExit('extra oracle responses')
    print(f'real-tag snapshots and explicit consumer policy: {len(cases)} cases passed')


if __name__ == '__main__':
    main()
