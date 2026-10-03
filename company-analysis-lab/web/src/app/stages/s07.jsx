// Stage 7 — Risk Analysis (Risikoanalyse)
import React, { useState } from "react";
import * as CA from "../../lib/ca.js";
import * as D from "../../lib/data.js";
import * as C from "../../lib/calc.js";
import { Btn, Callout, Cfa, Choice, Details, Metric, MultiChoice, Slider, StageHeader, Table, Task, TextArea } from "../ui.jsx";
import { Chart, C as Charts } from "../charts.jsx";
import { StageFooter } from "../quiz.jsx";

const N = 7;
const TRENDS = ["Rising", "Stable", "Falling"];
const CHANNELS = ["Earnings / ROE", "Capital / book value / payouts", "Cost of equity (uncertainty)"];
const REF_ALIAS = { interest_rate: "interest" };

export function riskTypes(bank) {
  const r = [
    { key: "credit", en: "Credit risk", de: "Kreditrisiko", cfa: "risk_credit", what: bank ? "Borrowers or counterparties fail to pay — loans, mortgages, Lombard loans, derivatives counterparties." : "Issuers in the bond portfolio default or are downgraded; reinsurers or counterparties fail to pay.", find: bank ? "Credit risk section of the risk report; IFRS 9 stages (1/2/3) and ECL allowances; Pillar 3 credit tables." : "Investment note: rating mix of fixed income; counterparty default risk in the SFCR/SST." },
    { key: "market", en: "Market risk", de: "Marktrisiko", cfa: "risk_market", what: bank ? "Equity, FX and credit-spread moves hit trading positions and — via client assets — fee income." : "Equity, real estate, credit-spread and FX moves hit investment results, solvency and asset-based fees.", find: bank ? "Market risk section (VaR, stress tests); fee income sensitivity to invested assets." : "Investment allocation; sensitivity analyses in the notes/SFCR (equity −30 %, spreads +100 bp)." },
    { key: "interest", en: "Interest-rate risk", de: "Zinsänderungsrisiko", cfa: "risk_interest", what: bank ? "Rate changes alter net interest income (deposit margins) and the value of fixed-rate assets." : "Low or falling rates squeeze the spread on guaranteed products; rate moves change the value of assets vs liabilities (duration gap).", find: bank ? "Interest-rate risk in the banking book (IRRBB) disclosures; NII sensitivity tables." : "Asset–liability management section; SST/Solvency II interest-rate sensitivities." },
    { key: "liquidity", en: "Liquidity risk", de: "Liquiditätsrisiko", cfa: "risk_liquidity", what: bank ? "Depositors withdraw faster than assets can be turned into cash (the risk that brought down Credit Suisse in 2023)." : "Mass surrenders/lapses, collateral calls on derivatives or large catastrophe payouts require cash quickly.", find: bank ? "Liquidity coverage ratio (LCR), net stable funding ratio (NSFR), funding mix." : "Liquidity management section; surrender options; derivative collateral." },
    { key: "operational", en: "Operational risk", de: "Operationelles Risiko", cfa: "risk_operational", what: "Losses from failed processes, people, IT/cyber, fraud, conduct and litigation.", find: "Operational risk section; provisions and contingent liabilities note (litigation); IT/cyber disclosures." },
    { key: "regulatory", en: "Regulatory risk", de: "Regulatorisches Risiko", cfa: "risk_regulatory", what: "Higher capital or liquidity requirements, conduct rules, tax or political changes that cap profitability or distributions.", find: "Capital management section; regulatory developments in the management report; outlook." },
    { key: "concentration", en: "Concentration risk", de: "Konzentrationsrisiko", cfa: "risk_concentration", what: "Dependence on one region, client segment, product, counterparty — or, for insurers, one peril (e.g. US hurricane).", find: "Segment and geographic information; largest exposures; peak-peril disclosures." },
  ];
  if (!bank) r.push({ key: "underwriting", en: "Insurance / underwriting risk", de: "Versicherungstechnisches Risiko", cfa: "risk_underwriting", what: "Claims, mortality, longevity, lapse or expenses turn out worse than priced — catastrophes, reserve deficiencies, pandemics.", find: "Insurance risk section; claims development tables; nat cat losses vs budget; lapse rates; SST/Solvency II underwriting risk module." });
  return r;
}

const upd = (app, fn) => app.update((d) => {
  const s = (d.stages[N] ||= {});
  s.answers ||= {};
  fn(s.answers);
});

