"""Analyst Lab — learn to analyse a bank or insurer step by step, like an equity analyst.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import importlib
import os

import streamlit as st

from lab import company_analysis as CA
from lab import data as D
from lab import storage, ui
from stages.common import AppContext, go_to

st.set_page_config(page_title="Analyst Lab", page_icon=":material/insights:", layout="wide", initial_sidebar_state="expanded")
ui.inject_css()

STAGE_MODULES = {
    1: "stages.stage01_business",
    2: "stages.stage02_data",
    3: "stages.stage03_trends",
    4: "stages.stage04_ratios",
    5: "stages.stage05_statements",
    6: "stages.stage06_quality",
    7: "stages.stage07_risk",
    8: "stages.stage08_peers",
    9: "stages.stage09_valuation",
    10: "stages.stage10_thesis",
}
UNLOCK_ALL = os.environ.get("ANALYST_LAB_UNLOCK_ALL", "") == "1"


def stage_module(number: int):
    try:
        return importlib.import_module(STAGE_MODULES[number])
    except ModuleNotFoundError as exc:
        if exc.name == STAGE_MODULES[number]:
            return None  # stage not built yet
        raise


learner = storage.load_learner()
companies = D.list_companies()
if not companies:
    st.error("No company datasets found in datasets/companies/.")
    st.stop()
ids = [c["id"] for c in companies]
by_id = {c["id"]: c for c in companies}

if "company_id" not in st.session_state:
    last = learner.get("settings", {}).get("last_company")
    st.session_state["company_id"] = last if last in ids else ids[0]
st.session_state.setdefault("view", "stage")

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown('<p class="al-side-brand">Analyst Lab</p><p class="al-side-sub">Equity analysis of banks &amp; insurers — learn by doing</p>', unsafe_allow_html=True)

    def _on_company_change():
        learner.setdefault("settings", {})["last_company"] = st.session_state["company_select"]
        storage.save_learner(learner)
        st.session_state["company_id"] = st.session_state["company_select"]
        st.session_state["view"] = "stage"
        st.session_state.pop("stage", None)

    st.selectbox(
        "Company",
        ids,
        index=ids.index(st.session_state["company_id"]),
        format_func=lambda i: f"{by_id[i]['short_name']}  ·  {by_id[i]['sector'].capitalize()}",
        key="company_select",
        on_change=_on_company_change,
    )
    profile = by_id[st.session_state["company_id"]]
    progress = storage.load_progress(profile["id"])

    training_mode = st.toggle(
        "Analyst Training Mode",
        value=learner.get("settings", {}).get("training_mode", True),
        help="After every stage you get 5 questions (Level 1 identify → Level 5 analyst reasoning). Mistakes come back later via spaced repetition. When on, the quiz is required to unlock the next stage.",
    )
    if training_mode != learner.get("settings", {}).get("training_mode", True):
        learner.setdefault("settings", {})["training_mode"] = training_mode
        storage.save_learner(learner)

    st.progress(CA.overall_progress(progress, training_mode), text=f"Progress on {profile['short_name']}")
    if UNLOCK_ALL:
        st.caption("Instructor mode: all stages unlocked.")

    if "stage" not in st.session_state:
        st.session_state["stage"] = CA.current_stage(progress, training_mode)

    st.markdown("**Stages** · <span class='al-de'>Analyseschritte</span>", unsafe_allow_html=True)
    for s in CA.STAGES:
        unlocked = CA.is_unlocked(progress, s.number, training_mode, UNLOCK_ALL)
        passed = CA.stage_passed(progress, s.number, training_mode)
        active = st.session_state["view"] == "stage" and st.session_state["stage"] == s.number
        icon = ":material/check_circle:" if passed else (s.icon if unlocked else ":material/lock:")
        if st.button(
            f"{s.number}. {s.en}",
            key=f"nav-{s.number}",
            icon=icon,
            disabled=not unlocked,
            type="primary" if active else "tertiary",
            width="stretch",
        ):
            go_to(s.number)
            st.rerun()

    st.markdown("**Learning** · <span class='al-de'>Lernen</span>", unsafe_allow_html=True)
    if st.button("Concept review", icon=":material/psychology:", width="stretch", type="primary" if st.session_state["view"] == "review" else "tertiary", key="nav-review"):
        st.session_state["view"] = "review"
        st.rerun()

    with st.expander("Workspace", icon=":material/folder:"):
        st.download_button("Export my work (JSON)", storage.export_bundle(profile["id"]), file_name=f"analyst-lab-{profile['id']}.json", mime="application/json", icon=":material/download:", width="stretch")
        up = st.file_uploader("Restore an export", type=["json"], key="restore-upload")
        if up is not None and st.button("Restore", key="restore-btn"):
            try:
                cid = storage.import_bundle(up.getvalue().decode("utf-8"))
                st.success(f"Restored work on {cid}.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        st.divider()
        confirm = st.checkbox(f"I want to delete all my work on {profile['short_name']}", key="reset-confirm")
        if st.button("Reset this company", disabled=not confirm, key="reset-btn", icon=":material/restart_alt:"):
            storage.reset_company(profile["id"])
            st.session_state.pop("stage", None)
            st.session_state.pop("reset-confirm", None)
            st.rerun()

    with st.expander("Add a company", icon=":material/add_business:"):
        with st.form("add-company"):
            name = st.text_input("Company name")
            sector = st.selectbox("Sector", ["bank", "insurer"])
            currency = st.selectbox("Reporting currency", ["CHF", "EUR", "USD", "GBP"])
            country = st.text_input("Country")
            listed = st.checkbox("Listed on a stock exchange", value=True)
            if st.form_submit_button("Create dataset"):
                if not name.strip():
                    st.error("Enter a name.")
                else:
                    new_id = D.create_company(name.strip(), sector, currency, country.strip(), listed)
                    st.session_state["company_id"] = new_id
                    st.session_state.pop("stage", None)
                    learner.setdefault("settings", {})["last_company"] = new_id
                    storage.save_learner(learner)
                    st.rerun()
        st.caption("Creates datasets/companies/<id>/ with a profile and an empty template. Add reference notes to profile.json later.")

# ------------------------------------------------------------------ main area
app = AppContext(profile=profile, progress=progress, learner=learner, training_mode=training_mode, unlock_all=UNLOCK_ALL)

if st.session_state["view"] == "review":
    from stages import training

    training.render_review(app)
else:
    number = st.session_state["stage"]
    if not CA.is_unlocked(progress, number, training_mode, UNLOCK_ALL):
        number = CA.current_stage(progress, training_mode)
        st.session_state["stage"] = number
    module = stage_module(number)
    if module is None:
        st.info(f"Stage {number} is not built yet.", icon=":material/construction:")
    else:
        module.render(app)
