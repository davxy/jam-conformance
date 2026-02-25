# JAM Conformance Fuzzer Web App

Web UI for running fuzzing sessions against JAM implementations. The app wraps
`scripts/fuzz-workflow.py`, launching it as a subprocess per session and
streaming its output to the browser in real time via WebSocket.

## Prerequisites

- Python 3.10+
- The `polkajam-fuzz` binary (prebuilt or compiled from source)
- Docker (only needed for targets that use container images, e.g. boka, turbojam, pyjamaz)

## Install

```bash
./install.sh
```

This creates a virtual environment at `~/.local/pip/fuzz-app` and installs
the dependencies (`fastapi`, `uvicorn[standard]`, `jam-types`).

## Configuration

The app reads defaults from `config.json` in the app directory. Environment
variables override config file values, which override hard-coded defaults.

```json
{
  "polkajam_fuzz_bin": "/path/to/polkajam-fuzz",
  "scripts_dir": "/path/to/scripts",
  "sessions_dir": "./sessions",
  "max_steps": 1000000,
  "max_mutations": 3,
  "mutation_ratio": 0.1,
  "profile": "full",
  "fuzzy_profile": "rand",
  "safrole": false,
  "skip_slots": false
}
```

`polkajam_fuzz_bin` and `scripts_dir` are required -- the app will refuse
to start if either is missing (empty or unset in both config and environment).
`scripts_dir` must point to the directory containing `fuzz-workflow.py` and
`targets.json`.

The remaining fields set the default values for the UI configuration panel.
They are served to the frontend via `GET /api/defaults` on page load.

### Environment variable overrides

Any config value can be overridden by setting the corresponding environment
variable. Environment variables take precedence over `config.json`.

| Config key | Environment variable | Description |
|------------|---------------------|-------------|
| `polkajam_fuzz_bin` | `POLKAJAM_FUZZ_BIN` | Path to the polkajam-fuzz binary |
| `scripts_dir` | `JAM_FUZZ_SCRIPTS_DIR` | Path to the scripts directory |
| `sessions_dir` | `JAM_FUZZ_SESSIONS_DIR` | Session artifacts directory (default: `./sessions`) |
| `max_steps` | `JAM_FUZZ_MAX_STEPS_DEFAULT` | Default max steps |
| `max_mutations` | `JAM_FUZZ_MAX_MUTATIONS_DEFAULT` | Default max mutations |
| `mutation_ratio` | `JAM_FUZZ_MUTATION_RATIO_DEFAULT` | Default mutation ratio |
| `profile` | `JAM_FUZZ_PROFILE_DEFAULT` | Default profile |
| `fuzzy_profile` | `JAM_FUZZ_FUZZY_PROFILE_DEFAULT` | Default fuzzy profile |
| `safrole` | `JAM_FUZZ_SAFROLE_DEFAULT` | Default safrole toggle |
| `skip_slots` | `JAM_FUZZ_SKIP_SLOTS_DEFAULT` | Default skip-slots toggle |
| -- | `GITHUB_TOKEN` | GitHub token; avoids API rate limits when downloading targets |

Each spawned subprocess also receives `JAM_FUZZ_SESSION_ID`,
`JAM_FUZZ_MAX_STEPS`, `JAM_FUZZ_SEED`, and optionally `JAM_FUZZ_SAFROLE`
and `JAM_FUZZ_SKIP_SLOTS`, set by the app based on the request parameters.

## Start

```bash
./start.sh
```

If `polkajam_fuzz_bin` is set in `config.json`, no environment variable
is needed. Otherwise pass it on the command line:

```bash
POLKAJAM_FUZZ_BIN=/path/to/polkajam-fuzz ./start.sh
```

Then open `http://localhost:8000` in a browser.

## Interface

The UI is a single page with three areas: Configuration, Bulk Operations,
and the Sessions table. A collapsible log viewer appears below the table
when a session is selected.

### Configuration

The top panel contains all parameters for launching a fuzzing session:

- **Target** -- dropdown populated from `scripts/targets.json`, sorted
  alphabetically. An `-- all --` option launches one session per target
  in parallel.
- **Max Steps** -- number of fuzzing steps before the session ends.
- **Seed** -- RNG seed for reproducibility. A reload button next to the
  field generates a new random value. The seed is preserved after starting
  a session so it can be reused.
- **Profile** -- the work-report profile passed to the fuzzer
  (`full`, `fuzzy`, `empty`, `preimages`, `storage`). Default: `full`.
- **Fuzzy Profile** -- sub-profile for the fuzzy service
  (`rand`, `full`, `empty`, `mem-check`, `storage`, `preimages`,
  `management`, `services`). Default: `rand`. Only meaningful when
  Profile is set to `fuzzy`.
