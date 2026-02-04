#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
import difflib

def run_jam_decode(input_type, input_value, type_arg, spec_name=None):
    """Run jam_decode and return the JSON output."""
    cmd = [sys.executable, "-m", "jam_types.scripts.jam_decode"]
    
    if input_type == "data":
        cmd.extend(["-d", input_value])
    elif input_type == "file":
        cmd.extend(["-f", input_value])
    
    cmd.extend(["-t", type_arg])
    
    if spec_name:
        cmd.extend(["-s", spec_name])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running jam_decode: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON output: {e}", file=sys.stderr)
        sys.exit(1)

def colorize_diff_line(line):
    """Add color to diff lines."""
    if line.startswith('+ '):
        return f"\033[32m{line}\033[0m"  # Green for additions
    elif line.startswith('- '):
        return f"\033[31m{line}\033[0m"  # Red for deletions
    elif line.startswith('? '):
        return f"\033[33m{line}\033[0m"  # Yellow for hints
    elif line.startswith('@@'):
        return f"\033[36m{line}\033[0m"  # Cyan for context
    else:
        return line

def print_colored_diff(json1, json2, label1="Input 1", label2="Input 2", verbose=False):
    """Print a colored diff of two JSON objects."""
    # Pretty print JSON with consistent formatting
    json1_str = json.dumps(json1, indent=2)
    json2_str = json.dumps(json2, indent=2)
    
    if verbose:
        # In verbose mode, show full content with inline diff markers
        lines1 = json1_str.splitlines()
        lines2 = json2_str.splitlines()
        
        # Use SequenceMatcher to find differences
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        
        has_diff = False
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Lines are the same, print without markers
                for line in lines1[i1:i2]:
                    print(f"   {line}")
            elif tag == 'delete':
                # Lines only in first file
                has_diff = True
                for line in lines1[i1:i2]:
                    print(colorize_diff_line(f"-  {line}"))
            elif tag == 'insert':
                # Lines only in second file
                has_diff = True
                for line in lines2[j1:j2]:
                    print(colorize_diff_line(f"+  {line}"))
            elif tag == 'replace':
                # Lines differ between files
                has_diff = True
                for line in lines1[i1:i2]:
                    print(colorize_diff_line(f"-  {line}"))
                for line in lines2[j1:j2]:
                    print(colorize_diff_line(f"+  {line}"))
        
        if not has_diff:
            print("No differences found.")
    else:
        # Original behavior - show unified diff
        lines1 = json1_str.splitlines(keepends=True)
        lines2 = json2_str.splitlines(keepends=True)
        
        # Generate unified diff
        diff = difflib.unified_diff(
            lines1, lines2,
            fromfile=label1,
            tofile=label2,
            lineterm=''
        )
        
        # Print with colors
        has_diff = False
        for line in diff:
            has_diff = True
            print(colorize_diff_line(line), end='')
        
        if not has_diff:
            print("No differences found.")

def main():
    parser = argparse.ArgumentParser(
        description="Compare JAM type decodings using jam_decode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  jam_diff -d "0x1234" -d "0x5678" -t Block
  jam_diff -f file1.bin -f file2.bin -t Header
  jam_diff -d "0x1234" -f data.bin -t WorkPackage -s tiny
        """
    )
    
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Show full decoded content with inline diff markers")
    parser.add_argument("-d", "--data", action="append", dest="data_inputs",
                       help="Hex data to decode (can be used up to 2 times)")
    parser.add_argument("-f", "--file", action="append", dest="file_inputs", 
                       help="File containing binary data to decode (can be used up to 2 times)")
    parser.add_argument("-t", "--type", required=True,
                       help="Type name to decode as")
    parser.add_argument("-s", "--spec", 
                       help="Specification name (e.g., 'full', 'tiny')")
    
    args = parser.parse_args()
    
    # Collect all inputs
    inputs = []
    
    if args.data_inputs:
        for data in args.data_inputs:
            inputs.append(("data", data))
    
    if args.file_inputs:
        for file_path in args.file_inputs:
            inputs.append(("file", file_path))
    
    # Validate input count
    if len(inputs) != 2:
        print("Error: Exactly 2 inputs required (combination of -d and -f)", file=sys.stderr)
        sys.exit(1)
    
    # Decode both inputs
    results = []
    labels = []
    
    for i, (input_type, input_value) in enumerate(inputs):
        result = run_jam_decode(input_type, input_value, args.type, args.spec)
        results.append(result)
        
        if input_type == "data":
            labels.append(f"Data: {input_value}")
        else:
            labels.append(f"File: {input_value}")
    
    # Print the diff
    print_colored_diff(results[0], results[1], labels[0], labels[1], args.verbose)

if __name__ == "__main__":
    main()
