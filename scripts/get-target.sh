#!/usr/bin/env bash
# 
# Quick one-liner to download a target

./fuzz-workflow.py -t "$1" --skip-run --skip-report --parallel
