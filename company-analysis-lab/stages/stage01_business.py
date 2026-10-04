"""Stage 1 — Understand the Business (Geschäftsmodell verstehen)."""

from __future__ import annotations

import streamlit as st

from lab import company_analysis as CA
from lab import ui
from stages.common import AppContext, stage_footer, stage_header

NUMBER = 1
MIN_WORDS = 10

QUESTIONS = [
    {
        "key": "what_it_does",
        "en": "What does the company actually do?",
        "de": "Was macht das Unternehmen konkret?",
        "hint": "Annual report: 'At a glance', the CEO/Chair letter and the strategy section.",
        "think": {"bank": "Is it a universal bank, a wealth manager, a retail bank? Which activity defines it?", "insurer": "Life, non-life, reinsurance? Savings products or pure risk cover? Does it also manage assets for others?", "corporate": "Which products or services? Who uses them and for what? Which division or product line defines the company?"},
    },
    {
        "key": "how_money",
        "en": "How does it make money?",
        "de": "Wie verdient es Geld?",
        "hint": "Income statement plus the notes on revenues (interest, fees, trading — insurance revenue, investment result — or sales by product and region).",
        "think": {"bank": "Split operating income into interest, fees and trading. Which is largest? Which is most stable? What drives each one?", "insurer": "Underwriting result vs investment result vs fees. Who bears the investment risk? Where does the 'float' come from?", "corporate": "Product sales, services, licences or royalties? One-off sales or recurring revenue? What sets the price — patents, brand, cost?"},
    },
    {
        "key": "segments",
        "en": "What are its major business segments?",
        "de": "Welches sind die wichtigsten Geschäftssegmente?",
        "hint": "Segment reporting note (IFRS 8 'Operating segments') and the divisional sections of the management report.",
        "think": {"bank": "List each segment and note which one earns the most profit — not just revenue.", "insurer": "List each segment (by line of business or geography) and its share of profit.", "corporate": "List each division or segment with its share of sales and of operating profit — margins often differ a lot."},
    },
    {
        "key": "customers",
        "en": "Who are its customers?",
        "de": "Wer sind die Kunden?",
        "hint": "Strategy section and divisional descriptions; distribution channels.",
        "think": {"bank": "Private, wealthy, corporate, institutional? Through which channels?", "insurer": "Individuals, companies (group life), other insurers (reinsurance)? Via own agents, brokers, banks?", "corporate": "Consumers, professionals, businesses or governments? Who decides, who uses and who pays? Direct sales or distributors?"},
    },
    {
        "key": "markets",
        "en": "Which countries / markets does it operate in?",
        "de": "In welchen Ländern / Märkten ist es tätig?",
        "hint": "Geographic information in the segment note; operating income or invested assets by region.",
        "think": {"bank": "Where are the clients, where is the booking centre, where are the profits?", "insurer": "Where are premiums written, and where are the peak risks?", "corporate": "Where are sales earned and where are the costs incurred? Which currency mismatch does that create?"},
    },
    {
        "key": "advantages",
        "en": "What are its major competitive advantages?",
        "de": "Was sind die wichtigsten Wettbewerbsvorteile?",
        "hint": "Strategy section and market-position claims — note them now and test them with numbers in later stages.",
        "think": {"bank": "Scale, brand, client relationships, cost position, capital strength, regulatory licences?", "insurer": "Scale and diversification, distribution control, underwriting expertise, capital strength, ratings?", "corporate": "Patents, brand, technology, cost position, switching costs, distribution network, scale?"},
    },
    {
        "key": "threats",
        "en": "What could threaten the business model?",
        "de": "Was könnte das Geschäftsmodell bedrohen?",
        "hint": "Risk report / 'risk factors', outlook section, regulatory developments.",
        "think": {"bank": "Interest rates, regulation, competition, technology, reputation, market downturns?", "insurer": "Catastrophes, interest rates, longevity, regulation, pricing cycle, competition?", "corporate": "Competition, patent expiry, price regulation, the economic cycle, input costs, currency, technology shifts?"},
    },
]


def _criteria(answers: dict, submitted: bool) -> list[tuple[str, bool]]:
    n_answered = sum(1 for q in QUESTIONS if CA.word_count(answers.get(q["key"], "")) >= MIN_WORDS)
    n_sent = CA.sentence_count(answers.get("summary", ""))
    return [
        (f"All seven questions answered in your own words (≥ {MIN_WORDS} words each) — {n_answered}/7", n_answered == len(QUESTIONS)),
        (f"Business summary of 3–5 sentences — currently {n_sent}", 3 <= n_sent <= 5),
        ("Submitted and compared with the analyst reference", submitted),
    ]


