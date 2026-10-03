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


# ---------- notebook 09: ML from scratch ----------
def _c_09_1(g):
    f = g["sigmoid"]
    try:
        ok = abs(float(f(0)) - 0.5) < 1e-9 and np.allclose(f(np.array([-2.0, 2.0])), [0.11920292, 0.88079708], atol=1e-6)
    except Exception as e:
        return False, f"sigmoid raised {type(e).__name__}: {e}"
    return ok, "sigmoid(z) = 1 / (1 + np.exp(-z)); it must work on NumPy arrays."


def _e_09_2():
    d = _csv("factor_returns.csv")
    return [_ols(d["fund_excess"], d[["mkt_excess", "smb", "hml", "mom"]]).params.values]


def _c_09_3(g):
    f = g["gini"]
    try:
        vals = [f(np.array(v)) for v in ([0, 0, 1, 1], [1, 1, 1], [0, 1, 1, 1])]
        ok = np.allclose(vals, [0.5, 0.0, 0.375])
    except Exception as e:
        return False, f"gini raised {type(e).__name__}: {e}"
    return ok, "Gini = 1 − Σ pₖ² where pₖ is the share of each class; gini([0, 1, 1, 1]) should be 0.375."


def _e_09_4():
    from sklearn.tree import DecisionTreeClassifier
    cr = _csv("credit_default.csv")
    t = DecisionTreeClassifier(max_depth=1).fit(cr[["fico"]], cr["default"])
    return [t.tree_.threshold[0]]


def _c_09_5(g):
    f = g["wcss"]
    X = np.array([[0.0, 0.0], [0.0, 2.0], [4.0, 0.0], [6.0, 0.0]]); lab = np.array([0, 0, 1, 1]); C = np.array([[0.0, 1.0], [5.0, 0.0]])
    try:
        ok = abs(float(f(X, lab, C)) - 4.0) < 1e-9
    except Exception as e:
        return False, f"wcss raised {type(e).__name__}: {e}"
    return ok, "Sum over all points of the squared distance to their own cluster's centroid: ((X - C[labels])**2).sum()."


# ---------- notebook 10: workflow and leakage ----------
def _credit_pipe(C=1.0):
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LogisticRegression
    num = ["income_k", "debt_to_income", "fico", "loan_to_value", "years_employed", "home_owner"]
    pre = ColumnTransformer([("num", StandardScaler(), num), ("cat", OneHotEncoder(handle_unknown="ignore"), ["purpose"])])
    return Pipeline([("prep", pre), ("model", LogisticRegression(C=C, max_iter=1000))])


def _e_10_1():
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    cr = _csv("credit_default.csv")
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    return [cross_val_score(_credit_pipe(), cr.drop(columns="default"), cr["default"], cv=cv, scoring="roc_auc").mean()]


def _e_10_2():
    from sklearn.model_selection import StratifiedKFold, GridSearchCV
    cr = _csv("credit_default.csv")
    gs = GridSearchCV(_credit_pipe(), {"model__C": [0.01, 0.1, 1, 10]}, cv=StratifiedKFold(5, shuffle=True, random_state=0), scoring="roc_auc")
    gs.fit(cr.drop(columns="default"), cr["default"])
    return [gs.best_params_["model__C"]]


def _c_10_3(g):
    a = g["leak_answers"]
    right = {"leak1": "A", "leak2": "B", "leak3": "C", "leak4": "D"}
    if not isinstance(a, dict):
        return False, "leak_answers must be a dict like {'leak1': 'A', ...}."
    wrong = [k for k in right if str(a.get(k, "")).strip().upper() != right[k]]
    return not wrong, ("Look again at: " + ", ".join(wrong) + ". Ask: when would this information really be available?") if wrong else ""


def _noise_data():
    rng = np.random.default_rng(42)
    X = rng.normal(size=(200, 2000)); y = rng.integers(0, 2, 200)
    return X, y


def _e_10_4():
    from sklearn.pipeline import make_pipeline
    from sklearn.feature_selection import SelectKBest, f_classif
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    X, y = _noise_data()
    pipe = make_pipeline(SelectKBest(f_classif, k=20), LogisticRegression(max_iter=1000))
    return [cross_val_score(pipe, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=0)).mean()]


def _e_10_5():
    from sklearn.metrics import average_precision_score
    Xtr, Xte, ytr, yte = _credit_split()
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    m = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000)).fit(Xtr, ytr)
    return [average_precision_score(yte, m.predict_proba(Xte)[:, 1])]


# ---------- notebook 14: explainability ----------
def _c_14_1(g):
    v = g["additivity_gap"]
    try:
        ok = float(v) < 1e-4
    except (TypeError, ValueError):
        return False, "Store a single number: the maximum absolute difference."
    return ok, "base value + sum of SHAP values should match gbm.decision_function(X_test) (log-odds), not predict_proba."


