"""Stage 10 — Investment Thesis (Investment-These).

The learner must close the analysis with a structured thesis. The app gives no buy/sell verdict.
"""

from __future__ import annotations

import streamlit as st

from lab import company_analysis as CA
from lab import storage, ui
from stages.common import AppContext, stage_footer, stage_header

NUMBER = 10
MIN = 12  # words per section

SECTIONS = [
    ("summary", "Business summary", "Geschäftsmodell in Kürze"),
    ("trend", "Financial trend", "Finanzielle Entwicklung"),
    ("capital", "Capital strength", "Kapitalstärke"),
    ("valuation", "Valuation", "Bewertung"),
    ("change", "What would change my thesis?", "Was würde meine These ändern?"),
]
CASES = [("bull", "Bull case"), ("base", "Base case"), ("bear", "Bear case")]


def _prefill(app: AppContext) -> dict:
    """Starting points from earlier stages — the learner must rewrite/condense them."""
    st_ = app.progress.get("stages", {})
    s1 = st_.get("1", {}).get("answers", {})
    s7 = st_.get("7", {}).get("answers", {})
    s9 = st_.get("9", {}).get("answers", {})
    risk_names = {"credit": "Credit risk", "market": "Market risk", "interest": "Interest-rate risk", "liquidity": "Liquidity risk", "operational": "Operational risk",
                  "regulatory": "Regulatory risk", "concentration": "Concentration risk", "underwriting": "Underwriting risk"}
    risks = [f"{risk_names.get(k, k)}: {s7.get('top3', {}).get('why', {}).get(k, '')}" for k in s7.get("top3", {}).get("keys", [])]
    val = ""
    if s9.get("conclusion_submitted"):
        val = f"Value range {s9.get('range_lo')} – {s9.get('range_hi')}. {s9.get('conclusion', '')}"
    return {"summary": s1.get("summary", ""), "risks": risks, "valuation": val}


def _criteria(answers: dict) -> list[tuple[str, bool]]:
    t = answers.get("thesis", {})
    secs = all(CA.word_count(t.get(k, "")) >= MIN for k, _, _ in SECTIONS)
    reasons = all(CA.word_count(x) >= 5 for x in t.get("reasons", ["", "", ""])) and len(t.get("reasons", [])) == 3
    risks = all(CA.word_count(x) >= 5 for x in t.get("risks", ["", "", ""])) and len(t.get("risks", [])) == 3
    cases = all(CA.word_count(t.get(f"case_{k}", "")) >= 8 for k, _ in CASES)
    final = CA.word_count(t.get("chf10k", "")) >= 25
    return [
        ("Summary, financial trend, capital strength, valuation and thesis-breakers written", secs),
        ("Three reasons the company could perform well", reasons),
        ("Three major risks", risks),
        ("Bull, base and bear cases", cases),
        ("Answered: what else would you need before allocating CHF 10,000?", final and bool(answers.get("submitted"))),
    ]


