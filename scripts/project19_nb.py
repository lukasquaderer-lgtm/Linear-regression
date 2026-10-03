"""Project 19: multi-asset portfolio for a Swiss pension fund, with model solution."""
from nb_helpers import md, code, header
from projects_nb import project

F = "19_project_pension_portfolio.ipynb"
SOL = "solutions/" + F.replace(".ipynb", "_solution.ipynb")

LOAD = '''
rets = pd.read_csv(DATA + "asset_returns_daily.csv", index_col=0, parse_dates=True)
assets = list(rets.columns)
BENCH = pd.Series({"CH_EQUITY": 0.20, "WORLD_EQUITY": 0.15, "EM_EQUITY": 0.05, "CHF_BONDS": 0.30,
                   "GLOBAL_BONDS": 0.10, "GOLD": 0.05, "SWISS_REAL_ESTATE": 0.15, "COMMODITIES": 0.00})[assets]
GROUPS = {"equities": ["CH_EQUITY", "WORLD_EQUITY", "EM_EQUITY"], "real estate": ["SWISS_REAL_ESTATE"],
          "alternatives": ["GOLD", "COMMODITIES"]}
LIMITS = {"equities": 0.50, "real estate": 0.30, "alternatives": 0.15}   # inspired by Swiss pension rules (BVV 2)
MAX_SINGLE = 0.35
print(rets.shape, "| current strategic allocation:"); print(BENCH)
'''

CELLS = project(F, "19 · Project: build and defend a pension fund portfolio", """
**Business problem.** The (fictional) Alpstein Pension Fund manages CHF 2 billion for Swiss employees. Its investment
committee asks you to review the current strategic allocation and propose a better one. You must respect the fund's
investment rules, show the risk of both portfolios, and explain your proposal to non-specialists.

**Rules (inspired by Swiss pension regulation, BVV 2):** long-only and fully invested; at most 35% in any single asset;
equities in total at most 50%; real estate at most 30%; gold and commodities (alternatives) together at most 15%.

**Data:** the daily multi-asset returns from notebooks 17–18 (2010–2024). Use notebooks 17 and 18 as your toolbox.
""", LOAD, [
    ("Diagnose the current allocation", "Annual return, volatility, Sharpe ratio (risk-free 0.5%), maximum drawdown, 1-day and 1-month 99% VaR and ES, risk contributions by asset, and the loss in the Feb–Mar 2020 window. Where does its risk really come from?"),
    ("Choose your inputs", "Decide how you will estimate the covariance matrix (sample? shrinkage? which window?) and whether you will use expected returns at all. Justify each choice in two sentences, citing what you learned about estimation error."),
    ("Build your portfolio", "Formulate an optimisation that respects every rule and solve it with `scipy.optimize.minimize`. Candidates: constrained minimum variance, constrained risk parity, maximum diversification, or Black–Litterman. Verify every constraint holds."),
    ("Walk-forward backtest", "Rebalance monthly from 2012 on, using only data available at each rebalancing date (e.g. the previous 2 years), with 0.10% trading costs. Compare your strategy with the current allocation and with 1/N (respecting the rules where possible): return, volatility, Sharpe, maximum drawdown, turnover."),
    ("Risk report for your proposal", "Same metrics as Task 1 for your portfolio, plus a stress test of your own design. Present both portfolios side by side."),
    ("Attribution", "Versus the current allocation: active return, tracking error, information ratio, and an allocation-effect breakdown by asset class."),
    ("Investment committee memo", "One page: the recommendation, the expected change in risk and return, the main risks of the proposal, and what would make you change your mind."),
], [
    ("Rules respected", "15", "Every constraint enforced in the optimiser and verified numerically"),
    ("Input choices justified", "15", "Covariance and return estimates chosen deliberately, with reasons tied to estimation error"),
    ("No look-ahead in the backtest", "20", "Weights at each date use only past data; costs included"),
    ("Risk analysis", "20", "VaR, ES, drawdown, risk contributions and stress tests for both portfolios"),
    ("Attribution", "10", "Active return, tracking error, information ratio and allocation effects"),
    ("Memo", "20", "Clear recommendation a non-specialist can follow, with honest risks"),
], ["Every rule holds for every rebalancing date", "My backtest uses only past data at each date",
    "I compared against the current allocation, not just 1/N", "My memo states numbers and the main risk in plain words"])

