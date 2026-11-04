#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Classify narrowly allowlisted fuzz evidence without masking early failures."""
import argparse
import os
from pathlib import Path

REPORTS = ('summary.json', 'run.log', 'self-test.log')
DIRECTORIES = ('artifacts', 'corpus')


def inspect(work, outcome):
    if outcome not in ('success', 'failure', 'cancelled'):
        return False, []
    available = any((work / name).is_file() for name in REPORTS)
    available = available or any(path.is_file() for name in DIRECTORIES
                                 for path in (work / name).rglob('*'))
    missing = [name for name in REPORTS
               if not (work / name).is_file() or (work / name).stat().st_size == 0]
    return available, missing if outcome == 'success' else []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outcome', choices=('', 'success', 'failure', 'cancelled', 'skipped'), required=True)
    args = parser.parse_args()
    work = Path(__file__).resolve().parents[1] / '.build/fuzz'
    available, missing = inspect(work, args.outcome)
    value = f'upload_required={str(available).lower()}\n'
    if 'GITHUB_OUTPUT' in os.environ:
        # Emit before failure so existing partial evidence can still upload.
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write(value)
    print(value, end='')
    if missing:
        raise SystemExit('Successful fuzz campaign is missing nonempty reports: ' + ', '.join(missing))
    if not available:
        print('No allowlisted fuzz evidence produced; see job logs for skipped/setup/compiler failures.')


if __name__ == '__main__':
    main()
