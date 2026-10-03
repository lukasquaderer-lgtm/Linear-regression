"""Short 'CFA Connection' notes — one or two sentences each, linking the task to the curriculum.

Topic areas follow the CFA Program: Financial Statement Analysis, Equity Investments,
Corporate Issuers, Fixed Income, Economics, Portfolio Management, Derivatives.
"""

from __future__ import annotations

CFA: dict[str, tuple[str, str]] = {
    "business_model": ("Corporate Issuers · Equity Investments", "Understanding the business model, revenue drivers and competitive position is the first step of company analysis (industry and competitive analysis, e.g. Porter's five forces)."),
    "industry_analysis": ("Equity Investments", "Competitive advantages ('moats') explain whether high returns on equity can persist — the link between industry structure and valuation."),
    "data_collection": ("Financial Statement Analysis", "Analysts start from the audited statements and must understand the reporting basis (IFRS vs US GAAP, restatements) before comparing years."),
    "growth_cagr": ("Quantitative Methods · FSA", "CAGR is the geometric mean growth rate — it smooths volatile year-to-year changes, unlike the arithmetic average of growth rates."),
    "trend": ("Financial Statement Analysis", "Trend (horizontal) analysis compares a line item across periods; always ask whether a change is operational, accounting-driven or one-off."),
    "roe": ("Financial Statement Analysis · Equity", "ROE = net income ÷ average shareholders' equity. CFA uses average balances because income is earned over the whole year."),
    "roa": ("Financial Statement Analysis", "ROA measures profit per unit of total assets. Banks and insurers have very low ROA (≈0.3–1 %) because their balance sheets are highly leveraged."),
    "dupont": ("Financial Statement Analysis", "DuPont analysis: ROE = net margin × asset turnover × financial leverage (= ROA × leverage). It shows whether ROE comes from profitability or from leverage."),
    "net_margin": ("Financial Statement Analysis", "Net profit margin links the income statement's top and bottom lines — for financials, define 'revenue' carefully (operating income, insurance revenue)."),
    "cost_income": ("Financial Statement Analysis", "Cost/income is the bank-specific efficiency ratio — the analogue of an operating margin (1 − cost/income ≈ pre-provision margin)."),
    "leverage": ("Financial Statement Analysis · Corporate Issuers", "Financial leverage (equity multiplier) = average assets ÷ average equity. Higher leverage amplifies ROE — and losses."),
    "payout": ("Corporate Issuers · Equity", "Payout ratio and retention ratio (b = 1 − payout) determine sustainable growth: g = b × ROE."),
    "bvps": ("Equity Investments", "Book value per share is the anchor for P/B valuation — most relevant for banks and insurers whose assets are largely financial and marked close to fair value."),
    "cet1": ("Financial Statement Analysis (financial institutions)", "Bank analysis follows CAMELS (capital, asset quality, management, earnings, liquidity, sensitivity). The CET1 ratio is the 'C'."),
    "rwa_density": ("Financial Statement Analysis (financial institutions)", "RWA density (RWA ÷ total assets) shows how risky the balance sheet is in regulatory terms — and how much capital growth will consume."),
    "revenue_mix": ("Financial Statement Analysis (financial institutions)", "Revenue mix (interest vs fee income) drives earnings quality and sensitivity to interest rates — the 'E' and 'S' in CAMELS."),
    "nnm": ("Equity Investments", "Net new money is a leading indicator for wealth managers: it signals future fee income independent of market moves."),
    "insurance_metrics": ("Financial Statement Analysis (insurance)", "Insurer analysis focuses on underwriting (combined ratio), investment returns, reserves, capital (solvency ratio) and liquidity — not on industrial working capital."),
    "statement_links": ("Financial Statement Analysis", "The three statements articulate: net income flows into retained earnings; the cash flow statement reconciles profit to cash; the statement of changes in equity explains every equity movement."),
    "notes": ("Financial Statement Analysis", "The notes disclose accounting policies, estimates and judgements — where most quality-of-earnings red flags hide."),
    "auditor": ("Financial Statement Analysis", "The audit opinion and key audit matters tell you where the auditor saw the highest risk of material misstatement."),
    "quality_earnings": ("Financial Statement Analysis", "Earnings quality: high-quality earnings are sustainable, cash-backed and free of aggressive estimates or one-offs."),
    "accruals": ("Financial Statement Analysis", "Accrual ratio = (net income − operating cash flow) ÷ average assets. Large accruals signal lower earnings persistence — for industrial companies, much less for banks."),
    "one_offs": ("Financial Statement Analysis", "Separate recurring from non-recurring items to estimate 'core' or 'underlying' earnings before forecasting or valuing."),
    "reserves": ("Financial Statement Analysis (insurance)", "Reserve releases or strengthening (prior-year development) change insurer earnings without any new business — a classic earnings-management lever."),
    "risk_credit": ("Fixed Income", "Credit risk = probability of default × loss given default × exposure. Expected credit losses (IFRS 9) are the accounting estimate of it."),
    "risk_market": ("Portfolio Management · Fixed Income", "Market risk covers equity, interest-rate, credit-spread and FX moves; VaR and stress tests quantify it."),
    "risk_interest": ("Fixed Income", "Duration measures price sensitivity to rates. Life insurers worry about asset–liability duration gaps; banks about repricing gaps and NII sensitivity."),
    "risk_liquidity": ("Fixed Income · Financial Statement Analysis", "Banks: LCR and NSFR; insurers: lapse-driven outflows and collateral calls. Liquidity, not solvency, usually kills banks first (e.g. Credit Suisse 2023)."),
    "risk_operational": ("Portfolio Management", "Operational risk: losses from failed processes, people, systems or external events — including conduct and cyber risk."),
    "risk_regulatory": ("Economics · Corporate Issuers", "Capital rules (Basel III, SST, Solvency II) determine how much equity a financial firm must hold — and therefore achievable ROE and payouts."),
    "risk_underwriting": ("Financial Statement Analysis (insurance)", "Underwriting risk: claims or lapses differ from pricing assumptions (catastrophes, mortality, longevity, lapse)."),
    "risk_concentration": ("Portfolio Management", "Concentration risk: exposure to one client, region, sector or peril — the opposite of diversification."),
    "derivatives": ("Derivatives", "Banks and insurers use derivatives (swaps, options) to hedge interest-rate and market risk — hedge accounting can create accounting mismatches."),
    "peers": ("Equity Investments", "Comparable-company analysis only works with truly comparable firms: same business model, accounting basis and currency — compare ratios, not absolute amounts."),
    "pe": ("Equity Investments", "P/E = price ÷ EPS. Use normalised (recurring) earnings — one-offs distort it."),
    "pb": ("Equity Investments", "P/B = price ÷ book value per share. For financials book value is meaningful because assets are mostly financial."),
    "dividend_yield": ("Equity Investments", "Dividend yield = DPS ÷ price. Check sustainability via payout ratio and capital generation."),
    "justified_pb": ("Equity Investments", "Justified P/B = (ROE − g) ÷ (r − g): a firm earning its cost of equity (ROE = r) should trade at book value."),
    "ddm": ("Equity Investments", "Gordon growth model: V₀ = D₁ ÷ (r − g). Appropriate for mature dividend payers — very sensitive to r − g."),
    "residual_income": ("Equity Investments", "Residual income model: value = book value + PV of (ROE − r) × book value. Well suited to financial institutions."),
    "dcf": ("Equity Investments · Corporate Issuers", "FCFF/FCFE DCF suits industrial firms. For banks, debt is raw material, not financing, so use FCFE defined as distributable capital, or DDM/RI."),
    "capm": ("Portfolio Management · Equity", "CAPM: r = r_f + β × equity risk premium — the cost of equity used to discount dividends and residual income."),
    "thesis": ("Equity Investments · Portfolio Management", "An investment thesis states expected value drivers, risks, scenarios and the evidence that would prove it wrong — before any portfolio decision."),
    "portfolio": ("Portfolio Management", "Position decisions depend on your investment policy statement: objectives, risk tolerance, constraints, diversification and the rest of the portfolio."),
}


def note(key: str) -> tuple[str, str] | None:
    return CFA.get(key)
