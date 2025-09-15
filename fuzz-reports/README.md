# Fuzzer Reports

## Organization

- Reports are stored **per team** in the `./<jam-version>/reports` subfolder.  
- Traces are stored in the `./<jam-version>/traces` subfolder.  
- Each report is named after the **trace involved**.
- **Disputed traces** are preserved permanently, even after the dispute has been resolved for all teams.  

## Enrolled Teams

### V0.7.0 (fuzz proto v1)

* jamduna (go)
* jampy (python)
* javajam (java)
* spacejam (rust)
* tsjam (ts)
* vinwolf (rust)

* jamzilla (go)     (proto fail)
* pyjamaz (python)
* jamzig (zig)
* typeberry (ts)    (startup fail)

### V0.7.0 (fuzz proto v0)

* boka (swift)
* fastroll (rust)
* jamixir (elixir)
* tessera (python)
* turbojam (c++)

### v0.6.7

* graymatter (elixir)
* gossamer (go)

## Disputes

* ❌ : Fails with report
* 💀 : Crash or fuzzer protocol failure
* 🕒 : Timeout (>30 sec)

Empty cells indicate successful processing without disputes.
Only disputed reports are shown in the table

### GP 0.7.0

|            | boka | fastroll | jamduna | jamixir | jampy | jamzig | jamzilla | javajam | pyjamaz | spacejam | tessera |tsjam | turbojam | typeberry | vinwolf |
|------------|------|----------|---------|---------|-------|--------|----------|---------|---------|----------|---------|------|----------|-----------|---------|
| 1756548459 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1756548583 |  ❌  |          |         |         |       |        |          |         |         |          |   ❌    |      |    ❌    |           |         |
| 1756548667 |      |          |         |         |       |        |          |         |         |          |   ❌    |      |          |           |         |
| 1756548706 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1756548741 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1756548767 |      |          |         |         |       |        |          |         |         |          |   ❌    |      |          |           |         |
| 1756548796 |      |          |         |         |       |        |          |         |         |          |   ❌    |      |          |           |         | 
| 1756572122 |      |          |         |         |       |        |          |         |         |    ❌    |         |      |    ❌    |           |         |
| 1756790723 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1756791458 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1756814312 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1756832925 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1757062927 |      |          |         |         |       |        |          |         |         |          |   ❌    |      |          |           |         |
| 1757063641 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1757092821 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1757406079 |  ❌  |          |         |         |       |        |          |         |         |          |   ❌    |      |    ❌    |           |         |
| 1757406238 |      |          |         |         |       |        |    ❌    |         |         |          |   ❌    |      |    ❌    |           |         |
| 1757406356 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1757406441 |      |    ❌    |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1757406516 |  ❌  |          |         |         |       |        |          |         |         |          |   ❌    |      |          |           |         |
| 1757406558 |  ❌  |          |         |         |       |   ❌   |    ❌    |         |         |          |   ❌    |      |          |           |         |
| 1757406598 |      |          |         |         |       |        |    ❌    |         |         |    ❌    |   ❌    |      |    ❌    |           |         |
| 1757421101 |  💀  |          |         |         |       |   ❌   |    ❌    |         |         |          |   ❌    |      |    ❌    |           |         |
| 1757421743 |      |          |         |         |       |   ❌   |          |         |         |          |         |      |          |           |         |
| 1757421824 |  💀  |          |         |         |       |        |    ❌    |         |         |          |   ❌    |      |    ❌    |           |         |
| 1757421952 |      |          |         |         |       |        |          |         |         |          |   ❌    |      |          |           |         |
| 1757422106 |      |    ❌    |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1757422178 |  💀  |          |         |         |       |        |    ❌    |         |         |          |   ❌    |      |    ❌    |           |         |
| 1757422206 |  ❌  |          |         |         |       |   ❌   |    ❌    |         |         |          |   ❌    |      |    ❌    |           |         |
| 1757422550 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1757422647 |      |          |         |         |       |        |          |         |         |          |   ❌    |      |          |           |         |
| 1757422771 |  ❌  |    ❌    |         |         |       |   ❌   |          |         |   ❌    |    ❌    |   ❌    |      |    ❌    |           |         |
| 1757423102 |  ❌  |    ❌    |         |         |       |   ❌   |          |         |   ❌    |    ❌    |   ❌    |      |    ❌    |           |         |
| 1757423195 |      |          |         |         |       |        |          |         |         |    ❌    |   ❌    |      |          |           |         |
| 1757423271 |      |          |         |         |       |        |          |         |         |          |         |      |    ❌    |           |         |
| 1757423365 |  ❌  |    ❌    |         |         |       |   ❌   |          |         |   ❌    |    ❌    |   ❌    |      |    ❌    |           |         |
| 1757423433 |      |          |         |         |       |   ❌   |          |         |         |          |   ❌    |      |          |           |         |
| 1757423902 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |


