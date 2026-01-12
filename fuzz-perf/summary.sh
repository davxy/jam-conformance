#!/bin/bash

# Performance table generator for JAM teams
# Groups by test file name and creates tables sorted from fastest to slowest

GP_VERSION=${GP_VERSION:-"0.7.2"}

OUTPUT_DIR="summary"

# Find all team perf directories 
PERF_DIRS=$(find "$GP_VERSION" -type d -not -path "$GP_VERSION" | sort)

if [ -z "$PERF_DIRS" ]; then
    echo "No performance directories found"
    exit 1
fi

# Collect all unique test file names
TEST_FILES=()
for dir in $PERF_DIRS; do
    for json_file in "$dir"/*.json; do
        if [ -f "$json_file" ]; then
            test_name=$(basename "$json_file" .json)
            if [[ ! " ${TEST_FILES[@]} " =~ " ${test_name} " ]]; then
                TEST_FILES+=("$test_name")
            fi
        fi
    done
done

# Create perf directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Process each test file
for test_file in "${TEST_FILES[@]}"; do
    output_file="$OUTPUT_DIR/${test_file}.md"
    
    # Start writing to the output file
    {
        echo "# Performance Results: $test_file"
        echo
        
        # Collect all unique stat keys for this test (excluding specified ones)
        STAT_KEYS=()
        for dir in $PERF_DIRS; do
            json_file="$dir/$test_file.json"
            if [ -f "$json_file" ]; then
                keys=$(jq -r '.stats | keys[]' "$json_file" 2>/dev/null | grep -v -E '^(steps|imported|import_max_step)$')
                for key in $keys; do
                    if [[ ! " ${STAT_KEYS[@]} " =~ " ${key} " ]]; then
                        STAT_KEYS+=("$key")
                    fi
                done
            fi
        done
        
        # Generate table for each stat key
        for stat_key in "${STAT_KEYS[@]}"; do
            echo "## $stat_key"
            echo
            
            # Collect team data for this stat
            declare -a team_data
            
            for dir in $PERF_DIRS; do
                team_name=$(basename "$dir")
                json_file="$dir/$test_file.json"
                
                if [ -f "$json_file" ]; then
                    value=$(jq -r ".stats.\"$stat_key\" // empty" "$json_file" 2>/dev/null)
                    
                    if [ -n "$value" ] && [ "$value" != "null" ]; then
                        team_data+=("$value:$team_name")
                    fi
                fi
            done
            
            # Sort by value (fastest/smallest first)
            if [ ${#team_data[@]} -gt 0 ]; then
                IFS=$'\n' sorted_data=($(printf '%s\n' "${team_data[@]}" | sort -n))
                
                echo "| Team | Value |"
                echo "|------|-------|"
                
                for entry in "${sorted_data[@]}"; do
                    value=$(echo "$entry" | cut -d: -f1)
                    team=$(echo "$entry" | cut -d: -f2)
                    echo "| $team | $value |"
                done
            else
                echo "No data found"
            fi
            
            echo
            unset team_data
        done
        
    } > "$output_file"
    
    echo "Generated: $output_file"
done

echo "Table generation complete!"
