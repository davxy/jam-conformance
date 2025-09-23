# Fuzzer Reports

## Organization

- Reports are stored **per team** in the `./<jam-version>/reports` subfolder.  
- Traces are stored in the `./<jam-version>/traces` subfolder.  
- Each report is named after the **trace involved**.
- **Disputed traces** are preserved permanently, even after the dispute has been resolved for all teams.  

## Enrolled Teams

### V0.7.0

* boka (swift) (v0)
* fastroll (rust)
* jamduna (go)
* jamixir (elixir)
* jampy (python)
* jamzig (zig)
* jamzilla (go)
* javajam (java)
* pyjamaz (python)
* spacejam (rust)
* tessera (python)
* tsjam (ts)
* turbojam (c++)
* typeberry (ts)
* vinwolf (rust)

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

|            | boka | fastroll | jamduna | jamixir | jampy | jamzig | jamzilla | javajam | pyjamaz | spacejam | tessera | tsjam | turbojam | typeberry | vinwolf |
|------------|------|----------|---------|---------|-------|--------|----------|---------|---------|----------|---------|-------|----------|-----------|---------|
| 1756548459 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1756548583 |  ❌  |          |         |         |       |        |          |         |         |          |         |       |    ❌    |           |         |
| 1756548667 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1756548706 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1756548741 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1756548767 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1756548796 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         | 
| 1756572122 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1756790723 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1756791458 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1756814312 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1756832925 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1757062927 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1757092821 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1757406079 |  ❌  |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757406238 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757406356 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757406441 |      |          |         |         |       |        |    ❌    |         |         |          |         |       |          |           |         |
| 1757406516 |  ❌  |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757406558 |  ❌  |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757406598 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757421101 |  💀  |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757421743 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757421824 |  💀  |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757421952 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1757422106 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1757422178 |  💀  |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757422206 |  ❌  |          |         |         |       |        |          |         |         |          |   ❌    |       |    ❌    |           |         |
| 1757422550 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1757422647 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757422771 |  ❌  |    ❌    |         |         |       |        |          |         |         |          |   ❌    |       |    ❌    |           |         |
| 1757423102 |  ❌  |    ❌    |         |         |       |        |          |         |         |          |   ❌    |       |    ❌    |           |         |
| 1757423195 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757423271 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757423365 |  ❌  |    ❌    |         |         |       |        |          |         |         |          |   ❌    |       |    ❌    |           |         |
| 1757423433 |      |          |         |         |       |   ❌   |          |         |         |          |         |       |          |           |         |
| 1757423902 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1757841566 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757842797 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757842852 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757843609 |      |          |         |         |       |        |          |         |         |          |         |       |          |           |         |
| 1757843719 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |    ❌    |           |         |
| 1757843735 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757861618 |      |          |         |         |  ❌   |   ❌   |          |         |         |          |   ❌    |   ❌  |    ❌    |           |         |
| 1757862207 |      |          |         |         |       |        |          |         |         |          |   ❌    |   ❌  |          |           |         |
| 1757862468 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757862472 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1757862743 |      |    ❌    |         |         |       |        |          |         |         |          |   ❌    |       |    ❌    |           |         |

#### New

