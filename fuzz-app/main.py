import asyncio
import io
import json
import os
import random
import re
import signal
import sys
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Resolve paths relative to the repo root (one level up from app/).
APP_DIR = Path(__file__).resolve().parent
REPO_DIR = APP_DIR.parent
SCRIPTS_DIR = REPO_DIR / "scripts"
TARGETS_JSON = SCRIPTS_DIR / "targets.json"
FUZZ_WORKFLOW = SCRIPTS_DIR / "fuzz-workflow.py"

# Where sessions are stored. Defaults to ./sessions relative to cwd,
# same as fuzz-workflow.py does.
SESSIONS_BASE = Path(os.environ.get("JAM_FUZZ_SESSIONS_DIR", Path.cwd() / "sessions"))

STEP_RE = re.compile(r'\[STEP (\d{8})\]')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}')


def validate_environment():
    fuzz_bin = os.environ.get("POLKAJAM_FUZZ_BIN")
    if not fuzz_bin:
        print("Error: POLKAJAM_FUZZ_BIN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    bin_path = Path(fuzz_bin)
    if not bin_path.is_file():
        print(f"Error: POLKAJAM_FUZZ_BIN '{fuzz_bin}' is not a valid file.", file=sys.stderr)
        sys.exit(1)
    if not os.access(bin_path, os.X_OK):
        print(f"Error: POLKAJAM_FUZZ_BIN '{fuzz_bin}' is not executable.", file=sys.stderr)
        sys.exit(1)
    if not TARGETS_JSON.exists():
        print(f"Error: targets.json not found at {TARGETS_JSON}", file=sys.stderr)
        sys.exit(1)
    if not FUZZ_WORKFLOW.exists():
        print(f"Error: fuzz-workflow.py not found at {FUZZ_WORKFLOW}", file=sys.stderr)
        sys.exit(1)


validate_environment()


# ---------------------------------------------------------------------------
# Session tracking
# ---------------------------------------------------------------------------

@dataclass
class FuzzSession:
    session_id: str
    target: str
    max_steps: int
    mode: str = "start"  # "start" or "download"
    status: str = "running"  # running | paused | stopping | completed | failed | stopped
    paused: bool = False
    return_code: Optional[int] = None
    current_step: Optional[int] = None
    start_time: float = field(default_factory=time.time)
    process: Optional[asyncio.subprocess.Process] = None
    pgid: Optional[int] = None


sessions: dict[str, FuzzSession] = {}


def generate_session_id() -> str:
    sid = str(int(time.time()))
    if sid in sessions:
        suffix = 1
        while f"{sid}_{suffix}" in sessions:
            suffix += 1
        sid = f"{sid}_{suffix}"
    return sid


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="JAM Conformance Fuzzer")


@app.on_event("shutdown")
async def shutdown_all_sessions():
    """Kill all running/paused sessions and their containers on server exit."""
    for s in sessions.values():
        if s.status not in ("running", "paused"):
            continue
        # Kill the process group.
        if s.pgid is not None:
            try:
                os.killpg(s.pgid, signal.SIGKILL)
            except OSError:
                pass
        # Stop the target container (best-effort, don't wait long).
        if s.mode == "start":
            container = f"{s.target}-{s.session_id}"
            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker", "rm", "-f", container,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except Exception:
                pass


@app.get("/")
async def index():
    return FileResponse(
        APP_DIR / "static" / "index.html",
        headers={"Cache-Control": "no-cache"},
    )


# Serve static assets (css, js, etc.) if any are added later.
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/api/targets")
async def get_targets():
    data = json.loads(TARGETS_JSON.read_text())
    targets = []
    for name, meta in data.items():
        targets.append({
            "name": name,
            "gp_version": meta.get("gp_version"),
            "has_image": "image" in meta,
            "has_repo": "repo" in meta,
        })
    return targets


class FuzzRequest(BaseModel):
    target: str
    max_steps: int = 1000000
    seed: Optional[int] = None
    max_mutations: int = 3
    mutation_ratio: float = 0.1
    safrole: bool = False
    mode: str = "start"  # "start" or "download"


