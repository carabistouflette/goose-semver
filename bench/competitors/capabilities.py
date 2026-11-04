# SPDX-License-Identifier: Apache-2.0
"""Non-ranked compatibility probes; expected answers deliberately differ."""
CASES = [
    ('parse','v_prefix','v1.2.3','',{'goose':0,'rust':0,'node':1}),
    ('parse','surrounding_space',' 1.2.3 ','',{'goose':0,'rust':0,'node':1}),
    ('compare','large_numeric_prerelease','1.2.3-9007199254740992','1.2.3-9007199254740993',{'goose':-1,'rust':-1,'node':0}),
    ('parse','beyond_u64_core','18446744073709551616.0.0','',{'goose':1,'rust':0,'node':0}),
    ('parse','version_257_bytes','1.2.3-'+'a'*251,'',{'goose':1,'rust':1,'node':0}),
]
