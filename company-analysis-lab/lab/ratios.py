"""Ratio definitions and answer checking for Stage 4.

Each ratio knows its formula, which numbers it needs (and whether a balance is
averaged), the convention the app uses (CFA: average balances), an alternative
convention it recognises in the learner's answer, and how to interpret it for
banks and insurers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from . import metrics as M
from .calculations import is_close


@dataclass(frozen=True)
class InputSpec:
    metric: str
    averaged: bool = False  # True → needs opening (t−1) and closing (t) balance


@dataclass(frozen=True)
class RatioDef:
    key: str
    en: str
    de: str
    latex: str
    text: str
    inputs: tuple[InputSpec, ...]
    combine: Callable[[list[float]], float]  # receives resolved input values (averages already taken)
    unit: str  # "%", "x", "ccy"
    sectors: tuple[str, ...] = M.SECTORS
    higher_is_better: bool | None = True
    core: bool | tuple[str, ...] = False  # part of the mandatory Stage 4 set (True = every sector, tuple = these sectors)
    cfa: str = ""
    interpretation: dict = field(default_factory=dict)  # sector -> text
    benchmark: dict = field(default_factory=dict)  # sector -> rule-of-thumb range text

    def label(self) -> str:
        return f"{self.en} · {self.de}"

    @property
    def needs_prior_year(self) -> bool:
        return any(i.averaged for i in self.inputs)

    def is_core(self, sector: str) -> bool:
        return self.core is True or (isinstance(self.core, tuple) and sector in self.core)


def _div(a: float, b: float) -> float:
    return np.nan if b == 0 else a / b


RATIOS: dict[str, RatioDef] = {
    r.key: r
    for r in [
        RatioDef(
            "roe", "Return on equity (ROE)", "Eigenkapitalrendite",
            r"\text{ROE} = \frac{\text{Net income}_t}{\tfrac{1}{2}(\text{Equity}_{t-1} + \text{Equity}_t)} \times 100",
            "Net income ÷ average shareholders' equity × 100",
            (InputSpec("net_income"), InputSpec("total_equity", averaged=True)),
            lambda v: _div(v[0], v[1]) * 100, "%", core=True, cfa="roe",
            interpretation={
                "bank": "Compare ROE with the cost of equity (roughly 8–12 % for European banks). ROE above it creates value and supports P/B above 1. Check whether ROE comes from margins or from leverage (DuPont), and adjust for one-offs.",
                "insurer": "Compare ROE with the cost of equity (roughly 7–10 % for large insurers). Under IFRS 17 equity excludes the CSM (future profit), which can make ROE look higher than under IFRS 4. Reinsurers' ROE swings with catastrophe losses.",
                "corporate": "Compare ROE with the cost of equity (roughly 6–9 % for large Swiss companies). Use DuPont to see whether it comes from margins, asset turnover or debt. Buybacks and write-offs shrink equity and inflate ROE — for pharma, ROCE or ROIC is often more telling.",
            },
            benchmark={"bank": "Swiss/European banks: about 5–15 %", "insurer": "Life insurers: about 8–15 %; reinsurers: volatile, 0–20 %", "corporate": "Pharma: 15–40 % (equity reduced by buybacks); industrials: about 10–25 %"},
        ),
        RatioDef(
            "roa", "Return on assets (ROA)", "Gesamtkapitalrendite",
            r"\text{ROA} = \frac{\text{Net income}_t}{\tfrac{1}{2}(\text{Total assets}_{t-1} + \text{Total assets}_t)} \times 100",
            "Net income ÷ average total assets × 100",
            (InputSpec("net_income"), InputSpec("total_assets", averaged=True)),
            lambda v: _div(v[0], v[1]) * 100, "%", core=True, cfa="roa",
            interpretation={
                "bank": "Banks earn thin returns on a large balance sheet: 0.3–1 % is normal. A low ROA with a decent ROE means high leverage. Wealth managers with off-balance-sheet client assets can earn higher ROA.",
                "insurer": "Insurers' balance sheets include large policyholder assets (e.g. unit-linked funds) on which they earn only fees — ROA is low by design. Compare with peers on the same accounting basis.",
                "corporate": "Non-financial companies earn far more per unit of assets than banks: 5–15 % is common. Large acquired intangibles and goodwill depress ROA; asset-light businesses show high ROA.",
            },
            benchmark={"bank": "about 0.3–1.0 %", "insurer": "about 0.3–1.5 %", "corporate": "about 5–15 %"},
        ),
        RatioDef(
            "net_margin", "Net profit margin", "Nettogewinnmarge",
            r"\text{Net margin} = \frac{\text{Net income}_t}{\text{Revenue}_t} \times 100",
            "Net income ÷ revenue (total operating income) × 100",
            (InputSpec("net_income"), InputSpec("revenue")),
            lambda v: _div(v[0], v[1]) * 100, "%", core=True, cfa="net_margin",
            interpretation={
                "bank": "Share of operating income that ends up as profit for shareholders. Falls when costs, credit losses or taxes rise. A margin above 50 % usually signals a one-off gain.",
                "insurer": "Depends heavily on what 'revenue' contains: IFRS 4 premiums (incl. savings) give low margins; IFRS 17 insurance revenue gives higher ones. Never compare across the accounting break.",
                "corporate": "Share of sales left after all costs, interest and tax. Patented medicines earn high margins (15–30 %); industrials 5–12 %. Disposal gains and impairments distort it — compare with the EBIT margin and with the company's 'core' or 'adjusted' figures.",
            },
            benchmark={"bank": "about 15–30 %", "insurer": "basis-dependent (IFRS 17: about 5–15 %)", "corporate": "pharma about 15–30 %; industrials about 5–12 %"},
        ),
        RatioDef(
            "cost_income", "Cost/income ratio", "Aufwand-Ertrags-Verhältnis",
            r"\text{C/I} = \frac{\text{Operating expenses}_t}{\text{Operating income}_t} \times 100",
            "Operating expenses ÷ total operating income × 100",
            (InputSpec("operating_expenses"), InputSpec("revenue")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("bank",), higher_is_better=False, core=True, cfa="cost_income",
            interpretation={
                "bank": "How many francs/dollars of cost the bank spends to earn one of income. Lower is better. Private banks run 60–80 %; efficient retail banks 50–60 %. Rising C/I with falling income = negative operating leverage.",
            },
            benchmark={"bank": "about 55–80 %"},
        ),
        RatioDef(
            "leverage", "Financial leverage (equity multiplier)", "Finanzielle Hebelwirkung (Eigenkapitalmultiplikator)",
            r"\text{Leverage} = \frac{\tfrac{1}{2}(\text{Assets}_{t-1} + \text{Assets}_t)}{\tfrac{1}{2}(\text{Equity}_{t-1} + \text{Equity}_t)}",
            "Average total assets ÷ average shareholders' equity (times)",
            (InputSpec("total_assets", averaged=True), InputSpec("total_equity", averaged=True)),
            lambda v: _div(v[0], v[1]), "x", higher_is_better=None, core=("bank", "insurer"), cfa="leverage",
            interpretation={
                "bank": "Banks typically run 12–25× leverage. Higher leverage boosts ROE but leaves less loss absorption — regulators cap it via capital and leverage-ratio rules.",
                "insurer": "Insurers often show 15–30× because policyholder liabilities dominate the balance sheet. Look at the solvency ratio for the real capital buffer.",
                "corporate": "Assets ÷ equity of 1.5–3× is typical. Higher leverage lifts ROE but raises financial risk — for a non-financial, judge debt with net debt ÷ EBITDA and interest cover.",
            },
            benchmark={"bank": "about 12–25×", "insurer": "about 10–30×", "corporate": "about 1.5–3×"},
        ),
        RatioDef(
            "equity_ratio", "Equity ratio", "Eigenkapitalquote",
            r"\text{Equity ratio} = \frac{\text{Equity}_t}{\text{Total assets}_t} \times 100",
            "Shareholders' equity ÷ total assets × 100 (year-end)",
            (InputSpec("total_equity"), InputSpec("total_assets")),
            lambda v: _div(v[0], v[1]) * 100, "%", cfa="leverage",
            interpretation={
                "bank": "Simple (unweighted) capital measure — the accounting cousin of the regulatory leverage ratio.",
                "insurer": "Low equity ratios are normal; what matters is the risk-based solvency ratio.",
                "corporate": "Share of assets financed by equity. 40–60 % is solid for an industrial (Hilti targets at least 45 %); buybacks and debt-financed acquisitions lower it.",
            },
            benchmark={"bank": "about 4–8 %", "insurer": "about 3–10 %", "corporate": "about 30–60 %"},
        ),
        RatioDef(
            "payout", "Dividend payout ratio", "Ausschüttungsquote",
            r"\text{Payout} = \frac{\text{DPS}_t}{\text{EPS}_t} \times 100",
            "Dividend per share ÷ diluted EPS × 100",
            (InputSpec("dps"), InputSpec("eps")),
            lambda v: _div(v[0], v[1]) * 100, "%", higher_is_better=None, cfa="payout",
            interpretation={
                "bank": "Swiss banks pay out 40–60 % in cash and often add buybacks. A payout above 100 % is only sustainable with excess capital.",
                "insurer": "Insurers often target 50–70 %+. Judge sustainability against capital generation (solvency ratio stable?), not only against IFRS earnings.",
                "corporate": "Swiss blue chips are known for rising dividends; 50–80 % of IFRS EPS is common (Roche targets about half of core EPS). Check that free cash flow covers dividends plus buybacks — and watch the currency of the dividend.",
            },
            benchmark={"bank": "about 40–60 % (plus buybacks)", "insurer": "about 50–80 %", "corporate": "about 40–80 %"},
        ),
        RatioDef(
            "bvps", "Book value per share", "Buchwert je Aktie",
            r"\text{BVPS} = \frac{\text{Equity}_t}{\text{Shares outstanding}_t}",
            "Shareholders' equity ÷ shares outstanding (currency per share)",
            (InputSpec("total_equity"), InputSpec("shares_outstanding")),
            lambda v: _div(v[0], v[1]), "ccy", higher_is_better=True, cfa="bvps",
            interpretation={
                "bank": "The denominator of P/B. Growing BVPS (plus dividends) is a good long-run measure of value creation for banks.",
                "insurer": "Under IFRS 17 book value excludes the CSM — some analysts add the after-tax CSM ('adjusted book value').",
                "corporate": "Less informative for non-financials: book value leaves out internally developed assets (R&D pipelines, brands) and shrinks with buybacks, so P/B of 5–10× for pharma says little on its own.",
            },
        ),
        # ---------------------------------------------------------------- banks
        RatioDef(
            "cet1_calc", "CET1 ratio (calculated)", "Harte Kernkapitalquote (berechnet)",
            r"\text{CET1 ratio} = \frac{\text{CET1 capital}_t}{\text{RWA}_t} \times 100",
            "CET1 capital ÷ risk-weighted assets × 100",
            (InputSpec("cet1_capital"), InputSpec("rwa")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("bank",), cfa="cet1",
            interpretation={"bank": "The core solvency metric. Compare with the regulatory requirement plus buffers and the bank's own target; excess capital above the target can be returned to shareholders."},
            benchmark={"bank": "about 12–20 % for Swiss/European banks"},
        ),
        RatioDef(
            "rwa_density", "RWA density", "RWA-Dichte",
            r"\text{RWA density} = \frac{\text{RWA}_t}{\text{Total assets}_t} \times 100",
            "Risk-weighted assets ÷ total assets × 100",
            (InputSpec("rwa"), InputSpec("total_assets")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("bank",), higher_is_better=None, cfa="rwa_density",
            interpretation={"bank": "Low density (mortgages, Lombard loans, central-bank cash) means less capital per unit of balance sheet; high density means riskier assets (corporate loans, trading)."},
            benchmark={"bank": "about 20–45 %"},
        ),
        RatioDef(
            "nii_share", "Net interest income share", "Anteil Zinserfolg am Geschäftsertrag",
            r"\text{NII share} = \frac{\text{Net interest income}_t}{\text{Operating income}_t} \times 100",
            "Net interest income ÷ total operating income × 100",
            (InputSpec("net_interest_income"), InputSpec("revenue")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("bank",), higher_is_better=None, cfa="revenue_mix",
            interpretation={"bank": "A high NII share makes earnings sensitive to interest rates (SNB cuts hurt); a high fee share makes them sensitive to markets and client assets."},
        ),
        RatioDef(
            "fee_share", "Fee income share", "Anteil Kommissionserfolg am Geschäftsertrag",
            r"\text{Fee share} = \frac{\text{Net fee \& commission income}_t}{\text{Operating income}_t} \times 100",
            "Net fee and commission income ÷ total operating income × 100",
            (InputSpec("fee_income"), InputSpec("revenue")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("bank",), higher_is_better=None, cfa="revenue_mix",
            interpretation={"bank": "Fee income needs little capital, so a high fee share supports high ROE and P/B — typical of wealth managers."},
        ),
        RatioDef(
            "nnm_growth", "Net new money growth", "Neugeldwachstum",
            r"\text{NNM growth} = \frac{\text{Net new money}_t}{\text{AuM}_{t-1}} \times 100",
            "Net new money ÷ opening assets under management × 100",
            (InputSpec("net_new_money"), InputSpec("aum")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("bank",), cfa="nnm",
            interpretation={"bank": "Organic growth of client assets, excluding market performance and acquisitions. Wealth managers target about 3–5 % a year."},
            benchmark={"bank": "targets often 3–5 %"},
        ),
        # ---------------------------------------------------------------- insurers
        RatioDef(
            "insurance_margin", "Insurance service margin", "Versicherungstechnische Marge",
            r"\text{Margin} = \frac{\text{Insurance service result}_t}{\text{Insurance revenue}_t} \times 100",
            "Insurance service result ÷ insurance revenue × 100 (IFRS 17)",
            (InputSpec("insurance_service_result"), InputSpec("insurance_revenue")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("insurer",), cfa="insurance_metrics",
            interpretation={"insurer": "Underwriting profitability under IFRS 17 before investment result. For P&C it is roughly 100 % − combined ratio; for life it reflects CSM release and risk adjustment."},
        ),
        RatioDef(
            "investment_share", "Investment income share", "Anteil Kapitalanlageertrag",
            r"\text{Share} = \frac{\text{Net investment income}_t}{\text{Revenue}_t} \times 100",
            "Net investment income ÷ revenue × 100",
            (InputSpec("investment_income"), InputSpec("revenue")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("insurer",), higher_is_better=None, cfa="insurance_metrics",
            interpretation={"insurer": "How dependent the insurer is on investment returns. Life insurers depend heavily on them (spread business); reinsurers less so but still materially."},
        ),
        # ---------------------------------------------------------------- non-financial companies
        RatioDef(
            "ebit_margin", "EBIT margin (operating margin)", "EBIT-Marge (Betriebsergebnismarge)",
            r"\text{EBIT margin} = \frac{\text{EBIT}_t}{\text{Revenue}_t} \times 100",
            "Operating result (EBIT) ÷ revenue × 100",
            (InputSpec("ebit"), InputSpec("revenue")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("corporate",), core=True, cfa="ebit_margin",
            interpretation={"corporate": "Profitability of the operating business before financing and tax — the best margin for comparing companies with different debt and tax. Watch the trend: falling EBIT margin with rising sales means costs or prices are moving against the company. Hilti calls it 'return on sales'."},
            benchmark={"corporate": "pharma about 25–35 % (IFRS; higher on core); industrials about 10–15 %"},
        ),
        RatioDef(
            "cash_conversion", "Cash conversion (OCF ÷ net income)", "Cash-Conversion (operativer Cashflow ÷ Reingewinn)",
            r"\text{Cash conversion} = \frac{\text{Operating cash flow}_t}{\text{Net income}_t} \times 100",
            "Operating cash flow ÷ net income × 100",
            (InputSpec("operating_cash_flow"), InputSpec("net_income")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("corporate",), core=True, cfa="cash_conversion",
            interpretation={"corporate": "Does profit turn into cash? Above 100 % is normal because depreciation and amortisation are non-cash. Persistently below 100 % — or falling while profit rises — points to working capital build-up or aggressive accounting. One-off gains in net income (disposals) make it look low."},
            benchmark={"corporate": "usually about 100–150 %"},
        ),
        RatioDef(
            "fcf_margin", "Free cash flow margin", "Free-Cashflow-Marge",
            r"\text{FCF margin} = \frac{\text{Operating cash flow}_t - \text{Capex}_t}{\text{Revenue}_t} \times 100",
            "(Operating cash flow − capex) ÷ revenue × 100",
            (InputSpec("operating_cash_flow"), InputSpec("capex"), InputSpec("revenue")),
            lambda v: _div(v[0] - v[1], v[2]) * 100, "%", sectors=("corporate",), cfa="fcf",
            interpretation={"corporate": "Cash left after maintaining and expanding the asset base, per unit of sales — what is available for dividends, buybacks, acquisitions and debt repayment. Pharma converts 20–30 % of sales into free cash flow; industrials 5–10 %."},
            benchmark={"corporate": "pharma about 20–30 %; industrials about 5–10 %"},
        ),
        RatioDef(
            "net_debt_ebitda", "Net debt ÷ EBITDA", "Nettoverschuldung ÷ EBITDA",
            r"\text{Net debt / EBITDA} = \frac{\text{Financial debt}_t - \text{Cash}_t}{\text{EBIT}_t + \text{D\&A}_t}",
            "(Financial debt − cash) ÷ (EBIT + D&A), times",
            (InputSpec("total_debt"), InputSpec("cash"), InputSpec("ebit"), InputSpec("depreciation_amortisation")),
            lambda v: _div(v[0] - v[1], v[2] + v[3]), "x", sectors=("corporate",), higher_is_better=False, cfa="net_debt_ebitda",
            interpretation={"corporate": "How many years of operating cash earnings it would take to repay net debt. Below 1.5× is conservative, 2–3× is common after acquisitions, above 3–4× worries rating agencies. Negative means net cash."},
            benchmark={"corporate": "about 0–2.5× for strong ratings"},
        ),
        RatioDef(
            "roce", "Return on capital employed (ROCE)", "Rendite auf das eingesetzte Kapital (ROCE)",
            r"\text{ROCE} = \frac{\text{EBIT}_t}{\tfrac{1}{2}(\text{Equity} + \text{Debt} - \text{Cash})_{t-1,t}} \times 100",
            "EBIT ÷ average capital employed (equity + financial debt − cash) × 100",
            (InputSpec("ebit"), InputSpec("total_equity", averaged=True), InputSpec("total_debt", averaged=True), InputSpec("cash", averaged=True)),
            lambda v: _div(v[0], v[1] + v[2] - v[3]) * 100, "%", sectors=("corporate",), cfa="roce",
            interpretation={"corporate": "Pre-tax return on all the capital the business uses, regardless of how it is financed — so buybacks and leverage do not inflate it like ROE. Compare it with the pre-tax cost of capital (WACC grossed up for tax, roughly 8–10 %). Hilti reports its own ROCE (2025: 11.8 %)."},
            benchmark={"corporate": "about 10–25 %"},
        ),
        RatioDef(
            "gross_margin", "Gross margin", "Bruttomarge",
            r"\text{Gross margin} = \frac{\text{Gross profit}_t}{\text{Revenue}_t} \times 100",
            "Gross profit ÷ revenue × 100",
            (InputSpec("gross_profit"), InputSpec("revenue")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("corporate",), cfa="gross_margin",
            interpretation={"corporate": "Pricing power and production cost. Patented medicines: 70–80 %. A falling gross margin points to price pressure, input-cost inflation or a shift to lower-margin products."},
            benchmark={"corporate": "pharma about 70–80 %; tools and industrials about 40–65 %"},
        ),
        RatioDef(
            "rnd_intensity", "R&D intensity", "F&E-Quote",
            r"\text{R\&D intensity} = \frac{\text{R\&D expense}_t}{\text{Revenue}_t} \times 100",
            "R&D expense ÷ revenue × 100",
            (InputSpec("rnd_expense"), InputSpec("revenue")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("corporate",), higher_is_better=None, cfa="rnd",
            interpretation={"corporate": "How much of each franc of sales is reinvested in innovation. Big pharma spends 18–25 %; Hilti about 7 %. Cutting R&D lifts today's margin at the expense of tomorrow's growth."},
            benchmark={"corporate": "pharma about 18–25 %; industrials about 3–8 %"},
        ),
        RatioDef(
            "capex_intensity", "Capex intensity", "Investitionsquote",
            r"\text{Capex intensity} = \frac{\text{Capex}_t}{\text{Revenue}_t} \times 100",
            "Capital expenditure ÷ revenue × 100",
            (InputSpec("capex"), InputSpec("revenue")),
            lambda v: _div(v[0], v[1]) * 100, "%", sectors=("corporate",), higher_is_better=None, cfa="capex",
            interpretation={"corporate": "How capital-intensive the business is. Compare capex with depreciation: capex persistently below D&A means the asset base is shrinking; well above means expansion."},
            benchmark={"corporate": "about 3–8 %"},
        ),
        RatioDef(
            "interest_cover", "Interest cover", "Zinsdeckungsgrad",
            r"\text{Interest cover} = \frac{\text{EBIT}_t}{\text{Interest expense}_t}",
            "EBIT ÷ interest expense, times",
            (InputSpec("ebit"), InputSpec("interest_expense")),
            lambda v: _div(v[0], v[1]), "x", sectors=("corporate",), cfa="net_debt_ebitda",
            interpretation={"corporate": "How many times operating profit covers interest. Above 8–10× is comfortable; below 3× is a warning sign. It falls quickly when rates or debt rise."},
            benchmark={"corporate": "above about 8× for strong ratings"},
        ),
        RatioDef(
            "current_ratio", "Current ratio", "Liquiditätsgrad 3 (Current Ratio)",
            r"\text{Current ratio} = \frac{\text{Current assets}_t}{\text{Current liabilities}_t}",
            "Current assets ÷ current liabilities, times",
            (InputSpec("current_assets"), InputSpec("current_liabilities")),
            lambda v: _div(v[0], v[1]), "x", sectors=("corporate",), cfa="liquidity_ratios",
            interpretation={"corporate": "Short-term liquidity: can the company pay obligations due within a year from short-term assets? Around 1–2× is normal; below 1× is fine only for companies with strong cash flow and credit access."},
            benchmark={"corporate": "about 1–2×"},
        ),
        RatioDef(
            "asset_turnover", "Asset turnover", "Kapitalumschlag",
            r"\text{Asset turnover} = \frac{\text{Revenue}_t}{\tfrac{1}{2}(\text{Total assets}_{t-1} + \text{Total assets}_t)}",
            "Revenue ÷ average total assets, times",
            (InputSpec("revenue"), InputSpec("total_assets", averaged=True)),
            lambda v: _div(v[0], v[1]), "x", sectors=("corporate",), cfa="dupont",
            interpretation={"corporate": "Sales generated per unit of assets — the middle term of DuPont. Acquisitions (goodwill) lower it; asset-light models raise it."},
            benchmark={"corporate": "pharma about 0.5–0.7×; industrials about 0.8–1.2×"},
        ),
    ]
}

# NNM growth uses the *opening* AuM, not the average — handled explicitly.
OPENING_BALANCE = {("nnm_growth", "aum")}


def available_ratios(profile: dict, values: pd.DataFrame) -> list[RatioDef]:
    excluded = set(profile.get("not_applicable", []))
    out = []
    for r in RATIOS.values():
        if profile["sector"] not in r.sectors:
            continue
        if any(i.metric in excluded for i in r.inputs):
            continue
        if not all(i.metric in values.index and values.loc[i.metric].notna().any() for i in r.inputs):
            continue
        out.append(r)
    return out


@dataclass
class RequiredNumber:
    metric: str
    year: int
    value: float | None
    label: str


@dataclass
class RatioResult:
    ratio: RatioDef
    year: int
    value: float | None
    required: list[RequiredNumber]
    steps: list[str]
    alternative: float | None = None  # same ratio with year-end balances
    missing: list[str] = field(default_factory=list)


def _get(values: pd.DataFrame, key: str, year: int) -> float | None:
    if key not in values.index or year not in values.columns:
        return None
    x = values.at[key, year]
    return None if pd.isna(x) else float(x)


def compute(ratio: RatioDef, values: pd.DataFrame, year: int, currency: str = "") -> RatioResult:
    required: list[RequiredNumber] = []
    resolved: list[float | None] = []
    resolved_end: list[float | None] = []
    steps: list[str] = []
    missing: list[str] = []
    for spec in ratio.inputs:
        name = M.short(spec.metric)
        if (ratio.key, spec.metric) in OPENING_BALANCE:
            v0 = _get(values, spec.metric, year - 1)
            required.append(RequiredNumber(spec.metric, year - 1, v0, f"{name} {year - 1} (opening)"))
            resolved.append(v0)
            resolved_end.append(v0)
            if v0 is None:
                missing.append(f"{name} {year - 1}")
            continue
        if spec.averaged:
            v0, v1 = _get(values, spec.metric, year - 1), _get(values, spec.metric, year)
            required.append(RequiredNumber(spec.metric, year - 1, v0, f"{name} {year - 1}"))
            required.append(RequiredNumber(spec.metric, year, v1, f"{name} {year}"))
            if v0 is None:
                missing.append(f"{name} {year - 1}")
            if v1 is None:
                missing.append(f"{name} {year}")
            avg = (v0 + v1) / 2 if v0 is not None and v1 is not None else None
            resolved.append(avg)
            resolved_end.append(v1)
            if avg is not None:
                steps.append(f"Average {name} = ({v0:,.2f} + {v1:,.2f}) ÷ 2 = {avg:,.2f}")
        else:
            v1 = _get(values, spec.metric, year)
            required.append(RequiredNumber(spec.metric, year, v1, f"{name} {year}"))
            resolved.append(v1)
            resolved_end.append(v1)
            if v1 is None:
                missing.append(f"{name} {year}")
    value = None
    alternative = None
    if not missing:
        value = float(ratio.combine([float(x) for x in resolved]))
        if not np.isfinite(value):
            value = None
        if ratio.needs_prior_year:
            alt = float(ratio.combine([float(x) for x in resolved_end]))
            alternative = alt if np.isfinite(alt) else None
        if value is not None:
            nums = " ; ".join(f"{x:,.2f}" for x in resolved)
            steps.append(f"{ratio.text}: inputs {nums} → {format_ratio(value, ratio, currency)}")
    return RatioResult(ratio, year, value, required, steps, alternative, missing)


def format_ratio(x: float | None, ratio: RatioDef, currency: str = "") -> str:
    if x is None or not np.isfinite(x):
        return "–"
    if ratio.unit == "%":
        return f"{x:.2f} %"
    if ratio.unit == "x":
        return f"{x:.2f}×"
    return f"{currency} {x:,.2f}".strip()


@dataclass
class Diagnosis:
    correct: bool
    headline: str
    details: list[str]


def diagnose(result: RatioResult, user_inputs: dict[str, float | None], user_value: float | None, currency: str = "") -> Diagnosis:
    """Explain what went right or wrong in the learner's attempt.

    ``user_inputs`` maps "metric|year" → number the learner used.
    """
    details: list[str] = []
    if result.value is None:
        return Diagnosis(False, "This ratio cannot be computed — data is missing.", [f"Missing: {', '.join(result.missing)}"])
    wrong_inputs = []
    for rn in result.required:
        given = user_inputs.get(f"{rn.metric}|{rn.year}")
        if given is None:
            details.append(f"You did not enter {rn.label}.")
            wrong_inputs.append(rn)
        elif rn.value is not None and not is_close(given, rn.value, rel=0.005, abs_tol=0.005):
            details.append(f"{rn.label}: you used {given:,.2f}, the dataset has {rn.value:,.2f}.")
            wrong_inputs.append(rn)

    if user_value is None:
        return Diagnosis(False, "No result entered.", details)

    tol_abs = 0.05 if result.ratio.unit in ("%",) else 0.02
    if is_close(user_value, result.value, rel=0.01, abs_tol=tol_abs):
        if wrong_inputs:
            details.append("Your final answer matches, but check the inputs above.")
        return Diagnosis(True, f"Correct — {format_ratio(result.value, result.ratio, currency)}.", details)

    # Same calculation with year-end balances instead of averages?
    if result.alternative is not None and is_close(user_value, result.alternative, rel=0.01, abs_tol=tol_abs):
        details.append(
            f"You used year-end balances ({format_ratio(result.alternative, result.ratio, currency)}). "
            "That is a common shortcut, but CFA convention uses the average of opening and closing balances because the income was earned over the whole year."
        )
        return Diagnosis(False, "Close — different convention (year-end instead of average balance).", details)

    # Percent vs decimal
    if result.ratio.unit == "%" and is_close(user_value * 100, result.value, rel=0.01, abs_tol=tol_abs):
        details.append("You entered a decimal (e.g. 0.12) — enter the ratio in percent (12.0).")
        return Diagnosis(False, "Right number, wrong format (decimal instead of percent).", details)

    # Inverted ratio?
    if result.value and is_close(user_value, (100 * 100 / result.value) if result.ratio.unit == "%" else 1 / result.value, rel=0.02, abs_tol=tol_abs):
        details.append("It looks like you divided the inputs the wrong way round (denominator ÷ numerator).")
        return Diagnosis(False, "Inverted ratio.", details)

    # Arithmetic consistent with the learner's own (wrong) inputs?
    try:
        vals: list[float] = []
        for spec in result.ratio.inputs:
            if (result.ratio.key, spec.metric) in OPENING_BALANCE:
                vals.append(float(user_inputs[f"{spec.metric}|{result.year - 1}"]))
            elif spec.averaged:
                a = user_inputs[f"{spec.metric}|{result.year - 1}"]
                b = user_inputs[f"{spec.metric}|{result.year}"]
                vals.append((float(a) + float(b)) / 2)
            else:
                vals.append(float(user_inputs[f"{spec.metric}|{result.year}"]))
        own = float(result.ratio.combine(vals))
        if wrong_inputs and is_close(user_value, own, rel=0.01, abs_tol=tol_abs):
            details.append("Your arithmetic is consistent with the numbers you picked — the problem is the inputs.")
            return Diagnosis(False, "Wrong inputs, correct method.", details)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        pass

    details.append(f"Expected {format_ratio(result.value, result.ratio, currency)}; you entered {format_ratio(user_value, result.ratio, currency)}.")
    return Diagnosis(False, "Not quite — compare your steps with the worked solution.", details)


def dupont(values: pd.DataFrame, year: int) -> dict | None:
    """Three-step DuPont: ROE = net margin × asset turnover × leverage (average balances)."""
    def g(k, y):
        return _get(values, k, y)

    ni, rev = g("net_income", year), g("revenue", year)
    a0, a1, e0, e1 = g("total_assets", year - 1), g("total_assets", year), g("total_equity", year - 1), g("total_equity", year)
    if None in (ni, a0, a1, e0, e1):
        return None
    avg_a, avg_e = (a0 + a1) / 2, (e0 + e1) / 2
    out = {"roa": ni / avg_a * 100, "leverage": avg_a / avg_e, "roe": ni / avg_e * 100}
    if rev:
        out["net_margin"] = ni / rev * 100
        out["asset_turnover"] = rev / avg_a
    return out
