"""Core calculations: growth, CAGR, averages, trend classification, unusual changes.

All functions are pure (pandas/NumPy in, numbers out) so they are easy to test.
Growth rates are returned in percent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import metrics as M


def yoy_growth(s: pd.Series) -> pd.Series:
    """Year-over-year growth in % (x_t / x_{t-1} − 1).

    Growth from a zero or negative base is not meaningful and returns NaN.
    """
    s = s.astype(float)
    prev = s.shift(1)
    out = (s / prev - 1.0) * 100.0
    out[(prev <= 0) | prev.isna() | s.isna()] = np.nan
    return out


def yoy_change(s: pd.Series) -> pd.Series:
    """Absolute year-over-year change (used for ratios: percentage points)."""
    return s.astype(float).diff()


def cagr(start: float | None, end: float | None, years: float) -> float | None:
    """Compound annual growth rate in %: (end / start)^(1/years) − 1.

    Undefined (None) when either value is missing or non-positive, or years ≤ 0.
    """
    if start is None or end is None or years <= 0:
        return None
    if not np.isfinite(start) or not np.isfinite(end) or start <= 0 or end <= 0:
        return None
    return ((end / start) ** (1.0 / years) - 1.0) * 100.0


def series_cagr(s: pd.Series) -> tuple[float | None, int | None, int | None]:
    """CAGR between the first and last available values. Returns (cagr, first_year, last_year)."""
    clean = s.dropna()
    if len(clean) < 2:
        return None, None, None
    y0, y1 = int(clean.index[0]), int(clean.index[-1])
    return cagr(float(clean.iloc[0]), float(clean.iloc[-1]), y1 - y0), y0, y1


def average_balance(s: pd.Series) -> pd.Series:
    """Average of opening and closing balance: (x_{t-1} + x_t) / 2."""
    s = s.astype(float)
    return (s + s.shift(1)) / 2.0


def is_close(user: float | None, correct: float | None, rel: float = 0.02, abs_tol: float = 0.15) -> bool:
    """Tolerant comparison for learner answers (rounding differences are fine)."""
    if user is None or correct is None:
        return False
    if not (np.isfinite(user) and np.isfinite(correct)):
        return False
    return abs(user - correct) <= max(abs_tol, rel * abs(correct))


@dataclass
class TrendVerdict:
    label: str  # improving | deteriorating | stable | volatile | growing | shrinking | insufficient data
    direction: str  # up | down | flat | mixed
    reasons: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def classify_trend(s: pd.Series, metric_key: str) -> TrendVerdict:
    """Rule-based trend classification used to give feedback *after* the learner's own verdict.

    * slope from an OLS line through the data (as % of the average level per year,
      or percentage points per year for ratio metrics)
    * "volatile" when the series changes direction repeatedly with large swings
    * judgement (improving/deteriorating) depends on whether higher is better
    """
    m = M.get(metric_key)
    clean = s.dropna().astype(float)
    if len(clean) < 3:
        return TrendVerdict("insufficient data", "flat", ["Fewer than three data points — no reliable trend."])
    x = np.array([int(i) for i in clean.index], dtype=float)
    y = clean.to_numpy()
    slope = float(np.polyfit(x - x.mean(), y, 1)[0])
    level = float(np.mean(np.abs(y))) or 1.0
    is_ratio = m is not None and m.unit == "pct"
    slope_norm = slope if is_ratio else slope / level * 100.0
    flat_band = 0.5 if is_ratio else 2.0  # pp per year, or % of level per year

    diffs = np.diff(y)
    signs = np.sign(diffs[np.abs(diffs) > (0.1 if is_ratio else 0.005 * level)])
    reversals = int(np.sum(signs[1:] != signs[:-1])) if len(signs) > 1 else 0
    cv = float(np.std(y) / level)
    swing = float(np.max(np.abs(diffs)) / level) if not is_ratio else float(np.max(np.abs(diffs)))
    unit = "pp per year" if is_ratio else "% of the average level per year"
    stats = {"slope": slope_norm, "reversals": reversals, "cv": cv, "unit": unit}
    first_last = (y[-1] - y[0]) if is_ratio else (y[-1] / y[0] - 1) * 100 if y[0] > 0 else np.nan
    stats["first_last"] = first_last

    reasons = [f"Fitted trend: {slope_norm:+.1f} {unit}."]
    if np.isfinite(first_last):
        reasons.append(f"First to last year: {first_last:+.1f}{' pp' if is_ratio else ' %'}.")
    if reversals >= 2 and (swing > (2.0 if is_ratio else 0.25) or cv > 0.3):
        reasons.append(f"The series changed direction {reversals} times with large swings — no clean trend.")
        return TrendVerdict("volatile", "mixed", reasons, stats)
    if np.any(y <= 0) and not is_ratio and np.any(y > 0):
        reasons.append("The series crosses zero — growth rates are not meaningful; judge the level.")
    if abs(slope_norm) < flat_band:
        reasons.append(f"Within ±{flat_band} {unit} — treated as stable.")
        return TrendVerdict("stable", "flat", reasons, stats)
    direction = "up" if slope_norm > 0 else "down"
    better = m.higher_is_better if m is not None else True
    if better is None:
        return TrendVerdict("growing" if direction == "up" else "shrinking", direction, reasons + ["Neither good nor bad by itself — ask what drives it."], stats)
    good = (direction == "up") == bool(better)
    if not better:
        reasons.append("Lower is better for this metric.")
    return TrendVerdict("improving" if good else "deteriorating", direction, reasons, stats)


IMPORTANCE = {"net_income": 1.6, "revenue": 1.4, "total_equity": 1.4, "eps": 1.2, "cet1_ratio": 1.3, "solvency_ratio": 1.3, "total_assets": 1.1,
              "operating_cash_flow": 0.3, "net_new_money": 0.5, "total_liabilities": 0.6}


def unusual_changes(values: pd.DataFrame, rel_threshold: float = 25.0, pp_threshold: float = 2.0, exclude: set | None = None) -> list[dict]:
    """Year-over-year moves large enough to investigate in the annual report (most important first)."""
    out = []
    years = sorted(int(c) for c in values.columns)
    exclude = exclude or set()
    for key in values.index:
        m = M.get(key)
        if m is None or m.unit in ("shares",) or key in ("share_price",) or key in exclude:
            continue
        s = values.loc[key].astype(float)
        s.index = [int(c) for c in s.index]
        for y0, y1 in zip(years, years[1:]):
            a, b = s.get(y0), s.get(y1)
            if pd.isna(a) or pd.isna(b):
                continue
            if m.unit == "pct":
                change = b - a
                if abs(change) >= pp_threshold:
                    out.append({"metric": key, "year": y1, "from": a, "to": b, "change": change, "unit": "pp", "score": abs(change) / pp_threshold * IMPORTANCE.get(key, 1.0)})
            else:
                if a == 0:
                    continue
                change = (b / a - 1) * 100 if a > 0 else np.nan
                sign_flip = a * b < 0
                if sign_flip or (np.isfinite(change) and abs(change) >= rel_threshold):
                    score = (10.0 if sign_flip else min(abs(change) / rel_threshold, 8.0)) * IMPORTANCE.get(key, 1.0)
                    out.append({"metric": key, "year": y1, "from": a, "to": b, "change": change, "unit": "%", "score": score, "sign_flip": sign_flip})
    out.sort(key=lambda d: -d["score"])
    return out


def implied_other_equity_movements(values: pd.DataFrame, year: int) -> dict | None:
    """Equity roll-forward: ΔEquity − (Net income − dividends paid).

    Dividends paid in year t ≈ DPS of fiscal year t−1 × shares. What is left are
    buybacks, OCI (e.g. unrealised bond losses), FX translation, acquisitions…
    """
    def v(key, y):
        if key not in values.index or y not in values.columns:
            return None
        x = values.at[key, y]
        return None if pd.isna(x) else float(x)

    e0, e1, ni = v("total_equity", year - 1), v("total_equity", year), v("net_income", year)
    dps_prev, shares = v("dps", year - 1), v("shares_outstanding", year)
    if None in (e0, e1, ni):
        return None
    dividends = dps_prev * shares if dps_prev is not None and shares is not None else 0.0
    other = (e1 - e0) - (ni - dividends)
    return {"opening": e0, "closing": e1, "net_income": ni, "dividends": dividends, "other": other, "dividends_known": dps_prev is not None and shares is not None}


# --------------------------------------------------------------------------- formatting


def fmt_num(x: float | None, decimals: int = 0) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    return f"{x:,.{decimals}f}".replace(",", "'")  # Swiss thousands separator


def fmt_pct(x: float | None, decimals: int = 1, signed: bool = False) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    return f"{x:+.{decimals}f} %" if signed else f"{x:.{decimals}f} %"


def fmt_metric(x: float | None, metric_key: str, currency: str) -> str:
    m = M.get(metric_key)
    if m is None:
        return fmt_num(x, 1)
    if m.unit == "pct":
        return fmt_pct(x)
    if m.unit == "per_share":
        return f"{currency} {fmt_num(x, 2)}" if x is not None else "–"
    if m.unit == "bn":
        return f"{currency} {fmt_num(x, 1)} bn" if x is not None else "–"
    if m.unit == "shares":
        return f"{fmt_num(x, 1)} m" if x is not None else "–"
    return f"{currency} {fmt_num(x)} m" if x is not None else "–"
