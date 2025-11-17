### [17-11-25]

New traces batch targeting protocol version 0.7.1 has been released.

### [27-10-25]

New traces batch targeting protocol version 0.7.1 has been released.

### [23-09-25]

New batch of **highly controversial** traces and reports released, primarily
targeting transfer and designate hostcalls. All teams are strongly encouraged to
review these reports carefully and critically.

### [20-09-25]

Updated "Testing Setup" section in fuzz-reports/README.md with comprehensive
performance testing configuration details. The documentation now includes
detailed kernel parameters, CPU frequency settings, and Docker configuration
used for benchmarking.

### [16-09-25]

Fuzzing is **temporarily on hold** for targets that cannot correctly process the
`minifuzz` test session: tessera, fastroll, jamixir, pyjamaz, boka, jamzilla,
jamduna, jamzig.

New `minifuzz` tool available at `fuzz-proto/minifuzz/minifuzz.py`.
This lightweight fuzzing tool allows teams to replay pre-constructed message sequences
against their JAM implementations for testing and debugging purposes of their fuzzer
protocol implementation.

Updated `fuzz-proto/README.md` with a new "Preliminary Self-Testing" section.
Teams are now strongly encouraged to perform self-testing using the `minifuzz` tool
before submitting their target implementations for fuzzy testing.

### [14-09-25]

New batch of challenging traces and reports released.
These traces are tested only with targets implementing fuzzer protocol v1.

Trace 1756548916 has been retired due to invalidation by the `tiny` L parameter change.
Note: The maximum age of the lookup anchor (L in GP) is now set to 24 when using the
tiny configuration.


### [12-09-25]

Fuzzer Protocol v1 specification has been released.  
Refer to the [PR](https://github.com/davxy/jam-conformance/pull/47) for details on the changes.  

The examples folder has been updated with a sample session using the new message format.

### [09-09-25]

Interesting traces batch and reports

### [08-09-25]

1757063641 has been retired, see https://github.com/davxy/jam-conformance/discussions/66

New targets: tessera (0.7.0) and gossamer (0.6.7)

### [05-09-25]

Three new interesting traces have been added: 1757062927, 1757063641, and 1757092821.

### [03-09-25]

Trace 1756792661 has been retired due to an invalid steps sequence. The trace
contained a failing step caused by a malformed block where a successfull parent
block step was expected instead.

New traces batch for 0.7.0: https://github.com/davxy/jam-conformance/pull/52

Fuzzer protocol v1 proposal now open for review: https://github.com/davxy/jam-conformance/pull/47

The extension introduces fuzzer version and peer supported features during the session handshake. 
Also proposes an extension for target refinement of WorkPackages.

### [29-08-25]

Performance reports for protocol version 0.7.0 are now available for participating teams.
These reports provide benchmarking data across different JAM test vectors traces categories.

Performance reports can be found in `fuzz-reports/0.7.0/reports/[team]/perf/` directories.
These benchmarks help track implementation efficiency and identify optimization opportunities
as teams advance their JAM protocol implementations.

All performance results were generated on an AMD Ryzen Threadripper 3970X 32-Core (64) @ 4.55 GHz running Linux.

### [23-08-25]

The reports table has been updated to include results from the new Turbojam implementation.

Cleanup: All previously sorted traces have been removed from the reports table to reduce clutter.

This concludes the 0.6.7 fuzzing session regarding new trace generation. Progress tracking
continues for teams that still need to address issues with previously delivered 0.6.7 traces.

### [21-08-25]

Two new highly controversial reports: 1755796851 1755796995

### [20-08-25]

README updated with [collaboration](https://github.com/davxy/jam-conformance?tab=readme-ov-file#collaboration) section.

New GitHub Discussions page now available: `https://github.com/davxy/jam-conformance/discussions`
Use this space for inter-team technical conversations about JAM conformance testing.
This complements the existing issue tracker for bug reports and team specific progress.

New Matrix public room available for JAM conformance discussions: `#jam-conformance:matrix.org`
Join the public room for real-time collaboration, questions, and updates related to
JAM implementation conformance testing. This complements the existing GitHub issues
and provides a more immediate communication channel for the community.
Can be used to announce new interesting discussions happening on GH.

### [19-08-25]

New traces have been submitted for evaluation under the `traces/TESTING` folder.
The reports table has been updated with the results for these traces, and the
reports are stored in each team’s folder as usual.

Retired traces: 1755530535, 1755530728 1755530896 1755531000 1755531081
1755531179 1755531229 1755531322 1755531375 1755531419 1755531480

### [18-08-25]

Updated the disputed reports table in `fuzz-reports/README.md` with additional  
**highly controversial** trace reports. Please review them **carefully and critically**.  
As often emphasized, GP is the single source of truth, avoid blindly matching against
the fuzzer's expected results.

### [17-08-25]

Added comprehensive Disputes table to fuzz-reports/README.md showing test results
across all the fuzzed JAM implementations.
The table provides a clear overview of which reports cause failures or crashes for each team,
making it easier to track implementation conformance and identify problematic test cases.

Enhanced README.md with "Notes on Reports, Requests, and Contributions" section
to help set clear expectations for collaboration and support. This guidance aims
to make interactions more effective for everyone while keeping the project sustainable.

### [15-08-25]

Highly disputed report: 1755248982 - All teams affected.
Possible reason: https://github.com/davxy/jam-conformance/issues/16#issuecomment-3190838048

Removed problematic reports from `archive`: 1754582958 1754725568 1754754058 1755184602

From now on, I will not continuously ping teams in their issue when new reports
are available. It is the team's responsibility to check their folder for any
new reports. Please leave a comment in the issue when an outstending report is
sorted/analyzed, including the reason for the failure. This reason will be added
to the archived report to help other teams and to speed up troubleshooting of
potential regressions. I will double-check the fix before moving the report to
the archive.

### [14-08-25]

Archive of inter-team reports: [./fuzz-reports/archive]  
Teams are encouraged to review and execute one another's reports.

Target download script available at [./scripts/get_target.sh].
Target run script available at [./scripts/run_target.sh].
Target implementors are encouraged to submit a PR when repository locations
change or to enhance the script functionality.

Binary decoder script added at [./scripts/decode.py] for decoding JAM-encoded
binaries found in this repository. Requires https://github.com/davxy/jam-types-py.
