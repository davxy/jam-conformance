#!/bin/bash

export POLKAJAM_FUZZ_DIR="/mnt/ssd/develop/jam/polkajam/crates/polkajam-fuzz"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
