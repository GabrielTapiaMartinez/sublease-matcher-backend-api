#!/usr/bin/env python3
"""[db-smoke] Smoke tests that exercise the SQLAlchemy storage backend."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from contextlib import suppress
from getpass import getuser
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

DEFAULT_DB_NAME = "sublease_dev_sql"
DEFAULT_PYTHONPATH = "src:../sublease-matcher-backend-core/src"


def _default_database_url(env: dict[str, str]) -> str:
    user = env.get("USER") or getuser()
    return f"postgresql+psycopg://{user}@localhost:5432/{DEFAULT_DB_NAME}"


def _ensure_database_url(env: dict[str, str]) -> str:
    database_url = env.get("SM_DATABASE_URL")
    if not database_url:
        database_url = _default_database_url(env)
        env["SM_DATABASE_URL"] = database_url
    return database_url


def _log(message: str) -> None:
    print(f"[db-smoke] {message}")


def _run(cmd: list[str], env: dict[str, str]) -> None:
    subprocess.run(cmd, check=True, env=env)


def _http_get(path: str, headers: dict[str, str] | None = None) -> bytes:
    req = Request(f"http://127.0.0.1:8000{path}", headers=headers or {})
    with urlopen(req, timeout=5) as resp:  # noqa: S310
        if resp.status != 200:
            raise RuntimeError(f"Unexpected status {resp.status} for {path}")
        return resp.read()


def _wait_for_server(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with suppress(Exception):
            _http_get("/healthz")
            return
        time.sleep(0.5)
    raise RuntimeError("Server did not become ready on port 8000")


def seed_demo_data(env: dict[str, str]) -> None:
    script_dir = Path(__file__).resolve().parent
    seed_script = script_dir / "seed_sql.py"
    _log("Seeding deterministic SQL data...")
    _run([sys.executable, str(seed_script)], env=env)


def main() -> None:
    env = os.environ.copy()
    database_url = _ensure_database_url(env)
    if not database_url:
        raise SystemExit("SM_DATABASE_URL must be set for smoke_sql.py")
    env["PYTHONPATH"] = env.get("PYTHONPATH", DEFAULT_PYTHONPATH)
    env.setdefault("SM_STORAGE", "sqlalchemy")
    _log(f"Using database URL: {database_url}")

    _log("Applying migrations...")
    _run(["python3", "-m", "alembic", "upgrade", "head"], env=env)
    _log("Seeding demo data...")
    seed_demo_data(env)

    server_env = env.copy()
    server_cmd = [
        "uvicorn",
        "--app-dir",
        "src",
        "sublease_matcher.api.main:app",
        "--reload",
    ]
    _log("Starting API server (SQL backend)...")
    proc = subprocess.Popen(  # noqa: S603
        server_cmd,
        env=server_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,
    )
    try:
        _wait_for_server()
        _log("Server is up. Running smoke requests...")
        _http_get("/healthz")
        _log("healthz OK")
        _http_get("/seekers/me/profile", headers={"X-Debug-User-Id": "user-1"})
        _log("seekers profile OK")
        _http_get("/listings/mine", headers={"X-Debug-User-Id": "user-1"})
        _log("listings mine OK")
        _http_get("/matches", headers={"X-Debug-User-Id": "user-1"})
        _log("matches OK")
    finally:
        _log("Stopping API server...")
        with suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            with suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)


if __name__ == "__main__":
    try:
        main()
    except URLError as err:  # pragma: no cover - smoke helper
        print(f"HTTP error during smoke test: {err}", file=sys.stderr)
        raise SystemExit(1) from err
    except Exception as exc:  # pragma: no cover
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise
