"""Notebook 20: messy market data and SQL."""
from nb_helpers import md, code, header, exercise

F = "20_messy_data_and_sql.ipynb"
CELLS = header(F, "20 · Real-world data: SQL, cleaning, corporate actions and point-in-time joins", """
In practice most of a quant's time goes into data, not models. Vendor files arrive with duplicates, odd number
formats, decimal errors, gaps, ticker changes, splits, dividends, several currencies, and fundamentals that were only
published weeks after the period they describe. Get any of these wrong and every model downstream is wrong too.

The files in `data/messy/` contain all of these problems on purpose (simulated, for 10 fictional Swiss and European
stocks, 2015–2024). You will query them with **SQL**, clean them with **pandas**, and build a trustworthy dataset.
""") + [
    code('''
    import sqlite3
    M = DATA + "messy/"
    raw = pd.read_csv(M + "prices_raw.csv", dtype={"close": str})       # read prices as text first: never trust a vendor's types
    actions = pd.read_csv(M + "corporate_actions.csv", parse_dates=["ex_date"])
    changes = pd.read_csv(M + "ticker_changes.csv")
    fx = pd.read_csv(M + "fx_rates.csv", parse_dates=["date"])
    fund = pd.read_csv(M + "fundamentals.csv", parse_dates=["fiscal_year_end", "report_date"])
    members = pd.read_csv(M + "index_membership.csv", parse_dates=["start_date", "end_date"])
    print(raw.shape); print(raw.dtypes); raw.head()
    '''),
    md("## 1. SQL: the language every data team speaks\nSQL queries tables in databases. Python ships with **SQLite**, so we can load the raw files into an in-memory database and query them exactly as you would a production database."),
    code('''
    con = sqlite3.connect(":memory:")
    raw.to_sql("prices", con, index=False)
    actions.assign(ex_date=actions.ex_date.dt.strftime("%Y-%m-%d")).to_sql("actions", con, index=False)
    fx.assign(date=fx.date.dt.strftime("%Y-%m-%d")).to_sql("fx", con, index=False)
    q = lambda sql: pd.read_sql(sql, con)

    # rows, first and last date per ticker
    q("""
    SELECT ticker, COUNT(*) AS n_rows, MIN(date) AS first_date, MAX(date) AS last_date, currency
    FROM prices
    GROUP BY ticker, currency
    ORDER BY ticker
    """)
    '''),
    md("Already three discoveries: `HLVT` stops and `HELV` starts on the same day (a ticker change), `CRYS` ends in 2023 (delisted) and `GLAC` starts in 2018 (IPO). Real universes change over time."),
    code('''
    # duplicates: the same ticker and date more than once
    q("""
    SELECT ticker, date, COUNT(*) AS copies
    FROM prices
    GROUP BY ticker, date
    HAVING COUNT(*) > 1
    ORDER BY copies DESC, date
    LIMIT 5
    """)
    '''),
    code('''
    # window functions: the previous close for each row (the building block of returns)
    q("""
    SELECT ticker, date, close,
           LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close
    FROM prices
    WHERE ticker = 'BRGN' AND date BETWEEN '2019-05-10' AND '2019-05-20'
    """)
    '''),
    md("Look at 15 May 2019: the price roughly halves. A crash? No: a **2-for-1 split** (see `actions`). Raw price returns are wrong on such days."),
    code('''
    # joining tables: prices of a EUR stock with the EUR/CHF rate on the same day
    q("""
    SELECT p.date, p.ticker, p.close, f.EURCHF, ROUND(CAST(p.close AS REAL) * f.EURCHF, 2) AS close_chf
    FROM prices p
    LEFT JOIN fx f ON p.date = f.date
    WHERE p.ticker = 'DELT' AND p.date BETWEEN '2016-01-04' AND '2016-01-12'
    """)
    '''),
    md("Some rows have no FX rate: the FX file has gaps. A plain join loses information; Section 5 fixes this with an **as-of join**."),
    *exercise(1, "Write a SQL query that returns the **average volume of JURA in 2020** (on the raw `prices` table). Store the number in `sql_avg_vol`.",
              "`q(\"SELECT AVG(volume) AS v FROM prices WHERE ticker = 'JURA' AND date BETWEEN '2020-01-01' AND '2020-12-31'\")['v'].iloc[0]`", key="20.2"),
    md("## 2. Cleaning in pandas"),
    *exercise(2, "Count the fully duplicated rows in `raw` and store the number in `n_dupes`.", "`raw.duplicated().sum()`", key="20.1"),
    code('''
    odd = raw[~raw["close"].fillna("").str.fullmatch(r"\\d+(\\.\\d+)?")]
    print(len(odd), "prices are not plain numbers, for example:"); print(odd.head(6))
    '''),
    *exercise(3, "Write `parse_price(x)` that turns `\"1'234.50\"` into `1234.5`, `\"45.3\"` into `45.3`, strips spaces, and returns `np.nan` for blank or missing values.",
              "Check for missing/blank first; then `float(str(x).replace(\"'\", \"\").replace(\" \", \"\"))`. Swiss formatting uses ' as the thousands separator.", key="20.3"),
    code('''
    def _parse(x):                                             # reference version so the notebook runs before Exercise 3
        if x is None or (isinstance(x, float) and np.isnan(x)) or str(x).strip() == "":
            return np.nan
        return float(str(x).replace("'", "").replace(" ", ""))

    df = raw.drop_duplicates().copy()
    df["close"] = df["close"].map(_parse)
    df["date"] = pd.to_datetime(df["date"])
    df["pid"] = df["ticker"].replace(dict(zip(changes.old_ticker, changes.new_ticker)))   # permanent identifier
    print("missing prices after parsing:", df["close"].isna().sum())
    df = df.dropna(subset=["close"]).sort_values(["pid", "date"])
    '''),
    md("### Bad ticks\nA price typed with the decimal point in the wrong place shows up as a single-day jump of 100× that reverses the next day. Compare each price with the median of its neighbours."),
    code('''
    ref = df.groupby("pid")["close"].transform(lambda c: c.rolling(5, center=True, min_periods=1).median())
    bad = df[~(df["close"] / ref).between(0.2, 5)]
    print("bad ticks found:"); print(bad[["date", "pid", "close"]].assign(neighbour_median=ref[bad.index].round(2)))
    df = df[(df["close"] / ref).between(0.2, 5)]
    print("clean rows:", len(df), "of", len(raw), "raw rows")
    '''),
    md("""
    Notice the centred window looks at the **next** days too. That is fine for cleaning history, but a live system can only
    compare with the past: in production, flag the tick and confirm it the next day.
    """),
    md(r"""
    ## 3. Corporate actions: from prices to total returns
    An investor's return on day *t* includes dividends paid and is not affected by splits:
    $$r_t = \frac{P_t \times \text{split ratio}_t + D_t}{P_{t-1}} - 1$$
    If a vendor file is missing the ex-date row, apply the action to the next available day.
    """),
    code('''
    actions["pid"] = actions["ticker"].replace(dict(zip(changes.old_ticker, changes.new_ticker)))

    def total_returns(pid):
        p = df[df.pid == pid].set_index("date")["close"]
        ratio = pd.Series(1.0, index=p.index); div = pd.Series(0.0, index=p.index)
        for _, a in actions[actions.pid == pid].iterrows():
            on = p.index[p.index >= a.ex_date]
            if len(on) == 0:
                continue
            if a.action == "split":
                ratio[on[0]] *= a.value
            else:
                div[on[0]] += a.value
        return (p * ratio + div) / p.shift(1) - 1

    brgn = df[df.pid == "BRGN"].set_index("date")["close"]
    comp = pd.DataFrame({"price return": brgn.pct_change(), "total return": total_returns("BRGN")})
    print(comp.loc["2019-05-13":"2019-05-17"].round(4))
    (1 + comp.fillna(0)).cumprod().plot(figsize=(9, 3.5), title="BRGN: growth of 1 with raw prices vs total returns"); plt.show()
    '''),
    *exercise(4, "Compute BRGN's **total return for calendar 2019** (from the last 2018 close to the last 2019 close), including the split and the dividend. Store it in `tr_brgn_2019`.",
              "`(1 + total_returns('BRGN').loc['2019']).prod() - 1`", key="20.4"),
    md("## 4. Ticker changes\nWe mapped `HLVT` to `HELV` with a permanent identifier (`pid`). Without it, the history splits into two stocks, one that “disappears” and one that “IPOs”. Vendors provide permanent ids (PERMNO, ISIN, FIGI) for exactly this reason; always key your data on them."),
    md("## 5. Currencies: the as-of join\nTo convert a EUR price to CHF you need the FX rate **at that date or the most recent one before it**. `pd.merge_asof` does exactly that, and never looks forward."),
    code('''
    eur = df[df.currency == "EUR"].sort_values("date")
    plain = eur.merge(fx, on="date", how="left")
    asof = pd.merge_asof(eur, fx.sort_values("date"), on="date", direction="backward")
    print("rows without FX rate | plain join:", plain["EURCHF"].isna().sum(), "| as-of join:", asof["EURCHF"].isna().sum())
    asof["close_chf"] = asof["close"] * asof["EURCHF"]
    asof[["date", "pid", "close", "EURCHF", "close_chf"]].head()
    '''),
    md("## 6. Point-in-time fundamentals: avoiding look-ahead\nFY2019 earnings describe the year to 31 Dec 2019, but they were only **published in March 2020**. Joining on the fiscal year end lets your backtest trade on numbers nobody had yet."),
    code('''
    fund["pid"] = fund["ticker"].replace(dict(zip(changes.old_ticker, changes.new_ticker)))
    fund["eps"] = fund["net_income_m"] / fund["shares_m"]
    days = df[df.pid == "BRGN"][["date", "pid", "close"]].sort_values("date")
    f_b = fund[fund.pid == "BRGN"].sort_values("fiscal_year_end")
    wrong = pd.merge_asof(days, f_b[["fiscal_year_end", "eps"]].rename(columns={"fiscal_year_end": "date"}), on="date")
    right = pd.merge_asof(days, f_b[["report_date", "eps"]].rename(columns={"report_date": "date"}).sort_values("date"), on="date")
    look = pd.DataFrame({"date": days.date, "eps by fiscal year end (look-ahead)": wrong.eps.values, "eps by report date (point-in-time)": right.eps.values}).set_index("date")
    print(look.loc["2020-01-02":"2020-04-01"].iloc[::10].round(3))
    print("\\nBRGN share count changed with the 2019 split, so EPS is not comparable across it either:"); print(f_b[["fiscal_year_end", "report_date", "shares_m", "eps"]].round({"eps": 3}).tail(6))
    '''),
    *exercise(5, "Which EPS figure for BRGN could an investor actually know on **14 February 2020**? Use the latest report with `report_date` on or before that day and store EPS (net income / shares) in `eps_pit`.", key="20.5"),
    md("## 7. Survivorship bias\nBuilding an index from the stocks that exist today silently drops the ones that died. Use membership as of each date instead."),
    code('''
    tr = pd.DataFrame({pid: total_returns(pid) for pid in df.pid.unique()})
    alive_today = [p for p in tr.columns if pd.isna(members.set_index("ticker").loc[p, "end_date"])]
    def in_index(date):
        m = members[(members.start_date <= date) & (members.end_date.isna() | (members.end_date >= date))]
        return list(m.ticker)
    pit = pd.Series({d: tr.loc[d, in_index(d)].mean() for d in tr.index[1:]})
    surv = tr[alive_today].iloc[1:].mean(axis=1)
    out = pd.DataFrame({"point-in-time membership": pit, "survivors only": surv})
    ann = out.mean() * 252
    print("Annualised return:"); print(ann.round(4))
    print(f"Survivors-only index overstates the return by {ann['survivors only'] - ann['point-in-time membership']:.2%} a year")
    (1 + out.fillna(0)).cumprod().plot(figsize=(9, 3.5), title="Equal-weight index: survivorship bias"); plt.show()
    '''),
    md("""
    One stock out of ten declined and was delisted, and the survivors-only index already looks better than what an
    investor could actually have earned. In real equity databases thousands of companies delist, mostly after poor
    performance (some leave through takeovers at a premium, which works the other way), and survivor-only backtests
    typically overstate returns by a percentage point or more per year.

    ## 8. Put it together: a reusable pipeline and a data-quality report
    """),
    code('''
    def quality_report(raw, clean):
        r = raw.assign(pid=raw["ticker"].replace(dict(zip(changes.old_ticker, changes.new_ticker))))
        rep = pd.DataFrame({
            "raw rows": r.groupby("pid").size(),
            "duplicates": r[r.duplicated()].groupby("pid").size(),
            "clean rows": clean.groupby("pid").size(),
            "first date": clean.groupby("pid")["date"].min().dt.date,
            "last date": clean.groupby("pid")["date"].max().dt.date,
        }).fillna(0)
        bdays = clean.groupby("pid")["date"].agg(lambda d: len(pd.bdate_range(d.min(), d.max())))
        rep["coverage"] = (rep["clean rows"] / bdays).round(3)
        return rep
    quality_report(raw, df)
    '''),
    md("""
    **Your turn (no checker):**
    1. Convert every stock's total returns to CHF (returns in CHF = (1 + local return) × (1 + FX return) − 1) and recompute the survivorship comparison in CHF.
    2. Build a point-in-time **earnings yield** (EPS / price) signal for each stock and month, and check that no value is used before its report date.
    3. Write the whole cleaning process as one function `build_clean_panel()` that returns a tidy table (date, pid, close, total return, return in CHF), so next month's file can be processed with one call. Notebook 21 shows how to test it.
    """),
    md("---\n## Solutions"),
    code('''
    n_dupes = int(raw.duplicated().sum()); print("1) duplicate rows:", n_dupes)
    sql_avg_vol = q("SELECT AVG(volume) AS v FROM prices WHERE ticker = 'JURA' AND date BETWEEN '2020-01-01' AND '2020-12-31'")["v"].iloc[0]
    print("2) JURA average volume 2020:", round(sql_avg_vol))

    def parse_price(x):
        if x is None or (isinstance(x, float) and np.isnan(x)) or str(x).strip() == "":
            return np.nan
        return float(str(x).replace("'", "").replace(" ", ""))

    tr_brgn_2019 = (1 + total_returns("BRGN").loc["2019"]).prod() - 1; print(f"4) BRGN total return 2019: {tr_brgn_2019:.2%}")
    k = fund[(fund.pid == "BRGN") & (fund.report_date <= "2020-02-14")].sort_values("report_date").iloc[-1]
    eps_pit = k.net_income_m / k.shares_m; print(f"5) EPS known on 2020-02-14: {eps_pit:.3f} (fiscal year {k.fiscal_year_end.year})")
    check_all("20")
    '''),
]
