#!/usr/bin/env python3

"""
Read per-target summary files from a folder and produce a single markdown table.

Usage:
    python3 generate-summary-table.py /path/to/summaries

Each .txt file in the folder is expected to have lines like:
    <emoji> <test_id>
where emoji is one of: green circle, red circle, yellow circle, white circle.

The output table is written to summary-table.md in the same folder.
"""

import os
import re
import sys

EMOJI_TO_SYMBOL = {
    "\U0001f7e2": "\U0001f7e2",  # green  -> green (ok)
    "\U0001f534": "\U0001f534",  # red    -> red (fail)
    "\U0001f7e1": "\U0001f7e1",  # yellow -> yellow (keep as-is)
    "\u26aa":     "\u26aa",      # white  -> white (skip/not applicable)
}

STATUS_LINE_RE = re.compile(r"^([\U0001f7e2\U0001f534\U0001f7e1\u26aa])\s+(.+)$")

# Symbol used when a test ID is not present for a target
NOT_PRESENT = "\u26aa"


def parse_summary(path):
    """Return dict mapping test_id -> emoji."""
    results = {}
    with open(path) as f:
        for line in f:
            m = STATUS_LINE_RE.match(line.strip())
            if m:
                symbol = EMOJI_TO_SYMBOL.get(m.group(1), "?")
                test_id = m.group(2)
                results[test_id] = symbol
    return results


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <summaries-folder>", file=sys.stderr)
        sys.exit(1)

    folder = sys.argv[1]
    if not os.path.isdir(folder):
        print(f"Error: {folder} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Collect all summary files
    files = sorted(f for f in os.listdir(folder) if f.endswith(".txt"))
    if not files:
        print("No .txt summary files found.", file=sys.stderr)
        sys.exit(1)

    # Parse all summaries: target_name -> {test_id -> symbol}
    targets = {}
    for fname in files:
        name = fname.removesuffix(".txt")
        targets[name] = parse_summary(os.path.join(folder, fname))

    target_names = list(targets.keys())

    # Collect all test IDs preserving the order from the first file
    first = targets[target_names[0]]
    test_ids = list(first.keys())

    # Also add any IDs that appear in other files but not the first
    all_ids = set(test_ids)
    for data in targets.values():
        for tid in data:
            if tid not in all_ids:
                test_ids.append(tid)
                all_ids.add(tid)

    # Compute column widths for aligned output.
    # Emojis are 1 codepoint but render as 2 columns in monospace fonts, so
    # data-row cells and text-row cells need matching visual widths.
    total = len(test_ids)
    summary_label = "**PASS**"
    id_width = max(
        len("test_id"),
        len(summary_label),
        max((len(tid) for tid in test_ids), default=0),
    )

    pass_counts = {}
    for name in target_names:
        green = sum(1 for tid in test_ids if targets[name].get(tid) == "\U0001f7e2")
        pass_counts[name] = f"**{green}/{total}**"

    # Target columns use visual width. Floor at 2 so a single emoji always fits.
    col_widths = {}
    for name in target_names:
        col_widths[name] = max(len(name), len(pass_counts[name]), 2)

    # Per-test failure count
    num_targets = len(target_names)
    test_failures = {}
    for tid in test_ids:
        failed = sum(1 for name in target_names if targets[name].get(tid) != "\U0001f7e2")
        test_failures[tid] = str(failed)

    stats_width = max(len("failures"), max(len(v) for v in test_failures.values()))

    def pad(text, width):
        """Center-pad text to width."""
        return text.center(width)

    # Build markdown table
    lines = []

    # Header
    header = f"| {pad('test_id', id_width)} | {pad('failures', stats_width)} |"
    for name in target_names:
        header += f" {pad(name, col_widths[name])} |"
    lines.append(header)

    # Alignment row
    align = f"| {'-' * id_width} | :{'-' * (stats_width - 2)}: |"
    for name in target_names:
        w = col_widths[name]
        align += f" :{'-' * (w - 2)}: |"
    lines.append(align)

    # Data rows
    for tid in test_ids:
        row = f"| {tid:<{id_width}} | {pad(test_failures[tid], stats_width)} |"
        for name in target_names:
            symbol = targets[name].get(tid, NOT_PRESENT)
            # Emoji renders as 2 columns; pad the remaining visual width
            padding = col_widths[name] - 2
            left = padding // 2
            right = padding - left
            row += f" {' ' * left}{symbol}{' ' * right} |"
        lines.append(row)

    # Repeat header before summary row
    repeat_header = f"| {pad('test_id', id_width)} | {pad('failures', stats_width)} |"
    for name in target_names:
        repeat_header += f" {pad(name, col_widths[name])} |"
    lines.append(repeat_header)

    # Summary row
    summary = f"| {summary_label:<{id_width}} | {pad('', stats_width)} |"
    for name in target_names:
        summary += f" {pad(pass_counts[name], col_widths[name])} |"
    lines.append(summary)

    output = "\n".join(lines) + "\n"

    out_path = os.path.join(folder, "summary-table.md")
    with open(out_path, "w") as f:
        f.write(output)

    print(f"Written {out_path} ({len(target_names)} targets, {len(test_ids)} tests)")


if __name__ == "__main__":
    main()