|            | boka | fastroll | jamduna | jamixir | jampy | jamzig | jamzilla | javajam | pyjamaz | spacejam | tessera | tsjam | turbojam | typeberry | vinwolf |
|------------|------|----------|---------|---------|-------|--------|----------|---------|---------|----------|---------|-------|----------|-----------|---------|
| 1758621171 |      |          |    ❌   |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1758621172 |      |          |         |   ❌    |       |        |          |         |         |    ❌    |   ❌    |       |          |           |         |
| 1758621173 |      |          |         |         |       |        |          |         |         |          |   ❌    |       |          |           |         |
| 1758621198 |      |          |    ❌   |   💀    |  💀   |   ❌   |    ❌    |    ❌   |   ❌    |    ❌    |   ❌    |   ❌  |    ❌    |    ❌     |         |
| 1758621412 |      |          |    ❌   |   💀    |  💀   |   ❌   |          |         |   ❌    |    ❌    |   ❌    |   ❌  |          |           |         |
| 1758621498 |      |          |    ❌   |   💀    |  💀   |   ❌   |          |         |   ❌    |    ❌    |   ❌    |   ❌  |          |           |         |
| 1758621547 |      |          |    ❌   |         |  💀   |   ❌   |    ❌    |    ❌   |   ❌    |    ❌    |   ❌    |       |    ❌    |           |         |
| 1758621879 |      |          |         |         |       |   ❌   |          |         |         |    ❌    |   ❌    |       |          |           |         |
| 1758621952 |      |          |    ❌   |         |  💀   |        |          |         |   ❌    |    ❌    |   ❌    |   ❌  |    ❌    |           |         |
| 1758622000 |      |          |    ❌   |         |  ❌   |        |    ❌    |         |         |          |   ❌    |       |    ❌    |           |         |
| 1758622051 |      |          |    ❌   |         |  ❌   |        |    ❌    |         |         |          |   ❌    |       |    ❌    |           |         |
| 1758622104 |      |          |    ❌   |   ❌    |  ❌   |        |          |         |         |    ❌    |   ❌    |       |          |           |         |
| 1758622160 |      |          |    ❌   |         |  ❌   |        |          |         |         |          |   ❌    |       |    ❌    |           |         |
| 1758622313 |      |          |         |         |       |   ❌   |          |         |         |          |   ❌    |       |          |           |         |
| 1758622403 |      |          |         |         |       |   ❌   |          |    ❌   |         |    ❌    |   ❌    |   ❌  |          |    ❌     |         |
| 1758622442 |      |          |         |         |       |   ❌   |          |    ❌   |   ❌    |    ❌    |   ❌    |   ❌  |          |    ❌     |         |
| 1758622524 |      |          |    ❌   |         |  ❌   |        |    ❌    |         |         |          |   ❌    |   ❌  |          |           |         |

#### New-2 (Mostly Transfer hostcall)

|            | boka | fastroll | jamduna | jamixir | jampy | jamzig | jamzilla | javajam | pyjamaz | spacejam | tessera | tsjam | turbojam | typeberry | vinwolf |
|------------|------|----------|---------|---------|-------|--------|----------|---------|---------|----------|---------|-------|----------|-----------|---------|
| 1758636573 |      |    ❌    |   ❌    |         |  💀   |   ❌   |    ❌    |    ❌   |         |          |         |       |          |           |         |
| 1758636775 |      |    ❌    |   ❌    |   💀    |  💀   |   ❌   |          |         |   ❌    |          |         |       |          |           |         |
| 1758636819 |      |    ❌    |   ❌    |   💀    |  💀   |   ❌   |    ❌    |    ❌   |   ❌    |          |         |       |          |           |         |
| 1758636961 |      |    ❌    |   ❌    |   💀    |  💀   |   ❌   |          |         |   ❌    |          |         |       |          |           |         |
| 1758637024 |      |    ❌    |   ❌    |   💀    |  💀   |   ❌   |          |         |   ❌    |          |         |       |          |           |         |
| 1758637136 |      |    ❌    |   ❌    |   💀    |  💀   |   ❌   |          |         |   ❌    |          |         |       |          |           |         |
| 1758637203 |      |    ❌    |   ❌    |         |  💀   |   ❌   |    ❌    |    ❌   |   ❌    |          |         |       |          |           |         |
| 1758637250 |      |    ❌    |   ❌    |   💀    |  💀   |   ❌   |          |         |   ❌    |          |         |       |          |           |         |
| 1758637297 |      |    ❌    |   ❌    |   💀    |  💀   |   ❌   |          |         |   ❌    |          |         |       |          |           |         |
| 1758637332 |      |    ❌    |   ❌    |         |  💀   |   ❌   |    ❌    |    ❌   |         |          |         |       |          |           |         |
| 1758637363 |      |    ❌    |   ❌    |   💀    |  💀   |   ❌   |          |         |   ❌    |          |         |       |          |           |         |
| 1758637447 |      |    ❌    |   ❌    |   💀    |  💀   |   ❌   |          |         |   ❌    |          |         |       |          |           |         |
| 1758637485 |      |    ❌    |   ❌    |   💀    |  💀   |   ❌   |          |         |   ❌    |          |         |       |          |           |         |

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

