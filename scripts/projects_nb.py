"""Notebooks 11-13: open-ended projects on real data, plus model solutions in notebooks/solutions/."""
import textwrap
from nb_helpers import md, code, header, REPO

LOADER = '''
# Load a real dataset from the ISLP package (Introduction to Statistical Learning with Python)
import subprocess, sys
def load_islp(name):
    try:
        import ISLP
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps", "ISLP"], check=True)
        import ISLP
    return pd.read_csv(Path(ISLP.__file__).parent / "data" / f"{name}.csv")
'''


def sol_link(f):
    s = f.replace(".ipynb", "_solution.ipynb")
    return f"https://colab.research.google.com/github/{REPO}/blob/master/notebooks/solutions/{s}"


def rubric(rows):
    t = "| Criterion | Points | What earns full marks |\n|---|---|---|\n" + "\n".join(f"| {a} | {b} | {c} |" for a, b, c in rows)
    return md("## Rubric (100 points)\nScore yourself honestly when you are done, then compare with the model solution.\n\n" + t)


def task(n, title, text):
    return [md(f"### Task {n}: {title}\n\n" + textwrap.dedent(text).strip()), code("# Your work here\n")]


def project(fname, title, brief, load, tasks, rub, checklist):
    cells = header(fname, title, brief)
    cells += [code(LOADER), code(load)]
    for i, (t, x) in enumerate(tasks, 1):
        cells += task(i, t, x)
    cells += [rubric(rub),
              md("## Before you look at the solution\n" + "\n".join(f"- [ ] {c}" for c in checklist) +
                 f"\n\n**Model solution:** [open in Colab]({sol_link(fname)}). There is no single right answer; compare your reasoning, not just your numbers.")]
    return cells


# ---------------------------------------------------------------- project 11
P11 = "11_project_insurance_targeting.ipynb"
P11_CELLS = project(P11, "11 · Project: who will buy the insurance?", """
**Business problem.** A Dutch insurer wants to sell caravan (camper) insurance by direct mail. Mailing everyone is too
expensive: the budget covers **10% of its 5,822 customers**. Your job is to rank customers so that the mailed 10%
contains as many buyers as possible, and to explain to marketing *who* buys.

**Data.** The real CoIL 2000 challenge data: 85 numeric features per customer (socio-demographics of their postcode
area in columns starting with M, and ownership of other insurance products in columns starting with P and A) and the
target `Purchase` (Yes/No). Only about 6% bought.

This is an open project: no hints, no checker. Work like an analyst, then compare with the model solution.
""", '''
car = load_islp("Caravan")
print(car.shape); car.iloc[:, -6:].head()
# Some column meanings: PPERSAUT = contribution to car policies, APERSAUT = number of car policies,
# PBRAND = contribution to fire policies, MKOOPKLA = purchasing power class, MOPLLAAG = share with lower education,
# MINKGEM = average income, MOSTYPE = customer subtype, PWAPART = contribution to private third-party insurance
''', [
    ("Frame the problem", "What is the base purchase rate? If marketing mailed a random 10%, how many buyers would they reach? Define the evaluation metric you will use (hint: the metric should match the business decision, which is “who goes in the top 10%”)."),
    ("Split honestly", "Set aside a stratified 25% test set now (`random_state=0`) and do not touch it until Task 6."),
    ("Baselines", "Score two baselines with your metric using cross-validation on the training set: random ranking, and a simple rule of your choice (for example, rank by `PPERSAUT`)."),
    ("Compare at least three models", "Use pipelines and stratified 5-fold cross-validation on the training set only. Include at least one linear model and one tree ensemble. Report your metric and AUC for each."),
    ("Tune the best model", "Tune two or three hyperparameters with cross-validation. Is the gain larger than the fold-to-fold noise?"),
    ("Final test, once", "Evaluate your final model on the test set: precision in the top 10%, lift over random, and the number of buyers reached per 100 letters."),
    ("Explain the model", "Which features drive the ranking? Use permutation importance on the test set and describe the top drivers in plain words."),
    ("Recommendation", "Write five sentences for the head of marketing: how many letters, expected buyers, who to target, and the main risk of the model."),
], [
    ("Problem framing and metric", "10", "Metric matches the top-10% decision; base rate and random benchmark stated"),
    ("Leakage-safe pipeline and split", "20", "Test set untouched until the end; all preprocessing inside pipelines; stratified CV"),
    ("Model comparison", "20", "≥3 models plus baselines, compared on the same CV folds with the business metric"),
    ("Tuning", "10", "Sensible grid, CV-based, gain compared with CV noise"),
    ("Honest test evaluation", "15", "Single test evaluation; lift and buyers per 100 letters reported"),
    ("Interpretation", "15", "Permutation importance on held-out data, explained in business language"),
    ("Communication", "10", "Clear, quantified recommendation with risks"),
], ["My test set was used only once, at the end", "Every model was scored with the same folds and the same metric",
    "I compared against a random and a simple-rule baseline", "My recommendation contains numbers a manager can act on"])

