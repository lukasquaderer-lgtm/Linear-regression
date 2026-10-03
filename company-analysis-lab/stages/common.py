"""Context object handed to every stage, plus the shared stage footer."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from lab import company_analysis as CA
from lab import data as D
from lab import storage
from lab import ui


@dataclass
class AppContext:
    profile: dict
    progress: dict
    learner: dict
    training_mode: bool
    unlock_all: bool = False

    # ----------------------------------------------------------------- identity
    @property
    def company_id(self) -> str:
        return self.profile["id"]

    @property
    def name(self) -> str:
        return self.profile.get("short_name", self.profile["name"])

    @property
    def sector(self) -> str:
        return self.profile["sector"]

    @property
    def currency(self) -> str:
        return self.progress.get("settings", {}).get("currency") or self.profile.get("currency", "CHF")

    @property
    def custom_metrics(self) -> dict:
        return self.progress.setdefault("custom_metrics", {})

    # ----------------------------------------------------------------- data
    def dataset(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        values, meta = D.load_working(self.company_id)
        values, meta = D.ensure_rows(values, meta, D.required_metric_keys(self.profile))
        return values, meta

    @property
    def values(self) -> pd.DataFrame:
        return self.dataset()[0]

    # ----------------------------------------------------------------- state
    def state(self, stage: int) -> dict:
        return storage.stage_state(self.progress, stage)

    def save(self) -> None:
        storage.save_progress(self.progress)

    def save_learner(self) -> None:
        storage.save_learner(self.learner)


def record_attempt(app: AppContext, stage: int, once_key: str, concept: str, correct: bool) -> None:
    """Feed a first attempt from the stage work (not only quizzes) into spaced repetition."""
    from lab import questions as Q

    state = app.state(stage)
    seen = state.setdefault("recorded", [])
    if once_key in seen:
        return
    seen.append(once_key)
    Q.record(app.learner, concept, "correct" if correct else "wrong")
    app.save_learner()


def go_to(stage: int) -> None:
    st.session_state["view"] = "stage"
    st.session_state["stage"] = stage


def stage_header(app: AppContext, number: int) -> None:
    s = CA.STAGE_BY_NUMBER[number]
    p = app.profile
    chips = [
        p.get("subsector") or p["sector"].capitalize(),
        f"Reporting currency: {app.currency}",
        "Listed: " + (p.get("exchange_ticker") or "yes") if p.get("listed") else "Not listed",
    ]
    ui.header(p, f"Stage {number} of 10 · {s.de}", f"{s.en} — {p['name']}", s.goal, chips)


def stage_footer(app: AppContext, number: int, criteria: list[tuple[str, bool]]) -> None:
    """Completion checklist → 'Complete stage' → training quiz → continue."""
    from stages import training  # local import avoids a cycle

    st.divider()
    st.subheader("Stage checklist")
    ui.checklist(criteria)
    state = app.state(number)
    done = all(ok for _, ok in criteria)
    if not state.get("completed"):
        if st.button("Complete stage", type="primary", disabled=not done, key=f"complete-{number}", icon=":material/check_circle:"):
            CA.mark_complete(app.progress, number)
            st.rerun()
        if not done:
            st.caption("Finish every item above to complete the stage.")
        return

    st.success(f"Stage {number} completed.", icon=":material/task_alt:")
    if app.training_mode:
        training.render_stage_quiz(app, number)
    passed = CA.stage_passed(app.progress, number, app.training_mode)
    if number < 10 and passed:
        nxt = CA.STAGE_BY_NUMBER[number + 1]
        if st.button(f"Continue to Stage {number + 1}: {nxt.en}", type="primary", key=f"next-{number}", icon=":material/arrow_forward:"):
            go_to(number + 1)
            st.rerun()
    elif number < 10 and app.training_mode:
        st.info("Finish the Analyst Training quiz above to unlock the next stage.", icon=":material/school:")
