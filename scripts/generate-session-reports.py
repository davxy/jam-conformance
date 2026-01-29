#!/usr/bin/env python3

# Generate reports from existing session folders.
# This script takes a session folder and regenerates reports from the traces found there.
# It mimics the report generation logic from fuzz-workflow.py but works on existing sessions.

# example command: scripts/.venv/bin/python3 scripts/generate-session-reports.py scripts/sessions/<session-number> --spec tiny
# (target is auto-detected from logs, but can be overridden with --target)

import json
import os
import re
import shutil
import sys
import tempfile
import argparse

from jam_types import ScaleBytes
from jam_types import spec
from jam_types.fuzzer import Genesis, TraceStep, FuzzerReport

# Set JAM_CONFORMANCE_DIR relative to the script's actual location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JAM_CONFORMANCE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

DEFAULT_GP_VERSION = "0.7.2"


def parse_command_line_args():
    parser = argparse.ArgumentParser(
        description="Generate reports from existing session folders"
    )
    parser.add_argument(
        "session_dir",
        type=str,
        help="Path to the session directory containing traces",
    )
    parser.add_argument(
        "-s",
        "--report-depth",
        type=int,
        default=2,
        help="Report chain depth (default: 2)",
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
        "--gp-version",
        type=str,
        default=DEFAULT_GP_VERSION,
        help=f"Gray Paper version (default: {DEFAULT_GP_VERSION})",
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Target name (auto-detected from logs if not specified)",
    )
    parser.add_argument(
        "--spec",
        default="tiny",
        choices=["tiny", "full"],
        help="Specification to use (default=tiny)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing report directory if it exists",
    )

    args = parser.parse_args()
    return args


def decode_file_to_json(input_file, type, output_file):
    """Decode a binary file to JSON format"""
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


def generate_report(session_trace_dir, session_report_dir, report_depth, report_prune):
    """Generate a report from the traces collected in a session"""

    if not os.path.exists(session_trace_dir):
        print(f"Error: Traces directory does not exist: {session_trace_dir}")
        exit(1)

    print("-----------------------------------------------")
    print("Generating report from traces...")
    print(f"* Report dir: {session_report_dir}")
    print(f"* Traces dir: {session_trace_dir}")
    print(f"  - depth {report_depth}")
    print(f"  - prune {report_prune}")
    print("-----------------------------------------------")
    print("")

    step_files = [
        f for f in os.listdir(session_trace_dir) if re.match(r"\d{8}\.bin$", f)
    ]
    step_files.sort(reverse=True)
    if "genesis.bin" in os.listdir(session_trace_dir):
        step_files.append("genesis.bin")

    head_ancestry_depth = 0
    parent_hash = ""

    tmp_file_obj = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
    tmp_file = tmp_file_obj.name
    tmp_file_obj.close()

    # Traverse the files from the most recent to the oldest.
    for f in step_files:
        input_file = os.path.join(session_trace_dir, f)
        print(f"* Processing: {input_file}")

        shutil.copy(input_file, session_report_dir)

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

        output_file = os.path.join(session_report_dir, f"{f[:-4]}.json")
        shutil.copy(tmp_file, output_file)

        if head_ancestry_depth >= report_depth:
            break

    if os.path.exists(tmp_file):
        os.remove(tmp_file)

    process_report_file(session_trace_dir, session_report_dir)


def detect_target_from_logs(session_dir):
    """Auto-detect target name from log filenames"""
    logs_dir = os.path.join(session_dir, "logs")

    if not os.path.exists(logs_dir):
        return None

    # Look for fuzzer_*.log or target_*.log files
    log_files = os.listdir(logs_dir)
    for log_file in log_files:
        # Match fuzzer_{target}.log or target_{target}.log
        match = re.match(r'(?:fuzzer|target)_(.+)\.log$', log_file)
        if match:
            target = match.group(1)
            print(f"Auto-detected target from logs: {target}")
            return target

    return None


