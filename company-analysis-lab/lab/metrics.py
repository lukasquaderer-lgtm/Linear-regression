"""Metric catalogue.

Every financial line the app knows about is defined once here, with its English
(CFA-style) name, the German term used in Swiss/Liechtenstein annual reports, its
unit, which sector it applies to, where to find it, and a plausibility range used
by the validator.

Units
-----
money      millions of the reporting currency (e.g. "CHF m")
bn         billions of the reporting currency (assets under management, net new money)
per_share  currency units per share
pct        percent, entered as 14.3 for 14.3 %
shares     millions of shares
"""

from __future__ import annotations

from dataclasses import dataclass, field

SECTORS = ("bank", "insurer")


@dataclass(frozen=True)
class Metric:
    key: str
    en: str
    de: str
    unit: str
    sectors: tuple[str, ...] = SECTORS  # sectors the metric applies to
    core: bool = False  # required for every company
    sector_required: bool = False  # required for companies in `sectors`
    statement: str = ""  # where it is reported
    description: str = ""
    higher_is_better: bool | None = True  # None = no natural direction
    plausible: tuple[float | None, float | None] = (None, None)  # warning range
    hard: tuple[float | None, float | None] = (None, None)  # error range
    trend_metric: bool = True  # offered in Stage 3 trend analysis

    def label(self) -> str:
        return f"{self.en} · {self.de}"


def _m(*args, **kwargs) -> Metric:
    return Metric(*args, **kwargs)


