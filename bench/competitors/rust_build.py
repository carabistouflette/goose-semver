#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build one pinned native Rust adapter and select Cargo's actual executable."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def build(binary, target_dir):
    env = dict(os.environ)
    for key in list(env):
        if key in {'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER',
                   'RUSTC_WORKSPACE_WRAPPER', 'RUSTC_BOOTSTRAP', 'RUSTC',
                   'CARGO_BUILD_RUSTFLAGS'} or key.startswith('CARGO_PROFILE_'):
            del env[key]
    env.update(CARGO_TARGET_DIR=str(target_dir.resolve()), RUSTFLAGS='',
               RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER='')
    version = subprocess.check_output(['rustc', '-Vv'], env=env, text=True, timeout=30)
    host = next(line.removeprefix('host: ') for line in version.splitlines()
                if line.startswith('host: '))
    command = [
        'cargo', 'build', '--locked', '--release', '--target', host,
        '--bin', binary, '--message-format=json',
        '--config', 'build.rustflags=[]', '--config', 'profile.release.opt-level=3',
        '--config', 'profile.release.lto="thin"', '--config', 'profile.release.codegen-units=1',
        '--manifest-path', str(ROOT / 'bench/competitors/rust/Cargo.toml'),
    ]
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                            text=True, timeout=180, check=False)
    if result.returncode:
        print(result.stderr[-8000:], file=sys.stderr, end='')
        result.check_returncode()
    artifacts = [row['executable'] for line in result.stdout.splitlines()
                 if (row := json.loads(line)).get('reason') == 'compiler-artifact'
                 and row['target']['name'] == binary and row.get('executable')]
    if len(artifacts) != 1 or not Path(artifacts[0]).is_file():
        raise RuntimeError('Cargo did not identify exactly one adapter executable')
    return Path(artifacts[0]).resolve()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin', required=True)
    parser.add_argument('--target-dir', type=Path, default=ROOT / '.build/competitors/rust')
    args = parser.parse_args()
    print(build(args.bin, args.target_dir))
