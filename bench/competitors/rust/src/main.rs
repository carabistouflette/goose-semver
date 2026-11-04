// SPDX-License-Identifier: Apache-2.0
//! Pinned semver baseline for the shared TSV comparison corpus.
//!
//! Parsing constructs and drops owned results inside the timed loop. Comparing
//! and matching use values parsed before timing; precedence ignores build data.
//! Inputs and outputs cross black_box to discourage fixture-specific folding.
use semver::{Version, VersionReq};
use std::cmp::Ordering;
use std::error::Error;
use std::hint::black_box;
use std::time::Instant;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Operation {
    Parse,
    Compare,
    Requirement,
    Match,
}

impl Operation {
    fn parse(text: &str) -> Result<Self, String> {
        match text {
            "parse" => Ok(Self::Parse),
            "compare" => Ok(Self::Compare),
            "requirement" => Ok(Self::Requirement),
            "match" => Ok(Self::Match),
            _ => Err(format!("unknown operation: {text}")),
        }
    }
}

struct Case {
    left: String,
    right: String,
    expected: i64,
}

struct Fixture {
    operation: Operation,
    name: String,
    cases: Vec<Case>,
}

fn load_fixtures(path: &str) -> Result<Vec<Fixture>, Box<dyn Error>> {
    let source = std::fs::read_to_string(path)?;
    let mut fixtures: Vec<Fixture> = Vec::new();
    for (index, line) in source.lines().enumerate() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let fields: Vec<_> = line.split('\t').collect();
        if fields == ["operation", "name", "left", "right", "expected"] {
            continue;
        }
        if fields.len() != 5 || !line.is_ascii() {
            return Err(format!("line {}: expected five ASCII TSV fields", index + 1).into());
        }
        let operation = Operation::parse(fields[0])?;
        let name = fields[1];
        if name.is_empty()
            || !name
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-'))
        {
            return Err(format!("line {}: invalid fixture name", index + 1).into());
        }
        let expected: i64 = fields[4].parse()?;
        let valid_expected = match operation {
            Operation::Compare => (-1..=1).contains(&expected),
            _ => (0..=1).contains(&expected),
        };
        if !valid_expected {
            return Err(format!("line {}: invalid expected result", index + 1).into());
        }
        let case = Case {
            left: fields[2].to_owned(),
            right: fields[3].to_owned(),
            expected,
        };
        if let Some(fixture) = fixtures.iter_mut().find(|fixture| fixture.name == name) {
            if fixture.operation != operation {
                return Err(format!("fixture {name}: operation changes between variants").into());
            }
            fixture.cases.push(case);
        } else {
            fixtures.push(Fixture {
                operation,
                name: name.to_owned(),
                cases: vec![case],
            });
        }
    }
    if fixtures.is_empty() {
        return Err("empty fixture corpus".into());
    }
    Ok(fixtures)
}

fn sign(order: Ordering) -> i64 {
    match order {
        Ordering::Less => -1,
        Ordering::Equal => 0,
        Ordering::Greater => 1,
    }
}

fn validate(fixture: &Fixture) -> Result<(), Box<dyn Error>> {
    for (index, case) in fixture.cases.iter().enumerate() {
        let actual = match fixture.operation {
            Operation::Parse => i64::from(Version::parse(&case.left).is_ok()),
            Operation::Requirement => i64::from(VersionReq::parse(&case.left).is_ok()),
            Operation::Compare => {
                let left = Version::parse(&case.left)?;
                let right = Version::parse(&case.right)?;
                sign(left.cmp_precedence(&right))
            }
            Operation::Match => {
                let requirement = VersionReq::parse(&case.left)?;
                let version = Version::parse(&case.right)?;
                i64::from(requirement.matches(&version))
            }
        };
        if actual != case.expected {
            return Err(format!(
                "fixture {} variant {}: got {}, expected {}",
                fixture.name, index, actual, case.expected
            )
            .into());
        }
    }
    Ok(())
}

fn timed<F>(variants: usize, iterations: usize, mut operation: F) -> (u128, i64)
where
    F: FnMut(usize) -> i64,
{
    let mut index = 0;
    let mut checksum = 0;
    let start = Instant::now();
    for _ in 0..iterations {
        checksum += black_box(operation(index));
        index += 1;
        if index == variants {
            index = 0;
        }
    }
    (start.elapsed().as_nanos(), black_box(checksum))
}

fn measure(fixture: &Fixture, iterations: usize) -> Result<(u128, i64), Box<dyn Error>> {
    let cases = &fixture.cases;
    Ok(match fixture.operation {
        Operation::Parse => timed(cases.len(), iterations, |index| {
            let parsed = black_box(Version::parse(black_box(cases[index].left.as_str())));
            let accepted = i64::from(parsed.is_ok());
            drop(parsed);
            accepted
        }),
        Operation::Requirement => timed(cases.len(), iterations, |index| {
            let parsed = black_box(VersionReq::parse(black_box(cases[index].left.as_str())));
            let accepted = i64::from(parsed.is_ok());
            drop(parsed);
            accepted
        }),
        Operation::Compare => {
            let values = cases
                .iter()
                .map(|case| Ok((Version::parse(&case.left)?, Version::parse(&case.right)?)))
                .collect::<Result<Vec<_>, semver::Error>>()?;
            timed(values.len(), iterations, |index| {
                let (left, right) = &values[index];
                sign(black_box(left).cmp_precedence(black_box(right)))
            })
        }
        Operation::Match => {
            let values = cases
                .iter()
                .map(|case| Ok((VersionReq::parse(&case.left)?, Version::parse(&case.right)?)))
                .collect::<Result<Vec<_>, semver::Error>>()?;
            timed(values.len(), iterations, |index| {
                let (requirement, version) = &values[index];
                i64::from(black_box(requirement).matches(black_box(version)))
            })
        }
    })
}

fn main() -> Result<(), Box<dyn Error>> {
    let arguments: Vec<_> = std::env::args().collect();
    if arguments.len() != 3 {
        return Err("usage: goose-semver-rust-comparison FIXTURES.tsv ITERATIONS".into());
    }
    let iterations: usize = arguments[2].parse()?;
    if !(1..=1_000_000_000).contains(&iterations) {
        return Err("iterations must be in 1..1000000000".into());
    }
    let fixtures = load_fixtures(&arguments[1])?;
    for fixture in fixtures {
        validate(&fixture)?;
        let (elapsed, checksum) = measure(&fixture, iterations)?;
        let full_cycles = iterations / fixture.cases.len();
        let remainder = iterations % fixture.cases.len();
        let expected = fixture.cases.iter().map(|case| case.expected).sum::<i64>()
            * full_cycles as i64
            + fixture.cases[..remainder]
                .iter()
                .map(|case| case.expected)
                .sum::<i64>();
        if checksum != expected {
            return Err(format!(
                "fixture {}: checksum {}, expected {}",
                fixture.name, checksum, expected
            )
            .into());
        }
        println!("{}\t{elapsed}\t{iterations}\t{checksum}", fixture.name);
    }
    Ok(())
}