P11_SOL = header("solutions/" + P11.replace(".ipynb", "_solution.ipynb"), "11 · Model solution: insurance targeting", """
One reasonable way to do the project. Your numbers will differ if you made different choices; what matters is the
process: an honest split, a metric that matches the decision, baselines, and a clear recommendation.
""") + [code(LOADER), code('''
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate, GridSearchCV
from sklearn.metrics import make_scorer, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
import warnings; warnings.filterwarnings("ignore")

car = load_islp("Caravan")
X = car.drop(columns="Purchase"); y = (car["Purchase"] == "Yes").astype(int)
base = y.mean()
print(f"1) Base rate {base:.2%}: a random 10% mailing (582 letters) reaches about {0.10 * len(y) * base:.0f} buyers")

def precision_at_top(y_true, scores, frac=0.10):
    k = int(np.ceil(frac * len(scores)))
    return np.asarray(y_true)[np.argsort(np.asarray(scores))[::-1][:k]].mean()
top10 = make_scorer(precision_at_top, response_method="predict_proba")
'''), code('''
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)     # 2) test set locked away
cv = StratifiedKFold(5, shuffle=True, random_state=0)

# 3) baselines
rng = np.random.default_rng(0)
rand = np.mean([precision_at_top(y_tr.iloc[te], rng.random(len(te))) for _, te in cv.split(X_tr, y_tr)])
rule = np.mean([precision_at_top(y_tr.iloc[te], X_tr["PPERSAUT"].iloc[te] + 1e-6 * rng.random(len(te))) for _, te in cv.split(X_tr, y_tr)])
print(f"3) precision in top 10% | random: {rand:.3f} | rule 'rank by PPERSAUT': {rule:.3f}")

# 4) model comparison on the same folds
models = {
    "Logistic (L2)": make_pipeline(StandardScaler(), LogisticRegression(C=0.05, max_iter=2000)),
    "Logistic (L1)": make_pipeline(StandardScaler(), LogisticRegression(C=0.05, penalty="l1", solver="liblinear")),
    "Random forest": RandomForestClassifier(n_estimators=400, min_samples_leaf=20, random_state=0, n_jobs=-1),
    "Gradient boosting": HistGradientBoostingClassifier(learning_rate=0.05, max_depth=3, random_state=0),
}
rows = []
for name, m in models.items():
    r = cross_validate(m, X_tr, y_tr, cv=cv, scoring={"top10": top10, "auc": "roc_auc"})
    rows.append([name, r["test_top10"].mean(), r["test_top10"].std(), r["test_auc"].mean()])
pd.DataFrame(rows, columns=["model", "precision@10%", "± std", "AUC"]).set_index("model").round(3)
'''), md("All models roughly double or triple the random hit rate, and the fold-to-fold standard deviation is large: with only ~260 buyers in training, differences of 0.01–0.02 are noise. A simple regularised logistic regression is competitive."), code('''
# 5) tune the logistic model's penalty
gs = GridSearchCV(make_pipeline(StandardScaler(), LogisticRegression(penalty="l1", solver="liblinear")),
                  {"logisticregression__C": [0.005, 0.01, 0.02, 0.05, 0.1, 0.5]}, cv=cv, scoring=top10).fit(X_tr, y_tr)
print("5) best C:", gs.best_params_, "| CV precision@10%:", round(gs.best_score_, 3))
final = gs.best_estimator_

# 6) the one and only test evaluation
s_te = final.predict_proba(X_te)[:, 1]
p10 = precision_at_top(y_te, s_te)
print(f"6) test precision@10% = {p10:.3f} | lift = {p10 / y_te.mean():.1f}x | buyers per 100 letters: {100 * p10:.0f} vs {100 * y_te.mean():.0f} at random | AUC {roc_auc_score(y_te, s_te):.3f}")
'''), code('''
# 7) what drives the ranking? (permutation importance on the held-out test set)
pi = permutation_importance(final, X_te, y_te, scoring=top10, n_repeats=20, random_state=0)
imp = pd.Series(pi.importances_mean, index=X.columns).sort_values(ascending=False).head(10)
print(imp.round(4))
coef = pd.Series(final[-1].coef_[0], index=X.columns)
print("\\nNon-zero L1 coefficients:", int((coef != 0).sum()), "of", len(coef)); print(coef[coef != 0].sort_values().round(3))
'''), md("""
### 8) Recommendation (example)
Mail the 10% of customers ranked highest by the model: on unseen data, roughly **{lift}× as many buyers per letter as a
random mailing** (about 19 buyers per 100 letters instead of 6). Buyers are concentrated among customers who already hold car insurance with us (`PPERSAUT`) and
fire insurance (`PBRAND`), and in higher purchasing-power areas, so cross-selling to existing car-policy holders is the
core of the campaign. The random forest scored slightly higher in cross-validation, but within the fold-to-fold noise,
so I chose the lasso-penalised logistic model: it keeps only about a third of the features and is easy to explain and audit. Main risk: only about 350 buyers exist in the data, so the hit rate could vary by several percentage points from
campaign to campaign; run the first wave as a test against a random control group.
""".replace("{lift}", "3"))]

