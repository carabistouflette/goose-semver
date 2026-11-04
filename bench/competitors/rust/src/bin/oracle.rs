// SPDX-License-Identifier: Apache-2.0
//! Test-only adapter for tests/oracle.goose's line/hex protocol.

use semver::{Version, VersionReq};
use std::cmp::Ordering;
use std::io::{self, BufRead, Read, Write};

const VERSION_LIMIT: usize = 4096;
const REQUIREMENT_LIMIT: usize = 16384;
const LINE_LIMIT: usize = 2 * (VERSION_LIMIT + REQUIREMENT_LIMIT) + 4;

fn decode(text: &[u8], limit: usize) -> Option<String> {
    if text.len() % 2 != 0 || text.len() / 2 > limit {
        return None;
    }
    fn digit(byte: u8) -> Option<u8> {
        match byte {
            b'0'..=b'9' => Some(byte - b'0'),
            b'a'..=b'f' => Some(byte - b'a' + 10),
            b'A'..=b'F' => Some(byte - b'A' + 10),
            _ => None,
        }
    }
    let bytes: Option<Vec<u8>> = text
        .chunks_exact(2)
        .map(|pair| Some(digit(pair[0])? * 16 + digit(pair[1])?))
        .collect();
    String::from_utf8(bytes?).ok()
}

fn version(text: &[u8]) -> Option<Version> {
    Version::parse(&decode(text, VERSION_LIMIT)?).ok()
}

fn response(line: &[u8]) -> &'static str {
    let mut fields = line.split(|byte| *byte == b'\t');
    match (fields.next(), fields.next(), fields.next(), fields.next()) {
        (Some(b"P"), Some(source), None, None) => {
            if version(source).is_some() {
                "1"
            } else {
                "0"
            }
        }
        (Some(b"C"), Some(left), Some(right), None) => match (version(left), version(right)) {
            (Some(left), Some(right)) => match left.cmp_precedence(&right) {
                Ordering::Less => "-1",
                Ordering::Equal => "0",
                Ordering::Greater => "1",
            },
            _ => "E",
        },
        (Some(b"M"), Some(requirement), Some(candidate), None) => {
            let requirement = decode(requirement, REQUIREMENT_LIMIT)
                .and_then(|text| VersionReq::parse(&text).ok());
            match (requirement, version(candidate)) {
                (Some(requirement), Some(candidate)) => {
                    if requirement.matches(&candidate) {
                        "1"
                    } else {
                        "0"
                    }
                }
                _ => "E",
            }
        }
        _ => "E",
    }
}

fn main() -> io::Result<()> {
    let stdin = io::stdin();
    let mut input = stdin.lock();
    let stdout = io::stdout();
    let mut output = io::BufWriter::new(stdout.lock());
    let mut line = Vec::new();
    loop {
        line.clear();
        // Bound allocation even if this test adapter receives a hostile line.
        let length = (&mut input)
            .take((LINE_LIMIT + 1) as u64)
            .read_until(b'\n', &mut line)?;
        if length == 0 {
            break;
        }
        if length > LINE_LIMIT {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "protocol line too long",
            ));
        }
        if line.last() == Some(&b'\n') {
            line.pop();
        }
        writeln!(output, "{}", response(&line))?;
    }
    output.flush()
}