function Tiles({ app }) {
  const ys = app.ds.years;
  const y = ys[ys.length - 1];
  const v = (k) => D.value(app.ds, k, y);
  const t = [];
  if (app.profile.sector === "bank") {
    t.push(["CET1 ratio", C.fmtPct(v("cet1_ratio")), "Capital buffer vs risk-weighted assets"]);
    t.push(["RWA density", v("rwa") && v("total_assets") ? C.fmtPct((v("rwa") / v("total_assets")) * 100) : "–", "Riskiness of the balance sheet"]);
    t.push(["NII share of income", v("net_interest_income") && v("revenue") ? C.fmtPct((v("net_interest_income") / v("revenue")) * 100) : "–", "Rate sensitivity"]);
    t.push(["Fee share of income", v("fee_income") && v("revenue") ? C.fmtPct((v("fee_income") / v("revenue")) * 100) : "–", "Market sensitivity"]);
    if (v("customer_loans") && v("customer_deposits")) t.push(["Loans / deposits", C.fmtPct((v("customer_loans") / v("customer_deposits")) * 100), "Funding / liquidity"]);
  } else {
    t.push(["Solvency ratio", C.fmtPct(v("solvency_ratio"), 0), "Capital buffer vs requirement"]);
    if (v("combined_ratio") !== null) t.push(["Combined ratio", C.fmtPct(v("combined_ratio")), "Underwriting profitability (P&C)"]);
    t.push(["Investment income share", v("investment_income") && v("revenue") ? C.fmtPct((v("investment_income") / v("revenue")) * 100) : "–", "Dependence on markets"]);
  }
  t.push(["Equity / assets", v("total_equity") && v("total_assets") ? C.fmtPct((v("total_equity") / v("total_assets")) * 100) : "–", "Unweighted leverage"]);
  return (
    <>
      <div className="metrics">{t.map(([l, val, h]) => <Metric key={l} label={l} value={val} help={h} />)}</div>
      <p className="muted small">Latest year: {y}. Indicators come from your Stage 2 dataset — they show where to look, not the answer.</p>
    </>
  );
}

export default function Stage7({ app }) {
  const { profile, currency } = app;
  const ans = app.doc.stages?.[N]?.answers || {};
  const rts = riskTypes(profile.sector === "bank");
  const names = Object.fromEntries(rts.map((r) => [r.key, r.en]));
  const order = rts.map((r) => r.key);
  const assessed = rts.filter((r) => ans.risks?.[r.key]?.saved).map((r) => ({ id: order.indexOf(r.key) + 1, key: r.key, name: r.en, ...ans.risks[r.key] }));
  const top = ans.top3 || {};
  const topOk = (top.keys || []).length === 3 && top.keys.every((k) => CA.wordCount(top.why?.[k]) >= 10) && top.submitted;
  const criteria = [
    [`Every risk type assessed with evidence — ${assessed.length}/${rts.length}`, assessed.length === rts.length],
    ["Three risks with the largest effect on value chosen and explained", Boolean(topOk)],
  ];
  return (
    <div className="page">
      <StageHeader stage={CA.STAGES[6]} profile={profile} currency={currency} />
      <div className="grid-2 wide-left">
        <Task>Use the risk report, Pillar 3 / SFCR disclosures and the notes. For every risk type rate <b>likelihood</b> and <b>impact on value</b> (1–5), the <b>trend</b>, and note your evidence. Then pick the three risks that could move the company's value the most — and explain the channel.</Task>
        <Cfa k="risk_regulatory" />
      </div>
      <Tiles app={app} />
      <section className="section">
        <div className="section-head"><h2>1 · Risk dashboard</h2></div>
        <div className="stack">{rts.map((r) => <RiskItem key={r.key} app={app} r={r} saved={ans.risks?.[r.key] || {}} />)}</div>
        {assessed.length > 0 && (
          <div className="grid-2 wide-left">
            <Chart spec={Charts.riskMatrix(assessed)} label="Risk matrix" />
            <Table columns={[{ key: "id", label: "#", num: true }, { key: "name", label: "Risk" }, { key: "likelihood", label: "L", num: true }, { key: "impact", label: "I", num: true }, { key: "score", label: "Score", num: true }, { key: "trend", label: "Trend" }]}
              rows={[...assessed].map((a) => ({ ...a, _key: a.key, score: a.likelihood * a.impact })).sort((p, q) => q.score - p.score || p.id - q.id)} />
          </div>
        )}
      </section>
      <section className="section">
        <div className="section-head"><h2>2 · The three risks that matter most for value</h2></div>
        <Top3 app={app} names={names} top={top} />
        {top.submitted && <Feedback app={app} names={names} mine={top.keys} />}
      </section>
      <StageFooter app={app} n={N} criteria={criteria} />
    </div>
  );
}