# ---------------------------------------------------------------- project 12
P12 = "12_project_volume_forecasting.ipynb"
P12_CELLS = project(P12, "12 · Project: forecast tomorrow’s trading volume", """
**Business problem.** An execution desk splits large orders across days. Better forecasts of tomorrow’s market
volume mean less market impact. Build the best next-day forecast of NYSE trading volume you can, honestly evaluated.

**Data.** Real daily NYSE data, December 1962 to December 1986 (6,051 trading days):
`log_volume` (detrended log of shares traded; the target), `DJ_return` (Dow Jones daily return), `log_volatility`
(log of recent absolute returns), `day_of_week`, and `train` (True for days before 1980). Use `train == False` as
your final test period.

**Ground rule:** to forecast day *t* you may only use information available at the close of day *t − 1*
(day-of-week of day *t* is known in advance).
""", '''
nyse = load_islp("NYSE")
nyse["date"] = pd.to_datetime(nyse["date"])
print(nyse.shape); nyse.head()
''', [
    ("Explore", "Plot `log_volume` over time and its autocorrelation. Is it persistent? Stationary?"),
    ("Build features without look-ahead", "Create lags 1–5 of `log_volume`, `DJ_return` and `log_volatility`, plus day-of-week dummies. Drop rows with missing lags. Prove to yourself that no feature uses day *t* information."),
    ("Baselines", "On the test period, compute R² for (a) predicting yesterday’s value and (b) an AR(5) linear regression on lagged volume only."),
    ("Models", "Fit at least a linear model with all features and one tree ensemble. Tune using `TimeSeriesSplit` **inside the training period only**."),
    ("Evaluate", "Report test R² and RMSE for every model. Plot actual vs forecast for one year of the test period."),
    ("Diagnose", "Look at residual autocorrelation and residuals by day of week. What is the model still missing?"),
    ("Recommendation", "Which model would you deploy, and why? Mention stability, interpretability and the size of the improvement over the AR(5)."),
], [
    ("No look-ahead in features", "25", "All features lagged correctly; day-of-week the only same-day input"),
    ("Baselines", "15", "Persistence and AR(5) evaluated on the same test period"),
    ("Time-aware validation", "20", "TimeSeriesSplit within training only; test period untouched until the end"),
    ("Modelling", "15", "≥2 model families compared fairly"),
    ("Evaluation and diagnostics", "15", "R², RMSE, a forecast plot, residual checks"),
    ("Communication", "10", "Clear deployment recommendation with the size of the gain"),
], ["No feature uses information from the day being forecast", "I never shuffled the time order",
    "I beat (or honestly failed to beat) the AR(5) baseline", "My conclusion states how much better, in numbers"])