- **Max Mutations** / **Mutation Ratio** -- control how aggressively the
  fuzzer mutates state between steps.
- **Safrole** -- enables safrole mode. When checked, Max Mutations and
  Mutation Ratio are forced to 0 and their inputs are disabled.
- **Skip Slots** -- enables slot skipping in the fuzzer.

Two buttons sit below the parameters:

- **Start** -- launches the target container and begins fuzzing.
- **Download** -- downloads/builds the target binary without running a
  fuzzing session.

### Bulk Operations

A second panel with buttons that act on all sessions at once:

- **Stop** -- stops all running/downloading sessions.
- **Pause** -- pauses all running sessions (sends SIGSTOP to the process
  group and pauses the Docker container).
- **Resume** -- resumes all paused sessions.
- **Clean** -- removes all finished/stopped/failed sessions from the list.

### Sessions table

Each row represents one session. Columns: Session ID, Target, Started,
Status, and Actions. Click any column header to sort by that column; click
again to reverse the order. A small arrow indicates the active sort
direction. The table refreshes every second.

The Status column shows the current state (`running`, `downloading`,
`paused`, `stopping`, `completed`, `downloaded`, `failed`, `stopped`) and,
for running sessions, the current step count (e.g. `running step 1234 / 1000000`).

Clicking a session row does two things:

1. Populates the Configuration panel with the parameters that were used to
   start that session, so the same config can be reused or tweaked for a
   new run.
2. Toggles the log viewer for that session. Click the same row again to
   collapse it.

### Per-session actions

Each row has action buttons depending on the session state:

- **Pause / Resume** -- available for running sessions started with
  "Start" (not "Download"). Sends SIGSTOP/SIGCONT to the process group
  and pauses/unpauses the Docker container.
- **Stop** -- sends SIGTERM to the process group, waits 2 seconds, then
  SIGKILL if still alive. Works for both running and downloading sessions.
- **Report** -- appears after a session completes successfully. Downloads
  a zip archive of the report directory, which contains the conformance
  test results (JSON traces, state diffs, and a summary).
- **Remove** -- removes a finished session from the list (does not delete
  files on disk).

### Log viewer

When a session row is selected, a log panel appears below the table. Three
buttons switch between log streams:

- **workflow** -- output of `fuzz-workflow.py` itself (build progress,
  target download, container management).
- **fuzzer** -- output of the `polkajam-fuzz` binary (step-by-step
  fuzzing progress, errors, state transitions).
- **target** -- stdout/stderr of the target implementation.

Logs are streamed in real time over a WebSocket connection. The viewer
auto-scrolls to new content. When the session finishes, a status line
is appended. The WebSocket is disconnected when the log panel is collapsed,
so inactive sessions don't consume resources.

## Session artifacts

Each session creates a directory under the sessions base path:

```
sessions/<session_id>/
  workflow.log                       # stdout/stderr of fuzz-workflow.py
  logs/
    fuzzer_<target>.log              # polkajam-fuzz output
    target_<target>.log              # target implementation output
  trace/                             # collected traces (binary)
  report/                            # conformance report (when completed)
```

Sessions are tracked in memory only. Restarting the server loses the session
list, but the files on disk remain.

## Concurrency

Multiple sessions run in parallel without conflict. Each gets its own
session ID, directory under `sessions/`, and unix socket
(`/tmp/jam_fuzz_<session_id>.sock`). Session IDs are unix timestamps with
a `_N` suffix appended on collision, so even simultaneous launches (e.g.
the "all" target option) get unique IDs.

## Troubleshooting

**Server won't start: "POLKAJAM_FUZZ_BIN is not set"**
Export the variable pointing to your polkajam-fuzz binary.

**Session stays "running" but no fuzzer log appears**
The first run triggers a cargo build of `polkajam-fuzz`, which can take
several minutes. Watch the workflow log -- it shows build progress. The
WebSocket waits up to 5 minutes for log files to appear.

**Session fails immediately**
Check the workflow log. Common causes: the target binary isn't available
(needs download), Docker isn't running (for container-based targets), or
the cargo build failed.

**HTTP 403 rate limit when downloading targets**
The download fetches release information from the GitHub API. Without
authentication, the limit is 60 requests/hour. Set `GITHUB_TOKEN` to a
personal access token (no scopes needed for public repos) to raise the
limit to 5,000/hour.

**Orphaned processes after server crash**
If the server is killed without graceful shutdown, subprocess trees may
survive. Find them with `ps aux | grep fuzz-workflow` or
`ps aux | grep polkajam-fuzz` and kill manually.