@app.post("/api/fuzz")
async def start_fuzz(req: FuzzRequest):
    if req.mode not in ("start", "download"):
        return JSONResponse({"error": f"Invalid mode: {req.mode}"}, status_code=400)

    # Validate target exists.
    data = json.loads(TARGETS_JSON.read_text())
    if req.target not in data:
        return JSONResponse({"error": f"Unknown target: {req.target}"}, status_code=400)

    sid = generate_session_id()
    session_dir = SESSIONS_BASE / sid
    session_dir.mkdir(parents=True, exist_ok=True)

    workflow_log = session_dir / "workflow.log"

    seed = req.seed if req.seed is not None else random.randint(0, 2**32 - 1)

    # Safrole mode: inhibit mutations.
    if req.safrole:
        req.max_mutations = 0
        req.mutation_ratio = 0.0

    env = os.environ.copy()
    env["JAM_FUZZ_SESSION_ID"] = sid
    env["JAM_FUZZ_MAX_STEPS"] = str(req.max_steps)
    env["JAM_FUZZ_SEED"] = str(seed)
    env["JAM_FUZZ_SESSIONS_DIR"] = str(SESSIONS_BASE)
    env["JAM_FUZZ_REMOTE_TIMEOUT"] = "30" #str(2**32 - 1)
    if req.safrole:
        env["JAM_FUZZ_SAFROLE"] = "1"

    log_fh = open(workflow_log, "w")

    args = [
        sys.executable, str(FUZZ_WORKFLOW), "-t", req.target, "--omit-log-tail",
        "--max-mutations", str(req.max_mutations),
        "--mutation-ratio", str(req.mutation_ratio),
    ]
    if req.mode == "start":
        args.append("--skip-get")
    else:
        args.append("--skip-run")

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=log_fh,
        stderr=log_fh,
        env=env,
        start_new_session=True,
    )

    session = FuzzSession(
        session_id=sid,
        target=req.target,
        max_steps=req.max_steps,
        mode=req.mode,
        process=proc,
    )
    # Store the process group id for later killing.
    try:
        session.pgid = os.getpgid(proc.pid)
    except OSError:
        session.pgid = None

    sessions[sid] = session

    # Background tasks: monitor process completion and track step progress.
    asyncio.create_task(_monitor_process(sid, log_fh))
    asyncio.create_task(_track_steps(sid))

    return {"session_id": sid, "status": "running"}


def _log_tail_has_error(path: Path, n: int = 10) -> bool:
    """Check if any of the last *n* lines of a log file contain 'Error'."""
    try:
        tail, _ = _read_tail(path, n)
        return any("Error" in line for line in tail)
    except (OSError, ValueError):
        return False


async def _monitor_process(sid: str, log_fh):
    session = sessions.get(sid)
    if not session or not session.process:
        return
    try:
        rc = await session.process.wait()
        session.return_code = rc
        if session.status == "stopping":
            session.status = "stopped"
        elif rc != 0:
            session.status = "failed"
        else:
            # Check the fuzzer log tail for errors.
            fuzzer_log = _resolve_log_path(sid, session.target, "fuzzer")
            if await asyncio.to_thread(_log_tail_has_error, fuzzer_log):
                session.status = "failed"
            else:
                session.status = "downloaded" if session.mode == "download" else "completed"
    except Exception:
        if session.status == "stopping":
            session.status = "stopped"
        else:
            session.status = "failed"
    finally:
        try:
            log_fh.close()
        except Exception:
            pass


async def _track_steps(sid: str):
    """Tail the fuzzer log and extract the current step number."""
    session = sessions.get(sid)
    if not session:
        return
    log_path = _resolve_log_path(sid, session.target, "fuzzer")

    # Wait for the fuzzer log to appear.
    while not log_path.exists():
        if session.status not in ("running", "paused", "stopping"):
            return
        await asyncio.sleep(2.0)

    with open(log_path, "r") as fh:
        while True:
            line = fh.readline()
            if line:
                m = STEP_RE.search(line)
                if m:
                    session.current_step = int(m.group(1))
            else:
                if session.status not in ("running", "paused", "stopping"):
                    # Final flush.
                    while True:
                        line = fh.readline()
                        if not line:
                            break
                        m = STEP_RE.search(line)
                        if m:
                            session.current_step = int(m.group(1))
                    return
                await asyncio.sleep(0.5)


