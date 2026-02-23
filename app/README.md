# JAM Conformance Fuzzer Web App

Web UI for running fuzzing sessions against JAM implementations. The app wraps
`scripts/fuzz-workflow.py`, launching it as a subprocess per session and
streaming its output to the browser in real time via WebSocket.

## Prerequisites

- Python 3.10+
- The `polkajam-fuzz` repo cloned locally (the fuzzer itself, built via cargo)
- Rust toolchain (cargo) -- `fuzz-workflow.py` builds and runs the fuzzer with `cargo run`
- Docker (only needed for targets that use container images, e.g. boka, turbojam, pyjamaz)

## Setup

```bash
cd app
pip install -r requirements.txt
```

This installs `fastapi` and `uvicorn[standard]`.

## Running

```bash
POLKAJAM_FUZZ_DIR=/path/to/polkajam-fuzz python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in a browser.

The server will refuse to start if `POLKAJAM_FUZZ_DIR` is not set, or if
`scripts/targets.json` or `scripts/fuzz-workflow.py` are missing from the
repo.

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POLKAJAM_FUZZ_DIR` | yes | -- | Path to the polkajam-fuzz repository |
| `JAM_FUZZ_SESSIONS_DIR` | no | `./sessions` | Directory where session artifacts are stored |

Each spawned subprocess also receives `JAM_FUZZ_SESSION_ID` and
`JAM_FUZZ_MAX_STEPS`, set by the app based on the request parameters.
All other `JAM_FUZZ_*` variables from the server's environment are inherited
by subprocesses (e.g. `JAM_FUZZ_SEED`, `JAM_FUZZ_STEP_PERIOD`).

## Usage

1. Select a target implementation from the dropdown (populated from
   `scripts/targets.json`).
2. Set the max steps (default: 1,000,000). Use a small value like 100 for
   quick tests.
3. Click **Start Fuzzing**. The log viewer will connect automatically and
   show the workflow output (building the fuzzer, downloading the target,
   starting the run).
4. Once the fuzzer is running, use the **fuzzer** and **target** buttons
   above the log viewer to switch to those log streams.
5. The sessions table (refreshed every 5 seconds) shows all sessions with
   their status. Click **Stop** on a running session to terminate it, or
   **Logs** to view its output.
6. Multiple sessions can run concurrently -- each gets its own session
   directory, log files, and unix socket.

## Session artifacts

Each session creates a directory under the sessions base path:

```
sessions/<session_id>/
  workflow.log                       # stdout/stderr of fuzz-workflow.py
  logs/
    fuzzer_<target>.log              # polkajam-fuzz output
    target_<target>.log              # target implementation output
  trace/                             # collected traces (binary)
```

Sessions are tracked in memory only. Restarting the server loses the session
list, but the files on disk remain.

## Stopping sessions

The stop endpoint sends `SIGTERM` to the entire process group (the workflow
script and all its children: the target binary, cargo/fuzzer). If the
processes don't exit within 2 seconds, `SIGKILL` is sent. This ensures
no orphaned processes are left behind.

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve the web UI |
| `GET` | `/api/targets` | List available targets from `targets.json` |
| `POST` | `/api/fuzz` | Start a session. Body: `{"target": "boka", "max_steps": 1000000}` |
| `GET` | `/api/sessions` | List all sessions |
| `GET` | `/api/sessions/{id}` | Single session detail (includes available log files) |
| `POST` | `/api/sessions/{id}/stop` | Stop a running session |
| `WS` | `/ws/logs/{id}?log=workflow\|fuzzer\|target` | Stream log output in real time |

The WebSocket sends JSON messages with an `event` field:

- `{"event": "waiting", "message": "..."}` -- log file not yet created (cargo build in progress)
- `{"event": "log", "data": "..."}` -- a line of log output
- `{"event": "done", "status": "completed", "return_code": 0}` -- process finished
- `{"event": "error", "message": "..."}` -- something went wrong

## Troubleshooting

**Server won't start: "POLKAJAM_FUZZ_DIR is not set"**
Export the variable pointing to your local polkajam-fuzz checkout.

**Session stays "running" but no fuzzer log appears**
The first run triggers a cargo build of `polkajam-fuzz`, which can take
several minutes. Watch the workflow log -- it shows build progress. The
WebSocket waits up to 5 minutes for log files to appear.

**Session fails immediately**
Check the workflow log. Common causes: the target binary isn't available
(needs download), Docker isn't running (for container-based targets), or
the cargo build failed.

**Orphaned processes after server crash**
If the server is killed without graceful shutdown, subprocess trees may
survive. Find them with `ps aux | grep fuzz-workflow` or
`ps aux | grep polkajam-fuzz` and kill manually.
