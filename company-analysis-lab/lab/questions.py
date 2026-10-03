"""Analyst Training Mode: question bank, grading and spaced repetition.

After each stage the app builds a 5-question quiz with progressively harder levels:

    Level 1  identify the metric
    Level 2  calculate it
    Level 3  interpret it
    Level 4  connect several financial statements
    Level 5  analyst-style reasoning (free text, self-assessed against a model answer)

Questions are generated from templates using the company's own data where possible
(with hypothetical numbers as a fallback). Every question is tagged with a concept;
concepts answered wrongly are scheduled for review with a Leitner system and come
back in later quizzes (replacing the easiest questions) and on the Review page.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

import numpy as np
import pandas as pd

from . import calculations as C
from . import metrics as M
from . import ratios as R
from . import valuation as V

# --------------------------------------------------------------------------- model


@dataclass
class Question:
    id: str
    stage: int
    level: int
    concept: str
    kind: str  # "mc" | "numeric" | "text"
    prompt: str
    options: list[str] = field(default_factory=list)
    answer: float | int | None = None
    rel_tol: float = 0.02
    abs_tol: float = 0.1
    unit: str = ""
    explanation: str = ""
    model_answer: str = ""
    review: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Question":
        return Question(**d)


@dataclass
class QuizContext:
    profile: dict
    values: pd.DataFrame
    currency: str
    progress: dict = field(default_factory=dict)
    peer_profile: dict | None = None
    peer_values: pd.DataFrame | None = None

    @property
    def sector(self) -> str:
        return self.profile["sector"]

    @property
    def name(self) -> str:
        return self.profile.get("short_name", self.profile["name"])


LEVEL_NAMES = {1: "Identify", 2: "Calculate", 3: "Interpret", 4: "Connect statements", 5: "Analyst reasoning"}

CONCEPT_LABELS = {
    "revenue_lines": "Revenue lines of banks and insurers",
    "business_model": "Business model and earnings drivers",
    "revenue_mix": "Revenue mix (interest vs fees)",
    "payout": "Payout ratio and retention",
    "linking_statements": "Linking the financial statements",
    "competitive_advantage": "Competitive advantages",
    "statement_location": "Where metrics are reported",
    "balance_sheet_identity": "Balance-sheet identity",
    "data_units": "Units and data hygiene",
    "eps_consistency": "EPS, shares and net income",
    "accounting_changes": "Accounting changes and restatements",
    "growth_cagr": "CAGR",
    "yoy_growth": "Year-over-year growth",
    "trend_interpretation": "Interpreting trends",
    "ratio_definitions": "Ratio definitions",
    "roe": "Return on equity",
    "roa": "Return on assets",
    "dupont": "DuPont decomposition",
    "roe_vs_cost_of_equity": "ROE vs cost of equity",
    "annual_report_navigation": "Navigating the annual report",
    "statement_links": "Equity roll-forward",
    "auditor_report": "Auditor's report and key audit matters",
    "cash_flow_banks": "Cash flow statements of banks",
    "operational_vs_accounting": "Operational vs accounting-driven changes",
    "one_off_items": "One-off items",
    "underlying_earnings": "Underlying earnings",
    "reserves": "Reserve and provision releases",
    "accruals": "Accrual ratio",
    "quality_earnings": "Earnings quality judgement",
    "regulatory_capital": "Regulatory capital ratios",
    "capital_shock": "Capital stress arithmetic",
    "risk_interest": "Interest-rate risk",
    "risk_market": "Market risk transmission",
    "risk_prioritisation": "Prioritising risks",
    "peers": "Peer comparability",
    "justified_pb": "ROE and P/B",
    "leverage": "Leverage",
    "peer_selection": "Choosing peers",
    "valuation_methods": "Choosing a valuation method",
    "ddm": "Dividend discount model",
    "thesis": "Investment thesis discipline",
    "scenario_analysis": "Scenario-weighted value",
    "portfolio": "Portfolio context",
    "sustainable_growth": "Sustainable growth",
    "acquisition_effects": "Acquisition effects",
    "combined_ratio": "Combined ratio",
}


def concept_label(concept: str) -> str:
    return CONCEPT_LABELS.get(concept, concept.replace("_", " ").capitalize())


# --------------------------------------------------------------------------- helpers


def _val(values: pd.DataFrame, key: str, year: int) -> float | None:
    if values is None or key not in values.index or year not in values.columns:
        return None
    x = values.at[key, year]
    return None if pd.isna(x) else float(x)


def _years(values: pd.DataFrame) -> list[int]:
    return sorted(int(c) for c in values.columns) if values is not None else []


def _latest_with(values: pd.DataFrame, keys: list[str], need_prior: bool = False) -> int | None:
    for y in reversed(_years(values)):
        if all(_val(values, k, y) is not None for k in keys):
            if need_prior and not all(_val(values, k, y - 1) is not None for k in keys):
                continue
            return y
    return None


def _mc(qid, stage, level, concept, prompt, correct, wrong, rng, explanation="") -> Question:
    options = [correct] + list(wrong)
    order = list(range(len(options)))
    rng.shuffle(order)
    shuffled = [options[i] for i in order]
    return Question(qid, stage, level, concept, "mc", prompt, shuffled, shuffled.index(correct), explanation=explanation)


def _num(qid, stage, level, concept, prompt, answer, unit, explanation, rel_tol=0.02, abs_tol=0.1) -> Question:
    return Question(qid, stage, level, concept, "numeric", prompt, answer=float(answer), unit=unit, explanation=explanation, rel_tol=rel_tol, abs_tol=abs_tol)


def _text(qid, stage, level, concept, prompt, model_answer) -> Question:
    return Question(qid, stage, level, concept, "text", prompt, model_answer=model_answer)


def _money(x: float, ccy: str) -> str:
    return f"{ccy} {C.fmt_num(x)} m"


PROFILE_CONCEPT_STAGE = {
    "business_model": 1,
    "combined_ratio": 2,
    "accounting_changes": 3,
    "one_off_items": 5,
    "acquisition_effects": 5,
    "linking_statements": 5,
    "valuation_methods": 9,
}


def _profile_question(ctx: QuizContext, stage: int, level: int, rng) -> Question | None:
    items = [q for q in ctx.profile.get("quiz", []) if PROFILE_CONCEPT_STAGE.get(q["concept"]) == stage and q["level"] == level]
    if not items:
        return None
    q = rng.choice(items)
    correct = q["options"][q["answer"]]
    wrong = [o for i, o in enumerate(q["options"]) if i != q["answer"]]
    return _mc(f"profile-{ctx.profile['id']}-{q['concept']}-{level}", stage, level, q["concept"], q["prompt"], correct, wrong, rng, q.get("explanation", ""))


# --------------------------------------------------------------------------- templates


@dataclass
class Template:
    id: str
    stage: int
    level: int
    concepts: tuple[str, ...]
    build: Callable[[QuizContext, random.Random], Question | None]


TEMPLATES: list[Template] = []


def template(id: str, stage: int, level: int, *concepts: str):
    def deco(fn):
        TEMPLATES.append(Template(id, stage, level, concepts, fn))
        return fn

    return deco


# ---------------------------------------------------------------- Stage 1 — business


@template("s1-revenue-line", 1, 1, "revenue_lines")
def _(ctx, rng):
    if ctx.sector == "bank":
        return _mc("s1-revenue-line-bank", 1, 1, "revenue_lines",
                   "Which income-statement line captures what a bank earns on loans and securities after paying interest on deposits and debt?",
                   "Net interest income (Zinserfolg)", ["Net fee and commission income", "Trading income", "Other operating income"], rng,
                   "Net interest income = interest income − interest expense. Fees come from services; trading from market-making and FX.")
    return _mc("s1-revenue-line-ins", 1, 1, "revenue_lines",
               "Under IFRS 17, which line shows what an insurer earns for providing insurance cover in the period?",
               "Insurance revenue (Versicherungsumsatz)", ["Gross written premiums", "Net investment income", "Insurance finance expenses"], rng,
               "Insurance revenue reflects services provided in the period and excludes investment components; gross written premiums is a volume measure.")


@template("s1-profile-l1", 1, 1, "business_model")
def _(ctx, rng):
    return _profile_question(ctx, 1, 1, rng)


@template("s1-payout", 1, 2, "payout")
def _(ctx, rng):
    y = _latest_with(ctx.values, ["eps", "dps"])
    if y is not None and (_val(ctx.values, "eps", y) or 0) > 0:
        eps, dps = _val(ctx.values, "eps", y), _val(ctx.values, "dps", y)
        ans = dps / eps * 100
        return _num(f"s1-payout-{y}", 1, 2, "payout",
                    f"How much of its profit does {ctx.name} hand back as dividends? In {y} diluted EPS was {ctx.currency} {eps:.2f} and the dividend per share {ctx.currency} {dps:.2f}. Calculate the payout ratio in %.",
                    ans, "%", f"Payout = DPS ÷ EPS = {dps:.2f} ÷ {eps:.2f} = {ans:.1f} %.")
    eps = rng.choice([4.0, 5.5, 8.0, 12.0])
    dps = round(eps * rng.choice([0.4, 0.5, 0.6, 0.7]), 2)
    return _num("s1-payout-generic", 1, 2, "payout",
                f"A financial company reports diluted EPS of {eps:.2f} and proposes a dividend of {dps:.2f} per share. What is the payout ratio in %?",
                dps / eps * 100, "%", f"Payout = DPS ÷ EPS = {dps:.2f} ÷ {eps:.2f} = {dps / eps * 100:.1f} %.")


@template("s1-revenue-mix", 1, 2, "revenue_mix")
def _(ctx, rng):
    if ctx.sector == "bank":
        y = _latest_with(ctx.values, ["fee_income", "revenue"])
        if y is not None:
            fee, rev = _val(ctx.values, "fee_income", y), _val(ctx.values, "revenue", y)
            return _num(f"s1-feeshare-{y}", 1, 2, "revenue_mix",
                        f"{ctx.name} {y}: net fee and commission income {_money(fee, ctx.currency)}, total operating income {_money(rev, ctx.currency)}. What share of operating income comes from fees (%)?",
                        fee / rev * 100, "%", f"Fee share = {fee:,.0f} ÷ {rev:,.0f} = {fee / rev * 100:.1f} %.")
        nii, fee, trd = rng.choice([(4200, 5100, 1700), (300, 520, 80), (6500, 19000, 9000)])
        tot = nii + fee + trd
        return _num("s1-feeshare-generic", 1, 2, "revenue_mix",
                    f"A bank earns net interest income of {nii:,}, fees of {fee:,} and trading income of {trd:,} (total {tot:,}). What share of operating income comes from fees (%)?",
                    fee / tot * 100, "%", f"{fee:,} ÷ {tot:,} = {fee / tot * 100:.1f} %. A high fee share means less capital-intensive, more market-sensitive earnings.")
    sav, risk, fee = rng.choice([(600, 250, 400), (900, 300, 700), (450, 150, 500)])
    tot = sav + risk + fee
    return _num("s1-feeshare-ins", 1, 2, "revenue_mix",
                f"A life insurer's operating result comes from the savings result {sav}, the risk result {risk} and the fee result {fee} (total {tot}). What share comes from the fee result (%)?",
                fee / tot * 100, "%", f"{fee} ÷ {tot} = {fee / tot * 100:.1f} %. Fee income needs little solvency capital.")


@template("s1-interpret", 1, 3, "business_model")
def _(ctx, rng):
    q = _profile_question(ctx, 1, 3, rng)
    if q:
        return q
    if ctx.sector == "bank":
        return _mc("s1-interpret-bank", 1, 3, "business_model",
                   "Most of a wealth manager's fees are 'recurring' — charged as a percentage of client assets. What happens to these fees if markets fall 20 % and no client leaves?",
                   "They fall roughly in line with client assets — earnings are market-sensitive even without outflows",
                   ["They stay flat because no client left", "They rise because clients trade more", "They are unaffected because they are contractual fixed fees"], rng,
                   "Asset-based fees scale with the value of assets under management.")
    return _mc("s1-interpret-ins", 1, 3, "business_model",
               "Why do a reinsurer's profits swing more from year to year than a life insurer's?",
               "Large natural catastrophes hit P&C reinsurance results in irregular years",
               ["Reinsurers do not invest their premiums", "Reinsurers report under cash accounting", "Life insurers have no investment risk"], rng,
               "Catastrophe losses are lumpy; life business earns more stable spread and fee income.")


@template("s1-link", 1, 4, "linking_statements")
def _(ctx, rng):
    if ctx.sector == "bank":
        return _mc("s1-link-bank", 1, 4, "linking_statements",
                   "A bank's customer deposits grow strongly while loans stay flat. Where does the extra money end up, and what happens to net interest income if central-bank rates then fall?",
                   "In cash at the central bank and liquid securities (balance sheet); NII falls as the yield on that liquidity drops",
                   ["In equity; NII rises", "In goodwill; NII is unaffected", "In the cash flow statement only; NII rises"], rng,
                   "Deposits are liabilities funding assets — surplus deposits are parked in liquidity whose yield moves with policy rates.")
    return _mc("s1-link-ins", 1, 4, "linking_statements",
               "An insurer collects premiums today and pays claims years later. Where does that money sit in the meantime, and which income-statement line does it feed?",
               "In investments (balance sheet), producing investment income (income statement)",
               ["In equity, producing fee income", "In goodwill, producing insurance revenue", "Off balance sheet, producing nothing"], rng,
               "The 'float' is invested — matched by insurance liabilities on the other side of the balance sheet.")


@template("s1-moat", 1, 5, "competitive_advantage")
def _(ctx, rng):
    ref = ctx.profile.get("business_reference", {}).get("advantages", {}).get("reference", "")
    extra = ("For a bank: falling net new money, a shrinking fee margin (fees ÷ average client assets), rising cost/income, loss of market share in key regions."
             if ctx.sector == "bank" else
             "For an insurer: falling new-business margins or CSM growth, rising lapse rates, a deteriorating combined ratio, losing market share in core lines.")
    return _text("s1-moat", 1, 5, "competitive_advantage",
                 f"Choose the competitive advantage of {ctx.name} you think is most durable. Which numbers in the annual report, tracked over several years, would show you that it is eroding?",
                 f"Reference advantages: {ref} Evidence of erosion — {extra} A good answer names one specific advantage, the metric that measures it, and the direction that would worry you.")


# ---------------------------------------------------------------- Stage 2 — data

STATEMENT_OF = {
    "revenue": "Income statement", "net_income": "Income statement", "operating_expenses": "Income statement",
    "net_interest_income": "Income statement", "fee_income": "Income statement", "eps": "Income statement",
    "insurance_revenue": "Income statement", "investment_income": "Income statement", "insurance_service_result": "Income statement",
    "total_assets": "Balance sheet", "total_liabilities": "Balance sheet", "total_equity": "Balance sheet",
    "customer_loans": "Balance sheet", "customer_deposits": "Balance sheet",
    "operating_cash_flow": "Cash flow statement",
    "cet1_capital": "Regulatory disclosure (Pillar 3 / SFCR)", "rwa": "Regulatory disclosure (Pillar 3 / SFCR)",
    "cet1_ratio": "Regulatory disclosure (Pillar 3 / SFCR)", "solvency_ratio": "Regulatory disclosure (Pillar 3 / SFCR)",
    "aum": "Management report / key figures", "net_new_money": "Management report / key figures", "gross_premiums": "Management report / key figures",
}
STATEMENT_OPTIONS = ["Income statement", "Balance sheet", "Cash flow statement", "Regulatory disclosure (Pillar 3 / SFCR)", "Management report / key figures"]


@template("s2-where", 2, 1, "statement_location")
def _(ctx, rng):
    keys = [k for k in STATEMENT_OF if ctx.sector in M.CATALOG[k].sectors and k not in ctx.profile.get("not_applicable", [])]
    key = rng.choice(keys)
    correct = STATEMENT_OF[key]
    wrong = [o for o in STATEMENT_OPTIONS if o != correct][:3]
    return _mc(f"s2-where-{key}", 2, 1, "statement_location", f"Where would you primarily look up '{M.CATALOG[key].label()}'?", correct, wrong, rng,
               f"{M.CATALOG[key].en}: {M.CATALOG[key].statement or correct}.")


@template("s2-profile-l1", 2, 1, "combined_ratio")
def _(ctx, rng):
    return _profile_question(ctx, 2, 1, rng)


@template("s2-identity", 2, 2, "balance_sheet_identity")
def _(ctx, rng):
    y = _latest_with(ctx.values, ["total_assets", "total_equity"])
    if y is not None:
        a, e = _val(ctx.values, "total_assets", y), _val(ctx.values, "total_equity", y)
        return _num(f"s2-identity-{y}", 2, 2, "balance_sheet_identity",
                    f"{ctx.name} {y}: total assets {_money(a, ctx.currency)}, shareholders' equity {_money(e, ctx.currency)}. Ignoring non-controlling interests, what are total liabilities ({ctx.currency} m)?",
                    a - e, f"{ctx.currency} m", f"Assets = liabilities + equity → liabilities = {a:,.0f} − {e:,.0f} = {a - e:,.0f}. (Minority interests would sit between the two.)", rel_tol=0.005, abs_tol=1)
    a, e = rng.choice([(25000, 2100), (220000, 7500), (130000, 23000)])
    return _num("s2-identity-generic", 2, 2, "balance_sheet_identity",
                f"Total assets are {a:,} and shareholders' equity {e:,}. What are total liabilities?", a - e, "", f"{a:,} − {e:,} = {a - e:,}.", rel_tol=0.005, abs_tol=1)


@template("s2-units", 2, 3, "data_units")
def _(ctx, rng):
    return _mc("s2-units", 2, 3, "data_units",
               "Your dataset shows equity of 85,079 (USD m) for a bank. A colleague's spreadsheet shows 85.1 for the same year and the same company. What is the most likely explanation?",
               "The colleague's sheet is in billions, yours in millions — always label units",
               ["The colleague used a different company", "The bank restated equity by 99.9 %", "One of you used per-share values"], rng,
               "Unit mismatches (m vs bn, % vs decimal) are the most common data-entry error. That is why every row in Stage 2 carries a unit.")


@template("s2-eps", 2, 4, "eps_consistency")
def _(ctx, rng):
    y = _latest_with(ctx.values, ["net_income", "eps"])
    if y is not None and (_val(ctx.values, "eps", y) or 0) > 0:
        ni, eps = _val(ctx.values, "net_income", y), _val(ctx.values, "eps", y)
        return _num(f"s2-eps-{y}", 2, 4, "eps_consistency",
                    f"{ctx.name} {y}: net income attributable to shareholders {_money(ni, ctx.currency)} (income statement) and diluted EPS {ctx.currency} {eps:.2f}. What diluted share count (millions) do these two numbers imply?",
                    ni / eps, "m shares", f"Shares ≈ net income ÷ EPS = {ni:,.0f} ÷ {eps:.2f} = {ni / eps:,.1f} m. Compare with the EPS note — a big gap means a different earnings basis or a data error.", rel_tol=0.01)
    ni, eps = rng.choice([(1200, 42.0), (7500, 2.3), (165, 5.4)])
    return _num("s2-eps-generic", 2, 4, "eps_consistency", f"Net income is {ni:,} m and diluted EPS {eps:.2f}. Implied diluted share count (millions)?", ni / eps, "m shares", f"{ni:,} ÷ {eps:.2f} = {ni / eps:,.1f} m.", rel_tol=0.01)


@template("s2-basis", 2, 5, "accounting_changes")
def _(ctx, rng):
    bases = list(dict.fromkeys(ctx.profile.get("accounting", {}).values()))
    if len(bases) > 1:
        return _text("s2-basis", 2, 5, "accounting_changes",
                     f"Your {ctx.name} dataset mixes accounting bases: {', '.join(bases)}. How does this affect trend analysis, and what would you do about it?",
                     "Figures before and after a change in standards are not comparable (e.g. IFRS 17 removes savings components from revenue and moves future profit into the CSM; US GAAP vs IFRS measure equity differently). Use restated comparatives where the company provides them, mark the break in charts, compare growth only within the same basis, and prefer ratios/KPIs that are less affected (e.g. solvency ratio, dividends). State the limitation explicitly.")
    return _text("s2-basis-vendor", 2, 5, "accounting_changes",
                 f"Part of your {ctx.name} dataset came from a data vendor. Give two reasons why vendor figures can differ from the annual report, and say which source you treat as authoritative.",
                 "Vendors standardise line items to an industrial template (mapping a bank's 'operating income' to 'gross profit'), may use different definitions (attributable vs total net income, basic vs diluted EPS), mix restated and original figures, or convert currencies. The audited annual report is authoritative; the vendor is a cross-check.")


# ---------------------------------------------------------------- Stage 3 — trends


@template("s3-cagr-def", 3, 1, "growth_cagr")
def _(ctx, rng):
    return _mc("s3-cagr-def", 3, 1, "growth_cagr", "Net income grew at a 4-year CAGR of 5 %. What does that mean?",
               "The constant annual growth rate that turns the first year's value into the last year's value",
               ["Net income grew by 5 % in each of the four years", "The average of the four yearly growth rates was 5 %", "Net income is 5 % higher than four years ago"], rng,
               "CAGR is a geometric average: (end ÷ start)^(1/n) − 1. Individual years can differ wildly.")


@template("s3-cagr", 3, 2, "growth_cagr")
def _(ctx, rng):
    candidates = []
    for key in ["net_income", "total_equity", "revenue", "dps", "eps", "aum", "total_assets"]:
        s = ctx.values.loc[key].dropna() if key in ctx.values.index else pd.Series(dtype=float)
        if len(s) >= 3 and s.iloc[0] > 0 and s.iloc[-1] > 0:
            candidates.append((key, s))
    if candidates:
        key, s = rng.choice(candidates)
        y0, y1 = int(s.index[0]), int(s.index[-1])
        ans = C.cagr(float(s.iloc[0]), float(s.iloc[-1]), y1 - y0)
        return _num(f"s3-cagr-{key}", 3, 2, "growth_cagr",
                    f"{ctx.name}: {M.short(key)} was {s.iloc[0]:,.2f} in {y0} and {s.iloc[-1]:,.2f} in {y1}. Calculate the CAGR in %.",
                    ans, "%", f"CAGR = ({s.iloc[-1]:,.2f} ÷ {s.iloc[0]:,.2f})^(1/{y1 - y0}) − 1 = {ans:.2f} %.", abs_tol=0.1)
    a, b, n = rng.choice([(100, 146.4, 4), (2000, 2600, 4), (50, 41, 3)])
    ans = C.cagr(a, b, n)
    return _num("s3-cagr-generic", 3, 2, "growth_cagr", f"A metric went from {a} to {b} over {n} years. CAGR in %?", ans, "%", f"({b} ÷ {a})^(1/{n}) − 1 = {ans:.2f} %.")


@template("s3-yoy", 3, 2, "yoy_growth")
def _(ctx, rng):
    ys = _years(ctx.values)
    pairs = []
    for key in ["net_income", "revenue", "total_equity", "eps"]:
        for y in ys[1:]:
            a, b = _val(ctx.values, key, y - 1), _val(ctx.values, key, y)
            if a and b and a > 0:
                pairs.append((key, y, a, b))
    if pairs:
        key, y, a, b = rng.choice(pairs)
        ans = (b / a - 1) * 100
        return _num(f"s3-yoy-{key}-{y}", 3, 2, "yoy_growth", f"{ctx.name}: {M.short(key)} {y - 1} = {a:,.2f}, {y} = {b:,.2f}. Year-over-year growth in %?",
                    ans, "%", f"({b:,.2f} ÷ {a:,.2f}) − 1 = {ans:+.2f} %.")
    return _num("s3-yoy-generic", 3, 2, "yoy_growth", "Revenue went from 480 to 516. Growth in %?", 7.5, "%", "516 ÷ 480 − 1 = 7.5 %.")


@template("s3-margin", 3, 3, "trend_interpretation")
def _(ctx, rng):
    rev = ctx.values.loc["revenue"].dropna() if "revenue" in ctx.values.index else pd.Series(dtype=float)
    ni = ctx.values.loc["net_income"].dropna() if "net_income" in ctx.values.index else pd.Series(dtype=float)
    common = [y for y in rev.index if y in ni.index]
    if len(common) >= 3:
        y0, y1 = common[0], common[-1]
        gr = C.cagr(rev[y0], rev[y1], y1 - y0)
        gn = C.cagr(ni[y0], ni[y1], y1 - y0)
        if gr is not None and gn is not None and abs(gr - gn) > 0.5:
            correct = "It rose — profit grew faster than revenue" if gn > gr else "It fell — profit grew more slowly than revenue (costs, losses or taxes rose faster)"
            wrong = ["It fell — profit grew more slowly than revenue (costs, losses or taxes rose faster)" if gn > gr else "It rose — profit grew faster than revenue",
                     "It cannot change if both grow", "It doubled"]
            return _mc(f"s3-margin-{ctx.profile['id']}", 3, 3, "trend_interpretation",
                       f"From {y0} to {y1}, {ctx.name}'s revenue grew at {gr:.1f} % a year and net income at {gn:.1f} % a year. What happened to the net profit margin?",
                       correct, wrong, rng, "Margin = net income ÷ revenue. If the numerator grows faster than the denominator, the margin rises.")
    return _mc("s3-margin-generic", 3, 3, "trend_interpretation",
               "Revenue grew at 5 % a year while net income fell at 3 % a year. What does it tell you?",
               "Margins are compressing — investigate costs, credit losses, taxes or one-offs",
               ["The company is becoming more efficient", "Nothing — growth rates of different lines are unrelated", "The share count must have fallen"], rng)


@template("s3-profile-l3", 3, 3, "accounting_changes")
def _(ctx, rng):
    for lvl in (2, 4, 3):
        q = _profile_question(ctx, 3, lvl, rng)
        if q:
            q.level = 3
            return q
    return None


@template("s3-equity-roll", 3, 4, "linking_statements")
def _(ctx, rng):
    for y in reversed(_years(ctx.values)):
        r = C.implied_other_equity_movements(ctx.values, y)
        if r and r["dividends_known"]:
            ans = r["other"]
            return _num(f"s3-roll-{y}", 3, 4, "linking_statements",
                        f"{ctx.name} {y}: equity rose from {_money(r['opening'], ctx.currency)} to {_money(r['closing'], ctx.currency)}. Net income was {_money(r['net_income'], ctx.currency)} and dividends paid about {_money(r['dividends'], ctx.currency)} (prior-year DPS × shares). "
                        f"How large were all OTHER equity movements combined (buybacks, OCI, FX, acquisitions…)? Enter a negative number for a reduction ({ctx.currency} m).",
                        ans, f"{ctx.currency} m",
                        f"ΔEquity − (net income − dividends) = ({r['closing']:,.0f} − {r['opening']:,.0f}) − ({r['net_income']:,.0f} − {r['dividends']:,.0f}) = {ans:,.0f}. Find the components in the statement of changes in equity.",
                        rel_tol=0.03, abs_tol=max(1.0, abs(r["closing"]) * 0.002))
    o, ni, d, c = 10000, 900, 450, 10150
    return _num("s3-roll-generic", 3, 4, "linking_statements",
                f"Opening equity {o:,}, net income {ni:,}, dividends paid {d:,}, closing equity {c:,}. Other movements combined?", c - o - ni + d, "", f"{c:,} − {o:,} − {ni:,} + {d:,} = {c - o - ni + d:,}.", abs_tol=1)


@template("s3-reverse", 3, 5, "trend_interpretation")
def _(ctx, rng):
    model = ("Banks: net interest income after central-bank rate cuts (SNB at 0 %), credit-loss releases that cannot repeat, cost savings that are front-loaded, one-off gains (e.g. negative goodwill) dropping out. "
             if ctx.sector == "bank" else
             "Insurers: reserve releases or a benign catastrophe year that will not repeat, investment yields after rate moves, accounting effects from IFRS 17 transition, buyback-driven EPS growth. ")
    return _text("s3-reverse", 3, 5, "trend_interpretation",
                 f"Which trend you analysed for {ctx.name} is most likely to reverse in the next two years? Explain the mechanism, not just the direction.",
                 model + "A strong answer names the metric, the driver behind the past trend, why that driver changes, and which number you would monitor.")


# ---------------------------------------------------------------- Stage 4 — ratios


@template("s4-identify", 4, 1, "ratio_definitions")
def _(ctx, rng):
    choices = [
        ("Net income ÷ average shareholders' equity", "Return on equity (ROE)"),
        ("Net income ÷ average total assets", "Return on assets (ROA)"),
        ("Average total assets ÷ average equity", "Financial leverage (equity multiplier)"),
        ("Operating expenses ÷ operating income", "Cost/income ratio"),
        ("Dividend per share ÷ EPS", "Payout ratio"),
    ]
    formula, correct = rng.choice(choices)
    wrong = [c[1] for c in choices if c[1] != correct][:3]
    return _mc(f"s4-identify-{correct[:10]}", 4, 1, "ratio_definitions", f"Which ratio is defined as: {formula}?", correct, wrong, rng)


@template("s4-calc", 4, 2, "roa", "roe")
def _(ctx, rng):
    options = []
    for key in ("roa", "roe"):
        rd = R.RATIOS[key]
        y = _latest_with(ctx.values, [i.metric for i in rd.inputs], need_prior=True)
        if y is not None:
            options.append((key, y))
    if options:
        key, y = rng.choice(options)
        res = R.compute(R.RATIOS[key], ctx.values, y, ctx.currency)
        if res.value is not None:
            nums = "; ".join(f"{rn.label}: {rn.value:,.0f}" for rn in res.required)
            return _num(f"s4-{key}-{y}", 4, 2, key, f"{ctx.name} {y}. {nums}. Calculate {R.RATIOS[key].en} using average balances (in %).",
                        res.value, "%", " → ".join(res.steps), abs_tol=0.05)
    return _num("s4-roe-generic", 4, 2, "roe", "Net income 1,200; equity 10,000 at the start and 11,000 at the end of the year. ROE on average equity (%)?",
                1200 / 10500 * 100, "%", "Average equity = 10,500 → ROE = 1,200 ÷ 10,500 = 11.43 %.", abs_tol=0.05)


@template("s4-dupont-interpret", 4, 3, "dupont")
def _(ctx, rng):
    return _mc("s4-dupont-int", 4, 3, "dupont", "A bank's ROE rose from 8 % to 11 % while its ROA stayed unchanged. What explains the increase?",
               "Higher financial leverage (more assets per unit of equity)", ["Higher net profit margin", "Lower cost/income ratio", "Higher dividend payout"], rng,
               "ROE = ROA × leverage. If ROA is flat, leverage must have risen — higher ROE but thinner capital buffer.")


@template("s4-dupont-calc", 4, 4, "dupont")
def _(ctx, rng):
    for y in reversed(_years(ctx.values)):
        d = R.dupont(ctx.values, y)
        if d:
            return _num(f"s4-dupont-{y}", 4, 4, "dupont",
                        f"{ctx.name} {y}: ROA (on average assets) = {d['roa']:.3f} % and financial leverage (average assets ÷ average equity) = {d['leverage']:.2f}×. Using DuPont, what is ROE (%)?",
                        d["roa"] * d["leverage"], "%", f"ROE = ROA × leverage = {d['roa']:.3f} % × {d['leverage']:.2f} = {d['roa'] * d['leverage']:.2f} %. This connects the income statement (net income) with the balance sheet (assets, equity).", abs_tol=0.1)
    return _num("s4-dupont-generic", 4, 4, "dupont", "ROA 0.6 %, leverage 18×. ROE (%)?", 10.8, "%", "0.6 % × 18 = 10.8 %.")


@template("s4-value", 4, 5, "roe_vs_cost_of_equity")
def _(ctx, rng):
    return _text("s4-value", 4, 5, "roe_vs_cost_of_equity",
                 f"Compare {ctx.name}'s latest ROE with a cost of equity of roughly 9–10 %. Is it creating value for shareholders? Name three levers management could pull to raise ROE — and the risk each lever brings.",
                 "Value is created when ROE exceeds the cost of equity (then P/B > 1 is justified). Levers: (1) higher margins/revenue (pricing, fee growth) — competitive risk; (2) cost cuts (lower cost/income) — execution and franchise risk; (3) more leverage or returning excess capital via buybacks — lower capital buffer, regulatory limits; also mix shift to capital-light businesses. Adjust ROE for one-offs before judging.")


# ---------------------------------------------------------------- Stage 5 — statements

WHERE_ITEMS = [
    ("details of goodwill impairment testing", "Notes to the financial statements"),
    ("the key audit matters", "Auditor's report"),
    ("dividends paid and share buybacks during the year", "Statement of changes in equity"),
    ("the reconciliation of net income to operating cash flow", "Cash flow statement"),
    ("unrealised gains and losses that bypass net income (OCI)", "Statement of comprehensive income"),
]
WHERE_OPTIONS = ["Notes to the financial statements", "Auditor's report", "Statement of changes in equity", "Cash flow statement", "Statement of comprehensive income"]


@template("s5-where", 5, 1, "annual_report_navigation")
def _(ctx, rng):
    item, correct = rng.choice(WHERE_ITEMS)
    wrong = [o for o in WHERE_OPTIONS if o != correct][:3]
    return _mc(f"s5-where-{item[:12]}", 5, 1, "annual_report_navigation", f"Where in the annual report do you find {item}?", correct, wrong, rng)


@template("s5-roll", 5, 2, "statement_links")
def _(ctx, rng):
    o = rng.choice([8000, 12000, 25000])
    ni = round(o * rng.choice([0.08, 0.1, 0.12]))
    div = round(ni * 0.5)
    bb = rng.choice([0, 200, 500])
    oci = rng.choice([-600, -150, 120, 300])
    c = o + ni - div - bb + oci
    return _num(f"s5-roll-{o}-{oci}", 5, 2, "statement_links",
                f"Opening equity {o:,}; net income {ni:,}; dividends paid {div:,}; share buybacks {bb:,}; other comprehensive income {oci:+,}. What is closing equity?",
                c, "", f"{o:,} + {ni:,} − {div:,} − {bb:,} {oci:+,} = {c:,}. Every movement appears in the statement of changes in equity.", abs_tol=0.5)


@template("s5-kam", 5, 3, "auditor_report")
def _(ctx, rng):
    focus = ctx.profile.get("audit_focus") or ["Valuation of insurance contract liabilities"]
    item = rng.choice(focus)
    return _mc(f"s5-kam-{sum(map(ord, item)) % 997}", 5, 3, "auditor_report",
               f"A key audit matter in {ctx.name}'s auditor's report is: '{item}'. What should it tell you as an analyst?",
               "The area involves significant judgement or estimation — read the related note, its assumptions and sensitivities",
               ["The auditor found an error that was not corrected", "The figure is guaranteed to be accurate", "The company will restate its accounts"], rng,
               "Key audit matters flag the highest-risk areas; they are not qualifications. A qualified opinion would be stated in the opinion paragraph.")


@template("s5-profile-l3", 5, 3, "one_off_items", "acquisition_effects")
def _(ctx, rng):
    return _profile_question(ctx, 5, 3, rng)


@template("s5-bank-cf", 5, 4, "cash_flow_banks")
def _(ctx, rng):
    if ctx.sector == "bank":
        return _mc("s5-bank-cf", 5, 4, "cash_flow_banks", "A bank reports positive net income but a large negative operating cash flow. Why is this usually NOT a red flag?",
                   "Operating cash flow of banks is dominated by changes in loans, deposits and trading balances, not by earnings quality",
                   ["Banks never collect their interest in cash", "Negative cash flow always means fraud", "Net income is not audited for banks"], rng,
                   "For banks, lending and deposit-taking are operating activities — growing the loan book 'consumes' operating cash.")
    return _mc("s5-ins-cf", 5, 4, "cash_flow_banks", "A life insurer's operating cash flow swings between strongly positive and negative while net income is stable. Most likely reason?",
               "Investment purchases/sales and policyholder flows (premiums, surrenders) are partly classified as operating cash flows",
               ["Net income is wrong", "The insurer stopped paying claims", "Depreciation changed"], rng)


@template("s5-profile-l4", 5, 4, "linking_statements")
def _(ctx, rng):
    return _profile_question(ctx, 5, 4, rng)


@template("s5-investigate", 5, 5, "operational_vs_accounting")
def _(ctx, rng):
    changes = C.unusual_changes(ctx.values)
    if changes:
        ch = changes[0]
        evs = [e for e in ctx.profile.get("events", []) if e.get("year") == ch["year"] and (not e.get("metrics") or ch["metric"] in e["metrics"])]
        model = " ".join(f"{e['title']}: {e['detail']} Verify in: {e['where_to_verify']}" for e in evs) or \
            "Start from the management report, then the relevant note; check whether the change is due to volumes/prices (operational), a change in standards or estimates (accounting), or a non-recurring event; verify in the statement of changes in equity, the segment note and the auditor's key audit matters."
        change_txt = f"{ch['change']:+.1f} {ch['unit']}" if np.isfinite(ch.get("change", np.nan)) else "a sign change"
        return _text(f"s5-investigate-{ch['metric']}-{ch['year']}", 5, 5, "operational_vs_accounting",
                     f"{ctx.name}'s {M.short(ch['metric'])} moved {change_txt} in {ch['year']}. Is the change operational or accounting-driven, recurring or one-off — and exactly where in the annual report would you verify it?", model)
    return _text("s5-investigate-generic", 5, 5, "operational_vs_accounting",
                 "Pick the largest change in your dataset. Operational or accounting-driven? Recurring or one-off? Where would you verify it?",
                 "Name the driver, classify it, and cite the specific note or statement that proves it.")


# ---------------------------------------------------------------- Stage 6 — quality of earnings


@template("s6-nonrec", 6, 1, "one_off_items")
def _(ctx, rng):
    return _mc("s6-nonrec", 6, 1, "one_off_items", "Which item is most likely non-recurring?", "Gain on the sale of a subsidiary",
               ["Net interest income", "Recurring asset-management fees", "Personnel expenses"], rng,
               "Disposal gains, negative goodwill, litigation settlements and restructuring charges are typical one-offs.")


@template("s6-underlying", 6, 2, "underlying_earnings")
def _(ctx, rng):
    y = _latest_with(ctx.values, ["net_income"])
    ni = _val(ctx.values, "net_income", y) if y else 1000.0
    ni = ni if ni and ni > 0 else 1000.0
    gain = round(abs(ni) * rng.choice([0.1, 0.15, 0.2]))
    tax = rng.choice([0.15, 0.2, 0.25])
    ans = ni - gain * (1 - tax)
    return _num(f"s6-underlying-{gain}", 6, 2, "underlying_earnings",
                f"Suppose {ctx.name}'s reported net income of {_money(ni, ctx.currency)} includes a one-off pre-tax gain of {_money(gain, ctx.currency)}, taxed at {tax * 100:.0f} %. What is underlying net income ({ctx.currency} m)?",
                ans, f"{ctx.currency} m", f"Underlying = {ni:,.0f} − {gain:,.0f} × (1 − {tax:.2f}) = {ans:,.0f}. Remove one-offs after tax.", rel_tol=0.005, abs_tol=1)


@template("s6-reserves", 6, 3, "reserves")
def _(ctx, rng):
    if ctx.sector == "insurer":
        return _mc("s6-reserves-ins", 6, 3, "reserves", "An insurer's profit rises mainly because it released reserves set aside for prior-year claims. How should you view that profit?",
                   "Lower quality — it depends on past estimates being too cautious and cannot be relied on to recur",
                   ["Higher quality — it is cash income", "Neutral — reserves have no effect on profit", "It means the insurer wrote more business"], rng,
                   "Prior-year reserve development changes earnings without new business; repeated releases can also signal earlier over-reserving used for smoothing.")
    return _mc("s6-reserves-bank", 6, 3, "reserves", "A bank's profit rises because it released credit-loss allowances (a negative credit loss expense). How should you view that profit?",
               "Lower quality — the release cannot recur indefinitely and depends on management's model assumptions",
               ["Higher quality — releases are recurring", "Neutral — allowances never affect profit", "It means loans grew faster"], rng)


@template("s6-accruals", 6, 4, "accruals")
def _(ctx, rng):
    for y in reversed(_years(ctx.values)):
        ni, ocf = _val(ctx.values, "net_income", y), _val(ctx.values, "operating_cash_flow", y)
        a0, a1 = _val(ctx.values, "total_assets", y - 1), _val(ctx.values, "total_assets", y)
        if None not in (ni, ocf, a0, a1):
            ans = (ni - ocf) / ((a0 + a1) / 2) * 100
            note = " For a bank this number says little — OCF is driven by balance-sheet flows." if ctx.sector == "bank" else ""
            return _num(f"s6-accr-{y}", 6, 4, "accruals",
                        f"{ctx.name} {y}: net income {_money(ni, ctx.currency)}, operating cash flow {_money(ocf, ctx.currency)}, total assets {_money(a0, ctx.currency)} (opening) and {_money(a1, ctx.currency)} (closing). Calculate the cash-flow accrual ratio (%).",
                        ans, "%", f"(NI − OCF) ÷ average assets = ({ni:,.0f} − {ocf:,.0f}) ÷ {(a0 + a1) / 2:,.0f} = {ans:.3f} %.{note}", abs_tol=0.02)
    return _num("s6-accr-generic", 6, 4, "accruals", "NI 500, OCF 200, average assets 10,000. Accrual ratio (%)?", 3.0, "%", "(500 − 200) ÷ 10,000 = 3 %.")


@template("s6-judge", 6, 5, "quality_earnings")
def _(ctx, rng):
    model = ("For a bank look at: share of recurring fees vs trading, credit-loss charges vs through-the-cycle levels, one-offs (negative goodwill, litigation, restructuring), tax effects (DTA recognition), and whether profit converts into CET1 capital and distributions."
             if ctx.sector == "bank" else
             "For an insurer look at: reserve releases, catastrophe losses vs budget, realised investment gains, IFRS 17 effects (CSM release, assumption changes), tax effects, and whether profit converts into solvency capital and cash remittances/dividends.")
    return _text("s6-judge", 6, 5, "quality_earnings", f"Rate the quality of {ctx.name}'s latest earnings (high / medium / low) and justify it with two pieces of evidence from your analysis.", model)


# ---------------------------------------------------------------- Stage 7 — risk


@template("s7-capital", 7, 1, "regulatory_capital")
def _(ctx, rng):
    if ctx.sector == "bank":
        return _mc("s7-cet1", 7, 1, "regulatory_capital", "What does a bank's CET1 ratio primarily protect against?", "Unexpected losses that would otherwise make the bank insolvent",
                   ["Daily cash outflows (liquidity)", "Rising cost/income ratios", "Currency translation differences"], rng,
                   "CET1 is loss-absorbing equity relative to risk-weighted assets — a solvency measure. Liquidity is covered by LCR/NSFR.")
    return _mc("s7-solv", 7, 1, "regulatory_capital", "An insurer reports a solvency ratio of 180 %. What does it mean?", "Available capital is 1.8× the regulatory required capital",
               ["The insurer can pay 180 % of its claims", "Assets are 180 % of liabilities", "Profit is 180 % of premiums"], rng)


@template("s7-shock", 7, 2, "capital_shock")
def _(ctx, rng):
    if ctx.sector == "bank":
        y = _latest_with(ctx.values, ["cet1_capital", "rwa"])
        if y is not None:
            c1, rwa = _val(ctx.values, "cet1_capital", y), _val(ctx.values, "rwa", y)
            loss = round(c1 * rng.choice([0.1, 0.15]))
        else:
            c1, rwa, loss = 1500.0, 10000.0, 300.0
        ans = (c1 - loss) / rwa * 100
        return _num(f"s7-shock-{int(loss)}", 7, 2, "capital_shock",
                    f"CET1 capital is {c1:,.0f} and RWA {rwa:,.0f} ({ctx.currency} m). An after-tax loss of {loss:,.0f} hits CET1 (RWA unchanged). What is the new CET1 ratio (%)?",
                    ans, "%", f"({c1:,.0f} − {loss:,.0f}) ÷ {rwa:,.0f} = {ans:.2f} % (before: {c1 / rwa * 100:.2f} %).", abs_tol=0.05)
    avail, req = rng.choice([(18000, 9000), (5000, 2500), (900, 450)])
    shock = round(avail * 0.15)
    ans = (avail - shock) / req * 100
    return _num(f"s7-shock-ins-{avail}", 7, 2, "capital_shock",
                f"An insurer has available capital of {avail:,} and required capital of {req:,}. A market shock reduces available capital by {shock:,} (required unchanged). New solvency ratio (%)?",
                ans, "%", f"({avail:,} − {shock:,}) ÷ {req:,} = {ans:.1f} % (before: {avail / req * 100:.0f} %).")


@template("s7-rates", 7, 3, "risk_interest")
def _(ctx, rng):
    if ctx.sector == "bank":
        return _mc("s7-rates-bank", 7, 3, "risk_interest", "A deposit-rich Swiss bank sees the SNB cut its policy rate to 0 %. What is the most likely effect?",
                   "Net interest income falls because deposit margins shrink (deposit rates cannot go much below zero)",
                   ["Net interest income rises because funding is cheaper", "Fee income falls to zero", "RWA double"], rng)
    return _mc("s7-rates-ins", 7, 3, "risk_interest", "A life insurer has long-dated guaranteed savings products. Which interest-rate scenario hurts it most?",
               "Persistently low or falling rates — reinvestment yields fall below the guaranteed rates",
               ["Rising rates — it can reinvest at higher yields", "Rates do not matter for life insurers", "Only a flat yield curve at 5 %"], rng)


@template("s7-market", 7, 4, "risk_market")
def _(ctx, rng):
    return _mc("s7-market", 7, 4, "risk_market", f"Equity markets fall 15 %. Through which statements does this reach {ctx.name}?",
               "Income statement (lower asset-based fees / investment results) and balance sheet / capital (lower asset values, solvency or CET1)",
               ["Only the cash flow statement", "Only the notes", "Nowhere — market risk is borne entirely by clients"], rng,
               "Market risk reaches earnings via fees and investment income and reaches capital via valuations — connect both statements.")


@template("s7-prioritise", 7, 5, "risk_prioritisation")
def _(ctx, rng):
    return _text("s7-prioritise", 7, 5, "risk_prioritisation",
                 f"Take your top three risks for {ctx.name}. For each, say whether it affects value mainly through future earnings (ROE), through capital (book value, payouts) or through the cost of equity — and what early-warning indicator you would track.",
                 "E.g. regulatory capital rules → capital/ROE (track draft rules, CET1 target); market downturn → earnings via fees (track AuM, net new money); catastrophe/reserve risk → earnings and capital (track nat cat losses vs budget, prior-year development); interest rates → NII or spread (track rate sensitivity disclosures). Risks that raise uncertainty also raise the cost of equity.")


# ---------------------------------------------------------------- Stage 8 — peers


@template("s8-ratios", 8, 1, "peers")
def _(ctx, rng):
    return _mc("s8-ratios", 8, 1, "peers", "Why compare UBS and LLB on ratios (ROE, cost/income, CET1 ratio) rather than on absolute figures like net income?",
               "They differ hugely in size and report in different currencies (USD vs CHF) — ratios normalise for scale and currency",
               ["Absolute figures are not audited", "Ratios are always higher", "Net income is not comparable between any two banks"], rng)


@template("s8-gap", 8, 2, "roe")
def _(ctx, rng):
    if ctx.peer_values is not None and ctx.peer_profile is not None:
        rd = R.RATIOS["roe"]
        for y in reversed(_years(ctx.values)):
            a = R.compute(rd, ctx.values, y)
            b = R.compute(rd, ctx.peer_values, y) if y in ctx.peer_values.columns else None
            if a.value is not None and b is not None and b.value is not None:
                ans = a.value - b.value
                return _num(f"s8-gap-{y}", 8, 2, "roe",
                            f"{y}: {ctx.name} net income {_money(a.required[0].value, ctx.currency)}, average equity {_money((a.required[1].value + a.required[2].value) / 2, ctx.currency)}; "
                            f"{ctx.peer_profile['short_name']} net income {b.required[0].value:,.0f}, average equity {(b.required[1].value + b.required[2].value) / 2:,.0f} ({ctx.peer_profile['currency']} m). "
                            f"By how many percentage points does {ctx.name}'s ROE exceed the peer's? (Negative if lower.)",
                            ans, "pp", f"{a.value:.2f} % − {b.value:.2f} % = {ans:+.2f} pp. Currencies cancel out in a ratio.", abs_tol=0.1)
    return _num("s8-gap-generic", 8, 2, "roe", "Bank A: NI 900, average equity 7,500. Bank B: NI 160, average equity 2,200. ROE difference A − B (pp)?",
                900 / 7500 * 100 - 160 / 2200 * 100, "pp", "12.00 % − 7.27 % = 4.73 pp.", abs_tol=0.1)


@template("s8-pbroe", 8, 3, "justified_pb")
def _(ctx, rng):
    return _mc("s8-pbroe", 8, 3, "justified_pb", "Bank A: ROE 14 %, P/B 1.8. Bank B: ROE 6 %, P/B 0.7. Cost of equity ≈ 10 % for both. Is this pattern consistent?",
               "Yes — the market pays above book only for banks expected to earn more than their cost of equity",
               ["No — P/B should be the same for all banks", "No — the lower-ROE bank should trade at a higher P/B", "It is random"], rng)


@template("s8-capital", 8, 4, "leverage")
def _(ctx, rng):
    return _mc("s8-capital", 8, 4, "leverage", "Your peer shows a higher ROE but a lower CET1 ratio and higher leverage. What must you check before concluding it is 'better'?",
               "Whether its higher ROE comes from leverage (less capital per unit of risk) rather than better profitability — compare ROA and risk-adjusted returns",
               ["Nothing — higher ROE is always better", "Only the dividend yield", "Whether it has more employees"], rng)


@template("s8-select", 8, 5, "peer_selection")
def _(ctx, rng):
    return _text("s8-select", 8, 5, "peer_selection", "Is the peer you selected truly comparable? Name two differences (business model, accounting, currency, size, regulation) that limit the comparison, and how you adjusted for them.",
                 "E.g. UBS vs LLB: global vs regional, USD vs CHF, investment bank exposure, TBTF regime vs EEA rules. Swiss Life vs Swiss Re: life/pensions vs reinsurance, CHF vs USD, different risk drivers (rates vs catastrophes). Compare ratios, index trends to 100, compare within the same accounting basis and acknowledge the residual differences.")


# ---------------------------------------------------------------- Stage 9 — valuation


@template("s9-method", 9, 1, "valuation_methods")
def _(ctx, rng):
    return _mc("s9-method", 9, 1, "valuation_methods", "Which valuation approach is generally LEAST appropriate for a bank?",
               "A free-cash-flow-to-the-firm (FCFF) DCF", ["Price-to-book vs ROE", "A dividend discount model", "A residual income model"], rng,
               "For banks debt is raw material (deposits), not financing; operating cash flow is not meaningful — so FCFF breaks down.")


@template("s9-profile", 9, 1, "valuation_methods")
def _(ctx, rng):
    for lvl in (3, 1, 2):
        q = _profile_question(ctx, 9, lvl, rng)
        if q:
            q.level = 1
            return q
    return None


@template("s9-jpb", 9, 2, "justified_pb")
def _(ctx, rng):
    roe, r, g = rng.choice([(0.12, 0.09, 0.02), (0.08, 0.10, 0.02), (0.15, 0.10, 0.03), (0.10, 0.085, 0.015)])
    ans = V.justified_pb(roe, r, g)
    return _num(f"s9-jpb-{roe}-{r}", 9, 2, "justified_pb", f"Sustainable ROE {roe * 100:.1f} %, cost of equity {r * 100:.1f} %, long-run growth {g * 100:.1f} %. Justified P/B (×)?",
                ans, "×", f"(ROE − g) ÷ (r − g) = ({roe:.3f} − {g:.3f}) ÷ ({r:.3f} − {g:.3f}) = {ans:.2f}×.", abs_tol=0.02)


@template("s9-pb-below", 9, 3, "justified_pb")
def _(ctx, rng):
    return _mc("s9-pb-below", 9, 3, "justified_pb", "A bank trades at 0.7× book value. What is the market implicitly saying?",
               "It expects the bank to earn an ROE below its cost of equity (or doubts the book value)",
               ["The bank is certainly cheap and will rise", "The bank has no debt", "The dividend yield must be zero"], rng,
               "Implied ROE = g + P/B × (r − g). P/B < 1 ⇒ implied ROE < r. Whether that is too pessimistic is your analysis — not a buy signal.")


@template("s9-ddm", 9, 4, "ddm")
def _(ctx, rng):
    y = _latest_with(ctx.values, ["dps"])
    d0 = _val(ctx.values, "dps", y) if y else None
    d0 = d0 if d0 and d0 > 0 else 2.5
    r, g = rng.choice([(0.08, 0.03), (0.09, 0.025), (0.075, 0.02)])
    ans = V.gordon_ddm(d0, r, g)
    return _num(f"s9-ddm-{r}-{g}", 9, 4, "ddm", f"Last dividend D₀ = {ctx.currency} {d0:.2f}. Dividends grow {g * 100:.1f} % forever; cost of equity {r * 100:.1f} %. Gordon growth value per share?",
                ans, ctx.currency, f"V₀ = D₀ × (1 + g) ÷ (r − g) = {d0:.2f} × {1 + g:.3f} ÷ {r - g:.3f} = {ans:.2f}. Note how sensitive it is to r − g.", rel_tol=0.01)


@template("s9-why", 9, 5, "valuation_methods")
def _(ctx, rng):
    return _text("s9-why", 9, 5, "valuation_methods", f"Why might a P/B–ROE or dividend/capital-generation approach be more informative than a traditional FCFF DCF for {ctx.name}?",
                 "Because for financials the balance sheet is the business: deposits/insurance liabilities are operating items, not financing; cash flow statements do not measure distributable cash; regulators cap distributions via capital requirements. Value therefore depends on sustainable ROE vs cost of equity (P/B) and on how much capital can be distributed after meeting capital targets (DDM / excess capital). DCF only works if you redefine FCFE as distributable capital.")


# ---------------------------------------------------------------- Stage 10 — thesis


@template("s10-breaker", 10, 1, "thesis")
def _(ctx, rng):
    return _mc("s10-breaker", 10, 1, "thesis", "What is a 'thesis breaker'?", "A specific, observable development that would prove your investment thesis wrong",
               ["The target price", "A broker's recommendation", "The last dividend payment"], rng)


@template("s10-ev", 10, 2, "scenario_analysis")
def _(ctx, rng):
    bear, base, bull = rng.choice([(60, 90, 120), (20, 30, 42), (400, 560, 700)])
    p = rng.choice([(0.25, 0.5, 0.25), (0.3, 0.5, 0.2), (0.2, 0.6, 0.2)])
    ans = bear * p[0] + base * p[1] + bull * p[2]
    return _num(f"s10-ev-{bear}-{p[0]}", 10, 2, "scenario_analysis", f"Bear {bear} (probability {p[0]:.0%}), base {base} ({p[1]:.0%}), bull {bull} ({p[2]:.0%}). Probability-weighted value?",
                ans, "", f"{bear}×{p[0]} + {base}×{p[1]} + {bull}×{p[2]} = {ans:.1f}.", abs_tol=0.1)


@template("s10-portfolio", 10, 3, "portfolio")
def _(ctx, rng):
    return _mc("s10-portfolio", 10, 3, "portfolio", "Before allocating money to any single stock, which consideration is about YOU rather than the company?",
               "Your risk tolerance, time horizon, existing exposures and diversification", ["The CET1 ratio", "The combined ratio", "The auditor's opinion"], rng)


@template("s10-growth", 10, 4, "sustainable_growth")
def _(ctx, rng):
    roe, payout = rng.choice([(0.12, 0.6), (0.10, 0.5), (0.15, 0.7)])
    ans = V.sustainable_growth(roe, payout) * 100
    return _num(f"s10-g-{roe}-{payout}", 10, 4, "sustainable_growth", f"ROE {roe * 100:.0f} %, payout ratio {payout * 100:.0f} %. Sustainable growth rate (%)?",
                ans, "%", f"g = (1 − payout) × ROE = {1 - payout:.2f} × {roe * 100:.0f} % = {ans:.1f} %. It links the income statement (ROE), dividend policy and balance-sheet growth.")


@template("s10-final", 10, 5, "thesis")
def _(ctx, rng):
    return _text("s10-final", 10, 5, "thesis", f"Write the one sentence that would make you abandon your thesis on {ctx.name}, including the number and the time frame.",
                 "A good thesis breaker is specific and measurable, e.g. 'If the CET1 ratio target rises above X % and buybacks stop in 2026' or 'If net new money is negative for two consecutive years' or 'If prior-year reserve strengthening recurs in 2026'.")


# --------------------------------------------------------------------------- grading


def grade(q: Question, response) -> bool | None:
    """True/False for MC and numeric; None for free text (self-assessed)."""
    if q.kind == "mc":
        return response is not None and int(response) == int(q.answer)
    if q.kind == "numeric":
        if response is None:
            return False
        try:
            x = float(response)
        except (TypeError, ValueError):
            return False
        return C.is_close(x, float(q.answer), rel=q.rel_tol, abs_tol=q.abs_tol)
    return None


# --------------------------------------------------------------------------- spaced repetition

BOX_GAP_QUIZZES = {1: 1, 2: 2, 3: 4, 4: 8, 5: 16}
BOX_GAP_DAYS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 21}


def record(learner: dict, concept: str, outcome: str) -> None:
    """Update the concept tracker. outcome ∈ {"correct", "partial", "wrong"}."""
    now = datetime.now(timezone.utc)
    c = learner.setdefault("concepts", {}).setdefault(concept, {"box": 1, "attempts": 0, "correct": 0, "wrong": 0, "partial": 0})
    c["attempts"] += 1
    if outcome == "correct":
        c["correct"] += 1
        c["box"] = min(5, c["box"] + 1)
    elif outcome == "partial":
        c["partial"] = c.get("partial", 0) + 1
    else:
        c["wrong"] += 1
        c["box"] = 1
    counter = learner.get("quiz_counter", 0)
    c["due_quiz"] = counter + BOX_GAP_QUIZZES[c["box"]]
    c["due_date"] = (now + timedelta(days=BOX_GAP_DAYS[c["box"]])).isoformat(timespec="seconds")
    c["last_seen"] = now.isoformat(timespec="seconds")


def due_concepts(learner: dict, limit: int | None = None) -> list[str]:
    """Concepts the learner got wrong before and that are due for review (weakest first)."""
    now = datetime.now(timezone.utc)
    counter = learner.get("quiz_counter", 0)
    due = []
    for concept, c in learner.get("concepts", {}).items():
        if c.get("wrong", 0) + c.get("partial", 0) == 0 or c.get("box", 1) >= 4:
            continue
        by_quiz = counter >= c.get("due_quiz", 0)
        try:
            # calendar-based review only for longer intervals; box 1 is driven by the next quiz
            by_date = BOX_GAP_DAYS[c.get("box", 1)] > 0 and now >= datetime.fromisoformat(c.get("due_date"))
        except (TypeError, ValueError, KeyError):
            by_date = False
        if by_quiz or by_date:
            due.append((c.get("box", 1), -(c.get("wrong", 0) - c.get("correct", 0)), concept))
    due.sort()
    out = [d[2] for d in due]
    return out[:limit] if limit else out


def concept_table(learner: dict) -> pd.DataFrame:
    rows = []
    for concept, c in learner.get("concepts", {}).items():
        attempts = c.get("attempts", 0)
        acc = c.get("correct", 0) / attempts * 100 if attempts else np.nan
        status = "Mastered" if c.get("box", 1) >= 4 else ("Needs review" if c.get("wrong", 0) + c.get("partial", 0) else "Learning")
        rows.append({"Concept": concept_label(concept), "Attempts": attempts, "Correct": c.get("correct", 0), "Wrong": c.get("wrong", 0),
                     "Accuracy %": acc, "Box (1–5)": c.get("box", 1), "Status": status, "_key": concept})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["Box (1–5)", "Wrong"], ascending=[True, False]).reset_index(drop=True)


# --------------------------------------------------------------------------- quiz builder


def templates_for_concept(concept: str, max_stage: int | None = None) -> list[Template]:
    return [t for t in TEMPLATES if concept in t.concepts and (max_stage is None or t.stage <= max_stage)]


def build_question(t: Template, ctx: QuizContext, rng: random.Random) -> Question | None:
    try:
        return t.build(ctx, rng)
    except (KeyError, ValueError, TypeError, ZeroDivisionError, IndexError):
        return None


def build_quiz(stage: int, ctx: QuizContext, learner: dict, seed: int | None = None, n_review: int = 2) -> list[Question]:
    """Five questions, levels 1→5. Due review concepts replace the easiest levels."""
    rng = random.Random(seed)
    questions: dict[int, Question] = {}
    for level in range(1, 6):
        candidates = [t for t in TEMPLATES if t.stage == stage and t.level == level]
        rng.shuffle(candidates)
        # prefer company-specific profile questions when available
        candidates.sort(key=lambda t: 0 if "profile" in t.id else 1)
        for t in candidates:
            q = build_question(t, ctx, rng)
            if q is not None:
                questions[level] = q
                break
    stage_concepts = {q.concept for q in questions.values()}
    review_slots = [lvl for lvl in (1, 2) if lvl in questions][:n_review]
    for concept in due_concepts(learner):
        if not review_slots:
            break
        if concept in stage_concepts:
            continue
        for t in sorted(templates_for_concept(concept), key=lambda t: t.level):
            q = build_question(t, ctx, rng)
            if q is not None:
                q.review = True
                questions[review_slots.pop(0)] = q
                stage_concepts.add(concept)
                break
    return [questions[k] for k in sorted(questions)]


def build_review(ctx: QuizContext, learner: dict, n: int = 5, seed: int | None = None, max_stage: int | None = None) -> list[Question]:
    """A review session made only of due/weak concepts (falls back to the weakest seen concepts)."""
    rng = random.Random(seed)
    concepts = due_concepts(learner)
    if len(concepts) < n:
        table = concept_table(learner)
        if not table.empty:
            for key in table["_key"]:
                if key not in concepts:
                    concepts.append(key)
    out = []
    for concept in concepts:
        if len(out) >= n:
            break
        ts = templates_for_concept(concept, max_stage)
        rng.shuffle(ts)
        for t in ts:
            q = build_question(t, ctx, rng)
            if q is not None:
                q.review = True
                out.append(q)
                break
    return out
