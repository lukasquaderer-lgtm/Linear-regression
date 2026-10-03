"""Build (and optionally execute) the practice notebooks in ../notebooks.

    python scripts/build_notebooks.py            # write notebooks
    python scripts/build_notebooks.py --execute  # write and run them, saving outputs
"""
import sys
from pathlib import Path
import nbformat as nbf
from nb_helpers import md, code, header, exercise, build

NB = Path(__file__).resolve().parent.parent / "notebooks"
NB.mkdir(exist_ok=True)
notebooks = {}

# --------------------------------------------------------------------------------------------
f = "00_python_quickstart.ipynb"
notebooks[f] = header(f, "00 · Python quick-start for quant finance", """
Never written Python? Start here. Fifteen minutes and you will be able to load a dataset,
explore it and make a chart, which is everything the other notebooks build on.

**How to use a notebook:** click a grey code cell and press **Shift + Enter** to run it.
Output appears underneath. Cells run top to bottom; if something breaks, use *Runtime → Restart and run all*
(Colab) or *Kernel → Restart & Run All* (Jupyter).
""") + [
    md("## 1. Variables, arithmetic and printing"),
    code('''
    price_buy = 100.0
    price_sell = 112.5
    dividend = 2.0
    holding_period_return = (price_sell - price_buy + dividend) / price_buy
    print("HPR =", holding_period_return)
    print(f"HPR = {holding_period_return:.2%}")   # f-strings format numbers nicely
    '''),
    md("## 2. Lists, loops and functions"),
    code('''
    returns = [0.05, -0.02, 0.03, 0.04, -0.01]

    def geometric_mean(rs):
        growth = 1.0
        for r in rs:
            growth *= (1 + r)
        return growth ** (1 / len(rs)) - 1

    print("Arithmetic mean:", sum(returns) / len(returns))
    print("Geometric mean: ", round(geometric_mean(returns), 5))
    '''),
    md("## 3. NumPy: fast maths on whole arrays\nNo loops needed: operations apply element by element."),
    code('''
    r = np.array(returns)
    print("mean", r.mean(), "| std (sample)", r.std(ddof=1))
    print("cumulative growth of $1:", np.cumprod(1 + r))
    '''),
    md("## 4. pandas: load a dataset\n`pd.read_csv` returns a **DataFrame**, a table with named columns."),
    code('''
    df = pd.read_csv(DATA + "factor_returns.csv")
    df.head()
    '''),
    code('''
    df.describe()            # count, mean, std, min, quartiles, max for each column
    '''),
    md("## 5. Select, filter and create columns"),
    code('''
    print(df["stock_excess"].mean())                 # one column
    down_months = df[df["mkt_excess"] < 0]            # filter rows
    print("Down months:", len(down_months), "| avg stock return in them:", down_months["stock_excess"].mean().round(3))
    df["stock_total"] = df["stock_excess"] + df["rf"]  # new column
    df[["month", "stock_excess", "rf", "stock_total"]].head()
    '''),
    md("## 6. Plot"),
    code('''
    fig, ax = plt.subplots()
    ax.scatter(df["mkt_excess"], df["stock_excess"], alpha=0.6)
    ax.set_xlabel("Market excess return (%)"); ax.set_ylabel("Stock excess return (%)")
    ax.set_title("Each dot is one month")
    plt.show()
    '''),
    md("## 7. Correlation matrix"),
    code('''
    df[["mkt_excess", "smb", "hml", "mom", "stock_excess"]].corr().round(2)
    '''),
    *exercise(1, "Compute the **annualised** mean (×12) and annualised standard deviation (×√12) of `mkt_excess`.",
              "`df['mkt_excess'].mean() * 12` and `df['mkt_excess'].std() * np.sqrt(12)`"),
    *exercise(2, "How many months did the stock beat the market (`stock_excess > mkt_excess`)? What fraction is that?",
              "A comparison gives True/False values; `.sum()` counts the Trues and `.mean()` gives the fraction."),
    *exercise(3, "Load `macro_quarterly.csv` and plot `inflation` against `quarter` as a line chart.",
              "`m = pd.read_csv(DATA + 'macro_quarterly.csv')` then `plt.plot(m['t'], m['inflation'])`"),
    md("---\n## Solutions"),
    code('''
    # Exercise 1
    print("Annualised mean:", df["mkt_excess"].mean() * 12, "| annualised std:", df["mkt_excess"].std() * np.sqrt(12))
    # Exercise 2
    beat = df["stock_excess"] > df["mkt_excess"]
    print("Months beating market:", beat.sum(), "fraction:", round(beat.mean(), 3))
    # Exercise 3
    m = pd.read_csv(DATA + "macro_quarterly.csv")
    plt.plot(m["t"], m["inflation"]); plt.xlabel("quarter number"); plt.ylabel("inflation %"); plt.show()
    '''),
]