P12_SOL = header("solutions/" + P12.replace(".ipynb", "_solution.ipynb"), "12 · Model solution: volume forecasting", """
One reasonable solution. The *Introduction to Statistical Learning* authors report a test R² of about 0.41 for an
AR(5) model on this data and about 0.46 with day-of-week added; we reproduce that and then try tree ensembles.
""") + [code(LOADER), code('''
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import r2_score, mean_squared_error
from statsmodels.tsa.stattools import acf

nyse = load_islp("NYSE"); nyse["date"] = pd.to_datetime(nyse["date"])
fig, ax = plt.subplots(1, 2, figsize=(12, 3.5))
ax[0].plot(nyse["date"], nyse["log_volume"], lw=0.5); ax[0].set_title("log_volume (detrended)")
ax[1].bar(range(1, 21), acf(nyse["log_volume"], nlags=20)[1:]); ax[1].set_title("autocorrelation, lags 1-20"); plt.show()
'''), code('''
# 2) lagged features: everything known at the close of t-1
feat = pd.DataFrame(index=nyse.index)
for var in ["log_volume", "DJ_return", "log_volatility"]:
    for L in range(1, 6):
        feat[f"{var}_L{L}"] = nyse[var].shift(L)
dow = pd.get_dummies(nyse["day_of_week"], prefix="dow", drop_first=True, dtype=float)   # known in advance
data = pd.concat([nyse[["date", "log_volume", "train"]], feat, dow], axis=1).dropna()
tr, te = data[data["train"]], data[~data["train"]]
lagvol = [f"log_volume_L{L}" for L in range(1, 6)]
allf = list(feat.columns) + list(dow.columns)
print(f"train {tr['date'].min():%Y-%m-%d} to {tr['date'].max():%Y-%m-%d} ({len(tr)} days) | test {te['date'].min():%Y-%m-%d} to {te['date'].max():%Y-%m-%d} ({len(te)} days)")
'''), code('''
def report(name, pred):
    return [name, r2_score(te["log_volume"], pred), np.sqrt(mean_squared_error(te["log_volume"], pred))]

rows = [report("Persistence (yesterday)", te["log_volume_L1"])]
ar5 = LinearRegression().fit(tr[lagvol], tr["log_volume"]); rows.append(report("AR(5)", ar5.predict(te[lagvol])))
ar5d = LinearRegression().fit(tr[lagvol + list(dow.columns)], tr["log_volume"]); rows.append(report("AR(5) + day of week", ar5d.predict(te[lagvol + list(dow.columns)])))
lin = RidgeCV(alphas=np.logspace(-3, 3, 13)).fit(tr[allf], tr["log_volume"]); rows.append(report("Ridge, all features", lin.predict(te[allf])))

tscv = TimeSeriesSplit(5)
gb = GridSearchCV(HistGradientBoostingRegressor(random_state=0),
                  {"learning_rate": [0.03, 0.1], "max_depth": [2, 4], "max_iter": [200, 400]}, cv=tscv, scoring="r2").fit(tr[allf], tr["log_volume"])
rows.append(report("Gradient boosting (tuned)", gb.predict(te[allf])))
res = pd.DataFrame(rows, columns=["model", "test R²", "test RMSE"]).set_index("model").round(4)
print("best boosting params:", gb.best_params_); res
'''), code('''
pred = gb.predict(te[allf]); yr = te["date"].dt.year == 1985
plt.figure(figsize=(12, 3.5)); plt.plot(te.loc[yr, "date"], te.loc[yr, "log_volume"], lw=0.8, label="actual")
plt.plot(te.loc[yr, "date"], pred[yr.to_numpy()], lw=0.8, label="gradient boosting"); plt.legend(); plt.title("1985: actual vs forecast"); plt.show()
resid = te["log_volume"] - pred
print("residual autocorrelation lags 1-5:", np.round(acf(resid, nlags=5)[1:], 3))
print(resid.groupby(nyse.loc[te.index, "day_of_week"]).mean().round(3))
'''), md("""
### 7) Recommendation (example)
Yesterday's volume alone gives a test R² of about 0.18; an AR(5) raises it to about 0.37, and adding the day of the
week to about 0.42, in line with the textbook result. A ridge regression that also uses lagged returns and volatility is
best at about 0.46. Gradient boosting did not beat it, so the extra complexity is not worth it here. I would deploy the
ridge model: transparent, stable and cheap to re-fit daily, and keep the boosted model as a challenger to re-test each
year.
""")]