function RiskItem({ app, r, saved }) {
  const [f, setF] = useState({ likelihood: saved.likelihood || 3, impact: saved.impact || 3, trend: saved.trend || "Stable", evidence: saved.evidence || "" });
  const [warn, setWarn] = useState(null);
  const save = () => {
    if (CA.wordCount(f.evidence) < 5) return setWarn("Add at least five words of evidence.");
    setWarn(null);
    upd(app, (a) => (a.risks = { ...(a.risks || {}), [r.key]: { ...f, evidence: f.evidence.trim(), saved: true } }));
  };
  const label = `${r.en} · ${r.de}` + (saved.saved ? ` — L${saved.likelihood} × I${saved.impact}, ${saved.trend.toLowerCase()}` : "");
  return (
    <Details status={saved.saved ? "done" : "todo"} summary={label}>
      <p><b>What it means here:</b> {r.what}</p>
      <p className="muted small">Where to look: {r.find}</p>
      <Cfa k={r.cfa} />
      <div className="grid-3">
        <Slider label="Likelihood (1 rare – 5 likely)" min={1} max={5} step={1} value={f.likelihood} onChange={(v) => setF({ ...f, likelihood: v })} />
        <Slider label="Impact on value (1 minor – 5 severe)" min={1} max={5} step={1} value={f.impact} onChange={(v) => setF({ ...f, impact: v })} />
        <Choice label="Trend" options={TRENDS} value={f.trend} onChange={(v) => setF({ ...f, trend: v })} />
      </div>
      <TextArea id={`s7-e-${r.key}`} label="Evidence (figures, disclosures, page references)" rows={3} value={f.evidence} onChange={(v) => setF({ ...f, evidence: v })} />
      {warn && <Callout tone="warn">{warn}</Callout>}
      <div><Btn id={`s7-save-${r.key}`} onClick={save}>Save assessment</Btn></div>
    </Details>
  );
}

function Top3({ app, names, top }) {
  const [keys, setKeys] = useState(top.keys || []);
  const [why, setWhy] = useState(top.why || {});
  const [chan, setChan] = useState(top.channel || {});
  const [warn, setWarn] = useState(null);
  const submit = () => {
    if (keys.length !== 3) return setWarn("Choose exactly three risks.");
    if (keys.some((k) => CA.wordCount(why[k]) < 10 || !chan[k])) return setWarn("For each risk pick a channel and explain it in at least 10 words.");
    setWarn(null);
    upd(app, (a) => (a.top3 = { keys, why: Object.fromEntries(keys.map((k) => [k, why[k].trim()])), channel: Object.fromEntries(keys.map((k) => [k, chan[k]])), submitted: true }));
  };
  return (
    <div className="stack">
      <MultiChoice label="Choose exactly three" max={3} options={Object.entries(names).map(([value, label]) => ({ value, label }))} value={keys} onChange={setKeys} />
      {keys.map((k) => (
        <div className="card" key={k}>
          <h3>{names[k]}</h3>
          <Choice label="Main channel to value" options={CHANNELS} value={chan[k]} onChange={(v) => setChan({ ...chan, [k]: v })} />
          <TextArea id={`s7-why-${k}`} label="How exactly would it change the company's value? What would you monitor?" rows={3} value={why[k] || ""} onChange={(v) => setWhy({ ...why, [k]: v })} />
        </div>
      ))}
      {warn && <Callout tone="warn">{warn}</Callout>}
      <div><Btn kind="primary" id="s7-top-submit" disabled={keys.length !== 3} onClick={submit}>{top.submitted ? "Update my top three" : "Submit my top three"}</Btn></div>
    </div>
  );
}

function Feedback({ app, names, mine }) {
  const ref = app.profile.top_risks_reference || [];
  if (!ref.length) return <Callout tone="info">No reference view for this company — compare your choice with the 'principal risks' the company itself lists in its risk report.</Callout>;
  const refKeys = ref.map((r) => REF_ALIAS[r.risk] || r.risk);
  const overlap = mine.filter((k) => refKeys.includes(k)).length;
  return (
    <div className="card">
      <p><b>Analyst reference view</b> — you share {overlap} of 3. Different choices are fine if your channel-to-value reasoning holds.</p>
      <ul className="plain">
        {ref.map((r) => {
          const k = REF_ALIAS[r.risk] || r.risk;
          return <li key={k}>{mine.includes(k) ? "✓" : "○"} <b>{names[k] || k}</b> — {r.why}</li>;
        })}
      </ul>
      <p className="muted small">Channels: risks hit value through future earnings (ROE), through capital (book value, distributions) or through a higher cost of equity when uncertainty rises.</p>
    </div>
  );
}
