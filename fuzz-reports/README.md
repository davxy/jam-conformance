# Fuzzer Reports

## Organization

- Reports are stored **per team** in the `./<jam-version>/reports` subfolder.  
- Traces are stored in the `./<jam-version>/traces` subfolder.  
- Each report is named after the **trace involved**.
- **Disputed traces** are preserved permanently, even after the dispute has been resolved for all teams.  

## Enrolled Teams

* boka (swift)
* fastroll (rust)
* graymatter (elixir)
* jamduna (go)
* jamixir (elixir)
* jampy (python)
* tsjam (typescript)
* jamzig (zig)
* jamzilla (go)
* javajam (java)
* pyjamaz (python)
* spacejam (rust)
* turbojam (c++)
* vinwolf (rust)

## Disputes

* ❌ := Fails with report
* 💀 := Crash or fuzzer protocol failure

Empty cells indicate successful processing without disputes.
Only disputed reports are shown in the table

### GP 0.7.0

|            | boka | fastroll | jamduna | jamixir | jampy | jamzig | jamzilla | javajam | pyjamaz | spacejam | tsjam | turbojam | vinwolf |
|------------|------|----------|---------|---------|-------|--------|----------|---------|---------|----------|-------|----------|---------|
| 1756548459 |      |          |   ❌    |   💀    |       |   ❌   |          |         |         |          |  ❌   |          |         |
| 1756548583 |  ❌  |          |   ❌    |         |       |        |          |         |         |          |  💀   |    ❌    |         |
| 1756548667 |  ❌  |          |         |         |       |        |          |         |         |    ❌    |  ❌   |          |         |
| 1756548706 |  ❌  |    ❌    |   ❌    |   ❌    |       |   ❌   |    ❌    |         |   ❌    |    ❌    |  ❌   |    ❌    |         |
| 1756548741 |      |          |   ❌    |         |       |   ❌   |          |         |         |          |  ❌   |    ❌    |         |
| 1756548767 |      |          |         |         |       |        |          |         |   ❌    |    ❌    |  ❌   |          |         |
| 1756548796 |  ❌  |          |         |         |       |        |          |         |         |    ❌    |  ❌   |          |         |
| 1756548916 |      |          |   ❌    |   ❌    |       |   ❌   |          |         |   ❌    |    ❌    |  ❌   |    ❌    |         |
| 1756572122 |  ❌  |          |         |         |  ❌   |   ❌   |          |         |   💀    |    ❌    |  ❌   |    ❌    |         |


### GP 0.6.7

Archived total traces: 33

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
