# Quant Methods Atlas

Hands-on study material for the quantitative methods on the CFA Level II syllabus — regression, time series and machine learning — in Python.

- **`notebooks/`** — nine Jupyter notebooks. Notebooks 00–07 have worked examples and self-checking exercises: run `check("01.1")` after an exercise to get ✅ or ❌ with a hint. Notebook 08 is a capstone on real market data.
- **`data/`** — six practice datasets (simulated with a fixed seed so everyone gets the same numbers).
- **`quant-atlas.html`** — the interactive study guide: topic explanations, formulas, labs, a data workbench, 10 exam-style item sets, a model chooser and practice questions. Open it in any browser.
- **`company-analysis-lab/`** — *Analyst Lab*, a Streamlit app that teaches you to analyse banks, insurers and non-financial companies (UBS, LLB, GKB, Swiss Life, Swiss Re, PrismaLife, Roche, Novartis, Hilti) step by step, from the business model to an investment thesis, with quizzes and spaced repetition. See [its README](company-analysis-lab/README.md); run it with `cd company-analysis-lab && pip install -r requirements.txt && streamlit run app.py`, or use the single-page web version in `company-analysis-lab/web/`.

## Run the notebooks

**Google Colab (nothing to install):** click a badge below, sign in with Google, then press **Shift + Enter** on each cell. The notebooks load the data straight from this repository.

**Locally:**

```bash
git clone https://github.com/lukasquaderer-lgtm/Linear-regression.git
cd Linear-regression
pip install -r requirements.txt
jupyter lab
```

| # | Notebook | Covers | Colab |
|---|---|---|---|
| 00 | [Python quick-start](notebooks/00_python_quickstart.ipynb) | Variables, NumPy, pandas, loading a CSV, plotting | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lukasquaderer-lgtm/Linear-regression/blob/master/notebooks/00_python_quickstart.ipynb) |
| 01 | [Simple linear regression](notebooks/01_simple_linear_regression.ipynb) | CAPM beta by hand and with statsmodels; ANOVA, t-test, prediction interval | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lukasquaderer-lgtm/Linear-regression/blob/master/notebooks/01_simple_linear_regression.ipynb) |
| 02 | [Multiple regression](notebooks/02_multiple_regression.ipynb) | Four-factor model, adjusted R², F-test, AIC/BIC, nested F-test | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lukasquaderer-lgtm/Linear-regression/blob/master/notebooks/02_multiple_regression.ipynb) |
| 03 | [Misspecification and extensions](notebooks/03_misspecification_and_extensions.ipynb) | Breusch–Pagan, White & Newey–West SEs, VIF, Cook’s D, dummies, logistic regression | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lukasquaderer-lgtm/Linear-regression/blob/master/notebooks/03_misspecification_and_extensions.ipynb) |
| 04 | [Time series](notebooks/04_time_series.ipynb) | Trend models, AR(1), mean reversion, Dickey–Fuller, seasonality, ARCH, cointegration | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lukasquaderer-lgtm/Linear-regression/blob/master/notebooks/04_time_series.ipynb) |
| 05 | [Supervised ML](notebooks/05_supervised_ml.ipynb) | LASSO, logistic, KNN, SVM, CART, random forest, boosting, cross-validation, ROC | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lukasquaderer-lgtm/Linear-regression/blob/master/notebooks/05_supervised_ml.ipynb) |
| 06 | [Unsupervised ML](notebooks/06_unsupervised_ml.ipynb) | PCA on Treasury yields, k-means and hierarchical clustering | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lukasquaderer-lgtm/Linear-regression/blob/master/notebooks/06_unsupervised_ml.ipynb) |
| 07 | [Neural nets and text](notebooks/07_neural_nets_and_text.ipynb) | MLP hyperparameters, tokenisation, document-term matrix, TF-IDF, sentiment | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lukasquaderer-lgtm/Linear-regression/blob/master/notebooks/07_neural_nets_and_text.ipynb) |
| 08 | [Capstone: real market data](notebooks/08_capstone_real_market_data.ipynb) | Real Swiss stock prices from Yahoo Finance: betas, momentum factor, time-series tests, PCA, clustering, backtest, ML forecast | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/lukasquaderer-lgtm/Linear-regression/blob/master/notebooks/08_capstone_real_market_data.ipynb) |

## Datasets

| File | Rows | Use it for |
|---|---|---|
| `factor_returns.csv` | 120 months | Simple and multiple regression (CAPM, factor models, heteroskedasticity) |
| `macro_quarterly.csv` | 120 quarters | Trend models, AR, unit roots, seasonality, ARCH, cointegration |
| `treasury_yields.csv` | 240 months | PCA (level, slope, curvature) |
| `credit_default.csv` | 800 loans | Logistic regression, dummies, classification, model evaluation |
| `company_fundamentals.csv` | 150 companies | K-means and hierarchical clustering |
| `headlines.csv` | 300 headlines | Text preparation, TF-IDF, sentiment classification |
| `capstone_prices.csv`, `capstone_sectors.csv` | 180 months, 20 stocks | Fallback for the capstone if the Yahoo Finance download fails |

Load any of them with `pd.read_csv("https://raw.githubusercontent.com/lukasquaderer-lgtm/Linear-regression/master/data/<file>.csv")`.

## Rebuild

```bash
python scripts/make_data.py                    # regenerate the datasets
python scripts/build_notebooks.py --execute    # rebuild and run every notebook
```
