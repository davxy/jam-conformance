#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: $0 <folder>"
    exit 1
fi

FOLDER="$1"

if [ ! -d "$FOLDER" ]; then
    echo "Error: Folder '$FOLDER' does not exist"
    exit 1
fi

FOLDER=$(realpath "$FOLDER")

SCRIPT_DIR=$(dirname "$(realpath "$0")")

# Create output folder
mkdir -p output

# Find all subfolders containing report.bin
find "$FOLDER" -name "report.bin" -type f | while read -r report_bin; do
    subfolder_path=$(dirname "$report_bin")
    subfolder_name=$(basename "$subfolder_path")
    
    output_dir="output/$subfolder_name"
    mkdir -p "$output_dir"
    
    "$SCRIPT_DIR/decode.py" "$report_bin" > "$output_dir/report.json"
    
    cp "$report_bin" "$output_dir/"
    
    echo "Processed: $subfolder_path -> $output_dir"
done

echo "Processing complete. Results in output/ folder."