# --------------------------------------------------------------------------------------------
f = "01_simple_linear_regression.ipynb"
notebooks[f] = header(f, "01 · Simple linear regression: estimating a stock’s beta", """
**Goal:** estimate the CAPM beta of a stock by regressing its monthly excess return on the market’s excess
return, first **by hand with the CFA formulas**, then with `statsmodels` to check every number.

Dataset: `factor_returns.csv` (120 simulated months).
""") + [
    code('''
    df = pd.read_csv(DATA + "factor_returns.csv")
    X = df["mkt_excess"].to_numpy()
    Y = df["stock_excess"].to_numpy()
    n = len(Y)
    print("n =", n)
    '''),
    md(r"""
    ## Step 1. Slope and intercept from the formulas
    $\hat b_1 = \dfrac{\sum (X_i-\bar X)(Y_i-\bar Y)}{\sum (X_i-\bar X)^2}, \qquad \hat b_0 = \bar Y - \hat b_1 \bar X$
    """),
    code('''
    x_bar, y_bar = X.mean(), Y.mean()
    b1 = ((X - x_bar) * (Y - y_bar)).sum() / ((X - x_bar) ** 2).sum()
    b0 = y_bar - b1 * x_bar
    print(f"beta (b1) = {b1:.4f},  alpha (b0) = {b0:.4f}")
    '''),
    md(r"""
    ## Step 2. Variance decomposition: SST = SSR + SSE
    """),
    code('''
    Y_hat = b0 + b1 * X
    resid = Y - Y_hat
    SST = ((Y - y_bar) ** 2).sum()
    SSR = ((Y_hat - y_bar) ** 2).sum()
    SSE = (resid ** 2).sum()
    R2 = SSR / SST
    SEE = np.sqrt(SSE / (n - 2))
    print(f"SST={SST:.1f}  SSR={SSR:.1f}  SSE={SSE:.1f}  (SSR+SSE={SSR+SSE:.1f})")
    print(f"R^2 = {R2:.4f}   SEE = {SEE:.4f}   check: corr^2 = {np.corrcoef(X, Y)[0,1]**2:.4f}")
    '''),
    md("## Step 3. Is the slope significant? t-test with n − 2 degrees of freedom"),
    code('''
    from scipy import stats
    s_b1 = SEE / np.sqrt(((X - x_bar) ** 2).sum())
    t_stat = (b1 - 0) / s_b1
    t_crit = stats.t.ppf(0.975, df=n - 2)
    p_val = 2 * (1 - stats.t.cdf(abs(t_stat), df=n - 2))
    print(f"s_b1 = {s_b1:.4f}, t = {t_stat:.2f}, critical t = {t_crit:.3f}, p = {p_val:.2e}")
    print("Reject H0: b1 = 0" if abs(t_stat) > t_crit else "Fail to reject H0")
    '''),
    md("## Step 4. ANOVA table and the F-statistic (F = t² in simple regression)"),
    code('''
    MSR, MSE = SSR / 1, SSE / (n - 2)
    anova = pd.DataFrame({"df": [1, n - 2, n - 1], "SS": [SSR, SSE, SST], "MS": [MSR, MSE, np.nan]},
                         index=["Regression", "Error", "Total"])
    print(anova.round(3)); print("F =", round(MSR / MSE, 3), "| t^2 =", round(t_stat ** 2, 3))
    '''),
    md("## Step 5. Same thing in two lines with statsmodels\nAlways add a constant: `sm.add_constant` creates the intercept column."),
    code('''
    model = sm.OLS(df["stock_excess"], sm.add_constant(df["mkt_excess"])).fit()
    print(model.summary())
    '''),
    md("## Step 6. Plot the fit and the residuals"),
    code('''
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].scatter(X, Y, alpha=0.5); xs = np.linspace(X.min(), X.max(), 50)
    ax[0].plot(xs, b0 + b1 * xs, color="C1", lw=2); ax[0].set_title(f"Y = {b0:.2f} + {b1:.2f} X")
    ax[1].scatter(X, resid, alpha=0.5); ax[1].axhline(0, color="k", lw=1); ax[1].set_title("Residuals vs X")
    plt.show()
    '''),
    md("## Step 7. Prediction interval for a −5% market month"),
    code('''
    new = pd.DataFrame({"const": [1.0], "mkt_excess": [-5.0]})
    pred = model.get_prediction(new).summary_frame(alpha=0.05)
    pred[["mean", "obs_ci_lower", "obs_ci_upper"]]   # obs_ci = prediction interval for a single new Y
    '''),
    *exercise(1, "Regress `fund_excess` on `mkt_excess`. Report the beta, its t-statistic and R².",
              "Copy Step 5 and change the column name."),
    *exercise(2, "For the **stock**, test H₀: β = 1 against H₁: β ≠ 1 at the 5% level. Compute t by hand using `b1` and `s_b1` from above.",
              "t = (b1 − 1) / s_b1, then compare with `t_crit`. Or use `model.t_test('mkt_excess = 1')`."),
    *exercise(3, "What is the 95% prediction interval for the stock’s excess return when the market returns **+8%**? Why is it wider than the interval at the mean of X?"),
    *exercise(4, "Run a log-log style check: does the scatter look linear? What would a log transformation do here (hint: returns can be negative)?"),
    md("---\n## Solutions"),
    code('''
    # 1
    fm = sm.OLS(df["fund_excess"], sm.add_constant(df["mkt_excess"])).fit()
    print("beta", round(fm.params["mkt_excess"], 4), "t", round(fm.tvalues["mkt_excess"], 2), "R2", round(fm.rsquared, 4))
    # 2
    t_beta1 = (b1 - 1) / s_b1
    print("t for H0 beta=1:", round(t_beta1, 3), "->", "reject" if abs(t_beta1) > t_crit else "fail to reject")
    print(model.t_test("mkt_excess = 1"))
    # 3
    print(model.get_prediction(pd.DataFrame({"const": [1.0], "mkt_excess": [8.0]})).summary_frame()[["mean", "obs_ci_lower", "obs_ci_upper"]])
    print("Wider because (Xf - X̄)^2 in s_f grows as Xf moves away from the mean of X =", round(x_bar, 2))
    # 4
    print("Returns include negatives, so ln(Y) is undefined; the scatter is linear, so the plain linear model is appropriate.")
    '''),
]

