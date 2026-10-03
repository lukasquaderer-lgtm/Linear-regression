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
    core: bool = False  # part of the mandatory Stage 4 set
    cfa: str = ""
    interpretation: dict = field(default_factory=dict)  # sector -> text
    benchmark: dict = field(default_factory=dict)  # sector -> rule-of-thumb range text

    def label(self) -> str:
        return f"{self.en} · {self.de}"

    @property
    def needs_prior_year(self) -> bool:
        return any(i.averaged for i in self.inputs)


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
            },
            benchmark={"bank": "Swiss/European banks: about 5–15 %", "insurer": "Life insurers: about 8–15 %; reinsurers: volatile, 0–20 %"},
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
            },
            benchmark={"bank": "about 0.3–1.0 %", "insurer": "about 0.3–1.5 %"},
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
            },
            benchmark={"bank": "about 15–30 %", "insurer": "basis-dependent (IFRS 17: about 5–15 %)"},
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
            lambda v: _div(v[0], v[1]), "x", higher_is_better=None, core=True, cfa="leverage",
            interpretation={
                "bank": "Banks typically run 12–25× leverage. Higher leverage boosts ROE but leaves less loss absorption — regulators cap it via capital and leverage-ratio rules.",
                "insurer": "Insurers often show 15–30× because policyholder liabilities dominate the balance sheet. Look at the solvency ratio for the real capital buffer.",
            },
            benchmark={"bank": "about 12–25×", "insurer": "about 10–30×"},
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
            },
            benchmark={"bank": "about 4–8 %", "insurer": "about 3–10 %"},
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
            },
            benchmark={"bank": "about 40–60 % (plus buybacks)", "insurer": "about 50–80 %"},
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
