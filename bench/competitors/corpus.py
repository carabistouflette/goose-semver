#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the shared, semantically checked ASCII comparison subset."""
import sys
from pathlib import Path

def raw_cases():
    for i in range(64):
        yield 'parse','parse_release',f'1.{i % 8}.{i}','',1
        yield 'parse','parse_pre_short',f'1.2.{i}-rc.{i % 10}+b','',1
        yield 'parse','parse_pre_long',f'1.2.{i}-'+ 'a'*192 + f'.{i}+build','',1
        yield 'parse','parse_build_long',f'1.2.{i}+'+'z'*200,'',1
        yield 'parse','parse_invalid',['1.2.03','1.2.3-01','1.2.3?','1.2.3-a..b'][i%4],'',0
        yield 'compare','compare_release',f'1.2.{i}',f'1.2.{i+1}',-1
        yield 'compare','compare_onebyte_core',f'1.2.{i%9}',f'1.2.{i%9+1}',-1
        yield 'compare','compare_multidigit_core',f'{100+i}.{200+i}.{300+i}',f'{100+i}.{200+i}.{301+i}',-1
        yield 'compare','compare_multidigit_equal',f'{100+i}.{200+i}.{300+i}+left',f'{100+i}.{200+i}.{300+i}+right',0
        yield 'compare','compare_pre',f'1.2.{i}-alpha.1',f'1.2.{i}-beta.1',-1
        yield 'compare','compare_equal_build',f'1.2.{i}-rc.1+left',f'1.2.{i}-rc.1+right',0
        yield 'compare','compare_long_pre_early',f'1.2.{i}-'+'a'*192,f'1.2.{i}-'+'b'*192,-1
        yield 'compare','compare_long_pre_late',f'1.2.{i}-'+'a'*192,f'1.2.{i}-'+'a'*191+'b',-1
        yield 'requirement','requirement_exact_warm',f'=1.2.{i}','',1
        yield 'requirement','requirement_caret_warm',f'^1.2.{i}','',1
        yield 'requirement','requirement_and_warm',f'>=1.2.{i}, <2.0.0','',1
        yield 'match','match_release',f'^1.2.{i}',f'1.9.{i}',1
        yield 'match','match_prerelease',f'>=1.2.{i}-alpha, <2.0.0',f'1.2.{i}-beta',1
        yield 'match','match_reject',f'^1.2.{i}',f'2.0.{i}',0
        req=', '.join([f'>=1.0.{8*i+j}' for j in range(8)]+[f'<2.0.{8*i+j}' for j in range(8)])
        yield 'match','match_many',req,f'1.5.{i}',1
    # Exceeds npm's default1000-entry range cache with genuinely distinct keys.
    for i in range(2048):
        yield 'requirement','requirement_caret_miss',f'^1.2.{i}','',1

def cases():
    seen={}
    for operation,name,left,right,expected in raw_cases():
        at=seen.get(name,0);seen[name]=at+1
        if operation=='compare' and at%2:
            left,right=right,left;expected=-expected
        yield operation,name,left,right,expected

def main():
    groups={}
    for row in cases():
        groups.setdefault(row[1],[]).append(row)
    out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(''.join('\t'.join(map(str,row))+'\n' for rows in groups.values() for row in rows))
    print(f'{len(groups)} fixtures, {sum(map(len,groups.values()))} variants: {out}')
if __name__=='__main__':main()