# ---------------------------------------------------------------- project 13
P13 = "13_project_market_direction.ipynb"
P13_CELLS = project(P13, "13 · Project: can you predict the market’s direction?", """
**Business problem.** A colleague claims that last weeks’ returns predict whether the S&P 500 will rise next week,
and wants to run money on it. You are asked to test the claim rigorously, statistically and economically.

**Data.** Real weekly S&P 500 data, 1990 to 2010 (1,089 weeks): `Lag1`–`Lag5` (returns of the previous five weeks, %),
`Volume` (average daily shares traded, billions), `Today` (this week’s return, %) and `Direction` (Up/Down).
Use 1990–2008 for training and 2009–2010 as the test period.

The skill this project trains is scepticism: knowing when a result is real.
""", '''
wk = load_islp("Weekly")
print(wk.shape); wk.head()
''', [
    ("The bar to beat", "What share of test weeks went up? That is the accuracy of the naive rule “always predict Up”."),
    ("Fit the colleague’s model", "Logistic regression of Direction on Lag1–Lag5 and Volume, trained on 1990–2008. Which coefficients are significant? Test accuracy and confusion matrix?"),
    ("Is it better than luck?", "Use a binomial test: is the test accuracy significantly higher than the “always Up” rate? What is the p-value?"),
    ("The garden of forking paths", "Try several variants (single lags, LDA/QDA, KNN with several k, a random forest). Note the best test accuracy, then explain why picking the best of many tries on the same test set overstates skill."),
    ("Does it make money?", "Turn the predictions into a strategy (long the S&P 500 in predicted-up weeks, cash otherwise) and compare total return, volatility and Sharpe ratio with buy-and-hold over the test period."),
    ("Walk-forward check", "Re-train every year from 2000 on (expanding window) and record accuracy year by year. Is any edge stable?"),
    ("Memo", "Write a short memo to the colleague: is there evidence of predictability, and would you allocate capital?"),
], [
    ("Correct benchmark", "15", "“Always Up” rate on the test period stated and used throughout"),
    ("Clean train/test split by time", "15", "1990–2008 train, 2009–2010 test, no shuffling"),
    ("Statistical testing", "20", "Binomial (or similar) test with a correctly interpreted p-value"),
    ("Multiple-testing awareness", "15", "Explains why the best of many models on one test set is biased"),
    ("Economic evaluation", "20", "Strategy vs buy-and-hold with return, risk and Sharpe"),
    ("Memo", "15", "Clear, sceptical, evidence-based conclusion"),
], ["I compared every accuracy with the ‘always Up’ benchmark", "I ran a significance test, not just a comparison",
    "I counted how many models I tried before picking one", "I checked whether the signal makes money after risk"])