# --------------------------------------------------------------------------------------------
f = "02_multiple_regression.ipynb"
notebooks[f] = header(f, "02 · Multiple regression: a four-factor model for a fund", """
**Goal:** explain a fund’s returns with the market, size (SMB), value (HML) and momentum (MOM) factors.
Compute adjusted R², the F-test, AIC/BIC and a nested-model joint F-test, by hand and with `statsmodels`.
""") + [
    code('''
    df = pd.read_csv(DATA + "factor_returns.csv")
    y = df["fund_excess"]
    X4 = sm.add_constant(df[["mkt_excess", "smb", "hml", "mom"]])
    m4 = sm.OLS(y, X4).fit()
    print(m4.summary())
    '''),
    md("""
    **Interpretation:** each slope is the change in the fund’s excess return for a 1-point move in that factor,
    **holding the other factors constant**. Look at which t-statistics exceed ~2.
    """),
    md(r"## Adjusted R² and the F-statistic by hand"),
    code('''
    n, k = int(m4.nobs), 4
    R2 = m4.rsquared
    adj = 1 - (n - 1) / (n - k - 1) * (1 - R2)
    SSE = (m4.resid ** 2).sum(); SST = ((y - y.mean()) ** 2).sum(); SSR = SST - SSE
    F = (SSR / k) / (SSE / (n - k - 1))
    print(f"R2={R2:.4f}  adj R2={adj:.4f} (statsmodels {m4.rsquared_adj:.4f})")
    print(f"F={F:.2f} (statsmodels {m4.fvalue:.2f}), p={m4.f_pvalue:.2e}")
    '''),
    md("## Compare models with AIC and BIC (lower is better)"),
    code('''
    def fit(cols):
        return sm.OLS(y, sm.add_constant(df[cols])).fit()

    models = {"CAPM": ["mkt_excess"], "3-factor": ["mkt_excess", "smb", "hml"], "4-factor": ["mkt_excess", "smb", "hml", "mom"]}
    rows = []
    for name, cols in models.items():
        r = fit(cols)
        sse = (r.resid ** 2).sum(); kk = len(cols)
        aic_cfa = n * np.log(sse / n) + 2 * (kk + 1)            # CFA formula
        bic_cfa = n * np.log(sse / n) + np.log(n) * (kk + 1)
        rows.append([name, r.rsquared, r.rsquared_adj, aic_cfa, bic_cfa])
    pd.DataFrame(rows, columns=["model", "R2", "adj R2", "AIC (CFA)", "BIC (CFA)"]).set_index("model").round(3)
    '''),
    md("""
    Note: statsmodels’ `.aic` / `.bic` use the log-likelihood version; the **ranking** is the same as the CFA formula.
    """),
    md(r"""
    ## Nested models: do SMB and HML add value jointly?
    $F = \dfrac{(SSE_R - SSE_U)/q}{SSE_U/(n-k-1)}$ with *q* = 2 restrictions.
    """),
    code('''
    from scipy import stats
    rest, unres = fit(["mkt_excess", "mom"]), m4
    sse_r, sse_u, q = (rest.resid ** 2).sum(), (unres.resid ** 2).sum(), 2
    F_joint = ((sse_r - sse_u) / q) / (sse_u / (n - k - 1))
    print(f"F = {F_joint:.2f}, critical F(2,{n-k-1}) = {stats.f.ppf(0.95, q, n-k-1):.2f}")
    print(m4.f_test("smb = 0, hml = 0"))          # same test in one line
    '''),
    md("## Diagnostic plot: residuals vs fitted"),
    code('''
    plt.scatter(m4.fittedvalues, m4.resid, alpha=0.5); plt.axhline(0, color="k", lw=1)
    plt.xlabel("fitted"); plt.ylabel("residual"); plt.title("A fan shape hints at heteroskedasticity (see notebook 03)"); plt.show()
    '''),
    *exercise(1, "Is momentum significant for this fund at 5%? Use the t-stat and p-value from `m4`."),
    *exercise(2, "Add a useless random variable `noise = np.random.default_rng(0).normal(size=n)` to the 4-factor model. What happens to R² and to adjusted R²? Why?"),
    *exercise(3, "Predict the fund’s excess return in a month where mkt = 2, smb = −1, hml = 0.5, mom = 1.",
              "`m4.predict(pd.DataFrame({'const':[1], 'mkt_excess':[2], 'smb':[-1], 'hml':[0.5], 'mom':[1]}))`"),
    md("---\n## Solutions"),
    code('''
    print("1) MOM t =", round(m4.tvalues["mom"], 2), "p =", round(m4.pvalues["mom"], 3))
    d2 = df.copy(); d2["noise"] = np.random.default_rng(0).normal(size=n)
    r5 = sm.OLS(y, sm.add_constant(d2[["mkt_excess", "smb", "hml", "mom", "noise"]])).fit()
    print(f"2) R2 {m4.rsquared:.4f} -> {r5.rsquared:.4f} (never falls); adj R2 {m4.rsquared_adj:.4f} -> {r5.rsquared_adj:.4f} (penalised)")
    print("3)", m4.predict(pd.DataFrame({"const": [1], "mkt_excess": [2], "smb": [-1], "hml": [0.5], "mom": [1]})).round(3).tolist())
    '''),
]