def _e_14_2():
    import shap
    from sklearn.ensemble import GradientBoostingClassifier
    Xtr, Xte, ytr, yte = _credit_split()
    gbm = GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=0).fit(Xtr, ytr)
    i = int(np.argmax(gbm.predict_proba(Xte)[:, 1]))
    sv = shap.TreeExplainer(gbm)(Xte)
    return [str(Xte.columns[np.argmax(sv.values[i])])]


def _c_14_3(g):
    ok = str(g["leak_feature"]) == "sent_to_collections"
    return ok, "Compute the mean absolute SHAP value per column of the leaky model and take the largest."


# ---------- notebook 15: PyTorch ----------
def _e_15_1():
    d = _csv("factor_returns.csv")
    X = np.column_stack([np.ones(len(d)), d[["mkt_excess", "smb", "hml", "mom"]].to_numpy()]); y = d["fund_excess"].to_numpy()
    b = np.array([0.1, 1.0, 0.5, 0.3, 0.0])
    return [2 / len(y) * X.T @ (X @ b - y)]


# ---------- notebook 16: LLMs ----------
def _c_16_1(g):
    f = g["cosine"]
    try:
        a = float(f(np.array([1.0, 0.0]), np.array([1.0, 0.0]))); b = float(f(np.array([1.0, 0.0]), np.array([0.0, 2.0])))
        c = float(f(np.array([1.0, 2.0, 3.0]), np.array([-1.0, -2.0, -3.0])))
        ok = abs(a - 1) < 1e-9 and abs(b) < 1e-9 and abs(c + 1) < 1e-9
    except Exception as e:
        return False, f"cosine raised {type(e).__name__}: {e}"
    return ok, "cosine(a, b) = a·b / (‖a‖ ‖b‖); use np.dot and np.linalg.norm."


def _c_16_2(g):
    f = g["numbers_supported"]
    src = "Revenue rose 8% to CHF 1.24 billion; we expect margins of 14.5% next year."
    try:
        ok = f(src, [8, 1.24, 14.5]) is True and f(src, [8, 1.42]) is False and f(src, []) is True
    except Exception as e:
        return False, f"numbers_supported raised {type(e).__name__}: {e}"
    return ok, "Extract every number in the text (re.findall(r'\\d+(?:\\.\\d+)?', text)), then check each claimed value is among them; return a bool."


# ---------- notebooks 17-18: portfolio construction and risk ----------
PORT_W = {"CH_EQUITY": 0.20, "WORLD_EQUITY": 0.20, "EM_EQUITY": 0.05, "CHF_BONDS": 0.25,
          "GLOBAL_BONDS": 0.10, "GOLD": 0.05, "SWISS_REAL_ESTATE": 0.10, "COMMODITIES": 0.05}


def _assets():
    return pd.read_csv(DATA + "asset_returns_daily.csv", index_col=0, parse_dates=True)


def _e_17_1():
    r = _assets(); S = r.cov().to_numpy() * 252; w = np.full(r.shape[1], 1 / r.shape[1])
    return [float(np.sqrt(w @ S @ w))]


def _e_17_2():
    S = _assets().cov().to_numpy() * 252; ones = np.ones(len(S)); x = np.linalg.solve(S, ones)
    return [x / x.sum()]


def _e_17_3():
    from sklearn.covariance import LedoitWolf
    return [LedoitWolf().fit(_assets().to_numpy()).shrinkage_]


def _e_17_4():
    r = _assets(); S = r.cov().to_numpy() * 252; w = np.full(r.shape[1], 1 / r.shape[1])
    rc = w * (S @ w) / np.sqrt(w @ S @ w)
    return [rc / rc.sum()]


def _port():
    r = _assets()
    return r[list(PORT_W)] @ pd.Series(PORT_W)


def _e_18_1():
    return [-np.quantile(_port(), 0.01)]


def _e_18_2():
    p = _port(); q = np.quantile(p, 0.01)
    return [-p[p <= q].mean()]


def _e_18_3():
    from scipy.stats import norm
    p = _port()
    return [-(p.mean() + norm.ppf(0.01) * p.std())]


def _kupiec_ref(x, n, p):
    from scipy.stats import chi2
    pi = x / n
    ll0 = (n - x) * np.log(1 - p) + x * np.log(p)
    ll1 = (n - x) * np.log(1 - pi) + (x * np.log(pi) if x > 0 else 0.0)
    return 1 - chi2.cdf(-2 * (ll0 - ll1), 1)


def _c_18_4(g):
    f = g["kupiec_pvalue"]
    try:
        ok = all(abs(float(f(x, n, 0.01)) - _kupiec_ref(x, n, 0.01)) < 1e-6 for x, n in [(2, 250), (8, 250), (15, 500), (5, 500)])
    except Exception as e:
        return False, f"kupiec_pvalue raised {type(e).__name__}: {e}"
    return ok, "LR = −2[ln L(p) − ln L(x/n)] with ln L(q) = (n−x)·ln(1−q) + x·ln(q); p-value = 1 − chi2.cdf(LR, 1)."


