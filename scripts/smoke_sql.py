#!/usr/bin/env python3
"""Smoke tests that exercise the SQLAlchemy storage backend."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from contextlib import suppress
from urllib.error import URLError
from urllib.request import Request, urlopen

DEFAULT_PYTHONPATH = "src:../sublease-matcher-backend-core/src"


def _ensure_pythonpath() -> None:
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        return
    os.environ["PYTHONPATH"] = DEFAULT_PYTHONPATH
    for path in DEFAULT_PYTHONPATH.split(":"):
        if path and path not in sys.path:
            sys.path.insert(0, path)


_ensure_pythonpath()

from sublease_matcher.api.adapters.seed_data import build_seed  # noqa: E402
from sublease_matcher.api.adapters.sqlalchemy.db import SessionLocal  # noqa: E402
from sublease_matcher.api.adapters.sqlalchemy.uow import SqlAlchemyUnitOfWork  # noqa: E402


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


def _format_email(user_id: str) -> str:
    return f"{user_id}@example.edu"


def seed_demo_data() -> None:
    seekers_data, hosts_data, listings_data = build_seed()
    with SqlAlchemyUnitOfWork(SessionLocal) as uow:
        for seeker in seekers_data.values():
            payload = dict(seeker)
            payload.setdefault("contact_email", _format_email(payload["user_id"]))
            payload.setdefault("hidden", False)
            uow.seekers.upsert(payload)
        for host in hosts_data.values():
            payload = dict(host)
            payload.setdefault("contact_email", _format_email(payload["user_id"]))
            uow.hosts.upsert(payload)
        for listing in listings_data.values():
            uow.listings.upsert(dict(listing))


def main() -> None:
    env = os.environ.copy()
    database_url = env.get("SM_DATABASE_URL")
    if not database_url:
        raise SystemExit("SM_DATABASE_URL must be set for smoke_sql.py")
    env["PYTHONPATH"] = env.get("PYTHONPATH", DEFAULT_PYTHONPATH)
    env.setdefault("SM_STORAGE", "sqlalchemy")

    print("Applying migrations...")
    _run(["python3", "-m", "alembic", "upgrade", "head"], env=env)
    print("Seeding demo data...")
    seed_demo_data()

    server_env = env.copy()
    server_cmd = [
        "uvicorn",
        "--app-dir",
        "src",
        "sublease_matcher.api.main:app",
        "--reload",
    ]
    print("Starting API server (SQL backend)...")
    proc = subprocess.Popen(  # noqa: S603
        server_cmd,
        env=server_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,
    )
    try:
        _wait_for_server()
        print("Server is up. Running smoke requests...")
        _http_get("/healthz")
        print("healthz OK")
        _http_get("/seekers/me/profile", headers={"X-Debug-User-Id": "user-1"})
        print("seekers profile OK")
        _http_get("/listings/mine", headers={"X-Debug-User-Id": "user-10"})
        print("listings mine OK")
    finally:
        print("Stopping API server...")
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
