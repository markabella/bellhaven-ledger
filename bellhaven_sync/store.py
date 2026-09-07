from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import STATE_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_state(path: Path = STATE_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"generated_at": None, "proposals": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any], path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def merge_proposals(fresh: list[dict], path: Path = STATE_PATH) -> dict[str, Any]:
    previous = load_state(path)
    decided = {p["id"]: p for p in previous.get("proposals", []) if p.get("status") != "pending"}
    merged = []
    for proposal in fresh:
        old = decided.get(proposal["id"])
        if old:
            proposal.update({k: old[k] for k in ("status", "decided_at", "result") if k in old})
        merged.append(proposal)
    # Retain decided items even after the CRM change makes them disappear from a new scan.
    fresh_ids = {p["id"] for p in merged}
    merged.extend(p for pid, p in decided.items() if pid not in fresh_ids)
    state = {"generated_at": utc_now(), "proposals": merged}
    save_state(state, path)
    return state

