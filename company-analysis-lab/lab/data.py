"""Company datasets: loading, saving, import and validation.

A company lives in ``datasets/companies/<id>/``:

    profile.json     qualitative profile, accounting basis per year, reference notes
    financials.csv   wide table: one row per metric, one column per fiscal year,
                     plus ``source`` and ``note`` columns

To add a company, copy one of the folders (or use "Add a company" in the app),
edit ``profile.json`` and fill ``financials.csv``. The learner's edits are kept
separately in the workspace (see ``storage.py``) so the starter files stay clean.
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import metrics as M
from .storage import APP_DIR, company_dir

DATASETS_DIR = APP_DIR / "datasets" / "companies"
META_COLUMNS = ["source", "note"]


# --------------------------------------------------------------------------- profiles


def list_companies() -> list[dict]:
    profiles = []
    for folder in sorted(DATASETS_DIR.iterdir()) if DATASETS_DIR.exists() else []:
        if (folder / "profile.json").exists():
            try:
                profiles.append(load_profile(folder.name))
            except (json.JSONDecodeError, OSError):
                continue
    return sorted(profiles, key=lambda p: p.get("name", p["id"]))


def load_profile(company_id: str) -> dict:
    path = DATASETS_DIR / company_id / "profile.json"
    profile = json.loads(path.read_text(encoding="utf-8"))
    profile.setdefault("id", company_id)
    profile.setdefault("short_name", profile.get("name", company_id))
    profile.setdefault("required_extra", [])
    profile.setdefault("not_applicable", [])
    profile.setdefault("events", [])
    profile.setdefault("business_reference", {})
    profile.setdefault("top_risks_reference", [])
    profile.setdefault("audit_focus", [])
    profile.setdefault("quiz", [])
    profile.setdefault("accounting", {})
    return profile


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "company"


def create_company(name: str, sector: str, currency: str, country: str = "", listed: bool = True) -> str:
    """Create a new company folder with an empty template. Returns the new id."""
    if sector not in M.SECTORS:
        raise ValueError(f"Sector must be one of {M.SECTORS}")
    base = slugify(name)
    company_id, i = base, 2
    while (DATASETS_DIR / company_id).exists():
        company_id, i = f"{base}_{i}", i + 1
    folder = DATASETS_DIR / company_id
    folder.mkdir(parents=True)
    profile = {
        "id": company_id,
        "name": name,
        "short_name": name,
        "sector": sector,
        "subsector": "",
        "country": country,
        "headquarters": "",
        "listed": listed,
        "exchange_ticker": "",
        "currency": currency,
        "currency_confirmed": True,
        "fiscal_year_end": "31 December",
        "accounting": {},
        "accounting_notes": "",
        "regulator": "",
        "capital_regime": "",
        "investor_relations": "",
        "annual_report_hint": "Find the latest annual report on the company's investor-relations website.",
        "data_source": "Entered by the learner.",
        "required_extra": [],
        "not_applicable": [] if listed else ["eps", "dps", "shares_outstanding", "share_price"],
        "business_reference": {},
        "events": [],
        "top_risks_reference": [],
        "audit_focus": [],
        "quiz": [],
        "peers_suggested": [],
    }
    (folder / "profile.json").write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    template = empty_frame(required_metric_keys(profile), M.DEFAULT_YEARS)
    meta = pd.DataFrame({"source": "To collect from the annual report", "note": ""}, index=template.index)
    _write_csv(folder / "financials.csv", template, meta)
    return company_id


# --------------------------------------------------------------------------- metric sets


def applicable_metric_keys(profile: dict) -> list[str]:
    excluded = set(profile.get("not_applicable", []))
    return [m.key for m in M.metrics_for_sector(profile["sector"]) if m.key not in excluded]


def required_metric_keys(profile: dict) -> list[str]:
    excluded = set(profile.get("not_applicable", []))
    keys = [m.key for m in M.required_metrics(profile["sector"])]
    keys += [k for k in profile.get("required_extra", []) if k not in keys]
    return [k for k in keys if k not in excluded]


def core_metric_keys(profile: dict) -> list[str]:
    excluded = set(profile.get("not_applicable", []))
    return [m.key for m in M.CATALOG.values() if m.core and m.key not in excluded]


# --------------------------------------------------------------------------- frames


def empty_frame(metric_keys: list[str], years: list[int]) -> pd.DataFrame:
    return pd.DataFrame(np.nan, index=pd.Index(metric_keys, name="metric"), columns=list(years), dtype=float)


def year_columns(df: pd.DataFrame) -> list[int]:
    return sorted(int(c) for c in df.columns if str(c).isdigit())


def _split(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = raw.copy()
    raw["metric"] = raw["metric"].astype(str).str.strip()
    raw = raw.drop_duplicates("metric", keep="last").set_index("metric")
    years = [c for c in raw.columns if str(c).strip().isdigit()]
    values = raw[years].apply(pd.to_numeric, errors="coerce").astype(float)
    values.columns = [int(str(c).strip()) for c in years]
    values = values[sorted(values.columns)]
    meta = pd.DataFrame(index=raw.index)
    for col in META_COLUMNS:
        meta[col] = raw[col].fillna("").astype(str) if col in raw.columns else ""
    values.index.name = "metric"
    meta.index.name = "metric"
    return values, meta


def _write_csv(path: Path, values: pd.DataFrame, meta: pd.DataFrame) -> None:
    out = values.copy()
    out.columns = [str(c) for c in out.columns]
    meta = meta.reindex(out.index).fillna("")
    for col in META_COLUMNS:
        out[col] = meta[col] if col in meta.columns else ""
    out.index.name = "metric"
    out.to_csv(path, float_format="%.6g")


def load_starter(company_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(DATASETS_DIR / company_id / "financials.csv", dtype={"source": str, "note": str})
    return _split(raw)


def load_working(company_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The learner's dataset: workspace copy if it exists, otherwise the starter data."""
    path = company_dir(company_id) / "financials.csv"
    if path.exists():
        raw = pd.read_csv(path, dtype={"source": str, "note": str})
        return _split(raw)
    return load_starter(company_id)


