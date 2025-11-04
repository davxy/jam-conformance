# JAM Conformance Tests

The fuzzing tools implemented elsewhere in [polkajam-fuzz](https://github.com/paritytech/polkajam/) provide the means to test various external implementations against the JAM protocol as described by the Graypaper.

This repository is meant to hold proof of the conformance, or lack thereof, of said implementations. In order to do so, it is necessary to have an extensive and reliable battery of tests we can submit these implementations to. This document outlines the spirit of these tests and how to ultimately generate them.

## Pre-Requisites

- Python
- jam-types
- jam-conformance and polkajam-fuzz
- platform_dirs

## Fuzzing and Conformance Tests

Conformance requires that the target implementation (ie the implementation being tested) pass a battery of test-vectors. In order to produce these test-vectors, we can use the Fuzzing system, which works by comparing the target implementation against Polkajam when trying to import a succession of JAM blocks. It is not a given that Polkajam will be correct, but frequent iteration of this process can, and already has, reveal bugs in several implementations. 

The fuzzing process produces, among other artifacts, records of the Fuzzer's execution, which we call `traces`, composed of a linear sequence of steps. For each step in a trace, the Fuzzer produces a binary file (`<step_number>.bin`) and its textual representation (`<step_number>.json`) which describe:
- the block that the node tried to import at that step
- the exhaustive representation of the state, and its root hash, _before_ the block was imported
- the exhaustive representation of the state, and its root hash, _after_ the block was imported

When Fuzzing, our goal is to compare the responses of two implementations to the same trace, and find where they differ. It is expected that, when using the exact same randomness, two conformant implementations will produce the exact same output.

For conformance tests, we want to specify a given test-vector, composed of a trace and the expected response.
Then, once we have a well-defined test-vector, we can feed it to all candidate implementations and record their results.

We can use the Fuzzer for both these phases, by essentially running it in two different modes. We describe these below. 

## Creating a Test Vector

This is done by running the Fuzzer in an exploratory manner. This amounts to running the Fuzzer in "local mode" against a single target. This means the Fuzzer will produce a new block at each step and try to import it. It will also send the same block to the target, and receive its response. This process terminates either when the prescribed number of steps is reached, or the two implementations differ in their results.

In either case, the Fuzzer outputs a series of artifacts. All of these are grouped inside a "session" directory. Sessions are identified by a timestamp, corresponding to the Unix time the Fuzzer was started, and stored inside `sessions` in the current working directory. The following are included in a session:  
- `logs`: two log files with the Fuzzer's and the target's output
- `traces`: a sequence of binary (`.bin`) files for each of the executed steps, a block and the pre- and post-state. This also includes a corresponding file for the genesis state, and a report with the difference in the last step between the two implementations.
- `report`: this includes a textual (`.json`) representation of (at least) the last two steps of the trace, together with their binary files. It also includes the same binary report of the `traces` folder, and its textual (`.json`) representation. 

    Note that this directory can include more steps. This is tied to the reason why we need two steps in any case. Although strictly we only need the last step to see the different results in both implementations, we may want to reproduce the error for debugging and correction. This may require importing the parent block of the one we attempted to import in the last step, and so we need to provide the step that produced said block. In the simplest cases, this is just the previous step. However, when using "Mutations" (see below) we may have several intervening steps which proposed blocks that could not successfully be imported, which means the parent block was produced further behind the previous step.

It is useful to run these workflows several times by varying the fuzzing parameters. Where there are mismatches, the resulting trace is a potential test-case. The result should be analysed and if it reveals a unique scenario, it should be added to the test battery by copying the important part of the trace to `fuzz-reports` on the Jam-conformance repo. 

Running the same command once, with the same parameters, should produce essentially the same execution, as the randomness used is fixed by the parameters.

### Starting the Fuzzer in Local Mode

The basic command is
```
./fuzz-workflow.py --target <target> 
```

This downloads the target, executes a fuzzing session and stores the logs, trace and report in a new session directory.

If we further provide the switch `--report-publish`, the contents of the session's `report` are copied to `fuzz-reports`. 


It is usually more convenient to download the target only once and then use it for successive exploratory runs. This can be done by skipping all the main processing with
```
./fuzz-workflow.py --target <target> --skip-run --skip-report
```

To re-use the same target without downloading, we can instead run
```
./fuzz-workflow.py --target <target> --skip-get [--report-publish]
```

### Generated Artifacts

These are the potential outputs of a fuzzing session:
A session directory, in `<current_directory>/sessions/<session_id>`. The session identifier is a Unix timestamp.
- Fuzzer and target logs in `<session_directory>/logs`
- Full execution trace in `<session_directory>/traces` 
- Execution report in `<session_directory>/report` 

Published trace for use in a test battery, places in `jam-conformance:fuzz-reports/<gp_version>` where `gp_version` represents the version of the Graypaper that the implementations are meant to conform to.
- `traces/<session_id>` - includes only the binary and textual steps corresponding to the steps in the session's `report`.
- `reports/<target>/<session_id>` - includes only the binary and textual report from the session's `report` directory. 

### Parameters

A number of parameters can be changed to make the Fuzzing session exercise different behaviours or scenarios by using the following parameters:

- `--profile`: defines the possible operations to include in a work-package to be executed by the Bootstrap service during block authoring. One of the possible instructions is the creation of instances of the Fuzzy service.
- `--fuzzy-profile`: defines the possible operations to include in a work-package to be executed by the Fuzzy service during block authoring. Only active if `--profile` is set to `fuzzy`.
- `--max-mutations` and `--mutation-ratio`: can be used to allow the Fuzzer to try to import mutations (ie variations) of known good block. `--mutation-ratio` is only active if `--max-mutations > 0`.

Other parameters can also be changed by using environment variables:
- `JAM_FUZZ_MAX_STEPS`: the maximum number of steps to execute in one fuzzing session.
- `JAM_FUZZ_SEED`: the seed for all the randomness used in the session. Using the same seed in a new execution will ensure the all the pseudo-random choices will be the same. Note that if other parameters are different, this may cause the behaviour to change and different pseudo-random queries to be made.
- `JAM_FUZZ_SAFROLE`: whether we use Safrole to produce tickets to determine the next block author.
- `JAM_FUZZ_MAX_WORK_ITEMS` and `JAM_FUZZ_MAX_SERVICE_KEYS`: these affect the data of the various instructions executed by the services.

## Running a Test Battery

This can be done by running the Fuzzer in "trace mode". The Fuzzer reads all the traces in the `fuzz-reports` directory specified in the previous section. It is possible to select some subset of the traces only.
The battery can be run for a single target or for a list of them. Each target is run from scratch for each of the available traces, and a visual report is produced at the end of which target/trace combinations were successful or not.
In this mode, the Fuzzer does not produce any blocks. They are all described in the trace steps. Therefore, this mode does not use any options that modify or control how blocks are generated, which includes the profiles, the mutation or the service settings. 

### Starting the Fuzzer in Trace Mode

 specified by the switch `--target <target>`, or a list of targets. This last option can be chosen by using `--target all` _and_ specifying an environment variable `JAM_FUZZ_TARGETS` beforehand with a list of targets separated by commas. 

The basic command to start this mode is:
```
./fuzz-workflow.py --target [<target>|all] --source trace --skip-get --report-publish
```

An example with several, but not all targets:
```
JAM_FUZZ_TARGETS="jamduna, gossamer, fastroll" ./fuzz-workflow.py -t all --skip-get --report-publish --source trace --omit-log-tail
```

The switch `--omit-log-tail` can be added to avoid printing the log excerpt at the end of each individual  target/trace run.

### Generated Artifacts

Running the Fuzzer in trace mode also creates a `<session_directory>` with path `<current_directory>/sessions/<session_id>`. It contains:
- Fuzzer and target logs in `<session_directory>/logs`
- A directory `sessions/failed_traces_reports/<session_id>` that contains the reports for each session that did not finish successfully. 

  Each element in this directory corresponds to a combination target/trace that did not succeed. For each such case, a pair of binary (`report.bin`) and textual (`report.json`) files is created inside `<session_id>/<target>/<trace_id>`. 
  
The above organization ensures that all the failing test cases can be found inside `failed_traces_reports`, even across several testing sessions; and that for each particular testing session, all the failing reports can be found easily under one root directory. 

These reports are freshly generated by this session, and should be similar, but not necessarily equal, to a report generated for the same target/trace combination in local mode. 

### Parameters

The parameters that affect block production are ignored in this mode. But there are some others to make the tests more convenient.

- `--discard-logs`: Remove target and fuzzer logs in trace mode, to save space, unless an error occurs.
- `--first-trace`: Only process traces equal to or later than this trace.
- `--trace-count`: Process this many traces (0 means all).
- `--ignore-traces`: Ignore these traces. Specified as a list of identifiers, e.g. "1234567890,1234567891"'
- `--delete-bad-traces`: If the Fuzzer attempts to run a trace that is invalid (has fewer than two steps) remove it from the battery.

## Environment Variables

A few variables must be defined before running the script. Others may modify the default behaviour. 

- `POLKAJAM_FUZZ_DIR` [required]: pointer to the location of the `polkajam-fuzz` crate, that hosts the Fuzzer code.
- `TARGETS_DIR`: by default, targets are downloaded into a cache. If this is specified, that location will be used and the cache can be ignored.
- `SESSIONS_DIR`: by default, the `sessions` directory is created in the current directory. If this is specified, that location can be overridden.
- `JAM_FUZZ_SESSION_ID`: by default, the Fuzzer creates a session identified by the current Unix timestamp. If this is specified, that name is used instead.
- `JAM_FUZZ_STEP_PERIOD`: Minimum time (in ms) waited between successive steps. Defaults to 0.
- `JAM_FUZZ_VERBOSITY`: The level of log messages written by the Fuzzer. Defaults to 1.

# A Note on Fuzzer Mutations

The concept of mutation was referred above. We give a brief explanation of what that means.

In the base case, there are no mutations and the Fuzzer proceeds linearly: each step produces a new block, using as parent the one produced and imported (and finalized) in the previous step. 

Mutations introduce the possibility of generating forks in the testing procedure, and checking how the node behaves when dealing with potentially unsound blocks.

We can allow up to a certain number (parameter specified) of mutations per block. Mutations are generated probabilistically, depending ultimately on the parameter `--mutation-ratio`, and are siblings of the original block they mutate from, that is, they have the same chain parent.
It is guaranteed that the original block is processed after all its mutations, and only the original block is finalized. This means that when we finish dealing with a block and its mutations and advance to another block, it will be built on top of the previous original block.

Each mutation is handled in a different step, which means that the parent of an imported block was not always produced in the previous step.

