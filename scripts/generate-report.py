#!/usr/bin/env python3

"""
Regenerate a fuzzer report from a previously captured traces folder,
without rerunning the fuzzer. This is the report-generation logic from
fuzz-workflow.py extracted to operate on existing trace data.

Usage:
    scripts/generate-report.py <traces-dir> --spec <tiny/full>

The traces directory must contain the binary step files written by
the fuzzer (genesis.bin and NNNNNNNN.bin, plus optionally report.bin).

Steps are decoded from SCALE to JSON using the jam_types codecs and
processed newest-first. With --prune, only a linear chain of ancestor
blocks is kept (siblings whose parent matches the previously seen
step are dropped). The walk stops once --depth distinct ancestors
have been emitted (default 2).

Decoded JSON and the matching .bin files land in ./report/ under the
current working directory; report.bin, when present, is decoded into
report.json there as well. Pass --overwrite to replace an existing
report directory.

Dependencies:
    jam-types-py (https://github.com/davxy/jam-types-py) provides the
    SCALE codecs used to decode traces. Producing a correct report for
    a given Gray Paper version requires a matching jam-types-py
    release: traces produced by a target implementing GP 0.7.2 must be
    decoded with jam-types-py v0.7.2
    (https://github.com/davxy/jam-types-py/releases/tag/v0.7.2).
"""

import json
import os
import re
import shutil
import tempfile
import argparse

from jam_types import ScaleBytes
from jam_types import spec
from jam_types.fuzzer import Genesis, TraceStep, FuzzerReport


def parse_command_line_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate a report from an existing traces folder. "
            "Requires jam-types-py (https://github.com/davxy/jam-types-py); "
            "use a release matching the Gray Paper version of the traces."
        )
    )
    parser.add_argument(
        "traces_dir",
        type=str,
        help="Path to the directory containing the binary trace files",
    )
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=2,
        help="Report chain depth (default: 2)",
    )
    parser.add_argument(
        "-p",
        "--prune",
        action="store_true",
        help="Exclude stale siblings from report chain",
    )
    parser.add_argument(
        "-s",
        "--spec",
        default="tiny",
        choices=["tiny", "full"],
        help="Specification to use (default=tiny)",
    )
    parser.add_argument(
        "-o",
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


def generate_report(session_trace_dir, session_report_dir, depth, prune):
    """Generate a report from the traces collected in a session"""

    print("-----------------------------------------------")
    print("Generating report from traces...")
    print(f"* Report dir: {session_report_dir}")
    print(f"* Traces dir: {session_trace_dir}")
    print(f"  - depth {depth}")
    print(f"  - prune {prune}")
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

        if f == "genesis.bin":
            type = "Genesis"
        else:
            type = "TraceStep"

        try:
            decode_file_to_json(input_file, type, tmp_file)
        except Exception as e:
            print(f"Error converting {f} to JSON: {e}")
            continue

        # If `prune` option is enabled, we require the final output to be a
        # linear series of blocks, in which each step holds the parent block
        # of the following step.
        if type != "Genesis":
            with open(tmp_file, "r") as json_file:
                try:
                    data = json.load(json_file)
                except Exception as e:
                    print(f"Error loading JSON from {tmp_file}: {e}")
                    continue

            curr_parent_hash = data.get("block", {}).get("header", {}).get("parent", "")

            # For the first file, initialize parent_root
            if curr_parent_hash == parent_hash:
                if prune:
                    print(f"Skipping sibling {f}")
                    continue
            else:
                head_ancestry_depth += 1
                parent_hash = curr_parent_hash

        shutil.copy(input_file, session_report_dir)
        output_file = os.path.join(session_report_dir, f"{f[:-4]}.json")
        shutil.copy(tmp_file, output_file)

        if head_ancestry_depth >= depth:
            break

    if os.path.exists(tmp_file):
        os.remove(tmp_file)

    process_report_file(session_trace_dir, session_report_dir)


def main():
    args = parse_command_line_args()

    # Set the spec
    print(f"Setting JAM spec: {args.spec}")
    spec.set_spec(args.spec)

    # Validate traces directory
    session_trace_dir = os.path.abspath(args.traces_dir)
    if not os.path.exists(session_trace_dir):
        print(f"Error: Traces directory does not exist: {session_trace_dir}")
        exit(1)

    if not os.path.isdir(session_trace_dir):
        print(f"Error: {session_trace_dir} is not a directory")
        exit(1)

    # Report directory in the current working directory
    session_report_dir = os.path.abspath("report")

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
        args.depth,
        args.prune
    )

    print("")
    print("✓ Report generation complete!")
    print(f"  Report directory: {session_report_dir}")
    print("")


if __name__ == "__main__":
    main()
