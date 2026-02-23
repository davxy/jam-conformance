# JAM Conformance Fuzzer Web App

Web UI for running fuzzing sessions against JAM implementations. Wraps the existing `scripts/fuzz-workflow.py` -- the web app launches it as a subprocess and streams its output.

## Structure

```
app/
  main.py              FastAPI backend: endpoints, WebSocket, process management
  static/index.html    Single-page UI (vanilla JS, no build step)
  requirements.txt     fastapi, uvicorn[standard]
```

## How it works

The backend does not implement any fuzzing logic. It launches `scripts/fuzz-workflow.py` as an async subprocess per session, passing configuration through environment variables (`JAM_FUZZ_SESSION_ID`, `JAM_FUZZ_MAX_STEPS`, `JAM_FUZZ_SESSIONS_DIR`). Each subprocess runs in its own process group (`start_new_session=True`) so the entire tree can be killed cleanly.

Target list comes from `scripts/targets.json`, read directly at request time.

## Backend (main.py)

### Session model

In-memory `dict[str, FuzzSession]`. Nothing is persisted across server restarts. Each `FuzzSession` dataclass holds: session ID, target name, max_steps, status (`running`/`completed`/`failed`/`stopped`), return code, asyncio subprocess handle, and process group ID.

Session IDs are unix timestamps as strings, with a `_N` suffix appended on collision.

### Endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | `/` | Serves `static/index.html` |
| GET | `/api/targets` | Reads `scripts/targets.json`, returns name + metadata per target |
| POST | `/api/fuzz` | Body: `{"target": "...", "max_steps": N}`. Launches subprocess, returns `session_id` |
| GET | `/api/sessions` | All sessions with status |
| GET | `/api/sessions/{id}` | Single session + list of log files on disk |
| POST | `/api/sessions/{id}/stop` | SIGTERM to process group, 2s grace, then SIGKILL |
| WS | `/ws/logs/{id}?log=workflow\|fuzzer\|target` | Real-time log streaming |

### Subprocess launch (POST /api/fuzz)

Runs: `python fuzz-workflow.py -t <target> --skip-report`

stdout/stderr are redirected to `sessions/<id>/workflow.log`. An `asyncio.create_task` monitors the process and updates session status on exit.

### WebSocket log streaming

The `?log` query param selects which file to tail:
- `workflow` -- `sessions/<id>/workflow.log` (the script's own stdout: build progress, download, etc.)
- `fuzzer` -- `sessions/<id>/logs/fuzzer_<target>.log` (polkajam-fuzz output)
- `target` -- `sessions/<id>/logs/target_<target>.log` (target implementation output)

The handler polls for the file to appear (2s interval, 5min timeout -- cargo builds are slow), then tails with `readline()` in a loop, sleeping 300ms when no new data. When the process ends, it flushes remaining lines and sends a `done` event.

WebSocket messages are JSON with an `event` field: `waiting`, `log`, `done`, or `error`.

### Process termination

`os.killpg(pgid, SIGTERM)`, wait 2s, `os.killpg(pgid, SIGKILL)`. Using process groups ensures child processes (target binary, cargo/fuzzer) are also terminated.

### Startup validation

`validate_environment()` runs at import time and calls `sys.exit(1)` if `POLKAJAM_FUZZ_DIR` is unset/invalid, or if `targets.json`/`fuzz-workflow.py` are missing.

## Frontend (static/index.html)

Single HTML file, inline `<style>` and `<script>`, no dependencies.

Three sections:
1. **Controls** -- target dropdown (populated from `/api/targets` on load), max steps input, start button
2. **Sessions table** -- polled every 5s from `/api/sessions`, sorted newest first. Stop button for running sessions, Logs button for all.
3. **Log viewer** -- dark `<pre>`-style area connected via WebSocket. Three buttons switch between workflow/fuzzer/target logs for the currently selected session. Auto-scrolls on new lines.

## Concurrency

Multiple sessions run in parallel without conflict. Each gets its own session ID, directory under `sessions/`, and unix socket (`/tmp/jam_fuzz_<session_id>.sock` -- set by fuzz-workflow.py based on the session ID env var).

## Running

```bash
cd app
pip install -r requirements.txt
POLKAJAM_FUZZ_DIR=/path/to/polkajam python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `POLKAJAM_FUZZ_DIR` | yes | Path to the polkajam-fuzz repo (passed through to subprocess) |
| `JAM_FUZZ_SESSIONS_DIR` | no | Override sessions directory (default: `./sessions`) |

The app also passes through to each subprocess: `JAM_FUZZ_SESSION_ID`, `JAM_FUZZ_MAX_STEPS`, and `JAM_FUZZ_SESSIONS_DIR`.

## Files the app depends on (read-only, not owned by app/)

- `scripts/fuzz-workflow.py` -- launched as subprocess
- `scripts/targets.json` -- read for target list
- `scripts/target.py` -- invoked by fuzz-workflow.py to download/run targets
