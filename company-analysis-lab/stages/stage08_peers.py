"""Stage 8 — Peer Comparison (Peer-Vergleich)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lab import company_analysis as CA
from lab import data as D
from lab import metrics as M
from lab import ratios as R
from lab import ui
from lab import visualization as viz
from stages.common import AppContext, stage_footer, stage_header

NUMBER = 8
PREDICT = ["Target higher", "Peer higher", "About the same"]


def ratio_series(values: pd.DataFrame, key: str) -> pd.Series:
    rd = R.RATIOS[key]
    return pd.Series({y: R.compute(rd, values, y).value for y in D.year_columns(values)}, dtype=float).dropna()


def comparison_set(sector_a: str, sector_b: str) -> list[dict]:
    """Metrics that are meaningful for this pair — not every ratio for every pair."""
    common = [
        {"key": "roe", "kind": "ratio", "label": "Return on equity", "unit": "%", "why": "Profitability for shareholders — comparable across sectors."},
        {"key": "payout", "kind": "ratio", "label": "Dividend payout ratio", "unit": "%", "why": "How much profit is distributed."},
        {"key": "net_income", "kind": "indexed", "label": "Net income growth (indexed)", "unit": "index", "why": "Growth path, independent of size and currency."},
        {"key": "total_equity", "kind": "indexed", "label": "Book value growth (indexed)", "unit": "index", "why": "Growth of shareholders' equity."},
    ]
    if sector_a == sector_b == "bank":
        return common[:1] + [
            {"key": "roa", "kind": "ratio", "label": "Return on assets", "unit": "%", "why": "Profitability per unit of balance sheet."},
            {"key": "cost_income", "kind": "ratio", "label": "Cost/income ratio", "unit": "%", "why": "Efficiency (lower is better)."},
            {"key": "cet1_ratio", "kind": "metric", "label": "CET1 ratio", "unit": "%", "why": "Capital strength — note different regulatory regimes (Swiss TBTF vs EEA CRR)."},
            {"key": "leverage", "kind": "ratio", "label": "Financial leverage", "unit": "×", "why": "How much ROE comes from leverage."},
            {"key": "fee_share", "kind": "ratio", "label": "Fee income share", "unit": "%", "why": "Business mix: capital-light fees vs interest."},
            {"key": "nii_share", "kind": "ratio", "label": "Net interest income share", "unit": "%", "why": "Sensitivity to interest rates."},
        ] + common[1:]
    if sector_a == sector_b == "insurer":
        return common[:1] + [
            {"key": "roa", "kind": "ratio", "label": "Return on assets", "unit": "%", "why": "Profitability per unit of balance sheet (depends on unit-linked assets)."},
            {"key": "solvency_ratio", "kind": "metric", "label": "Solvency ratio", "unit": "%", "why": "Capital strength — SST and Solvency II ratios are not identical frameworks."},
            {"key": "leverage", "kind": "ratio", "label": "Financial leverage", "unit": "×", "why": "Balance-sheet leverage."},
            {"key": "investment_share", "kind": "ratio", "label": "Investment income share", "unit": "%", "why": "Dependence on investment returns."},
            {"key": "combined_ratio", "kind": "metric", "label": "Combined ratio", "unit": "%", "why": "Only meaningful if both write P&C business."},
        ] + common[1:]
    return common + [{"key": "equity_ratio", "kind": "ratio", "label": "Equity / total assets", "unit": "%", "why": "Rough leverage — but bank and insurer balance sheets are structurally different."}]


def series_for(item: dict, values: pd.DataFrame) -> pd.Series:
    if item["kind"] == "ratio":
        return ratio_series(values, item["key"])
    s = D.series(values, item["key"]).dropna()
    if item["kind"] == "indexed" and len(s) and s.iloc[0] > 0:
        return s / s.iloc[0] * 100
    return s if item["kind"] == "metric" else pd.Series(dtype=float)


def _criteria(answers: dict) -> list[tuple[str, bool]]:
    return [
        ("Peer selected and comparability assessed", bool(answers.get("peer_id")) and bool(answers.get("comparability_note"))),
        ("Predictions made before seeing the comparison", bool(answers.get("predicted"))),
        ("Biggest difference explained", CA.word_count(answers.get("explanation", "")) >= 25),
    ]


def render(app: AppContext) -> None:
    stage_header(app, NUMBER)
    values = app.values
    state = app.state(NUMBER)
    answers = state["answers"]

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        ui.task_box(
            "Choose a peer, check how comparable it really is, <b>predict</b> where the two differ — then look at the side-by-side 5-year trends. "
            "The app only compares metrics that make sense for the pair (a bank's CET1 ratio is not comparable with an insurer's solvency ratio)."
        )
    with c2:
        ui.cfa_box("peers")

    others = [c for c in D.list_companies() if c["id"] != app.company_id]
    ids = [c["id"] for c in others]
    by_id = {c["id"]: c for c in others}
    suggested = [p for p in app.profile.get("peers_suggested", []) if p in ids]
    current = answers.get("peer_id") if answers.get("peer_id") in ids else (suggested[0] if suggested else ids[0])
    peer_id = st.selectbox("Peer company", ids, index=ids.index(current), format_func=lambda i: f"{by_id[i]['short_name']} · {by_id[i]['sector']}" + ("  (suggested)" if i in suggested else ""), key="s8-peer")
    if peer_id != answers.get("peer_id"):
        answers.update({"peer_id": peer_id, "predicted": False, "predictions": {}})
        app.save()
    peer = D.load_profile(peer_id)
    pvalues, _ = D.load_working(peer_id)
    name_a, name_b = app.name, peer["short_name"]
    colors = {name_a: viz.SERIES[0], name_b: viz.SERIES[1]}

    # comparability
    st.subheader("1 · How comparable are they?")
    acc_a = sorted(set(app.profile.get("accounting", {}).values()))
    acc_b = sorted(set(peer.get("accounting", {}).values()))
    from lab import storage
    peer_currency = storage.load_progress(peer_id).get("settings", {}).get("currency") or peer.get("currency")
    rows = [
        ("Business model", app.profile.get("subsector", ""), peer.get("subsector", ""), app.sector == peer["sector"]),
        ("Sector", app.sector, peer["sector"], app.sector == peer["sector"]),
        ("Reporting currency", app.currency, peer_currency, app.currency == peer_currency),
        ("Accounting basis", ", ".join(acc_a), ", ".join(acc_b), acc_a == acc_b),
        ("Listed", "yes" if app.profile.get("listed") else "no", "yes" if peer.get("listed") else "no", app.profile.get("listed") == peer.get("listed")),
        ("Regulator / regime", app.profile.get("capital_regime", ""), peer.get("capital_regime", ""), app.profile.get("capital_regime") == peer.get("capital_regime")),
    ]
    st.dataframe(pd.DataFrame([{"Dimension": r[0], name_a: r[1], name_b: r[2], "Same?": "✓" if r[3] else "⚠"} for r in rows]), hide_index=True)
    if app.sector != peer["sector"]:
        st.warning("Cross-sector comparison: only ROE, payout, growth and simple leverage are shown. Capital ratios (CET1 vs solvency) measure different things.", icon=":material/warning:")
    if peer_currency != app.currency:
        st.info("Different reporting currencies: compare ratios and indexed growth, never absolute amounts.", icon=":material/currency_exchange:")
    missing_peer = [k for k in D.required_metric_keys(peer) if k not in pvalues.index or pvalues.loc[k].isna().all()]
    if missing_peer:
        st.caption(f"Peer data gaps: {', '.join(M.short(k) for k in missing_peer)} — switch to {name_b} and complete its Stage 2 to fill them.")
    with st.form("s8-comp"):
        note = st.text_area("Which differences limit this comparison, and how will you deal with them?", value=answers.get("comparability_note", ""), height=80)
        if st.form_submit_button("Save", icon=":material/save:"):
            if CA.word_count(note) < 10:
                st.warning("Write at least 10 words.")
            else:
                answers["comparability_note"] = note.strip()
                app.save()
                st.rerun()

    items = comparison_set(app.sector, peer["sector"])
    items = [it for it in items if len(series_for(it, values)) >= 2 or len(series_for(it, pvalues)) >= 2]

    # predictions
    st.subheader("2 · Predict first")
    pred_items = [it for it in items if it["kind"] != "indexed"][:3]
    if not answers.get("predicted"):
        with st.form("s8-predict"):
            st.caption("Based on what you know about both business models — before looking at the numbers.")
            for it in pred_items:
                st.radio(f"{it['label']}: which is higher in the latest year?", PREDICT, index=None, horizontal=True, key=f"s8-p-{it['key']}")
            reason = st.text_area("Why do you expect these differences?", height=80, key="s8-p-why")
            if st.form_submit_button("Lock in my predictions", type="primary", icon=":material/lock:"):
                preds = {it["key"]: st.session_state.get(f"s8-p-{it['key']}") for it in pred_items}
                if any(v is None for v in preds.values()) or CA.word_count(reason) < 10:
                    st.warning("Answer every prediction and give a reason (≥ 10 words).")
                else:
                    answers.update({"predicted": True, "predictions": preds, "prediction_why": reason.strip()})
                    app.save()
                    st.rerun()
        st.info("The comparison appears after you lock in your predictions.", icon=":material/lock:")
        stage_footer(app, NUMBER, _criteria(answers))
        return

    # reveal
    st.subheader("3 · Side by side — 5-year trends")
    summary = []
    for it in items:
        sa, sb = series_for(it, values), series_for(it, pvalues)
        latest = sorted(set(sa.index) & set(sb.index))
        actual = None
        if latest:
            y = latest[-1]
            a, b = sa[y], sb[y]
            actual = "About the same" if abs(a - b) <= 0.05 * max(abs(a), abs(b), 1e-9) else ("Target higher" if a > b else "Peer higher")
            summary.append({"Metric": it["label"], "Year": str(y), name_a: round(a, 2), name_b: round(b, 2), "Your prediction": answers.get("predictions", {}).get(it["key"], "—"), "Actual": actual})
    if summary:
        df = pd.DataFrame(summary)
        st.dataframe(df, hide_index=True)
        hits = sum(1 for r in summary if r["Your prediction"] == r["Actual"])
        n_pred = sum(1 for r in summary if r["Your prediction"] != "—")
        st.caption(f"Predictions correct: {hits}/{n_pred}. Misses are the interesting part — what did you not know?")
    cols = st.columns(2)
    for i, it in enumerate(items):
        sa, sb = series_for(it, values), series_for(it, pvalues)
        with cols[i % 2]:
            series = {k: v for k, v in {name_a: sa, name_b: sb}.items() if len(v)}
            ui.plotly(viz.compare_lines(series, it["label"], it["unit"], colors), key=f"s8-ch-{it['key']}")
            st.caption(it["why"])

    st.subheader("4 · Explain the biggest difference")
    with st.form("s8-explain"):
        text = st.text_area("Which difference matters most for valuation, and what explains it (business model, capital, accounting, one-offs)?", value=answers.get("explanation", ""), height=120)
        if st.form_submit_button("Submit", type="primary", icon=":material/send:"):
            if CA.word_count(text) < 25:
                st.warning("Write at least 25 words.")
            else:
                answers["explanation"] = text.strip()
                app.save()
                st.rerun()
    if CA.word_count(answers.get("explanation", "")) >= 25:
        covered, missed = CA.keyword_coverage(answers["explanation"], [
            {"point": "Business model / mix", "keywords": ["business model", "mix", "fee", "wealth", "reinsur", "life", "geschäftsmodell"]},
            {"point": "Capital and leverage", "keywords": ["capital", "kapital", "leverage", "cet1", "solvency", "solvenz"]},
            {"point": "Accounting differences", "keywords": ["ifrs", "gaap", "accounting", "rechnungslegung"]},
            {"point": "One-off effects", "keywords": ["one-off", "einmal", "goodwill", "acquisition", "restructur"]},
            {"point": "Link to valuation (P/B, ROE vs cost of equity)", "keywords": ["p/b", "price-to-book", "valuation", "bewertung", "cost of equity", "multiple"]},
        ])
        ui.coverage_feedback(covered, missed)
        ui.cfa_box("justified_pb")

    stage_footer(app, NUMBER, _criteria(answers))