def render(app: AppContext) -> None:
    stage_header(app, NUMBER)
    p = app.profile
    state = app.state(NUMBER)
    answers = state["answers"]
    submitted = bool(state["submitted"].get("business"))

    left, right = st.columns([3, 2], gap="large")
    with left:
        ui.task_box(
            "Open the latest annual report and answer each question <b>in your own words</b>. "
            "Write what you understood, not what you copied. You will only see the analyst reference <b>after</b> you submit.",
        )
        ui.cfa_box("business_model")
    with right:
        with st.container(border=True):
            st.markdown("**Company facts** · <span class='al-de'>Unternehmensdaten</span>", unsafe_allow_html=True)
            st.markdown(
                f"- **Headquarters:** {ui.esc(p.get('headquarters', ''))}, {ui.esc(p.get('country', ''))}\n"
                f"- **Listing:** {ui.esc(p.get('exchange_ticker') or ('Listed' if p.get('listed') else 'Not listed'))}\n"
                f"- **Reporting currency:** {ui.esc(app.currency)}\n"
                f"- **Regulator:** {ui.esc(p.get('regulator', '–'))}\n"
                f"- **Capital regime:** {ui.esc(p.get('capital_regime', '–'))}\n"
                f"- **Accounting:** {ui.esc(', '.join(sorted(set(p.get('accounting', {}).values()))) or '–')}"
            )
            if p.get("investor_relations"):
                st.link_button("Open investor relations", p["investor_relations"], icon=":material/open_in_new:")
            st.caption(p.get("annual_report_hint", ""))

    st.subheader("1 · Seven questions about the business")
    with st.form("stage1-form"):
        for i, q in enumerate(QUESTIONS, start=1):
            st.markdown(f"**{i}. {q['en']}** · <span class='al-de'>{q['de']}</span>", unsafe_allow_html=True)
            st.text_area(
                q["en"],
                value=answers.get(q["key"], ""),
                key=f"s1-{q['key']}",
                height=100,
                label_visibility="collapsed",
                placeholder=q["think"][app.sector],
                help=f"Where to look: {q['hint']}",
            )
        st.markdown("---")
        st.markdown("**2 · The business in your own words** · <span class='al-de'>Das Geschäft in eigenen Worten</span>", unsafe_allow_html=True)
        st.caption("3–5 sentences, as if explaining the company to a colleague who has never heard of it: what it does, how it earns money, for whom, where, and what makes it special.")
        st.text_area("Business summary", value=answers.get("summary", ""), key="s1-summary", height=140, label_visibility="collapsed")
        go = st.form_submit_button("Submit my answers", type="primary", icon=":material/send:")

    if go:
        for q in QUESTIONS:
            answers[q["key"]] = st.session_state.get(f"s1-{q['key']}", "").strip()
        answers["summary"] = st.session_state.get("s1-summary", "").strip()
        problems = [q["en"] for q in QUESTIONS if CA.word_count(answers[q["key"]]) < MIN_WORDS]
        n_sent = CA.sentence_count(answers["summary"])
        if problems:
            st.warning(f"Expand these answers to at least {MIN_WORDS} words: " + "; ".join(problems), icon=":material/edit_note:")
        if not 3 <= n_sent <= 5:
            st.warning(f"Your summary has {n_sent} sentence(s) — write 3 to 5.", icon=":material/edit_note:")
        if not problems and 3 <= n_sent <= 5:
            state["submitted"]["business"] = True
            submitted = True
            app.save()
            st.rerun()
        app.save()

    if submitted:
        _feedback(app, answers)

    stage_footer(app, NUMBER, _criteria(answers, submitted))


def _feedback(app: AppContext, answers: dict) -> None:
    ref = app.profile.get("business_reference", {})
    st.subheader("3 · Compare with the analyst reference")
    if not ref:
        st.info("No reference notes exist for this company yet. Compare your answers with the annual report's own description and with a peer.", icon=":material/info:")
        return
    st.caption("Keyword matching gives a rough first check (English and German). Read the reference and judge for yourself what you missed or what you saw that the reference does not mention.")
    for q in QUESTIONS:
        r = ref.get(q["key"])
        if not r:
            continue
        covered, missed = CA.keyword_coverage(answers.get(q["key"], ""), r.get("key_points", []))
        icon = ":material/check_circle:" if not missed else ":material/radio_button_partial:"
        with st.expander(f"{q['en']} — {len(covered)}/{len(covered) + len(missed)} key points", icon=icon):
            st.markdown(f"*Your answer:* {ui.esc(answers.get(q['key'], ''))}", unsafe_allow_html=True)
            ui.coverage_feedback(covered, missed)
            st.info(f"**Analyst reference:** {r['reference']}", icon=":material/menu_book:")

    all_points = ref.get("what_it_does", {}).get("key_points", []) + ref.get("how_money", {}).get("key_points", [])
    covered, missed = CA.keyword_coverage(answers.get("summary", ""), all_points)
    with st.container(border=True):
        st.markdown("**Your summary**")
        st.markdown(ui.esc(answers.get("summary", "")))
        st.caption(f"{CA.sentence_count(answers.get('summary', ''))} sentences · {CA.word_count(answers.get('summary', ''))} words")
        ui.coverage_feedback(covered, missed, "Your summary mentions", "A complete summary would also mention")
    ui.cfa_box("industry_analysis")
    if app.profile.get("id") == "prismalife":
        st.caption("PrismaLife reference notes are based on limited public information — your own knowledge of the company may be more accurate.")
