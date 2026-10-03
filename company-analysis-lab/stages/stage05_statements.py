"""Stage 5 — Financial Statement Investigation (Analyse der Jahresrechnung)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from lab import calculations as C
from lab import company_analysis as CA
from lab import data as D
from lab import metrics as M
from lab import ui
from stages.common import AppContext, record_attempt, stage_footer, stage_header

NUMBER = 5
MIN_WORDS = 12
N_INVESTIGATE = 3

LOCATIONS = [
    "Income statement",
    "Balance sheet",
    "Cash flow statement",
    "Statement of changes in equity",
    "Statement of comprehensive income (OCI)",
    "Notes – accounting policies / changes in standards",
    "Notes – segment reporting",
    "Notes – business combinations / acquisitions",
    "Notes – provisions, litigation, contingent liabilities",
    "Notes – financial instruments / fair value",
    "Notes – insurance contracts / reserves",
    "Risk report / capital management (Pillar 3, SST, SFCR)",
    "Management report (Lagebericht)",
    "Auditor's report – key audit matters",
]

# What each event type should map to (used to give feedback on the learner's classification)
EXPECTED = {
    "one-off": ("Accounting-driven", "One-off"),
    "accounting": ("Accounting-driven", "One-off"),
    "operational": ("Operational", "Recurring"),
    "structural": ("Operational", "One-off"),
    "transitional": ("Both", "Partly"),
    "regulatory": ("Operational", "Partly"),
    "acquisition": ("Both", "One-off"),
    "capital": ("Operational", "Recurring"),
}


def statement_sections(app: AppContext) -> list[dict]:
    bank = app.sector == "bank"
    return [
        {
            "key": "is", "en": "Income statement", "de": "Erfolgsrechnung",
            "shows": "Revenues, expenses and profit over the year." + (" For banks: net interest income, fees, trading, operating expenses, credit losses." if bank else " For insurers (IFRS 17): insurance revenue, insurance service expenses, insurance finance result, investment result."),
            "look": (["Which revenue line drives the change?", "Credit loss expense — build or release?", "Any line called 'other' that is unusually large?", "Effective tax rate vs statutory rate"] if bank else
                     ["Insurance service result vs investment result", "Large catastrophe or reserve effects", "Realised gains on investments", "Effective tax rate"]),
            "task": "Which line of the income statement explains most of the change in net income in the latest year? Name it, give the size and say why it moved.",
        },
        {
            "key": "bs", "en": "Balance sheet", "de": "Bilanz",
            "shows": "What the company owns and how it is funded at year-end." + (" Banks are funded mainly by deposits and debt; equity is a thin layer." if bank else " Insurers' balance sheets are dominated by investments and insurance contract liabilities (IFRS 17: incl. the CSM)."),
            "look": (["Funding mix: deposits vs wholesale debt", "Loan book vs deposits (liquidity)", "Goodwill and intangibles (deducted from CET1)", "Level 3 assets"] if bank else
                     ["Investment mix (bonds, equities, real estate)", "Insurance liabilities and the CSM", "Unit-linked assets held for policyholders", "Goodwill and intangibles"]),
            "task": "How is the balance sheet funded? Describe the two largest liability items and what share of total assets is equity.",
        },
        {
            "key": "cf", "en": "Cash flow statement", "de": "Geldflussrechnung",
            "shows": "Cash flows from operating, investing and financing activities.",
            "look": (["Why operating cash flow swings with deposits, loans and trading balances", "Dividends and buybacks in financing cash flows", "Do not use OCF to judge a bank's earnings quality"] if bank else
                     ["Reconciliation from net income to operating cash flow", "Where investment purchases/sales are classified", "Dividends and buybacks"]),
            "task": ("Why is a bank's operating cash flow a poor measure of its earnings quality? Use your company's numbers in the answer." if bank else
                     "Reconcile net income to operating cash flow in the latest year: what are the two largest reconciling items?"),
        },
        {
            "key": "soce", "en": "Statement of changes in equity", "de": "Eigenkapitalnachweis",
            "shows": "Every movement in equity: net income, dividends, share buybacks, other comprehensive income (OCI), FX translation, acquisitions of minorities.",
            "look": ["Dividends paid vs net income", "Share buybacks (treasury shares)", "OCI — unrealised gains/losses", "Transactions with non-controlling interests"],
            "task": "Explain the 'other movements' in the equity roll-forward below — which items does the statement of changes in equity show?",
        },
        {
            "key": "notes", "en": "Notes", "de": "Anhang",
            "shows": "Accounting policies, key estimates and judgements, segment information and details behind every line.",
            "look": (["Significant estimates: expected credit losses, fair value Level 3, provisions, goodwill", "Changes in accounting policies or restatements", "Segment profitability", "Litigation provisions and contingent liabilities"] if bank else
                     ["Significant estimates: insurance liabilities, discount rates, CSM, investment valuation", "Changes in accounting policies (IFRS 17/9 transition)", "Segment profitability", "Sensitivity analyses"]),
            "task": "Name the two or three most important accounting estimates or judgements disclosed in the notes, and say why each could change profit.",
        },
        {
            "key": "audit", "en": "Auditor's report", "de": "Bericht der Revisionsstelle",
            "shows": "The auditor's opinion and the key audit matters (KAMs) — the areas of highest risk of material misstatement.",
            "look": ["Opinion: unqualified, qualified, adverse or disclaimer?", "Key audit matters and how the auditor addressed them", "Emphasis of matter / going concern paragraphs", "Who is the auditor and since when?"],
            "task": "List the key audit matters and explain in one sentence why each is risky for this company.",
        },
    ]


def _changes(app: AppContext, values: pd.DataFrame) -> list[dict]:
    exclude = {"operating_cash_flow", "total_liabilities"}
    ch = C.unusual_changes(values, exclude=exclude)
    if len(ch) < N_INVESTIGATE:
        seen = {(c["metric"], c["year"]) for c in ch}
        ch += [c for c in C.unusual_changes(values, rel_threshold=8.0, pp_threshold=1.0, exclude=exclude) if (c["metric"], c["year"]) not in seen]
    return ch[:8]


def _criteria(app: AppContext, answers: dict, n_changes: int) -> list[tuple[str, bool]]:
    secs = statement_sections(app)
    done_secs = sum(1 for s in secs if CA.word_count(answers.get("sections", {}).get(s["key"], "")) >= MIN_WORDS)
    needed = min(N_INVESTIGATE, n_changes)
    inv = sum(1 for v in answers.get("investigations", {}).values() if v.get("submitted"))
    opinion = bool(answers.get("audit_opinion"))
    return [
        (f"All six parts of the annual report worked through — {done_secs}/6", done_secs == 6),
        ("Audit opinion type identified", opinion),
        (f"Unusual changes investigated — {inv}/{needed}", inv >= needed),
    ]


def render(app: AppContext) -> None:
    stage_header(app, NUMBER)
    values = app.values
    state = app.state(NUMBER)
    answers = state["answers"]
    answers.setdefault("sections", {})
    answers.setdefault("investigations", {})
    changes = _changes(app, values)

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        ui.task_box(
            "Headline numbers are where analysis <b>starts</b>. Open the annual report and work through each part below, then investigate the "
            "unusual changes the app found in your dataset: <b>what caused it, is it operational or accounting-driven, recurring or one-off, and where can you verify it?</b>"
        )
    with c2:
        ui.cfa_box("statement_links")

    tab_parts, tab_inv = st.tabs(["Work through the annual report", f"Investigate unusual changes ({len(changes)})"])
    with tab_parts:
        _sections(app, values, answers)
    with tab_inv:
        _investigations(app, values, answers, changes)

    stage_footer(app, NUMBER, _criteria(app, answers, len(changes)))


def _sections(app: AppContext, values: pd.DataFrame, answers: dict) -> None:
    secs = statement_sections(app)
    for s in secs:
        done = CA.word_count(answers["sections"].get(s["key"], "")) >= MIN_WORDS
        with st.expander(f"{'✓' if done else '○'}  {s['en']} · {s['de']}", expanded=not done and s["key"] == next((x["key"] for x in secs if CA.word_count(answers["sections"].get(x["key"], "")) < MIN_WORDS), None)):
            st.markdown(f"**What it shows:** {s['shows']}")
            st.markdown("**What to look for:**\n" + "\n".join(f"- {x}" for x in s["look"]))
            if s["key"] == "soce":
                _equity_rollforward(app, values)
            if s["key"] == "cf":
                _cash_vs_profit(app, values)
            if s["key"] == "notes":
                ui.cfa_box("notes")
            if s["key"] == "audit":
                ui.cfa_box("auditor")
                opts = ["Unqualified (clean)", "Qualified", "Adverse", "Disclaimer of opinion"]
                cur = answers.get("audit_opinion")
                op = st.radio("Type of audit opinion in the latest annual report", opts, index=opts.index(cur) if cur in opts else None, horizontal=True, key="s5-opinion")
                if op != cur and op is not None:
                    answers["audit_opinion"] = op
                    app.save()
            with st.form(f"s5-sec-{s['key']}"):
                txt = st.text_area(f"Your task: {s['task']}", value=answers["sections"].get(s["key"], ""), height=110, key=f"s5-sec-txt-{s['key']}")
                if st.form_submit_button("Save", icon=":material/save:"):
                    if CA.word_count(txt) < MIN_WORDS:
                        st.warning(f"Write at least {MIN_WORDS} words.")
                    else:
                        answers["sections"][s["key"]] = txt.strip()
                        app.save()
                        st.rerun()
            if done and s["key"] == "audit" and app.profile.get("audit_focus"):
                st.info("**Typical key audit matters for this company** (compare with what you found):\n" + "\n".join(f"- {k}" for k in app.profile["audit_focus"]), icon=":material/menu_book:")
                if answers.get("audit_opinion") and answers["audit_opinion"] != "Unqualified (clean)":
                    st.warning("A modified opinion is rare for large listed financial groups — double-check the opinion paragraph.", icon=":material/warning:")


def _equity_rollforward(app: AppContext, values: pd.DataFrame) -> None:
    years = D.year_columns(values)
    rows = []
    for y in years[1:]:
        r = C.implied_other_equity_movements(values, y)
        if r:
            rows.append({"Year": str(y), "Opening equity": r["opening"], "+ Net income": r["net_income"], "− Dividends paid (est.)": -r["dividends"], "± Other movements": r["other"], "= Closing equity": r["closing"]})
    if rows:
        st.markdown("**Equity roll-forward from your dataset** (dividends ≈ prior-year DPS × shares)")
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, column_config={c: st.column_config.NumberColumn(format="localized") for c in df.columns if c != "Year"})
        st.caption("Large 'other movements' = buybacks, OCI (e.g. unrealised bond losses), FX translation, acquisitions of minorities, share-based payments. Find them in the statement of changes in equity.")


def _cash_vs_profit(app: AppContext, values: pd.DataFrame) -> None:
    ni, ocf = D.series(values, "net_income"), D.series(values, "operating_cash_flow")
    if ocf.notna().sum() >= 2:
        df = pd.DataFrame({"Year": [str(y) for y in ni.index], "Net income": ni.values, "Operating cash flow": ocf.reindex(ni.index).values})
        st.dataframe(df, hide_index=True, column_config={c: st.column_config.NumberColumn(format="localized") for c in ["Net income", "Operating cash flow"]})
        ui.cfa_box("accruals")


def _investigations(app: AppContext, values: pd.DataFrame, answers: dict, changes: list[dict]) -> None:
    if not changes:
        st.info("No large changes found in your dataset — complete more metrics in Stage 2.")
        return
    st.caption(f"Investigate at least {min(N_INVESTIGATE, len(changes))}. They are ranked by size and importance. Write your hypothesis first — the analyst notes appear after you submit.")
    labels = []
    for c in changes:
        mv = "sign change" if c.get("sign_flip") else (f"{c['change']:+.1f} {c['unit']}" if np.isfinite(c["change"]) else "large change")
        done = answers["investigations"].get(f"{c['metric']}|{c['year']}", {}).get("submitted")
        labels.append(f"{'✓' if done else '○'}  {M.short(c['metric'], app.custom_metrics)} {c['year']}: {mv}")
    idx = st.radio("Unusual changes", list(range(len(changes))), format_func=lambda i: labels[i], key="s5-change", label_visibility="collapsed", horizontal=False)
    c = changes[idx]
    key = f"{c['metric']}|{c['year']}"
    inv = answers["investigations"].setdefault(key, {})
    with st.container(border=True):
        st.markdown(f"### {M.short(c['metric'], app.custom_metrics)} · {c['year'] - 1} → {c['year']}")
        k1, k2, k3 = st.columns(3)
        k1.metric(str(c["year"] - 1), C.fmt_metric(c["from"], c["metric"], app.currency))
        k2.metric(str(c["year"]), C.fmt_metric(c["to"], c["metric"], app.currency))
        k3.metric("Change", "sign change" if c.get("sign_flip") else f"{c['change']:+.1f} {c['unit']}")
        acc = app.profile.get("accounting", {})
        if acc.get(str(c["year"] - 1)) and acc.get(str(c["year"])) and acc[str(c["year"] - 1)] != acc[str(c["year"])]:
            st.warning(f"Hint: the accounting basis changed between these years ({acc[str(c['year'] - 1)]} → {acc[str(c['year'])]}).", icon=":material/lightbulb:")

        with st.form(f"s5-inv-{key}"):
            cause = st.text_area("What caused this number to change?", value=inv.get("cause", ""), height=100, key=f"s5-cause-{key}")
            a1, a2 = st.columns(2)
            nat_opts = ["Operational", "Accounting-driven", "Both", "Not sure yet"]
            rec_opts = ["Recurring", "One-off", "Partly"]
            nature = a1.radio("Is the change operational or accounting-driven?", nat_opts, index=nat_opts.index(inv["nature"]) if inv.get("nature") in nat_opts else None, key=f"s5-nat-{key}")
            recur = a2.radio("Is it recurring or one-off?", rec_opts, index=rec_opts.index(inv["recur"]) if inv.get("recur") in rec_opts else None, key=f"s5-rec-{key}")
            where = st.multiselect("Where in the annual report could you verify this?", LOCATIONS, default=inv.get("where", []), key=f"s5-where-{key}")
            ref = st.text_input("Page / note reference (optional)", value=inv.get("ref", ""), key=f"s5-ref-{key}")
            go = st.form_submit_button("Submit my investigation", type="primary", icon=":material/send:")
        if go:
            if CA.word_count(cause) < MIN_WORDS or nature is None or recur is None or not where:
                st.warning(f"Explain the cause (≥ {MIN_WORDS} words), classify it twice and pick at least one place to verify it.")
            else:
                inv.update({"cause": cause.strip(), "nature": nature, "recur": recur, "where": where, "ref": ref, "submitted": True})
                app.save()
                st.rerun()

        if inv.get("submitted"):
            _investigation_feedback(app, c, inv)


def _investigation_feedback(app: AppContext, c: dict, inv: dict) -> None:
    evs = CA.events_for(app.profile, c["metric"], c["year"])
    st.markdown("**Feedback**")
    covered, missed = CA.keyword_coverage(inv.get("cause", ""), CA.EXPLANATION_DRIVERS)
    ui.coverage_feedback(covered, missed[:4], "Your explanation covers", "Other common drivers")
    if not evs:
        st.info(
            "No analyst note for this change. Test your hypothesis: (1) does the management report confirm it? (2) does the segment note show where it happened? "
            "(3) is there a matching item in the statement of changes in equity or the notes? If two sources agree, your explanation is probably right.",
            icon=":material/search:",
        )
        return
    for ev in evs:
        exp_nature, exp_recur = EXPECTED.get(ev.get("nature"), ("Both", "Partly"))
        ok_n = inv["nature"] == exp_nature or inv["nature"] == "Both" or exp_nature == "Both"
        ok_r = inv["recur"] == exp_recur or inv["recur"] == "Partly" or exp_recur == "Partly"
        record_attempt(app, NUMBER, f"inv-{c['metric']}-{c['year']}", "operational_vs_accounting", ok_n and ok_r)
        with st.container(border=True):
            st.markdown(f"**Analyst note — {ev['year']}: {ev['title']}** · _{CA.NATURE_LABEL.get(ev.get('nature'), '')}_")
            st.markdown(ev["detail"])
            st.markdown(f"**Where to verify:** {ev.get('where_to_verify', '')}")
            st.markdown(
                f"Your classification: **{inv['nature']} / {inv['recur']}** · analyst view: **{exp_nature} / {exp_recur}** "
                + ("✓" if ok_n and ok_r else "— think again about why they differ")
            )
