"""Stage 7 — Risk Analysis (Risikoanalyse)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lab import calculations as C
from lab import company_analysis as CA
from lab import data as D
from lab import ui
from lab import visualization as viz
from stages.common import AppContext, stage_footer, stage_header

NUMBER = 7
TRENDS = ["Rising", "Stable", "Falling"]
CHANNELS = ["Earnings / ROE", "Capital / book value / payouts", "Cost of equity (uncertainty)"]
REF_ALIAS = {"interest_rate": "interest"}


CORPORATE_RISKS = [
    {"key": "demand", "en": "Demand / cyclical risk", "de": "Konjunktur- und Nachfragerisiko", "cfa": "risk_demand",
     "what": "Sales fall with the economic or industry cycle (construction, capital goods, consumer spending); with high fixed costs, profit falls much faster than sales (operating leverage).",
     "find": "Management report (market development, outlook); sales by region and segment; order intake if disclosed."},
    {"key": "competition", "en": "Competitive risk", "de": "Wettbewerbsrisiko", "cfa": "risk_competition",
     "what": "Rivals launch better or cheaper products; new entrants or substitutes take market share and push prices down.",
     "find": "Strategy section; market-share claims; gross-margin trend; competitors' reports."},
    {"key": "pricing", "en": "Pricing and regulatory risk", "de": "Preis- und Regulierungsrisiko", "cfa": "risk_pricing",
     "what": "Governments, payers or customers force prices down (drug-price reforms, tariffs, procurement rules) or new regulation adds costs.",
     "find": "Risk factors; outlook; sales by region; notes on rebates and price adjustments."},
    {"key": "pipeline", "en": "Innovation, pipeline and patent-expiry risk", "de": "Innovations-, Pipeline- und Patentablaufrisiko", "cfa": "risk_pipeline",
     "what": "Key products lose patent protection or become outdated; new products fail in development or launch late.",
     "find": "Pipeline overview; patent-expiry tables; R&D spending; impairments of product rights."},
    {"key": "currency", "en": "Currency risk", "de": "Währungsrisiko", "cfa": "risk_currency",
     "what": "Sales and costs in different currencies: a strong home currency (CHF) cuts reported sales and margins; translation changes equity.",
     "find": "Financial risk management note (FX sensitivity); growth in local currencies vs reporting currency; translation differences in OCI."},
    {"key": "supply_chain", "en": "Supply-chain and input-cost risk", "de": "Lieferketten- und Kostenrisiko", "cfa": "risk_supply",
     "what": "Shortages, disruptions or price rises for raw materials, components, energy and logistics; dependence on single suppliers or sites.",
     "find": "Risk report; gross-margin trend; inventory levels; procurement commentary."},
    {"key": "legal", "en": "Legal and product-liability risk", "de": "Rechts- und Produkthaftungsrisiko", "cfa": "risk_legal",
     "what": "Lawsuits, patent disputes, product recalls or side effects, compliance breaches (antitrust, bribery).",
     "find": "Provisions and contingent liabilities note; legal proceedings section; risk factors."},
    {"key": "operational", "en": "Operational risk", "de": "Operationelles Risiko", "cfa": "risk_operational",
     "what": "Production or quality failures, IT and cyber attacks, fraud, loss of key people.",
     "find": "Risk report; quality and manufacturing disclosures; IT/cyber section."},
    {"key": "concentration", "en": "Concentration risk", "de": "Konzentrationsrisiko", "cfa": "risk_concentration",
     "what": "Dependence on a few products, customers, suppliers or one region.",
     "find": "Sales by product and region; largest customers; segment information."},
]


def risk_types(app: AppContext) -> list[dict]:
    if app.sector == "corporate":
        return [dict(r) for r in CORPORATE_RISKS]
    bank = app.sector == "bank"
    risks = [
        {"key": "credit", "en": "Credit risk", "de": "Kreditrisiko", "cfa": "risk_credit",
         "what": "Borrowers or counterparties fail to pay — loans, mortgages, Lombard loans, derivatives counterparties." if bank else "Issuers in the bond portfolio default or are downgraded; reinsurers or counterparties fail to pay.",
         "find": "Credit risk section of the risk report; IFRS 9 stages (1/2/3) and ECL allowances; Pillar 3 credit tables." if bank else "Investment note: rating mix of fixed income; counterparty default risk in the SFCR/SST."},
        {"key": "market", "en": "Market risk", "de": "Marktrisiko", "cfa": "risk_market",
         "what": "Equity, FX and credit-spread moves hit trading positions and — via client assets — fee income." if bank else "Equity, real estate, credit-spread and FX moves hit investment results, solvency and asset-based fees.",
         "find": "Market risk section (VaR, stress tests); fee income sensitivity to invested assets." if bank else "Investment allocation; sensitivity analyses in the notes/SFCR (equity −30 %, spreads +100 bp)."},
        {"key": "interest", "en": "Interest-rate risk", "de": "Zinsänderungsrisiko", "cfa": "risk_interest",
         "what": "Rate changes alter net interest income (deposit margins) and the value of fixed-rate assets." if bank else "Low or falling rates squeeze the spread on guaranteed products; rate moves change the value of assets vs liabilities (duration gap).",
         "find": "Interest-rate risk in the banking book (IRRBB) disclosures; NII sensitivity tables." if bank else "Asset–liability management section; SST/Solvency II interest-rate sensitivities."},
        {"key": "liquidity", "en": "Liquidity risk", "de": "Liquiditätsrisiko", "cfa": "risk_liquidity",
         "what": "Depositors withdraw faster than assets can be turned into cash (the risk that brought down Credit Suisse in 2023)." if bank else "Mass surrenders/lapses, collateral calls on derivatives or large catastrophe payouts require cash quickly.",
         "find": "Liquidity coverage ratio (LCR), net stable funding ratio (NSFR), funding mix." if bank else "Liquidity management section; surrender options; derivative collateral."},
        {"key": "operational", "en": "Operational risk", "de": "Operationelles Risiko", "cfa": "risk_operational",
         "what": "Losses from failed processes, people, IT/cyber, fraud, conduct and litigation.",
         "find": "Operational risk section; provisions and contingent liabilities note (litigation); IT/cyber disclosures."},
        {"key": "regulatory", "en": "Regulatory risk", "de": "Regulatorisches Risiko", "cfa": "risk_regulatory",
         "what": "Higher capital or liquidity requirements, conduct rules, tax or political changes that cap profitability or distributions.",
         "find": "Capital management section; regulatory developments in the management report; outlook."},
        {"key": "concentration", "en": "Concentration risk", "de": "Konzentrationsrisiko", "cfa": "risk_concentration",
         "what": "Dependence on one region, client segment, product, counterparty — or, for insurers, one peril (e.g. US hurricane).",
         "find": "Segment and geographic information; largest exposures; peak-peril disclosures."},
    ]
    if not bank:
        risks.append({"key": "underwriting", "en": "Insurance / underwriting risk", "de": "Versicherungstechnisches Risiko", "cfa": "risk_underwriting",
                      "what": "Claims, mortality, longevity, lapse or expenses turn out worse than priced — catastrophes, reserve deficiencies, pandemics.",
                      "find": "Insurance risk section; claims development tables; nat cat losses vs budget; lapse rates; SST/Solvency II underwriting risk module."})
    return risks


def _indicator_tiles(app: AppContext, values: pd.DataFrame) -> None:
    years = D.year_columns(values)
    latest = years[-1] if years else None

    def v(k, y=latest):
        return D.value(values, k, y) if y else None

    tiles = []
    if app.sector == "bank":
        tiles.append(("CET1 ratio", C.fmt_pct(v("cet1_ratio")), "Capital buffer vs risk-weighted assets"))
        rwa, ta = v("rwa"), v("total_assets")
        tiles.append(("RWA density", C.fmt_pct(rwa / ta * 100) if rwa and ta else "–", "Riskiness of the balance sheet"))
        nii, rev, fee = v("net_interest_income"), v("revenue"), v("fee_income")
        tiles.append(("NII share of income", C.fmt_pct(nii / rev * 100) if nii and rev else "–", "Rate sensitivity"))
        tiles.append(("Fee share of income", C.fmt_pct(fee / rev * 100) if fee and rev else "–", "Market sensitivity"))
        loans, dep = v("customer_loans"), v("customer_deposits")
        if loans and dep:
            tiles.append(("Loans / deposits", C.fmt_pct(loans / dep * 100), "Funding / liquidity"))
    elif app.sector == "corporate":
        ebit, rev, da = v("ebit"), v("revenue"), v("depreciation_amortisation")
        debt, cash, intr, ocf, ni, rnd = v("total_debt"), v("cash"), v("interest_expense"), v("operating_cash_flow"), v("net_income"), v("rnd_expense")
        tiles.append(("EBIT margin", C.fmt_pct(ebit / rev * 100) if ebit is not None and rev else "–", "Operating profitability — cushion against shocks"))
        ebitda = (ebit + da) if ebit is not None and da is not None else None
        tiles.append(("Net debt / EBITDA", f"{(debt - cash) / ebitda:.1f}×" if debt is not None and cash is not None and ebitda else "–", "Financial risk"))
        tiles.append(("Interest cover", f"{ebit / intr:.1f}×" if ebit is not None and intr else "–", "Debt service capacity"))
        tiles.append(("Cash conversion", C.fmt_pct(ocf / ni * 100, 0) if ocf is not None and ni else "–", "Does profit become cash?"))
        if rnd is not None and rev:
            tiles.append(("R&D intensity", C.fmt_pct(rnd / rev * 100), "Reinvestment in the pipeline"))
    else:
        tiles.append(("Solvency ratio", C.fmt_pct(v("solvency_ratio"), 0), "Capital buffer vs requirement"))
        if v("combined_ratio") is not None:
            tiles.append(("Combined ratio", C.fmt_pct(v("combined_ratio")), "Underwriting profitability (P&C)"))
        inv, rev = v("investment_income"), v("revenue")
        tiles.append(("Investment income share", C.fmt_pct(inv / rev * 100) if inv and rev else "–", "Dependence on markets"))
    e, a = v("total_equity"), v("total_assets")
    tiles.append(("Equity / assets", C.fmt_pct(e / a * 100) if e and a else "–", "Unweighted leverage"))
    cols = st.columns(len(tiles))
    for col, (label, val, help_) in zip(cols, tiles):
        col.metric(label, val, help=help_, border=True)
    st.caption(f"Latest year: {latest}. Indicators come from your Stage 2 dataset — they show where to look, not the answer.")


def _criteria(app: AppContext, answers: dict) -> list[tuple[str, bool]]:
    rts = risk_types(app)
    assessed = sum(1 for r in rts if answers.get("risks", {}).get(r["key"], {}).get("saved"))
    top = answers.get("top3", {})
    top_ok = len(top.get("keys", [])) == 3 and all(CA.word_count(top.get("why", {}).get(k, "")) >= 10 for k in top.get("keys", []))
    return [
        (f"Every risk type assessed with evidence — {assessed}/{len(rts)}", assessed == len(rts)),
        ("Three risks with the largest effect on value chosen and explained", top_ok and bool(top.get("submitted"))),
    ]


def render(app: AppContext) -> None:
    stage_header(app, NUMBER)
    values = app.values
    state = app.state(NUMBER)
    answers = state["answers"]
    answers.setdefault("risks", {})
    rts = risk_types(app)
    names = {r["key"]: r["en"] for r in rts}

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        ui.task_box(
            "Use the risk report, Pillar 3 / SFCR disclosures and the notes. For every risk type rate <b>likelihood</b> and <b>impact on value</b> (1–5), "
            "the <b>trend</b>, and note your evidence. Then pick the three risks that could move the company's value the most — and explain the channel."
        )
    with c2:
        ui.cfa_box("risk_regulatory")
    _indicator_tiles(app, values)

    st.subheader("1 · Risk dashboard")
    for r in rts:
        a = answers["risks"].setdefault(r["key"], {})
        label = f"{'✓' if a.get('saved') else '○'}  {r['en']} · {r['de']}"
        if a.get("saved"):
            label += f"   —   L{a['likelihood']} × I{a['impact']}, {a['trend'].lower()}"
        with st.expander(label):
            st.markdown(f"**What it means here:** {r['what']}")
            st.caption(f"Where to look: {r['find']}")
            ui.cfa_box(r["cfa"])
            with st.form(f"s7-{r['key']}"):
                s1, s2, s3 = st.columns(3)
                lik = s1.slider("Likelihood (1 rare – 5 likely)", 1, 5, int(a.get("likelihood", 3)), key=f"s7-l-{r['key']}")
                imp = s2.slider("Impact on value (1 minor – 5 severe)", 1, 5, int(a.get("impact", 3)), key=f"s7-i-{r['key']}")
                trd = s3.radio("Trend", TRENDS, index=TRENDS.index(a["trend"]) if a.get("trend") in TRENDS else 1, horizontal=True, key=f"s7-t-{r['key']}")
                ev = st.text_area("Evidence (figures, disclosures, page references)", value=a.get("evidence", ""), height=80, key=f"s7-e-{r['key']}")
                if st.form_submit_button("Save assessment", icon=":material/save:"):
                    if CA.word_count(ev) < 5:
                        st.warning("Add at least five words of evidence.")
                    else:
                        a.update({"likelihood": lik, "impact": imp, "trend": trd, "evidence": ev.strip(), "saved": True})
                        app.save()
                        st.rerun()

    order = list(names)
    assessed = [{"id": order.index(k) + 1, "name": names[k], "likelihood": v["likelihood"], "impact": v["impact"], "key": k}
                for k, v in answers["risks"].items() if v.get("saved") and k in names]
    if assessed:
        mc, tc = st.columns([3, 2])
        with mc:
            ui.plotly(viz.risk_matrix(assessed), key="s7-matrix")
        with tc:
            df = pd.DataFrame([{"#": x["id"], "Risk": x["name"], "L": x["likelihood"], "I": x["impact"], "Score": x["likelihood"] * x["impact"], "Trend": answers["risks"][x["key"]]["trend"]} for x in assessed]).sort_values(["Score", "#"], ascending=[False, True])
            st.dataframe(df, hide_index=True)

    st.subheader("2 · The three risks that matter most for value")
    top = answers.setdefault("top3", {"keys": [], "why": {}, "channel": {}})
    default = [k for k in top.get("keys", []) if k in names]
    chosen = st.multiselect("Choose exactly three", list(names), default=default, format_func=lambda k: names[k], max_selections=3, key="s7-top3")
    with st.form("s7-top-form"):
        for k in chosen:
            st.markdown(f"**{names[k]}**")
            ch = top.get("channel", {}).get(k)
            st.radio("Main channel to value", CHANNELS, index=CHANNELS.index(ch) if ch in CHANNELS else None, horizontal=True, key=f"s7-ch-{k}")
            st.text_area("How exactly would it change the company's value? What would you monitor?", value=top.get("why", {}).get(k, ""), height=80, key=f"s7-why-{k}")
        go = st.form_submit_button("Submit my top three", type="primary", icon=":material/send:", disabled=len(chosen) != 3)
    if go:
        whys = {k: st.session_state.get(f"s7-why-{k}", "").strip() for k in chosen}
        chans = {k: st.session_state.get(f"s7-ch-{k}") for k in chosen}
        if any(CA.word_count(w) < 10 for w in whys.values()) or any(c is None for c in chans.values()):
            st.warning("For each risk pick a channel and explain it in at least 10 words.")
        else:
            answers["top3"] = {"keys": chosen, "why": whys, "channel": chans, "submitted": True}
            app.save()
            st.rerun()
    if len(chosen) != 3:
        st.caption("Select three risks to unlock the form.")

    if answers["top3"].get("submitted"):
        _feedback(app, answers, names)

    stage_footer(app, NUMBER, _criteria(app, answers))


def _feedback(app: AppContext, answers: dict, names: dict) -> None:
    ref = app.profile.get("top_risks_reference", [])
    if not ref:
        st.info("No reference view for this company — compare your choice with the 'principal risks' the company itself lists in its risk report.")
        return
    ref_keys = [REF_ALIAS.get(r["risk"], r["risk"]) for r in ref]
    mine = answers["top3"]["keys"]
    overlap = [k for k in mine if k in ref_keys]
    st.markdown(f"**Analyst reference view** — you share {len(overlap)} of 3. Different choices are fine if your channel-to-value reasoning holds.")
    for r in ref:
        k = REF_ALIAS.get(r["risk"], r["risk"])
        mark = "✓" if k in mine else "○"
        st.markdown(f"{mark} **{names.get(k, k.capitalize())}** — {r['why']}")
    st.caption("Channels: risks hit value through future earnings (ROE), through capital (book value, distributions) or through a higher cost of equity when uncertainty rises.")