@app.get("/api/sessions")
async def list_sessions():
    result = []
    for s in sessions.values():
        result.append(_session_summary(s))
    return result


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    s = sessions.get(session_id)
    if not s:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    info = _session_summary(s)

    # List available log files.
    logs_dir = SESSIONS_BASE / session_id / "logs"
    log_files = []
    if logs_dir.is_dir():
        for f in sorted(logs_dir.iterdir()):
            if f.is_file():
                log_files.append(f.name)
    info["log_files"] = log_files
    return info


def _session_summary(s: FuzzSession) -> dict:
    report_dir = SESSIONS_BASE / s.session_id / "report"
    return {
        "session_id": s.session_id,
        "target": s.target,
        "max_steps": s.max_steps,
        "mode": s.mode,
        "status": s.status,
        "paused": s.paused,
        "return_code": s.return_code,
        "current_step": s.current_step,
        "start_time": s.start_time,
        "has_report": report_dir.is_dir(),
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    s = sessions.get(session_id)
    if not s:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    if s.status in ("running", "paused", "stopping"):
        return JSONResponse({"error": "Cannot remove a running session (stop it first)"}, status_code=400)
    del sessions[session_id]
    return {"session_id": session_id, "removed": True}


@app.get("/api/sessions/{session_id}/report")
async def download_report(session_id: str):
    s = sessions.get(session_id)
    if not s:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    report_dir = SESSIONS_BASE / session_id / "report"
    if not report_dir.is_dir():
        return JSONResponse({"error": "No report available"}, status_code=404)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(report_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(report_dir))
    buf.seek(0)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="report-{session_id}.zip"'},
    )


