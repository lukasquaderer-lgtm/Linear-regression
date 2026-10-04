"""Stage 6 — Quality of Earnings (Qualität der Gewinne)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from lab import calculations as C
from lab import company_analysis as CA
from lab import data as D
from lab import ui
from lab import visualization as viz
from stages.common import AppContext, stage_footer, stage_header

NUMBER = 6
STATUS = ["No issue found", "Issue found", "Not applicable"]


def checks(app: AppContext) -> list[dict]:
    bank = app.sector == "bank"
    corp = app.sector == "corporate"
    return [
        {
            "key": "cash", "en": "Net income vs cash / capital generation", "de": "Gewinn vs. Cash- bzw. Kapitalgenerierung", "cfa": "accruals",
            "why": ("For banks, operating cash flow mixes loans, deposits and trading flows, so it says little about earnings quality. Ask instead: does profit turn into **capital** (CET1) and **distributions** (dividends, buybacks)?"
                    if bank else
                    "Compare net income with operating cash flow over several years (cash conversion). Persistent gaps (accruals) mean earnings are less likely to persist. Watch working capital: receivables and inventories growing faster than sales tie up cash and can signal aggressive revenue recognition."
                    if corp else
                    "Compare net income with operating cash flow over several years. Persistent gaps (accruals) mean earnings are less likely to persist. For life insurers, also ask whether profit turns into solvency capital and cash remittances."),
            "where": "Cash flow statement; capital management section; statement of changes in equity",
        },
        {
            "key": "oneoff", "en": "One-off gains and losses", "de": "Einmalige Gewinne und Verluste", "cfa": "one_offs",
            "why": "Disposal gains, negative goodwill, litigation settlements, insurance recoveries, revaluation gains. Remove them (after tax) to see underlying earnings.",
            "where": "Income statement 'other income'; management report 'underlying/adjusted' results; notes",
        },
        {
            "key": "estimates", "en": "Changes in accounting estimates", "de": "Änderungen von Schätzungen", "cfa": "notes",
            "why": ("Expected-credit-loss model parameters, fair-value inputs (Level 3), useful lives, pension assumptions." if bank else
                    "Revenue deductions (rebates, chargebacks, returns), useful lives, capitalised development costs, impairment-test assumptions (growth, discount rate), pension assumptions." if corp else
                    "Actuarial assumptions (mortality, lapse, expenses), discount rates, CSM unlocking, investment valuations."),
            "where": "Notes: significant accounting estimates and judgements; changes in estimates",
        },
        {
            "key": "restructuring", "en": "Restructuring charges", "de": "Restrukturierungskosten", "cfa": "one_offs",
            "why": "Integration and restructuring costs are often presented as 'one-off' — but if they appear every year, they are part of the cost base.",
            "where": "Income statement; notes on provisions and personnel expenses; 'underlying' reconciliation",
        },
        {
            "key": "impairments", "en": "Impairments", "de": "Wertminderungen", "cfa": "one_offs",
            "why": "Goodwill and intangible impairments (non-cash, usually one-off but signal overpaying for an acquisition); " + ("loan impairments are recurring credit costs." if bank else "write-downs of product rights after failed trials or weaker sales — if they recur, the 'core' profit that excludes them is too flattering." if corp else "investment impairments."),
            "where": "Notes on goodwill/intangibles and financial assets",
        },
        {
            "key": "reserves", "en": "Reserve and provision changes", "de": "Reserve- und Rückstellungsveränderungen", "cfa": "reserves",
            "why": ("Releases of credit-loss allowances or litigation provisions boost profit without new business — check whether they can recur." if bank else
                    "Releases of provisions (litigation, restructuring, warranties) or of inventory and receivable allowances boost profit without new business — check whether they can recur." if corp else
                    "Prior-year reserve development (releases or strengthening) changes earnings without new business; repeated releases can mean earlier over-reserving used to smooth profit."),
            "where": "Credit risk note / provisions note" if bank else "Provisions note; inventory and trade receivables notes" if corp else "Notes on insurance liabilities; claims development tables; P&C prior-year development",
        },
        {
            "key": "acquisitions", "en": "Acquisition effects", "de": "Akquisitionseffekte", "cfa": "one_offs",
            "why": "Consolidating a target adds revenue and profit that is not organic; purchase-price allocation creates amortisation or negative goodwill; integration costs follow.",
            "where": "Note on business combinations; segment reporting; management report",
        },
        {
            "key": "tax", "en": "Unusual tax effects", "de": "Ungewöhnliche Steuereffekte", "cfa": "one_offs",
            "why": "Recognition or write-off of deferred tax assets, tax-rate changes, settlements. Compare the effective tax rate with the statutory rate (Switzerland ≈ 12–21 % by canton; Liechtenstein 12.5 %; Germany ≈ 30 %).",
            "where": "Income tax note (tax rate reconciliation)",
        },
    ]


def _criteria(app: AppContext, answers: dict) -> list[tuple[str, bool]]:
    cks = checks(app)
    done = sum(1 for c in cks if answers.get("checks", {}).get(c["key"], {}).get("status") in STATUS and CA.word_count(answers["checks"][c["key"]].get("note", "")) >= 5)
    bridge = bool(answers.get("bridge_saved"))
    rating = bool(answers.get("rating")) and CA.word_count(answers.get("rating_why", "")) >= 15
    return [
        (f"All eight checks completed with a short note — {done}/8", done == len(cks)),
        ("Underlying earnings bridge built (or confirmed that no adjustment is needed)", bridge),
        ("Overall earnings-quality rating with justification", rating),
    ]


def render(app: AppContext) -> None:
    stage_header(app, NUMBER)
    values = app.values
    state = app.state(NUMBER)
    answers = state["answers"]
    answers.setdefault("checks", {})

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        ui.task_box(
            "High-quality earnings are <b>recurring, cash- or capital-backed and free of aggressive estimates</b>. "
            "Run the eight checks against the annual report, build a bridge from reported to underlying net income, and rate the overall quality. "
            + ("For a bank, swap 'cash' for 'capital': does profit become CET1 capital and distributions?" if app.sector == "bank" else
               "For a non-financial company, cash conversion and working capital are the key tests — and check what the company leaves out of its 'core' or 'adjusted' profit." if app.sector == "corporate" else
               "For an insurer, watch reserve releases and investment gains.")
        )
    with c2:
        ui.cfa_box("quality_earnings")

    st.subheader("1 · Eight checks")
    _cash_panel(app, values)
    for ck in checks(app):
        a = answers["checks"].setdefault(ck["key"], {})
        done = a.get("status") in STATUS and CA.word_count(a.get("note", "")) >= 5
        with st.expander(f"{'✓' if done else '○'}  {ck['en']} · {ck['de']}", expanded=False):
            st.markdown(ck["why"])
            st.caption(f"Where to look: {ck['where']}")
            ui.cfa_box(ck["cfa"])
            with st.form(f"s6-ck-{ck['key']}"):
                status = st.radio("Result", STATUS, index=STATUS.index(a["status"]) if a.get("status") in STATUS else None, horizontal=True, key=f"s6-st-{ck['key']}")
                note = st.text_area("What did you find? (item, year, amount, page)", value=a.get("note", ""), height=90, key=f"s6-note-{ck['key']}")
                if st.form_submit_button("Save check", icon=":material/save:"):
                    if status is None or CA.word_count(note) < 5:
                        st.warning("Pick a result and write at least five words.")
                    else:
                        a.update({"status": status, "note": note.strip()})
                        app.save()
                        st.rerun()

    st.subheader("2 · From reported to underlying net income")
    _bridge(app, values, answers)

    st.subheader("3 · Your verdict")
    with st.form("s6-rating"):
        opts = ["High", "Medium", "Low"]
        rating = st.radio("Overall earnings quality", opts, index=opts.index(answers["rating"]) if answers.get("rating") in opts else None, horizontal=True, key="s6-rating-r")
        why = st.text_area("Justify with at least two pieces of evidence from your checks.", value=answers.get("rating_why", ""), height=110, key="s6-rating-why")
        if st.form_submit_button("Submit verdict", type="primary", icon=":material/send:"):
            if rating is None or CA.word_count(why) < 15:
                st.warning("Choose a rating and justify it in at least 15 words.")
            else:
                answers.update({"rating": rating, "rating_why": why.strip()})
                app.save()
                st.rerun()
    if answers.get("rating"):
        evs = [e for e in app.profile.get("events", []) if e.get("nature") in ("one-off", "accounting", "transitional", "acquisition")]
        if evs:
            st.markdown("**Analyst notes on items that affect earnings quality** — did your checks catch them?")
            for e in evs:
                st.markdown(f"- **{e['year']} · {e['title']}** ({CA.NATURE_LABEL.get(e['nature'], '')}): {e['detail']}")
        st.caption("There is no single right rating — what matters is that your evidence supports it.")

    stage_footer(app, NUMBER, _criteria(app, answers))


def _cash_panel(app: AppContext, values: pd.DataFrame) -> None:
    ni = D.series(values, "net_income")
    with st.container(border=True):
        if app.sector == "bank":
            dps, sh = D.series(values, "dps"), D.series(values, "shares_outstanding")
            div = (dps * sh).reindex(ni.index)
            series = {"Net income": ni, "Dividends declared (DPS × shares)": div}
            ui.plotly(viz.compare_lines({k: v for k, v in series.items() if v.notna().sum() >= 2}, "Profit vs dividends declared", f"{app.currency} m"), key="s6-bank-cash")
            c1 = D.series(values, "cet1_capital")
            if c1.notna().sum() >= 2:
                st.caption("CET1 capital over the same years — does it grow with retained profit?")
                ui.plotly(viz.history_line(c1, "CET1 capital", f"{app.currency} m"), key="s6-cet1")
            st.caption("Banks: compare profit with distributions and capital build-up rather than with operating cash flow.")
        else:
            ocf = D.series(values, "operating_cash_flow")
            if ocf.notna().sum() >= 2:
                lines = {"Net income": ni, "Operating cash flow": ocf}
                capex = D.series(values, "capex")
                if app.sector == "corporate" and capex.notna().sum() >= 2:
                    lines["Free cash flow (OCF − capex)"] = (ocf - capex.reindex(ocf.index))
                ui.plotly(viz.compare_lines({k: v for k, v in lines.items() if v.notna().sum() >= 2}, "Net income vs operating cash flow", f"{app.currency} m"), key="s6-ocf")
                cum_ni, cum_ocf = ni.dropna().sum(), ocf.dropna().sum()
                st.caption(f"Cumulative over the period: net income {C.fmt_num(cum_ni)} vs operating cash flow {C.fmt_num(cum_ocf)} ({app.currency} m).")
            else:
                st.caption("No operating cash flow data — add it in Stage 2 if the company publishes a cash flow statement.")


def _bridge(app: AppContext, values: pd.DataFrame, answers: dict) -> None:
    years = [y for y in D.year_columns(values) if D.value(values, "net_income", y) is not None]
    if not years:
        st.info("Net income missing.")
        return
    year = st.selectbox("Year", years[::-1], index=0, key="s6-year")
    ni = D.value(values, "net_income", year)
    items = answers.setdefault("bridge", {}).get(str(year))
    if items is None:
        items = []
    df = pd.DataFrame(items or [{"Item": "", "Pre-tax amount": np.nan, "Gain or loss": "Gain", "Tax rate %": 20.0}])
    st.caption("List one-off items you found. Gains are removed, losses added back — after tax. Leave the table empty if you found none.")
    with st.form(f"s6-bridge-{year}"):
        edited = st.data_editor(
            df,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "Item": st.column_config.TextColumn(width="large"),
                "Pre-tax amount": st.column_config.NumberColumn(f"Pre-tax amount ({app.currency} m)", format="localized"),
                "Gain or loss": st.column_config.SelectboxColumn(options=["Gain", "Loss"]),
                "Tax rate %": st.column_config.NumberColumn(min_value=0.0, max_value=60.0, format="%.1f"),
            },
            key=f"s6-bridge-ed-{year}-{st.session_state.get('s6-ver', 0)}",
        )
        saved = st.form_submit_button("Save bridge", icon=":material/save:")
    if saved:
        rows = [r for r in edited.to_dict("records") if str(r.get("Item") or "").strip() and pd.notna(r.get("Pre-tax amount"))]
        for r in rows:
            r["Tax rate %"] = 0.0 if pd.isna(r.get("Tax rate %")) else float(r["Tax rate %"])
            r["Pre-tax amount"] = float(r["Pre-tax amount"])
        answers["bridge"][str(year)] = rows
        answers["bridge_saved"] = True
        app.save()
        st.session_state["s6-ver"] = st.session_state.get("s6-ver", 0) + 1  # fresh editor, no stale row edits
        st.rerun()
    steps = [("Reported net income", ni, "absolute")]
    underlying = ni
    for r in items:
        after_tax = r["Pre-tax amount"] * (1 - r["Tax rate %"] / 100)
        adj = -after_tax if r["Gain or loss"] == "Gain" else after_tax
        underlying += adj
        steps.append((str(r["Item"])[:28], adj, "relative"))
    steps.append(("Underlying net income", underlying, "total"))
    if answers.get("bridge_saved") and str(year) in answers.get("bridge", {}):
        ui.plotly(viz.waterfall(steps, f"{year}: reported → underlying net income", f"{app.currency} m"), key=f"s6-wf-{year}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Reported", C.fmt_num(ni))
        k2.metric("Underlying", C.fmt_num(underlying))
        k3.metric("Adjustments", f"{(underlying / ni - 1) * 100:+.1f} %" if ni else "–")
        eq = D.series(values, "total_equity")
        if year - 1 in eq.index and year in eq.index and not eq[[year - 1, year]].isna().any():
            avg = (eq[year - 1] + eq[year]) / 2
            st.caption(f"ROE reported {ni / avg * 100:.1f} % vs underlying {underlying / avg * 100:.1f} % — use the underlying figure for valuation (Stage 9).")
        if answers.setdefault("underlying", {}).get(str(year)) != underlying:
            answers["underlying"][str(year)] = underlying
            app.save()