# --------------------------------------------------------------------------------------------
f = "03_misspecification_and_extensions.ipynb"
notebooks[f] = header(f, "03 · Model misspecification, influence, dummies and logistic regression", """
**Goal:** run every diagnostic test from the CFA curriculum on real regression output and apply the fixes:
Breusch–Pagan + White SEs, Durbin–Watson / Breusch–Godfrey + Newey–West, VIF, leverage and Cook’s D,
dummy variables, and a logistic regression for loan default.
""") + [
    code('''
    from statsmodels.stats.diagnostic import het_breuschpagan, acorr_breusch_godfrey
    from statsmodels.stats.stattools import durbin_watson
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    from scipy import stats

    df = pd.read_csv(DATA + "factor_returns.csv")
    X = sm.add_constant(df[["mkt_excess", "smb", "hml", "mom"]])
    m = sm.OLS(df["fund_excess"], X).fit()
    '''),
    md("## 1. Conditional heteroskedasticity: Breusch–Pagan test\nBP = n × R² from regressing squared residuals on the X’s; compare with χ²(k)."),
    code('''
    aux = sm.OLS(m.resid ** 2, X).fit()
    BP = m.nobs * aux.rsquared
    print(f"BP by hand = {BP:.2f}, chi2 critical (k=4) = {stats.chi2.ppf(0.95, 4):.2f}")
    lm, lm_p, _, _ = het_breuschpagan(m.resid, X)
    print(f"statsmodels: LM = {lm:.2f}, p = {lm_p:.4f}")
    print("→ reject homoskedasticity: conditional heteroskedasticity" if lm_p < 0.05 else "→ no evidence")
    '''),
    md("**Fix:** keep the coefficients, replace the standard errors with White (robust) SEs."),
    code('''
    robust = sm.OLS(df["fund_excess"], X).fit(cov_type="HC1")
    pd.DataFrame({"coef": m.params, "OLS SE": m.bse, "White SE": robust.bse, "OLS t": m.tvalues, "White t": robust.tvalues}).round(3)
    '''),
    md("## 2. Serial correlation: Durbin–Watson and Breusch–Godfrey"),
    code('''
    print("DW =", round(durbin_watson(m.resid), 3), "(≈2 means none)")
    bg_lm, bg_p, _, _ = acorr_breusch_godfrey(m, nlags=4)
    print(f"Breusch-Godfrey (4 lags): LM = {bg_lm:.2f}, p = {bg_p:.3f}")
    nw = sm.OLS(df["fund_excess"], X).fit(cov_type="HAC", cov_kwds={"maxlags": 4})   # Newey-West fix
    print(nw.bse.round(3))
    '''),
    md("## 3. Multicollinearity: VIF = 1 / (1 − R²ⱼ)\nWe add a variable that is almost a copy of the market to see the damage."),
    code('''
    d = df.copy()
    d["mkt_copy"] = d["mkt_excess"] + np.random.default_rng(1).normal(0, 0.3, len(d))
    Xc = sm.add_constant(d[["mkt_excess", "mkt_copy", "smb", "hml"]])
    mc = sm.OLS(d["fund_excess"], Xc).fit()
    vif = pd.Series([variance_inflation_factor(Xc.values, i) for i in range(1, Xc.shape[1])], index=Xc.columns[1:])
    print("VIF:"); print(vif.round(1))
    print(f"R2 = {mc.rsquared:.3f}, F p-value = {mc.f_pvalue:.1e}")
    print(mc.summary().tables[1])
    '''),
    md("Classic symptom: high R² and a significant F, but the two market variables have huge SEs. **Fix:** drop one."),
    md("## 4. Influential observations: leverage, studentised residuals, Cook’s D\nWe plant one extreme month to see if the tests catch it."),
    code('''
    d = df[["mkt_excess", "stock_excess"]].copy()
    d.loc[len(d)] = [-25.0, 20.0]                 # planted point: market crash, stock soars
    Xi = sm.add_constant(d["mkt_excess"])
    mi = sm.OLS(d["stock_excess"], Xi).fit()
    infl = mi.get_influence()
    k, n = 1, len(d)
    tab = pd.DataFrame({"leverage": infl.hat_matrix_diag, "student_resid": infl.resid_studentized_external, "cooks_d": infl.cooks_distance[0]})
    flags = tab[(tab.leverage > 3 * (k + 1) / n) | (tab.cooks_d > 2 * np.sqrt(k / n)) | (tab.student_resid.abs() > stats.t.ppf(0.975, n - k - 2))]
    print("Thresholds: leverage >", round(3 * (k + 1) / n, 3), "| Cook's D >", round(2 * np.sqrt(k / n), 3))
    print(flags.round(3))
    print("beta with planted point:", round(mi.params.iloc[1], 3), "| without:", round(sm.OLS(df["stock_excess"], sm.add_constant(df["mkt_excess"])).fit().params.iloc[1], 3))
    '''),
    md("## 5. Dummy variables\nLoan purpose has 4 categories → 3 dummies (the dropped one is the base case)."),
    code('''
    cr = pd.read_csv(DATA + "credit_default.csv")
    dummies = pd.get_dummies(cr["purpose"], prefix="p", drop_first=True, dtype=float)
    print("Base category:", sorted(cr["purpose"].unique())[0]); dummies.head()
    '''),
    md("## 6. Logistic regression: probability of default\nEstimated by maximum likelihood. Coefficients are changes in **log-odds**; `exp(coef)` is the odds ratio."),
    code('''
    Xl = sm.add_constant(pd.concat([cr[["income_k", "debt_to_income", "fico", "loan_to_value", "years_employed", "home_owner"]], dummies], axis=1))
    logit = sm.Logit(cr["default"], Xl).fit(disp=0)
    print(logit.summary())
    '''),
    code('''
    out = pd.DataFrame({"coef": logit.params, "odds_ratio": np.exp(logit.params), "p": logit.pvalues}).round(4)
    print(out)
    print(f"\\nLikelihood ratio test: LR = {logit.llr:.1f}, p = {logit.llr_pvalue:.2e}; pseudo R2 = {logit.prsquared:.3f}")
    '''),
    *exercise(1, "Re-run the Breusch–Pagan test on the **stock** CAPM regression (`stock_excess` on `mkt_excess`). Is there heteroskedasticity?"),
    *exercise(2, "Interpret the odds ratio on `fico`: by what percentage do the odds of default change for a 10-point higher FICO score?",
              "Odds ratio for 10 points = exp(10 × coef)."),
    *exercise(3, "Predict the default probability for: income 50, DTI 45, FICO 620, LTV 90, 1 year employed, not a home owner, purpose small_business.",
              "Build a one-row DataFrame with exactly the columns of `Xl` (const = 1 and the three dummy columns), then `logit.predict(row)`."),
    md("---\n## Solutions"),
    code('''
    ms = sm.OLS(df["stock_excess"], sm.add_constant(df["mkt_excess"])).fit()
    bp_p = het_breuschpagan(ms.resid, ms.model.exog)[1]
    print("1) BP p-value:", round(bp_p, 4), "→", "heteroskedasticity" if bp_p < 0.05 else "no evidence of conditional heteroskedasticity")
    b = logit.params["fico"]; print(f"2) 10-point FICO: odds × {np.exp(10*b):.3f} → {100*(np.exp(10*b)-1):.1f}% change")
    row = pd.DataFrame([dict(const=1, income_k=50, debt_to_income=45, fico=620, loan_to_value=90, years_employed=1, home_owner=0,
                             p_debt_consolidation=0, p_home_improvement=0, p_small_business=1)])[Xl.columns]
    print("3) PD =", round(float(logit.predict(row).iloc[0]), 3))
    '''),
]

