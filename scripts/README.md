# JAM Conformance Tests

The fuzzing tools implemented elsewhere in
[polkajam-fuzz](https://github.com/paritytech/polkajam/) provide the means to test various
external implementations against the JAM protocol as described by the Graypaper.

This repository is meant to hold proof of the conformance, or lack thereof, of said
implementations. In order to do so, it is necessary to have an extensive and reliable battery of
tests we can submit these implementations to.

## Prerequisites

The following components are required to run the conformance test suite:

- **Python 3**: Runtime environment for the test scripts
- **[jam-types-py](https://github.com/davxy/jam-types-py)**: Python library providing JAM
  protocol support types and utilities
- **[jam-conformance](https://github.com/davxy/jam-conformance)**: Repository containing the
  conformance testing infrastructure (scripts, reports, traces)
- **[polkajam-fuzz](https://github.com/paritytech/polkajam)**: Fuzzer based on the PolkaJam
  implementation

## Scripts Overview

### target.py

The `target.py` script is a target manager that handles downloading and running JAM implementation
targets. It provides the following capabilities:

- **Target Management**: Downloads JAM implementations from GitHub releases or Docker images
- **Execution**: Runs targets either directly on the host or within Docker containers
- **Configuration**: Targets are defined in `targets.json` with information about their source,
  execution command, and platform support

Key commands:
```
./target.py get <target>     # Download a target implementation
./target.py run <target>     # Run a target implementation
./target.py list             # List all available targets
./target.py info <target>    # Show detailed information about a target
./target.py clean <target>   # Clean downloaded target files
```

Targets are downloaded to a directory (default: `./targets` or `TARGETS_DIR` if set) and can be
executed via Unix domain sockets for communication with the fuzzer. For details on the
communication protocol between the fuzzer and targets, see the [fuzzer protocol
documentation](../fuzz-proto/README.md).

### fuzz-workflow.py

The `fuzz-workflow.py` script orchestrates the complete fuzzing workflow by coordinating both the
target implementation (via `target.py`) and the fuzzer (from `POLKAJAM_FUZZ_DIR`). It automates:

- **Target Setup**: Downloads and prepares target implementations using `target.py`
- **Fuzzer Execution**: Runs the fuzzer from the `polkajam-fuzz` crate located at
  `POLKAJAM_FUZZ_DIR`
- **Session Management**: Creates session directories with logs, traces, and reports
- **Report Generation**: Converts binary traces to JSON format and publishes results

The script operates in two primary modes:
- **Local Mode**: Generates new traces by running a target against the fuzzer with block generation
- **Trace Mode**: Replays existing traces against one or more targets to verify conformance

In practice, `fuzz-workflow.py`:
1. Uses `target.py` to download and launch the target implementation
2. Starts the fuzzer from `POLKAJAM_FUZZ_DIR` via cargo
3. Coordinates communication between them through Unix domain sockets
4. Collects and processes the results into session directories
5. Optionally publishes reports to the `fuzz-reports` directory

## Fuzzing and Conformance Tests

Conformance requires that the target implementation (i.e. the implementation being tested) pass a
battery of test-vectors. In order to produce these test-vectors, we can use the Fuzzing system,
which works by comparing the target implementation against PolkaJam when trying to import a
succession of JAM blocks. It is not a given that PolkaJam will be correct, but frequent
iteration of this process can, and already has, reveal bugs in several implementations.

The fuzzing process produces, among other artifacts, records of the Fuzzer's execution, which we
call `traces`, composed of a linear sequence of steps. For each step in a trace, the Fuzzer
produces a binary file (`<step_number>.bin`) and its textual representation
(`<step_number>.json`) which describe:
- the block that the node tried to import at that step
- the exhaustive representation of the state, and its root hash, _before_ the block was imported
- the exhaustive representation of the state, and its root hash, _after_ the block was imported

When Fuzzing, our goal is to compare the responses of two implementations to the same trace, and
find where they differ. It is expected that, when using the exact same randomness, two
conformant implementations will produce the exact same output.

For conformance tests, we want to specify a given test-vector, composed of a trace and the
expected response. Then, once we have a well-defined test-vector, we can feed it to all
candidate implementations and record their results.

We can use the Fuzzer for both these phases, by essentially running it in two different modes.
We describe these below.

## Environment Variables

Several environment variables control the behavior of the fuzzing workflow. Some are required,
while others provide optional configuration.

### Required Variables

- `POLKAJAM_FUZZ_DIR` - Path to the `polkajam-fuzz` crate that hosts the Fuzzer code. This must be
  set before running the fuzzing workflow.

### Directory Configuration

- `JAM_FUZZ_TARGETS_DIR` - Directory where target implementations are downloaded. Defaults to
  `./targets` in the current working directory. Override this to use a shared cache location across
  multiple projects.
- `JAM_FUZZ_SESSIONS_DIR` - Directory where session artifacts are stored. Defaults to `./sessions`
  in the current working directory.
- `JAM_FUZZ_TARGETS_FILE` - Path to the targets configuration JSON file. Defaults to
  `./scripts/targets.json`. Override this to use a custom targets configuration.

### Target Execution Configuration

- `JAM_FUZZ_TARGET_SOCK` - Unix domain socket path for communication between fuzzer and target.
  Defaults to `/tmp/jam_target.sock`. Each session can override this to run multiple targets
  concurrently.
- `JAM_FUZZ_RUN_DOCKER` - Whether to run targets in Docker containers (`1`) or directly on the host
  (`0`). Defaults to `1`. Can be overridden with `--docker` or `--no-docker` flags.
- `JAM_FUZZ_DOCKER_CPU_SET` - CPU cores allocated to Docker containers (e.g., `16-32`). Defaults to
  `16-32`. Useful for isolating fuzzing workloads on multi-core systems.

### Session Configuration

- `JAM_FUZZ_SESSION_ID` - Custom session identifier. Defaults to the current Unix timestamp. Use
  this to create named sessions or overwrite existing session data.
- `JAM_FUZZ_STEP_PERIOD` - Minimum time (in milliseconds) to wait between successive steps.
  Defaults to `0` (no delay). Useful for rate-limiting or debugging.
- `JAM_FUZZ_VERBOSITY` - Log verbosity level for the Fuzzer. Defaults to `1`. Higher values
  produce more detailed logging output.

### Fuzzing Behavior (Local Mode Only)

These variables control how blocks are generated and imported during local mode fuzzing. They are
ignored in trace mode since blocks are read from existing traces.

- `JAM_FUZZ_MAX_STEPS` - Maximum number of steps to execute in a fuzzing session. Controls how
  long the fuzzer runs before terminating.
- `JAM_FUZZ_SEED` - Seed for all randomness used in the session. Using the same seed with the same
  parameters ensures reproducible execution. The seed can be found in session reports to reproduce
  specific runs.
- `JAM_FUZZ_SAFROLE` - Whether to use Safrole to produce tickets for determining the next block
  author. Affects consensus behavior during fuzzing.
- `JAM_FUZZ_MAX_WORK_ITEMS` - Maximum number of work items in work packages. Affects the data
  volume of various instructions executed by services.

## Creating a Test Vector

This is done by running the Fuzzer in an **exploratory** manner. This amounts to running the Fuzzer
in "local mode" against a target. This means the Fuzzer will produce a new block at each
step and try to import it. It will also send the same block to the target, and receive its
response. This process terminates either when the prescribed number of steps is reached, or the
two implementations differ in their results.

In either case, the Fuzzer outputs a series of artifacts. All of these are grouped inside a
"session" directory. Sessions are identified by a timestamp, corresponding to the Unix time the
Fuzzer was started, and stored inside `sessions` in the current working directory. The following
are included in a session:
- `logs`: two log files with the Fuzzer's and the target's output
- `traces`: a sequence of binary (`.bin`) files for each of the executed steps, a block and the
  pre- and post-state. This also includes a corresponding file for the genesis state, and a
  report with the difference in the last step between the two implementations.
- `report`: this includes a textual (`.json`) representation of (at least) the last two steps
  of the trace, together with their binary files. It also includes the same binary report of
  the `traces` folder, and its textual (`.json`) representation.

    Note that this directory can include more steps. This is tied to the reason why we need two
    steps in any case. Although strictly we only need the last step to see the different results
    in both implementations, we may want to reproduce the error for debugging and correction.
    This may require importing the parent block of the one we attempted to import in the last
    step, and so we need to provide the step that produced said block. In the simplest cases,
    this is just the previous step. However, when using "Mutations" (see below) we may have
    several intervening steps which proposed blocks that could not successfully be imported,
    which means the parent block was produced further behind the previous step.

It is useful to run these workflows several times by varying the fuzzing parameters. Where there
are mismatches, the resulting trace is a potential test-case. The result should be analysed and
if it reveals a unique scenario, it should be added to the test battery by copying the important
part of the trace to `fuzz-reports` on the Jam-conformance repo.

Running the same command once, with the same parameters, should produce essentially the same
execution, as the randomness used is fixed by the parameters.

### Starting the Fuzzer in Local Mode

The basic command syntax is:
```
./fuzz-workflow.py --target [[<count>]<target>[,...] | all]
```

where:
- `<count>` is an optional integer specifying the number of parallel instances (defaults to 1)
- `<target>` is the target name
- Multiple targets are comma-separated
- `all` runs all available targets

#### Basic Examples

Run a single target:
```
./fuzz-workflow.py --target jamduna
```

Run multiple instances of the same target (e.g., 3 instances):
```
./fuzz-workflow.py --target 3jamduna
```
This downloads the target once and executes three parallel fuzzing sessions, storing logs, traces,
and reports in separate session directories (one per instance).

Run multiple different targets:
```
./fuzz-workflow.py --target jamduna,gossamer,fastroll
```

Run multiple targets with different instance counts:
```
./fuzz-workflow.py --target 3jamduna,2gossamer,fastroll
```

Run all available targets:
```
./fuzz-workflow.py --target all
```

#### Controlling Randomness

By default, the fuzzer uses a fixed seed for reproducibility. To generate different execution
paths, use a random seed:
```
./fuzz-workflow.py --target <target> --rand-seed
```

The seed used for a particular run can be found in the report file, allowing you to reproduce the
exact same execution by setting the `JAM_FUZZ_SEED` environment variable.

#### Publishing Reports

To copy the session's report to `fuzz-reports`, add the `--report-publish` flag:
```
./fuzz-workflow.py --target <target> --report-publish
```

#### Optimizing Workflow

It is usually more convenient to download the target only once and then use it for successive
exploratory runs. This can be done by skipping all the main processing:
```
./fuzz-workflow.py --target <target> --skip-run --skip-report
```

To re-use the same target without downloading:
```
./fuzz-workflow.py --target <target> --skip-get [--report-publish]
```

### Generated Artifacts

These are the potential outputs of a fuzzing session:
A session directory, in `<current_directory>/sessions/<session_id>`. The session identifier is a
Unix timestamp.
- Fuzzer and target logs in `<session_directory>/logs`
- Full execution trace in `<session_directory>/trace`
- Execution report in `<session_directory>/report`

Published trace for use in a test battery, places in
`jam-conformance:fuzz-reports/<gp_version>` where `gp_version` represents the version of the
Graypaper that the implementations are meant to conform to.
- `traces/<session_id>` - includes only the binary and textual steps corresponding to the steps
  in the session's `report`.
- `reports/<target>/<session_id>` - includes only the binary and textual report from the
  session's `report` directory.

### Local Mode Parameters

Several command-line parameters control block generation behavior during local mode fuzzing. These
parameters are ignored in trace mode since blocks are read from existing traces.

#### Block Generation Profiles
- `--profile <name>` - Defines the possible operations to include in work packages executed by
  the *Bootstrap* service during block authoring. One of the possible instructions is the creation
  of instances of the *Fuzzy* service.
- `--fuzzy-profile <name>` - Defines the possible operations to include in work packages executed
  by the *Fuzzy* service during block authoring. Only active if `--profile` is set to `fuzzy`.

#### Mutation Testing
- `--max-mutations <n>` - Maximum number of mutations per block. Mutations are variations of known
  good blocks used to test fork handling and invalid block rejection.
- `--mutation-ratio <ratio>` - Probability of generating mutations. Only active if
  `--max-mutations > 0`.

See the [Environment Variables](#environment-variables) section for additional configuration
options including `JAM_FUZZ_MAX_STEPS`, `JAM_FUZZ_SEED`, `JAM_FUZZ_SAFROLE`, and
`JAM_FUZZ_MAX_WORK_ITEMS`.

## Running a Test Battery

This can be done by running the Fuzzer in "trace mode". The Fuzzer reads all the traces in the
`fuzz-reports` directory specified in the previous section. It is possible to select some subset
of the traces only. The battery can be run for a single target or for a list of them. Each
target is run from scratch for each of the available traces, and a visual report is produced at
the end of which target/trace combinations were successful or not. In this mode, the Fuzzer does
not produce any blocks. They are all described in the trace steps. Therefore, this mode does not
use any options that modify or control how blocks are generated, which includes the profiles,
the mutation or the service settings.

### Starting the Fuzzer in Trace Mode

The basic command syntax is:
```
./fuzz-workflow.py --target [[<count>]<target>[,...] | all] --source trace [--skip-get] [--report-publish]
```

where the target specification follows the same format as local mode:
- `<count>` is an optional integer specifying the number of parallel instances (defaults to 1)
- `<target>` is the target name
- Multiple targets are comma-separated
- `all` runs all available targets

Common flags for trace mode:
- `--source trace` - Required to enable trace mode
- `--skip-get` - Skip downloading targets (use cached versions)
- `--report-publish` - Publish results to `fuzz-reports`
- `--omit-log-tail` - Suppress log excerpts at the end of each target/trace run

#### Basic Examples

Run a single target against all traces:
```
./fuzz-workflow.py --target jamduna --source trace --skip-get --report-publish
```

Run multiple targets against all traces:
```
./fuzz-workflow.py --target jamduna,gossamer,fastroll --source trace --skip-get --report-publish
```

Run all available targets:
```
./fuzz-workflow.py --target all --source trace --skip-get --report-publish
```

Suppress log output for cleaner reports:
```
./fuzz-workflow.py --target jamduna,gossamer,fastroll --source trace --skip-get --report-publish --omit-log-tail
```

### Generated Artifacts

Running the Fuzzer in trace mode also creates a `<session_directory>` with path
`<current_directory>/sessions/<session_id>`. It contains:
- Fuzzer and target logs in `<session_directory>/logs`
- A directory `sessions/failed_traces_reports/<session_id>` that contains the reports for each
  session that did not finish successfully.

  Each element in this directory corresponds to a combination target/trace that did not succeed.
  For each such case, a pair of binary (`report.bin`) and textual (`report.json`) files is
  created inside `<session_id>/<target>/<trace_id>`.

The above organization ensures that all the failing test cases can be found inside
`failed_traces_reports`, even across several testing sessions; and that for each particular
testing session, all the failing reports can be found easily under one root directory.

These reports are freshly generated by this session, and should be similar, but not necessarily
equal, to a report generated for the same target/trace combination in local mode.

### Trace Mode Parameters

The parameters that affect block production (profiles, mutations, service settings) are ignored in
trace mode since blocks are read from existing traces rather than generated. However, several
parameters are available to control trace execution and filtering:

#### Trace Selection
- `--first-trace <id>` - Only process traces equal to or later than this trace ID
- `--trace-count <n>` - Process this many traces (0 means all, default: all)
- `--ignore-traces <id1,id2,...>` - Skip specific traces by ID (e.g., "1234567890,1234567891")
- `--delete-bad-traces` - Remove invalid traces (fewer than two steps) from the battery

#### Output Control
- `--discard-logs` - Remove target and fuzzer logs to save space (retained if errors occur)
- `--omit-log-tail` - Suppress log excerpts in output for cleaner reports

#### Examples

Process only traces after a specific ID:
```
./fuzz-workflow.py --target all --source trace --first-trace 1234567890
```

Process only the first 10 traces:
```
./fuzz-workflow.py --target all --source trace --trace-count 10
```

Skip specific problematic traces:
```
./fuzz-workflow.py --target all --source trace --ignore-traces 1234567890,1234567891
```

Save disk space by discarding logs:
```
./fuzz-workflow.py --target all --source trace --discard-logs --omit-log-tail
```

# A Note on Fuzzer Mutations

The concept of mutation was referred above. We give a brief explanation of what that means.

In the base case, there are no mutations and the Fuzzer proceeds linearly: each step produces a
new block, using as parent the one produced and imported (and finalized) in the previous step.

Mutations introduce the possibility of generating forks in the testing procedure, and checking
how the node behaves when dealing with potentially unsound blocks.

We can allow up to a certain number (parameter specified) of mutations per block. Mutations are
generated probabilistically, depending ultimately on the parameter `--mutation-ratio`, and are
siblings of the original block they mutate from, that is, they have the same chain parent. It is
guaranteed that the original block is processed after all its mutations, and only the original
block is finalized. This means that when we finish dealing with a block and its mutations and
advance to another block, it will be built on top of the previous original block.

Each mutation is handled in a different step, which means that the parent of an imported block
was not always produced in the previous step.
