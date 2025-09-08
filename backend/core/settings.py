"""Application settings loader.

Loads environment variables from a local `.env` file and exposes helpers
to retrieve required configuration values.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv


def _load_env() -> None:
    """Load env vars from `.env` in backend directory if present.

    We call `load_dotenv()` twice:
    - First with an explicit path to `backend/.env` (common in this project)
    - Then a generic call to allow parent/root `.env` to be picked up if used
    """
    # backend/core/settings.py -> backend/.env
    here = Path(__file__).resolve().parent
    env_path = here.parent / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
    # Also load from current working directory as a fallback
    load_dotenv(override=False)


_load_env()


def _get_required(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise ValueError(f"Missing required environment variable: {name}")
    return val


def get_db_settings() -> Dict[str, str]:
    """Return required DB settings from env (no in-code defaults)."""
    return {
        "host": _get_required("DB_HOST"),
        "port": _get_required("DB_PORT"),
        "dbname": _get_required("DB_NAME"),
        "user": _get_required("DB_USER"),
        "password": _get_required("DB_PASS"),
    }