# --------------------------------------------------------------------------------------------
f = "04_time_series.ipynb"
notebooks[f] = header(f, "04 · Time series: trends, AR models, unit roots, seasonality, ARCH, cointegration", """
**Goal:** walk the full CFA time-series workflow on quarterly data.

Columns in `macro_quarterly.csv`: `retail_sales` (growing, seasonal), `inflation` (mean-reverting),
`fx_rate` (random walk), `index_return` (volatility clusters), `oil_price`, `energy_stock`, `gold_price` (for cointegration).
""") + [
    code('''
    from statsmodels.stats.stattools import durbin_watson
    from statsmodels.tsa.stattools import adfuller, coint, acf
    from statsmodels.stats.diagnostic import het_arch

    ts = pd.read_csv(DATA + "macro_quarterly.csv")
    T = len(ts)
    ts[["retail_sales", "inflation", "fx_rate", "index_return"]].plot(subplots=True, figsize=(10, 7), layout=(2, 2)); plt.show()
    '''),
    md("## 1. Trend models: linear vs log-linear for retail sales"),
    code('''
    t = sm.add_constant(ts["t"])
    lin = sm.OLS(ts["retail_sales"], t).fit()
    loglin = sm.OLS(np.log(ts["retail_sales"]), t).fit()
    print(f"Linear:     b1 = {lin.params['t']:.3f} per quarter, DW = {durbin_watson(lin.resid):.2f}")
    print(f"Log-linear: b1 = {loglin.params['t']:.4f} → growth ≈ {100*(np.exp(loglin.params['t'])-1):.2f}% per quarter, DW = {durbin_watson(loglin.resid):.2f}")
    # forecast next quarter from the log-linear model: remember to exponentiate
    print("Log-linear forecast for t = 121:", round(np.exp(loglin.params["const"] + loglin.params["t"] * 121), 2))
    '''),
    md("DW far from 2 → the residuals are serially correlated → a trend model alone is misspecified."),
    md("## 2. AR(1) model for inflation\nRegress $x_t$ on $x_{t-1}$; the mean-reverting level is $b_0/(1-b_1)$."),
    code('''
    x = ts["inflation"]
    d = pd.DataFrame({"x": x, "x_lag1": x.shift(1)}).dropna()
    ar1 = sm.OLS(d["x"], sm.add_constant(d["x_lag1"])).fit()
    b0, b1 = ar1.params
    print(ar1.summary().tables[1])
    print(f"Mean-reverting level = {b0/(1-b1):.3f}; last value = {x.iloc[-1]:.3f}")
    '''),
    md("### Check residual autocorrelations: t = ρ / (1/√T)"),
    code('''
    r = acf(ar1.resid, nlags=8, fft=False)[1:]
    Tn = len(ar1.resid)
    pd.DataFrame({"lag": range(1, 9), "autocorr": r, "t_stat": r / (1 / np.sqrt(Tn))}).round(3).set_index("lag")
    '''),
    md("No |t| above ~2 → AR(1) is correctly specified. (Test many lags and about 1 in 20 can look significant by chance.) Now forecast with the **chain rule**:"),
    code('''
    f1 = b0 + b1 * x.iloc[-1]; f2 = b0 + b1 * f1
    print(f"one step ahead: {f1:.3f}, two steps ahead: {f2:.3f}")
    '''),
    md("### Out-of-sample comparison: AR(1) vs AR(2) by RMSE\nFit on the first 100 quarters, forecast the last 20 one step at a time."),
    code('''
    def oos_rmse(p, split=100):
        lags = pd.concat({f"l{i}": x.shift(i) for i in range(1, p + 1)}, axis=1)
        dd = pd.concat([x.rename("x"), lags], axis=1).dropna()
        train, test = dd[dd.index < split], dd[dd.index >= split]
        fit = sm.OLS(train["x"], sm.add_constant(train.drop(columns="x"))).fit()
        pred = fit.predict(sm.add_constant(test.drop(columns="x"), has_constant="add"))
        return np.sqrt(((test["x"] - pred) ** 2).mean())
    print("RMSE AR(1):", round(oos_rmse(1), 4), "| RMSE AR(2):", round(oos_rmse(2), 4))
    '''),
    md("## 3. Random walk and the Dickey–Fuller test on the exchange rate\nH₀: unit root (g₁ = 0). `adfuller` with `maxlag=0` is the plain DF test."),
    code('''
    stat, p, *_ = adfuller(ts["fx_rate"], maxlag=0, autolag=None, regression="c")
    print(f"Levels: DF t = {stat:.2f}, p = {p:.3f} → {'unit root, cannot reject' if p > 0.05 else 'stationary'}")
    dfx = ts["fx_rate"].diff().dropna()
    stat, p, *_ = adfuller(dfx, maxlag=0, autolag=None, regression="c")
    print(f"First difference: DF t = {stat:.2f}, p = {p:.4f} → {'stationary' if p < 0.05 else 'still unit root'}")
    '''),
    code('''
    # The same test by hand: regress Δx_t on x_{t-1}
    dd = pd.DataFrame({"dx": ts["fx_rate"].diff(), "lag": ts["fx_rate"].shift(1)}).dropna()
    dfm = sm.OLS(dd["dx"], sm.add_constant(dd["lag"])).fit()
    print("g1 =", round(dfm.params["lag"], 4), "t =", round(dfm.tvalues["lag"], 2), "(compare with DF critical ≈ -2.89, not -1.96)")
    '''),
    md("## 4. Seasonality\nModel quarterly growth in (log) retail sales, check residual autocorrelation at lag 4, then add the seasonal lag."),
    code('''
    g = np.log(ts["retail_sales"]).diff()
    d = pd.DataFrame({"g": g, "l1": g.shift(1), "l4": g.shift(4)}).dropna()
    m1 = sm.OLS(d["g"], sm.add_constant(d[["l1"]])).fit()
    r = acf(m1.resid, nlags=6, fft=False)[1:]
    print("Residual autocorr t-stats, AR(1):", np.round(r * np.sqrt(len(d)), 2))
    m4 = sm.OLS(d["g"], sm.add_constant(d[["l1", "l4"]])).fit()
    r = acf(m4.resid, nlags=6, fft=False)[1:]
    print("Residual autocorr t-stats, AR(1)+lag 4:", np.round(r * np.sqrt(len(d)), 2))
    print(m4.params.round(4))
    '''),
    md("## 5. ARCH: does volatility cluster in index returns?\nRegress ε̂²ₜ on ε̂²ₜ₋₁; a significant slope means ARCH(1)."),
    code('''
    e = ts["index_return"] - ts["index_return"].mean()
    e2 = pd.DataFrame({"e2": e ** 2, "e2_lag": (e ** 2).shift(1)}).dropna()
    arch = sm.OLS(e2["e2"], sm.add_constant(e2["e2_lag"])).fit()
    a0, a1 = arch.params
    print(f"a1 = {a1:.3f}, t = {arch.tvalues['e2_lag']:.2f}")
    print(f"Next-quarter variance forecast = a0 + a1·e_T² = {a0 + a1 * e.iloc[-1]**2:.2f}")
    print("statsmodels het_arch p-value:", round(het_arch(e, nlags=1)[1], 4))
    '''),
    md("## 6. Two series with unit roots: cointegration (Engle–Granger)"),
    code('''
    for a, b in [("energy_stock", "oil_price"), ("gold_price", "oil_price")]:
        t_stat, p, _ = coint(ts[a], ts[b])
        print(f"{a} vs {b}: EG t = {t_stat:.2f}, p = {p:.3f} → {'cointegrated: regression valid' if p < 0.05 else 'NOT cointegrated: regression spurious'}")
    '''),
    *exercise(1, "Run the Dickey–Fuller test on `inflation` in levels. Do you reject the unit root? Is that consistent with the AR(1) estimate b₁?"),
    *exercise(2, "Fit an AR(1) to the first-differenced `fx_rate`. Is b₁ significant? What does that say about predicting exchange-rate changes?"),
    *exercise(3, "Forecast inflation **four** quarters ahead with the chain rule. Which value does the forecast approach as the horizon grows?"),
    *exercise(4, "Regress `gold_price` on `oil_price` with OLS and look at R² and the t-stat. Why should you not trust them?"),
    md("---\n## Solutions"),
    code('''
    s, p, *_ = adfuller(ts["inflation"], maxlag=0, autolag=None); print(f"1) DF t={s:.2f}, p={p:.4f}; b1={b1:.3f} < 1 → stationary")
    dd = pd.DataFrame({"y": dfx, "l": dfx.shift(1)}).dropna(); r2 = sm.OLS(dd["y"], sm.add_constant(dd["l"])).fit()
    print(f"2) b1={r2.params['l']:.3f}, p={r2.pvalues['l']:.3f} →", "changes are not predictable (random walk)" if r2.pvalues["l"] > 0.05 else "some predictability")
    f = x.iloc[-1]
    for h in range(1, 5):
        f = b0 + b1 * f; print(f"3) h={h}: {f:.3f}")
    print("   → converges to the mean-reverting level", round(b0 / (1 - b1), 3))
    sp = sm.OLS(ts["gold_price"], sm.add_constant(ts["oil_price"])).fit()
    print(f"4) R2={sp.rsquared:.2f}, t={sp.tvalues['oil_price']:.1f}: both unit-root, not cointegrated → spurious regression")
    '''),
]

