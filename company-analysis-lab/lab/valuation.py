"""Valuation formulas (Stage 9).

All rates are in decimals here (0.09 = 9 %). The UI converts from percent.

Methods and when they fit
-------------------------
P/E                 any profitable company; use normalised EPS, not one-off-inflated EPS
P/B                 banks and insurers — book value is mostly financial assets
EV/EBITDA           non-financial companies; capital-structure neutral
Dividend yield      mature dividend payers; check payout sustainability
Justified P/B       (ROE − g)/(r − g): links profitability, growth and cost of equity
Gordon DDM          stable dividend payers with g < r
Two-stage DDM       when near-term dividend growth differs from long-run growth
Residual income     financials and any firm where book value is meaningful
FCFF DCF (WACC)     non-financial firms; for banks/insurers only with FCFE = distributable capital
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0 or not np.isfinite(a) or not np.isfinite(b):
        return None
    return a / b


def pe(price: float | None, eps: float | None) -> float | None:
    if eps is None or eps <= 0:
        return None  # P/E is not meaningful for losses
    return safe_div(price, eps)


def pb(price: float | None, bvps: float | None) -> float | None:
    if bvps is None or bvps <= 0:
        return None
    return safe_div(price, bvps)


def dividend_yield(dps: float | None, price: float | None) -> float | None:
    """In decimals."""
    return safe_div(dps, price)


def capm(rf: float, beta: float, erp: float) -> float:
    """Cost of equity r = rf + β × ERP."""
    return rf + beta * erp


def sustainable_growth(roe: float, payout: float) -> float:
    """g = retention ratio × ROE = (1 − payout) × ROE."""
    return (1.0 - payout) * roe


def justified_pb(roe: float, r: float, g: float) -> float | None:
    """Justified P/B = (ROE − g) / (r − g). Requires r > g."""
    if r <= g:
        return None
    return (roe - g) / (r - g)


def justified_pe(payout: float, r: float, g: float, trailing: bool = True) -> float | None:
    """Justified P/E from the Gordon model: trailing = payout × (1 + g)/(r − g); leading = payout/(r − g)."""
    if r <= g:
        return None
    return payout * (1 + g) / (r - g) if trailing else payout / (r - g)


def implied_roe_from_pb(pb_ratio: float, r: float, g: float) -> float:
    """ROE the market price implies: ROE = g + P/B × (r − g)."""
    return g + pb_ratio * (r - g)


def gordon_ddm(d0: float, r: float, g: float) -> float | None:
    """V0 = D1 / (r − g) with D1 = D0 × (1 + g)."""
    if r <= g:
        return None
    return d0 * (1 + g) / (r - g)


def two_stage_ddm(d0: float, g1: float, years: int, g2: float, r: float) -> dict | None:
    """Dividends grow at g1 for `years`, then at g2 forever."""
    if r <= g2 or years < 0:
        return None
    dividends, pv = [], []
    d = d0
    for t in range(1, years + 1):
        d = d * (1 + g1)
        dividends.append(d)
        pv.append(d / (1 + r) ** t)
    terminal = d * (1 + g2) / (r - g2)
    pv_terminal = terminal / (1 + r) ** years
    return {"dividends": dividends, "pv_dividends": pv, "terminal": terminal, "pv_terminal": pv_terminal, "value": sum(pv) + pv_terminal}


def residual_income(bv0: float, roe: float, r: float, g: float, payout: float, years: int = 10, fade_to_r: bool = False) -> dict | None:
    """Residual income model.

    V0 = BV0 + Σ (ROE_t − r) × BV_{t−1} / (1+r)^t + terminal value of the last residual income
    growing at g. Book value grows by retained earnings: BV_t = BV_{t−1} × (1 + ROE × (1 − payout)).
    With ``fade_to_r`` ROE converges linearly to r (competitive advantage fades).
    """
    if r <= g:
        return None
    bv = bv0
    rows, total = [], 0.0
    for t in range(1, years + 1):
        roe_t = roe + (r - roe) * (t / years) if fade_to_r else roe
        ri = (roe_t - r) * bv
        pv = ri / (1 + r) ** t
        rows.append({"year": t, "bv_open": bv, "roe": roe_t, "residual_income": ri, "pv": pv})
        total += pv
        bv = bv * (1 + roe_t * (1 - payout))
    last_ri = rows[-1]["residual_income"]
    terminal = last_ri * (1 + g) / (r - g) if not fade_to_r else 0.0
    pv_terminal = terminal / (1 + r) ** years
    return {"rows": rows, "pv_ri": total, "pv_terminal": pv_terminal, "value": bv0 + total + pv_terminal}


def fcfe_dcf(fcfe0: float, g_high: float, years: int, g_terminal: float, r: float) -> dict | None:
    """Simple two-stage FCFE DCF (per share or in total)."""
    return two_stage_ddm(fcfe0, g_high, years, g_terminal, r)


def bank_distributable_fcfe(net_income: float, rwa: float, rwa_growth: float, cet1_target: float) -> float:
    """FCFE for a bank = net income − capital needed to support RWA growth at the target CET1 ratio."""
    return net_income - rwa * rwa_growth * cet1_target


def sensitivity_grid(fn, r_values: list[float], g_values: list[float]) -> np.ndarray:
    """Evaluate fn(r, g) over a grid (rows = r, columns = g). Invalid cells are NaN."""
    grid = np.full((len(r_values), len(g_values)), np.nan)
    for i, r in enumerate(r_values):
        for j, g in enumerate(g_values):
            v = fn(r, g)
            if v is not None and np.isfinite(v):
                grid[i, j] = v
    return grid


@dataclass(frozen=True)
class MethodGuide:
    key: str
    name: str
    when: str
    caution: str
    cfa: str


METHOD_GUIDE = [
    MethodGuide("pe", "P/E (Kurs-Gewinn-Verhältnis)", "Profitable companies with stable, recurring earnings.", "Distorted by one-offs (e.g. negative goodwill), losses and accounting changes. Use normalised EPS.", "pe"),
    MethodGuide("pb", "P/B (Kurs-Buchwert-Verhältnis)", "Banks and insurers: assets are mostly financial and close to fair value, and regulation ties capital to book equity.", "Intangible-heavy or IFRS 17-affected book values need adjustment (goodwill, CSM).", "pb"),
    MethodGuide("dy", "Dividend yield (Dividendenrendite)", "Mature, regular dividend payers (most Swiss financials).", "A high yield can signal an expected dividend cut — check payout and capital.", "dividend_yield"),
    MethodGuide("jpb", "ROE vs P/B (justified P/B)", "Financials: value creation = ROE above cost of equity.", "Very sensitive to r − g; use sustainable (through-the-cycle) ROE.", "justified_pb"),
    MethodGuide("ddm", "Dividend discount model (Dividendendiskontierungsmodell)", "Stable payers whose dividends reflect capital generation.", "Ignores buybacks unless you include them; explodes as g approaches r.", "ddm"),
    MethodGuide("ri", "Residual income (Residualgewinnmodell)", "Banks and insurers — anchored on book value, value comes from ROE − r.", "Requires clean-surplus accounting; OCI swings and IFRS 17 CSM need thought.", "residual_income"),
    MethodGuide("ev_ebitda", "EV/EBITDA (Unternehmenswert / EBITDA)", "Non-financial companies — compares firms with different debt levels and depreciation policies.", "Meaningless for banks and insurers (no EBITDA, debt is operating). Treat leases and minorities consistently in EV.", "ev_ebitda"),
    MethodGuide("dcf", "DCF on free cash flow (FCFF at the WACC)", "Non-financial companies with clear free cash flow. For financials only if redefined as FCFE = distributable capital.", "Very sensitive to the WACC and terminal growth. For banks, 'debt' is operating raw material and cash flow statements are not informative — FCFF is inappropriate.", "dcf"),
]

# Methods that fit — or clearly do not fit — each sector (Stage 9 feedback).
SUITED = {"bank": {"pb", "jpb", "ddm", "ri"}, "insurer": {"pb", "jpb", "ddm", "ri"}, "corporate": {"pe", "ev_ebitda", "dcf", "ddm"}}
UNSUITED = {"bank": {"dcf", "ev_ebitda"}, "insurer": {"dcf", "ev_ebitda"}, "corporate": {"pb", "jpb"}}


def wacc(equity_value: float, cost_of_equity: float, debt_value: float, cost_of_debt: float, tax_rate: float) -> float | None:
    v = equity_value + debt_value
    if v <= 0:
        return None
    return equity_value / v * cost_of_equity + debt_value / v * cost_of_debt * (1 - tax_rate)


def implied_growth(enterprise_value: float, fcf0: float, r: float) -> float | None:
    """Perpetual growth that makes FCF₀ × (1 + g) ÷ (r − g) equal the enterprise value."""
    if enterprise_value + fcf0 == 0:
        return None
    return (enterprise_value * r - fcf0) / (enterprise_value + fcf0)
