"""Stage 9 — Valuation (Bewertung).

Valuation comes after the fundamental work. For banks and insurers the emphasis is on
P/B versus ROE, dividends and capital generation rather than an industrial FCFF DCF;
for non-financial companies on a free-cash-flow DCF at the WACC, EV/EBITDA and P/E.
The app never turns the result into a buy/sell call.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from lab import calculations as C
from lab import company_analysis as CA
from lab import data as D
from lab import ratios as R
from lab import ui
from lab import valuation as V
from lab import visualization as viz
from stages.common import AppContext, record_attempt, stage_footer, stage_header

NUMBER = 9
RF_DEFAULT = {"CHF": 0.5, "EUR": 2.5, "USD": 4.2, "GBP": 4.3}
G_DEFAULT = {"CHF": 1.0, "EUR": 1.5, "USD": 2.0, "GBP": 2.0}
TAX_DEFAULT = {"CHF": 15.0, "EUR": 25.0, "USD": 21.0, "GBP": 25.0}


def base_inputs(app: AppContext, values: pd.DataFrame) -> dict | None:
    years = [y for y in D.year_columns(values) if D.value(values, "net_income", y) is not None and D.value(values, "total_equity", y) is not None]
    if not years:
        return None
    y = years[-1]
    ni, eq = D.value(values, "net_income", y), D.value(values, "total_equity", y)
    shares = D.value(values, "shares_outstanding", y)
    per_share = bool(app.profile.get("listed")) and shares is not None and shares > 0
    underlying = app.progress.get("stages", {}).get("6", {}).get("answers", {}).get("underlying", {}).get(str(y))
    eps = D.value(values, "eps", y) if per_share else None
    dps = D.value(values, "dps", y) or (D.value(values, "dps", y - 1) if per_share else None)
    roe_hist = [R.compute(R.RATIOS["roe"], values, yy).value for yy in years[-3:]]
    roe_hist = [x for x in roe_hist if x is not None]
    roe_default, roe_basis = (float(np.median(roe_hist)), "median ROE of the last 3 years (robust to one-off years)") if roe_hist else (None, "")
    prev_eq = D.value(values, "total_equity", y - 1)
    if underlying is not None and prev_eq:
        roe_default, roe_basis = underlying / ((prev_eq + eq) / 2) * 100, f"underlying ROE {y} from your Stage 6 bridge"
    return {
        "year": y, "ni": ni, "equity": eq, "shares": shares, "per_share": per_share,
        "eps": eps if eps is not None else (ni / shares if per_share else None),
        "dps": dps, "bvps": eq / shares if per_share else None,
        "underlying_ni": underlying,
        "roe_avg3": roe_default,
        "roe_basis": roe_basis,
        "payout": (dps / eps * 100) if (per_share and dps and eps and eps > 0) else None,
        "rwa": D.value(values, "rwa", y), "cet1_ratio": D.value(values, "cet1_ratio", y),
        **_corporate_inputs(values, y),
    }


def _corporate_inputs(values: pd.DataFrame, y: int) -> dict:
    """EBITDA, net debt and free cash flow for non-financial companies (None where data is missing)."""
    g = lambda k: D.value(values, k, y)  # noqa: E731
    ebit, da, debt, cash, ocf, capex = g("ebit"), g("depreciation_amortisation"), g("total_debt"), g("cash"), g("operating_cash_flow"), g("capex")
    fcf = (ocf - capex) if ocf is not None and capex is not None else g("free_cash_flow")
    return {
        "ebit": ebit, "ebitda": (ebit + da) if ebit is not None and da is not None else None,
        "net_debt": (debt - cash) if debt is not None and cash is not None else None,
        "debt": debt, "fcf0": fcf, "fcf_basis": "operating cash flow − capex" if ocf is not None and capex is not None else "reported free cash flow",
    }


def _criteria(app: AppContext, answers: dict) -> list[tuple[str, bool]]:
    listed = bool(app.profile.get("listed"))
    return [
        ("Valuation methods chosen and justified", bool(answers.get("methods_submitted"))),
        ("Market multiples calculated yourself" if listed else "Peer multiples applied to the unlisted company", bool(answers.get("multiples_done"))),
        ("Base-case assumptions saved", "base" in answers.get("scenarios", {})),
        ("Valuation conclusion written (method + value range)", bool(answers.get("conclusion_submitted"))),
    ]


def render(app: AppContext) -> None:
    stage_header(app, NUMBER)
    values = app.values
    state = app.state(NUMBER)
    answers = state["answers"]
    b = base_inputs(app, values)
    if b is None:
        st.warning("Net income and equity are needed — complete Stage 2.")
        stage_footer(app, NUMBER, _criteria(app, answers))
        return

    corp = app.sector == "corporate"
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        if corp:
            ui.task_box(
                "Valuation comes <b>last</b> — it translates your analysis into numbers. For a non-financial company, value comes from the <b>free cash flow</b> "
                "the business generates for all capital providers: discount it at the <b>WACC</b> (FCFF DCF) and cross-check with <b>EV/EBITDA</b> and P/E. "
                "Debt matters here: <b>equity value = enterprise value − net debt</b>. Change the assumptions and watch the value move."
            )
        else:
            ui.task_box(
                "Valuation comes <b>last</b> — it translates your analysis into numbers. For banks and insurers, <b>P/B versus ROE</b>, dividends and "
                "<b>capital generation</b> are usually more informative than an industrial free-cash-flow DCF: their 'debt' (deposits, policy liabilities) is raw material, "
                "not financing, and regulators decide how much capital can be paid out. Change the assumptions and watch the value move."
            )
    with c2:
        ui.cfa_box("fcff" if corp else "justified_pb")
        st.caption("This tool does not tell you whether to buy or sell. A gap between your value and the market price is a hypothesis to test.")

    _methods(app, answers)
    st.divider()
    price = _multiples(app, answers, b)
    st.divider()
    _playground(app, answers, b, price)
    st.divider()
    _conclusion(app, answers, b)
    stage_footer(app, NUMBER, _criteria(app, answers))


def _methods(app: AppContext, answers: dict) -> None:
    st.subheader("1 · Which methods fit this company?")
    names = {m.key: m.name for m in V.METHOD_GUIDE}
    with st.form("s9-methods"):
        chosen = st.multiselect("Pick the two or three methods you consider most informative", list(names), default=answers.get("methods", []), format_func=lambda k: names[k], key="s9-m")
        why = st.text_area("Why these — and why not the others?", value=answers.get("methods_why", ""), height=90, key="s9-m-why")
        if st.form_submit_button("Submit my choice", type="primary", icon=":material/send:"):
            if not 2 <= len(chosen) <= 3 or CA.word_count(why) < 12:
                st.warning("Choose two or three methods and explain in at least 12 words.")
            else:
                answers.update({"methods": chosen, "methods_why": why.strip(), "methods_submitted": True})
                app.save()
                record_attempt(app, NUMBER, "methods", "valuation_methods", not (set(chosen) & V.UNSUITED[app.sector]))
                st.rerun()
    if answers.get("methods_submitted"):
        chosen = set(answers["methods"])
        corp = app.sector == "corporate"
        if chosen & V.UNSUITED[app.sector]:
            if corp:
                st.warning("You included P/B or justified P/B. For pharma and industrial companies book value leaves out the most valuable assets (patents, brands, know-how) and buybacks shrink it — P/B says little. Use cash flow and earnings multiples.", icon=":material/warning:")
            else:
                st.warning("You included an FCFF-style DCF or EV/EBITDA. For a bank or insurer, cash flow statements do not measure distributable cash, and debt is operating funding — use FCFE defined as distributable capital instead (section 3).", icon=":material/warning:")
        good = chosen & V.SUITED[app.sector]
        kind = "non-financial" if corp else "financial-sector"
        st.success(f"{len(good)} of your choices are classic {kind} methods." if good else f"None of your choices is a typical {kind} method — compare with the guide below.", icon=":material/fact_check:")
        guide = pd.DataFrame([{"Method": m.name, "When it fits": m.when, "Watch out for": m.caution} for m in V.METHOD_GUIDE])
        st.dataframe(guide, hide_index=True, column_config={"When it fits": st.column_config.TextColumn(width="large"), "Watch out for": st.column_config.TextColumn(width="large")})
        ui.cfa_box("dcf")


def _multiples(app: AppContext, answers: dict, b: dict) -> float | None:
    listed = b["per_share"]
    st.subheader("2 · Market multiples" if listed else "2 · Valuing an unlisted company with peer multiples")
    ccy = app.currency
    if listed:
        st.caption("Look up the current share price (stock exchange / financial website). Note: some companies report in a different currency than their share trades in (e.g. UBS reports in USD, trades in CHF) — use the same currency for price and per-share figures.")
        price = st.number_input(f"Current share price ({ccy})", value=answers.get("price"), min_value=0.0, format="%.2f", step=None, key="s9-price")
        if price != answers.get("price"):
            answers["price"] = price
            answers["multiples_done"] = False
            app.save()
        if not price:
            st.info("Enter a share price to continue.", icon=":material/edit:")
            return None
        eps_basis = b["eps"]
        corp = app.sector == "corporate"
        if corp and (b["ebitda"] is None or b["net_debt"] is None):
            st.info("EV/EBITDA needs EBIT, D&A, financial debt and cash — complete them in Stage 2.", icon=":material/edit:")
            return price
        ev = price * b["shares"] + b["net_debt"] if corp else None
        correct = {
            "pe": V.pe(price, eps_basis),
            "pb": (ev / b["ebitda"] if b["ebitda"] else None) if corp else V.pb(price, b["bvps"]),
            "dy": (V.dividend_yield(b["dps"], price) or 0) * 100 if b["dps"] else None,
        }
        if corp:
            st.markdown(f"Use your dataset ({b['year']}): EPS {ccy} {eps_basis:.2f} · shares {C.fmt_num(b['shares'], 1)} m · EBITDA (EBIT + D&A) {C.fmt_num(b['ebitda'])} m · net debt (debt − cash) {C.fmt_num(b['net_debt'])} m · DPS {('%.2f' % b['dps']) if b['dps'] else '–'}")
        else:
            st.markdown(f"Use your dataset ({b['year']}): EPS {ccy} {eps_basis:.2f} · equity {C.fmt_num(b['equity'])} m · shares {C.fmt_num(b['shares'], 1)} m · DPS (latest declared) {('%.2f' % b['dps']) if b['dps'] else '–'}")
        with st.form("s9-mult"):
            m1, m2, m3 = st.columns(3)
            pe_in = m1.number_input("P/E (×)", value=answers.get("pe_in"), format="%.2f", step=None, key="s9-pe")
            pb_in = m2.number_input("EV/EBITDA (×) — compute EV = market cap + net debt first" if corp else "P/B (×) — compute BVPS first", value=answers.get("pb_in"), format="%.2f", step=None, key="s9-pb")
            dy_in = m3.number_input("Dividend yield (%)", value=answers.get("dy_in"), format="%.2f", step=None, key="s9-dy")
            go = st.form_submit_button("Check my multiples", type="primary", icon=":material/calculate:")
        if go:
            if None in (pe_in, pb_in) or (correct["dy"] is not None and dy_in is None):
                st.warning("Fill in all multiples.")
            else:
                ok = {k: C.is_close(v, correct[k], rel=0.02, abs_tol=0.05) if correct[k] is not None else True for k, v in (("pe", pe_in), ("pb", pb_in), ("dy", dy_in))}
                answers.update({"pe_in": pe_in, "pb_in": pb_in, "dy_in": dy_in, "multiples_ok": ok, "multiples_done": True})
                app.save()
                record_attempt(app, NUMBER, "pb", "ev_multiples" if corp else "justified_pb", ok["pb"])
                st.rerun()
        if answers.get("multiples_done"):
            ok = answers.get("multiples_ok", {})
            bvps = b["bvps"]
            cols = st.columns(3)
            cols[0].metric("P/E", f"{correct['pe']:.2f}×" if correct["pe"] else "n/m", help=f"{price:.2f} ÷ EPS {eps_basis:.2f}")
            if corp:
                cols[1].metric("EV/EBITDA", f"{correct['pb']:.2f}×" if correct["pb"] else "n/m", help=f"EV = {price:.2f} × {C.fmt_num(b['shares'], 1)} m + net debt {C.fmt_num(b['net_debt'])} = {C.fmt_num(ev)} m; ÷ EBITDA {C.fmt_num(b['ebitda'])}")
            else:
                cols[1].metric("P/B", f"{correct['pb']:.2f}×" if correct["pb"] else "n/m", help=f"BVPS = {C.fmt_num(b['equity'])} ÷ {C.fmt_num(b['shares'], 1)} = {bvps:.2f}")
            cols[2].metric("Dividend yield", f"{correct['dy']:.2f} %" if correct["dy"] is not None else "–")
            st.markdown(" · ".join(f"{('EV/EBITDA' if (k == 'pb' and corp) else k.upper())}: {'✓' if v else '✗'}" for k, v in ok.items()))
            if corp:
                st.caption("Enterprise value belongs to all capital providers, so it is compared with EBITDA (before interest); market cap belongs to shareholders and is compared with net income (P/E). Strictly, minorities and pension deficits also belong in EV.")
            if b.get("underlying_ni") and b["shares"]:
                u_eps = b["underlying_ni"] / b["shares"]
                st.caption(f"On your underlying earnings from Stage 6 (EPS ≈ {u_eps:.2f}) the P/E would be {price / u_eps:.2f}× — which one is more meaningful?")
            ui.cfa_box("pe")
        return price

    # unlisted: peer multiples
    st.caption("No market price exists. Analysts use multiples of listed peers (or of recent transactions — e.g. what an acquirer paid) and intrinsic models.")
    if app.sector == "corporate":
        _peer_multiples_corporate(app, answers, b)
        return None
    with st.form("s9-peer-mult"):
        p1, p2 = st.columns(2)
        pb_peer = p1.number_input("Peer P/B you looked up (×)", value=answers.get("peer_pb"), format="%.2f", step=None, key="s9-ppb")
        pe_peer = p2.number_input("Peer P/E you looked up (×)", value=answers.get("peer_pe"), format="%.2f", step=None, key="s9-ppe")
        disc = st.slider("Discount for size / illiquidity (%)", 0, 40, int(answers.get("discount", 15)), key="s9-disc")
        if st.form_submit_button("Apply peer multiples", type="primary", icon=":material/calculate:"):
            if not pb_peer or not pe_peer:
                st.warning("Enter both peer multiples.")
            else:
                answers.update({"peer_pb": pb_peer, "peer_pe": pe_peer, "discount": disc, "multiples_done": True})
                app.save()
                st.rerun()
    if answers.get("multiples_done"):
        f = 1 - answers["discount"] / 100
        v_pb = answers["peer_pb"] * b["equity"] * f
        v_pe = answers["peer_pe"] * b["ni"] * f
        cols = st.columns(2)
        cols[0].metric(f"Equity value via P/B ({app.currency} m)", C.fmt_num(v_pb))
        cols[1].metric(f"Equity value via P/E ({app.currency} m)", C.fmt_num(v_pe))
        st.caption("Why do the two differ? Because the company's ROE differs from the peers' — which is exactly what P/B = f(ROE) captures.")
    return None


def _peer_multiples_corporate(app: AppContext, answers: dict, b: dict) -> None:
    with st.form("s9-peer-mult-corp"):
        p1, p2 = st.columns(2)
        ev_peer = p1.number_input("Peer EV/EBITDA you looked up (×)", value=answers.get("peer_ev"), format="%.2f", step=None, key="s9-pev")
        pe_peer = p2.number_input("Peer P/E you looked up (×)", value=answers.get("peer_pe"), format="%.2f", step=None, key="s9-ppe")
        disc = st.slider("Discount for size / illiquidity (%)", 0, 40, int(answers.get("discount", 15)), key="s9-disc")
        if st.form_submit_button("Apply peer multiples", type="primary", icon=":material/calculate:"):
            if not ev_peer or not pe_peer:
                st.warning("Enter both peer multiples.")
            else:
                answers.update({"peer_ev": ev_peer, "peer_pe": pe_peer, "discount": disc, "multiples_done": True})
                app.save()
                st.rerun()
    if answers.get("multiples_done") and answers.get("peer_ev"):
        f = 1 - answers["discount"] / 100
        cols = st.columns(2)
        if b["ebitda"] is not None and b["net_debt"] is not None:
            ev = answers["peer_ev"] * f * b["ebitda"]
            cols[0].metric(f"Equity value via EV/EBITDA ({app.currency} m)", C.fmt_num(ev - b["net_debt"]), help=f"EV = {answers['peer_ev']:.1f}× × (1 − {answers['discount']} %) × EBITDA {C.fmt_num(b['ebitda'])} = {C.fmt_num(ev)}; minus net debt {C.fmt_num(b['net_debt'])}")
        else:
            cols[0].info("EBITDA and net debt need EBIT, D&A, financial debt and cash — collect them in Stage 2.")
        cols[1].metric(f"Equity value via P/E ({app.currency} m)", C.fmt_num(answers["peer_pe"] * f * b["ni"]))
        st.caption("EV/EBITDA values the whole business, so net debt must be deducted to reach equity value; P/E values the equity directly. Large differences point to different leverage or to one-offs in net income.")


def _playground(app: AppContext, answers: dict, b: dict, price: float | None) -> None:
    if app.sector == "corporate":
        _playground_corporate(app, answers, b, price)
        return
    st.subheader("3 · Assumptions → value (live)")
    per_share = b["per_share"]
    unit = f"{app.currency}/share" if per_share else f"{app.currency} m"
    saved = answers.get("scenarios", {}).get("base", {}).get("assumptions", {})
    ccy = app.currency
    left, right = st.columns([2, 3], gap="large")
    with left:
        st.markdown("**Cost of equity (CAPM)** · <span class='al-de'>Eigenkapitalkosten</span>", unsafe_allow_html=True)
        rf = st.slider("Risk-free rate (%)", 0.0, 6.0, float(saved.get("rf", RF_DEFAULT.get(ccy, 2.0))), 0.1, key="s9-rf")
        beta = st.slider("Beta", 0.4, 2.0, float(saved.get("beta", 1.15 if app.sector == "bank" else 0.95)), 0.05, key="s9-beta")
        erp = st.slider("Equity risk premium (%)", 3.0, 8.0, float(saved.get("erp", 5.5)), 0.1, key="s9-erp")
        r = V.capm(rf / 100, beta, erp / 100)
        st.markdown(f"→ cost of equity **r = {r * 100:.2f} %**")
        ui.cfa_box("capm")
        st.markdown("**Profitability, payout and growth**")
        roe_default = b["roe_avg3"] if b["roe_avg3"] is not None else 10.0
        roe = st.slider("Sustainable ROE (%)", 0.0, 25.0, float(np.clip(saved.get("roe", round(roe_default, 1)), 0.0, 25.0)), 0.1, key="s9-roe",
                        help=f"Default = {b['roe_basis'] or 'assumption'} ({roe_default:.1f} %). Adjust for one-offs (Stage 6).")
        payout = st.slider("Payout ratio (%)", 0.0, 100.0, float(np.clip(saved.get("payout", b["payout"] if b["payout"] is not None else 60.0), 0.0, 100.0)), 1.0, key="s9-payout")
        g = st.slider("Long-term growth g (%)", 0.0, 4.0, float(saved.get("g", G_DEFAULT.get(ccy, 1.5))), 0.1, key="s9-g")
        n = st.slider("Years of explicit forecast", 1, 10, int(saved.get("n", 5)), key="s9-n")
        g_sus = V.sustainable_growth(roe / 100, payout / 100) * 100
        g1 = st.slider("Near-term dividend growth (%)", -5.0, 15.0, float(saved.get("g1", round(min(max(g_sus, -5.0), 15.0), 1))), 0.1, key="s9-g1", help=f"Sustainable growth (1 − payout) × ROE = {g_sus:.1f} %")
        fade = st.checkbox("Let ROE fade to the cost of equity (no lasting advantage)", value=bool(saved.get("fade", False)), key="s9-fade")
        rwa_g, cet1_t = None, None
        if app.sector == "bank" and b["rwa"]:
            st.markdown("**Capital generation (bank FCFE)**")
            rwa_g = st.slider("RWA growth (%)", -5.0, 10.0, float(saved.get("rwa_g", 3.0)), 0.5, key="s9-rwag")
            cet1_t = st.slider("Target CET1 ratio (%)", 8.0, 20.0, float(saved.get("cet1_t", b["cet1_ratio"] or 14.0)), 0.1, key="s9-cet1t")

    with right:
        R_, G_, ROE_, P_ = r, g / 100, roe / 100, payout / 100
        bv = b["bvps"] if per_share else b["equity"]
        earn = (bv * ROE_)  # normalised earnings on sustainable ROE
        d0 = earn * P_
        results = []
        jpb = V.justified_pb(ROE_, R_, G_)
        if jpb is not None:
            results.append(("Justified P/B × book value", jpb * bv))
        jpe = V.justified_pe(P_, R_, G_)
        if jpe is not None:
            results.append(("Justified P/E × normalised earnings", jpe * earn))
        ddm = V.gordon_ddm(d0, R_, G_)
        if ddm is not None:
            results.append(("Gordon DDM", ddm))
        ts = V.two_stage_ddm(d0, g1 / 100, n, G_, R_)
        if ts is not None:
            results.append((f"Two-stage DDM ({n} yrs at {g1:.1f} %)", ts["value"]))
        ri = V.residual_income(bv, ROE_, R_, G_, P_, years=10, fade_to_r=fade)
        if ri is not None:
            results.append(("Residual income" + (" (ROE fades)" if fade else ""), ri["value"]))
        if rwa_g is not None and cet1_t is not None and b["rwa"]:
            scale = b["shares"] if per_share else 1.0
            fcfe = V.bank_distributable_fcfe(earn * scale, b["rwa"], rwa_g / 100, cet1_t / 100) / scale
            dcf = V.fcfe_dcf(fcfe, rwa_g / 100, n, G_, R_)
            if dcf is not None:
                results.append(("Capital-generation DCF (FCFE)", dcf["value"]))
        if not results:
            st.error("r must be greater than g for these models.")
            return
        ui.plotly(viz.value_bars(results, f"Value per share ({unit})" if per_share else f"Equity value ({unit})", unit, reference=price if per_share else None), key="s9-bars")
        if price and per_share:
            mid = float(np.median([v for _, v in results]))
            st.caption(f"Median of your model values: {mid:,.2f} vs market price {price:,.2f} ({(mid / price - 1) * 100:+.1f} %). A gap is a question — which assumption would have to change to close it?")
            market_pb = price / b["bvps"]
            implied = V.implied_roe_from_pb(market_pb, R_, G_) * 100
            st.info(f"**Reverse-engineering:** at P/B {market_pb:.2f}× and your r = {r * 100:.1f} %, g = {g:.1f} %, the market price implies a sustainable ROE of **{implied:.1f} %** (your assumption: {roe:.1f} %).", icon=":material/swap_horiz:")
            points = [{"name": f"{app.name} (market)", "roe": b["roe_avg3"] or roe, "pb": market_pb}]
        else:
            points = []
        points.append({"name": "Your assumption", "roe": roe, "pb": jpb if jpb is not None else np.nan})
        ui.plotly(viz.pb_roe_chart(R_, G_, points), key="s9-pbroe")
        r_vals = [R_ + d / 100 for d in (-2, -1, 0, 1, 2)]
        g_vals = [max(G_ + d / 100, 0) for d in (-1, -0.5, 0, 0.5, 1)]
        grid = V.sensitivity_grid(lambda rr, gg: (V.justified_pb(ROE_, rr, gg) or np.nan) * bv, r_vals, g_vals)
        ui.plotly(viz.sensitivity_heatmap(grid, r_vals, g_vals, "Sensitivity — justified P/B value", unit), key="s9-sens")
        ui.table_view(pd.DataFrame(results, columns=["Method", unit]), hide_index=True)

    scen = st.segmented_control("Save these assumptions as", ["base", "bull", "bear"], default="base", key="s9-scen", format_func=lambda s: s.capitalize() + " case")
    if st.button("Save scenario", icon=":material/bookmark_add:", key="s9-save"):
        answers.setdefault("scenarios", {})[scen or "base"] = {
            "assumptions": {"rf": rf, "beta": beta, "erp": erp, "roe": roe, "payout": payout, "g": g, "n": n, "g1": g1, "fade": fade, "rwa_g": rwa_g, "cet1_t": cet1_t},
            "r": r * 100, "results": {k: float(v) for k, v in results}, "median": float(np.median([v for _, v in results])), "unit": unit,
        }
        app.save()
        st.toast(f"{(scen or 'base').capitalize()} case saved.", icon=":material/bookmark:")
        st.rerun()
    sc = answers.get("scenarios", {})
    if sc:
        st.dataframe(pd.DataFrame([{"Scenario": k.capitalize(), "Cost of equity %": v["r"], "ROE %": v["assumptions"]["roe"], "g %": v["assumptions"]["g"], f"Median value ({v['unit']})": v["median"]} for k, v in sc.items()]), hide_index=True)


def _playground_corporate(app: AppContext, answers: dict, b: dict, price: float | None) -> None:
    st.subheader("3 · Assumptions → value (live)")
    per_share = b["per_share"]
    unit = f"{app.currency}/share" if per_share else f"{app.currency} m"
    ccy = app.currency
    if b["fcf0"] is None or b["net_debt"] is None:
        st.info("The DCF needs operating cash flow and capex (or reported free cash flow), financial debt and cash — complete them in Stage 2.", icon=":material/edit:")
        return
    saved = answers.get("scenarios", {}).get("base", {}).get("assumptions", {})
    mcap = price * b["shares"] if price and per_share else None
    d_default = b["net_debt"] / (mcap + b["net_debt"]) * 100 if mcap and mcap + b["net_debt"] > 0 else 20.0
    left, right = st.columns([2, 3], gap="large")
    with left:
        st.markdown("**Cost of capital (WACC)** · <span class='al-de'>Kapitalkosten</span>", unsafe_allow_html=True)
        rf = st.slider("Risk-free rate (%)", 0.0, 6.0, float(saved.get("rf", RF_DEFAULT.get(ccy, 2.0))), 0.1, key="s9c-rf")
        beta = st.slider("Beta", 0.4, 2.0, float(saved.get("beta", 0.9)), 0.05, key="s9c-beta")
        erp = st.slider("Equity risk premium (%)", 3.0, 8.0, float(saved.get("erp", 5.5)), 0.1, key="s9c-erp")
        rd = st.slider("Pre-tax cost of debt (%)", 0.0, 8.0, float(saved.get("rd", round(rf + 1.0, 1))), 0.1, key="s9c-rd")
        tax = st.slider("Tax rate (%)", 0.0, 35.0, float(saved.get("tax", TAX_DEFAULT.get(ccy, 20.0))), 0.5, key="s9c-tax")
        dw = st.slider("Debt weight D/(D+E) (%)", 0.0, 60.0, float(np.clip(saved.get("dw", round(max(d_default, 0.0), 1)), 0.0, 60.0)), 0.5, key=f"s9c-dw-{int(bool(mcap))}",
                       help="Default: net debt ÷ (market cap + net debt), at market values." if mcap else "Default 20 %. Use market values (net debt ÷ (market cap + net debt)) — book equity is distorted by buybacks.")
        re = V.capm(rf / 100, beta, erp / 100)
        w = V.wacc(1 - dw / 100, re, dw / 100, rd / 100, tax / 100)
        st.markdown(f"→ cost of equity **{re * 100:.2f} %** · **WACC {w * 100:.2f} %**")
        if ccy == "CHF":
            st.caption("Swiss government bond yields are close to zero; many analysts use a 'normalised' risk-free rate of 1–2 % for CHF valuations.")
        ui.cfa_box("wacc")
        st.markdown("**Cash flow and growth**")
        fcf0 = st.number_input(f"Base free cash flow to the firm ({ccy} m)", value=float(saved.get("fcf0", round(b["fcf0"], 1))), step=None, format="%.1f", key="s9c-fcf0",
                               help=f"Default: {b['fcf_basis']} {b['year']} = {C.fmt_num(b['fcf0'])}. Normalise it: remove one-offs and unusual working-capital swings (Stage 6).")
        g1 = st.slider("Free cash flow growth, explicit years (%)", -5.0, 15.0, float(saved.get("g1", 4.0)), 0.1, key="s9c-g1")
        n = st.slider("Years of explicit forecast", 1, 10, int(saved.get("n", 5)), key="s9c-n")
        g = st.slider("Terminal growth g (%)", 0.0, 4.0, float(saved.get("g", G_DEFAULT.get(ccy, 1.5))), 0.1, key="s9c-g")
        st.markdown("**Multiples**")
        mult = st.slider("EV/EBITDA multiple (×)", 4.0, 25.0, float(saved.get("mult", 12.0)), 0.5, key="s9c-mult")
        payout = st.slider("Payout ratio for justified P/E (%)", 0.0, 100.0, float(np.clip(saved.get("payout", b["payout"] if b["payout"] is not None else 50.0), 0.0, 100.0)), 1.0, key="s9c-payout")

    with right:
        W, G, scale = w, g / 100, (b["shares"] if per_share else 1.0)
        results = []
        dcf = V.two_stage_ddm(fcf0, g1 / 100, n, G, W)
        if dcf is not None:
            results.append((f"DCF: FCFF at WACC ({n} yrs at {g1:.1f} %, then {g:.1f} %)", (dcf["value"] - b["net_debt"]) / scale))
        if b["ebitda"] is not None:
            results.append((f"EV/EBITDA {mult:.1f}× − net debt", (mult * b["ebitda"] - b["net_debt"]) / scale))
        jpe = V.justified_pe(payout / 100, re, G)
        earn = b["eps"] if per_share else b["ni"]
        if jpe is not None and earn:
            results.append((f"Justified P/E {jpe:.1f}× × earnings", jpe * earn))
        if per_share and b["dps"]:
            ddm = V.gordon_ddm(b["dps"], re, G)
            if ddm is not None:
                results.append(("Gordon DDM (dividends)", ddm))
        if not results:
            st.error("The discount rate must be greater than g for these models.")
            return
        ui.plotly(viz.value_bars(results, f"Value per share ({unit})" if per_share else f"Equity value ({unit})", unit, reference=price if per_share else None), key="s9c-bars")
        if dcf is not None:
            pv_tv = dcf["pv_terminal"] / dcf["value"] * 100 if dcf["value"] else 0
            st.caption(f"Enterprise value (DCF) {C.fmt_num(dcf['value'])} m − net debt {C.fmt_num(b['net_debt'])} m = equity {C.fmt_num(dcf['value'] - b['net_debt'])} m. The terminal value is {pv_tv:.0f} % of the enterprise value — that is how much rests on the long-term assumptions.")
        if price and per_share:
            mid = float(np.median([v for _, v in results]))
            st.caption(f"Median of your model values: {mid:,.2f} vs market price {price:,.2f} ({(mid / price - 1) * 100:+.1f} %). A gap is a question — which assumption would have to change to close it?")
            ev_mkt = price * b["shares"] + b["net_debt"]
            gi = V.implied_growth(ev_mkt, fcf0, W)
            if gi is not None:
                st.info(f"**Reverse-engineering:** at a market EV of {C.fmt_num(ev_mkt)} m and your WACC of {W * 100:.2f} %, the price implies that free cash flow of {C.fmt_num(fcf0)} m grows **{gi * 100:.1f} % a year forever** (your assumption: {g1:.1f} % for {n} years, then {g:.1f} %).", icon=":material/swap_horiz:")
        w_vals = [W + d / 100 for d in (-2, -1, 0, 1, 2)]
        g_vals = [max(G + d / 100, 0) for d in (-1, -0.5, 0, 0.5, 1)]

        def cell(ww, gg):
            r = V.two_stage_ddm(fcf0, g1 / 100, n, gg, ww)
            return np.nan if r is None else (r["value"] - b["net_debt"]) / scale

        grid = V.sensitivity_grid(cell, w_vals, g_vals)
        ui.plotly(viz.sensitivity_heatmap(grid, w_vals, g_vals, "Sensitivity — DCF equity value (rows: WACC)", unit), key="s9c-sens")
        ui.table_view(pd.DataFrame(results, columns=["Method", unit]), hide_index=True)

    scen = st.segmented_control("Save these assumptions as", ["base", "bull", "bear"], default="base", key="s9c-scen", format_func=lambda s: s.capitalize() + " case")
    if st.button("Save scenario", icon=":material/bookmark_add:", key="s9c-save"):
        answers.setdefault("scenarios", {})[scen or "base"] = {
            "assumptions": {"rf": rf, "beta": beta, "erp": erp, "rd": rd, "tax": tax, "dw": dw, "fcf0": fcf0, "g1": g1, "n": n, "g": g, "mult": mult, "payout": payout},
            "r": w * 100, "results": {k: float(v) for k, v in results}, "median": float(np.median([v for _, v in results])), "unit": unit, "kind": "corporate",
        }
        app.save()
        st.toast(f"{(scen or 'base').capitalize()} case saved.", icon=":material/bookmark:")
        st.rerun()
    sc = answers.get("scenarios", {})
    if sc:
        st.dataframe(pd.DataFrame([{"Scenario": k.capitalize(), "WACC %": v["r"], "FCF growth %": v["assumptions"].get("g1"), "Terminal g %": v["assumptions"]["g"], f"Median value ({v['unit']})": v["median"]} for k, v in sc.items()]), hide_index=True)


def _conclusion(app: AppContext, answers: dict, b: dict) -> None:
    st.subheader("4 · Your valuation conclusion")
    unit = f"{app.currency}/share" if b["per_share"] else f"{app.currency} m"
    with st.form("s9-concl"):
        text = st.text_area("Which method do you trust most for this company, why, and which assumption drives the value most?", value=answers.get("conclusion", ""), height=110)
        c1, c2 = st.columns(2)
        lo = c1.number_input(f"Value range — low ({unit})", value=answers.get("range_lo"), format="%.2f", step=None)
        hi = c2.number_input(f"Value range — high ({unit})", value=answers.get("range_hi"), format="%.2f", step=None)
        if st.form_submit_button("Submit conclusion", type="primary", icon=":material/send:"):
            if CA.word_count(text) < 20 or lo is None or hi is None or lo > hi:
                st.warning("Write at least 20 words and give a low and a high value (low ≤ high).")
            else:
                answers.update({"conclusion": text.strip(), "range_lo": lo, "range_hi": hi, "conclusion_submitted": True})
                app.save()
                st.rerun()
    if answers.get("conclusion_submitted"):
        if app.sector == "corporate":
            st.info(
                "**Checklist for a credible valuation:** the WACC reflects the risks from Stage 7 · base free cash flow excludes one-offs and unusual working-capital swings (Stage 6) · "
                "terminal growth is below long-run nominal GDP growth · net debt (and minorities, pension deficits) is deducted · the range is wide enough to reflect your uncertainty · you can name the assumption that would change your mind.",
                icon=":material/checklist:",
            )
        else:
            st.info(
                "**Checklist for a credible valuation:** the cost of equity reflects the risks from Stage 7 · sustainable ROE excludes the one-offs from Stage 6 · "
                "growth is consistent with payout × ROE · the range is wide enough to reflect your uncertainty · you can name the assumption that would change your mind.",
                icon=":material/checklist:",
            )