# --------------------------------------------------------------------------------------------
f = "05_supervised_ml.ipynb"
notebooks[f] = header(f, "05 · Supervised machine learning: predicting loan default", """
**Goal:** train and compare the CFA supervised algorithms (penalized regression, logistic regression, KNN,
SVM, CART, random forest, boosting) with proper train/test splits, cross-validation and evaluation metrics.
""") + [
    code('''
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.linear_model import LogisticRegression, LassoCV
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.svm import SVC
    from sklearn.tree import DecisionTreeClassifier, export_text
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.metrics import confusion_matrix, classification_report, roc_auc_score, roc_curve

    cr = pd.read_csv(DATA + "credit_default.csv")
    X = pd.get_dummies(cr.drop(columns="default"), columns=["purpose"], drop_first=True, dtype=float)
    y = cr["default"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)
    print(X_train.shape, X_test.shape, "| default rate:", round(y.mean(), 3))
    '''),
    md("## 1. Penalized regression (LASSO) on the factor data\nWe add 10 pure-noise features. LASSO should set most of them to exactly zero."),
    code('''
    fr = pd.read_csv(DATA + "factor_returns.csv")
    feats = fr[["mkt_excess", "smb", "hml", "mom"]].copy()
    rng = np.random.default_rng(3)
    for i in range(10):
        feats[f"noise_{i}"] = rng.normal(size=len(fr))
    lasso = make_pipeline(StandardScaler(), LassoCV(cv=5, random_state=0)).fit(feats, fr["fund_excess"])
    coefs = pd.Series(lasso[-1].coef_, index=feats.columns)
    print("lambda chosen by CV:", round(lasso[-1].alpha_, 4)); print(coefs.round(3))
    '''),
    md("## 2. Train several classifiers and compare test AUC\nScaling matters for distance- and margin-based models (KNN, SVM), so they go in a pipeline."),
    code('''
    models = {
        "Logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "KNN (k=15)": make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=15)),
        "SVM (RBF)": make_pipeline(StandardScaler(), SVC(probability=True, random_state=0)),
        "CART (depth 4)": DecisionTreeClassifier(max_depth=4, random_state=0),
        "Random forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, random_state=0),
        "Gradient boosting": GradientBoostingClassifier(random_state=0),
    }
    rows = []
    for name, mdl in models.items():
        mdl.fit(X_train, y_train)
        p = mdl.predict_proba(X_test)[:, 1]
        cv = cross_val_score(mdl, X_train, y_train, cv=5, scoring="roc_auc").mean()
        rows.append([name, roc_auc_score(y_train, mdl.predict_proba(X_train)[:, 1]), cv, roc_auc_score(y_test, p)])
    pd.DataFrame(rows, columns=["model", "train AUC", "5-fold CV AUC", "test AUC"]).set_index("model").round(3)
    '''),
    md("A big gap between **train** and **test** AUC is overfitting (variance error)."),
    md("## 3. Overfitting in one picture: tree depth vs accuracy"),
    code('''
    depths = range(1, 16); tr, te = [], []
    for dpt in depths:
        t = DecisionTreeClassifier(max_depth=dpt, random_state=0).fit(X_train, y_train)
        tr.append(t.score(X_train, y_train)); te.append(t.score(X_test, y_test))
    plt.plot(depths, tr, "o-", label="train"); plt.plot(depths, te, "o-", label="test")
    plt.xlabel("max depth (complexity)"); plt.ylabel("accuracy"); plt.legend(); plt.title("Fitting curve"); plt.show()
    '''),
    md("## 4. Read a decision tree"),
    code('''
    print(export_text(DecisionTreeClassifier(max_depth=3, random_state=0).fit(X_train, y_train), feature_names=list(X.columns)))
    '''),
    md("## 5. Which features matter? (random forest importance)"),
    code('''
    pd.Series(models["Random forest"].feature_importances_, index=X.columns).sort_values().plot.barh(); plt.show()
    '''),
    md("## 6. Confusion matrix, precision, recall, F1 for the logistic model"),
    code('''
    lg = models["Logistic"]
    pred = lg.predict(X_test)   # threshold 0.5
    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
    print(f"TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"precision={tp/(tp+fp):.3f} recall={tp/(tp+fn):.3f} accuracy={(tp+tn)/len(y_test):.3f}")
    print(classification_report(y_test, pred, digits=3))
    '''),
    md("## 7. ROC curve and choosing a threshold"),
    code('''
    p = lg.predict_proba(X_test)[:, 1]
    fpr, tpr, thr = roc_curve(y_test, p)
    plt.plot(fpr, tpr, label=f"logistic AUC={roc_auc_score(y_test, p):.3f}"); plt.plot([0, 1], [0, 1], "k--")
    plt.xlabel("False positive rate"); plt.ylabel("Recall (TPR)"); plt.legend(); plt.show()
    for th in [0.2, 0.35, 0.5]:
        pr = (p >= th).astype(int); tn, fp, fn, tp = confusion_matrix(y_test, pr).ravel()
        print(f"threshold {th}: precision {tp/max(tp+fp,1):.2f}, recall {tp/(tp+fn):.2f}")
    '''),
    *exercise(1, "Try KNN with k = 1, 5, 15, 51. Report train and test accuracy. Which k overfits? Which underfits?"),
    *exercise(2, "Fit KNN **without** the StandardScaler. Why does test AUC drop?", "Look at the scale of `income_k` vs `fico` vs `home_owner`."),
    *exercise(3, "The bank says missing a default costs 5× more than a false alarm. Pick a threshold for the logistic model that minimises `5*FN + FP` on the test set."),
    md("---\n## Solutions"),
    code('''
    for k in [1, 5, 15, 51]:
        m = make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=k)).fit(X_train, y_train)
        print(f"1) k={k:>2}: train {m.score(X_train, y_train):.3f}  test {m.score(X_test, y_test):.3f}")
    raw = KNeighborsClassifier(n_neighbors=15).fit(X_train, y_train)
    print("2) unscaled KNN test AUC:", round(roc_auc_score(y_test, raw.predict_proba(X_test)[:, 1]), 3), "→ fico/income dominate the distance")
    costs = {th: 5 * ((p < th) & (y_test == 1)).sum() + ((p >= th) & (y_test == 0)).sum() for th in np.arange(0.05, 0.95, 0.05)}
    best = min(costs, key=costs.get); print(f"3) best threshold ≈ {best:.2f}, cost {costs[best]}")
    '''),
]

