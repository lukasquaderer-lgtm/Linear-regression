# Analyst Lab — learn to analyse a bank or insurer like an equity analyst

An interactive Streamlit app that walks you through a full company analysis in ten stages — from understanding the business to writing an investment thesis. It is a **learning tool, not a stock picker**: you enter the data, do the calculations, form the hypotheses and write the interpretations. The app checks your work, explains mistakes and only then shows its own view.

It comes with five companies: **UBS, LLB, Swiss Life, Swiss Re and PrismaLife**. You can add more.

## Quick start

```bash
cd company-analysis-lab
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501. Your work is saved automatically in `company-analysis-lab/workspace/` (git-ignored).

### Web version (no installation)

`web/` contains the same app as a single self-contained web page, published as a claude.ai Artifact. Same ten stages, quizzes, spaced repetition, datasets and validation, ported to JavaScript and React. Your work is saved to your Claude account when the page runs there, otherwise in the browser.

```bash
cd company-analysis-lab/web
npm install
npm run build   # exports the datasets from Python, then writes dist/analyst-lab.html
npm test        # JS logic tests; PARITY_FILE=… also checks results against the Python version
```

`dist/analyst-lab.html` also opens directly in a browser (charts load Plotly from jsDelivr). Add `#unlock-all` to the URL to unlock every stage.

## The ten stages

You must complete each stage before the next one unlocks. Completed stages stay open for revisiting.

| # | Stage | What you do | What the app does after you commit |
|---|---|---|---|
| 1 | Understand the Business | Answer seven questions and write a 3–5 sentence summary in your own words | Compares your answers with an analyst reference, key point by key point (English and German keywords) |
| 2 | Collect Financial Data | Build a 5-year table, fill the industry KPIs from the annual report, tick figures as verified, import CSV/Excel | Flags missing, impossible and inconsistent values (balance-sheet identity, EPS × shares, CET1 ÷ RWA, decimal-vs-percent, m-vs-bn) |
| 3 | Historical Trend Analysis | Calculate YoY growth and CAGR yourself, judge each trend and explain *why* | Checks your numbers, shows the full growth table and chart, a rule-based trend verdict and the analyst notes on what happened |
| 4 | Ratio Analysis | Formula → numbers required → **your calculation** → correct calculation → interpretation | Diagnoses errors (wrong inputs, year-end instead of average balances, decimal instead of percent, inverted ratio), then DuPont |
| 5 | Financial Statement Investigation | Work through the income statement, balance sheet, cash flow, changes in equity, notes and auditor's report; investigate the unusual changes the app finds | Shows the analyst notes and checks your operational/accounting and recurring/one-off classification |
| 6 | Quality of Earnings | Eight checks adapted for financials, a reported → underlying earnings bridge, an overall rating | Waterfall chart and underlying ROE |
| 7 | Risk Analysis | Rate credit, market, interest-rate, liquidity, operational, regulatory, concentration (and underwriting) risk; pick the three that matter most for value | Risk matrix and comparison with a reference view |
| 8 | Peer Comparison | Pick a peer, assess comparability, **predict** the differences | Side-by-side 5-year trends on the metrics that are actually comparable for that pair |
| 9 | Valuation | Choose methods, calculate P/E, P/B and dividend yield yourself, then move the assumptions | Live justified P/B, DDM, residual income and capital-generation DCF, sensitivity table, implied ROE, ROE-vs-P/B chart |
| 10 | Investment Thesis | Summary, 3 reasons, 3 risks, trend, capital, valuation, bull/base/bear, thesis-breakers — and *what you would still need to know before allocating CHF 10,000* | Reflection prompts and a Markdown export. **No buy/sell verdict.** |

Every important metric is labelled in English (CFA terminology) and German, e.g. *Return on equity · Eigenkapitalrendite*. Short **CFA Connection** boxes link each task to the curriculum (Financial Statement Analysis, Equity, Corporate Issuers, Fixed Income, Economics, Portfolio Management, Derivatives).

## Analyst Training Mode and spaced repetition

With *Analyst Training Mode* on (sidebar), each completed stage ends with five questions of increasing difficulty:

1. **Identify** the metric
2. **Calculate** it — usually with the company's own numbers
3. **Interpret** it
4. **Connect** several financial statements
5. **Analyst reasoning** — free text, self-assessed against a model answer

