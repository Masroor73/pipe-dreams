"""Start the Pipe Dreams API and frontend with one command.

Usage (from the repo root):
    python scripts/start.py                     # API + frontend on synthetic artifacts
    python scripts/start.py --artifacts artifacts/final-freeze-v1
    python scripts/start.py --fixtures          # frontend only, built-in fixtures, no API
    python scripts/start.py --no-open           # don't open a browser tab

First run creates backend/.venv and installs backend + frontend dependencies.
Press Ctrl+C to stop both servers.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
FRONTEND = REPO_ROOT / "frontend"
VENV = BACKEND / ".venv"
IS_WINDOWS = os.name == "nt"
VENV_PYTHON = VENV / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def log(msg: str) -> None:
    print(f"[start] {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"[start] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def run(cmd: list[str], cwd: Path) -> None:
    log(" ".join(str(c) for c in cmd))
    if subprocess.run(cmd, cwd=cwd).returncode != 0:
        fail(f"command failed: {' '.join(str(c) for c in cmd)}")


def find_python311() -> list[str]:
    """Return a command that runs Python 3.11 to create the venv."""
    candidates = [["py", "-3.11"]] if IS_WINDOWS else [["python3.11"]]
    candidates.append([sys.executable])
    for cmd in candidates:
        if shutil.which(cmd[0]) is None and not Path(cmd[0]).exists():
            continue
        out = subprocess.run(
            cmd + ["-c", "import sys; print(sys.version_info[:2])"],
            capture_output=True,
            text=True,
        )
        if out.returncode == 0 and "(3, 11)" in out.stdout:
            return cmd
    fail("Python 3.11 not found (TECH_STACK.md requires 3.11). Install it, then re-run.")
    return []  # unreachable


def ensure_backend() -> None:
    if not VENV_PYTHON.exists():
        log("creating backend/.venv (first run)")
        run(find_python311() + ["-m", "venv", str(VENV)], REPO_ROOT)
    has_deps = subprocess.run(
        [str(VENV_PYTHON), "-c", "import fastapi, uvicorn, pandas, pyarrow, shapely"],
        capture_output=True,
    ).returncode == 0
    if not has_deps:
        log("installing backend dependencies")
        run([str(VENV_PYTHON), "-m", "pip", "install", "-q", "-e", f"{BACKEND}[dev]"], REPO_ROOT)


def npm_cmd() -> str:
    npm = shutil.which("npm")
    if npm is None:
        fail("npm not found. Install Node.js 20+.")
    return npm


def ensure_frontend() -> None:
    if not (FRONTEND / "node_modules").exists():
        log("installing frontend dependencies (first run)")
        run([npm_cmd(), "install"], FRONTEND)


def port_free(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def spawn(cmd: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    kwargs: dict = {"cwd": cwd, "env": env}
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if IS_WINDOWS:
        # Kill the whole tree (npm -> node -> vite, python -> uvicorn worker).
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def wait_for(url: str, proc: subprocess.Popen, timeout_s: float) -> dict | None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc.poll() is not None:
            return None
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                body = resp.read().decode("utf-8", "replace")
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    return {}
        except OSError:
            time.sleep(0.5)
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Start the Pipe Dreams API and frontend.")
    ap.add_argument("--artifacts", help="artifact dir for the API (default: artifacts/synthetic)")
    ap.add_argument("--fixtures", action="store_true", help="frontend only, using built-in fixtures")
    ap.add_argument("--api-port", type=int, default=8000)
    ap.add_argument("--web-port", type=int, default=5173)
    ap.add_argument("--no-open", action="store_true", help="don't open a browser tab")
    args = ap.parse_args()

    ports = [args.web_port] if args.fixtures else [args.api_port, args.web_port]
    busy = [p for p in ports if not port_free(p)]
    if busy:
        fail(
            f"port(s) {busy} already in use (another dev server running?). "
            "Stop it, or pass --api-port/--web-port."
        )

    web_url = f"http://localhost:{args.web_port}"
    api_url = f"http://localhost:{args.api_port}"
    procs: list[subprocess.Popen] = []

    if not args.fixtures:
        ensure_backend()
    ensure_frontend()

    try:
        if not args.fixtures:
            api_env = os.environ.copy()
            api_env["PIPE_DREAMS_CORS_ORIGINS"] = json.dumps([web_url, f"http://127.0.0.1:{args.web_port}"])
            if args.artifacts:
                api_env["PIPE_DREAMS_ARTIFACT_DIR"] = args.artifacts
            log(f"starting API on {api_url}")
            api = spawn(
                [str(VENV_PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(args.api_port)],
                BACKEND,
                api_env,
            )
            procs.append(api)
            health = wait_for(f"{api_url}/api/health", api, 60)
            if health is None:
                fail("API did not start. See its output above.")
            log(f"API health: {health}")
            if health.get("status") != "ok":
                log("WARNING: API is degraded (artifacts missing or invalid); pages will show 'Artifacts unavailable'.")

        web_env = os.environ.copy()
        web_env["VITE_USE_FIXTURES"] = "true" if args.fixtures else "false"
        web_env["VITE_API_BASE_URL"] = api_url
        log(f"starting frontend on {web_url} ({'fixtures' if args.fixtures else 'live API'})")
        web = spawn(
            [npm_cmd(), "run", "dev", "--", "--port", str(args.web_port), "--strictPort"],
            FRONTEND,
            web_env,
        )
        procs.append(web)
        if wait_for(web_url, web, 90) is None:
            fail("frontend did not start. See its output above.")

        log(f"ready: {web_url}   (Ctrl+C to stop)")
        if not args.no_open:
            webbrowser.open(web_url)

        while all(p.poll() is None for p in procs):
            time.sleep(1)
        log("a server exited; shutting down the other.")
    except KeyboardInterrupt:
        log("stopping...")
    finally:
        for p in procs:
            stop(p)


if __name__ == "__main__":
    main()
