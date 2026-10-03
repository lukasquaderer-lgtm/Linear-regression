"""Notebooks 21 (professional practice) and 22 (your own project)."""
from nb_helpers import md, code, header, exercise, REPO

F21 = "21_professional_practice.ipynb"
CELLS21 = header(F21, "21 · Professional practice: functions, tests, Git and automated reports", """
Notebooks are great for exploring, but code you rely on every month must be **reusable, tested and versioned**.
This notebook turns analysis code into a small tested module, shows the Git workflow every quant team uses, and
automates a monthly report, the kind of task a junior quant is typically given in the first weeks.
""") + [
    md("## 1. From copy-pasted cells to functions\nIf you have pasted the same three lines into five notebooks, it belongs in a function: one name, one docstring, one place to fix bugs. Good functions take inputs as arguments (no hidden globals), validate them, and return a result instead of printing it."),
    code('''
    rets = pd.read_csv(DATA + "asset_returns_daily.csv", index_col=0, parse_dates=True)
    port = rets.mean(axis=1)                       # an equal-weight portfolio to test our functions on

    def annualized_return(returns, periods=252):
        """Geometric annual return of periodic returns."""
        r = pd.Series(returns, dtype=float).dropna()
        return (1 + r).prod() ** (periods / len(r)) - 1

    print(f"equal-weight annual return: {annualized_return(port):.2%}")
    '''),
    *exercise(1, "Write `annualized_vol(returns, periods=252)` returning the sample standard deviation (ddof=1) times √periods. It must accept a NumPy array or a pandas Series.", key="21.1"),
    *exercise(2, "Write `max_drawdown(returns)` returning the largest peak-to-trough loss of cumulative wealth as a negative number (0 if there is none). Wealth starts at 1, so a loss on the very first day counts.",
              "`wealth = np.concatenate([[1.0], np.cumprod(1 + np.asarray(returns))])`, then `(wealth / np.maximum.accumulate(wealth) - 1).min()`.", key="21.2"),
    md("## 2. A module: one file, imported everywhere\n`%%writefile` saves a cell as a file. Any notebook or script can then `import` it, so a fix in one place fixes every analysis."),
    code('''
    %%writefile quantkit.py
    """Small, tested helpers for performance analysis."""
    import numpy as np
    import pandas as pd


    def _clean(returns):
        r = pd.Series(returns, dtype=float).dropna()
        if r.empty:
            raise ValueError("returns is empty")
        return r


    def annualized_return(returns, periods=252):
        r = _clean(returns)
        return float((1 + r).prod() ** (periods / len(r)) - 1)


    def annualized_vol(returns, periods=252):
        return float(_clean(returns).std(ddof=1) * np.sqrt(periods))


    def sharpe_ratio(returns, rf=0.0, periods=252):
        r = _clean(returns) - rf / periods
        return float(r.mean() / r.std(ddof=1) * np.sqrt(periods))


    def max_drawdown(returns):
        wealth = np.concatenate([[1.0], (1 + _clean(returns)).cumprod().to_numpy()])
        return float((wealth / np.maximum.accumulate(wealth) - 1).min())


    def summary(returns, rf=0.0, periods=252):
        return pd.Series({"ann. return": annualized_return(returns, periods), "ann. vol": annualized_vol(returns, periods),
                          "Sharpe": sharpe_ratio(returns, rf, periods), "max drawdown": max_drawdown(returns)})
    '''),
    code('''
    import importlib, quantkit
    importlib.reload(quantkit)                      # pick up edits without restarting
    quantkit.summary(port, rf=0.005).round(4)
    '''),
    md("## 3. Tests: prove the code does what you think\nA test calls your function on a case where you know the answer. Run all tests after every change; if one fails, you find the bug before it reaches a client report. `pytest` finds every function whose name starts with `test_`."),
    code('''
    %%writefile test_quantkit.py
    import numpy as np
    import pytest
    import quantkit as qk


    def test_vol_definition():
        r = np.array([0.01, -0.02, 0.015, 0.0, -0.005])
        assert qk.annualized_vol(r) == pytest.approx(np.std(r, ddof=1) * np.sqrt(252))


    def test_drawdown_known_path():
        assert qk.max_drawdown([0.10, -0.50, 0.20]) == pytest.approx(-0.5)
        assert qk.max_drawdown([0.05, 0.05]) == 0.0


    def test_constant_growth_return():
        daily = 1.10 ** (1 / 252) - 1
        assert qk.annualized_return(np.full(504, daily)) == pytest.approx(0.10)


    def test_empty_input_raises():
        with pytest.raises(ValueError):
            qk.annualized_vol([np.nan])
    '''),
    code('''
    import subprocess, sys
    print(subprocess.run([sys.executable, "-m", "pytest", "-q", "test_quantkit.py"], capture_output=True, text=True).stdout[-400:])
    '''),
    md("""
    **Try breaking it:** change `ddof=1` to `ddof=0` in `quantkit.py`, rerun the two cells above, and watch a test fail
    with a message showing expected vs actual. That is the point: the test catches the mistake, not your client.
    Good test cases: known textbook answers, edge cases (empty input, one observation, all losses), and invariants
    (weights sum to 1, drawdown ≤ 0, no look-ahead).
    """),
    md("## 4. Git: version control\nGit records every change to your code with a message, so you can see what changed, why, and go back. GitHub hosts the repository so others (and recruiters) can see it. The core loop is just four commands."),
    code('''
    import os, tempfile
    repo = tempfile.mkdtemp()
    def git(*args):
        out = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
        return (out.stdout + out.stderr).strip()

    git("init", "-q"); git("config", "user.email", "you@example.com"); git("config", "user.name", "Your Name")
    with open(os.path.join(repo, "analysis.py"), "w") as f:
        f.write("RF = 0.005\\n")
    print(git("add", "analysis.py")); print(git("commit", "-q", "-m", "Add risk-free rate setting"))
    with open(os.path.join(repo, "analysis.py"), "w") as f:
        f.write("RF = 0.01   # updated to current SARON level\\n")
    print("--- what changed (git diff):"); print(git("diff"))
    git("commit", "-q", "-am", "Update risk-free rate"); print("--- history (git log):"); print(git("log", "--oneline"))
    '''),
    md(f"""
    **The everyday workflow** (in a terminal or VS Code):
    ```bash
    git clone https://github.com/<you>/<project>.git   # once
    git pull                                          # get the latest version
    git add src/ tests/ README.md                     # choose what to record
    git commit -m "Add inverse-volatility weighting"  # record it with a clear message
    git push                                          # upload to GitHub
    ```
    **From Colab:** *File → Save a copy in GitHub* commits the open notebook to any repository you own (Colab asks to
    connect your GitHub account once). Never commit passwords or API keys; keep them in Colab secrets or a `.env` file
    listed in `.gitignore`.

    **Good commit messages** say what and why in the imperative: “Fix look-ahead in monthly rebalance”, not “changes”.
    """),
    md("## 5. Reproducibility checklist\nSomeone (including you in six months) must be able to rerun your analysis and get the same numbers."),
    code('''
    import platform, sklearn, scipy
    print("Python", platform.python_version(), "| pandas", pd.__version__, "| numpy", np.__version__, "| scipy", scipy.__version__, "| scikit-learn", sklearn.__version__)
    CONFIG = {"start": "2015-01-01", "end": "2024-12-31", "rf": 0.005, "seed": 42}   # every setting in one place, at the top
    rng = np.random.default_rng(CONFIG["seed"])                                       # fixed seed = same random draws every run
    print("first random draw (identical on every run):", round(rng.normal(), 6))
    '''),
    md("""
    - Fix random seeds; put every setting in one config at the top.
    - Record package versions (`pip freeze > requirements.txt`).
    - Keep raw data read-only; every cleaning step in code, never by hand in Excel.
    - Store data snapshots or the exact download date, because vendors revise history.
    """),
    md("## 6. Automating the monthly report\nA function that takes returns and produces a finished HTML report can run every month with one call, or on a schedule (cron, GitHub Actions, a scheduled Colab notebook)."),
    code('''
    import base64, io, datetime as dt
    from IPython.display import HTML, display

    def monthly_report(returns: pd.DataFrame, weights: pd.Series, path="monthly_report.html", rf=0.005):
        port = returns[weights.index] @ weights
        last = port.index.max(); month = port.loc[str(last.to_period("M"))]
        ytd = port.loc[str(last.year)]
        stats_ = pd.DataFrame({"Year to date": quantkit.summary(ytd, rf), "Since inception": quantkit.summary(port, rf)}).T
        stats_.insert(0, "total return", [(1 + ytd).prod() - 1, (1 + port).prod() - 1])
        stats_.loc["This month"] = [(1 + month).prod() - 1] + [np.nan] * 4      # annualising one month would mislead
        stats_ = stats_.loc[["This month", "Year to date", "Since inception"]]
        contrib = (returns.loc[month.index, weights.index] * weights).sum()
        fig, ax = plt.subplots(1, 2, figsize=(10, 3.2))
        (1 + port.loc[str(last.year)]).cumprod().plot(ax=ax[0], title="Growth of 1, year to date")
        contrib.sort_values().plot.barh(ax=ax[1], title="Contribution to this month's return"); plt.tight_layout()
        buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=110); plt.close(fig)
        img = base64.b64encode(buf.getvalue()).decode()
        html = f"""<html><head><meta charset="utf-8"><title>Monthly report {last:%B %Y}</title>
        <style>body{{font-family:Arial,sans-serif;margin:32px;color:#222}} table{{border-collapse:collapse}}
        td,th{{border:1px solid #ccc;padding:4px 10px;text-align:right}}</style></head><body>
        <h2>Portfolio report: {last:%B %Y}</h2><p>Generated {dt.date.today()} from {len(port)} daily returns.</p>
        {stats_.style.format("{{:.2%}}", na_rep="–").format("{{:.2f}}", subset=["Sharpe"], na_rep="–").to_html()}
        <img src="data:image/png;base64,{img}" style="max-width:100%"></body></html>"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path, stats_

    W = pd.Series({"CH_EQUITY": 0.20, "WORLD_EQUITY": 0.20, "EM_EQUITY": 0.05, "CHF_BONDS": 0.25,
                   "GLOBAL_BONDS": 0.10, "GOLD": 0.05, "SWISS_REAL_ESTATE": 0.10, "COMMODITIES": 0.05})
    path, tbl = monthly_report(rets, W)
    print("written:", path); display(tbl.round(4))
    '''),
    md("""
    In Colab, open the file browser (folder icon, left) and download `monthly_report.html`, or send it by email from a
    scheduled job. **Your turn (no checker):** add a 1-day 99% VaR line and the top-3 risk contributors to the report,
    using functions from notebook 18, and add a test for each new function.

    ## 7. A code review checklist (use it on your own work)
    - Does every function do one thing, with a docstring and no hidden globals?
    - Is there a test for each function, including edge cases?
    - Could any step use information from the future (look-ahead)?
    - Are settings in one config and random seeds fixed?
    - Would a colleague understand the code without you explaining it?
    """),
    md("---\n## Solutions"),
    code('''
    def annualized_vol(returns, periods=252):
        return float(np.std(np.asarray(returns, dtype=float), ddof=1) * np.sqrt(periods))

    def max_drawdown(returns):
        wealth = np.concatenate([[1.0], np.cumprod(1 + np.asarray(returns, dtype=float))])
        return float((wealth / np.maximum.accumulate(wealth) - 1).min())

    print(f"vol {annualized_vol(port):.2%} | max drawdown {max_drawdown(port):.2%}")
    check_all("21")
    '''),
]

