from __future__ import annotations

import os
from pathlib import Path

BASE_URL = os.getenv(
    "BELLHAVEN_BASE_URL",
    "https://analyst-assessment-production.up.railway.app",
).rstrip("/")
API_BASE = f"{BASE_URL}/api/v1"
TOKEN = os.getenv("BELLHAVEN_API_TOKEN", "")
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STATE_PATH = DATA_DIR / "review_state.json"


def require_token() -> str:
    if not TOKEN:
        raise RuntimeError(
            "BELLHAVEN_API_TOKEN is required. Copy .env.example to .env or set it "
            "in your shell before running the pipeline."
        )
    return TOKEN