def publish_report_traces(session_report_dir, session_id, gp_version):
    """Publish trace files to the jam-conformance directory"""
    print("* Publish report traces")
    dest_base = os.path.join(JAM_CONFORMANCE_DIR, "fuzz-reports", gp_version)
    dest_dir = os.path.join(dest_base, "traces", session_id)

    os.makedirs(dest_dir, exist_ok=True)

    for f in os.listdir(session_report_dir):
        if not (
            re.match(r"\d{8}\.(bin|json)$", f) or re.match(r"genesis\.(bin|json)$", f)
        ):
            print(f"Skipping non-trace file {f}")
            continue
        print(f"Copying trace file {f} to {dest_dir}")
        shutil.copy(os.path.join(session_report_dir, f), dest_dir)
    print(f"Traces copied to {dest_dir}")


def publish_report_report(session_report_dir, session_id, target, gp_version):
    """Publish report files to the jam-conformance directory"""
    print("* Publish report")
    dest_base = os.path.join(JAM_CONFORMANCE_DIR, "fuzz-reports", gp_version)
    dest_dir = os.path.join(dest_base, "reports", target, session_id)

    os.makedirs(dest_dir, exist_ok=True)

    for f in os.listdir(session_report_dir):
        if f not in ["report.bin", "report.json"]:
            continue
        print(f"Copying report file {f} to {dest_dir}")
        shutil.copy(os.path.join(session_report_dir, f), dest_dir)
    print(f"Reports copied to {dest_dir}")


def publish_report(session_report_dir, session_id, target, gp_version):
    """Publish both traces and reports to jam-conformance"""
    print("* Publishing report")
    if not os.path.exists(session_report_dir):
        print(f"Error: Report directory does not exist: {session_report_dir}")
        exit(1)

    publish_report_traces(session_report_dir, session_id, gp_version)
    publish_report_report(session_report_dir, session_id, target, gp_version)


def main():
    args = parse_command_line_args()

    # Set the spec
    print(f"Setting JAM spec: {args.spec}")
    spec.set_spec(args.spec)

    # Validate session directory
    session_dir = os.path.abspath(args.session_dir)
    if not os.path.exists(session_dir):
        print(f"Error: Session directory does not exist: {session_dir}")
        exit(1)

    if not os.path.isdir(session_dir):
        print(f"Error: {session_dir} is not a directory")
        exit(1)

    # Get session ID from directory name
    session_id = os.path.basename(session_dir)
    print(f"Processing session: {session_id}")

    # Auto-detect target if not specified
    if args.target is None:
        args.target = detect_target_from_logs(session_dir)
        if args.target is None:
            args.target = "unknown"
            print("Warning: Could not auto-detect target from logs. Using 'unknown'.")

    # Define directories
    session_trace_dir = os.path.join(session_dir, "trace")
    session_report_dir = os.path.join(session_dir, "report")

    # Check if trace directory exists
    if not os.path.exists(session_trace_dir):
        print(f"Error: Trace directory not found: {session_trace_dir}")
        print(f"Expected structure: {session_dir}/trace/")
        exit(1)

    # Create or verify report directory
    if os.path.exists(session_report_dir):
        if args.overwrite:
            print(f"Warning: Removing existing report directory: {session_report_dir}")
            shutil.rmtree(session_report_dir)
        else:
            print(f"Error: Report directory already exists: {session_report_dir}")
            print("Use --overwrite to replace it")
            exit(1)

    os.makedirs(session_report_dir)

    # Generate the report
    generate_report(
        session_trace_dir,
        session_report_dir,
        args.report_depth,
        args.report_prune
    )

    print("")
    print("✓ Report generation complete!")
    print(f"  Report directory: {session_report_dir}")

    # Optionally publish the report
    if args.report_publish:
        if args.target == "unknown":
            print("Warning: No target specified. Using 'unknown' as target name.")
            print("Use --target to specify the correct target name for publishing.")

        publish_report(
            session_report_dir,
            session_id,
            args.target,
            args.gp_version
        )
        print("✓ Report published!")

    print("")


if __name__ == "__main__":
    main()