CATALOG: dict[str, Metric] = {
    m.key: m
    for m in [
        # ------------------------------------------------------------------ common
        _m(
            "revenue",
            "Total operating income / revenue",
            "Geschäftsertrag / Umsatz",
            "money",
            core=True,
            statement="Income statement",
            description=(
                "Banks: total operating income (net interest + fees + trading + other). "
                "Insurers: total income/revenues; under IFRS 17 this no longer contains "
                "savings deposits, so it is not comparable with IFRS 4 'premiums'."
            ),
            hard=(None, None),
            plausible=(0, None),
        ),
        _m(
            "operating_expenses",
            "Operating expenses",
            "Geschäftsaufwand",
            "money",
            sectors=("bank",),
            sector_required=True,
            statement="Income statement",
            description="Personnel plus general and administrative expenses, depreciation and amortisation.",
            higher_is_better=False,
            plausible=(0, None),
        ),
        _m(
            "net_income",
            "Net income attributable to shareholders",
            "Konzerngewinn (den Aktionären zurechenbar)",
            "money",
            core=True,
            statement="Income statement",
            description="Profit after tax attributable to the parent's shareholders (excludes non-controlling interests).",
        ),
        _m(
            "total_assets",
            "Total assets",
            "Bilanzsumme (Total Aktiven)",
            "money",
            core=True,
            statement="Balance sheet",
            description="Everything the group controls. For banks and insurers mostly financial assets.",
            higher_is_better=None,
            hard=(0, None),
        ),
        _m(
            "total_liabilities",
            "Total liabilities",
            "Total Verbindlichkeiten (Fremdkapital)",
            "money",
            core=True,
            statement="Balance sheet",
            description="Deposits, debt issued, insurance contract liabilities, derivatives and other obligations.",
            higher_is_better=None,
            hard=(0, None),
        ),
        _m(
            "total_equity",
            "Shareholders' equity",
            "Eigenkapital (den Aktionären zurechenbar)",
            "money",
            core=True,
            statement="Balance sheet",
            description="Equity attributable to shareholders (excludes non-controlling interests). Used for ROE and book value per share.",
            plausible=(0, None),
        ),
        _m(
            "operating_cash_flow",
            "Cash flow from operating activities",
            "Geldfluss aus Geschäftstätigkeit",
            "money",
            statement="Cash flow statement",
            description=(
                "Meaningful for insurers with care; for banks it is dominated by changes in loans, "
                "deposits and trading positions and is rarely used to judge earnings quality."
            ),
            trend_metric=False,
        ),
        _m(
            "eps",
            "Diluted earnings per share (EPS)",
            "Verwässerter Gewinn pro Aktie",
            "per_share",
            core=True,
            statement="Income statement",
            description="Net income attributable to shareholders divided by diluted weighted average shares.",
        ),
        _m(
            "dps",
            "Dividend per share (for the fiscal year)",
            "Dividende pro Aktie (für das Geschäftsjahr)",
            "per_share",
            core=True,
            statement="Proposal for appropriation of profit / statement of changes in equity",
            description="Dividend proposed for the fiscal year (paid in the following spring).",
            hard=(0, None),
        ),
        _m(
            "shares_outstanding",
            "Shares outstanding (diluted, average)",
            "Ausstehende Aktien (verwässert, Durchschnitt)",
            "shares",
            statement="EPS note",
            description="Needed for book value per share and market capitalisation.",
            higher_is_better=None,
            hard=(0, None),
            trend_metric=False,
        ),
        _m(
            "share_price",
            "Share price at year-end",
            "Aktienkurs per Jahresende",
            "per_share",
            statement="Market data (stock exchange)",
            description="Optional. Needed for historical P/E, P/B and dividend yield.",
            higher_is_better=None,
            hard=(0, None),
            trend_metric=False,
        ),
        _m(
            "aum",
            "Assets under management / invested assets",
            "Verwaltete Vermögen",
            "bn",
            statement="Management report / segment reporting",
            description="Client assets managed or advised. Drives recurring fee income. Off-balance-sheet.",
            hard=(0, None),
        ),
        _m(
            "roe_reported",
            "Return on equity (as reported)",
            "Eigenkapitalrendite (ausgewiesen)",
            "pct",
            statement="Key figures",
            description="The company's own ROE definition — compare it with your calculation in Stage 4.",
            plausible=(-30, 40),
            hard=(-100, 100),
        ),
        # ------------------------------------------------------------------ banks
        _m(
            "net_interest_income",
            "Net interest income (NII)",
            "Zinserfolg (Nettozinsertrag)",
            "money",
            sectors=("bank",),
            sector_required=True,
            statement="Income statement",
            description="Interest earned on loans and securities minus interest paid on deposits and debt.",
        ),
        _m(
            "fee_income",
            "Net fee and commission income",
            "Kommissions- und Dienstleistungserfolg",
            "money",
            sectors=("bank",),
            sector_required=True,
            statement="Income statement",
            description="Asset-management, advisory, brokerage and custody fees. Usually the most stable bank revenue.",
        ),
        _m(
            "cet1_capital",
            "Common equity tier 1 (CET1) capital",
            "Hartes Kernkapital (CET1)",
            "money",
            sectors=("bank",),
            statement="Capital management / Basel III Pillar 3 disclosure",
            description="Regulatory loss-absorbing equity after deductions (goodwill, DTAs, dividend accrual …).",
            plausible=(0, None),
        ),
        _m(
            "rwa",
            "Risk-weighted assets (RWA)",
            "Risikogewichtete Aktiven (RWA)",
            "money",
            sectors=("bank",),
            statement="Capital management / Pillar 3 disclosure",
            description="Assets weighted by credit, market and operational risk. Denominator of the CET1 ratio.",
            higher_is_better=None,
            hard=(0, None),
        ),
        _m(
            "cet1_ratio",
            "CET1 capital ratio",
            "Harte Kernkapitalquote (CET1-Quote)",
            "pct",
            sectors=("bank",),
            sector_required=True,
            statement="Key figures / capital management",
            description="CET1 capital ÷ RWA. The key solvency measure for banks.",
            plausible=(8, 40),
            hard=(0, 100),
        ),
        _m(
            "net_new_money",
            "Net new money / net new assets",
            "Netto-Neugeld",
            "bn",
            sectors=("bank",),
            statement="Management report",
            description="Client inflows minus outflows, excluding market performance. A leading indicator for fee income.",
        ),
        _m(
            "cost_income_ratio",
            "Cost/income ratio (as reported)",
            "Aufwand-Ertrags-Verhältnis (Cost-Income-Ratio)",
            "pct",
            sectors=("bank",),
            sector_required=True,
            statement="Key figures",
            description="Operating expenses ÷ operating income. Lower is more efficient.",
            higher_is_better=False,
            plausible=(30, 110),
            hard=(0, 300),
        ),
        _m(
            "credit_loss_expense",
            "Credit loss expense / (release)",
            "Wertberichtigungen für Ausfallrisiken",
            "money",
            sectors=("bank",),
            statement="Income statement / credit risk note",
            description="Expected credit loss charges. A release (negative) boosts profit — check if it is recurring.",
            higher_is_better=False,
            trend_metric=False,
        ),
        _m(
            "customer_loans",
            "Loans and advances to customers",
            "Forderungen gegenüber Kunden (inkl. Hypotheken)",
            "money",
            sectors=("bank",),
            statement="Balance sheet",
            higher_is_better=None,
            hard=(0, None),
            trend_metric=False,
        ),
        _m(
            "customer_deposits",
            "Customer deposits",
            "Verpflichtungen aus Kundeneinlagen",
            "money",
            sectors=("bank",),
            statement="Balance sheet",
            higher_is_better=None,
            hard=(0, None),
            trend_metric=False,
        ),
        # ------------------------------------------------------------------ insurers
        _m(
            "gross_premiums",
            "Gross written premiums (incl. policy fees & deposits)",
            "Gebuchte Bruttoprämien (inkl. Policengebühren und Einlagen)",
            "money",
            sectors=("insurer",),
            statement="Management report (volume measure, not IFRS 17 revenue)",
            description="Business volume written in the year. Still reported as a KPI after IFRS 17.",
            plausible=(0, None),
        ),
        _m(
            "insurance_revenue",
            "Insurance revenue (IFRS 17)",
            "Versicherungsumsatz (IFRS 17)",
            "money",
            sectors=("insurer",),
            sector_required=True,
            statement="Income statement",
            description="Revenue for insurance services provided in the period; excludes investment components.",
            plausible=(0, None),
        ),
        _m(
            "investment_income",
            "Net investment income",
            "Nettoertrag aus Kapitalanlagen",
            "money",
            sectors=("insurer",),
            sector_required=True,
            statement="Income statement / investment note",
            description="Interest, dividends and rental income on the investment portfolio (before insurance finance expenses).",
        ),
        _m(
            "insurance_service_result",
            "Insurance service result (IFRS 17)",
            "Versicherungstechnisches Ergebnis (IFRS 17)",
            "money",
            sectors=("insurer",),
            statement="Income statement",
            description="Insurance revenue minus insurance service expenses (and reinsurance result).",
        ),
        _m(
            "solvency_ratio",
            "Solvency ratio (SST / Solvency II)",
            "Solvenzquote (SST / Solvency II)",
            "pct",
            sectors=("insurer",),
            sector_required=True,
            statement="Financial condition report / SFCR",
            description="Available risk-bearing capital ÷ required capital. Below 100 % triggers supervisory action.",
            plausible=(100, 400),
            hard=(0, 1000),
        ),
        _m(
            "combined_ratio",
            "Combined ratio (P&C)",
            "Schaden-Kosten-Quote (Combined Ratio)",
            "pct",
            sectors=("insurer",),
            statement="Segment reporting (P&C)",
            description="(Claims + expenses) ÷ earned premiums. Below 100 % = underwriting profit. Not used for life insurers.",
            higher_is_better=False,
            plausible=(70, 130),
            hard=(0, 300),
        ),
        _m(
            "csm",
            "Contractual service margin (CSM)",
            "Vertragliche Servicemarge (CSM)",
            "money",
            sectors=("insurer",),
            statement="Insurance contracts note (IFRS 17)",
            description="Unearned profit on in-force insurance contracts, released over the coverage period.",
            plausible=(0, None),
        ),
    ]
}