F22 = "22_your_own_project.ipynb"
CELLS22 = header(F22, "22 · Your own project: from idea to a GitHub portfolio piece", f"""
Everything so far had a dataset and a question chosen for you. A project you design yourself, on real data, written
up clearly and published on GitHub, is the strongest evidence you can show an employer that you can do the job.

This notebook gives you a **tested project template**, a menu of project ideas with data sources, a 4-week plan, the
rubric to judge your work, and a publishing checklist.
""") + [
    md("## 1. Get the project template\nThe template is a small Python package with tests, a backtester that cannot look ahead, and an example. The cell below copies it into a folder called `my_project`."),
    code(f'''
    import shutil, subprocess, sys
    from pathlib import Path
    tpl = Path("../project_template")
    if not tpl.exists():                                   # in Colab: fetch it from GitHub
        if not Path("qma_repo").exists():
            subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/{REPO}.git", "qma_repo"], check=True)
        tpl = Path("qma_repo/project_template")
    work = Path("my_project")
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(tpl, work)
    for p in sorted(work.rglob("*")):
        if p.is_file():
            print(p)
    '''),
    code('''
    run = lambda *cmd: print(subprocess.run(list(cmd), cwd=work, capture_output=True, text=True).stdout[-900:])
    run(sys.executable, "-m", "pytest", "-q")          # all tests should pass
    run(sys.executable, "run_example.py")               # reproduces an example backtest
    '''),
    md("Open `my_project/src/quantproject/backtest.py` and `my_project/tests/test_backtest.py`: one test proves the backtester never uses data from after the rebalance date. Keep tests like that as you build."),
    md("""
    ## 2. Choose a question
    A good project question is **specific, decision-relevant and answerable with free data in about four weeks**.
    Pick one of these or adapt it:

    | # | Question | Free data | Techniques |
    |---|---|---|---|
    | 1 | Does low-volatility investing work in Swiss equities after costs? | Yahoo Finance (SMI stocks) | Portfolio construction, backtest, notebook 17 |
    | 2 | How much does the CHF move when the SNB surprises? | SNB data portal (data.snb.ch), Yahoo FX | Event study, regression, time series |
    | 3 | Can a factor model explain Swiss fund returns? | Fund NAVs (Yahoo), Kenneth French data library | Multiple regression, misspecification tests |
    | 4 | A VaR model for a Swiss pension portfolio: which method passes the backtest? | Yahoo Finance ETFs | VaR/ES, Kupiec, EWMA, filtered HS |
    | 5 | Do momentum signals work in European sector ETFs? | Yahoo Finance (STOXX sector ETFs) | Walk-forward ML, leakage control |
    | 6 | What drives Swiss real-estate fund premiums to NAV? | SIX/Yahoo prices, published NAVs | Regression, panel data cleaning |
    | 7 | Sentiment of SNB or ECB statements vs market moves | Central-bank websites, Yahoo | Text analytics, LLMs (notebook 16) |
    | 8 | Is gold a better crisis hedge than CHF bonds for a Swiss investor? | Yahoo Finance | Correlation regimes, stress tests, drawdowns |

    **Scope it down.** “Predict the stock market” is not a project; “Does 12-1 momentum in 20 SMI stocks beat equal
    weight after 0.1% costs, 2010–2024?” is.
    """),
    md("## 3. Starter: download real data\nRuns in Colab (needs internet). Swap in the tickers your question needs."),
    code('''
    TICKERS = ["NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "ZURN.SW", "ABBN.SW"]
    try:
        try:
            import yfinance as yf
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "yfinance"], check=False)
            import yfinance as yf
        px = yf.download(TICKERS, start="2015-01-01", end="2024-12-31", auto_adjust=True, progress=False)["Close"]
        if px.dropna(how="all").empty:
            raise RuntimeError("no data returned")
        print(px.shape); print(px.tail(3).round(2))
        (work / "data").mkdir(exist_ok=True); px.to_csv(work / "data" / "prices.csv")
        print("saved my_project/data/prices.csv; record today's date in data/README.md")
    except Exception as e:
        print("Download not possible here:", repr(e)[:120], "→ run this in Colab, or start from the course datasets.")
    '''),
    md("""
    ## 4. A four-week plan
    | Week | Goal | Done when |
    |---|---|---|
    | 1 | Question, data, cleaning | Clean dataset saved; data-quality checks written as tests (notebook 20) |
    | 2 | Baseline and main method | Simple baseline (e.g. equal weight, buy-and-hold) and your method, both in `src/`, tested |
    | 3 | Honest evaluation | Out-of-sample or walk-forward results, costs, robustness (sub-periods, parameters), significance |
    | 4 | Write-up and publish | README with question, one chart, one table, limitations; repository public on GitHub |

    ## 5. Rubric (score yourself, 100 points)
    | Criterion | Points | Full marks when |
    |---|---|---|
    | Question | 10 | Specific, decision-relevant, answerable |
    | Data | 15 | Sources documented, cleaning in code, biases (survivorship, look-ahead) addressed |
    | Method | 15 | Appropriate technique, simple baseline included |
    | Evaluation | 25 | Out-of-sample, costs, robustness checks, uncertainty stated |
    | Code quality | 15 | Functions in `src/`, tests pass, reproducible from a fresh clone |
    | Communication | 20 | README a non-specialist can follow; limitations honest; one clear chart |

    ## 6. Publishing checklist
    - [ ] Repository is public, with a clear name (e.g. `swiss-low-vol-backtest`)
    - [ ] README starts with the question and the answer in two sentences
    - [ ] `python -m pytest -q` passes on a fresh clone; `requirements.txt` is complete
    - [ ] No API keys, passwords or licensed data committed
    - [ ] One chart and one results table in the README, with the period and costs stated
    - [ ] A “Limitations” section that a sceptical reviewer would accept
    - [ ] Link it on your CV and LinkedIn; be ready to explain one design decision and one thing you would do differently

    **In an interview**, expect: “What would make this result wrong?” Answer with the biases you checked for
    (look-ahead, survivorship, data snooping, costs), and you will stand out.
    """),
]
