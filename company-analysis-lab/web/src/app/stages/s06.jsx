// Stage 6 — Quality of Earnings (Qualität der Gewinne)
import React, { useState } from "react";
import * as CA from "../../lib/ca.js";
import * as D from "../../lib/data.js";
import * as C from "../../lib/calc.js";
import { Btn, Callout, Cfa, Choice, Details, Metric, NumberField, Select, StageHeader, Task, TextArea } from "../ui.jsx";
import { Chart, C as Charts } from "../charts.jsx";
import { StageFooter } from "../quiz.jsx";

const N = 6;
const STATUS = ["No issue found", "Issue found", "Not applicable"];

function checks(bank) {
  return [
    { key: "cash", en: "Net income vs cash / capital generation", de: "Gewinn vs. Cash- bzw. Kapitalgenerierung", cfa: "accruals", why: bank ? "For banks, operating cash flow mixes loans, deposits and trading flows, so it says little about earnings quality. Ask instead: does profit turn into capital (CET1) and distributions (dividends, buybacks)?" : "Compare net income with operating cash flow over several years. Persistent gaps (accruals) mean earnings are less likely to persist. For life insurers, also ask whether profit turns into solvency capital and cash remittances.", where: "Cash flow statement; capital management section; statement of changes in equity" },
    { key: "oneoff", en: "One-off gains and losses", de: "Einmalige Gewinne und Verluste", cfa: "one_offs", why: "Disposal gains, negative goodwill, litigation settlements, insurance recoveries, revaluation gains. Remove them (after tax) to see underlying earnings.", where: "Income statement 'other income'; management report 'underlying/adjusted' results; notes" },
    { key: "estimates", en: "Changes in accounting estimates", de: "Änderungen von Schätzungen", cfa: "notes", why: bank ? "Expected-credit-loss model parameters, fair-value inputs (Level 3), useful lives, pension assumptions." : "Actuarial assumptions (mortality, lapse, expenses), discount rates, CSM unlocking, investment valuations.", where: "Notes: significant accounting estimates and judgements; changes in estimates" },
    { key: "restructuring", en: "Restructuring charges", de: "Restrukturierungskosten", cfa: "one_offs", why: "Integration and restructuring costs are often presented as 'one-off' — but if they appear every year, they are part of the cost base.", where: "Income statement; notes on provisions and personnel expenses; 'underlying' reconciliation" },
    { key: "impairments", en: "Impairments", de: "Wertminderungen", cfa: "one_offs", why: "Goodwill and intangible impairments (non-cash, usually one-off but signal overpaying for an acquisition); " + (bank ? "loan impairments are recurring credit costs." : "investment impairments."), where: "Notes on goodwill/intangibles and financial assets" },
    { key: "reserves", en: "Reserve and provision changes", de: "Reserve- und Rückstellungsveränderungen", cfa: "reserves", why: bank ? "Releases of credit-loss allowances or litigation provisions boost profit without new business — check whether they can recur." : "Prior-year reserve development (releases or strengthening) changes earnings without new business; repeated releases can mean earlier over-reserving used to smooth profit.", where: bank ? "Credit risk note / provisions note" : "Notes on insurance liabilities; claims development tables; P&C prior-year development" },
    { key: "acquisitions", en: "Acquisition effects", de: "Akquisitionseffekte", cfa: "one_offs", why: "Consolidating a target adds revenue and profit that is not organic; purchase-price allocation creates amortisation or negative goodwill; integration costs follow.", where: "Note on business combinations; segment reporting; management report" },
    { key: "tax", en: "Unusual tax effects", de: "Ungewöhnliche Steuereffekte", cfa: "one_offs", why: "Recognition or write-off of deferred tax assets, tax-rate changes, settlements. Compare the effective tax rate with the statutory rate (Switzerland ≈ 12–21 % by canton; Liechtenstein 12.5 %; Germany ≈ 30 %).", where: "Income tax note (tax rate reconciliation)" },
  ];
}

const upd = (app, fn) => app.update((d) => {
  const s = (d.stages[N] ||= {});
  s.answers ||= {};
  fn(s.answers);
});