def save_working(company_id: str, values: pd.DataFrame, meta: pd.DataFrame) -> None:
    _write_csv(company_dir(company_id) / "financials.csv", values, meta)


def reset_working(company_id: str) -> None:
    path = company_dir(company_id) / "financials.csv"
    if path.exists():
        path.unlink()


def ensure_rows(values: pd.DataFrame, meta: pd.DataFrame, keys: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Make sure every key in ``keys`` has a row (missing rows are added empty)."""
    missing = [k for k in keys if k not in values.index]
    if missing:
        values = pd.concat([values, empty_frame(missing, year_columns(values) or M.DEFAULT_YEARS)])
        add = pd.DataFrame({"source": "To collect from the annual report", "note": ""}, index=pd.Index(missing, name="metric"))
        meta = pd.concat([meta, add])
    return values, meta


def ordered(values: pd.DataFrame, profile: dict, custom: dict | None = None) -> pd.DataFrame:
    """Sort rows: catalogue order (common → sector) then custom metrics."""
    catalog_order = {k: i for i, k in enumerate(M.CATALOG)}
    keys = sorted(values.index, key=lambda k: (catalog_order.get(k, 10_000), str(k)))
    return values.loc[keys]


def series(values: pd.DataFrame, key: str) -> pd.Series:
    if key not in values.index:
        return pd.Series(dtype=float)
    s = values.loc[key]
    s.index = [int(c) for c in s.index]
    return s.astype(float)


def value(values: pd.DataFrame, key: str, year: int) -> float | None:
    if key not in values.index or year not in values.columns:
        return None
    v = values.at[key, year]
    return None if pd.isna(v) else float(v)


# --------------------------------------------------------------------------- import


@dataclass
class ImportReport:
    mapped: dict  # original label -> metric key
    unmapped: list
    years: list
    orientation: str


def parse_number(x, decimal_comma: bool = False) -> float:
    """Parse numbers as written in annual reports: 1'234.5 · 1,234.5 · 1.234,5 · (123) · 14.3 % · –."""
    if x is None:
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    t = str(x).strip().replace("\u2019", "'").replace("\u202f", "").replace("\xa0", "").replace(" ", "").replace("'", "").replace("%", "")
    if t in ("", "-", "–", "—", "n/a", "na", "nan", "None"):
        return np.nan
    negative = t.startswith("(") and t.endswith(")")
    t = t.strip("()").replace("−", "-").replace("–", "-")
    if decimal_comma:
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", "")
    try:
        v = float(t)
    except ValueError:
        return np.nan
    return -v if negative else v


def _looks_like_year(x) -> bool:
    try:
        y = int(float(str(x).strip()))
    except ValueError:
        return False
    return 1990 <= y <= 2100 and str(x).strip().replace(".0", "").isdigit()


def import_table(content: bytes, filename: str) -> tuple[pd.DataFrame, ImportReport]:
    """Read a CSV or Excel file in wide or long format and map rows to catalogue metrics.

    Accepted layouts:
      * wide:       metric | 2021 | 2022 | ...        (metrics as rows, years as columns)
      * transposed: year | revenue | net_income | ... (years as rows)
      * long:       metric | year | value
    Unknown labels are kept as custom metrics (key = slug of the label).
    """
    name = filename.lower()
    sep = ","
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        raw = pd.read_excel(io.BytesIO(content))
    else:
        text = content.decode("utf-8-sig", errors="replace")
        sep = ";" if text.count(";") > text.count(",") else ","
        raw = pd.read_csv(io.StringIO(text), sep=sep)
    raw.columns = [str(c).strip() for c in raw.columns]
    lower = {c.lower(): c for c in raw.columns}

    if {"metric", "year", "value"} <= set(lower):
        orientation = "long"
        long = raw.rename(columns={lower["metric"]: "metric", lower["year"]: "year", lower["value"]: "value"})
        long["year"] = pd.to_numeric(long["year"], errors="coerce")
        long = long.dropna(subset=["year"])
        long["year"] = long["year"].astype(int)
        wide = long.pivot_table(index="metric", columns="year", values="value", aggfunc="last")
    else:
        first = raw.columns[0]
        year_cols = [c for c in raw.columns[1:] if _looks_like_year(c)]
        if year_cols:
            orientation = "wide"
            wide = raw.set_index(first)[year_cols]
            wide.columns = [int(float(c)) for c in year_cols]
        elif raw[first].map(_looks_like_year).all():
            orientation = "transposed"
            wide = raw.set_index(first).T
            wide.columns = [int(float(c)) for c in wide.columns]
        else:
            raise ValueError(
                "Could not find year columns. Use either 'metric, 2021, 2022, …' (wide), "
                "'year, revenue, net_income, …' (years as rows) or 'metric, year, value' (long)."
            )

    decimal_comma = sep == ";" if not name.endswith((".xlsx", ".xlsm", ".xls")) else False
    wide = wide.apply(lambda col: col.map(lambda x: parse_number(x, decimal_comma)))
    mapped, unmapped, rows = {}, [], {}
    for label, row in wide.iterrows():
        key = M.resolve_alias(str(label))
        if key is None:
            key = slugify(str(label))
            unmapped.append(str(label))
        else:
            mapped[str(label)] = key
        rows[key] = row
    out = pd.DataFrame(rows).T.astype(float)
    out.index.name = "metric"
    out = out[sorted(out.columns)]
    return out, ImportReport(mapped, unmapped, list(out.columns), orientation)


def merge_import(values: pd.DataFrame, imported: pd.DataFrame, overwrite: bool = True) -> pd.DataFrame:
    """Combine imported values into the working dataset (new years/rows are added)."""
    years = sorted(set(year_columns(values)) | set(int(c) for c in imported.columns))
    keys = list(dict.fromkeys(list(values.index) + list(imported.index)))
    merged = values.reindex(index=keys, columns=years)
    imp = imported.reindex(index=keys, columns=years)
    if overwrite:
        merged = imp.combine_first(merged)
    else:
        merged = merged.combine_first(imp)
    merged.index.name = "metric"
    return merged.astype(float)


# --------------------------------------------------------------------------- validation


@dataclass
class Issue:
    severity: str  # "error" | "warning" | "info"
    metric: str
    year: int | None
    message: str

    def as_dict(self) -> dict:
        return asdict(self)


SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def _fmt_years(years: list[int]) -> str:
    return ", ".join(str(y) for y in years)


def validate(values: pd.DataFrame, profile: dict, custom: dict | None = None) -> list[Issue]:
    """Flag impossible, implausible, inconsistent and missing values."""
    issues: list[Issue] = []
    years = year_columns(values)
    if len(years) < 5:
        issues.append(Issue("error", "—", None, f"Only {len(years)} fiscal years — the analysis needs at least 5."))
    if years and years != list(range(years[0], years[-1] + 1)):
        issues.append(Issue("warning", "—", None, "Years are not consecutive — growth rates between gaps are misleading."))

    required = set(required_metric_keys(profile))
    core = set(core_metric_keys(profile))
    latest3 = years[-3:]
    v = values

    # ---- missing values
    for key in sorted(required | set(v.index), key=lambda k: list(M.CATALOG).index(k) if k in M.CATALOG else 999):
        s = series(v, key)
        missing = [y for y in years if y not in s.index or pd.isna(s.get(y))]
        if not missing:
            continue
        if key in core:
            issues.append(Issue("error", key, None, f"Missing for {_fmt_years(missing)} (required for every year)."))
        elif key in required:
            recent_missing = [y for y in missing if y in latest3]
            if recent_missing:
                issues.append(Issue("error", key, None, f"Missing for {_fmt_years(recent_missing)} (needed at least for the latest three years)."))
            older = [y for y in missing if y not in latest3]
            if older:
                issues.append(Issue("warning", key, None, f"Missing for {_fmt_years(older)} — fill in for a full 5-year trend."))
        elif len(missing) < len(years):
            issues.append(Issue("info", key, None, f"Partly filled (missing {_fmt_years(missing)})."))

    # ---- range checks
    for key in v.index:
        m = M.get(key)
        if m is None:
            continue
        for y in years:
            x = value(v, key, y)
            if x is None:
                continue
            lo, hi = m.hard
            if (lo is not None and x < lo) or (hi is not None and x > hi):
                issues.append(Issue("error", key, y, f"{x:,.2f} is impossible for {m.en} (allowed range {lo if lo is not None else '−∞'} to {hi if hi is not None else '∞'})."))
                continue
            if m.unit == "pct" and 0 < abs(x) < 1 and (m.plausible[0] or 0) >= 1:
                issues.append(Issue("warning", key, y, f"{x} looks like a decimal — enter percentages as 14.3, not 0.143."))
                continue
            plo, phi = m.plausible
            if (plo is not None and x < plo) or (phi is not None and x > phi):
                issues.append(Issue("warning", key, y, f"{x:,.2f} is outside the usual range for {m.en} ({plo if plo is not None else '…'} to {phi if phi is not None else '…'}) — double-check."))
            if m.unit == "bn" and abs(x) > 20_000:
                issues.append(Issue("warning", key, y, f"{x:,.0f} bn is very large — this metric is in billions. Did you enter millions?"))

    for y in years:
        a, l, e = value(v, "total_assets", y), value(v, "total_liabilities", y), value(v, "total_equity", y)
        ni, eps, sh = value(v, "net_income", y), value(v, "eps", y), value(v, "shares_outstanding", y)
        rev = value(v, "revenue", y)
        # ---- balance sheet identity
        if a is not None and l is not None and e is not None and a > 0:
            gap = a - l - e
            rel_equity = abs(gap) / abs(e) if e else float("inf")
            if rel_equity > 0.25 and abs(gap) > 0.001 * a:
                issues.append(Issue("error", "total_assets", y, f"Assets ({a:,.0f}) ≠ liabilities + equity ({l + e:,.0f}); gap {gap:,.0f}. Check units or a typo."))
            elif rel_equity > 0.02:
                issues.append(Issue("info", "total_equity", y, f"Assets − liabilities − equity = {gap:,.0f} — usually non-controlling interests (minority interests). Fine if so."))
        if l is not None and a is not None and l > a:
            issues.append(Issue("warning", "total_liabilities", y, "Liabilities exceed assets (negative equity) — verify."))
        # ---- EPS consistency
        if ni is not None and eps is not None and ni != 0 and eps != 0 and np.sign(ni) != np.sign(eps):
            issues.append(Issue("warning", "eps", y, "EPS and net income have opposite signs."))
        if ni is not None and eps is not None and sh and ni:
            implied = eps * sh
            if abs(implied - ni) / abs(ni) > 0.10:
                issues.append(Issue("warning", "eps", y, f"EPS × shares = {implied:,.0f} but net income = {ni:,.0f} (>10 % apart). Check the share count unit (millions) or the EPS basis."))
        # ---- dividends
        dps = value(v, "dps", y)
        if dps is not None and eps is not None and eps > 0 and dps > eps:
            issues.append(Issue("info", "dps", y, f"Dividend ({dps}) exceeds EPS ({eps}) — payout above 100 %. Sustainable?"))
        # ---- net income vs revenue
        if ni is not None and rev is not None and rev > 0 and ni > rev:
            issues.append(Issue("info", "net_income", y, "Net income exceeds revenue — usually a gain outside revenue (e.g. negative goodwill or a disposal gain). Investigate in Stage 5."))
        # ---- bank capital consistency
        c1, rwa, ratio = value(v, "cet1_capital", y), value(v, "rwa", y), value(v, "cet1_ratio", y)
        if c1 is not None and rwa and ratio is not None:
            calc = c1 / rwa * 100
            if abs(calc - ratio) > 0.3:
                issues.append(Issue("warning", "cet1_ratio", y, f"CET1 capital ÷ RWA = {calc:.1f} % but the CET1 ratio entered is {ratio:.1f} %."))
        if rwa is not None and a is not None and rwa > a:
            issues.append(Issue("warning", "rwa", y, "RWA exceed total assets — unusual (RWA density > 100 %)."))
        # ---- non-financial consistency
        ebit, gp = value(v, "ebit", y), value(v, "gross_profit", y)
        if gp is not None and rev is not None and rev > 0 and gp > rev * 1.001:
            issues.append(Issue("error", "gross_profit", y, f"Gross profit ({gp:,.0f}) exceeds revenue ({rev:,.0f}) — impossible. Check the revenue definition or a typo."))
        if ebit is not None and rev is not None and rev > 0 and ebit > rev:
            issues.append(Issue("warning", "ebit", y, f"Operating result ({ebit:,.0f}) exceeds revenue ({rev:,.0f}) — check units or whether revenue excludes large other income."))
        ocf, capex, fcf = value(v, "operating_cash_flow", y), value(v, "capex", y), value(v, "free_cash_flow", y)
        if ocf is not None and capex is not None and fcf is not None and abs(fcf) > 0:
            own = ocf - capex
            if abs(own - fcf) > 0.15 * max(abs(fcf), abs(own)):
                issues.append(Issue("info", "free_cash_flow", y, f"Operating cash flow − capex = {own:,.0f} but reported free cash flow = {fcf:,.0f} — the company uses its own definition (leases, interest, acquisitions?). Note which one you use."))
        debt = value(v, "total_debt", y)
        if debt is not None and l is not None and debt > l * 1.001:
            issues.append(Issue("error", "total_debt", y, f"Financial debt ({debt:,.0f}) exceeds total liabilities ({l:,.0f}) — impossible."))
        for part in ("current_assets", "cash", "inventories", "receivables"):
            x = value(v, part, y)
            if x is not None and a is not None and a > 0 and x > a * 1.001:
                issues.append(Issue("error", part, y, f"{M.short(part)} ({x:,.0f}) exceeds total assets ({a:,.0f}) — impossible."))
        opex, ci = value(v, "operating_expenses", y), value(v, "cost_income_ratio", y)
        if opex is not None and rev and ci is not None:
            calc = opex / rev * 100
            if abs(calc - ci) > 3:
                issues.append(Issue("info", "cost_income_ratio", y, f"Operating expenses ÷ revenue = {calc:.1f} % vs reported {ci:.1f} % — the company may use an adjusted definition."))

    # ---- implausible jumps (possible unit errors)
    for key in v.index:
        m = M.get(key)
        if m is None or m.unit not in ("money", "bn") or key in ("operating_cash_flow", "net_new_money", "credit_loss_expense", "free_cash_flow"):
            continue
        s = series(v, key).dropna()
        for (y0, x0), (y1, x1) in zip(s.items(), list(s.items())[1:]):
            if x0 and abs(x0) > 0 and abs(x1 / x0) > 5 and abs(x1) > 0:
                issues.append(Issue("info", key, y1, f"Changed by a factor of {abs(x1 / x0):.1f} vs {y0} — unit error, or a genuine event to investigate?"))

    issues.sort(key=lambda i: (SEVERITY_ORDER[i.severity], str(i.metric), i.year or 0))
    return issues


def issues_frame(issues: list[Issue], custom: dict | None = None) -> pd.DataFrame:
    if not issues:
        return pd.DataFrame(columns=["Severity", "Metric", "Year", "Issue"])
    return pd.DataFrame(
        {
            "Severity": [i.severity.capitalize() for i in issues],
            "Metric": [M.short(i.metric, custom) if i.metric != "—" else "Dataset" for i in issues],
            "Year": [str(i.year) if i.year else "" for i in issues],
            "Issue": [i.message for i in issues],
        }
    )
