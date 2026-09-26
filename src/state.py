from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_state(path: str) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(path: str, state: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    tmp.replace(p)


def diff(old: dict | None, new: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (added, changed, removed) records.

    The record id is stable for a particular exam slot. If the site changes
    a field, the record goes into changed.
    """
    old_items = {x["id"]: x for x in (old or {}).get("exams", [])}
    new_items = {x["id"]: x for x in new.get("exams", [])}

    added = [new_items[k] for k in sorted(new_items.keys() - old_items.keys())]
    removed = [old_items[k] for k in sorted(old_items.keys() - new_items.keys())]

    changed = []
    for k in sorted(new_items.keys() & old_items.keys()):
        if new_items[k] != old_items[k]:
            changed.append({"before": old_items[k], "after": new_items[k]})

    return added, changed, removed
