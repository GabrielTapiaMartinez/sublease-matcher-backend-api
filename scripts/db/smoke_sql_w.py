"""[db-smoke] Smoke tests that exercise the SQLAlchemy storage backend."""

from __future__ import annotations

import os

# Import platform to check the operating system
import platform
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

# --- Helper Functions ---


def _default_database_url(env: dict[str, str]) -> str:
    # Use 'USERNAME' on Windows, or fallback to 'USER' or getuser()
    if platform.system() == "Windows":
        user = env.get("USERNAME") or getuser()
    else:
        user = env.get("USER") or getuser()

    # Note: postgresql may need explicit configuration on Windows if run as a system service.
    # This URL format remains standard.
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
    # Use 'python' instead of 'python3' for better Windows compatibility
    if cmd and cmd[0] == "python3":
        cmd[0] = "python"

    # On Windows, need shell=True for some commands like 'alembic' if not in PATH
    # However, for simple python calls, it's usually better to avoid shell=True
    # unless necessary for command line arguments or pathing. We'll keep it simple here.
    subprocess.run(cmd, check=True, env=env)


def _http_get(path: str, headers: dict[str, str] | None = None) -> bytes:
    # S310 is a bandit warning for urllib.request.urlopen use, which is acceptable
    # for a smoke test connecting to a localhost server.
    req = Request(f"http://127.0.0.1:8001{path}", headers=headers or {})
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

    # Use 'python' for compatibility
    _run([sys.executable, str(seed_script)], env=env)


# --- Main Logic ---


def main() -> None:
    env = os.environ.copy()
    database_url = _ensure_database_url(env)
    if not database_url:
        raise SystemExit("SM_DATABASE_URL must be set for smoke_sql.py")
    env["PYTHONPATH"] = env.get("PYTHONPATH", DEFAULT_PYTHONPATH)
    env.setdefault("SM_STORAGE", "sqlalchemy")
    _log(f"Using database URL: {database_url}")

    _log("Applying migrations...")
    # Using 'python' instead of 'python3'
    _run(["python", "-m", "alembic", "upgrade", "head"], env=env)
    _log("Seeding demo data...")
    seed_demo_data(env)

    server_env = env.copy()
    server_cmd = [
        "uvicorn",
        "--app-dir",
        "src",
        "sublease_matcher.api.main:app",
        "--reload",
        "--port",
        "8001",
    ]
    _log("Starting API server (SQL backend)...")

    # Use cross-platform process handling: set start_new_session=True for
    # better process group management, which helps with clean termination.
    proc = subprocess.Popen(  # noqa: S603
        server_cmd,
        env=server_env,
        # Force output to the current process's stdout/stderr streams
        stdout=sys.stdout,
        stderr=sys.stderr,
        start_new_session=True,
    )

    try:
        _wait_for_server()
        _log("Server is up. Running smoke requests...")
        _http_get("/healthz")
        _log("healthz OK")
        _http_get("/seekers/me/profile", headers={"X-Debug-User-Id": "user-1"})
        _log("seekers profile OK")
        _http_get("/listings/mine", headers={"X-Debug-User-Id": "user-10"})
        _log("listings mine OK")
    finally:
        _log("Stopping API server...")

        # Windows-compatible shutdown logic:
        # 1. Try to terminate gracefully (SIGTERM equivalent)
        with suppress(OSError):
            proc.terminate()

        # 2. Wait for it to close
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            # 3. If it times out, try a forceful kill
            _log("Server did not stop gracefully, forcing kill...")
            with suppress(OSError):
                proc.kill()

            # 4. Wait again for final cleanup
            proc.wait(timeout=5)


if __name__ == "__main__":
    try:
        main()
    except URLError as err:  # pragma: no cover - smoke helper
        print(f"HTTP error during smoke test: {err}", file=sys.stderr)
        raise SystemExit(1) from err
    except Exception as exc:  # pragma: no cover
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise
