#!/usr/bin/env python3

# Automated Fuzzing workflow. This script supports running all stages of the workflow,
# including running a single target agains the fuzzer to generate interesting traces,
# or regenerating reports for a target for a group of existing traces.
# A new version of the target is downloaded by default, unless the --skip-get argument is provided.
# The fuzzing stage can be skipped by providing the --skip-run argument.
# A fuzzing session clears the traces directory before starting, so this always contains the
# result of the last fuzzing session.
# The script can analyse that last execution, storing the trace permanently in jam-conformance
# in case this trace ended with an error, or the flag --always-store-trace is provided.
# This analysis is run and possibly stored with a new timestamp each time the script is executed.
#
# The script can run in two modes:
# - local mode, which runs a single target, and is meant to be used
#   in an exploratory session to generate new traces.
# - trace mode, which runs a group of existing traces against several targets,
#   and is meant to regenerate reports for existing traces.

import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time

from jam_types import ScaleBytes
from jam_types import spec
from jam_types.fuzzer import Genesis, TraceStep, FuzzerReport

DEFAULT_GP_VERSION = "0.7.1"
# GP_VERSION will be determined from polkajam-fuzz --version or command line
GP_VERSION = DEFAULT_GP_VERSION

CURRENT_DIR = os.getcwd()

# Set JAM_CONFORMANCE_DIR (the entry point to the jam-conformance repo) relative to the script's actual location.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JAM_CONFORMANCE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

TARGETS_DIR = os.environ.get("JAM_FUZZ_TARGETS_DIR", f"{CURRENT_DIR}/targets")

os.makedirs(TARGETS_DIR, exist_ok=True)

# Sessions run artifacts
SESSIONS_DIR = os.environ.get("JAM_FUZZ_SESSIONS_DIR", f"{CURRENT_DIR}/sessions")

# Fuzzing session id, defaults to unix timestamp
SESSION_ID = os.environ.get("JAM_FUZZ_SESSION_ID", str(int(time.time())))
# Session dir
SESSION_DIR = os.path.join(SESSIONS_DIR, SESSION_ID)
# The directory where we store the traces for one fuzzer session
SESSION_TRACE_DIR = os.path.join(SESSION_DIR, "trace")
# The directory where we store generated report for one fuzzer session
SESSION_REPORT_DIR = os.path.join(SESSION_DIR, "report")
# The directory where we store generated logs for one fuzzer session
SESSION_LOGS_DIR = os.path.join(SESSION_DIR, "logs")
# The directory where failed traces are stored
SESSION_FAILED_TRACES_DIR = os.path.join(SESSION_DIR, "failed_traces_reports")

# Target unix domain socket
SESSION_TARGET_SOCK = os.environ.get("JAM_FUZZ_TARGET_SOCK", f"/tmp/jam_fuzz_{SESSION_ID}.sock")

# Global environment variables that affect the fuzzer.
SEED = os.environ.get("JAM_FUZZ_SEED", "42")
MAX_STEPS = os.environ.get("JAM_FUZZ_MAX_STEPS", "1000000")
STEP_PERIOD = os.environ.get("JAM_FUZZ_STEP_PERIOD", "0")
MAX_WORK_ITEMS = os.environ.get("JAM_FUZZ_MAX_WORK_ITEMS", "5")
SAFROLE = os.environ.get("JAM_FUZZ_SAFROLE", "false")
SINGLE_STEP = os.environ.get("JAM_FUZZ_SINGLE_STEP", "false")
VERBOSITY = os.environ.get("JAM_FUZZ_VERBOSITY", "1")

FUZZER_LOG_TAIL_LENGTH = 100


def make_dir(path, remove=True):
    """Helper function that optionally removes directory if it exists, then creates it"""
    if remove and os.path.exists(path):
        print(f"Warning: Removing existing directory: {path}")
        shutil.rmtree(path)
    # If this fails, something went wrong about the previous removal.
    os.makedirs(path)


