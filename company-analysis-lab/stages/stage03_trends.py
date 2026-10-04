"""Stage 3 — Historical Trend Analysis (Historische Trendanalyse)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from lab import calculations as C
from lab import company_analysis as CA
from lab import data as D
from lab import metrics as M
from lab import ui
from lab import visualization as viz
from stages.common import AppContext, record_attempt, stage_footer, stage_header

NUMBER = 3
VERDICTS = ["Improving", "Deteriorating", "Stable", "Volatile / no clear trend"]
DRIVERS = ["Mainly operational", "Mainly accounting-driven", "Mainly one-off items", "A mix"]
MIN_WHY_WORDS = 15
CORE_TREND = ["revenue", "net_income", "total_equity", "eps"]
SECTOR_PRIORITY = {
    "bank": ["cet1_ratio", "cost_income_ratio", "net_interest_income", "fee_income", "net_new_money", "aum"],
    "insurer": ["solvency_ratio", "combined_ratio", "investment_income", "insurance_revenue", "gross_premiums", "aum"],
    "corporate": ["ebit", "operating_cash_flow", "free_cash_flow", "rnd_expense", "gross_profit", "total_debt"],
}


def trend_metrics(app: AppContext, values: pd.DataFrame) -> list[str]:
    applicable = set(D.applicable_metric_keys(app.profile)) | set(app.custom_metrics)
    out = []
    for key in list(M.CATALOG) + list(app.custom_metrics):
        m = M.get(key)
        if key not in applicable or (m is not None and not m.is_trend(app.sector)) or key not in values.index:
            continue
        if values.loc[key].notna().sum() >= 3:
            out.append(key)
    return out


def required_trend_metrics(app: AppContext, available: list[str]) -> list[str]:
    req = [k for k in CORE_TREND if k in available]
    sector = [k for k in SECTOR_PRIORITY[app.sector] if k in available]
    return req + sector[:2]


def _is_ratio(key: str, app: AppContext) -> bool:
    m = M.get(key)
    if m is not None:
        return m.unit == "pct"
    return app.custom_metrics.get(key, {}).get("unit") == "pct"


def _criteria(app: AppContext, required: list[str], answers: dict) -> list[tuple[str, bool]]:
    calc = sum(1 for k in required if answers.get(k, {}).get("calc_checked"))
    judged = sum(1 for k in required if answers.get(k, {}).get("submitted"))
    names = ", ".join(M.short(k, app.custom_metrics) for k in required)
    return [
        (f"Growth calculated yourself for the core metrics ({names}) — {calc}/{len(required)}", calc == len(required) and bool(required)),
        (f"Trend judged and explained for each of them — {judged}/{len(required)}", judged == len(required) and bool(required)),
    ]


def render(app: AppContext) -> None:
    stage_header(app, NUMBER)
    values = app.values
    available = trend_metrics(app, values)
    required = required_trend_metrics(app, available)
    state = app.state(NUMBER)
    answers = state["answers"].setdefault("trend", {})

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        ui.task_box(
            "For each metric: <b>(1)</b> look at the 5-year history, <b>(2)</b> calculate the latest year-over-year growth and the CAGR yourself, "
            "<b>(3)</b> decide whether the trend is improving, deteriorating or stable, and <b>(4)</b> explain <b>why</b>. "
            "The app's own assessment and the analyst notes only appear after you commit to your view."
        )
    with c2:
        ui.cfa_box("growth_cagr")
        ui.cfa_box("trend")

    if not available:
        st.warning("Not enough data — go back to Stage 2 and fill at least three years per metric.", icon=":material/warning:")
        stage_footer(app, NUMBER, _criteria(app, required, answers))
        return

    def status(k: str) -> str:
        a = answers.get(k, {})
        mark = "✓" if a.get("submitted") else ("◐" if a.get("calc_checked") else "○")
        star = " ★" if k in required else ""
        return f"{mark}  {M.short(k, app.custom_metrics)}{star}"

    nav, work = st.columns([1, 3], gap="large")
    with nav:
        st.markdown("**Metrics** · <span class='al-de'>Kennzahlen</span>", unsafe_allow_html=True)
        st.caption("★ required · ✓ done · ◐ calculated")
        key = st.radio("Metric", available, format_func=status, key="s3-metric", label_visibility="collapsed")
    with work:
        _metric_workspace(app, values, key, answers.setdefault(key, {}))

    with st.expander("Overview — your verdicts vs the rule-based assessment", icon=":material/table_chart:"):
        rows = []
        for k in available:
            a = answers.get(k, {})
            if not a.get("submitted"):
                continue
            v = C.classify_trend(D.series(values, k), k)
            rows.append({"Metric": M.short(k, app.custom_metrics), "Your verdict": a.get("verdict"), "Rule-based": v.label.capitalize(), "Driver (yours)": a.get("driver", ""), "Your explanation": a.get("why", "")})
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, column_config={"Your explanation": st.column_config.TextColumn(width="large")})
        else:
            st.caption("Nothing submitted yet.")

    stage_footer(app, NUMBER, _criteria(app, required, answers))


def _metric_workspace(app: AppContext, values: pd.DataFrame, key: str, a: dict) -> None:
    custom = app.custom_metrics
    s = D.series(values, key).dropna()
    unit = M.unit_label(key, app.currency) if M.get(key) else app.custom_metrics.get(key, {}).get("unit", "")
    ratio = _is_ratio(key, app)
    years = [int(y) for y in s.index]
    st.markdown(f"### {ui.bilingual(key, custom)}", unsafe_allow_html=True)
    m = M.get(key)
    if m and m.description:
        st.caption(m.description)

    # accounting breaks inside the window
    acc = app.profile.get("accounting", {})
    bases = [acc.get(str(y)) for y in years if acc.get(str(y))]
    if len(set(bases)) > 1:
        st.warning(f"The series spans different accounting bases ({' → '.join(dict.fromkeys(bases))}). Treat growth across the break with caution.", icon=":material/warning:")

    # Step 1 — history
    st.markdown("**Step 1 · The 5-year history**")
    ui.plotly(viz.history_line(s, f"{M.short(key, custom)} — history", unit), key=f"s3-hist-{key}")
    ui.table_view(pd.DataFrame({"Year": [str(y) for y in years], unit or "Value": s.values}), hide_index=True)

    # Step 2 — calculations
    st.markdown("**Step 2 · Your calculations**")
    y_last, y_prev, y_first = years[-1], years[-2], years[0]
    last, prev, first = float(s.iloc[-1]), float(s.iloc[-2]), float(s.iloc[0])
    n = y_last - y_first
    if ratio:
        q1 = f"Change {y_prev} → {y_last} in percentage points"
        q2 = f"Change {y_first} → {y_last} in percentage points"
        correct1, correct2 = last - prev, last - first
        f1 = rf"\Delta = x_{{{y_last}}} - x_{{{y_prev}}}"
        f2 = rf"\Delta = x_{{{y_last}}} - x_{{{y_first}}}"
        note = "For ratios, growth rates of a percentage are confusing — analysts talk about changes in percentage points (pp)."
    else:
        q1 = f"Year-over-year growth {y_prev} → {y_last} (%)"
        q2 = f"CAGR {y_first} → {y_last} over {n} years (%)"
        correct1 = (last / prev - 1) * 100 if prev > 0 else None
        correct2 = C.cagr(first, last, n)
        f1 = rf"g = \frac{{x_{{{y_last}}}}}{{x_{{{y_prev}}}}} - 1"
        f2 = rf"\text{{CAGR}} = \left(\frac{{x_{{{y_last}}}}}{{x_{{{y_first}}}}}\right)^{{1/{n}}} - 1"
        note = "Growth from a negative or zero base is not meaningful — if a box says 'not meaningful', explain the change in words instead."
    st.caption(note)
    fc1, fc2 = st.columns(2)
    fc1.latex(f1)
    fc2.latex(f2)
    with st.form(f"s3-calc-{key}"):
        i1, i2 = st.columns(2)
        disabled1, disabled2 = correct1 is None, correct2 is None
        v1 = i1.number_input(q1 + (" — not meaningful" if disabled1 else ""), value=a.get("yoy"), format="%.2f", step=None, key=f"s3-yoy-{key}", disabled=disabled1)
        v2 = i2.number_input(q2 + (" — not meaningful" if disabled2 else ""), value=a.get("cagr"), format="%.2f", step=None, key=f"s3-cagr-{key}", disabled=disabled2)
        check = st.form_submit_button("Check my calculations", icon=":material/calculate:")
    if check:
        if (not disabled1 and v1 is None) or (not disabled2 and v2 is None):
            st.warning("Enter both numbers first.")
        else:
            ok1 = disabled1 or C.is_close(v1, correct1, rel=0.01, abs_tol=0.1)
            ok2 = disabled2 or C.is_close(v2, correct2, rel=0.01, abs_tol=0.1)
            a.update({"yoy": v1, "cagr": v2, "calc_checked": True, "ok1": bool(ok1), "ok2": bool(ok2)})
            app.save()
            record_attempt(app, NUMBER, f"yoy-{key}", "yoy_growth", bool(ok1))
            if not ratio:
                record_attempt(app, NUMBER, f"cagr-{key}", "growth_cagr", bool(ok2))
            st.rerun()

    if not a.get("calc_checked"):
        st.info("Check your calculations to unlock the full growth table and the judgement step.", icon=":material/lock:")
        return

    r1, r2 = st.columns(2)
    for col, ok, label, correct, given in ((r1, a.get("ok1"), q1, correct1, a.get("yoy")), (r2, a.get("ok2"), q2, correct2, a.get("cagr"))):
        with col:
            if correct is None:
                st.info(f"{label}: not meaningful (negative or zero base).")
            elif ok:
                st.success(f"✓ {label}: {correct:+.2f}{' pp' if ratio else ' %'}")
            else:
                st.error(f"✗ {label}: you entered {given if given is not None else '–'}, correct is {correct:+.2f}{' pp' if ratio else ' %'}")
    if not ratio and not a.get("ok2") and correct2 is not None:
        avg = np.nanmean(C.yoy_growth(s).values[1:])
        st.caption(f"Common mistake: the arithmetic average of the yearly growth rates is {avg:.2f} % — not the same as the CAGR ({correct2:.2f} %).")

    growth = C.yoy_change(s) if ratio else C.yoy_growth(s)
    gc1, gc2 = st.columns([3, 2])
    with gc1:
        ui.plotly(viz.growth_bars(growth, "Year-over-year change", "pp" if ratio else "%"), key=f"s3-growth-{key}")
    with gc2:
        tbl = pd.DataFrame({"Year": [str(y) for y in years], "Value": s.values, "Change": growth.values})
        st.dataframe(tbl, hide_index=True, column_config={"Value": st.column_config.NumberColumn(format="localized"), "Change": st.column_config.NumberColumn("YoY " + ("pp" if ratio else "%"), format="%+.2f")})

    # Step 3 — judgement
    st.markdown("**Step 3 · Your judgement**")
    better = m.higher_is_better if m else app.custom_metrics.get(key, {}).get("higher_is_better", True)
    if better is None:
        st.caption("Careful: for this metric 'more' is not automatically 'better' (e.g. a bigger balance sheet). Say why you see it as improving or deteriorating.")
    elif better is False:
        st.caption("Careful: for this metric lower is better.")
    with st.form(f"s3-judge-{key}"):
        verdict = st.radio("The trend is…", VERDICTS, index=VERDICTS.index(a["verdict"]) if a.get("verdict") in VERDICTS else None, horizontal=True, key=f"s3-verdict-{key}")
        driver = st.radio("What mainly drives it?", DRIVERS, index=DRIVERS.index(a["driver"]) if a.get("driver") in DRIVERS else None, horizontal=True, key=f"s3-driver-{key}")
        why = st.text_area("Why? Explain the drivers behind the numbers (use the annual report's management commentary).", value=a.get("why", ""), height=110, key=f"s3-why-{key}")
        go = st.form_submit_button("Submit my interpretation", type="primary", icon=":material/send:")
    if go:
        if verdict is None or driver is None or CA.word_count(why) < MIN_WHY_WORDS:
            st.warning(f"Choose a verdict and a driver, and explain in at least {MIN_WHY_WORDS} words.")
        else:
            a.update({"verdict": verdict, "driver": driver, "why": why.strip(), "submitted": True})
            app.save()
            st.rerun()

    if a.get("submitted"):
        _feedback(app, key, s, a)


def _feedback(app: AppContext, key: str, s: pd.Series, a: dict) -> None:
    st.markdown("**Step 4 · Feedback**")
    v = C.classify_trend(s, key)
    mine = a["verdict"].split(" /")[0].lower()
    rule = v.label
    agree = (mine == rule) or (mine == "improving" and rule == "growing") or (mine == "deteriorating" and rule == "shrinking") or (mine == "volatile" and rule == "volatile")
    with st.container(border=True):
        cols = st.columns(2)
        cols[0].metric("Your verdict", a["verdict"])
        cols[1].metric("Rule-based assessment", rule.capitalize())
        for r in v.reasons:
            st.markdown(f"- {r}")
        if agree:
            st.success("Your verdict matches the mechanical assessment. Now check that your *explanation* is right — that is what matters.", icon=":material/thumb_up:")
        elif rule in ("growing", "shrinking"):
            st.info(f"The metric is {rule}. Whether that is good depends on *why* — your reasoning decides.", icon=":material/info:")
        else:
            st.warning("Your verdict differs from the mechanical assessment. That can be fine (e.g. you adjusted for a one-off or an accounting break) — but make sure your explanation says so.", icon=":material/compare_arrows:")

    covered, missed = CA.keyword_coverage(a.get("why", ""), CA.EXPLANATION_DRIVERS)
    st.markdown("**Drivers your explanation mentions**")
    ui.coverage_feedback(covered, missed[:5], "Mentioned", "Did you consider")

    evs = CA.events_for(app.profile, key)
    if evs:
        st.markdown("**Analyst notes — what actually happened** (compare with your explanation)")
        for ev in evs:
            with st.expander(f"{ev['year']} · {ev['title']} — {CA.NATURE_LABEL.get(ev.get('nature'), ev.get('nature', ''))}", icon=":material/menu_book:"):
                st.markdown(ev["detail"])
                st.caption(f"Verify in: {ev.get('where_to_verify', '')}")
    else:
        st.caption("No analyst notes for this metric — check your explanation against the management report and the notes.")
