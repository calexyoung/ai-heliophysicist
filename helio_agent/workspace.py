"""Persistent workspace layout.

Everything a session produces lands on disk under workspace/ so that state
outlives any one conversation (the "enduring environment" of the pattern).
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("HELIO_AGENT_ROOT", Path(__file__).resolve().parent.parent))
WORKSPACE = ROOT / "workspace"
DATA_DIR = WORKSPACE / "data"          # downloaded mission data, cached
OUTPUT_DIR = WORKSPACE / "outputs"     # plots, tables, reports
LOG_DIR = WORKSPACE / "logs"           # audit trail


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


load_env()


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
