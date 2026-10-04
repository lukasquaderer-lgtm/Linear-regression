// Stage 3 — Historical Trend Analysis (Historische Trendanalyse)
import React, { useState } from "react";
import * as CA from "../../lib/ca.js";
import * as D from "../../lib/data.js";
import * as M from "../../lib/metrics.js";
import * as C from "../../lib/calc.js";
import { Btn, Callout, Cfa, Choice, Coverage, Details, Metric, NumberField, StageHeader, Table, Task, TextArea } from "../ui.jsx";
import { Chart, C as Charts } from "../charts.jsx";
import { StageFooter } from "../quiz.jsx";

const N = 3;
const VERDICTS = ["Improving", "Deteriorating", "Stable", "Volatile / no clear trend"];
const DRIVERS = ["Mainly operational", "Mainly accounting-driven", "Mainly one-off items", "A mix"];
const MIN_WHY = 15;
const CORE = ["revenue", "net_income", "total_equity", "eps"];
const SECTOR_PRIORITY = { bank: ["cet1_ratio", "cost_income_ratio", "net_interest_income", "fee_income", "net_new_money", "aum"], insurer: ["solvency_ratio", "combined_ratio", "investment_income", "insurance_revenue", "gross_premiums", "aum"], corporate: ["ebit", "operating_cash_flow", "free_cash_flow", "rnd_expense", "gross_profit", "total_debt"] };

export function trendMetrics(app) {
  const applicable = new Set([...D.applicableMetricKeys(app.profile), ...Object.keys(app.custom)]);
  return [...M.ORDER, ...Object.keys(app.custom)].filter((k) => {
    const m = M.get(k);
    if (!applicable.has(k) || (m && !M.isTrend(m, app.profile.sector)) || !app.ds.values[k]) return false;
    return D.clean(D.series(app.ds, k)).length >= 3;
  });
}
export function requiredTrend(app, available) {
  return [...CORE.filter((k) => available.includes(k)), ...SECTOR_PRIORITY[app.profile.sector].filter((k) => available.includes(k)).slice(0, 2)];
}

