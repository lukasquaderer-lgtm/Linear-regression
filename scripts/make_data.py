"""Generate the practice datasets in ../data.

All data is SIMULATED with a fixed seed so results are reproducible.
The data-generating processes mimic real financial data closely enough
to practise every CFA Level II quantitative technique.

Run:  python scripts/make_data.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

SEEDS = {"main": 42, "macro": 2024, "fx": 5}
rng = np.random.default_rng(SEEDS["main"])
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)


# 1. Monthly factor returns + one stock + one fund  (regression, CAPM, factor models)
n = 120
dates = pd.period_range("2015-01", periods=n, freq="M").astype(str)
mkt = rng.normal(0.7, 4.3, n)            # market excess return, %
smb = rng.normal(0.1, 2.6, n) + 0.15 * mkt
hml = rng.normal(0.0, 2.9, n) - 0.10 * mkt
mom = rng.normal(0.5, 3.8, n) - 0.20 * hml
rf = np.round(np.clip(0.05 + np.cumsum(rng.normal(0, 0.02, n)), 0, None), 3)
stock = 0.2 + 1.25 * mkt + rng.normal(0, 5.0, n)
# fund: real exposures + volatility rising with market moves (heteroskedasticity)
fund = 0.1 + 0.95 * mkt + 0.45 * smb + 0.30 * hml + rng.normal(0, 1, n) * 1.1 * np.exp(0.17 * mkt)
pd.DataFrame({"month": dates, "rf": rf, "mkt_excess": mkt.round(3), "smb": smb.round(3),
              "hml": hml.round(3), "mom": mom.round(3),
              "stock_excess": stock.round(3), "fund_excess": fund.round(3)}).to_csv(OUT / "factor_returns.csv", index=False)

# 2. Quarterly macro / market series  (time series)
rng = np.random.default_rng(SEEDS["macro"])
T = 120
q = pd.period_range("1996Q1", periods=T, freq="Q").astype(str)
t = np.arange(1, T + 1)
g = np.empty(T); g[:4] = [-0.05, 0.02, 0.01, 0.07]
for i in range(4, T):                                                          # seasonal AR in quarterly growth
    g[i] = 0.0036 + 0.75 * g[i - 4] + rng.normal(0, 0.008)
retail_sales = 100 * np.exp(np.cumsum(g))                                      # exponential growth + seasonality
infl = np.empty(T); infl[0] = 2.5
for i in range(1, T):                                                          # AR(1): MRL = 0.6/(1-0.75) = 2.4
    infl[i] = 0.6 + 0.75 * infl[i - 1] + rng.normal(0, 0.45)
rfx = np.random.default_rng(SEEDS["fx"])
fx = 1.20 + np.concatenate([[0], np.cumsum(rfx.normal(0, 0.03, T - 1))])        # random walk
eps = np.empty(T); h = np.empty(T); eps[0] = 0.0
for i in range(T):                                                             # ARCH(1) returns
    h[i] = 4.0 + 0.6 * (eps[i - 1] ** 2 if i else 0)
    eps[i] = np.sqrt(h[i]) * rng.normal()
index_return = 1.8 + eps
x_price = 50 + np.cumsum(rng.normal(0.2, 1.5, T))                              # unit-root series
y_price = 5 + 0.8 * x_price + rng.normal(0, 1.2, T)                            # cointegrated with x
z_price = 40 + np.cumsum(rng.normal(0.1, 1.5, T))                              # independent unit-root series
pd.DataFrame({"quarter": q, "t": t, "retail_sales": retail_sales.round(2), "inflation": infl.round(3),
              "fx_rate": fx.round(4), "index_return": index_return.round(3),
              "oil_price": x_price.round(2), "energy_stock": y_price.round(2),
              "gold_price": z_price.round(2)}).to_csv(OUT / "macro_quarterly.csv", index=False)

# 3. Treasury yield curves  (PCA)
rng = np.random.default_rng(SEEDS["main"] + 3)
m = 240
mats = ["3m", "1y", "2y", "3y", "5y", "7y", "10y", "20y", "30y"]
tau = np.array([0.25, 1, 2, 3, 5, 7, 10, 20, 30])
lam = 0.6
slope_load = (1 - np.exp(-lam * tau)) / (lam * tau)
curv_load = slope_load - np.exp(-lam * tau)
L = np.empty(m); S = np.empty(m); C = np.empty(m)
L[0], S[0], C[0] = 4.0, -1.5, 0.5
for i in range(1, m):
    L[i] = 0.05 + 0.988 * L[i - 1] + rng.normal(0, 0.20)
    S[i] = -0.02 + 0.97 * S[i - 1] + rng.normal(0, 0.25)
    C[i] = 0.98 * C[i - 1] + rng.normal(0, 0.35)
Y = L[:, None] + S[:, None] * slope_load + C[:, None] * curv_load + rng.normal(0, 0.03, (m, 9))
ydf = pd.DataFrame(Y.round(3), columns=[f"y_{c}" for c in mats])
ydf.insert(0, "month", pd.period_range("2005-01", periods=m, freq="M").astype(str))
ydf.to_csv(OUT / "treasury_yields.csv", index=False)

# 4. Credit default data  (logistic, KNN, SVM, trees, evaluation)
N = 800
income = np.round(rng.lognormal(np.log(65), 0.45, N), 1)                       # $000s
dti = np.round(np.clip(rng.normal(32, 11, N), 2, 75), 1)                       # debt-to-income %
fico = np.round(np.clip(rng.normal(690, 55, N), 500, 850)).astype(int)
ltv = np.round(np.clip(rng.normal(75, 14, N), 20, 120), 1)
years_job = np.round(np.clip(rng.exponential(5, N), 0, 35), 1)
home_owner = rng.binomial(1, 0.55, N)
purpose = rng.choice(["debt_consolidation", "home_improvement", "small_business", "auto"], N, p=[0.45, 0.2, 0.15, 0.2])
z = (-1.4 - 0.022 * (fico - 690) + 0.045 * (dti - 32) + 0.03 * (ltv - 75) - 0.008 * (income - 65)
     - 0.05 * years_job - 0.35 * home_owner + 0.9 * (purpose == "small_business")
     + 0.0012 * (dti - 32) ** 2)                                               # mild non-linearity
default = rng.binomial(1, 1 / (1 + np.exp(-z)))
pd.DataFrame({"income_k": income, "debt_to_income": dti, "fico": fico, "loan_to_value": ltv,
              "years_employed": years_job, "home_owner": home_owner, "purpose": purpose,
              "default": default}).to_csv(OUT / "credit_default.csv", index=False)

# 5. Company fundamentals  (clustering)
groups = {  # name: (rev_growth, op_margin, pe, div_yield, beta, debt_equity)
    "growth_tech": (22, 24, 38, 0.3, 1.35, 0.3),
    "utilities": (3, 18, 17, 3.8, 0.55, 1.6),
    "banks": (6, 32, 11, 3.0, 1.10, 2.5),
    "consumer_staples": (4, 15, 22, 2.6, 0.70, 0.9),
    "energy": (8, 12, 9, 4.5, 1.25, 0.7),
}
rows = []
spread = np.array([5, 4, 5, 0.6, 0.15, 0.3])
for g, mu in groups.items():
    for i in range(30):
        v = np.array(mu) + rng.normal(0, 1, 6) * spread
        rows.append([f"{g[:3].upper()}{i + 1:02d}", *np.round(v, 2), g])
cols = ["ticker", "revenue_growth", "operating_margin", "pe_ratio", "dividend_yield", "beta", "debt_to_equity", "true_sector"]
comp = pd.DataFrame(rows, columns=cols).sample(frac=1, random_state=1).reset_index(drop=True)
comp["dividend_yield"] = comp["dividend_yield"].clip(lower=0)
comp.to_csv(OUT / "company_fundamentals.csv", index=False)

# 6. Financial headlines  (text / NLP)
pos = ["beats estimates", "raises guidance", "record revenue", "strong demand", "margin expansion",
       "upgraded to buy", "dividend increase", "share buyback", "profit surges", "wins major contract"]
neg = ["misses estimates", "cuts guidance", "revenue decline", "weak demand", "margin pressure",
       "downgraded to sell", "dividend cut", "faces lawsuit", "profit falls", "loses key customer"]
neu = ["announces conference call", "files quarterly report", "appoints new director", "schedules earnings date",
       "completes debt offering", "holds annual meeting"]
cos = ["Acme Corp", "Globex", "Initech", "Umbrella Inc", "Stark Industries", "Wayne Enterprises", "Hooli", "Vandelay"]
extra_pos = ["as cloud sales grow", "on solid quarter", "after strong holiday season", "amid robust orders"]
extra_neg = ["as costs rise", "amid slowing sales", "after weak quarter", "on supply problems"]
extra_neu = ["for next quarter", "this week", "in New York", "as planned"]
hl = []
for _ in range(300):
    s = rng.choice(["positive", "negative", "neutral"], p=[0.4, 0.4, 0.2])
    c = rng.choice(cos)
    if s == "positive":
        txt = f"{c} {rng.choice(pos)} {rng.choice(extra_pos)}"
    elif s == "negative":
        txt = f"{c} {rng.choice(neg)} {rng.choice(extra_neg)}"
    else:
        txt = f"{c} {rng.choice(neu)} {rng.choice(extra_neu)}"
    if rng.random() < 0.08:  # label noise, like real annotated data
        s = rng.choice(["positive", "negative", "neutral"])
    hl.append([txt, s])
pd.DataFrame(hl, columns=["headline", "sentiment"]).to_csv(OUT / "headlines.csv", index=False)

# 7. Monthly stock prices for the capstone (fallback when Yahoo Finance is unavailable)
rng = np.random.default_rng(SEEDS["main"] + 7)
months = pd.date_range("2010-01-31", periods=180, freq="ME")
sectors = {"BANK": "Financials", "PHARMA": "Health care", "FOOD": "Consumer staples", "TECH": "Technology", "INDU": "Industrials"}
names = [f"{s}{i}" for s in sectors for i in range(1, 5)]
Tm = len(months)
h = np.empty(Tm); e = np.empty(Tm); h[0] = 0.0016
for i in range(Tm):                                    # GARCH-style market volatility
    if i:
        h[i] = 0.00012 + 0.12 * e[i - 1] ** 2 + 0.80 * h[i - 1]
    e[i] = np.sqrt(h[i]) * rng.normal()
mkt_r = 0.007 + e
sec_f = {s: rng.normal(0, 0.03, Tm) for s in sectors}
beta_by_sector = {"BANK": 1.25, "PHARMA": 0.70, "FOOD": 0.60, "TECH": 1.45, "INDU": 1.10}
rets = {}
past = np.zeros((Tm, len(names)))
for j, nm in enumerate(names):
    sec = nm.rstrip("1234")
    b = beta_by_sector[sec] + rng.normal(0, 0.12)
    idio = 0.03 + rng.uniform(0, 0.02)
    r = 0.001 + b * mkt_r + sec_f[sec] + rng.normal(0, idio, Tm)
    rets[nm] = r
R = pd.DataFrame(rets, index=months)
mom = (1 + R).rolling(11).apply(np.prod, raw=True).shift(2) - 1          # 12-1 momentum known at t-1
R = R + 0.006 * mom.sub(mom.mean(axis=1), axis=0).fillna(0)               # small momentum premium
prices = 100 * (1 + R).cumprod()
prices.loc[: "2018-12-31", "TECH4"] = np.nan                            # a later listing, like real data
prices.insert(0, "INDEX", (1000 * (1 + mkt_r).cumprod()).round(2))
prices.round(2).rename_axis("date").to_csv(OUT / "capstone_prices.csv")
pd.DataFrame({"ticker": names, "sector": [sectors[n.rstrip("1234")] for n in names]}).to_csv(OUT / "capstone_sectors.csv", index=False)

# 8. Daily multi-asset returns (portfolio construction and risk)
rng = np.random.default_rng(SEEDS["main"] + 8)
assets = ["CH_EQUITY", "WORLD_EQUITY", "EM_EQUITY", "CHF_BONDS", "GLOBAL_BONDS", "GOLD", "SWISS_REAL_ESTATE", "COMMODITIES"]
mu_a = np.array([0.07, 0.08, 0.08, 0.01, 0.02, 0.05, 0.05, 0.03])          # annual expected returns
vol_a = np.array([0.15, 0.16, 0.21, 0.04, 0.05, 0.15, 0.12, 0.20])         # annual volatilities
corr = np.array([
    [1.00, 0.85, 0.70, 0.05, 0.10, 0.05, 0.45, 0.35],
    [0.85, 1.00, 0.80, 0.00, 0.05, 0.05, 0.40, 0.40],
    [0.70, 0.80, 1.00, 0.00, 0.05, 0.15, 0.35, 0.50],
    [0.05, 0.00, 0.00, 1.00, 0.70, 0.20, 0.30, -0.10],
    [0.10, 0.05, 0.05, 0.70, 1.00, 0.25, 0.25, -0.05],
    [0.05, 0.05, 0.15, 0.20, 0.25, 1.00, 0.10, 0.35],
    [0.45, 0.40, 0.35, 0.30, 0.25, 0.10, 1.00, 0.20],
    [0.35, 0.40, 0.50, -0.10, -0.05, 0.35, 0.20, 1.00]])
L = np.linalg.cholesky(corr)
days = pd.bdate_range("2010-01-04", "2024-12-31")
nd = len(days)
h = np.empty(nd); h[0] = 1.0; shock = 0.0
for i in range(1, nd):                                   # common GARCH-style volatility regime
    h[i] = 0.02 + 0.08 * shock ** 2 + 0.90 * h[i - 1]
    shock = rng.standard_t(5) / np.sqrt(5 / 3)
crisis = (days >= "2020-02-20") & (days <= "2020-04-15")    # a pandemic-style shock window
h[crisis] *= 4
scale = np.sqrt(h / h.mean())
z = rng.standard_t(5, size=(nd, len(assets))) / np.sqrt(5 / 3) @ L.T     # fat-tailed, correlated
equity_like = np.array([1, 1, 1, 0, 0, 0, 0.6, 0.7])
regime = scale[:, None] * equity_like + (1 - equity_like) * (0.5 + 0.5 * scale[:, None])
daily = mu_a / 252 + z * regime * vol_a / np.sqrt(252)
crash = (days >= "2020-02-20") & (days <= "2020-03-16")
rebound = (days > "2020-03-16") & (days <= "2020-04-15")
daily[crash] += np.array([-0.014, -0.014, -0.015, 0.0003, 0.0002, -0.002, -0.009, -0.012])   # sell-off
daily[rebound] += np.array([0.006, 0.007, 0.006, 0.0, 0.0001, 0.002, 0.004, 0.002])          # partial recovery
ar = pd.DataFrame(daily, index=days, columns=assets).round(6)
ar.rename_axis("date").to_csv(OUT / "asset_returns_daily.csv")

# 9. Messy raw market data (data wrangling and SQL): realistic problems on purpose
rng = np.random.default_rng(SEEDS["main"] + 9)
MESSY = OUT / "messy"; MESSY.mkdir(exist_ok=True)
bdays = pd.bdate_range("2015-01-02", "2024-12-31")
spec = {  # permanent id: (currency, start price, beta, annual dividend yield, listed from, delisted on)
    "ALPN": ("CHF", 60, 1.0, 0.030, None, None), "BRGN": ("CHF", 180, 0.7, 0.025, None, None),
    "CRYS": ("CHF", 25, 1.3, 0.040, None, "2023-06-09"), "DELT": ("EUR", 75, 1.1, 0.020, None, None),
    "EDLW": ("CHF", 95, 0.6, 0.035, None, None), "FJRD": ("USD", 40, 1.2, 0.015, None, None),
    "GLAC": ("CHF", 30, 1.4, 0.000, "2018-03-01", None), "HELV": ("CHF", 110, 0.9, 0.028, None, None),
    "IBEX": ("EUR", 150, 1.0, 0.022, None, None), "JURA": ("CHF", 1150, 0.8, 0.018, None, None)}
splits = {("BRGN", "2019-05-15"): 2.0, ("IBEX", "2021-07-01"): 3.0}
mkt = rng.normal(0.0003, 0.010, len(bdays))
rows, actions = [], []
for tk, (ccy, p0, beta, dy, start, end) in spec.items():
    days = bdays[(bdays >= (start or "1900")) & (bdays <= (end or "2100"))]
    m = pd.Series(mkt, index=bdays).loc[days].to_numpy()
    r = 0.0002 + beta * m + rng.normal(0, 0.012, len(days))              # daily total return
    if tk == "CRYS":                                                     # most delistings follow a long decline
        r = r - 0.0015 * (days >= pd.Timestamp("2020-06-01"))
    ex_dates = set()
    if dy > 0:
        for yr in range(2015, 2025):
            cands = days[(days >= f"{yr}-05-02")]
            if len(cands) and cands[0].year == yr:
                ex_dates.add(cands[0])
    close, prev = [], p0
    for d, rt in zip(days, r):
        div = round(prev * dy, 2) if d in ex_dates else 0.0
        ratio = splits.get((tk, str(d.date())), 1.0)
        px = (prev * (1 + rt) - div) / ratio
        name = "HLVT" if (tk == "HELV" and d < pd.Timestamp("2021-01-04")) else tk   # vendor files use the ticker of the day
        if div:
            actions.append([name, d.date(), "dividend", div])
        if ratio != 1.0:
            actions.append([name, d.date(), "split", ratio])
        close.append(px); prev = px
    vol = rng.integers(20_000, 400_000, len(days))
    for d, c, v in zip(days, close, vol):
        shown = "HLVT" if (tk == "HELV" and d < pd.Timestamp("2021-01-04")) else tk     # ticker change
        rows.append([d.date(), shown, round(c, 2), int(v), ccy])
raw = pd.DataFrame(rows, columns=["date", "ticker", "close", "volume", "currency"])
raw = raw.sample(frac=0.99, random_state=1).sort_values(["date", "ticker"])          # ~1% of rows missing
raw["close"] = raw["close"].astype(object)
for i in raw.index[(raw["ticker"] == "JURA").to_numpy()][::20]:                     # Swiss thousands separator
    raw.at[i, "close"] = f"{raw.at[i, 'close']:,.2f}".replace(",", "'")
for i in rng.choice(raw.index, 8, replace=False):                                    # blank prices
    raw.at[i, "close"] = ""
for tk, d in [("DELT", "2017-03-14"), ("FJRD", "2020-11-02"), ("EDLW", "2022-08-17")]:  # bad ticks: decimal errors
    j = raw.index[(raw["ticker"] == tk) & (raw["date"].astype(str) == d)]
    if len(j):
        raw.at[j[0], "close"] = round(float(raw.at[j[0], "close"]) * 100, 2)
raw = pd.concat([raw, raw.sample(n=60, random_state=2)]).sort_values(["date", "ticker"])   # duplicate rows
raw.to_csv(MESSY / "prices_raw.csv", index=False)
pd.DataFrame(actions, columns=["ticker", "ex_date", "action", "value"]).sort_values("ex_date").to_csv(MESSY / "corporate_actions.csv", index=False)
pd.DataFrame([["HLVT", "HELV", "2021-01-04"]], columns=["old_ticker", "new_ticker", "effective_date"]).to_csv(MESSY / "ticker_changes.csv", index=False)
fx = pd.DataFrame({"date": bdays.date,
                   "EURCHF": (1.07 * np.exp(np.cumsum(rng.normal(-0.00005, 0.004, len(bdays))))).round(4),
                   "USDCHF": (0.97 * np.exp(np.cumsum(rng.normal(-0.00003, 0.005, len(bdays))))).round(4)})
fx.sample(frac=0.97, random_state=3).sort_values("date").to_csv(MESSY / "fx_rates.csv", index=False)  # gaps
fund = []
for tk, (ccy, p0, *_rest) in spec.items():
    shares = 100e6
    for yr in range(2014, 2024):
        if tk == "GLAC" and yr < 2018: continue
        if tk == "CRYS" and yr > 2022: continue
        if tk == "BRGN" and yr >= 2019: shares = 200e6
        if tk == "IBEX" and yr >= 2021: shares = 300e6
        ni = shares * p0 / 16 * (1 + rng.normal(0.05, 0.15)) * (1 + 0.04 * (yr - 2014))
        rep = pd.Timestamp(f"{yr + 1}-03-01") + pd.Timedelta(days=int(rng.integers(0, 45)))
        name = "HLVT" if (tk == "HELV" and rep < pd.Timestamp("2021-01-04")) else tk
        fund.append([name, f"{yr}-12-31", rep.date(), ccy, round(ni / 1e6, 1), shares / 1e6])
pd.DataFrame(fund, columns=["ticker", "fiscal_year_end", "report_date", "currency", "net_income_m", "shares_m"]).to_csv(MESSY / "fundamentals.csv", index=False)
pd.DataFrame([[tk, (s or "2015-01-02"), (e or "")] for tk, (c, p, b, d, s, e) in spec.items()],
             columns=["ticker", "start_date", "end_date"]).to_csv(MESSY / "index_membership.csv", index=False)

print("Wrote:", *sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*.csv")))
