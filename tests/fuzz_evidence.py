#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evidence-state regressions; no compiler, network or campaign required."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fuzz_evidence import inspect, REPORTS


class Evidence(unittest.TestCase):
    def test_early_failure_has_no_upload_or_secondary_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'unrelated.env').write_text('outside allowlist')
            for outcome in ('failure', 'cancelled', 'skipped', ''):
                self.assertEqual(inspect(root, outcome), (False, []))

    def test_success_requires_each_report_and_preserves_partial_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in REPORTS:
                (root / name).write_text('report')
            self.assertEqual(inspect(root, 'success'), (True, []))
            for name in REPORTS:
                (root / name).write_text('')
                self.assertEqual(inspect(root, 'success'), (True, [name]))
                (root / name).unlink()
                self.assertEqual(inspect(root, 'success'), (True, [name]))
                (root / name).write_text('report')
            self.assertEqual(inspect(root, 'skipped'), (False, []))

    def test_zero_byte_failure_input_is_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'artifacts').mkdir()
            (root / 'artifacts/.empty-crash').write_bytes(b'')
            self.assertEqual(inspect(root, 'failure'), (True, []))


if __name__ == '__main__':
    unittest.main()