export default function Stage3({ app }) {
  const { profile, currency } = app;
  const available = trendMetrics(app);
  const required = requiredTrend(app, available);
  const trend = app.doc.stages?.[N]?.answers?.trend || {};
  const [picked, setKey] = useState(available[0]);
  const key = available.includes(picked) ? picked : available[0];
  const calc = required.filter((k) => trend[k]?.calcChecked).length;
  const judged = required.filter((k) => trend[k]?.submitted).length;
  const names = required.map((k) => M.short(k, app.custom)).join(", ");
  const criteria = [
    [`Growth calculated yourself for the core metrics (${names}) — ${calc}/${required.length}`, required.length > 0 && calc === required.length],
    [`Trend judged and explained for each of them — ${judged}/${required.length}`, required.length > 0 && judged === required.length],
  ];
  const mark = (k) => (trend[k]?.submitted ? "done" : trend[k]?.calcChecked ? "half" : "todo");

  return (
    <div className="page">
      <StageHeader stage={CA.STAGES[2]} profile={profile} currency={currency} />
      <div className="grid-2 wide-left">
        <Task>
          For each metric: <b>(1)</b> look at the 5-year history, <b>(2)</b> calculate the latest year-over-year growth and the CAGR yourself, <b>(3)</b> decide whether the trend is improving, deteriorating or stable, and <b>(4)</b> explain <b>why</b>. The app's own assessment and the analyst notes only appear after you commit to your view.
        </Task>
        <div className="stack tight">
          <Cfa k="growth_cagr" />
          <Cfa k="trend" />
        </div>
      </div>
      {!available.length ? (
        <Callout tone="warn">Not enough data — go back to Stage 2 and fill at least three years per metric.</Callout>
      ) : (
        <div className="split">
          <nav className="side-list" aria-label="Metrics">
            <div className="eyebrow">Metrics · <span lang="de">Kennzahlen</span></div>
            <p className="muted small">★ required</p>
            {available.map((k) => (
              <button key={k} type="button" className={`side-item ${k === key ? "active" : ""}`} onClick={() => setKey(k)}>
                <span className={`status-dot ${mark(k)}`} />
                <span>{M.short(k, app.custom)}{required.includes(k) && <span className="req"> ★</span>}</span>
              </button>
            ))}
          </nav>
          <div className="split-main">
            <Workspace key={key} app={app} k={key} a={trend[key] || {}} />
          </div>
        </div>
      )}
      <Details summary="Overview — your verdicts vs the rule-based assessment">
        <Table
          columns={[{ key: "m", label: "Metric" }, { key: "v", label: "Your verdict" }, { key: "r", label: "Rule-based" }, { key: "d", label: "Driver (yours)" }, { key: "w", label: "Your explanation" }]}
          rows={available.filter((k) => trend[k]?.submitted).map((k) => ({ _key: k, m: M.short(k, app.custom), v: trend[k].verdict, r: cap(C.classifyTrend(D.series(app.ds, k), k, app.custom).label), d: trend[k].driver, w: trend[k].why }))}
        />
      </Details>
      <StageFooter app={app} n={N} criteria={criteria} />
    </div>
  );
}

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function Workspace({ app, k, a }) {
  const s = D.clean(D.series(app.ds, k));
  const unit = M.unitLabel(k, app.currency, app.custom);
  const ratio = M.unitOf(k, app.custom) === "pct";
  const m = M.get(k);
  const ys = s.map(([y]) => y);
  const [yLast, last] = s[s.length - 1];
  const [yPrev, prev] = s[s.length - 2];
  const [yFirst, first] = s[0];
  const n = yLast - yFirst;
  const [inp, setInp] = useState({ yoy: a.yoy ?? null, cagr: a.cagr ?? null });
  const [judge, setJudge] = useState({ verdict: a.verdict || null, driver: a.driver || null, why: a.why || "" });
  const [warn, setWarn] = useState(null);

  const q1 = ratio ? `Change ${yPrev} → ${yLast} in percentage points` : `Year-over-year growth ${yPrev} → ${yLast} (%)`;
  const q2 = ratio ? `Change ${yFirst} → ${yLast} in percentage points` : `CAGR ${yFirst} → ${yLast} over ${n} years (%)`;
  const c1 = ratio ? last - prev : prev > 0 ? (last / prev - 1) * 100 : null;
  const c2 = ratio ? last - first : C.cagr(first, last, n);

  const acc = app.profile.accounting || {};
  const bases = [...new Set(ys.map((y) => acc[String(y)]).filter(Boolean))];

  const upd = (fn) => app.update((d) => {
    const st = (d.stages[N] ||= {});
    st.answers ||= {};
    st.answers.trend ||= {};
    st.answers.trend[k] = { ...(st.answers.trend[k] || {}), ...fn };
  });

  const check = () => {
    if ((c1 !== null && inp.yoy === null) || (c2 !== null && inp.cagr === null)) return setWarn("Enter both numbers first.");
    setWarn(null);
    const ok1 = c1 === null || C.isClose(inp.yoy, c1, 0.01, 0.1);
    const ok2 = c2 === null || C.isClose(inp.cagr, c2, 0.01, 0.1);
    upd({ yoy: inp.yoy, cagr: inp.cagr, calcChecked: true, ok1, ok2 });
    app.recordAttempt(N, `yoy-${k}`, "yoy_growth", ok1);
    if (!ratio) app.recordAttempt(N, `cagr-${k}`, "growth_cagr", ok2);
  };
  const submit = () => {
    if (!judge.verdict || !judge.driver || CA.wordCount(judge.why) < MIN_WHY) return setWarn(`Choose a verdict and a driver, and explain in at least ${MIN_WHY} words.`);
    setWarn(null);
    upd({ ...judge, why: judge.why.trim(), submitted: true });
  };

  const growth = ratio ? C.yoyChange(s) : C.yoyGrowth(s);
  const better = M.higherIsBetter(k, app.custom);
  return (
    <div className="stack">
      <h2 className="metric-title">{M.short(k, app.custom)} <span className="de" lang="de">· {M.german(k, app.custom)}</span></h2>
      {m?.description && <p className="muted">{m.description}</p>}
      {bases.length > 1 && <Callout tone="warn">The series spans different accounting bases ({bases.join(" → ")}). Treat growth across the break with caution.</Callout>}

      <h3>Step 1 · The 5-year history</h3>
      <Chart spec={Charts.history(s, `${M.short(k, app.custom)} — history`, unit)} label={`${M.short(k)} history`}
        table={<details className="details"><summary>Table view</summary><div className="details-body"><Table columns={[{ key: "y", label: "Year" }, { key: "v", label: unit || "Value", num: true }]} rows={s.map(([y, v]) => ({ y, v: C.fmtNum(v, 2), _key: y }))} /></div></details>} />

      <h3>Step 2 · Your calculations</h3>
      <p className="muted small">{ratio ? "For ratios, growth rates of a percentage are confusing — analysts talk about changes in percentage points (pp)." : "Growth from a negative or zero base is not meaningful — if a box says 'not meaningful', explain the change in words instead."}</p>
      <div className="formulas">
        {ratio ? <code>Δ = x<sub>{yLast}</sub> − x<sub>{yPrev}</sub></code> : <code>g = x<sub>{yLast}</sub> ÷ x<sub>{yPrev}</sub> − 1</code>}
        {ratio ? <code>Δ = x<sub>{yLast}</sub> − x<sub>{yFirst}</sub></code> : <code>CAGR = (x<sub>{yLast}</sub> ÷ x<sub>{yFirst}</sub>)<sup>1/{n}</sup> − 1</code>}
      </div>
      <div className="grid-2">
        <NumberField id={`s3-yoy-${k}`} label={q1 + (c1 === null ? " — not meaningful" : "")} disabled={c1 === null} value={inp.yoy} onChange={(v) => setInp({ ...inp, yoy: v })} />
        <NumberField id={`s3-cagr-${k}`} label={q2 + (c2 === null ? " — not meaningful" : "")} disabled={c2 === null} value={inp.cagr} onChange={(v) => setInp({ ...inp, cagr: v })} />
      </div>
      <div><Btn id={`s3-check-${k}`} onClick={check}>Check my calculations</Btn></div>
      {warn && <Callout tone="warn">{warn}</Callout>}
      {!a.calcChecked ? (
        <Callout tone="info">Check your calculations to unlock the full growth table and the judgement step.</Callout>
      ) : (
        <>
          <div className="grid-2">
            {[[a.ok1, q1, c1, a.yoy], [a.ok2, q2, c2, a.cagr]].map(([ok, label, correct, given]) => (
              correct === null ? <Callout key={label} tone="info">{label}: not meaningful (negative or zero base).</Callout>
                : ok ? <Callout key={label} tone="success">✓ {label}: {sgn(correct)}{ratio ? " pp" : " %"}</Callout>
                : <Callout key={label} tone="error">✗ {label}: you entered {given ?? "–"}, correct is {sgn(correct)}{ratio ? " pp" : " %"}</Callout>
            ))}
          </div>
          {!ratio && !a.ok2 && c2 !== null && (
            <p className="muted small">Common mistake: the arithmetic average of the yearly growth rates is {avgGrowth(growth).toFixed(2)} % — not the same as the CAGR ({c2.toFixed(2)} %).</p>
          )}
          <div className="grid-2 wide-left">
            <Chart spec={Charts.growth(growth, "Year-over-year change", ratio ? "pp" : "%")} label="Year-over-year change" />
            <Table columns={[{ key: "y", label: "Year" }, { key: "v", label: "Value", num: true }, { key: "g", label: ratio ? "YoY pp" : "YoY %", num: true }]} rows={s.map(([y, v], i) => ({ _key: y, y, v: C.fmtNum(v, 2), g: growth[i][1] === null ? "–" : sgn(growth[i][1]) }))} />
          </div>

          <h3>Step 3 · Your judgement</h3>
          {better === null && <p className="muted small">Careful: for this metric 'more' is not automatically 'better' (e.g. a bigger balance sheet). Say why you see it as improving or deteriorating.</p>}
          {better === false && <p className="muted small">Careful: for this metric lower is better.</p>}
          <Choice label="The trend is…" options={VERDICTS} value={judge.verdict} onChange={(v) => setJudge({ ...judge, verdict: v })} />
          <Choice label="What mainly drives it?" options={DRIVERS} value={judge.driver} onChange={(v) => setJudge({ ...judge, driver: v })} />
          <TextArea id={`s3-why-${k}`} label="Why? Explain the drivers behind the numbers (use the annual report's management commentary)." rows={4} value={judge.why} onChange={(v) => setJudge({ ...judge, why: v })} hint={`${CA.wordCount(judge.why)} words`} />
          <div><Btn kind="primary" id={`s3-submit-${k}`} onClick={submit}>{a.submitted ? "Update my interpretation" : "Submit my interpretation"}</Btn></div>
          {a.submitted && <Feedback app={app} k={k} s={s} a={a} />}
        </>
      )}
    </div>
  );
}