P13_SOL = header("solutions/" + P13.replace(".ipynb", "_solution.ipynb"), "13 · Model solution: market direction", """
One reasonable solution. Spoiler: the evidence for predictability is weak, which is the most common honest answer
in return forecasting.
""") + [code(LOADER), code('''
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix

wk = load_islp("Weekly"); wk["up"] = (wk["Direction"] == "Up").astype(int)
tr, te = wk[wk["Year"] <= 2008], wk[wk["Year"] >= 2009]
always_up = te["up"].mean()
print(f"1) test weeks: {len(te)}, share up: {always_up:.3f} → 'always Up' accuracy")

cols = ["Lag1", "Lag2", "Lag3", "Lag4", "Lag5", "Volume"]
full = sm.Logit(tr["up"], sm.add_constant(tr[cols])).fit(disp=0)
print(full.summary().tables[1])
p = full.predict(sm.add_constant(te[cols])); pred = (p > 0.5).astype(int)
acc = (pred == te["up"]).mean()
print(f"2) test accuracy {acc:.3f}"); print(confusion_matrix(te["up"], pred))
'''), code('''
def binom_p(correct_pred):
    return binomtest(int(correct_pred.sum()), len(correct_pred), always_up, alternative="greater").pvalue

print(f"3) full model: accuracy {acc:.3f} vs {always_up:.3f}, one-sided binomial p = {binom_p(pred == te['up']):.3f}")

variants = {
    "Logit Lag2": (LogisticRegression(), ["Lag2"]),
    "LDA Lag2": (LinearDiscriminantAnalysis(), ["Lag2"]),
    "QDA Lag2": (QuadraticDiscriminantAnalysis(), ["Lag2"]),
    **{f"KNN k={k} Lag2": (KNeighborsClassifier(k), ["Lag2"]) for k in [1, 5, 25, 75]},
    "Logit Lag1-2": (LogisticRegression(), ["Lag1", "Lag2"]),
    "Random forest all": (RandomForestClassifier(300, min_samples_leaf=20, random_state=0), cols),
}
rows = []
for name, (m, c) in variants.items():
    pr = m.fit(tr[c], tr["up"]).predict(te[c]); ok = pr == te["up"]
    rows.append([name, ok.mean(), binom_p(ok)])
tab = pd.DataFrame(rows, columns=["model", "test accuracy", "binomial p"]).set_index("model").sort_values("test accuracy", ascending=False)
print("4)"); print(tab.round(3))
print(f"Tried {len(tab)} variants; the best p-value ignores that we picked it from {len(tab)} tries (Bonferroni threshold ≈ {0.05/len(tab):.4f})")
'''), code('''
# 5) does the best-looking model make money?
best = LogisticRegression().fit(tr[["Lag2"]], tr["up"]).predict(te[["Lag2"]])
r = te["Today"].to_numpy() / 100
strat = np.where(best == 1, r, 0.0)
def perf(x):
    return pd.Series({"total return": np.prod(1 + x) - 1, "ann. vol": x.std() * np.sqrt(52), "Sharpe (rf=0)": x.mean() / x.std() * np.sqrt(52)})
print("5)"); print(pd.DataFrame({"Logit Lag2 strategy": perf(strat), "Buy and hold": perf(r)}).round(3))

# 6) walk-forward: re-train each year on all prior data
acc_by_year = {}
for yr in range(2000, 2011):
    trn, tst = wk[wk["Year"] < yr], wk[wk["Year"] == yr]
    m = LogisticRegression().fit(trn[["Lag2"]], trn["up"])
    acc_by_year[yr] = ((m.predict(tst[["Lag2"]]) == tst["up"]).mean(), tst["up"].mean())
wf = pd.DataFrame(acc_by_year, index=["model accuracy", "always-Up accuracy"]).T
print("6)"); print(wf.round(3)); print("Years the model beat 'always Up':", int((wf.iloc[:, 0] > wf.iloc[:, 1]).sum()), "of", len(wf))
'''), md("""
### 7) Memo (example)
The full model's coefficients are mostly insignificant (only Lag2 is borderline), and its test accuracy does not
significantly beat simply predicting “Up” every week. The best variant we found (logistic regression on Lag2) looks
better, but it was chosen after trying about ten models on the same two-year test set, so its apparent edge is
overstated; even before any multiple-testing adjustment its p-value is about 0.24, so it is not significant.
Walk-forward re-training beat “always Up” in only 2 of 11 years. The Lag2 strategy did slightly better than buy-and-hold
over 2009–10 (about 37% vs 35%, with lower volatility), but two years is far too short to separate skill from luck. **Recommendation: do not allocate capital.** If the idea is pursued, pre-register
one model and test it on new data.
""")]

NOTEBOOKS = {P11: P11_CELLS, P12: P12_CELLS, P13: P13_CELLS}
SOLUTIONS = {"solutions/" + P11.replace(".ipynb", "_solution.ipynb"): P11_SOL,
             "solutions/" + P12.replace(".ipynb", "_solution.ipynb"): P12_SOL,
             "solutions/" + P13.replace(".ipynb", "_solution.ipynb"): P13_SOL}
