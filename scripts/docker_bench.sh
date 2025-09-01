#!/usr/bin/env bash
#
# Benchmark friendly container
#
# Benchmark performance optimization parameters:
# nice -n -20: sets highest CPU priority (-20 is highest, 19 is lowest)
# ionice -c1 -n0: sets real-time I/O scheduling class with highest priority
# --cpuset-cpus="0-16": restricts container to use only CPU cores 0-16
# --cpu-shares=2048: sets relative CPU weight (default 1024), higher = more CPU priority

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_SOCK="/tmp/jam_target.sock"

sudo nice -n -20 ionice -c1 -n0 \
docker run --rm -it \
  --cpuset-cpus="0-16" \
  --cpu-shares=2048 \
  -v $CURR_DIR:/benchmark \
  -v /tmp:/tmp \
  --user "$(id -u):$(id -g)" \
  -w /benchmark \
  debian bash
