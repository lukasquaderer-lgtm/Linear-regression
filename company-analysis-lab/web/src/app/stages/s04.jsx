// Stage 4 — Ratio Analysis (Kennzahlenanalyse)
// Formula → numbers required → your calculation → correct calculation → interpretation.
import React, { useState } from "react";
import * as CA from "../../lib/ca.js";
import * as D from "../../lib/data.js";
import * as M from "../../lib/metrics.js";
import * as C from "../../lib/calc.js";
import * as R from "../../lib/ratios.js";
import { Btn, Callout, Cfa, Details, Formula, NumberField, Select, StageHeader, Table, Task, TextArea } from "../ui.jsx";
import { Chart, C as Charts } from "../charts.jsx";
import { StageFooter } from "../quiz.jsx";

const N = 4;
const MIN_INTERP = 15;
const CONCEPT_OF = { roe: "roe", roa: "roa", leverage: "dupont", net_margin: "ratio_definitions", cost_income: "ratio_definitions", payout: "payout", equity_ratio: "leverage", bvps: "ratio_definitions", cet1_calc: "regulatory_capital", rwa_density: "regulatory_capital", nii_share: "revenue_mix", fee_share: "revenue_mix", nnm_growth: "ratio_definitions", insurance_margin: "ratio_definitions", investment_share: "revenue_mix", ebit_margin: "ratio_definitions", cash_conversion: "cash_conversion", fcf_margin: "cash_conversion", net_debt_ebitda: "debt_capacity", roce: "roe", gross_margin: "ratio_definitions", rnd_intensity: "cost_structure", capex_intensity: "cost_structure", interest_cover: "debt_capacity", current_ratio: "ratio_definitions", asset_turnover: "dupont" };
const SHORT = { roe: "ROE", roa: "ROA", net_margin: "Net margin", cost_income: "C/I", leverage: "Leverage", equity_ratio: "Equity ratio", payout: "Payout", bvps: "BVPS", cet1_calc: "CET1 ratio", rwa_density: "RWA density", nii_share: "NII share", fee_share: "Fee share", nnm_growth: "NNM growth", insurance_margin: "Margin", investment_share: "Share", ebit_margin: "EBIT margin", cash_conversion: "Cash conversion", fcf_margin: "FCF margin", net_debt_ebitda: "Net debt / EBITDA", roce: "ROCE", gross_margin: "Gross margin", rnd_intensity: "R&D intensity", capex_intensity: "Capex intensity", interest_cover: "Interest cover", current_ratio: "Current ratio", asset_turnover: "Asset turnover" };

export function requiredRatios(app, available) {
  const sec = app.profile.sector;
  const core = available.filter((r) => R.isCore(r, sec)).map((r) => r.key);
  const sector = available.filter((r) => !R.isCore(r, sec) && r.sectors.length !== M.SECTORS.length && r.sectors.includes(sec)).map((r) => r.key);
  return [...core, ...sector.slice(0, 2)];
}

