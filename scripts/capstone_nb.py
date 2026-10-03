"""Cells for notebook 08 (capstone on real market data). Imported by build_notebooks.py."""
from nb_helpers import md, code, header

F = "08_capstone_real_market_data.ipynb"
CELLS = header(F, "08 · Capstone: the whole toolkit on real market data", """
This project downloads **real monthly prices** for the 20 largest Swiss stocks and the SMI index from
Yahoo Finance, then runs everything from the course on them: CAPM betas and diagnostics, a momentum factor,
time-series tests, PCA, clustering, a backtest, and a machine-learning forecast.

**Real data is messy and markets are hard to predict.** Expect weaker, noisier results than in the clean practice
datasets. That is the lesson. If the download fails (no internet, Yahoo changes its API), the notebook
automatically switches to a bundled *simulated* dataset so every cell still runs.

Each section ends with a **Your turn** task. There is no single right answer, so there is no checker here.
""") + [
    md("## 0. Settings: change these to analyse any market"),
    code('''
    USE_REAL_DATA = True          # False = use the bundled simulated prices
    INDEX = "^SSMI"               # Swiss Market Index (for the US use "^GSPC")
    TICKERS = {                   # ticker: sector
        "NESN.SW": "Consumer staples", "NOVN.SW": "Health care", "ROG.SW": "Health care", "UBSG.SW": "Financials",
        "ZURN.SW": "Financials", "ABBN.SW": "Industrials", "CFR.SW": "Consumer discretionary", "SIKA.SW": "Materials",
        "LONN.SW": "Health care", "GIVN.SW": "Materials", "SREN.SW": "Financials", "HOLN.SW": "Materials",
        "SCMN.SW": "Communication", "ALC.SW": "Health care", "GEBN.SW": "Industrials", "PGHN.SW": "Financials",
        "SLHN.SW": "Financials", "KNIN.SW": "Industrials", "LOGN.SW": "Technology", "SGSN.SW": "Industrials",
    }
    START, END = "2010-01-01", "2024-12-31"
    RF_ANNUAL = 0.005             # risk-free rate used for excess returns (roughly the CHF average)
    # US example: INDEX = "^GSPC"; TICKERS = {"AAPL": "Technology", "MSFT": "Technology", "JPM": "Financials", ...}
    '''),
    md("## 1. Download prices and convert to monthly returns"),
    code('''
    import subprocess, sys, warnings
    warnings.filterwarnings("ignore")

    def load_prices():
        if USE_REAL_DATA:
            try:
                try:
                    import yfinance as yf
                except ImportError:
                    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "yfinance"], check=False)
                    import yfinance as yf
                raw = yf.download(list(TICKERS) + [INDEX], start=START, end=END, auto_adjust=True, progress=False)["Close"]
                raw.index = pd.to_datetime(raw.index).tz_localize(None)
                try:
                    monthly = raw.resample("ME").last()
                except ValueError:                      # older pandas
                    monthly = raw.resample("M").last()
                if monthly[INDEX].notna().sum() > 36:
                    return monthly, dict(TICKERS), INDEX, "Yahoo Finance (real data)"
                print("Download returned too little data; using the simulated dataset.")
            except Exception as e:
                print("Download failed:", repr(e)[:200], "\\nUsing the simulated dataset instead.")
        p = pd.read_csv(DATA + "capstone_prices.csv", index_col=0, parse_dates=True)
        sec = pd.read_csv(DATA + "capstone_sectors.csv").set_index("ticker")["sector"].to_dict()
        return p, sec, "INDEX", "bundled SIMULATED data"

    prices, SECTORS, IDX, SOURCE = load_prices()
    prices = prices.dropna(axis=1, thresh=36)              # need at least 3 years of history
    stocks = [c for c in prices.columns if c != IDX]
    print(f"Source: {SOURCE} | {len(prices)} months | {len(stocks)} stocks | {prices.index[0]:%Y-%m} to {prices.index[-1]:%Y-%m}")

    rets = prices.pct_change().iloc[1:]
    rf = (1 + RF_ANNUAL) ** (1 / 12) - 1
    ex = rets - rf                                          # monthly excess returns
    (prices / prices.bfill().iloc[0]).plot(legend=False, alpha=0.6, figsize=(10, 4), logy=True, title="Growth of 1 (log scale)")
    plt.show()
    '''),
    md("### Summary statistics (annualised)"),
    code('''
    summary = pd.DataFrame({
        "mean return": rets.mean() * 12,
        "volatility": rets.std() * np.sqrt(12),
        "months": rets.count(),
    })
    summary["Sharpe"] = (summary["mean return"] - RF_ANNUAL) / summary["volatility"]
    summary.sort_values("Sharpe", ascending=False).round(3)
    '''),
    md("**Your turn:** which stock had the best risk-adjusted return? Is it the same as the highest raw return?"),
    md("## 2. CAPM betas for every stock, with diagnostics\nRegress each stock’s excess return on the index excess return; record beta, alpha, R², Breusch–Pagan and Durbin–Watson."),
    code('''
    from statsmodels.stats.diagnostic import het_breuschpagan
    from statsmodels.stats.stattools import durbin_watson

    rows = []
    for s in stocks:
        d = ex[[s, IDX]].dropna()
        m = sm.OLS(d[s], sm.add_constant(d[IDX])).fit()
        rows.append({"stock": s, "sector": SECTORS.get(s, "?"), "beta": m.params[IDX], "t(beta=1)": (m.params[IDX] - 1) / m.bse[IDX],
                     "alpha (ann.)": m.params["const"] * 12, "t(alpha)": m.tvalues["const"], "R2": m.rsquared,
                     "BP p": het_breuschpagan(m.resid, m.model.exog)[1], "DW": durbin_watson(m.resid)})
    capm = pd.DataFrame(rows).set_index("stock").sort_values("beta")
    capm.round(3)
    '''),
    code('''
    ax = capm["beta"].plot.barh(figsize=(8, 6), color=["C3" if b > 1 else "C0" for b in capm["beta"]])
    ax.axvline(1, color="k", lw=1); ax.set_title("CAPM beta (red = more volatile than the market)"); plt.show()
    print("Stocks with significant alpha at 5%:", list(capm.index[capm["t(alpha)"].abs() > 1.96]) or "none")
    print("Stocks with conditional heteroskedasticity (BP p < 0.05):", list(capm.index[capm["BP p"] < 0.05]) or "none")
    '''),
    md("""
    Real alphas are rarely significant: that is the efficient-market lesson. Where Breusch–Pagan fires, use White standard
    errors before trusting any t-stat.

    **Your turn:** for the stock with the highest beta, re-estimate with `cov_type="HC1"` and compare the t-stat on beta.
    """),
    code("# Your code here\n"),
    md("## 3. Build a momentum factor and run a two-factor model\nEach month, rank stocks on their return from t−12 to t−1 (skipping the latest month), go long the top third and short the bottom third. The signal only uses past prices, so there is no look-ahead bias."),
    code('''
    mom_signal = (prices[stocks].shift(1) / prices[stocks].shift(12) - 1).loc[rets.index]   # known at the start of each month
    def long_short(signal, r, frac=1/3):
        out = []
        for t in r.index:
            s = signal.loc[t].dropna()
            if len(s) < 6:
                out.append(np.nan); continue
            n = max(1, int(len(s) * frac))
            top, bot = s.nlargest(n).index, s.nsmallest(n).index
            out.append(r.loc[t, top].mean() - r.loc[t, bot].mean())
        return pd.Series(out, index=r.index)
    MOM = long_short(mom_signal, rets[stocks]).rename("MOM")
    print(f"Momentum factor: mean {MOM.mean()*12:.2%} a year, t = {MOM.mean()/MOM.std()*np.sqrt(MOM.count()):.2f}")

    two = []
    for s in stocks:
        d = pd.concat([ex[s], ex[IDX], MOM], axis=1).dropna()
        m = sm.OLS(d[s], sm.add_constant(d[[IDX, "MOM"]])).fit()
        two.append({"stock": s, "beta_mkt": m.params[IDX], "beta_mom": m.params["MOM"], "t_mom": m.tvalues["MOM"], "adj R2": m.rsquared_adj,
                    "adj R2 CAPM": capm.loc[s, "R2"] - (1 - capm.loc[s, "R2"]) / (len(d) - 2)})
    pd.DataFrame(two).set_index("stock").round(3)
    '''),
    md("**Your turn:** build a *low-volatility* factor the same way (long the third with the lowest trailing 12-month volatility, short the highest) and add it as a third factor. Does adjusted R² improve?"),
    code("# Your code here\n"),
    md("## 4. Time-series analysis of the index"),
    code('''
    from statsmodels.tsa.stattools import adfuller, acf
    from statsmodels.stats.diagnostic import het_arch
    level = np.log(prices[IDX].dropna()); r_idx = rets[IDX].dropna()
    for name, series in [("log price level", level), ("monthly return", r_idx)]:
        t, p, *_ = adfuller(series, maxlag=0, autolag=None)
        print(f"Dickey-Fuller on {name:16}: t = {t:6.2f}, p = {p:.3f} → {'unit root' if p > 0.05 else 'stationary'}")

    d = pd.DataFrame({"r": r_idx, "lag": r_idx.shift(1)}).dropna()
    ar1 = sm.OLS(d["r"], sm.add_constant(d["lag"])).fit()
    print(f"AR(1) on returns: b1 = {ar1.params['lag']:.3f}, p = {ar1.pvalues['lag']:.3f}  (prices ≈ random walk if insignificant)")
    print("Residual autocorrelation t-stats, lags 1-6:", np.round(acf(ar1.resid, nlags=6, fft=False)[1:] * np.sqrt(len(d)), 2))
    print(f"ARCH(1) test p-value: {het_arch(r_idx - r_idx.mean(), nlags=1)[1]:.4f}")

    vol = r_idx.rolling(12).std() * np.sqrt(12)
    fig, ax = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    ax[0].plot(r_idx); ax[0].set_title("Monthly index return"); ax[1].plot(vol, color="C3"); ax[1].set_title("Rolling 12-month volatility")
    plt.show()
    '''),
    md("**Your turn:** run the same tests on the momentum factor `MOM`. Is it stationary? Does its volatility cluster?"),
    code("# Your code here\n"),
    md("## 5. PCA on stock returns: how much is just “the market”?"),
    code('''
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    R = rets[stocks].dropna()                                 # common sample with no gaps
    Zr = StandardScaler().fit_transform(R)
    pca = PCA().fit(Zr)
    print("Variance share of PC1-PC5:", np.round(pca.explained_variance_ratio_[:5], 3))
    pc1 = pd.Series(pca.transform(Zr)[:, 0], index=R.index)
    print("Correlation of PC1 scores with the index return:", round(abs(pc1.corr(rets.loc[R.index, IDX])), 3))
    load = pd.DataFrame(pca.components_[:2].T, index=stocks, columns=["PC1", "PC2"])
    load["sector"] = [SECTORS.get(s, "?") for s in stocks]
    load.sort_values("PC2").round(3)
    '''),
    md("PC1 is the market. PC2 often splits defensive from cyclical stocks: look at which sectors sit at each end."),
    md("## 6. Cluster the stocks"),
    code('''
    from sklearn.cluster import KMeans
    from scipy.cluster.hierarchy import linkage, dendrogram
    from scipy.spatial.distance import squareform

    feat = pd.DataFrame({"beta": capm["beta"], "vol": summary["volatility"], "mean": summary["mean return"],
                         "pc1": load["PC1"], "pc2": load["PC2"]}).loc[stocks].dropna()
    km = KMeans(n_clusters=4, n_init=10, random_state=0).fit(StandardScaler().fit_transform(feat))
    print(pd.crosstab(pd.Series(km.labels_, index=feat.index, name="cluster"), pd.Series([SECTORS.get(s, "?") for s in feat.index], index=feat.index, name="sector")))

    dist = 1 - R.corr()                                       # correlation distance between stocks
    Lk = linkage(squareform(dist.values, checks=False), method="average")
    plt.figure(figsize=(10, 4)); dendrogram(Lk, labels=list(R.columns), leaf_rotation=90); plt.title("Hierarchical clustering on return correlations"); plt.show()
    '''),
    md("**Your turn:** do stocks from the same sector merge early in the dendrogram? Which stock is the odd one out?"),
    md("## 7. Backtest three strategies\nMonthly rebalancing, equal weights, 0.10% trading cost per unit of turnover. Signals use only information available at the start of each month."),
    code('''
    COST = 0.001

    def backtest(weights):
        """weights: DataFrame (months x stocks) decided at the start of each month."""
        w = weights.fillna(0)
        gross = (w * rets[stocks].fillna(0)).sum(axis=1)
        turnover = w.diff().abs().sum(axis=1).fillna(w.abs().sum(axis=1))
        return gross - COST * turnover

    def top_n(signal, n=5, largest=True):
        w = pd.DataFrame(0.0, index=signal.index, columns=signal.columns)
        for t in signal.index:
            s = signal.loc[t].dropna()
            if len(s) >= n:
                pick = s.nlargest(n).index if largest else s.nsmallest(n).index
                w.loc[t, pick] = 1 / n
        return w

    available = rets[stocks].notna().astype(float)
    ew = available.div(available.sum(axis=1), axis=0)
    roll_beta = rets[stocks].rolling(36, min_periods=24).cov(rets[IDX]).div(rets[IDX].rolling(36, min_periods=24).var(), axis=0).shift(1)
    strategies = {
        "Index": rets[IDX],
        "Equal weight": backtest(ew),
        "Momentum top 5": backtest(top_n(mom_signal, 5)),
        "Low beta top 5": backtest(top_n(roll_beta, 5, largest=False)),
    }
    start = mom_signal.dropna(how="all").index[0]
    perf = pd.DataFrame(strategies).loc[start:]

    def stats(r):
        g = (1 + r).cumprod(); dd = g / g.cummax() - 1
        return pd.Series({"CAGR": g.iloc[-1] ** (12 / len(r)) - 1, "volatility": r.std() * np.sqrt(12),
                          "Sharpe": (r.mean() * 12 - RF_ANNUAL) / (r.std() * np.sqrt(12)), "max drawdown": dd.min(), "hit rate": (r > 0).mean()})
    print(perf.apply(stats).T.round(3))
    (1 + perf).cumprod().plot(logy=True, figsize=(10, 4), title="Growth of 1 (log scale)"); plt.show()
    '''),
    md("""
    **Be sceptical of any backtest.** This one has **survivorship bias**: the stock list is today's index members, which by
    definition survived and grew. A fair test would use the index members as they were at each date. Other traps:
    look-ahead bias (avoided here with `.shift`), data snooping (trying many strategies and reporting the best), and costs.

    **Your turn:** raise `COST` to 0.5%. Which strategy suffers most, and why? (Hint: compare turnover.)
    """),
    code("# Your code here\n"),
    md("## 8. Machine learning: can we predict next month’s winners?\nTarget: does a stock beat the cross-sectional median next month? Features known at the start of the month. Train on the first 70% of months, test on the last 30% (a walk-forward split; never shuffle time series)."),
    code('''
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.metrics import roc_auc_score

    feats = {
        "mom_12_1": mom_signal,
        "reversal_1m": rets[stocks].shift(1),
        "vol_12m": rets[stocks].rolling(12).std().shift(1),
        "beta_36m": roll_beta,
    }
    panel = pd.concat({k: v.stack() for k, v in feats.items()}, axis=1)
    target = rets[stocks].gt(rets[stocks].median(axis=1), axis=0).astype(int).where(rets[stocks].notna())
    panel["y"] = target.stack()
    panel = panel.dropna()
    dates = panel.index.get_level_values(0).unique().sort_values()
    cut = dates[int(len(dates) * 0.7)]
    train, test = panel[panel.index.get_level_values(0) < cut], panel[panel.index.get_level_values(0) >= cut]
    X_cols = list(feats)
    models = {"Logistic": make_pipeline(StandardScaler(), LogisticRegression()),
              "Random forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=20, random_state=0)}
    for name, mdl in models.items():
        mdl.fit(train[X_cols], train["y"])
        print(f"{name:14} train AUC {roc_auc_score(train['y'], mdl.predict_proba(train[X_cols])[:, 1]):.3f} | "
              f"test AUC {roc_auc_score(test['y'], mdl.predict_proba(test[X_cols])[:, 1]):.3f}")
    print(f"Train: {len(train)} stock-months to {cut:%Y-%m}; test: {len(test)} stock-months after")
    '''),
    md("""
    A test AUC near **0.50** means the model is barely better than a coin flip, which is normal for monthly stock returns.
    A random forest with a much higher *train* AUC is overfitting noise. In finance, an out-of-sample AUC of 0.52–0.55
    that holds up over time can already be valuable.

    **Your turn (final project):**
    1. Swap in another market: change `INDEX` and `TICKERS` in section 0 (e.g. US mega-caps) and rerun everything.
    2. Add a feature (e.g. distance from the 52-week high) to section 8. Does test AUC improve?
    3. Turn the model's predictions into a portfolio (buy the 5 highest predicted probabilities each test month) and backtest it with the function from section 7.
    4. Write three sentences for an investment committee: what worked, what did not, and what biases remain.
    """),
    code("# Your code here\n"),
]
