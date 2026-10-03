"""Stage 4 — Ratio Analysis (Kennzahlenanalyse).

For every ratio: formula → numbers required → your calculation → correct calculation → interpretation.
Nothing is revealed before the learner submits an attempt.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lab import company_analysis as CA
from lab import data as D
from lab import metrics as M
from lab import ratios as R
from lab import ui
from lab import visualization as viz
from stages.common import AppContext, record_attempt, stage_footer, stage_header

NUMBER = 4
MIN_INTERP_WORDS = 15
CONCEPT_OF = {"roe": "roe", "roa": "roa", "leverage": "dupont", "net_margin": "ratio_definitions", "cost_income": "ratio_definitions", "payout": "payout",
              "equity_ratio": "leverage", "bvps": "ratio_definitions", "cet1_calc": "regulatory_capital", "rwa_density": "regulatory_capital",
              "nii_share": "revenue_mix", "fee_share": "revenue_mix", "nnm_growth": "ratio_definitions", "insurance_margin": "ratio_definitions", "investment_share": "revenue_mix"}


def required_ratios(app: AppContext, available: list[R.RatioDef]) -> list[str]:
    core = [r.key for r in available if r.core]
    sector = [r.key for r in available if not r.core and app.sector in r.sectors and r.sectors != M.SECTORS]
    return core + sector[:2]


def _criteria(app: AppContext, required: list[str], answers: dict) -> list[tuple[str, bool]]:
    attempted = sum(1 for k in required if answers.get(k, {}).get("attempted"))
    interpreted = sum(1 for k in required if answers.get(k, {}).get("interp_submitted"))
    names = ", ".join(R.RATIOS[k].en.split(" (")[0] for k in required)
    return [
        (f"Calculated yourself before seeing the solution: {names} — {attempted}/{len(required)}", attempted == len(required) and bool(required)),
        (f"Interpreted each ratio in your own words — {interpreted}/{len(required)}", interpreted == len(required) and bool(required)),
    ]


def render(app: AppContext) -> None:
    stage_header(app, NUMBER)
    values = app.values
    available = R.available_ratios(app.profile, values)
    required = required_ratios(app, available)
    state = app.state(NUMBER)
    answers = state["answers"].setdefault("ratios", {})

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        ui.task_box(
            "Work through each ratio in five steps: <b>formula → numbers required → your calculation → correct calculation → interpretation</b>. "
            "Pick the numbers from your Stage 2 dataset (open it below). The worked solution appears only after you submit your attempt. "
            "Convention: balances are <b>averaged</b> (opening + closing) ÷ 2, as in the CFA curriculum."
        )
    with c2:
        ui.cfa_box("dupont")
    with st.expander("Your Stage 2 dataset (look up the numbers here)", icon=":material/table_view:"):
        disp = values.copy()
        disp.index = [M.short(k, app.custom_metrics) + f" [{M.unit_label(k, app.currency)}]" for k in values.index]
        disp.columns = [str(c) for c in disp.columns]
        st.dataframe(disp, column_config={c: st.column_config.NumberColumn(format="localized") for c in disp.columns})

    if not available:
        st.warning("No ratio can be computed yet — complete the dataset in Stage 2.", icon=":material/warning:")
        stage_footer(app, NUMBER, _criteria(app, required, answers))
        return

    def status(k: str) -> str:
        a = answers.get(k, {})
        mark = "✓" if a.get("interp_submitted") else ("◐" if a.get("attempted") else "○")
        return f"{mark}  {R.RATIOS[k].en}{' ★' if k in required else ''}"

    nav, work = st.columns([1, 3], gap="large")
    with nav:
        st.markdown("**Ratios** · <span class='al-de'>Kennzahlen</span>", unsafe_allow_html=True)
        st.caption("★ required · ✓ done · ◐ calculated")
        key = st.radio("Ratio", [r.key for r in available], format_func=status, key="s4-ratio", label_visibility="collapsed")
    with work:
        _ratio_workspace(app, values, R.RATIOS[key], answers.setdefault(key, {}))

    if all(answers.get(k, {}).get("attempted") for k in ("roe", "roa", "leverage") if k in [r.key for r in available]):
        _dupont(app, values)

    stage_footer(app, NUMBER, _criteria(app, required, answers))


def _ratio_workspace(app: AppContext, values: pd.DataFrame, rd: R.RatioDef, a: dict) -> None:
    years = D.year_columns(values)
    valid_years = [y for y in years if R.compute(rd, values, y).value is not None]
    if not valid_years:
        st.warning("Data missing for this ratio.")
        return
    st.markdown(f"### {rd.en} · <span class='al-de'>{rd.de}</span>", unsafe_allow_html=True)
    if rd.cfa:
        ui.cfa_box(rd.cfa)

    # 1 — formula
    st.markdown("**1 · Formula**")
    st.latex(rd.latex)

    # year choice is locked once attempted, so the learner cannot fish for answers
    year = a.get("year") if a.get("attempted") else st.selectbox("Fiscal year to analyse", valid_years[::-1], key=f"s4-year-{rd.key}")
    res = R.compute(rd, values, year, app.currency)

    # 2 — numbers required
    st.markdown("**2 · Numbers required** — find them in your dataset / the annual report")
    st.markdown("\n".join(f"- {rn.label}  ·  _{M.get(rn.metric).statement if M.get(rn.metric) else ''}_" for rn in res.required))

    # 3 — my calculation
    st.markdown("**3 · Your calculation**")
    with st.form(f"s4-form-{rd.key}"):
        cols = st.columns(len(res.required) + 1)
        for col, rn in zip(cols, res.required):
            col.number_input(rn.label, value=a.get("inputs", {}).get(f"{rn.metric}|{rn.year}"), format="%.4f", step=None, key=f"s4-in-{rd.key}-{rn.metric}-{rn.year}", disabled=bool(a.get("attempted")))
        unit = {"%": "%", "x": "×", "ccy": app.currency}[rd.unit]
        cols[-1].number_input(f"Result ({unit})", value=a.get("result"), format="%.4f", step=None, key=f"s4-res-{rd.key}", disabled=bool(a.get("attempted")))
        go = st.form_submit_button("Submit my attempt", type="primary", disabled=bool(a.get("attempted")), icon=":material/send:")
    if go:
        inputs = {f"{rn.metric}|{rn.year}": st.session_state.get(f"s4-in-{rd.key}-{rn.metric}-{rn.year}") for rn in res.required}
        result = st.session_state.get(f"s4-res-{rd.key}")
        if result is None or any(v is None for v in inputs.values()):
            st.warning("Fill in every number and your result — that is the point of the exercise.")
        else:
            diag = R.diagnose(res, inputs, result, app.currency)
            a.update({"year": year, "inputs": inputs, "result": result, "attempted": True, "correct": diag.correct, "headline": diag.headline, "details": diag.details})
            app.save()
            record_attempt(app, NUMBER, f"ratio-{rd.key}", CONCEPT_OF.get(rd.key, "ratio_definitions"), diag.correct)
            st.rerun()

    if not a.get("attempted"):
        st.info("The correct calculation appears after you submit your attempt.", icon=":material/lock:")
        return

    # 4 — correct calculation
    st.markdown("**4 · Correct calculation**")
    (st.success if a.get("correct") else st.error)(a.get("headline", ""), icon=":material/check_circle:" if a.get("correct") else ":material/error:")
    for d in a.get("details", []):
        st.markdown(f"- {d}")
    with st.container(border=True):
        for step in res.steps:
            st.markdown(f"`{step}`")
        if res.alternative is not None:
            st.caption(f"For reference — with year-end balances instead of averages: {R.format_ratio(res.alternative, rd, app.currency)}")
        reported = None
        if rd.key == "roe":
            reported = D.value(values, "roe_reported", year)
        elif rd.key == "cost_income":
            reported = D.value(values, "cost_income_ratio", year)
        elif rd.key == "cet1_calc":
            reported = D.value(values, "cet1_ratio", year)
        if reported is not None:
            st.caption(f"The company reports {reported:.1f} %. Differences usually come from definitions (e.g. adjusted figures, tangible equity, excluding items).")

    # 5 — interpretation
    st.markdown("**5 · Interpretation**")
    with st.form(f"s4-interp-{rd.key}"):
        text = st.text_area("What does this ratio tell you about the company? Is the level good or bad for this type of company, and why?", value=a.get("interpretation", ""), height=110, key=f"s4-int-{rd.key}")
        sub = st.form_submit_button("Submit interpretation", icon=":material/send:")
    if sub:
        if CA.word_count(text) < MIN_INTERP_WORDS:
            st.warning(f"Write at least {MIN_INTERP_WORDS} words.")
        else:
            a.update({"interpretation": text.strip(), "interp_submitted": True})
            app.save()
            st.rerun()
    if a.get("interp_submitted"):
        guide = rd.interpretation.get(app.sector, "")
        bench = rd.benchmark.get(app.sector)
        st.info(f"**How an analyst reads it:** {guide}" + (f"\n\n**Rule-of-thumb range:** {bench}" if bench else ""), icon=":material/lightbulb:")
        hist = pd.Series({y: R.compute(rd, values, y).value for y in years}, dtype=float).dropna()
        if len(hist) >= 2:
            unit_txt = {"%": "%", "x": "×", "ccy": app.currency}[rd.unit]
            ui.plotly(viz.history_line(hist, f"{rd.en} — all years (calculated)", unit_txt), key=f"s4-hist-{rd.key}")
            st.caption("Now that you have your own view: does the multi-year trend support your interpretation?")


def _dupont(app: AppContext, values: pd.DataFrame) -> None:
    st.divider()
    st.subheader("DuPont analysis — where does ROE come from?")
    ui.cfa_box("dupont")
    rows = []
    for y in D.year_columns(values):
        d = R.dupont(values, y)
        if d:
            rows.append({"Year": str(y), "Net margin %": d.get("net_margin"), "Asset turnover ×": d.get("asset_turnover"), "ROA %": d["roa"], "Leverage ×": d["leverage"], "ROE %": d["roe"]})
    if not rows:
        st.caption("Needs net income, assets and equity for two consecutive years.")
        return
    df = pd.DataFrame(rows)
    st.latex(r"\text{ROE} = \underbrace{\frac{NI}{\text{Revenue}}}_{\text{margin}} \times \underbrace{\frac{\text{Revenue}}{\overline{\text{Assets}}}}_{\text{turnover}} \times \underbrace{\frac{\overline{\text{Assets}}}{\overline{\text{Equity}}}}_{\text{leverage}} = \text{ROA} \times \text{Leverage}")
    st.dataframe(df, hide_index=True, column_config={c: st.column_config.NumberColumn(format="%.3f") for c in df.columns if c != "Year"})
    cols = st.columns(3)
    s = df.set_index("Year")
    for col, (c, u) in zip(cols, [("ROA %", "%"), ("Leverage ×", "×"), ("ROE %", "%")]):
        with col:
            ui.plotly(viz.small_line(s[c], c, u), key=f"s4-dupont-{c}")
    st.caption("Question to ask yourself: did ROE move because the company became more profitable (ROA) or because it used more leverage? Banks and insurers can raise ROE simply by holding less capital.")
