"""Reads settings from the environment, loading a local .env if present."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def get(name: str, default: str | None = None, *, required: bool = False) -> str | None:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required setting {name} (see .env.example)")
    return value
