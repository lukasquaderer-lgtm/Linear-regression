"""Stage registry, gating and feedback helpers shared by all stages."""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import storage


@dataclass(frozen=True)
class Stage:
    number: int
    key: str
    en: str
    de: str
    icon: str
    goal: str

    def title(self) -> str:
        return f"Stage {self.number} — {self.en}"


STAGES: list[Stage] = [
    Stage(1, "business", "Understand the Business", "Geschäftsmodell verstehen", ":material/storefront:", "Explain what the company does and how it makes money — in your own words."),
    Stage(2, "data", "Collect Financial Data", "Finanzdaten erfassen", ":material/table_view:", "Build and verify a clean 5-year dataset from the annual reports."),
    Stage(3, "trends", "Historical Trend Analysis", "Historische Trendanalyse", ":material/trending_up:", "Calculate growth, judge each trend and explain why it happened."),
    Stage(4, "ratios", "Ratio Analysis", "Kennzahlenanalyse", ":material/percent:", "Calculate the key ratios yourself and interpret them."),
    Stage(5, "statements", "Financial Statement Investigation", "Analyse der Jahresrechnung", ":material/find_in_page:", "Investigate unusual changes in the annual report — not just headline numbers."),
    Stage(6, "quality", "Quality of Earnings", "Qualität der Gewinne", ":material/fact_check:", "Separate recurring, cash-backed earnings from one-offs and accounting effects."),
    Stage(7, "risk", "Risk Analysis", "Risikoanalyse", ":material/shield:", "Map the risks and identify the three that matter most for value."),
    Stage(8, "peers", "Peer Comparison", "Peer-Vergleich", ":material/compare_arrows:", "Compare with a peer on the metrics that are actually comparable."),
    Stage(9, "valuation", "Valuation", "Bewertung", ":material/calculate:", "Value the equity with methods that fit a financial institution."),
    Stage(10, "thesis", "Investment Thesis", "Investment-These", ":material/flag:", "Pull everything together into a thesis with scenarios — no buy/sell verdict."),
]

STAGE_BY_NUMBER = {s.number: s for s in STAGES}


def stage_complete(progress: dict, number: int) -> bool:
    return bool(progress.get("stages", {}).get(str(number), {}).get("completed"))


def quiz_done(progress: dict, number: int) -> bool:
    state = progress.get("stages", {}).get(str(number), {})
    quiz = state.get("quiz")
    return bool(state.get("quiz_completed_once") or (quiz and quiz.get("finished")))


def stage_passed(progress: dict, number: int, training_mode: bool) -> bool:
    """A stage is passed when its tasks are complete (and its quiz, in training mode)."""
    if not stage_complete(progress, number):
        return False
    return quiz_done(progress, number) if training_mode else True


def is_unlocked(progress: dict, number: int, training_mode: bool, unlock_all: bool = False) -> bool:
    if unlock_all or number == 1:
        return True
    return stage_passed(progress, number - 1, training_mode)


def current_stage(progress: dict, training_mode: bool) -> int:
    for s in STAGES:
        if not stage_passed(progress, s.number, training_mode):
            return s.number
    return STAGES[-1].number


def overall_progress(progress: dict, training_mode: bool) -> float:
    return sum(stage_passed(progress, s.number, training_mode) for s in STAGES) / len(STAGES)


def mark_complete(progress: dict, number: int) -> None:
    state = storage.stage_state(progress, number)
    state["completed"] = True
    state["completed_at"] = storage.now_iso()
    storage.save_progress(progress)


# --------------------------------------------------------------------------- text feedback


SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9\"“(])")
ABBREVIATIONS = ("e.g.", "i.e.", "z.B.", "z. B.", "d.h.", "bzw.", "inkl.", "ca.", "Inc.", "Ltd.", "AG.", "vs.", "etc.", "approx.", "Nr.", "u.a.")


def sentence_count(text: str) -> int:
    t = (text or "").strip()
    if not t:
        return 0
    for abbr in ABBREVIATIONS:
        t = t.replace(abbr, abbr.replace(".", ""))
    parts = [p for p in SENTENCE_SPLIT.split(t) if len(p.split()) >= 3]
    return len(parts)


def word_count(text: str) -> int:
    return len((text or "").split())


def _matches(text: str, keyword: str) -> bool:
    kw = keyword.strip().lower()
    if not kw:
        return False
    if len(kw) <= 3 and re.fullmatch(r"[a-z0-9&]+", kw):
        # short tokens (ib, us, fee, nii) need word boundaries; allow a plural ending ("fees")
        return re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?:s|es)?(?![a-z0-9])", text) is not None
    return kw in text  # longer stems match inside words (zins → Zinsen, Zinserfolg)


def keyword_coverage(text: str, key_points: list[dict]) -> tuple[list[str], list[str]]:
    """Which reference key points does the learner's text touch on (EN/DE keywords)?"""
    low = " " + (text or "").lower() + " "
    covered, missed = [], []
    for kp in key_points:
        if any(_matches(low, kw) for kw in kp.get("keywords", [])):
            covered.append(kp["point"])
        else:
            missed.append(kp["point"])
    return covered, missed


# Generic "did you consider…?" prompts used when explaining a change (Stages 3 and 5).
EXPLANATION_DRIVERS = [
    {"point": "Interest rates / monetary policy", "keywords": ["interest", "zins", "rate", "snb", "fed", "ecb", "ezb", "monetary"]},
    {"point": "Acquisition, disposal or change in scope", "keywords": ["acqui", "übernahme", "uebernahme", "merger", "fusion", "disposal", "verkauf", "divest", "scope", "konsolidier", "credit suisse"]},
    {"point": "Accounting change or restatement", "keywords": ["ifrs", "gaap", "accounting", "rechnungslegung", "restat", "standard", "oci"]},
    {"point": "One-off item (gain, loss, provision, impairment)", "keywords": ["one-off", "one off", "einmal", "non-recurring", "impair", "wertminder", "provision", "rückstell", "rueckstell", "goodwill", "litigation", "restructur"]},
    {"point": "Markets / client assets / volumes", "keywords": ["market", "markt", "asset", "volume", "volumen", "client", "kunde", "inflow", "zufluss", "aum"]},
    {"point": "Costs and efficiency", "keywords": ["cost", "kosten", "expense", "aufwand", "efficien", "effizien", "headcount", "personal"]},
    {"point": "Capital actions (buybacks, dividends)", "keywords": ["buyback", "rückkauf", "rueckkauf", "dividend", "share count", "aktien"]},
    {"point": "Currency effects", "keywords": ["fx", "currency", "währung", "waehrung", "franc", "franken", "dollar", "euro", "translation"]},
    {"point": "Catastrophes, claims or reserves (insurers)", "keywords": ["catastroph", "katastroph", "claims", "schäden", "schaeden", "reserve", "hurricane", "covid", "pandemic"]},
]


def events_for(profile: dict, metric: str | None = None, year: int | None = None) -> list[dict]:
    out = []
    for ev in profile.get("events", []):
        if year is not None and ev.get("year") != year:
            continue
        if metric is not None and ev.get("metrics") and metric not in ev["metrics"]:
            continue
        out.append(ev)
    return out


NATURE_LABEL = {
    "one-off": "One-off",
    "accounting": "Accounting-driven",
    "operational": "Operational",
    "structural": "Structural",
    "transitional": "Transitional",
    "regulatory": "Regulatory",
    "acquisition": "Acquisition",
    "capital": "Capital management",
}
