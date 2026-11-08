# Lexical comparison measurements

`lexical.goose` covers 89 fixture/length/position combinations across 17 lengths.
Not every position exists at every length: `last` requires two bytes, `middle`
three, `early1` five and `early2` seven. It exercises equal values and early/late
differences, including the maximum-length component.

`lexical_compare.py` retains every observation, its process-pair round and binary
order. Its adjacent manifest records source/binary hashes, flags, compiler and
CPU affinity. It rejects missing or duplicate observations, differing checksums
and identity changes. Preserve the raw TSV and manifest before interpreting it.

## Interpretation

Treat the process pair as the sampling unit. Inner loop iterations are correlated
observations, not independent samples. Alternating order reduces directional
drift but does not prove independent rounds or remove parity-correlated effects.
CPU affinity does not establish an idle host or constant frequency.

An A/A run compares identical binaries. A noise threshold defined as the maximum
over the same A/A runs necessarily reports no exceedance on those runs: that is
not independent validation. A run held out from threshold construction can still
exceed it. The campaign's old threshold-based win/loss count is a descriptive
screen, not a count of established improvements.

An exact paired sign test omits zero differences. Report its assumptions and
multiple-comparison family. Choosing among several variants on the reported
workloads introduces selection bias; a correction over fixtures alone does not
address that selection. Reanalysis of the existing campaign is exploratory and
does not substitute for a held-out confirmation.

Show equal, early-difference and late-difference results separately by length.
The narrower slices and earlier block entry benefit some fixtures and regress
others, including the long late-difference case. A majority of wins is not an
application-level performance guarantee. This branch has no accepted universal
performance or Rust-competitiveness claim.

Label estimates precisely: the ratio of the two marginal medians differs from
the median paired delta divided by the baseline median. Do not interchange the
two percentages or imply that the paired delta equals the difference of medians.

The existing released Rust/npm comparison remains evidence for its recorded
release source. It does not measure this changed lexical path.