export default function Stage6({ app }) {
  const { profile, currency } = app;
  const bank = profile.sector === "bank";
  const ans = app.doc.stages?.[N]?.answers || {};
  const cks = checks(bank);
  const done = cks.filter((c) => STATUS.includes(ans.checks?.[c.key]?.status) && CA.wordCount(ans.checks?.[c.key]?.note) >= 5).length;
  const criteria = [
    [`All eight checks completed with a short note — ${done}/8`, done === 8],
    ["Underlying earnings bridge built (or confirmed that no adjustment is needed)", Boolean(ans.bridgeSaved)],
    ["Overall earnings-quality rating with justification", Boolean(ans.rating) && CA.wordCount(ans.ratingWhy) >= 15],
  ];
  return (
    <div className="page">
      <StageHeader stage={CA.STAGES[5]} profile={profile} currency={currency} />
      <div className="grid-2 wide-left">
        <Task>
          High-quality earnings are <b>recurring, cash- or capital-backed and free of aggressive estimates</b>. Run the eight checks against the annual report, build a bridge from reported to underlying net income, and rate the overall quality. {bank ? "For a bank, swap 'cash' for 'capital': does profit become CET1 capital and distributions?" : "For an insurer, watch reserve releases and investment gains."}
        </Task>
        <Cfa k="quality_earnings" />
      </div>
      <section className="section">
        <div className="section-head"><h2>1 · Eight checks</h2></div>
        <CashPanel app={app} bank={bank} />
        <div className="stack">
          {cks.map((c) => <Check key={c.key} app={app} c={c} saved={ans.checks?.[c.key] || {}} />)}
        </div>
      </section>
      <section className="section">
        <div className="section-head"><h2>2 · From reported to underlying net income</h2></div>
        <Bridge app={app} ans={ans} />
      </section>
      <section className="section">
        <div className="section-head"><h2>3 · Your verdict</h2></div>
        <Verdict app={app} ans={ans} />
      </section>
      <StageFooter app={app} n={N} criteria={criteria} />
    </div>
  );
}

function Check({ app, c, saved }) {
  const [f, setF] = useState({ status: saved.status || null, note: saved.note || "" });
  const [warn, setWarn] = useState(null);
  const done = STATUS.includes(saved.status) && CA.wordCount(saved.note) >= 5;
  const save = () => {
    if (!f.status || CA.wordCount(f.note) < 5) return setWarn("Pick a result and write at least five words.");
    setWarn(null);
    upd(app, (a) => (a.checks = { ...(a.checks || {}), [c.key]: { status: f.status, note: f.note.trim() } }));
  };
  return (
    <Details status={done ? "done" : "todo"} summary={`${c.en} · ${c.de}${done ? ` — ${saved.status}` : ""}`}>
      <p>{c.why}</p>
      <p className="muted small">Where to look: {c.where}</p>
      <Cfa k={c.cfa} />
      <Choice label="Result" options={STATUS} value={f.status} onChange={(v) => setF({ ...f, status: v })} />
      <TextArea id={`s6-note-${c.key}`} label="What did you find? (item, year, amount, page)" rows={3} value={f.note} onChange={(v) => setF({ ...f, note: v })} />
      {warn && <Callout tone="warn">{warn}</Callout>}
      <div><Btn id={`s6-save-${c.key}`} onClick={save}>Save check</Btn></div>
    </Details>
  );
}

function CashPanel({ app, bank }) {
  const ni = D.series(app.ds, "net_income");
  if (bank) {
    const div = app.ds.years.map((y) => {
      const d = D.value(app.ds, "dps", y), s = D.value(app.ds, "shares_outstanding", y);
      return [y, d !== null && s !== null ? d * s : null];
    });
    const series = { "Net income": ni };
    if (D.clean(div).length >= 2) series["Dividends declared (DPS × shares)"] = div;
    const c1 = D.series(app.ds, "cet1_capital");
    return (
      <div className="card">
        <Chart spec={Charts.compare(series, "Profit vs dividends declared", `${app.currency} m`)} label="Profit vs dividends" />
        {D.clean(c1).length >= 2 && <Chart spec={Charts.history(c1, "CET1 capital — does it grow with retained profit?", `${app.currency} m`)} label="CET1 capital" />}
        <p className="muted small">Banks: compare profit with distributions and capital build-up rather than with operating cash flow.</p>
      </div>
    );
  }
  const ocf = D.series(app.ds, "operating_cash_flow");
  if (D.clean(ocf).length < 2) return <p className="muted small">No operating cash flow data — add it in Stage 2 if the company publishes a cash flow statement.</p>;
  const sum = (s) => D.clean(s).reduce((p, [, v]) => p + v, 0);
  return (
    <div className="card">
      <Chart spec={Charts.compare({ "Net income": ni, "Operating cash flow": ocf }, "Net income vs operating cash flow", `${app.currency} m`)} label="Net income vs operating cash flow" />
      <p className="muted small">Cumulative over the period: net income {C.fmtNum(sum(ni))} vs operating cash flow {C.fmtNum(sum(ocf))} ({app.currency} m).</p>
    </div>
  );
}

const blankRow = () => ({ item: "", amount: null, kind: "Gain", tax: 20 });