SOL_CELLS = header(SOL, "19 · Model solution: pension fund portfolio", """
One reasonable solution. The main design choice: expected returns are too noisy to optimise on (notebook 17, Section 4),
so this solution uses **only the covariance matrix** (Ledoit–Wolf, 2-year window) and compares three rule-compliant
constructions: minimum variance, risk parity and maximum diversification, each capped at the current allocation's risk.
""") + [code(LOAD), code('''
from scipy.optimize import minimize
from scipy import stats
from sklearn.covariance import LedoitWolf
ANN, RF, COST = 252, 0.005, 0.001
idx = {g: [assets.index(a) for a in m] for g, m in GROUPS.items()}

def rule_constraints(vol_cap=None, S=None):
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    for g, lim in LIMITS.items():
        cons.append({"type": "ineq", "fun": lambda w, ix=idx[g], lim=lim: lim - w[ix].sum()})
    if vol_cap is not None:
        cons.append({"type": "ineq", "fun": lambda w: vol_cap ** 2 - w @ S @ w})
    return cons

def solve(obj, S, vol_cap=None, x0=None):
    x0 = BENCH.to_numpy() if x0 is None else x0
    res = minimize(obj, x0, method="SLSQP", bounds=[(0, MAX_SINGLE)] * len(assets),
                   constraints=rule_constraints(vol_cap, S), options={"maxiter": 1000, "ftol": 1e-12})
    return np.clip(res.x, 0, None) / np.clip(res.x, 0, None).sum()

def min_var(S, cap):  return solve(lambda w: w @ S @ w, S, cap)
def max_div(S, cap):
    sd = np.sqrt(np.diag(S)); return solve(lambda w: -(w @ sd) / np.sqrt(w @ S @ w), S, cap)
def risk_par(S, cap):
    def obj(w):
        rc = w * (S @ w) / np.sqrt(w @ S @ w); return ((rc - rc.mean()) ** 2).sum() * 1e4
    return solve(obj, S, cap, x0=np.full(len(assets), 1 / len(assets)))

def check_rules(w):
    w = pd.Series(w, index=assets)
    ok = abs(w.sum() - 1) < 1e-6 and (w >= -1e-9).all() and (w <= MAX_SINGLE + 1e-6).all()
    ok &= all(w[m].sum() <= LIMITS[g] + 1e-6 for g, m in GROUPS.items())
    return bool(ok)
print("current allocation respects the rules:", check_rules(BENCH))
'''), code('''
def risk_report(r, w=None, S=None):
    g = (1 + r).cumprod(); q = np.quantile(r, 0.01)
    rep = {"ann. return": r.mean() * ANN, "ann. vol": r.std() * np.sqrt(ANN), "Sharpe": (r.mean() * ANN - RF) / (r.std() * np.sqrt(ANN)),
           "max drawdown": (g / g.cummax() - 1).min(), "VaR 99% 1-day": -q, "ES 99% 1-day": -r[r <= q].mean(),
           "VaR 99% 1-month (√21)": -q * np.sqrt(21), "Feb–Mar 2020 loss": (1 + r.loc["2020-02-20":"2020-03-16"]).prod() - 1}
    return pd.Series(rep)

S_full = rets.cov().to_numpy() * ANN
b = BENCH.to_numpy()
r_bench_static = rets @ BENCH
rc = b * (S_full @ b) / np.sqrt(b @ S_full @ b)
print("1) Current allocation:"); print(risk_report(r_bench_static).round(4))
print("\\nRisk contributions (share of volatility):"); print(pd.Series(rc / rc.sum(), index=assets).round(3))
'''), md("""
**Task 1 finding:** the three equity sleeves are 40% of the money but around three quarters of the risk; bonds are 40%
of the money and contribute almost nothing. The real question for the committee is therefore how much equity risk to
run, not how to fine-tune the bond split.

**Task 2 choices:** covariance from Ledoit–Wolf on the last 2 years (recent enough to track changing volatility, long
enough to be stable, shrinkage to tame noise). No expected-return estimates: their standard errors (about 4% a year for
equities, notebook 17) are as large as the premiums themselves. Instead, each construction is capped at the current
allocation's volatility so the committee compares like with like.
"""), code('''
# 3) + 4) walk-forward: monthly, 2-year Ledoit-Wolf window, rules enforced at every date
try:
    month_ends = rets.resample("ME").last().index
except ValueError:
    month_ends = rets.resample("M").last().index
LOOK = 504
builders = {"Current allocation": lambda S, cap: b,
            "1/N within rules": lambda S, cap: solve(lambda w: ((w - 1 / len(assets)) ** 2).sum(), S),
            "Min variance": min_var, "Risk parity": risk_par, "Max diversification": max_div}
paths = {k: [] for k in builders}; weights = {k: [] for k in builders}; turnover = {k: [] for k in builders}; prev = {k: np.zeros(len(assets)) for k in builders}
for i, me in enumerate(month_ends[:-1]):
    hist = rets.loc[:me].iloc[-LOOK:]
    if len(hist) < LOOK or me < pd.Timestamp("2012-01-01"):
        continue
    S = LedoitWolf().fit(hist.to_numpy()).covariance_ * ANN
    cap = np.sqrt(b @ S @ b)                                    # never riskier than the current allocation (ex ante)
    nxt = rets.loc[(rets.index > me) & (rets.index <= month_ends[i + 1])]
    for k, f in builders.items():
        w = f(S, cap); assert check_rules(w), (k, me)
        r = nxt.to_numpy() @ w; t = np.abs(w - prev[k]).sum(); r[0] -= COST * t
        paths[k].append(pd.Series(r, index=nxt.index)); weights[k].append(pd.Series(w, index=assets, name=me)); turnover[k].append(t); prev[k] = w
R = pd.DataFrame({k: pd.concat(v) for k, v in paths.items()})
table = R.apply(risk_report).T; table["avg monthly turnover"] = {k: np.mean(v[1:]) for k, v in turnover.items()}
print("4) Walk-forward 2012-2024, all rules enforced at every rebalancing:"); print(table.round(4))
(1 + R).cumprod().plot(figsize=(10, 4), title="Growth of 1, out of sample"); plt.show()
'''), md("""
**Choosing:** write the decision rule down *before* looking at the results, and include the current allocation as a
candidate. Here the rule is: recommend a change only if a new construction beats the current allocation's Sharpe ratio
without a deeper maximum drawdown. Otherwise the honest recommendation is to keep the current allocation, possibly
with a smaller, well-understood tilt. Simplification to note in the memo: returns assume the target weights are held
daily, and costs are charged only at the monthly rebalancing.
"""), code('''
# 5) apply the decision rule stated above
cands = ["Min variance", "Risk parity", "Max diversification"]
best = table.loc[cands, "Sharpe"].idxmax()
cur = table.loc["Current allocation"]
switch = table.loc[best, "Sharpe"] > cur["Sharpe"] and table.loc[best, "max drawdown"] >= cur["max drawdown"]
pick = best        # analysed below either way, so the committee sees the trade-off
print(f"Best new construction: {best} | beats current allocation on the rule: {switch}")
W_hist = pd.DataFrame(weights[pick]); w_now = W_hist.iloc[-1]
print(f"5) Best alternative analysed: {pick}. Latest weights (rules OK: {check_rules(w_now)}):"); print(w_now.round(3))
side = pd.DataFrame({"Current allocation": table.loc["Current allocation"], pick: table.loc[pick]})
custom = {"CHF +15% shock (foreign assets −15%, CHF assets −2%)": pd.Series({a: (-0.02 if a in ["CH_EQUITY", "CHF_BONDS", "SWISS_REAL_ESTATE"] else -0.15) for a in assets})}
for name, s in custom.items():
    side.loc[name] = [s @ BENCH, s @ w_now]
print(side.round(4))
W_hist.plot.area(figsize=(10, 3.5), title=f"{pick}: weights over time"); plt.legend(bbox_to_anchor=(1, 1)); plt.show()
'''), code('''
# 6) attribution versus the current allocation
active = R[pick] - R["Current allocation"]
te = active.std() * np.sqrt(ANN); ir = active.mean() * ANN / te
print(f"6) active return {active.mean() * ANN:.2%} a year | tracking error {te:.2%} | information ratio {ir:.2f}")
avg_w = W_hist.mean()
period = R.index
asset_ret = (1 + rets.loc[period]).prod() ** (ANN / len(period)) - 1           # annualised asset returns over the test period
Rb = BENCH @ asset_ret
alloc = (avg_w - BENCH) * (asset_ret - Rb)
print("Allocation effect by asset (average active weight × (asset return − benchmark return)):"); print(alloc.round(4))
print(f"sum of allocation effects ≈ {alloc.sum():.2%} a year (selection is zero: both portfolios hold the same asset-class indices)")
'''), md("### 7) Investment committee memo\nGenerated from the results above, so it stays honest if you change the data or the settings."),
code('''
c, p_ = table.loc["Current allocation"], table.loc[pick]
eq_risk = (rc / rc.sum())[[assets.index(a) for a in GROUPS["equities"]]].sum()
if switch:
    rec = (f"Replace the current allocation with a rule-based {pick} portfolio, rebalanced monthly from a two-year risk "
           f"estimate. Out of sample (2012-2024) it improved the Sharpe ratio from {c['Sharpe']:.2f} to {p_['Sharpe']:.2f} "
           f"without a deeper drawdown.")
else:
    rec = (f"Keep the current strategic allocation. The best risk-based alternative ({pick}) cut volatility from "
           f"{c['ann. vol']:.1%} to {p_['ann. vol']:.1%} and the Feb-Mar 2020 loss from {c['Feb–Mar 2020 loss']:.1%} to "
           f"{p_['Feb–Mar 2020 loss']:.1%}, but annual return fell from {c['ann. return']:.1%} to {p_['ann. return']:.1%} "
           f"and the Sharpe ratio from {c['Sharpe']:.2f} to {p_['Sharpe']:.2f}. Lower risk was paid for with too much return, "
           f"because the extra bonds earned almost nothing.")
memo = f"""INVESTMENT COMMITTEE MEMO - Strategic allocation review

Recommendation: {rec}

Today's risk: equities are 40% of assets but {eq_risk:.0%} of portfolio volatility. 1-day 99% VaR is {c['VaR 99% 1-day']:.2%}
(about CHF {c['VaR 99% 1-day'] * 2e9 / 1e6:.0f} million on CHF 2 billion); the worst drawdown since 2012 was {c['max drawdown']:.1%}.

Options if the board wants less risk: a partial move toward {pick} (for example halfway) lowers volatility and stress
losses at a known cost in expected return; the table above quantifies both ends.

Main risks of the analysis: one 13-year sample, simulated data, returns that assume daily rebalancing. Before any change,
re-test with 1- and 3-year estimation windows and with real index data."""
print(memo)
''')]
