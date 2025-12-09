# JAM Conformance Testing Material

This repository serves as a scratchpad for JAM protocol conformance testing
materials, including:

- Fuzzer reports 
- PVM execution traces
- Protocol conformance discussions and issues

While this may assist implementations in achieving protocol compliance,**THIS IS NOT THE OFFICIAL AUDITING PROCESS**

## Latest Updates

For the latest updates and announcements, see [NEWS.md](NEWS.md) which contains
information about new tools, discoveries, and improvements to the conformance
testing infrastructure.

## Repository Content

- [fuzz-proto](./fuzz-proto) - Fuzzer protocol specification
- [fuzz-reports](./fuzz-reports) - Fuzzer reports
- [fuzz-perf](./fuzz-perf) - Fuzzer performance reports
- [pvm-traces](./pvm-traces) - PVM execution traces scratchpad
- [crypto](./crypto) - Crypto primitives vectors
- [scripts](./scripts) - Conformance testing scripts and tools

## Running Conformance Tests

The [scripts](./scripts) directory contains the tooling needed to run conformance
tests against JAM implementations. See [scripts/README.md](./scripts/README.md)
for detailed documentation on:

- Setting up the fuzzing environment and prerequisites
- Using `target.py` to manage JAM implementation targets
- Running `fuzz-workflow.py` to execute fuzzing sessions
- Creating test vectors in exploratory/local mode
- Running test batteries against multiple implementations in trace mode
- Understanding generated artifacts and reports

## Collaboration

### Communication Channels

- **Matrix Room**: [#jam-conformance:matrix.org](https://matrix.to/#/#jam-conformance:matrix.org) - Real-time chat for quick questions, announcements, and coordination
- **GitHub Discussions**: [https://github.com/davxy/jam-conformance/discussions](https://github.com/davxy/jam-conformance/discussions) - Structured inter-team conversations about test vectors, fuzzer reports and conformance related things.
- **GitHub Issues**: For specific bug reports and team-specific technical issues

### Best Practices

- Use the Matrix room for immediate questions and to announce new discussions
- Start GitHub Discussions for broader technical conversations that benefit from structured threading
- File GitHub Issues for specific bugs, discrepancies, or actionable items
- Cross-reference between channels when discussions span multiple platforms

## Related Resources

- [Official JAM Test Vectors](https://github.com/w3f/jamtestvectors) - Officially released test vectors
- [JAM Test Vectors (Release Candidate)](https://github.com/davxy/jam-test-vectors) - Development test vectors

## Purpose

This repository facilitates JAM protocol implementation testing and
validation by providing a centralized location for test artifacts, enabling
cross-implementation comparison and protocol conformance verification.

## Notes on Reports, Requests, and Contributions

When a discrepancy shows up in a third-party implementation, the expectation is
a report that includes everything needed to reproduce the issue.

Time is limited, so not every ping or request can get an immediate follow-up.
In practice, attention tends to go to:
- issues that look genuinely interesting or relevant;
- disputes popping up across multiple implementations (which may hint at a fuzzer bug);
- teams that clearly did their analysis and can explain why their implementation
  diverges instead of immediately asking for help.

**Do not expect synchronous feedback.** . Always check the
[table](./fuzz-reports/README.md) first to see who is in a good position to
help. This repo is also meant as a vector for cross-team discussion and in some
cases other teams can provide better support (e.g. our PVM traces are not the
best to be analyzed).

The same logic applies to **feature requests or pings for new reports**:
the louder and more insistent, the less likely they will get attention
where it matters.

Clear, motivated ideas with proper context, though, are always welcome;
especially when tied to fuzzing. At that point, just open a PR or an issue.

This is not about laziness. Hand-holding and 24H support is simply not my job,
and time is finite. A bit of filtering is what keeps things sustainable for
everyone.

That said, **conversations that end up clarifying ambiguities or revealing bugs
in the fuzzer implementation are welcome and encouraged** :-)