function Bridge({ app, ans }) {
  const years = app.ds.years.filter((y) => D.value(app.ds, "net_income", y) !== null);
  const [year, setYear] = useState(years[years.length - 1]);
  const [rows, setRows] = useState(() => ans.bridge?.[String(year)] || [blankRow()]);
  if (!years.length) return <Callout tone="info">Net income missing.</Callout>;
  const ni = D.value(app.ds, "net_income", year);
  const savedRows = ans.bridge?.[String(year)];
  const pick = (y) => {
    setYear(+y);
    setRows(ans.bridge?.[String(y)] || [blankRow()]);
  };
  const setRow = (i, patch) => setRows(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const save = () => {
    const clean = rows.filter((r) => r.item.trim() && r.amount !== null).map((r) => ({ ...r, item: r.item.trim(), tax: r.tax ?? 0 }));
    upd(app, (a) => {
      a.bridge = { ...(a.bridge || {}), [String(year)]: clean };
      a.bridgeSaved = true;
      let u = ni;
      for (const r of clean) u += (r.kind === "Gain" ? -1 : 1) * r.amount * (1 - r.tax / 100);
      a.underlying = { ...(a.underlying || {}), [String(year)]: u };
    });
    setRows(clean.length ? clean : [blankRow()]);
  };
  let underlying = ni;
  const steps = [["Reported net income", ni, "absolute"]];
  for (const r of savedRows || []) {
    const adj = (r.kind === "Gain" ? -1 : 1) * r.amount * (1 - r.tax / 100);
    underlying += adj;
    steps.push([r.item.slice(0, 28), adj, "relative"]);
  }
  steps.push(["Underlying net income", underlying, "total"]);
  const e0 = D.value(app.ds, "total_equity", year - 1), e1 = D.value(app.ds, "total_equity", year);
  const avgE = e0 !== null && e1 !== null ? (e0 + e1) / 2 : null;
  return (
    <div className="stack">
      <Select id="s6-year" label="Year" value={String(year)} options={[...years].reverse().map((y) => ({ value: String(y), label: String(y) }))} onChange={pick} />
      <p className="muted small">List the one-off items you found. Gains are removed and losses added back, after tax. Save with no rows if you found none.</p>
      <div className="bridge-rows">
        {rows.map((r, i) => (
          <div key={i} className="bridge-row">
            <input className="cell text grow" aria-label="Item" placeholder="e.g. Negative goodwill from acquisition" value={r.item} onChange={(e) => setRow(i, { item: e.target.value })} />
            <NumberField compact label={`Pre-tax (${app.currency} m)`} value={r.amount} onChange={(v) => setRow(i, { amount: v })} />
            <Select label="Gain or loss" value={r.kind} options={[{ value: "Gain", label: "Gain" }, { value: "Loss", label: "Loss" }]} onChange={(v) => setRow(i, { kind: v })} />
            <NumberField compact label="Tax rate %" value={r.tax} onChange={(v) => setRow(i, { tax: v })} />
            <Btn kind="ghost" onClick={() => setRows(rows.filter((_, j) => j !== i))} aria-label="Remove row">Remove</Btn>
          </div>
        ))}
      </div>
      <div className="row">
        <Btn onClick={() => setRows([...rows, blankRow()])}>Add item</Btn>
        <Btn kind="primary" id="s6-bridge-save" onClick={save}>Save bridge</Btn>
      </div>
      {savedRows && (
        <>
          <Chart spec={Charts.waterfall(steps, `${year}: reported → underlying net income`, `${app.currency} m`)} label="Earnings bridge" />
          <div className="metrics">
            <Metric label="Reported" value={C.fmtNum(ni)} />
            <Metric label="Underlying" value={C.fmtNum(underlying)} />
            <Metric label="Adjustments" value={ni ? C.fmtPct((underlying / ni - 1) * 100, 1, true) : "–"} />
          </div>
          {avgE && <p className="muted small">ROE reported {((ni / avgE) * 100).toFixed(1)} % vs underlying {((underlying / avgE) * 100).toFixed(1)} % — use the underlying figure for valuation (Stage 9).</p>}
        </>
      )}
    </div>
  );
}

function Verdict({ app, ans }) {
  const [f, setF] = useState({ rating: ans.rating || null, why: ans.ratingWhy || "" });
  const [warn, setWarn] = useState(null);
  const submit = () => {
    if (!f.rating || CA.wordCount(f.why) < 15) return setWarn("Choose a rating and justify it in at least 15 words.");
    setWarn(null);
    upd(app, (a) => {
      a.rating = f.rating;
      a.ratingWhy = f.why.trim();
    });
  };
  const evs = (app.profile.events || []).filter((e) => ["one-off", "accounting", "transitional", "acquisition"].includes(e.nature));
  return (
    <div className="stack">
      <Choice label="Overall earnings quality" options={["High", "Medium", "Low"]} value={f.rating} onChange={(v) => setF({ ...f, rating: v })} />
      <TextArea id="s6-why" label="Justify with at least two pieces of evidence from your checks." rows={4} value={f.why} onChange={(v) => setF({ ...f, why: v })} />
      {warn && <Callout tone="warn">{warn}</Callout>}
      <div><Btn kind="primary" id="s6-verdict" onClick={submit}>{ans.rating ? "Update verdict" : "Submit verdict"}</Btn></div>
      {ans.rating && evs.length > 0 && (
        <div className="card">
          <p><b>Analyst notes on items that affect earnings quality</b> — did your checks catch them?</p>
          <ul>{evs.map((e) => <li key={e.title}><b>{e.year} · {e.title}</b> ({CA.NATURE_LABEL[e.nature]}): {e.detail}</li>)}</ul>
          <p className="muted small">There is no single right rating — what matters is that your evidence supports it.</p>
        </div>
      )}
    </div>
  );
}