// Numerator and denominator for the formula display (multi-input ratios mirror lab/ratios.py).
function formulaParts(r) {
  const t = (i) => termLabel(r.inputs[i]);
  if (r.key === "fcf_margin") return [<>{t(0)} − {t(1)}</>, t(2)];
  if (r.key === "net_debt_ebitda") return [<>{t(0)} − {t(1)}</>, <>{t(2)} + {t(3)}</>];
  if (r.key === "roce") return [t(0), <>average of (Shareholders' equity + Financial debt − Cash)<sub>t−1, t</sub></>];
  return [t(0), t(1)];
}

function termLabel(spec) {
  const name = M.short(spec.metric);
  if (spec.opening) return <>{name}<sub>t−1</sub></>;
  if (spec.averaged) return <>½ ({name}<sub>t−1</sub> + {name}<sub>t</sub>)</>;
  return <>{name}<sub>t</sub></>;
}

export default function Stage4({ app }) {
  const { profile, currency } = app;
  const available = R.availableRatios(profile, app.ds);
  const required = requiredRatios(app, available);
  const ans = app.doc.stages?.[N]?.answers?.ratios || {};
  const [picked, setPicked] = useState(available[0]?.key);
  const key = available.some((r) => r.key === picked) ? picked : available[0]?.key;
  const attempted = required.filter((k) => ans[k]?.attempted).length;
  const interpreted = required.filter((k) => ans[k]?.interpSubmitted).length;
  const names = required.map((k) => R.RATIOS[k].en.split(" (")[0]).join(", ");
  const criteria = [
    [`Calculated yourself before seeing the solution: ${names} — ${attempted}/${required.length}`, required.length > 0 && attempted === required.length],
    [`Interpreted each ratio in your own words — ${interpreted}/${required.length}`, required.length > 0 && interpreted === required.length],
  ];
  const mark = (k) => (ans[k]?.interpSubmitted ? "done" : ans[k]?.attempted ? "half" : "todo");
  const dupontReady = ["roe", "roa", "leverage"].filter((k) => available.some((r) => r.key === k)).every((k) => ans[k]?.attempted);

  return (
    <div className="page">
      <StageHeader stage={CA.STAGES[3]} profile={profile} currency={currency} />
      <div className="grid-2 wide-left">
        <Task>
          Work through each ratio in five steps: <b>formula → numbers required → your calculation → correct calculation → interpretation</b>. Pick the numbers from your Stage 2 dataset (open it below). The worked solution appears only after you submit your attempt. Convention: balances are <b>averaged</b> (opening + closing) ÷ 2, as in the CFA curriculum.
        </Task>
        <Cfa k="dupont" />
      </div>
      <Details summary="Your Stage 2 dataset (look up the numbers here)">
        <Table columns={[{ key: "m", label: "Metric" }, { key: "u", label: "Unit" }, ...app.ds.years.map((y) => ({ key: String(y), label: String(y), num: true }))]} rows={D.orderKeys(Object.keys(app.ds.values)).map((k) => ({ _key: k, m: M.short(k, app.custom), u: M.unitLabel(k, currency, app.custom), ...Object.fromEntries(app.ds.years.map((y) => { const v = D.value(app.ds, k, y); return [String(y), v === null ? "–" : C.fmtNum(v, Math.abs(v) < 100 ? 2 : 0)]; })) }))} />
      </Details>
      {!available.length ? (
        <Callout tone="warn">No ratio can be computed yet — complete the dataset in Stage 2.</Callout>
      ) : (
        <div className="split">
          <nav className="side-list" aria-label="Ratios">
            <div className="eyebrow">Ratios · <span lang="de">Kennzahlen</span></div>
            <p className="muted small">★ required</p>
            {available.map((r) => (
              <button key={r.key} type="button" className={`side-item ${r.key === key ? "active" : ""}`} onClick={() => setPicked(r.key)}>
                <span className={`status-dot ${mark(r.key)}`} />
                <span>{r.en}{required.includes(r.key) && <span className="req"> ★</span>}</span>
              </button>
            ))}
          </nav>
          <div className="split-main">
            <RatioWork key={key} app={app} r={R.RATIOS[key]} a={ans[key] || {}} />
          </div>
        </div>
      )}
      {dupontReady && <Dupont app={app} />}
      <StageFooter app={app} n={N} criteria={criteria} />
    </div>
  );
}

function RatioWork({ app, r, a }) {
  const validYears = app.ds.years.filter((y) => R.compute(r, app.ds, y).value !== null).reverse();
  const [year, setYear] = useState(a.year || validYears[0]);
  const [inputs, setInputs] = useState(a.inputs || {});
  const [result, setResult] = useState(a.result ?? null);
  const [interp, setInterp] = useState(a.interpretation || "");
  const [warn, setWarn] = useState(null);
  if (!validYears.length) return <Callout tone="warn">Data missing for this ratio.</Callout>;
  const y = a.attempted ? a.year : year;
  const res = R.compute(r, app.ds, y, app.currency);
  const unit = { "%": "%", x: "×", ccy: app.currency }[r.unit];
  const upd = (patch) => app.update((d) => {
    const s = (d.stages[N] ||= {});
    s.answers ||= {};
    s.answers.ratios ||= {};
    s.answers.ratios[r.key] = { ...(s.answers.ratios[r.key] || {}), ...patch };
  });
  const submit = () => {
    const filled = Object.fromEntries(res.required.map((rn) => [`${rn.metric}|${rn.year}`, inputs[`${rn.metric}|${rn.year}`] ?? null]));
    if (result === null || Object.values(filled).some((v) => v === null)) return setWarn("Fill in every number and your result — that is the point of the exercise.");
    setWarn(null);
    const dg = R.diagnose(res, filled, result, app.currency);
    upd({ year: y, inputs: filled, result, attempted: true, correct: dg.correct, headline: dg.headline, details: dg.details });
    app.recordAttempt(N, `ratio-${r.key}`, CONCEPT_OF[r.key] || "ratio_definitions", dg.correct);
  };
  const submitInterp = () => {
    if (CA.wordCount(interp) < MIN_INTERP) return setWarn(`Write at least ${MIN_INTERP} words.`);
    setWarn(null);
    upd({ interpretation: interp.trim(), interpSubmitted: true });
  };
  let reported = null;
  if (r.key === "roe") reported = D.value(app.ds, "roe_reported", y);
  if (r.key === "cost_income") reported = D.value(app.ds, "cost_income_ratio", y);
  if (r.key === "cet1_calc") reported = D.value(app.ds, "cet1_ratio", y);
  const hist = app.ds.years.map((yy) => [yy, R.compute(r, app.ds, yy).value]);

  return (
    <div className="stack">
      <h2 className="metric-title">{r.en} <span className="de" lang="de">· {r.de}</span></h2>
      {r.cfa && <Cfa k={r.cfa} />}
      <h3>1 · Formula</h3>
      <Formula lhs={SHORT[r.key] || r.en} num={formulaParts(r)[0]} den={formulaParts(r)[1]} times={r.unit === "%" ? "100" : null} />
      {!a.attempted && <Select id={`s4-year-${r.key}`} label="Fiscal year to analyse" value={String(year)} options={validYears.map((v) => ({ value: String(v), label: String(v) }))} onChange={(v) => { setYear(+v); setInputs({}); }} />}
      <h3>2 · Numbers required</h3>
      <ul>{res.required.map((rn) => <li key={rn.label}>{rn.label} · <em className="muted">{M.get(rn.metric)?.statement}</em></li>)}</ul>
      <h3>3 · Your calculation</h3>
      <div className="grid-4">
        {res.required.map((rn) => (
          <NumberField key={`${rn.metric}|${rn.year}`} id={`s4-in-${r.key}-${rn.metric}-${rn.year}`} label={rn.label} disabled={a.attempted} value={inputs[`${rn.metric}|${rn.year}`] ?? null} onChange={(v) => setInputs({ ...inputs, [`${rn.metric}|${rn.year}`]: v })} />
        ))}
        <NumberField id={`s4-res-${r.key}`} label={`Result (${unit})`} disabled={a.attempted} value={result} onChange={setResult} />
      </div>
      {!a.attempted && <div><Btn kind="primary" id={`s4-submit-${r.key}`} onClick={submit}>Submit my attempt</Btn></div>}
      {warn && <Callout tone="warn">{warn}</Callout>}
      {!a.attempted ? <Callout tone="info">The correct calculation appears after you submit your attempt.</Callout> : (
        <>
          <h3>4 · Correct calculation</h3>
          <Callout tone={a.correct ? "success" : "error"}>{a.headline}</Callout>
          {a.details?.length > 0 && <ul>{a.details.map((d) => <li key={d}>{d}</li>)}</ul>}
          <div className="card mono">
            {res.steps.map((s) => <div key={s}>{s}</div>)}
            {res.alternative !== null && <p className="muted small">For reference — with year-end balances instead of averages: {R.formatRatio(res.alternative, r, app.currency)}</p>}
            {reported !== null && <p className="muted small">The company reports {reported.toFixed(1)} %. Differences usually come from definitions (e.g. adjusted figures, tangible equity, excluding items).</p>}
          </div>
          <h3>5 · Interpretation</h3>
          <TextArea id={`s4-int-${r.key}`} label="What does this ratio tell you about the company? Is the level good or bad for this type of company, and why?" rows={4} value={interp} onChange={setInterp} />
          <div><Btn id={`s4-interp-${r.key}`} onClick={submitInterp}>{a.interpSubmitted ? "Update interpretation" : "Submit interpretation"}</Btn></div>
          {a.interpSubmitted && (
            <>
              <Callout tone="info" title="How an analyst reads it">
                {r.interpretation[app.profile.sector]}
                {r.benchmark[app.profile.sector] && <><br /><b>Rule-of-thumb range:</b> {r.benchmark[app.profile.sector]}</>}
              </Callout>
              {hist.filter(([, v]) => v !== null).length >= 2 && (
                <>
                  <Chart spec={Charts.history(hist, `${r.en} — all years (calculated)`, unit)} label={`${r.en} history`} />
                  <p className="muted small">Now that you have your own view: does the multi-year trend support your interpretation?</p>
                </>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

function Dupont({ app }) {
  const rows = app.ds.years.map((y) => [y, R.dupont(app.ds, y)]).filter(([, d]) => d);
  if (!rows.length) return null;
  const f3 = (x) => (x === undefined ? "–" : x.toFixed(3));
  return (
    <section className="section">
      <div className="section-head"><h2>DuPont analysis — where does ROE come from?</h2></div>
      <Cfa k="dupont" />
      <p className="formula-line">ROE = net margin × asset turnover × leverage = ROA × leverage</p>
      <Table columns={[{ key: "y", label: "Year" }, { key: "nm", label: "Net margin %", num: true }, { key: "at", label: "Asset turnover ×", num: true }, { key: "roa", label: "ROA %", num: true }, { key: "lev", label: "Leverage ×", num: true }, { key: "roe", label: "ROE %", num: true }]}
        rows={rows.map(([y, d]) => ({ _key: y, y, nm: f3(d.net_margin), at: f3(d.asset_turnover), roa: f3(d.roa), lev: f3(d.leverage), roe: f3(d.roe) }))} />
      <div className="grid-3">
        <Chart spec={Charts.history(rows.map(([y, d]) => [y, d.roa]), "ROA %", "%")} label="ROA" />
        <Chart spec={Charts.history(rows.map(([y, d]) => [y, d.leverage]), "Leverage ×", "×")} label="Leverage" />
        <Chart spec={Charts.history(rows.map(([y, d]) => [y, d.roe]), "ROE %", "%")} label="ROE" />
      </div>
      <p className="muted small">Question to ask yourself: did ROE move because the company became more profitable (ROA) or because it used more leverage? Banks and insurers can raise ROE simply by holding less capital; other companies by buying back shares with debt.</p>
    </section>
  );
}
