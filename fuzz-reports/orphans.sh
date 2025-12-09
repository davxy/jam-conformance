#!/bin/bash

folder="${1:-.}"

find "$folder" -type f -name "*.bin" | while IFS= read -r binfile; do
    jsonfile="${binfile%.bin}.json"
    if [[ ! -f "$jsonfile" ]]; then
        echo "Removing orphan .bin file: $binfile"
        rm "$binfile"
    fi
done