# --------------------------------------------------------------------------------------------
f = "06_unsupervised_ml.ipynb"
notebooks[f] = header(f, "06 · Unsupervised learning: PCA on yield curves and clustering companies", """
**Goal:** reduce nine Treasury yields to three principal components (level, slope, curvature) and group
150 companies into data-driven peer groups with k-means and hierarchical clustering.
""") + [
    md("## 1. PCA on monthly yield changes"),
    code('''
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans, AgglomerativeClustering
    from sklearn.metrics import silhouette_score
    from scipy.cluster.hierarchy import linkage, dendrogram

    yc = pd.read_csv(DATA + "treasury_yields.csv").set_index("month")
    dy = yc.diff().dropna()            # PCA on changes, the usual choice for rates
    pca = PCA().fit(dy)
    ev = pd.DataFrame({"eigenvalue": pca.explained_variance_, "share": pca.explained_variance_ratio_,
                       "cumulative": pca.explained_variance_ratio_.cumsum()}, index=[f"PC{i+1}" for i in range(9)])
    ev.round(4)
    '''),
    code('''
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    ax[0].bar(ev.index, ev["share"]); ax[0].set_title("Scree plot")
    load = pd.DataFrame(pca.components_[:3].T, index=dy.columns, columns=["PC1", "PC2", "PC3"])
    load.plot(ax=ax[1], marker="o"); ax[1].axhline(0, color="k", lw=0.8); ax[1].set_title("Loadings across maturities")
    plt.show()
    load.round(3)
    '''),
    md("""
    **Reading the loadings:** PC1 has the same sign at every maturity (a parallel shift = **level**),
    PC2 changes sign from short to long (**slope**), PC3 is high at the ends and low in the middle (**curvature**).
    Signs of components are arbitrary; flipping all of them changes nothing.
    """),
    code('''
    scores = pd.DataFrame(pca.transform(dy)[:, :3], columns=["PC1", "PC2", "PC3"], index=dy.index)
    print(scores.corr().round(3))      # components are uncorrelated
    '''),
    md("## 2. K-means on company fundamentals\nStandardise first: P/E is in the tens, beta is around 1."),
    code('''
    co = pd.read_csv(DATA + "company_fundamentals.csv")
    feats = ["revenue_growth", "operating_margin", "pe_ratio", "dividend_yield", "beta", "debt_to_equity"]
    Z = StandardScaler().fit_transform(co[feats])
    wcss, sil = [], []
    for k in range(1, 10):
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(Z)
        wcss.append(km.inertia_); sil.append(silhouette_score(Z, km.labels_) if k > 1 else np.nan)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    ax[0].plot(range(1, 10), wcss, "o-"); ax[0].set_title("Elbow: WCSS by k")
    ax[1].plot(range(1, 10), sil, "o-"); ax[1].set_title("Silhouette (higher is better)")
    plt.show()
    '''),
    code('''
    km = KMeans(n_clusters=5, n_init=10, random_state=0).fit(Z)
    co["cluster"] = km.labels_
    print(pd.crosstab(co["cluster"], co["true_sector"]))       # did clustering recover the sectors?
    co.groupby("cluster")[feats].mean().round(2)
    '''),
    md("## 3. Hierarchical (agglomerative) clustering and the dendrogram"),
    code('''
    Lk = linkage(Z, method="ward")
    plt.figure(figsize=(12, 4)); dendrogram(Lk, no_labels=True, color_threshold=12); plt.title("Dendrogram (Ward linkage)"); plt.show()
    agg = AgglomerativeClustering(n_clusters=5, linkage="ward").fit(Z)
    pd.crosstab(agg.labels_, co["true_sector"])
    '''),
    *exercise(1, "How many principal components do you need to explain 95% of the variance in yield changes?"),
    *exercise(2, "Run PCA on the **companies** (standardised). Plot the companies on PC1 vs PC2, coloured by `true_sector`."),
    *exercise(3, "Run k-means with k = 3 instead of 5. Which sectors get merged? Does that make economic sense?"),
    md("---\n## Solutions"),
    code('''
    print("1)", int((ev["cumulative"] < 0.95).sum() + 1), "components")
    pc = PCA(2).fit_transform(Z)
    for s in co["true_sector"].unique():
        msk = co["true_sector"] == s; plt.scatter(pc[msk, 0], pc[msk, 1], label=s, alpha=0.7)
    plt.legend(); plt.xlabel("PC1"); plt.ylabel("PC2"); plt.title("2) companies in PC space"); plt.show()
    print("3)"); print(pd.crosstab(KMeans(3, n_init=10, random_state=0).fit_predict(Z), co["true_sector"]))
    '''),
]