UNIT_SUFFIX = {"money": "m", "bn": "bn", "per_share": "/share", "pct": "%", "shares": "m shares"}

DEFAULT_YEARS = [2021, 2022, 2023, 2024, 2025]


def get(key: str) -> Metric | None:
    return CATALOG.get(key)


def metrics_for_sector(sector: str) -> list[Metric]:
    return [m for m in CATALOG.values() if sector in m.sectors]


def required_metrics(sector: str) -> list[Metric]:
    return [m for m in metrics_for_sector(sector) if m.core or m.sector_required]


def unit_label(metric_key: str, currency: str) -> str:
    m = CATALOG.get(metric_key)
    if m is None:
        return ""
    if m.unit == "money":
        return f"{currency} m"
    if m.unit == "bn":
        return f"{currency} bn"
    if m.unit == "per_share":
        return f"{currency} per share"
    if m.unit == "pct":
        return "%"
    if m.unit == "shares":
        return "m shares"
    return ""


def label(metric_key: str, custom: dict | None = None) -> str:
    """Bilingual label for a catalogue metric or a user-defined custom metric."""
    m = CATALOG.get(metric_key)
    if m is not None:
        return m.label()
    if custom and metric_key in custom:
        c = custom[metric_key]
        return f"{c.get('en', metric_key)} · {c.get('de', '')}".rstrip(" ·")
    return metric_key