const sgn = (x) => `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(2)}`;
const avgGrowth = (g) => {
  const v = g.map(([, x]) => x).filter((x) => x !== null);
  return v.reduce((p, q) => p + q, 0) / (v.length || 1);
};

function Feedback({ app, k, s, a }) {
  const v = C.classifyTrend(s, k, app.custom);
  const mine = a.verdict.split(" /")[0].toLowerCase();
  const rule = v.label;
  const agree = mine === rule || (mine === "improving" && rule === "growing") || (mine === "deteriorating" && rule === "shrinking");
  const [cov, miss] = CA.keywordCoverage(a.why, CA.EXPLANATION_DRIVERS);
  const evs = CA.eventsFor(app.profile, k);
  return (
    <div className="stack">
      <h3>Step 4 · Feedback</h3>
      <div className="card">
        <div className="metrics">
          <Metric label="Your verdict" value={a.verdict} />
          <Metric label="Rule-based assessment" value={cap(rule)} />
        </div>
        <ul>{v.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
        {agree ? <Callout tone="success">Your verdict matches the mechanical assessment. Now check that your <em>explanation</em> is right — that is what matters.</Callout>
          : rule === "growing" || rule === "shrinking" ? <Callout tone="info">The metric is {rule}. Whether that is good depends on <em>why</em> — your reasoning decides.</Callout>
          : <Callout tone="warn">Your verdict differs from the mechanical assessment. That can be fine (e.g. you adjusted for a one-off or an accounting break) — but make sure your explanation says so.</Callout>}
      </div>
      <Coverage covered={cov} missed={miss.slice(0, 5)} labelCovered="Your explanation mentions" labelMissed="Did you consider" />
      {evs.length ? (
        <>
          <p><b>Analyst notes — what actually happened</b> (compare with your explanation)</p>
          {evs.map((ev) => (
            <Details key={ev.title} summary={`${ev.year} · ${ev.title} — ${CA.NATURE_LABEL[ev.nature] || ev.nature}`}>
              <p>{ev.detail}</p>
              <p className="muted small">Verify in: {ev.where_to_verify}</p>
            </Details>
          ))}
        </>
      ) : <p className="muted small">No analyst notes for this metric — check your explanation against the management report and the notes.</p>}
    </div>
  );
}