def parse_command_line_args():
    import argparse

    parser = argparse.ArgumentParser(description="Fuzzing workflow script")
    parser.add_argument(
        "-t",
        "--targets",
        type=str,
        help="Comma separated list of targets to fuzz.",
    )
    parser.add_argument(
        "-p", "--profile", type=str, default="fuzzy", help="Fuzzing profile to use"
    )
    parser.add_argument(
        "--fuzzy-profile", type=str, default="rand", help="Fuzzy service profile to use"
    )
    parser.add_argument(
        "-m",
        "--max-mutations",
        type=int,
        default=0,
        help="Maximum number of mutations to apply",
    )
    parser.add_argument(
        "-r", "--mutation-ratio", type=float, default=0.1, help="Mutation ratio to use"
    )
    parser.add_argument(
        "--skip-get", action="store_true", help="Skip the GET target phase"
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Skip the RUN target phase, which also skips fuzzing",
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="Skip the REPORT phase",
    )
    parser.add_argument(
        "-s",
        "--report-depth",
        type=int,
        default=2,
        help="Report chain depth",
    )
    parser.add_argument(
        "--report-prune",
        action="store_true",
        help="Exclude stale siblings from report chain",
    )
    parser.add_argument(
        "--report-publish",
        action="store_true",
        help="Publish report to JAM_CONFORMANCE_DIR",
    )
    parser.add_argument(
        "-D",
        "--delete-bad-traces",
        action="store_true",
        help="Delete traces with fewer than two steps",
    )

    # Specification to use: tiny (default) or full
    # Note: at present, 'full' may lead to errors in decoding .bin files to .json.
    parser.add_argument(
        "--spec",
        default="tiny",
        choices=["tiny", "full"],
        help="Specification to use (default=tiny)",
    )

    parser.add_argument(
        "--source",
        default="local",
        choices=["local", "trace"],
        help="Source to use (default=local)",
    )

    parser.add_argument(
        "--omit-log-tail",
        action="store_true",
        help="Don't print the last lines of the fuzzer log at the end",
    )

    parser.add_argument(
        "--discard-logs",
        action="store_true",
        help="Discard target and fuzzer logs in trace mode, to save space, unless an error occurs.",
    )

    parser.add_argument(
        "--first-trace",
        type=str,
        default="",
        help="In trace mode, only process this trace and others coming after it (with greater timestamp)",
    )

    parser.add_argument(
        "--trace-count",
        type=int,
        default=0,
        help="In trace mode, only process this many traces (0 means all)",
    )

    parser.add_argument(
        "--ignore-traces",
        type=str,
        default="",
        help='In trace mode, ignore these traces. Specified as a list of ids, without spaces, e.g. "1234567890,1234567891"',
    )

    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run multiple targets in parallel by launching separate processes",
    )

    parser.add_argument(
        "--rand-seed",
        action="store_true",
        help="Use a random fuzzer seed",
    )

    parser.add_argument(
        "--list-targets",
        action="store_true",
        help="List all available targets and exit",
    )

    parser.add_argument(
        "--gp-version",
        type=str,
        default=None,
        help=f"Gray Paper version to use (default: auto-detect from polkajam-fuzz, fallback to {DEFAULT_GP_VERSION})",
    )

    args = parser.parse_args()
    return args


def polkajam_fuzz_dir():
    # Detect if jam-conformance repo is defined, and quit with appropriate message if not
    if not os.environ.get("POLKAJAM_FUZZ_DIR"):
        print("Error: POLKAJAM_FUZZ_DIR is not defined.")
        exit(1)
    polkajam_fuzz_dir = os.environ["POLKAJAM_FUZZ_DIR"]
    if not os.path.isdir(polkajam_fuzz_dir):
        print(f"Error: POLKAJAM_FUZZ_DIR '{polkajam_fuzz_dir}' is not a valid directory.")
        exit(1)
    return polkajam_fuzz_dir