|            | boka | fastroll | jamduna | jamixir | jampy | jamzig | jamzilla | javajam | pyjamaz | spacejam | tessera |tsjam | turbojam | typeberry | vinwolf |
|------------|------|----------|---------|---------|-------|--------|----------|---------|---------|----------|---------|------|----------|-----------|---------|
| 1757841566 |      |          |   ❌    |         |       |        |          |         |         |    ❌    |         |      |          |           |         |
| 1757842797 |      |          |         |         |       |        |          |         |         |          |         |      |          |           |         |
| 1757842852 |      |          |         |         |       |        |          |         |         |    ❌    |         |      |          |           |         |
| 1757843609 |      |          |   ❌    |         |       |        |          |         |         |          |         |      |          |           |         |
| 1757843719 |      |          |   ❌    |         |       |        |          |         |         |          |         |      |          |           |         |
| 1757843735 |      |          |   ❌    |         |       |        |          |         |         |          |         |      |          |           |         |
| 1757861618 |      |          |         |         |  ❌   |        |          |         |         |          |         |  ❌  |          |           |         |
| 1757862207 |      |          |         |         |       |        |          |         |         |          |         |  ❌  |          |           |         |
| 1757862468 |      |          |   ❌    |         |       |        |          |         |         |    ❌    |         |      |          |           |   ❌    |
| 1757862472 |      |          |   ❌    |         |       |        |          |         |         |    ❌    |         |      |          |           |   ❌    |
| 1757862743 |      |          |         |         |       |        |          |         |         |    ❌    |         |      |          |           |   ❌    |

### GP 0.6.7

Total archived traces: 33

## Performance Reports

Performance reports are available from protocol version 0.7.0 and provide
benchmarking data across some of the public JAM test vector traces.

Each participating team has their performance results stored in
`fuzz-reports/0.7.0/reports/[team]/perf/` directories.

Many teams are still providing non-optimized binaries, and the focus for M1 is
on conformance rather than performance. However, this is a good opportunity to
share some results and start looking into performance considerations. This is
especially important since the fuzzer will run for a significant number of steps
(currently exact number is undefined) and we cannot wait indefinitely for
targets to complete execution.

### Testing Setup

Current performance testing is conducted on the following platform
- **CPU**: AMD Ryzen Threadripper 3970X 32-Core (64 threads) @ 4.55 GHz
- **OS**: Linux

Note: Small differences of a few milliseconds are not significant as this is not
a dedicated machine nor long-running tests were run.

### Report Categories

Performance testing is currently run on the public jam-test-vectors traces to
allow easy reproduction and optimization. We plan to provide test traces that
target more aggressively the PVM in future testing cycles.

Current categories:
- `fallback`: No work reports. No safrole.
- `safrole`: No work reports. Safrole enabled.
- `storage`: At most 5 storage-related work items per report. No Safrole.
- `storage_light`: like `storage` but with at most 1 work item per reprot.

### Report Structure

Performance reports are stored as JSON files with the following structure:

- `info`: Implementation metadata
  - `name`: Application name
  - `app_version`: Application version (major, minor, patch)
  - `jam_version`: JAM protocol version (major, minor, patch)
- `stats`: Performance statistics
  - `steps`: Total number of fuzzer steps
  - `imported`: Number of successfully imported blocks
  - `import_max_step`: Trace step that generated the maximum execution time
  - `import_min`: Minimum import time (ms)
  - `import_max`: Maximum import time (ms)
  - `import_mean`: Mean import time (ms)
  - `import_p50`: 50th percentile import time (ms) (aka. median)
  - `import_p75`: 75th percentile import time (ms)
  - `import_p90`: 90th percentile import time (ms)
  - `import_p99`: 99th percentile import time (ms)
  - `import_std_dev`: Standard deviation of import times

Example report structure can be seen in `fuzz-reports/0.7.0/reports/polkajam/perf/storage.json`.

### Performance Dashboard

This repository provides the benchmark artifacts used by the
[JAM Conformance Dashboard](https://paritytech.github.io/jam-conformance-dashboard/).
It contains latency and throughput metrics (p50, p90, p99, mean, stdev)
for multiple JAM implementations, updated automatically for visualization
and comparison on the dashboard.