### Testing Environment

Current performance testing is conducted on the following platform:
- **CPU**: AMD Ryzen Threadripper 3970X 32-Core (64 threads) @ 4.55 GHz
- **OS**: Linux

Kernel parameters:
- `amd_pstate=passive`: CPU frequency is controlled explicitly by the governor.
- `cpufreq.default_governor=performance`: forces full-speed operation.
- `processor.max_cstate=1`: prevents deep C-states, so CPU doesn’t sleep in ways
  that add latency.
- `idle=poll`: forces busy-polling instead of halting for minimal latency.
- `isolcpus=16-31`: cores isolated from the scheduler for dedicated benchmarking.
- `nohz_full=16-31`: full tickless mode on isolated cores; minimizes kernel timer interrupts.
- `rcu_nocbs=16-31`: prevents RCU callbacks from running on isolated cores.
- `irqaffinity=0-16`: pins interrupts to cores, leaving isolated cores mostly free of OS noise.
- `tsc=reliable`: ensures the Time Stamp Counter (TSC) is monotonic and stable for
  precise timing measurements.
- `mitigations=off`: disables Spectre/Meltdown mitigations. Good for raw performance.

Additional tweaks:
- Pin CPU frequency to exactly the nominal frequency of workstation CPU:
  `cpupower frequency-set --min 3700MHz --max 3700MHz`
- Disable CPU boost (turbo) functionality:
  `echo 0 > /sys/devices/system/cpu/cpufreq/boost`

Targets that are not already provided as a Docker image, are run in a vanilla
debian-slim container started with parameters optimized for benchmarking

Docker parameters:

- `--cpuset-cpus 16-31`: Pin container to isolated CPU cores
- `--cpu-shares 2048`: High CPU priority (default is 1024)
- `--cpu-quota -1`: No CPU time limits (unlimited CPU usage)
- `--memory 8g`: Set memory limit to 8GB
- `--memory-swap 8g`: Set swap limit equal to memory (no additional swap)
- `--shm-size 1g`: Shared memory size for IPC operations
- `--ulimit nofile=65536:65536`: Increase file descriptor limit
- `--ulimit nproc=32768:32768`: Increase process/thread limit
- `--sysctl net.core.somaxconn=65535`: Increase socket connection backlog
- `--sysctl net.ipv4.tcp_tw_reuse=1`: Enable TCP TIME_WAIT socket reuse
- `--security-opt seccomp=unconfined`: Disable seccomp filtering for performance
- `--security-opt apparmor=unconfined`: Disable AppArmor restrictions
- `--cap-add SYS_NICE`: Allow process priority changes
- `--cap-add SYS_RESOURCE`: Allow resource limit modifications
- `--cap-add IPC_LOCK`: Allow memory locking (prevents swapping)

Docker process itself is run with the following priority related environment:

- `chrt -f 99`: Set real-time FIFO scheduling with highest priority (99)
- `nice -n -20`: Set highest CPU priority (-20 is highest nice value)
- `ionice -c1 -n0`: Set real-time I/O scheduling class with highest priority (0)
- `taskset -c 16-31`: Pin Docker process to isolated CPU cores (16-31)

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
  - `fuzz_version`: Fuzzer protocol version
  - `fuzz_features`: Fuzzer protocol features
  - `jam_version`: JAM protocol version (major, minor, patch)
  - `app_version`: Application version (major, minor, patch)
  - `app_name`: Application name
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
