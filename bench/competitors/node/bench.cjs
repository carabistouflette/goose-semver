// SPDX-License-Identifier: Apache-2.0
'use strict'

// semver 7.8.6, using normal public APIs. Node's immutable strings may be retained
// by parsed objects rather than copied. SemVer.compare ignores build metadata.
// Range.test receives a SemVer instance, so it does not parse the candidate.
// Range's private 1000-entry parsing LRU remains enabled: small repeated range
// corpora are warm-cache workloads. No upstream internals are patched.
// Every fixture warms up in THIS process before timing, to exercise V8 JIT code.
// Whole corpus passes keep the timed start aligned with the first input.
const fs = require('node:fs')
const assert = require('node:assert/strict')
const semver = require('semver')

const WARMUP_ITERATIONS = 50_000
const KNOWN_OPERATIONS = new Set(['parse', 'compare', 'requirement', 'match'])
const args = process.argv.slice(2)
if (args.length !== 2 || !/^[1-9][0-9]*$/.test(args[1])) {
  throw new Error('usage: node bench.cjs corpus.tsv iterations')
}
const iterations = Number(args[1])
if (!Number.isSafeInteger(iterations) || iterations > 100_000_000) {
  throw new Error('iterations must be in 1..100000000')
}

const fixtures = new Map()
const lines = fs.readFileSync(args[0], 'utf8').split(/\r?\n/)
for (const [index, line] of lines.entries()) {
  if (line === '' || line.startsWith('#')) continue
  const fields = line.split('\t')
  if (fields[0] === 'operation' && fields[1] === 'name') continue
  if (fields.length !== 5 || !/^[\x20-\x7e\t]+$/.test(line)) {
    throw new Error(`invalid five-field ASCII TSV row ${index + 1}`)
  }
  const [operation, name, left, right, expectedText] = fields
  if (!KNOWN_OPERATIONS.has(operation) || !/^[A-Za-z0-9_-]+$/.test(name) ||
      !/^-?[01]$/.test(expectedText)) {
    throw new Error(`invalid operation, name or expected value on row ${index + 1}`)
  }
  const expected = Number(expectedText)
  if (operation === 'match' && expected < 0) {
    throw new Error(`match expected value must be 0 or 1: row ${index + 1}`)
  }
  if (fixtures.has(name) && fixtures.get(name).operation !== operation) {
    throw new Error(`mixed operations in fixture ${name}`)
  }
  if (!fixtures.has(name)) fixtures.set(name, { operation, rows: [] })
  // node-semver uses spaces for comparator conjunctions. This grammar adapter
  // runs before either preparation or timing; all engines consume the same
  // meaning, rather than charging Node for another engine's comma spelling.
  const normalized = (operation === 'requirement' || operation === 'match')
    ? left.replaceAll(',', ' ')
    : left
  const row = { left: normalized, right, expected }
  if (operation === 'compare') {
    row.a = new semver.SemVer(left)
    row.b = new semver.SemVer(right)
  } else if (operation === 'match') {
    row.range = new semver.Range(normalized)
    row.version = new semver.SemVer(right)
  }
  fixtures.get(name).rows.push(row)
}
if (fixtures.size === 0) throw new Error('corpus contains no fixtures')

// Parsed objects escape through an observable store, preventing the benchmark
// from reducing successful constructor calls to a constant success counter.
// The store also means object allocation/GC belongs in the Node parse workload;
// compare/match perform only their library operations and checksum accumulation.
globalThis.__gooseSemverBenchmarkSink = null

function operationFor (operation) {
  switch (operation) {
    case 'parse':
      return row => {
        const value = semver.parse(row.left)
        globalThis.__gooseSemverBenchmarkSink = value
        return value === null ? 0 : 1
      }
    case 'requirement':
      return row => {
        const value = new semver.Range(row.left)
        globalThis.__gooseSemverBenchmarkSink = value
        return value.set.length > 0 ? 1 : 0
      }
    case 'compare':
      return row => Math.sign(row.a.compare(row.b))
    case 'match':
      return row => row.range.test(row.version) ? 1 : 0
    default:
      throw new Error('unreachable operation')
  }
}

for (const [name, fixture] of fixtures) {
  const { operation, rows } = fixture
  const step = operationFor(operation)
  for (const row of rows) {
    assert.equal(step(row), row.expected, `semantic disagreement in ${name}`)
  }
  let warmChecksum = 0
  const warmupIterations = Math.ceil(WARMUP_ITERATIONS / rows.length) * rows.length
  for (let i = 0; i < warmupIterations; i++) {
    warmChecksum += step(rows[i % rows.length])
  }
  assert(Number.isSafeInteger(warmChecksum))
  let checksum = 0
  const start = process.hrtime.bigint()
  for (let i = 0; i < iterations; i++) {
    checksum += step(rows[i % rows.length])
  }
  const elapsed = process.hrtime.bigint() - start
  const cycleExpected = rows.reduce((sum, row) => sum + row.expected, 0)
  let expected = Math.floor(iterations / rows.length) * cycleExpected
  for (let i = 0; i < iterations % rows.length; i++) expected += rows[i].expected
  assert.equal(checksum, expected, `timed checksum disagreement in ${name}`)
  if (operation === 'parse' || operation === 'requirement') {
    const lastInput = rows[(iterations - 1) % rows.length].left
    const expectedRaw = operation === 'requirement' ? lastInput.trim().replace(/\s+/g, ' ') : lastInput
    if (rows[(iterations - 1) % rows.length].expected === 0) assert.equal(globalThis.__gooseSemverBenchmarkSink, null)
    else assert.equal(globalThis.__gooseSemverBenchmarkSink.raw, expectedRaw)
  }
  process.stdout.write(`${name}\t${elapsed}\t${iterations}\t${checksum}\n`)
}
