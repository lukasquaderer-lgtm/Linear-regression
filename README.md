# Quant Methods Atlas

Hands-on study material for the quantitative methods on the CFA Level II syllabus — regression, time series and machine learning — in Python.

- **`notebooks/`** — eight Jupyter notebooks. Each has worked examples, exercises with hints, and solutions at the end.
- **`data/`** — six practice datasets (simulated with a fixed seed so everyone gets the same numbers).
- **`quant-atlas.html`** — the interactive study guide: topic explanations, formulas, labs, a data workbench, a model chooser and practice questions. Open it in any browser.

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

## Datasets

| File | Rows | Use it for |
|---|---|---|
| `factor_returns.csv` | 120 months | Simple and multiple regression (CAPM, factor models, heteroskedasticity) |
| `macro_quarterly.csv` | 120 quarters | Trend models, AR, unit roots, seasonality, ARCH, cointegration |
| `treasury_yields.csv` | 240 months | PCA (level, slope, curvature) |
| `credit_default.csv` | 800 loans | Logistic regression, dummies, classification, model evaluation |
| `company_fundamentals.csv` | 150 companies | K-means and hierarchical clustering |
| `headlines.csv` | 300 headlines | Text preparation, TF-IDF, sentiment classification |

Load any of them with `pd.read_csv("https://raw.githubusercontent.com/lukasquaderer-lgtm/Linear-regression/master/data/<file>.csv")`.

## Rebuild

```bash
python scripts/make_data.py                    # regenerate the datasets
python scripts/build_notebooks.py --execute    # rebuild and run every notebook
```
