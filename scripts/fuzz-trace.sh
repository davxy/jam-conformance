#!/usr/bin/env bash

# Quick one-liner to execute a trace workflow with a few targets and publish the corresponding reports.

JAM_FUZZ_TARGETS=$1 time ./fuzz-workflow.py -t all --skip-get --report-publish --source trace --omit-log-tail