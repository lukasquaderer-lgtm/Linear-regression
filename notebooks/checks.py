"""Answer checker for the Quant Methods Atlas notebooks.

Usage inside a notebook (after you have stored your answer in the named variables):

    check("01.1")

It prints ✅ when your answer is right, ❌ with a hint when it is not, and ⬜ if you
have not created the variables yet. Expected answers are computed from the data at
check time, so nothing is revealed by reading the output.
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

REPO = "lukasquaderer-lgtm/Linear-regression"
DATA = "../data/" if Path("../data").exists() else f"https://raw.githubusercontent.com/{REPO}/master/data/"
_cache = {}


def _csv(name):
    if name not in _cache:
        _cache[name] = pd.read_csv(DATA + name)
    return _cache[name].copy()


# ---------- helpers that rebuild the reference answers ----------
def _sm():
    import statsmodels.api as sm
    return sm


def _ols(y, X):
    sm = _sm()
    return sm.OLS(y, sm.add_constant(X)).fit()


def _credit_split():
    from sklearn.model_selection import train_test_split
    cr = _csv("credit_default.csv")
    X = pd.get_dummies(cr.drop(columns="default"), columns=["purpose"], drop_first=True, dtype=float)
    y = cr["default"]
    return train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)


def _company_Z():
    from sklearn.preprocessing import StandardScaler
    co = _csv("company_fundamentals.csv")
    feats = ["revenue_growth", "operating_margin", "pe_ratio", "dividend_yield", "beta", "debt_to_equity"]
    return co, StandardScaler().fit_transform(co[feats])


def _e_00_1():
    m = _csv("factor_returns.csv")["mkt_excess"]
    return [m.mean() * 12, m.std() * math.sqrt(12)]


def _e_00_2():
    d = _csv("factor_returns.csv"); b = d["stock_excess"] > d["mkt_excess"]
    return [int(b.sum()), float(b.mean())]


def _e_01_1():
    d = _csv("factor_returns.csv"); r = _ols(d["fund_excess"], d["mkt_excess"])
    return [r.params["mkt_excess"], r.tvalues["mkt_excess"], r.rsquared]


def _e_01_2():
    from scipy import stats
    d = _csv("factor_returns.csv"); r = _ols(d["stock_excess"], d["mkt_excess"])
    t = (r.params["mkt_excess"] - 1) / r.bse["mkt_excess"]
    return [t, bool(abs(t) > stats.t.ppf(0.975, r.df_resid))]


def _e_01_3():
    d = _csv("factor_returns.csv"); r = _ols(d["stock_excess"], d["mkt_excess"])
    f = r.get_prediction(pd.DataFrame({"const": [1.0], "mkt_excess": [8.0]})).summary_frame(alpha=0.05)
    return [f["obs_ci_lower"].iloc[0], f["obs_ci_upper"].iloc[0]]


def _m4():
    d = _csv("factor_returns.csv")
    return d, _ols(d["fund_excess"], d[["mkt_excess", "smb", "hml", "mom"]])


def _e_02_1():
    _, m = _m4()
    return [m.tvalues["mom"], bool(m.pvalues["mom"] < 0.05)]


def _e_02_2():
    d, _ = _m4(); d["noise"] = np.random.default_rng(0).normal(size=len(d))
    r = _ols(d["fund_excess"], d[["mkt_excess", "smb", "hml", "mom", "noise"]])
    return [r.rsquared, r.rsquared_adj]


def _e_02_3():
    _, m = _m4()
    return [float(m.predict(pd.DataFrame({"const": [1], "mkt_excess": [2], "smb": [-1], "hml": [0.5], "mom": [1]})).iloc[0])]


def _e_03_1():
    from statsmodels.stats.diagnostic import het_breuschpagan
    d = _csv("factor_returns.csv"); r = _ols(d["stock_excess"], d["mkt_excess"])
    p = het_breuschpagan(r.resid, r.model.exog)[1]
    return [p, bool(p < 0.05)]


def _logit():
    sm = _sm(); cr = _csv("credit_default.csv")
    dummies = pd.get_dummies(cr["purpose"], prefix="p", drop_first=True, dtype=float)
    Xl = sm.add_constant(pd.concat([cr[["income_k", "debt_to_income", "fico", "loan_to_value", "years_employed", "home_owner"]], dummies], axis=1))
    return Xl, sm.Logit(cr["default"], Xl).fit(disp=0)


def _e_03_2():
    _, lg = _logit()
    return [100 * (math.exp(10 * lg.params["fico"]) - 1)]


def _e_03_3():
    Xl, lg = _logit()
    row = pd.DataFrame([dict(const=1, income_k=50, debt_to_income=45, fico=620, loan_to_value=90, years_employed=1, home_owner=0,
                             p_debt_consolidation=0, p_home_improvement=0, p_small_business=1)])[Xl.columns]
    return [float(lg.predict(row).iloc[0])]


def _e_04_1():
    from statsmodels.tsa.stattools import adfuller
    s, p, *_ = adfuller(_csv("macro_quarterly.csv")["inflation"], maxlag=0, autolag=None)
    return [s, bool(p > 0.05)]


def _e_04_2():
    fx = _csv("macro_quarterly.csv")["fx_rate"].diff().dropna()
    d = pd.DataFrame({"y": fx, "l": fx.shift(1)}).dropna(); r = _ols(d["y"], d["l"])
    return [r.params["l"], r.pvalues["l"]]


def _e_04_3():
    x = _csv("macro_quarterly.csv")["inflation"]
    d = pd.DataFrame({"x": x, "l": x.shift(1)}).dropna(); r = _ols(d["x"], d["l"])
    b0, b1 = r.params; f = x.iloc[-1]
    for _ in range(4):
        f = b0 + b1 * f
    return [f]


def _e_04_4():
    from statsmodels.tsa.stattools import coint
    ts = _csv("macro_quarterly.csv"); p = coint(ts["gold_price"], ts["oil_price"])[1]
    return [p, bool(p > 0.05)]


def _e_05_1():
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.neighbors import KNeighborsClassifier
    Xtr, Xte, ytr, yte = _credit_split()
    return [{k: make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=k)).fit(Xtr, ytr).score(Xte, yte) for k in [1, 5, 15, 51]}]


def _e_05_2():
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.metrics import roc_auc_score
    Xtr, Xte, ytr, yte = _credit_split()
    return [roc_auc_score(yte, KNeighborsClassifier(n_neighbors=15).fit(Xtr, ytr).predict_proba(Xte)[:, 1])]


def _e_05_3():
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    Xtr, Xte, ytr, yte = _credit_split()
    p = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(Xtr, ytr).predict_proba(Xte)[:, 1]
    costs = {round(th, 2): 5 * ((p < th) & (yte == 1)).sum() + ((p >= th) & (yte == 0)).sum() for th in np.arange(0.05, 0.95, 0.05)}
    return [min(costs, key=costs.get)]


def _e_06_1():
    from sklearn.decomposition import PCA
    dy = _csv("treasury_yields.csv").set_index("month").diff().dropna()
    return [int(np.argmax(PCA().fit(dy).explained_variance_ratio_.cumsum() >= 0.95) + 1)]


def _e_06_2():
    from sklearn.decomposition import PCA
    _, Z = _company_Z()
    return [float(PCA(2).fit(Z).explained_variance_ratio_.sum())]


def _e_06_3():
    from sklearn.cluster import KMeans
    co, Z = _company_Z(); lab = KMeans(3, n_init=10, random_state=0).fit_predict(Z)
    major = pd.Series(lab).groupby(co["true_sector"]).agg(lambda s: s.mode().iloc[0])
    return [set(major[major == major["energy"]].index)]


def _e_07_1():
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.metrics import f1_score
    hl = _csv("headlines.csv")
    Xtr, Xte, ytr, yte = train_test_split(hl["headline"], hl["sentiment"], test_size=0.3, random_state=0, stratify=hl["sentiment"])
    nb = make_pipeline(CountVectorizer(ngram_range=(1, 2)), MultinomialNB()).fit(Xtr, ytr)
    return [f1_score(yte, nb.predict(Xte), average="macro")]


def _e_07_3():
    import warnings
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.neural_network import MLPClassifier
    from sklearn.metrics import roc_auc_score
    Xtr, Xte, ytr, yte = _credit_split()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        nn = make_pipeline(StandardScaler(), MLPClassifier((64, 64), max_iter=20, random_state=0)).fit(Xtr, ytr)
    return [roc_auc_score(yte, nn.predict_proba(Xte)[:, 1])]


# key: (variable names, reference function, absolute tolerances, hint)
SPECS = {
    "00.1": (["ann_mean", "ann_std"], _e_00_1, [0.01, 0.01], "Annualise the mean with × 12 and the standard deviation with × √12 (np.sqrt(12))."),
    "00.2": (["n_beat", "frac_beat"], _e_00_2, [0, 0.001], "Compare the two columns with >, then use .sum() for the count and .mean() for the fraction."),
    "00.3": (["m"], None, None, "Load macro_quarterly.csv with pd.read_csv(DATA + 'macro_quarterly.csv') into m."),
    "01.1": (["beta_fund", "t_fund", "r2_fund"], _e_01_1, [0.001, 0.01, 0.001], "Regress fund_excess on a constant plus mkt_excess; use .params, .tvalues and .rsquared."),
    "01.2": (["t_beta1", "reject_beta1"], _e_01_2, [0.01, 0], "t = (b1 − 1) / s_b1 for the stock regression; reject if |t| > critical t with n − 2 df."),
    "01.3": (["pi_lower", "pi_upper"], _e_01_3, [0.01, 0.01], "Use model.get_prediction(...).summary_frame() and the obs_ci_lower / obs_ci_upper columns (not mean_ci)."),
    "02.1": (["mom_t", "mom_significant"], _e_02_1, [0.01, 0], "Read m4.tvalues['mom'] and compare m4.pvalues['mom'] with 0.05."),
    "02.2": (["r2_noise", "adj_r2_noise"], _e_02_2, [0.0005, 0.0005], "Add noise = np.random.default_rng(0).normal(size=n) as a fifth regressor."),
    "02.3": (["pred_fund"], _e_02_3, [0.005], "Build a one-row DataFrame with const = 1 and the four factor values, then m4.predict(row)."),
    "03.1": (["bp_p_stock", "hetero_stock"], _e_03_1, [0.002, 0], "het_breuschpagan(model.resid, model.model.exog) returns (LM, p, F, p); take index 1."),
    "03.2": (["fico_change_pct"], _e_03_2, [0.2], "Percent change in odds for +10 points = 100 × (exp(10 × coef) − 1). It should be negative."),
    "03.3": (["pd_borrower"], _e_03_3, [0.005], "The row needs every column of Xl (const and all three p_ dummies) in the same order."),
    "04.1": (["df_t_infl", "unit_root_infl"], _e_04_1, [0.02, 0], "adfuller(x, maxlag=0, autolag=None) returns (t, p, ...); a unit root means you cannot reject (p > 0.05)."),
    "04.2": (["b1_dfx", "p_dfx"], _e_04_2, [0.005, 0.01], "Difference fx_rate first, then regress the change on its own lag."),
    "04.3": (["forecast_4q"], _e_04_3, [0.005], "Apply x̂ = b0 + b1·x̂ four times, starting from the last observed inflation."),
    "04.4": (["eg_p_gold", "spurious"], _e_04_4, [0.03, 0], "coint(ts['gold_price'], ts['oil_price']) returns (t, p, crit). No cointegration → spurious."),
    "05.1": (["knn_test"], _e_05_1, [0.005], "Store a dict {k: test accuracy} for k in [1, 5, 15, 51], scaling inside a pipeline."),
    "05.2": (["auc_unscaled"], _e_05_2, [0.005], "KNeighborsClassifier(n_neighbors=15) without StandardScaler; AUC on the test set."),
    "05.3": (["best_threshold"], _e_05_3, [0.051], "Try thresholds np.arange(0.05, 0.95, 0.05); cost = 5·FN + FP on the test set."),
    "06.1": (["n_pc_95"], _e_06_1, [0], "Use the cumulative explained_variance_ratio_ of PCA on yield changes."),
    "06.2": (["share_2pc"], _e_06_2, [0.002], "PCA(2) on the standardised company features; sum explained_variance_ratio_."),
    "06.3": (["merged_with_energy"], _e_06_3, None, "A Python set of sector names, e.g. {'energy', 'banks'}, that share energy's cluster when k = 3."),
    "07.1": (["nb_f1"], _e_07_1, [0.01], "Pipeline of CountVectorizer(ngram_range=(1, 2)) and MultinomialNB(); f1_score(..., average='macro')."),
    "07.3": (["auc_test_20"], _e_07_3, [0.03], "MLPClassifier((64, 64), max_iter=20, random_state=0) in a pipeline with StandardScaler."),
}


def _same(a, b, tol):
    if isinstance(b, (bool, np.bool_)):
        return bool(a) == bool(b) and isinstance(a, (bool, np.bool_))
    if isinstance(b, set):
        return set(a) == b
    if isinstance(b, dict):
        return isinstance(a, dict) and set(a) == set(b) and all(_same(a[k], b[k], tol) for k in b)
    try:
        return abs(float(a) - float(b)) <= (tol or 0) + 1e-9
    except (TypeError, ValueError):
        return False


def check(key, _quiet=False):
    """Check the exercise `key` (e.g. "01.2") against the variables in your notebook."""
    import __main__
    names, fn, tols, hint = SPECS[key]
    g = vars(__main__)
    missing = [n for n in names if n not in g]
    if missing:
        if not _quiet:
            print(f"⬜ Exercise {key}: not answered yet. Store your answer in " + ", ".join(f"`{n}`" for n in names) + ".")
        return False
    if fn is None:  # custom check for 00.3
        m = g["m"]; ok = isinstance(m, pd.DataFrame) and len(m) == 120 and "inflation" in m.columns
        print(f"✅ Exercise {key}: correct." if ok else f"❌ Exercise {key}: not quite. {hint}")
        return ok
    expected = fn()
    tols = tols or [0] * len(names)
    wrong = [n for n, e, t in zip(names, expected, tols) if not _same(g[n], e, t)]
    if not wrong:
        print(f"✅ Exercise {key}: correct.")
        return True
    print(f"❌ Exercise {key}: check " + ", ".join(f"`{n}`" for n in wrong) + f". Hint: {hint}")
    return False


def check_all(prefix):
    """Run every check for one notebook, e.g. check_all("01")."""
    keys = [k for k in SPECS if k.startswith(prefix + ".")]
    n = sum(check(k) for k in keys)
    print(f"\n{n} of {len(keys)} exercises correct.")
    return n == len(keys)
