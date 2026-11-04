# Git tags and strict versions

`semver::parse` accepts a version, not an arbitrary Git ref. It rejects `v7.8.6`,
`main`, `refs/tags/v7.8.6`, whitespace and partial versions. Applications choose
how to obtain candidate version text; the library never strips a prefix.

The [tag-candidate example](../examples/tag_candidates.goose) demonstrates one
explicit policy: for tag **names**, remove at most one lowercase ASCII `v`, then
use strict parsing. It accepts `v7.8.6` and `1.0.28`; `vv7.8.6`, `V7.8.6`, `main`
and release labels remain invalid. Syntax cannot identify Git ref kinds: a branch
named `1.2.3` looks like a version too. Callers must enumerate tag names explicitly
and never send arbitrary branch refs through this policy. It does not rewrite arbitrary refs,
fetch repositories or resolve dependencies. Keep an original ref and its pinned
commit separate from parsed version metadata.

Only fields explicitly defined as version requirements should use
`parse_requirement`. A Git dependency's `rev = "main"` or exact ref must retain
its ordinary Git meaning. Adding this library does not introduce constraint
solving, reinterpret exact Git/path dependencies or make a registry available.
Build metadata does not break precedence ties; consumers need an explicit policy
for multiple tags with equal precedence. Prereleases require same-core admission
even if they otherwise satisfy the numeric bounds.

## Offline real-tag fixtures

[tag-fixtures.json](../tests/tag-fixtures.json) records five upstream tag names,
their Git ref objects and peeled commits as observed on 2026-11-04. Sources:
[npm/node-semver tags](https://github.com/npm/node-semver/tags) and
[dtolnay/semver tags](https://github.com/dtolnay/semver/tags). Annotated tags and
lightweight tags are both represented. The tag names are examples, not trusted
dependency identities; refs can move after observation.

The tests verify strict rejection of prefixed raw text, explicit normalization,
ordering, build equivalence and full-version constraints using offline snapshots.
Synthetic malformed names and range boundaries are labeled separately from the
real tags. `make property` runs these fixtures against optimized and debug
oracles; `make test` runs the Goose consumer example. Honk's local Git repository
fixtures and normalization policy remain owned by Honk.

## Release and dependency pins

Use a reviewed full commit for reproducible imports, even when discovering it
through the `v0.1.0` release. Published release tags will not be moved; corrections
use another version. Before 1.0 the API is experimental: breaking contract changes
require an announced minor-version release, while patches preserve the documented
contract. This does not promise Cargo/npm requirement compatibility.