def render(app: AppContext) -> None:
    stage_header(app, NUMBER)
    state = app.state(NUMBER)
    answers = state["answers"]
    t = answers.setdefault("thesis", {})
    pre = _prefill(app)

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        ui.task_box(
            "Finish like an analyst: a thesis that someone else could read in two minutes and check against reality later. "
            "Earlier answers are pre-filled where available — <b>condense and sharpen them</b>. "
            "There is deliberately no 'buy' or 'sell' button: the purpose is to make your reasoning, scenarios and uncertainties explicit."
        )
    with c2:
        ui.cfa_box("thesis")

    with st.form("s10-thesis"):
        vals = {}
        for key, en, de in SECTIONS[:1]:
            st.markdown(f"**{en}** · <span class='al-de'>{de}</span>", unsafe_allow_html=True)
            vals[key] = st.text_area(en, value=t.get(key) or pre.get(key, ""), height=100, label_visibility="collapsed", key=f"s10-{key}")
        st.markdown("**Three reasons the company could perform well** · <span class='al-de'>Drei Gründe für eine gute Entwicklung</span>", unsafe_allow_html=True)
        reasons = [st.text_input(f"Reason {i + 1}", value=(t.get("reasons") or ["", "", ""])[i], key=f"s10-r{i}") for i in range(3)]
        st.markdown("**Three major risks** · <span class='al-de'>Drei Hauptrisiken</span>", unsafe_allow_html=True)
        pre_risks = (t.get("risks") or pre["risks"] + ["", "", ""])[:3]
        risks = [st.text_input(f"Risk {i + 1}", value=pre_risks[i] if i < len(pre_risks) else "", key=f"s10-k{i}") for i in range(3)]
        for key, en, de in SECTIONS[1:4]:
            st.markdown(f"**{en}** · <span class='al-de'>{de}</span>", unsafe_allow_html=True)
            default = t.get(key) or (pre.get(key, "") if key == "valuation" else "")
            vals[key] = st.text_area(en, value=default, height=90, label_visibility="collapsed", key=f"s10-{key}")
        st.markdown("**Scenarios** · <span class='al-de'>Szenarien</span>", unsafe_allow_html=True)
        cols = st.columns(3)
        cases = {}
        for col, (k, label) in zip(cols, CASES):
            with col:
                cases[k] = st.text_area(label, value=t.get(f"case_{k}", ""), height=120, key=f"s10-c-{k}", placeholder="What has to happen? Which numbers move? Rough value?")
        key, en, de = SECTIONS[4]
        st.markdown(f"**{en}** · <span class='al-de'>{de}</span>", unsafe_allow_html=True)
        vals[key] = st.text_area(en, value=t.get(key, ""), height=90, label_visibility="collapsed", key=f"s10-{key}", placeholder="Specific, measurable thesis-breakers (number + time frame).")
        st.divider()
        st.markdown("### If you had CHF 10,000 to allocate, what additional information would you need before making an investment decision?")
        chf = st.text_area("Your answer", value=t.get("chf10k", ""), height=140, label_visibility="collapsed", key="s10-chf")
        go = st.form_submit_button("Submit my investment thesis", type="primary", icon=":material/send:")

    if go:
        t.update({**vals, "reasons": [r.strip() for r in reasons], "risks": [r.strip() for r in risks], **{f"case_{k}": v.strip() for k, v in cases.items()}, "chf10k": chf.strip()})
        crit = _criteria({"thesis": t, "submitted": True})
        missing = [label for label, ok in crit if not ok]
        app.save()
        if missing:
            st.warning("Still incomplete: " + "; ".join(missing) + f". (Sections need ≥ {MIN} words, reasons/risks ≥ 5, cases ≥ 8, the final answer ≥ 25.)")
        else:
            answers["submitted"] = True
            answers["submitted_at"] = storage.now_iso()
            app.save()
            st.rerun()

    if answers.get("submitted"):
        _reflection(app, t)
        md = thesis_markdown(app, t)
        st.download_button("Download my thesis (Markdown)", md, file_name=f"thesis_{app.company_id}.md", mime="text/markdown", icon=":material/download:")
        with st.expander("Preview", icon=":material/description:"):
            st.markdown(md)

    stage_footer(app, NUMBER, _criteria(answers))
    if CA.stage_complete(app.progress, NUMBER):
        if not answers.get("celebrated"):
            st.balloons()
            answers["celebrated"] = True
            app.save()
        st.success(f"You have completed the full analysis of {app.name}. Pick another company — or a peer — and do it again: the second time you will be much faster.", icon=":material/emoji_events:")


def _reflection(app: AppContext, t: dict) -> None:
    covered, missed = CA.keyword_coverage(t.get("chf10k", ""), [
        {"point": "Your own objectives, time horizon and risk tolerance", "keywords": ["objective", "ziel", "horizon", "horizont", "risk tolerance", "risikotoleranz", "risikobereitschaft", "goal"]},
        {"point": "Your existing portfolio and diversification", "keywords": ["portfolio", "diversif", "exposure", "allocation", "allokation", "concentration"]},
        {"point": "Latest results, guidance and news since the annual report", "keywords": ["latest", "quarter", "quartal", "guidance", "news", "update", "half-year", "halbjahr"]},
        {"point": "Valuation versus peers and consensus expectations", "keywords": ["peer", "consensus", "konsens", "multiple", "analyst"]},
        {"point": "Costs, taxes and currency", "keywords": ["cost", "kosten", "fee", "tax", "steuer", "currency", "währung", "waehrung", "fx"]},
        {"point": "Liquidity / tradability of the shares", "keywords": ["liquidity", "liquidität", "liquiditaet", "trading volume", "unlisted", "nicht kotiert", "tradab"]},
        {"point": "Management, governance and capital-return plans", "keywords": ["management", "governance", "buyback", "rückkauf", "dividend policy", "capital return"]},
    ])
    st.markdown("**Reflection on your last answer**")
    ui.coverage_feedback(covered, missed, "You thought about", "Professionals would also consider")
    ui.cfa_box("portfolio")
    st.caption("Remember: this tool does not tell you whether to buy or sell. A good thesis tells you what to watch — and when you were wrong.")


def thesis_markdown(app: AppContext, t: dict) -> str:
    lines = [f"# Investment thesis — {app.profile['name']}", "", f"_Prepared with Analyst Lab · {storage.now_iso()[:10]} · reporting currency {app.currency}_", ""]
    lines += ["## Business summary", t.get("summary", ""), "", "## Three reasons the company could perform well"]
    lines += [f"{i + 1}. {r}" for i, r in enumerate(t.get("reasons", []))]
    lines += ["", "## Three major risks"] + [f"{i + 1}. {r}" for i, r in enumerate(t.get("risks", []))]
    for key, en, _ in SECTIONS[1:4]:
        lines += ["", f"## {en}", t.get(key, "")]
    lines += ["", "## Scenarios"]
    for k, label in CASES:
        lines += [f"**{label}:** {t.get(f'case_{k}', '')}", ""]
    lines += ["## What would change my thesis?", t.get("change", ""), "", "## Before allocating CHF 10,000 I would still need", t.get("chf10k", ""), "",
              "_This document is a learning exercise and not investment advice._"]
    return "\n".join(lines)