def short(metric_key: str, custom: dict | None = None) -> str:
    m = CATALOG.get(metric_key)
    if m is not None:
        return m.en
    if custom and metric_key in custom:
        return custom[metric_key].get("en", metric_key)
    return metric_key


# Aliases used when importing CSV/Excel files (lower-case, punctuation removed).
ALIASES: dict[str, str] = {
    "revenue": "revenue",
    "revenues": "revenue",
    "total revenues": "revenue",
    "total revenue": "revenue",
    "operating income": "revenue",
    "total operating income": "revenue",
    "geschaftsertrag": "revenue",
    "geschäftsertrag": "revenue",
    "umsatz": "revenue",
    "operating expenses": "operating_expenses",
    "opex": "operating_expenses",
    "geschaftsaufwand": "operating_expenses",
    "geschäftsaufwand": "operating_expenses",
    "net income": "net_income",
    "net profit": "net_income",
    "net profit attributable to shareholders": "net_income",
    "konzerngewinn": "net_income",
    "reingewinn": "net_income",
    "total assets": "total_assets",
    "bilanzsumme": "total_assets",
    "total liabilities": "total_liabilities",
    "fremdkapital": "total_liabilities",
    "equity": "total_equity",
    "total equity": "total_equity",
    "shareholders equity": "total_equity",
    "eigenkapital": "total_equity",
    "operating cash flow": "operating_cash_flow",
    "cash flow from operating activities": "operating_cash_flow",
    "eps": "eps",
    "diluted eps": "eps",
    "earnings per share": "eps",
    "gewinn pro aktie": "eps",
    "dps": "dps",
    "dividend per share": "dps",
    "dividende pro aktie": "dps",
    "shares": "shares_outstanding",
    "shares outstanding": "shares_outstanding",
    "share price": "share_price",
    "aktienkurs": "share_price",
    "net interest income": "net_interest_income",
    "nii": "net_interest_income",
    "zinserfolg": "net_interest_income",
    "fee income": "fee_income",
    "net fee and commission income": "fee_income",
    "kommissionserfolg": "fee_income",
    "cet1 capital": "cet1_capital",
    "cet1": "cet1_capital",
    "cet1 ratio": "cet1_ratio",
    "rwa": "rwa",
    "risk weighted assets": "rwa",
    "aum": "aum",
    "assets under management": "aum",
    "invested assets": "aum",
    "verwaltete vermogen": "aum",
    "verwaltete vermögen": "aum",
    "net new money": "net_new_money",
    "nnm": "net_new_money",
    "netto neugeld": "net_new_money",
    "cost income ratio": "cost_income_ratio",
    "cost/income ratio": "cost_income_ratio",
    "roe": "roe_reported",
    "return on equity": "roe_reported",
    "premiums": "gross_premiums",
    "gross written premiums": "gross_premiums",
    "insurance revenue": "insurance_revenue",
    "investment income": "investment_income",
    "net investment income": "investment_income",
    "insurance service result": "insurance_service_result",
    "solvency ratio": "solvency_ratio",
    "sst ratio": "solvency_ratio",
    "combined ratio": "combined_ratio",
    "csm": "csm",
    "credit loss expense": "credit_loss_expense",
    "loans": "customer_loans",
    "deposits": "customer_deposits",
}


def resolve_alias(name: str) -> str | None:
    """Map a free-text row label from an imported file to a catalogue key."""
    raw = str(name).strip()
    if raw in CATALOG:
        return raw
    norm = "".join(ch for ch in raw.lower().replace("_", " ").replace("-", " ") if ch.isalnum() or ch in " /äöü")
    norm = " ".join(norm.split())
    if norm in ALIASES:
        return ALIASES[norm]
    # drop a trailing unit annotation such as "(chf m)"
    for sep in ("(", "["):
        if sep in raw:
            return resolve_alias(raw.split(sep)[0])
    return None


@dataclass
class CustomMetric:
    key: str
    en: str
    de: str = ""
    unit: str = "money"
    higher_is_better: bool | None = True
    extra: dict = field(default_factory=dict)