Each question is tagged with a concept. Concepts you get wrong — in quizzes *and* in your stage work (e.g. a wrong CAGR or ROE) — go into a Leitner box system and come back in later quizzes and on the **Concept review** page until you master them.

## Company data

| Company | Sector | Starter data | Notes |
|---|---|---|---|
| UBS | Bank | Core figures 2021–2025 | Reports in USD; Credit Suisse acquisition 2023 |
| LLB | Bank | Core figures 2021–2025 | ZKB Österreich acquisition 2025 |
| Swiss Life | Insurer | Core figures 2021–2025 | IFRS 4 → IFRS 17 break between 2022 and 2023 |
| Swiss Re | Insurer | Core figures 2021–2025 | US GAAP → IFRS break between 2022 and 2023 |
| PrismaLife | Insurer | **None** — collect everything yourself | Not listed; local GAAP + Solvency II; market multiples come from peers |

**Read this before relying on any number.** The starter values come from a third-party data vendor (FMP, retrieved via Bigdata.com) plus a few annual-report figures, and **have not been verified**. Vendor data maps bank and insurer accounts onto an industrial template, so some lines differ from the annual report. Industry-specific KPIs (CET1 ratio, cost/income, NII, solvency ratio, combined ratio, AuM …) are left empty on purpose: collecting and verifying them is the Stage 2 exercise. Where the vendor data was clearly inconsistent (e.g. UBS 2023 EPS), the cell is empty and has a note.

The qualitative reference notes (business model, events, risks) are written for learning and should also be checked against the companies' own reports. This is especially true for PrismaLife, where public information is limited.

### Adding a company

Use **Add a company** in the sidebar, or copy a folder in `datasets/companies/` and edit it:

- `profile.json` — name, sector (`bank`/`insurer`), currency, accounting basis per year, regulator, investor-relations link, and optionally reference notes, events, risks and company-specific quiz questions.
- `financials.csv` — one row per metric (keys from `lab/metrics.py`), one column per year, plus `source` and `note`.

### Importing data

Stage 2 accepts CSV or Excel in three layouts: wide (`metric, 2021, 2022, …`), years as rows (`year, revenue, net_income, …`) or long (`metric, year, value`). Labels in English or German are recognised (e.g. *Konzerngewinn*, *CET1 ratio*). Swiss/German number formats (`1'234.5`, `1.234,5`, `(12)`) are parsed correctly.

## Project structure

```
company-analysis-lab/
├── app.py                    Streamlit entry point: sidebar, gated navigation
├── lab/                      core logic (no Streamlit except ui.py)
│   ├── metrics.py            metric catalogue — English/German names, units, plausibility ranges
│   ├── data.py               datasets, CSV/Excel import, validation
│   ├── calculations.py       growth, CAGR, averages, trend classification, unusual changes
│   ├── ratios.py             ratio definitions, conventions, answer diagnosis, DuPont
│   ├── valuation.py          P/E, P/B, yield, justified P/B, DDM, residual income, FCFE
│   ├── visualization.py      Plotly charts (single axis, colour-blind-safe palette)
│   ├── company_analysis.py   stage registry, gating, text feedback helpers
│   ├── questions.py          quiz templates (levels 1–5), grading, spaced repetition
│   ├── cfa.py                CFA Connection notes
│   ├── storage.py            JSON persistence, export/import
│   └── ui.py                 shared Streamlit components and styling
├── stages/                   one module per stage + training (quiz/review)
├── datasets/companies/<id>/  profile.json + financials.csv per company
└── tests/                    pytest suite incl. end-to-end Streamlit AppTests
```

## Workspace, backup and instructor mode

- Everything you type is saved under `workspace/` (set `ANALYST_LAB_WORKSPACE` to use another folder).
- *Workspace → Export my work* downloads a JSON backup per company; *Restore an export* brings it back.
- `ANALYST_LAB_UNLOCK_ALL=1 streamlit run app.py` unlocks all stages (useful for teaching or reviewing).

## Tests

```bash
cd company-analysis-lab
python -m pytest -q
```

The suite covers the calculations, ratio diagnosis, valuation maths, validation and import, the quiz and spaced-repetition logic, and end-to-end runs of the app for every company and stage. The web version has its own tests (`cd web && npm test`).

---

*Learning material only — not investment advice.*
