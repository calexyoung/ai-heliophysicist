"""Persistent workspace layout.

Everything a session produces lands on disk under workspace/ so that state
outlives any one conversation (the "enduring environment" of the pattern).
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("HELIO_AGENT_ROOT", Path(__file__).resolve().parent.parent))


def active_user() -> str | None:
    """Active user profile (HELIO_AGENT_USER env var / .env), or None (core).

    With a user active, data/outputs/logs live under users/<name>/workspace
    so one-off analyses never mix into the shared tree. The HTTP cache stays
    global — cached archive responses are user-independent.
    """
    u = os.environ.get("HELIO_AGENT_USER", "").strip()
    if not u:
        return None
    if not u.replace("-", "").replace("_", "").isalnum():
        raise ValueError(f"bad HELIO_AGENT_USER {u!r}: use letters/digits/-/_")
    return u


def user_dir() -> Path | None:
    u = active_user()
    return (ROOT / "users" / u) if u else None


def _workspace() -> Path:
    ud = user_dir()
    return (ud / "workspace") if ud else (ROOT / "workspace")


def load_env() -> None:
    """Load KEY=value pairs from the project .env (API tokens) into os.environ.

    Existing environment variables win; the .env never overrides them.
    """
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and value and key not in os.environ:
            os.environ[key] = value


load_env()  # must run before the path constants: .env may set HELIO_AGENT_USER

WORKSPACE = _workspace()
DATA_DIR = WORKSPACE / "data"          # downloaded mission data
OUTPUT_DIR = WORKSPACE / "outputs"     # plots, tables, reports
LOG_DIR = WORKSPACE / "logs"           # audit trail (per user when active)
CACHE_DIR = ROOT / "workspace" / "cache"  # HTTP cache: always global/shared


def ensure_dirs() -> None:
    for d in (DATA_DIR, OUTPUT_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


def output_path(name: str) -> Path:
    """Path for a new output artifact (plot, table, report)."""
    ensure_dirs()
    return OUTPUT_DIR / name


def data_path(name: str) -> Path:
    """Path for downloaded/cached data."""
    ensure_dirs()
    return DATA_DIR / name