def _e_18_5():
    wp = np.array([0.30, 0.20, 0.25, 0.25]); wb = np.array([0.25, 0.30, 0.25, 0.20])
    rb = np.array([0.06, 0.06, 0.09, 0.12])
    return [float(((wp - wb) * (rb - wb @ rb)).sum())]


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
    "09.2": (["sigmoid"], _c_09_1, "custom", ""),
    "09.1": (["b_ne"], _e_09_2, [1e-6], "b = (XᵀX)⁻¹ Xᵀy with a column of ones first: np.linalg.solve(X.T @ X, X.T @ y)."),
    "09.3": (["gini"], _c_09_3, "custom", ""),
    "09.4": (["best_threshold_fico"], _e_09_4, [0.51], "Try midpoints between sorted unique FICO values; keep the one with the lowest weighted Gini of the two sides."),
    "09.5": (["wcss"], _c_09_5, "custom", ""),
    "10.1": (["cv_auc"], _e_10_1, [0.002], "Pipeline(ColumnTransformer(StandardScaler on numbers, OneHotEncoder on purpose), LogisticRegression(max_iter=1000)); StratifiedKFold(5, shuffle=True, random_state=0); scoring='roc_auc'."),
    "10.2": (["best_C"], _e_10_2, [0], "GridSearchCV over {'model__C': [0.01, 0.1, 1, 10]} with the same CV; read .best_params_."),
    "10.4": (["leak_answers"], _c_10_3, "custom", ""),
    "10.5": (["cv_noise_fixed"], _e_10_4, [0.005], "Put SelectKBest(f_classif, k=20) inside make_pipeline(..., LogisticRegression(max_iter=1000)) and cross-validate the whole pipeline."),
    "14.1": (["additivity_gap"], _c_14_1, "custom", ""),
    "14.2": (["top_reason"], _e_14_2, None, "Take the column with the largest positive SHAP value for that applicant: X_test.columns[np.argmax(sv.values[i])]."),
    "14.3": (["leak_feature"], _c_14_3, "custom", ""),
    "15.1": (["grad_autograd"], _e_15_1, [1e-6], "Make b a tensor with requires_grad=True, compute loss = ((X @ b - y) ** 2).mean(), call loss.backward() and read b.grad."),
    "15.2": (["n_params"], lambda: [865], [0], "Count weights and biases of every Linear layer: sum(p.numel() for p in model.parameters())."),
    "16.1": (["cosine"], _c_16_1, "custom", ""),
    "16.2": (["numbers_supported"], _c_16_2, "custom", ""),
    "17.1": (["ew_vol"], _e_17_1, [1e-5], "Annual covariance = r.cov() * 252; volatility = sqrt(wᵀ Σ w) with w = 1/8 for every asset."),
    "17.2": (["w_gmv"], _e_17_2, [1e-6], "w = Σ⁻¹1 / (1ᵀΣ⁻¹1): x = np.linalg.solve(S, np.ones(8)); w_gmv = x / x.sum()."),
    "17.3": (["lw_delta"], _e_17_3, [1e-6], "LedoitWolf().fit(returns.to_numpy()).shrinkage_ on the daily returns."),
    "17.4": (["rc_pct_ew"], _e_17_4, [1e-6], "Risk contribution RC = w * (Σw) / σ_p; divide by σ_p (their sum) to get shares that add to 1."),
    "18.1": (["var_hist_99"], _e_18_1, [1e-7], "Historical VaR is the loss at the 1% quantile: -np.quantile(port, 0.01). Report it as a positive number."),
    "18.2": (["es_hist_99"], _e_18_2, [1e-7], "ES = minus the average of the returns at or below the 1% quantile."),
    "18.3": (["var_norm_99"], _e_18_3, [1e-7], "Parametric VaR = -(mean + norm.ppf(0.01) * std) using the daily mean and std of the portfolio."),
    "18.4": (["kupiec_pvalue"], _c_18_4, "custom", ""),
    "18.5": (["total_allocation"], _e_18_5, [1e-9], "Brinson-Fachler allocation per sector = (w_p − w_b) × (r_b,sector − R_b); sum over sectors. R_b = Σ w_b r_b."),
    "10.3": (["ap_balanced"], _e_10_5, [0.005], "StandardScaler + LogisticRegression(class_weight='balanced', max_iter=1000) on the notebook-05 split; average_precision_score on test."),
}


def _same(a, b, tol):
    if isinstance(b, (bool, np.bool_)):
        return bool(a) == bool(b) and isinstance(a, (bool, np.bool_))
    if isinstance(b, str):
        return str(a) == b
    if isinstance(b, np.ndarray):
        try:
            a = np.asarray(a, dtype=float).ravel()
            return a.shape == b.ravel().shape and np.allclose(a, b.ravel(), atol=tol or 0, rtol=0)
        except (TypeError, ValueError):
            return False
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
    if tols == "custom":
        ok, msg = fn(g)
        print(f"✅ Exercise {key}: correct." if ok else f"❌ Exercise {key}: not quite. {msg}")
        return ok
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
