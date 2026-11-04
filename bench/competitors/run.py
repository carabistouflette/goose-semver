#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pinned cross-library comparisons. Every engine validates identical fixture outcomes.

Native parsing owns results; Node may retain immutable strings. Default npm
range caches are preserved, with both small warm and2048-key miss workloads.
Goose uses test-only external opaque calls (no LTO); their overhead is included.
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
import corpus
import capabilities
import rust_build

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / '.build/competitors'

def run(command, **kw):
    return subprocess.run(list(map(str, command)), cwd=ROOT, check=True, timeout=180, **kw)

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build_goose(goose,cc,source,label):
    out=WORK/label;out.mkdir(parents=True,exist_ok=True)
    run([goose,source,'--standalone','--header',out/'competitor.h','-o',out/'competitor.c'])
    run([cc,'-O2','-c',out/'competitor.c','-o',out/'competitor.o'])
    run([cc,'-O2','-c','bench/competitors/host.c','-I'+str(out),'-o',out/'host.o'])
    binary=out/'bench'
    run([cc,out/'competitor.o',out/'host.o','-lm','-ldl','-lpthread','-o',binary])
    return binary

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--goose',type=Path,default=ROOT/'.toolchain/goose/build/goose')
    p.add_argument('--cc',default='gcc')
    p.add_argument('--iterations',type=int,default=100000)
    p.add_argument('--rounds',type=int,default=9)
    p.add_argument('--cpu',type=int)
    p.add_argument('--reference',help='Also build previous Goose core with the same harness')
    a=p.parse_args()
    if not 1<=a.iterations<=10000000 or not 3<=a.rounds<=51:p.error('iterations1..10000000 and rounds3..51 required')
    files=['semver.goose','GOOSE_REVISION','bench/competitors/corpus.py','bench/competitors/capabilities.py','bench/competitors/goose.goose','bench/competitors/host.c','bench/competitors/run.py','bench/competitors/rust_build.py','bench/competitors/rust/Cargo.toml','bench/competitors/rust/Cargo.lock','bench/competitors/rust/src/main.rs','bench/competitors/node/package.json','bench/competitors/node/package-lock.json','bench/competitors/node/bench.cjs']
    source_revision=git('rev-parse','HEAD');source_dirty=bool(git('status','--porcelain'))
    source_hashes={f:digest(ROOT/f) for f in files}
    reference=git('rev-parse',a.reference+'^{commit}') if a.reference else None
    cleared=[]
    for key in list(os.environ):
        if key in {'RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUSTC_BOOTSTRAP','RUSTC','CARGO_BUILD_RUSTFLAGS','NODE_OPTIONS','NODE_PATH','NODE_V8_COVERAGE'} or key.startswith('CARGO_PROFILE_'):
            cleared.append(key);del os.environ[key]
    WORK.mkdir(parents=True,exist_ok=True)
    allowed=os.sched_getaffinity(0);cpu=a.cpu if a.cpu is not None else min(allowed)
    if cpu not in allowed:p.error('CPU is outside allowed affinity')
    # Builds may use the normal CPU set. Timed children inherit one CPU below.
    goose=str(a.goose.resolve())
    goose_sha256=digest(Path(goose))
    engines={'goose':[str(build_goose(goose,a.cc,ROOT/'bench/competitors/goose.goose','goose'))]}
    if a.reference:
        source=WORK/'reference-source';(source/'bench/competitors').mkdir(parents=True,exist_ok=True)
        (source/'semver.goose').write_text(git('show',reference+':semver.goose')+'\n')
        (source/'bench/competitors/goose.goose').write_bytes((ROOT/'bench/competitors/goose.goose').read_bytes())
        engines['goose_reference']=[str(build_goose(goose,a.cc,source/'bench/competitors/goose.goose','reference'))]
    rust_binary=rust_build.build('goose-semver-rust-comparison',WORK/'rust')
    run(['npm','ci','--prefix','bench/competitors/node','--ignore-scripts','--no-audit','--no-fund'],stdout=subprocess.DEVNULL)
    engines['rust']=[str(rust_binary)]
    engines['node']=['node',str(ROOT/'bench/competitors/node/bench.cjs')]
    groups={}
    for row in corpus.cases():groups.setdefault(row[1],[]).append(row)
    path=WORK/'corpus.tsv'
    path.write_text(''.join('\t'.join(map(str,row))+'\n' for rows in groups.values() for row in rows))
    expected={}
    for name,rows in groups.items():
        cycles,tail=divmod(a.iterations,len(rows));expected[name]=cycles*sum(r[4] for r in rows)+sum(r[4] for r in rows[:tail])
    os.sched_setaffinity(0,{cpu})
    def measure(label):
        result=run(engines[label]+[str(path),str(a.iterations)],capture_output=True,text=True)
        found={}
        for line in result.stdout.splitlines():
            name,ns,count,checksum=line.split('\t')
            if name in found or int(count)!=a.iterations or int(checksum)!=expected[name] or int(ns)<=0:raise ValueError('bad result: '+line)
            found[name]=int(ns)
        if list(found)!=list(groups):raise ValueError('missing/reordered fixtures: '+label)
        return found
    compatibility={}
    for label in engines:
        family='goose' if label.startswith('goose') else label
        cap_path=WORK/('capabilities-'+label+'.tsv')
        cap_path.write_text(''.join('\t'.join(map(str,[op,name,left,right,answers[family]]))+'\n' for op,name,left,right,answers in capabilities.CASES))
        result=run(engines[label]+[str(cap_path),'1'],capture_output=True,text=True)
        compatibility[label]={line.split('\t')[0]:int(line.split('\t')[3]) for line in result.stdout.splitlines()}
        if compatibility[label]!={row[1]:row[4][family] for row in capabilities.CASES}:
            raise RuntimeError('Unexpected compatibility behavior: '+label)
    for label in engines:measure(label)
    raw=[];rng=random.Random(20261104)
    for i in range(a.rounds):
        order=list(engines);rng.shuffle(order);row={'order':order,'total_ns':{}}
        for label in order:row['total_ns'][label]=measure(label)
        raw.append(row);print(f'completed round {i+1}/{a.rounds}',flush=True)
    controls=run(engines['goose']+['--barriers',str(a.iterations)],capture_output=True,text=True).stdout.strip().splitlines()
    if git('rev-parse','HEAD')!=source_revision or {f:digest(ROOT/f) for f in files}!=source_hashes or digest(Path(goose))!=goose_sha256:
        raise RuntimeError('Source changed during build/measurement; discard timings')
    fixtures={}
    for name in groups:
        vals={}
        for label in engines:
            samples=[row['total_ns'][label][name]/a.iterations for row in raw]
            vals[label]={'median_ns':statistics.median(samples),'min_ns':min(samples),'max_ns':max(samples),'samples_ns':samples}
        fixtures[name]=vals
    cpuinfo=Path('/proc/cpuinfo').read_text()
    # The requested pin is distinct from the executable supplied by --goose.
    compiler_provenance={'requested_goose_revision':(ROOT/'GOOSE_REVISION').read_text().strip(),'goose_executable_sha256':goose_sha256,'revision_verified_by_driver':False}
    report={'source_revision':source_revision,'dirty':source_dirty,'reference_revision':reference,'cleared_environment_keys':cleared,'goose_barrier_control_rows':controls,'cpu':next(line.split(':',1)[1].strip() for line in cpuinfo.splitlines() if line.startswith('model name')),'affinity_cpu':cpu,'platform':platform.platform(),'iterations':a.iterations,'rounds':a.rounds,'post_measurement_assertions':'Source hashes and Git HEAD unchanged since before build','seed':20261104,'goose_revision':(ROOT/'GOOSE_REVISION').read_text().strip(),'cc':run([a.cc,'--version'],capture_output=True,text=True).stdout.splitlines()[0],'rustc':run(['rustc','-Vv'],capture_output=True,text=True).stdout.strip(),'node':run(['node','--version'],capture_output=True,text=True).stdout.strip(),'versions':{'rust_semver':'1.0.28','npm_semver':'7.8.6'},'flags':{'goose':a.cc+' -O2, separate barrier TU, no LTO','rust':'Cargo release opt3, thin LTO, codegen-units1'},'sources_sha256':source_hashes,'corpus_sha256':digest(path),'binary_sha256':{label:digest(Path(command[0])) for label,command in engines.items() if label!='node'},'compatibility_probes_not_ranked':compatibility,'node_warmup':'At least200000 operations per fixture within each measured process using the same operation-specific loop as timing, rounded to whole corpus passes','scope':'Shared strict ASCII subset, safe numeric core/prerelease values and version length<=256. Owned native results; Node immutable input retention/GC. Preparsed comparisons/matches. Default npm cache retained; warm and2048-key miss workloads. Goose opaque-call overhead included, not subtracted. No cold-start, allocation-count or universal-ranking claim.','fixtures':fixtures,'raw_rounds':raw}
    report['compiler_provenance']=compiler_provenance
    out=WORK/'results.json';out.write_text(json.dumps(report,indent=2)+'\n')
    for name,vals in fixtures.items():print(name+' '+ ' '.join(f'{label}={v["median_ns"]:.1f}ns' for label,v in vals.items()))
    print('Raw report: .build/competitors/results.json')

if __name__=='__main__':main()
