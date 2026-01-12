# Fuzzer Performance Reports

Performance reports are available from protocol version 0.7.0 and provide
benchmarking data across some of the public JAM test vector traces.

Many teams are still providing non-optimized binaries, and the focus for M1 is
on conformance rather than performance. However, this is a good opportunity to
share some results and start looking into performance considerations. This is
especially important since the fuzzer will run for a significant number of steps
(currently exact number is undefined) and we cannot wait indefinitely for
targets to complete execution.

## Testing Environment

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

## Report Categories

Performance testing is currently run on the public jam-test-vectors traces to
allow easy reproduction and optimization. We plan to provide test traces that
target more aggressively the PVM in future testing cycles.

Current categories:
- `fallback`: No work reports. No safrole.
- `safrole`: No work reports. Safrole enabled.
- `storage`: At most 5 storage-related work items per report. No Safrole.
- `storage_light`: like `storage` but with at most 1 work item per reprot.

## Report Structure

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

Example report structure can be seen in [polkajam/storage.json].

## Performance Dashboard

This repository provides the benchmark artifacts used by the
[JAM Conformance Dashboard](https://paritytech.github.io/jam-conformance-dashboard/).
It contains latency and throughput metrics (p50, p90, p99, mean, stdev)
for multiple JAM implementations, updated automatically for visualization
and comparison on the dashboard.