@app.post("/api/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    s = sessions.get(session_id)
    if not s:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    if s.status not in ("running", "paused"):
        return JSONResponse({"error": f"Session is not running (status={s.status})"}, status_code=400)

    s.status = "stopping"
    s.paused = False

    killed = False
    # Try SIGTERM on the process group first.
    if s.pgid is not None:
        try:
            os.killpg(s.pgid, signal.SIGTERM)
        except OSError:
            pass

    # Wait up to 2 seconds, then SIGKILL.
    try:
        await asyncio.wait_for(s.process.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        if s.pgid is not None:
            try:
                os.killpg(s.pgid, signal.SIGKILL)
                killed = True
            except OSError:
                pass
        try:
            s.process.kill()
            killed = True
        except OSError:
            pass

    # Final status transition (stopping -> stopped) is handled by _monitor_process.
    return {"session_id": session_id, "status": "stopping", "killed": killed}


@app.post("/api/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    s = sessions.get(session_id)
    if not s:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    if s.status not in ("running", "paused"):
        return JSONResponse({"error": f"Session is not running (status={s.status})"}, status_code=400)

    container = f"{s.target}-{session_id}"

    if s.paused:
        # Resume: unpause container first, then SIGCONT the process group.
        proc = await asyncio.create_subprocess_exec(
            "docker", "unpause", container,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            return JSONResponse(
                {"error": f"docker unpause failed: {stderr.decode().strip()}"},
                status_code=500,
            )
        if s.pgid is not None:
            try:
                os.killpg(s.pgid, signal.SIGCONT)
            except OSError:
                pass
    else:
        # Pause: SIGSTOP the process group first, then pause container.
        if s.pgid is not None:
            try:
                os.killpg(s.pgid, signal.SIGSTOP)
            except OSError:
                pass
        proc = await asyncio.create_subprocess_exec(
            "docker", "pause", container,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            # Roll back: resume the process group since docker pause failed.
            if s.pgid is not None:
                try:
                    os.killpg(s.pgid, signal.SIGCONT)
                except OSError:
                    pass
            return JSONResponse(
                {"error": f"docker pause failed: {stderr.decode().strip()}"},
                status_code=500,
            )

    s.paused = not s.paused
    s.status = "paused" if s.paused else "running"
    return {"session_id": session_id, "status": s.status}


# ---------------------------------------------------------------------------
# WebSocket log streaming
# ---------------------------------------------------------------------------

def _read_tail(path: Path, n: int) -> tuple[list[str], int]:
    """Read the last *n* lines of a file efficiently (from the end).

    Returns (lines, end_position) so the caller can seek to end_position
    and continue tailing for new content.
    """
    with open(path, "rb") as f:
        f.seek(0, 2)
        end_pos = f.tell()
        if end_pos == 0:
            return [], 0
        buf = b""
        chunk_size = 8192
        pos = end_pos
        # Read backwards until we have enough newlines.
        while pos > 0:
            read_size = min(chunk_size, pos)
            pos -= read_size
            f.seek(pos)
            buf = f.read(read_size) + buf
            if buf.count(b"\n") > n:
                break
        lines = buf.decode("utf-8", errors="replace").splitlines()
        return lines[-n:], end_pos


def _read_fuzzer_config(path: Path) -> list[str]:
    """Read configuration lines from the top of the fuzzer log.

    These are the lines before the first date-prefixed log entry.
    """
    lines = []
    try:
        with open(path, "r") as f:
            for line in f:
                if DATE_RE.match(line):
                    break
                lines.append(line.rstrip("\n"))
    except OSError:
        pass
    return lines


@app.websocket("/ws/logs/{session_id}")
async def ws_logs(ws: WebSocket, session_id: str):
    await ws.accept()

    s = sessions.get(session_id)
    if not s:
        await ws.send_json({"event": "error", "message": "Session not found"})
        await ws.close()
        return

    log_type = ws.query_params.get("log", "workflow")
    log_path = _resolve_log_path(session_id, s.target, log_type)

    try:
        # Wait for the log file to appear (cargo build can be slow).
        waited = 0.0
        timeout = 300.0  # 5 minutes
        while not log_path.exists():
            if waited >= timeout:
                await ws.send_json({"event": "error", "message": f"Log file did not appear within {timeout}s"})
                await ws.close()
                return
            await ws.send_json({"event": "waiting", "message": f"Waiting for {log_path.name}..."})
            await asyncio.sleep(2.0)
            waited += 2.0

        # Send the last TAIL_LINES lines as a batch, then tail new ones.
        TAIL_LINES = 1000
        tail, end_pos = await asyncio.to_thread(_read_tail, log_path, TAIL_LINES)
        if tail:
            await ws.send_json({"event": "history", "lines": tail})

        # For workflow logs, inject the fuzzer config header once it's available.
        fuzzer_config_sent = log_type != "workflow"
        fuzzer_log_path = _resolve_log_path(session_id, s.target, "fuzzer")

        with open(log_path, "r") as fh:
            fh.seek(end_pos)

            while True:
                if not fuzzer_config_sent and fuzzer_log_path.exists():
                    config = await asyncio.to_thread(_read_fuzzer_config, fuzzer_log_path)
                    if config:
                        await ws.send_json({"event": "config", "lines": config})
                    fuzzer_config_sent = True

                line = fh.readline()
                if line:
                    await ws.send_json({"event": "log", "data": line.rstrip("\n")})
                else:
                    if s.status not in ("running", "paused", "stopping"):
                        # Flush remaining.
                        while True:
                            line = fh.readline()
                            if not line:
                                break
                            await ws.send_json({"event": "log", "data": line.rstrip("\n")})
                        await ws.send_json({
                            "event": "done",
                            "status": s.status,
                            "return_code": s.return_code,
                        })
                        break
                    await asyncio.sleep(0.3)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"event": "error", "message": str(e)})
            await ws.close()
        except Exception:
            pass


def _resolve_log_path(session_id: str, target: str, log_type: str) -> Path:
    session_dir = SESSIONS_BASE / session_id
    if log_type == "workflow":
        return session_dir / "workflow.log"
    elif log_type == "fuzzer":
        return session_dir / "logs" / f"fuzzer_{target}.log"
    elif log_type == "target":
        return session_dir / "logs" / f"target_{target}.log"
    else:
        return session_dir / "workflow.log"