def get_gp_version_from_fuzzer():
    """Get GP version from polkajam-fuzz --version output.
    Expected format: 'polkajam-fuzz 0.1.26 (GP 0.7.1)'
    Returns the GP version or DEFAULT_GP_VERSION if parsing fails."""
    try:
        print("Getting GP version from polkajam-fuzz")
        cargo_cmd = ["cargo", "run", "--release", "-p", "polkajam-fuzz", "--", "--version"]
        result = subprocess.run(
            cargo_cmd,
            cwd=polkajam_fuzz_dir(),
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            # Try to extract GP version from output like "polkajam-fuzz 0.1.26 (GP 0.7.1)"
            match = re.search(r'\(GP\s+([\d.]+)\)', result.stdout)
            if match:
                gp_version = match.group(1)
                print(f"Detected GP version from polkajam-fuzz: {gp_version}")
                return gp_version
        print("Warning: Could not parse GP version from polkajam-fuzz --version output")
    except Exception as e:
        print(f"Warning: Failed to get GP version from polkajam-fuzz: {e}")

    print(f"Using default GP version: {DEFAULT_GP_VERSION}")
    return DEFAULT_GP_VERSION


def build_fuzzer():
    print("Building polkajam-fuzz binary")
    cargo_cmd = ["cargo", "build", "--release", "-p", "polkajam-fuzz"]
    return subprocess.run(cargo_cmd, cwd=polkajam_fuzz_dir(), check=False, text=True)


def fuzzer_run(args, log_file):
    cargo_cmd = ["cargo", "run", "--release", "-p", "polkajam-fuzz", "--"] + args

    print(f"Running cargo command: {' '.join(cargo_cmd)}")
    # Run the command and redirect output to a log file
    print(f"Fuzzer output will be written to: {log_file}")

    log = open(log_file, "w")
    return subprocess.run(
        cargo_cmd,
        cwd=polkajam_fuzz_dir(),
        check=False,
        text=True,
        stdout=log,
        stderr=subprocess.STDOUT,
    )


def run_fuzzer_local_mode(args, log_file):
    """
    Run `polkajam-fuzz` with local source with the provided arguments.
    """

    if args.rand_seed:
        seed = format(random.randint(0, 2**64 - 1), 'x')
    else:
        seed = SEED

    fuzzer_args = [
        "--source",
        args.source,
        "--max-steps",
        MAX_STEPS,
        "--step-period",
        STEP_PERIOD,
        "--safrole",
        SAFROLE,
        "--seed",
        seed,
        "--max-work-items",
        MAX_WORK_ITEMS,
        "--single-step",
        SINGLE_STEP,
        "--profile",
        args.profile,
        "--fuzzy-profile",
        args.fuzzy_profile,
        "--trace-dir",
        SESSION_TRACE_DIR,
        "--target-sock",
        SESSION_TARGET_SOCK,
        "--mutation-ratio",
        str(args.mutation_ratio),
        "--max-mutations",
        str(args.max_mutations),
        "--verbosity",
        VERBOSITY,
        "--pvm-interpreter-backend",
    ]

    result = fuzzer_run(fuzzer_args, log_file)
    if result.returncode == 0:
        print("Fuzzer completed successfully.")
    else:
        print(f"Fuzzer completed with error code: {result.returncode}")
    print(f"Check {log_file} for detailed output.")


def run_fuzzer_trace_mode(target, trace_dir, log_file):
    """
    Run `cargo polkajam-fuzz` with 'trace' source.
    """
    fuzzer_args = [
        "--source",
        "trace",
        "--seed",
        SEED,
        "--trace-dir",
        trace_dir,
        "--target-sock",
        SESSION_TARGET_SOCK,
        "--verbosity",
        VERBOSITY,
        "--pvm-interpreter-backend",
        "--trace-traces",
    ]

    fuzzer_temp_folder = f"{trace_dir}_new"
    print(f"Using temporary directory in {fuzzer_temp_folder}")

    result = fuzzer_run(fuzzer_args, log_file)

    report_missing = False
    if result.returncode == 0:
        print("Fuzzer completed successfully.")
        shutil.rmtree(fuzzer_temp_folder)
    else:
        print(f"Fuzzer completed with error code: {result.returncode}")
        failed_trace_dir = os.path.join(
            SESSION_FAILED_TRACES_DIR, target, os.path.basename(trace_dir)
        )
        shutil.move(fuzzer_temp_folder, failed_trace_dir)

        # Remove all files except report.bin from this directory
        for f in os.listdir(failed_trace_dir):
            if f != "report.bin":
                os.remove(os.path.join(failed_trace_dir, f))

        # Processing report.bin if it exists
        report_missing = not process_report_file(failed_trace_dir, failed_trace_dir)

    print(f"Check {log_file} for detailed output.")
    return [result, report_missing]


def wait_for_target_sock(target_process):
    # Detect if we terminated with an error and exit immediately if so
    # Wait up to 10 seconds for TARGET_SOCK to be created
    socket_wait_timeout = 20
    socket_wait_start = time.time()
    while not os.path.exists(SESSION_TARGET_SOCK):
        if target_process.poll() is not None:
            print("Error: Target process terminated before creating socket.")
            exit(1)
        if time.time() - socket_wait_start > socket_wait_timeout:
            print(
                f"Error: Target socket {SESSION_TARGET_SOCK} was not created within {socket_wait_timeout} seconds."
            )
            exit(1)
        time.sleep(0.1)


def run_target(target, log_file):
    """Run the target"""
    print(f"* Running target: {target}")

    if os.path.exists(SESSION_TARGET_SOCK):
        os.remove(SESSION_TARGET_SOCK)
        print(f"Removed existing socket: {SESSION_TARGET_SOCK}")

    target_command = [
        os.path.join(JAM_CONFORMANCE_DIR, "scripts/target.py"),
        "run",
        target,
        "--container-name",
        f"{target}-{SESSION_ID}"
    ]
    print(f"Starting target with command: {' '.join(target_command)}")

    # Redirect target output to a log file
    print(f"Target output will be written to: {log_file}")

    with open(log_file, "w") as target_log:
        # Set up environment variables for the subprocess
        env = os.environ.copy()
        env["JAM_FUZZ_TARGETS_DIR"] = TARGETS_DIR
        env["JAM_FUZZ_TARGET_SOCK"] = SESSION_TARGET_SOCK
        target_process = subprocess.Popen(
            target_command,
            stdin=subprocess.DEVNULL,
            stdout=target_log,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
    target_pid = target_process.pid
    print(f"Target started with PID: {target_pid}")

    wait_for_target_sock(target_process)

    print(f"Target socket {SESSION_TARGET_SOCK} is ready.")
    return [target_process, target_pid if target_process else None]


def dump_logs(log_file, tail=None):
    """Dump the contents of a log file to the console"""
    print(f"Dumping contents of log file: {log_file}")
    if os.path.exists(log_file):
        with open(log_file, "r") as log:
            lines = log.readlines()
            if tail is not None:
                lines = lines[-tail:]
            for line in lines:
                print(line, end="")
    else:
        print(f"Log file {log_file} does not exist.")


def clean_up(target_process, target_pid):
    """Terminate the target process"""
    if target_process is not None:
        print(f"* Terminating target process with PID: {target_pid}")
        target_process.terminate()
        try:
            target_process.wait(timeout=5)
            print("Target process terminated successfully")
        except subprocess.TimeoutExpired:
            print("Target process did not terminate within timeout, killing it")
            target_process.kill()


def decode_file_to_json(input_file, type, output_file):
    if type == "Genesis":
        subsystem_type = Genesis
    elif type == "TraceStep":
        subsystem_type = TraceStep
    elif type == "FuzzerReport":
        subsystem_type = FuzzerReport
    else:
        raise ValueError(f"Unknown decoding type: {type}")

    with open(input_file, "rb") as file:
        blob = file.read()

    scale_bytes = ScaleBytes(blob)
    dump = subsystem_type(data=scale_bytes)
    decoded = dump.decode()
    with open(output_file, "w") as file:
        json.dump(decoded, file, indent=4)


def generate_report(report_depth, report_prune):
    """Generate a report from the traces collected"""

    if not os.path.exists(SESSION_TRACE_DIR):
        print(f"Error: Traces directory does not exist: {SESSION_TRACE_DIR}")
        print("You may want to run the session first")
        exit(1)

    print("-----------------------------------------------")
    print("Generating report from traces...")
    print(f"* Report dir: {SESSION_REPORT_DIR}")
    print(f"* Traces dir: {SESSION_TRACE_DIR}")
    print(f"  - depth {report_depth}")
    print(f"  - prune {report_prune}")
    print("-----------------------------------------------")
    print("")

    step_files = [
        f for f in os.listdir(SESSION_TRACE_DIR) if re.match(r"\d{8}\.bin$", f)
    ]
    step_files.sort(reverse=True)
    if "genesis.bin" in os.listdir(SESSION_TRACE_DIR):
        step_files.append("genesis.bin")

    head_ancestry_depth = 0
    parent_hash = ""

    tmp_file_obj = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
    tmp_file = tmp_file_obj.name
    tmp_file_obj.close()

    # Traverse the files from the most recent to the oldest.
    for f in step_files:
        input_file = os.path.join(SESSION_TRACE_DIR, f)
        print(f"* Processing: {input_file}")

        shutil.copy(input_file, SESSION_REPORT_DIR)

        if f == "genesis.bin":
            type = "Genesis"
        else:
            type = "TraceStep"

        try:
            decode_file_to_json(input_file, type, tmp_file)
        except Exception as e:
            print(f"Error converting {f} to JSON: {e}")
            continue

        # If `report-prune` option is enabled, we require the final output to
        # be a linear series of blocks, in which each step holds the parent
        # block of the following step.
        if type != "Genesis":
            with open(tmp_file, "r") as json_file:
                try:
                    data = json.load(json_file)
                except Exception as e:
                    print(f"Error loading JSON from {tmp_file}: {e}")
                    continue

            curr_parent_hash = data.get("block", {}).get("header", "{}").get("parent", "")

            # For the first file, initialize parent_root
            if curr_parent_hash == parent_hash:
                if report_prune:
                    print(f"Skipping sibling {f}")
                    continue
            else:
                head_ancestry_depth += 1
                parent_hash = curr_parent_hash

            with open(tmp_file, "r") as json_file:
                data = json.load(json_file)

        output_file = os.path.join(SESSION_REPORT_DIR, f"{f[:-4]}.json")
        shutil.copy(tmp_file, output_file)

        if head_ancestry_depth >= report_depth:
            break

    if os.path.exists(tmp_file):
        os.remove(tmp_file)

    process_report_file(SESSION_TRACE_DIR, SESSION_REPORT_DIR)


def process_report_file(source_dir, dest_dir):
    """Process report.bin if it exists. Returns True if successful."""
    print("* Processing report.bin if it exists")
    if "report.bin" in os.listdir(source_dir):
        input_file = os.path.join(source_dir, "report.bin")

        try:
            print(f"Creating report.json file in {dest_dir}")
            decode_file_to_json(
                input_file, "FuzzerReport", os.path.join(dest_dir, "report.json")
            )
        except Exception as e:
            print(f"Error converting {input_file} to JSON: {e}")

        if source_dir != dest_dir:
            print(f"Copying {input_file} to {dest_dir}")
            shutil.copy(input_file, dest_dir)
        return True
    else:
        print(f"Warning: report.bin not found in {source_dir}, skipping decode")
        return False


def publish_report_traces(dest_base):
    print("* Publish report traces")
    dest_dir = os.path.join(dest_base, "traces", SESSION_ID)
    make_dir(dest_dir)
    for f in os.listdir(SESSION_REPORT_DIR):
        if not (
            re.match(r"\d{8}\.(bin|json)$", f) or re.match(r"genesis\.(bin|json)$", f)
        ):
            print(f"Skipping non-trace file {f}")
            continue
        print(f"Copying trace file {f} to {dest_dir}")
        shutil.copy(os.path.join(SESSION_REPORT_DIR, f), dest_dir)
    print(f"Traces copied to {dest_dir}")


def publish_report_report(dest_base, target):
    print("* Publish report")
    dest_dir = os.path.join(dest_base, "reports", target, SESSION_ID)
    make_dir(dest_dir)

    for f in os.listdir(SESSION_REPORT_DIR):
        if f not in ["report.bin", "report.json"]:
            continue
        print(f"Copying report file {f} to {dest_dir}")
        shutil.copy(os.path.join(SESSION_REPORT_DIR, f), dest_dir)
    print(f"Reports copied to {dest_dir}")


def publish_report(target):
    print("* Publishing report")
    if not os.path.exists(SESSION_REPORT_DIR):
        print(f"Error: Traces directory does not exist: {SESSION_REPORT_DIR}")
        print("You may want to run the session first")
        exit(1)
    dest_base = os.path.join(JAM_CONFORMANCE_DIR, "fuzz-reports", GP_VERSION)
    publish_report_traces(dest_base)
    publish_report_report(dest_base, target)


def run_local_workflow(args, target):
    print("")
    print("==================================================")
    print(f"Running fuzzer local workflow for {target}")
    print("==================================================")
    print("")

    if target == "all":
        print("Error: Can only use target 'all' when source is 'trace'.")
        exit(1)

    make_dir(SESSION_TRACE_DIR, remove=True)
    make_dir(SESSION_LOGS_DIR)

    target_log_file = os.path.join(SESSION_LOGS_DIR, f"target_{target}.log")
    fuzzer_log_file = os.path.join(SESSION_LOGS_DIR, f"fuzzer_{target}.log")
    [target_process, target_pid] = run_target(target, target_log_file)
    if target_process is None and target_pid == -1:
        print(f"Error: Unable to start target: {target}.")
        exit(1)
    try:
        run_fuzzer_local_mode(args, fuzzer_log_file)
        clean_up(target_process, target_pid)
    except Exception as e:
        print(f"Cleaning up after error in local mode {e}")
        clean_up(target_process, target_pid)
        dump_logs(target_log_file)
        dump_logs(fuzzer_log_file)
        exit(1)

    if not args.skip_report:
        make_dir(SESSION_REPORT_DIR)
        generate_report(args.report_depth, args.report_prune)
        if args.report_publish:
            publish_report(target)
    else:
        print("Skipping report generation")


    if not args.omit_log_tail and not args.skip_run:
        print("")
        print("--------------------------------------------------")
        print(f"fuzzer_{target}.log tail")
        print("--------------------------------------------------")
        dump_logs(fuzzer_log_file, tail=FUZZER_LOG_TAIL_LENGTH)
        print("--------------------------------------------------\n")
      

def run_trace_workflow(args, target):
    if args.skip_report:
        print("Warning: Ignoring flag to skip report generation.")

    source_traces_dir = os.path.join(
        JAM_CONFORMANCE_DIR, "fuzz-reports", GP_VERSION, "traces"
    )
    if not os.path.exists(source_traces_dir):
        print(f"No traces available in {source_traces_dir}. Exiting.")
        exit(1)
        
    print(f"* Using source traces from: {source_traces_dir}")

    make_dir(SESSION_LOGS_DIR)
    make_dir(SESSION_FAILED_TRACES_DIR)

    print("")
    print("==================================================")
    print(f"Running fuzzer trace workflow for {target}")
    print("==================================================")

    trace_dirs = get_filtered_traces(source_traces_dir, args)

    results = run_trace_for_target(target, trace_dirs, source_traces_dir, args)

    print("")
    print("===================================================")
    print("Summary of results:")

    summary_file = os.path.join(SESSION_DIR, f"summary_{target}.txt")
    with open(summary_file, 'w') as f:
        f.write(f"Summary of results for {target}\n")
        f.write("=" * 50 + "\n")
        for r in results:
            print(f"{target}: {r}")
            f.write(f"{r}" + "\n")

    print("===================================================")
    print(f"Summary saved to: {summary_file}")
    print("")

    # We can override the SESSION_ID, which means it is possible to run the script
    # for an earlier session. That means we may have reports on file ready to publish,
    # even if we did not run the fuzzing process in this execution.
    if args.report_publish:
        print("* Publishing report to jam-conformance")
        # Overwrite the previous report if any. This always keeps the last example
        # of a target failing a particular trace.
        shutil.copytree(
            SESSION_FAILED_TRACES_DIR,
            os.path.join(JAM_CONFORMANCE_DIR, "fuzz-reports", GP_VERSION, "reports"),
            dirs_exist_ok=True,
        )


def check_trace_is_valid(source_traces_dir, trace, args):
    full_trace_dir = os.path.join(source_traces_dir, trace)
    step_files = [f for f in os.listdir(full_trace_dir) if is_step_file(f)]
    if len(step_files) < 2:
        print(
            f"Invalid trace directory: {full_trace_dir} has {len(step_files)} step files"
        )
        if args.delete_bad_traces:
            shutil.rmtree(full_trace_dir)
        return None
    return full_trace_dir

  
def get_filtered_traces(traces_dir, args):
    traces = []
    files = os.listdir(traces_dir)
    for file in files:
        if not os.path.isdir(os.path.join(traces_dir, file)):
            continue
        if not re.match(r'^\d+', file):
            continue
        if args.first_trace and file < args.first_trace:
            continue
        if args.ignore_traces and file in args.ignore_traces:
            continue
        traces.append(file)
    return traces


def run_trace_for_target(target, trace_dirs, source_traces_dir, args):
    target_results = []
    count_traces = 0
    for trace in trace_dirs:
        full_trace_dir = check_trace_is_valid(source_traces_dir, trace, args)
        if full_trace_dir is None:
            continue

        print("")
        print("--------------------------------------------------")
        print(f"Importing trace {trace}")
        print("--------------------------------------------------")

        target_log_file = os.path.join(
            SESSION_LOGS_DIR, f"target_{target}_{trace}.log"
        )
        fuzzer_log_file = os.path.join(
            SESSION_LOGS_DIR, f"fuzzer_{target}_{trace}.log"
        )

        [target_process, target_pid] = run_target(target, target_log_file)
        if target_process is None and target_pid == -1:
            print(f"Error: Unable to start target: {target}.")
            target_results.append(f"💀 {trace}")

        else:
            try:
                [trace_result, report_missing] = run_fuzzer_trace_mode(
                    target, full_trace_dir, fuzzer_log_file
                )
                if report_missing:
                    target_results.append(f"💀 {trace}")
                else:
                    if trace_result.returncode == 0:
                        target_results.append(f"🟢 {trace}")
                    else:
                        target_results.append(f"🔴 {trace}")

                clean_up(target_process, target_pid)
                if args.discard_logs:
                    os.remove(target_log_file)
                    os.remove(fuzzer_log_file)
            except Exception as e:
                print(
                    f"Cleaning up after error in trace mode while running {target}: {e}"
                )
                clean_up(target_process, target_pid)
                dump_logs(target_log_file)
                dump_logs(fuzzer_log_file)
                continue
        count_traces += 1
        if args.trace_count > 0 and count_traces == args.trace_count:
            break
    return target_results


def is_step_file(f):
    """Check if a file is a step file (8-digit .bin) or is genesis.bin"""
    return re.match(r"^\d{8}\.bin$", f) or f == "genesis.bin"


def get_full_target_list():
    """Get the list of available targets, optionally filtered by spec version"""
    cmd = [
        os.path.join(JAM_CONFORMANCE_DIR, "scripts/target.py"),
        "list",
        "--gp-version",
        GP_VERSION
    ]

    list_targets = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if list_targets.returncode != 0:
        print(f"Error: Unable to list targets: {list_targets}")
        return []
    targets = list_targets.stdout.splitlines()
    return targets

def get_selected_target_list(targets):
    """Get the list of targets selected by the user, filtered by GP_VERSION"""
    available_targets = get_full_target_list()
    if targets == ["all"]:
        return available_targets
    valid_targets = []
    for target in targets:
        if target in available_targets:
            valid_targets.append(target)
        else:
            print(f"⚠️ '{target}' is not available for the selected GP version and will be skipped")
    return valid_targets


def run_targets_recursively(targets, parallel=False, rand_seed=False):
    """
    Run multiple targets by launching separate script processes for each target.
    Each target gets its own subprocess with a unique session ID.

    Args:
        targets: List of target names to run
        original_args: Original command-line arguments
        parallel: If True, run all targets in parallel; if False, run sequentially
    """
    mode = "parallel" if parallel else "sequential"
    print(f"Running workflow for {len(targets)} targets in {mode} mode...")      

    # Build arguments for recursive calls
    base_args = []
    skip_next = False
    for i, arg in enumerate(sys.argv[1:]):
        if skip_next:
            skip_next = False
            continue
        # Skip the targets argument as we'll replace it
        if arg in ["-t", "--targets"]:
            skip_next = True
            continue
        # Skip --parallel and --rand-seed to avoid confusion in child processes
        if arg == "--parallel" or arg == "--rand-seed":
            continue
        base_args.append(arg)

    # Set up environment
    env = os.environ.copy()
    env["JAM_FUZZ_SINGLE_TARGET"] = "1"  # Prevent recursive execution

    # Launch processes for all targets
    processes = []
    for target in targets:
        # Generate unique session ID for each target
        session_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
        target_env = env.copy()
        target_env["JAM_FUZZ_SESSION_ID"] = session_id
        target_env["JAM_FUZZ_VERBOSITY"] = "0"

        if rand_seed:
            target_env["JAM_FUZZ_SEED"] = session_id
        else:
            target_env["JAM_FUZZ_SEED"] = SEED

        cmd = [sys.executable, os.path.abspath(__file__), "--target", target, "--gp-version", GP_VERSION, "--skip-get"] + base_args
        print(f"{'Launching' if parallel else 'Running'} target {target} with session {session_id}")
        proc = subprocess.Popen(cmd, env=target_env)
        processes.append((target, proc, session_id))

        # In sequential mode, wait for each process to complete before launching the next
        if not parallel:
            proc.wait()

    # Collect results (in parallel mode, this waits for all; in sequential mode, processes already completed)
    results = []
    for target, proc, session_id in processes:
        retcode = proc.wait()  # Returns immediately if already completed
        result_string = "Success" if retcode == 0 else f"Failed (exit {retcode})"
        results.append((target, session_id, result_string))

    # Print summary
    print("\n" + "="*50)
    print("Summary:")
    for target, session_id, result in results:
        print(f"  {target}: {result} (sid={session_id})")
    print("="*50)
    

def get_target(target):
    """Download the target if needed"""
    print(f"* Downloading target: {target}")
    env = os.environ.copy()
    env["JAM_FUZZ_TARGETS_DIR"] = TARGETS_DIR

    target_command = [
        os.path.join(JAM_CONFORMANCE_DIR, "scripts/target.py"),
        "get",
        target,
    ]
    target_process = subprocess.Popen(
        target_command,
        stdin=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    retcode = target_process.wait()
    if retcode != 0:
        exit(retcode)


def explode_target_args(targets):
    targets = targets.split(",")
    exploded = []
    for target in targets:
        target = target.strip()
        # Check if target matches pattern: number + separator + name (e.g., "2xboka", "2*boka", "2Xboka")
        import re
        match = re.match(r'^(\d+)(.+)$', target)
        if match:
            count = int(match.group(1))
            name = match.group(2)
            # Insert the target 'count' times
            exploded.extend([name] * count)
        else:
            exploded.append(target)
    print(exploded)
    return exploded
    

def main():
    global GP_VERSION
    args = parse_command_line_args()

    # If we will need the fuzzer, build it as soon as possible.
    # Do not attempt building on recursive calls
    if not os.environ.get("JAM_FUZZ_SINGLE_TARGET"):
        result = build_fuzzer()
        if result.returncode != 0:
            print(f"Error building fuzzer: {result.returncode}")
            exit(1)

    # Determine GP version: use command line if provided, otherwise detect from fuzzer
    if args.gp_version is not None:
        # User explicitly specified a version
        GP_VERSION = args.gp_version
    else:
        # Try to detect GP version from polkajam-fuzz
        GP_VERSION = get_gp_version_from_fuzzer()

    # Handle --list-targets command
    if args.list_targets:
        targets = get_full_target_list()
        print(f"Available targets for GP version {GP_VERSION}:")
        for target in targets:
            print(f"  {target}")
        return

    # Validate that targets are specified when not listing
    if not args.targets:
        print("Error: -t/--targets is required unless using --list-targets")
        exit(1)

    print(f"Setting JAM spec: {args.spec}")
    spec.set_spec(args.spec)

    mode = args.source

    targets = explode_target_args(args.targets)
    targets = get_selected_target_list(targets)
    if len(targets) == 0:
        print("No targets to run")
        exit(0)

    # Handle multiple targets with recursive execution
    # (sequential by default, parallel if --parallel flag is set)
    if len(targets) > 1 and not os.environ.get("JAM_FUZZ_SINGLE_TARGET"):
        run_targets_recursively(targets, parallel=args.parallel, rand_seed=args.rand_seed)
        return

    target = targets[0]

    if not args.skip_get:
        get_target(target)
    else:
        print("Skipping get")

    if not args.skip_run:
        if mode == "local":
            run_local_workflow(args, target)
        elif mode == "trace":
            run_trace_workflow(args, target)
    else:
        print("Skipping run")


if __name__ == "__main__":
    main()