# --------------------------------------------------------------------------------------------
f = "07_neural_nets_and_text.ipynb"
notebooks[f] = header(f, "07 · Neural networks and text analytics (big data projects)", """
**Goal:** train a small neural network, see how its hyperparameters matter, then run a complete text
project on financial headlines: tokenise, build a document-term matrix, TF-IDF, and classify sentiment.
""") + [
    md("## 1. A neural network (multi-layer perceptron) for default prediction"),
    code('''
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.neural_network import MLPClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score, confusion_matrix, classification_report
    import warnings; warnings.filterwarnings("ignore")

    cr = pd.read_csv(DATA + "credit_default.csv")
    X = pd.get_dummies(cr.drop(columns="default"), columns=["purpose"], drop_first=True, dtype=float)
    y = cr["default"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)

    for layers in [(4,), (16,), (64, 64)]:
        for lr in [0.001, 0.01]:
            nn = make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=layers, learning_rate_init=lr,
                                                               max_iter=600, random_state=0)).fit(X_train, y_train)
            print(f"layers {str(layers):9} lr {lr:<6} train AUC {roc_auc_score(y_train, nn.predict_proba(X_train)[:,1]):.3f}"
                  f"  test AUC {roc_auc_score(y_test, nn.predict_proba(X_test)[:,1]):.3f}")
    '''),
    md("""
    Hyperparameters (layers, nodes, learning rate, epochs) are set by **you**. Bigger nets fit the training data better
    but can generalise worse: the same bias–variance trade-off as before.
    """),
    md("## 2. What one neuron does: weighted sum + activation"),
    code('''
    x_in = np.array([0.5, -1.2, 2.0]); w = np.array([0.8, 0.1, -0.4]); b = 0.2
    z = x_in @ w + b
    print(f"summation z = {z:.3f} | ReLU = {max(0, z):.3f} | sigmoid = {1/(1+np.exp(-z)):.3f}")
    '''),
    md("## 3. Text project: from raw headlines to features"),
    code('''
    import re
    from collections import Counter
    hl = pd.read_csv(DATA + "headlines.csv")
    print(hl["sentiment"].value_counts()); hl.head()
    '''),
    code('''
    STOP = {"as", "on", "to", "in", "for", "the", "a", "this", "after", "amid", "inc", "corp"}
    def tokenize(s):
        tokens = re.findall(r"[a-z]+", s.lower())        # lowercase + strip punctuation/numbers
        return [t for t in tokens if t not in STOP]       # remove stop words
    def crude_stem(t):
        for suf in ("ing", "es", "ed", "s"):
            if t.endswith(suf) and len(t) > len(suf) + 2:
                return t[: -len(suf)]
        return t
    ex = hl["headline"].iloc[0]
    print(ex); print("tokens:", tokenize(ex)); print("stems: ", [crude_stem(t) for t in tokenize(ex)])
    print(Counter(t for h in hl["headline"] for t in tokenize(h)).most_common(12))
    '''),
    md("## 4. Bag-of-words, n-grams, document-term matrix and TF-IDF with scikit-learn"),
    code('''
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    bow = CountVectorizer(ngram_range=(1, 2), stop_words="english")
    dtm = bow.fit_transform(hl["headline"])
    print("Document-term matrix:", dtm.shape, "(documents × tokens incl. bigrams)")
    pd.DataFrame(dtm[:3].toarray(), columns=bow.get_feature_names_out()).loc[:, lambda d: d.sum() > 0]
    '''),
    code('''
    Xtr, Xte, ytr, yte = train_test_split(hl["headline"], hl["sentiment"], test_size=0.3, random_state=0, stratify=hl["sentiment"])
    clf = make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), LogisticRegression(max_iter=1000)).fit(Xtr, ytr)
    pred = clf.predict(Xte)
    print(classification_report(yte, pred, digits=3))
    print(pd.DataFrame(confusion_matrix(yte, pred, labels=clf.classes_), index=clf.classes_, columns=clf.classes_))
    '''),
    code('''
    # Most informative words per class
    vec, lr = clf[0], clf[-1]
    names = vec.get_feature_names_out()
    for i, c in enumerate(lr.classes_):
        print(c.ljust(8), ", ".join(names[np.argsort(lr.coef_[i])[-6:]][::-1]))
    print(clf.predict(["Initech beats estimates as demand grows", "Globex cuts guidance after weak quarter"]))
    '''),
    *exercise(1, "Replace the logistic regression with `MultinomialNB()` (naive Bayes) and a plain `CountVectorizer`. Compare macro F1."),
    *exercise(2, "Write three headlines of your own and classify them. Can you fool the model?"),
    *exercise(3, "Train the (64, 64) neural network for only `max_iter=20`. What happens to train and test AUC (underfitting)?"),
    md("---\n## Solutions"),
    code('''
    from sklearn.metrics import f1_score
    nb = make_pipeline(CountVectorizer(ngram_range=(1, 2)), MultinomialNB()).fit(Xtr, ytr)
    print("1) NB macro F1:", round(f1_score(yte, nb.predict(Xte), average="macro"), 3), "| logistic:", round(f1_score(yte, pred, average="macro"), 3))
    print("2)", clf.predict(["Hooli loses key customer but raises guidance", "Vandelay schedules earnings date", "Acme record revenue"]))
    nn = make_pipeline(StandardScaler(), MLPClassifier((64, 64), max_iter=20, random_state=0)).fit(X_train, y_train)
    print("3) train AUC", round(roc_auc_score(y_train, nn.predict_proba(X_train)[:, 1]), 3), "test AUC", round(roc_auc_score(y_test, nn.predict_proba(X_test)[:, 1]), 3))
    '''),
]

for name, cells in notebooks.items():
    nb = build(name, cells)
    path = NB / name
    if "--execute" in sys.argv:
        from nbclient import NotebookClient
        NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(NB)}}).execute()
    nbf.write(nb, path)
    print("wrote", path.name)
