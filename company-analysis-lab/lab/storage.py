"""Persistence of the learner's work.

Everything the learner types is saved as JSON under ``workspace/`` (git-ignored):

    workspace/learner.json                 settings + spaced-repetition concept tracker
    workspace/<company_id>/progress.json   stage answers, completion flags, quizzes
    workspace/<company_id>/financials.csv  the learner's working copy of the dataset

Set the environment variable ``ANALYST_LAB_WORKSPACE`` to use a different folder
(the tests do this).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent.parent


def workspace_dir() -> Path:
    path = Path(os.environ.get("ANALYST_LAB_WORKSPACE", APP_DIR / "workspace"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def company_dir(company_id: str) -> Path:
    path = workspace_dir() / company_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # A corrupt file must never lock the learner out — keep a backup and start fresh.
        backup = path.with_suffix(path.suffix + ".corrupt")
        try:
            path.replace(backup)
        except OSError:
            pass
        return default


def _write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(path)


# --------------------------------------------------------------------------- progress


def empty_progress(company_id: str) -> dict:
    return {
        "company_id": company_id,
        "created": now_iso(),
        "updated": now_iso(),
        "stages": {},
        "verified": {},  # "metric|year" -> True
        "settings": {},  # e.g. confirmed currency
        "custom_metrics": {},  # key -> {"en", "de", "unit", "higher_is_better"}
    }


def load_progress(company_id: str) -> dict:
    data = _read_json(company_dir(company_id) / "progress.json", None)
    if not isinstance(data, dict):
        data = empty_progress(company_id)
    base = empty_progress(company_id)
    for key, value in base.items():
        data.setdefault(key, value)
    return data


def save_progress(progress: dict) -> None:
    progress["updated"] = now_iso()
    _write_json(company_dir(progress["company_id"]) / "progress.json", progress)


def stage_state(progress: dict, stage: int) -> dict:
    """Mutable dict holding everything for one stage (created on first access)."""
    stages = progress.setdefault("stages", {})
    state = stages.setdefault(str(stage), {})
    state.setdefault("answers", {})
    state.setdefault("submitted", {})
    state.setdefault("completed", False)
    return state


def reset_company(company_id: str) -> None:
    folder = company_dir(company_id)
    for name in ("progress.json", "financials.csv"):
        path = folder / name
        if path.exists():
            path.unlink()


# --------------------------------------------------------------------------- learner


def empty_learner() -> dict:
    return {"created": now_iso(), "settings": {"training_mode": True}, "concepts": {}, "quiz_counter": 0, "history": []}


def load_learner() -> dict:
    data = _read_json(workspace_dir() / "learner.json", None)
    if not isinstance(data, dict):
        data = empty_learner()
    base = empty_learner()
    for key, value in base.items():
        data.setdefault(key, value)
    return data


def save_learner(learner: dict) -> None:
    _write_json(workspace_dir() / "learner.json", learner)


# --------------------------------------------------------------------------- export / import


def export_bundle(company_id: str) -> str:
    """One JSON string with the learner's work on a company (for download / backup)."""
    csv_path = company_dir(company_id) / "financials.csv"
    bundle = {
        "format": "analyst-lab-export/1",
        "exported": now_iso(),
        "progress": load_progress(company_id),
        "financials_csv": csv_path.read_text(encoding="utf-8") if csv_path.exists() else None,
    }
    return json.dumps(bundle, indent=2, ensure_ascii=False, default=str)


def import_bundle(text: str) -> str:
    """Restore an export. Returns the company id. Raises ValueError on bad input."""
    try:
        bundle = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Not a valid JSON export: {exc}") from exc
    if not isinstance(bundle, dict) or bundle.get("format") != "analyst-lab-export/1":
        raise ValueError("This file is not an Analyst Lab export.")
    progress = bundle.get("progress") or {}
    company_id = progress.get("company_id")
    if not company_id:
        raise ValueError("Export has no company id.")
    save_progress(progress)
    if bundle.get("financials_csv"):
        (company_dir(company_id) / "financials.csv").write_text(bundle["financials_csv"], encoding="utf-8")
    return company_id
