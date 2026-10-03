# <Project title: one line that states the question>

> Example: *Does low-volatility investing work in Swiss equities after costs? Evidence from SMI constituents, 2010–2024.*

## Question
What decision would this analysis inform, and for whom? (2–3 sentences)

## Data
| Source | What | Period | Notes |
|---|---|---|---|
| e.g. Yahoo Finance (`yfinance`) | daily adjusted prices of SMI stocks | 2010–2024 | survivorship: today's members only |

## Method
1. Data cleaning and checks (link to the notebook)
2. Signal / model
3. Backtest design: rebalancing, costs, no look-ahead
4. Robustness checks

## Results
One chart and one table with the key numbers. State the uncertainty (t-stats, confidence intervals, sub-periods).

## Limitations
Be explicit: data biases, short sample, multiple testing, what you did not test.

## How to run
```bash
pip install -r requirements.txt
python -m pytest -q          # all tests should pass
python run_example.py        # reproduces the example backtest
```

## Project structure
```
src/quantproject/   reusable code: data loading, metrics, backtest
tests/              unit tests (pytest)
notebooks/          analysis notebooks that import from src/
data/               small raw data or download scripts (large files are git-ignored)
reports/            generated figures and reports
```
