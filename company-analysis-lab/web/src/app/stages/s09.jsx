// Stage 9 — Valuation (Bewertung). Never turns the result into a buy/sell call.
import React, { useEffect, useRef, useState } from "react";
import * as CA from "../../lib/ca.js";
import * as D from "../../lib/data.js";
import * as C from "../../lib/calc.js";
import * as R from "../../lib/ratios.js";
import * as V from "../../lib/valuation.js";
import { Btn, Callout, Cfa, Choice, Metric, MultiChoice, NumberField, Slider, StageHeader, Table, Task, TextArea, Toggle } from "../ui.jsx";
import { Chart, C as Charts } from "../charts.jsx";
import { StageFooter } from "../quiz.jsx";

const N = 9;
const RF_DEFAULT = { CHF: 0.5, EUR: 2.5, USD: 4.2, GBP: 4.3 };
const G_DEFAULT = { CHF: 1.0, EUR: 1.5, USD: 2.0, GBP: 2.0 };
const SUITED = new Set(["pb", "jpb", "ddm", "ri"]);
const UNSUITED = new Set(["dcf"]);
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const median = (xs) => {
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const f2 = (x) => (Number.isFinite(x) ? x.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "–");

export function baseInputs(app) {
  const ds = app.ds;
  const years = ds.years.filter((y) => D.value(ds, "net_income", y) !== null && D.value(ds, "total_equity", y) !== null);
  if (!years.length) return null;
  const y = years[years.length - 1];
  const ni = D.value(ds, "net_income", y), eq = D.value(ds, "total_equity", y);
  const shares = D.value(ds, "shares_outstanding", y);
  const perShare = Boolean(app.profile.listed) && shares !== null && shares > 0;
  const underlying = app.doc.stages?.[6]?.answers?.underlying?.[String(y)] ?? null;
  const eps = perShare ? D.value(ds, "eps", y) : null;
  const dps = D.value(ds, "dps", y) || (perShare ? D.value(ds, "dps", y - 1) : null);
  const hist = years.slice(-3).map((yy) => R.compute(R.RATIOS.roe, ds, yy).value).filter((x) => x !== null);
  let roeDefault = hist.length ? median(hist) : null;
  let roeBasis = hist.length ? "median ROE of the last 3 years (robust to one-off years)" : "";
  const prevEq = D.value(ds, "total_equity", y - 1);
  if (underlying !== null && prevEq) {
    roeDefault = (underlying / ((prevEq + eq) / 2)) * 100;
    roeBasis = `underlying ROE ${y} from your Stage 6 bridge`;
  }
  const epsB = eps !== null ? eps : perShare ? ni / shares : null;
  return {
    year: y, ni, equity: eq, shares, perShare, eps: epsB, dps, bvps: perShare ? eq / shares : null, underlying,
    roeAvg3: roeDefault, roeBasis, payout: perShare && dps && epsB && epsB > 0 ? (dps / epsB) * 100 : null,
    rwa: D.value(ds, "rwa", y), cet1: D.value(ds, "cet1_ratio", y),
  };
}

const upd = (app, fn) => app.update((d) => {
  const s = (d.stages[N] ||= {});
  s.answers ||= {};
  fn(s.answers);
});

function criteria(app, a) {
  return [
    ["Valuation methods chosen and justified", Boolean(a.methods_submitted)],
    [app.profile.listed ? "Market multiples calculated yourself" : "Peer multiples applied to the unlisted company", Boolean(a.multiples_done)],
    ["Base-case assumptions saved", Boolean(a.scenarios?.base)],
    ["Valuation conclusion written (method + value range)", Boolean(a.conclusion_submitted)],
  ];
}

export default function Stage9({ app }) {
  const ans = app.doc.stages?.[N]?.answers || {};
  const b = baseInputs(app);
  return (
    <div className="page">
      <StageHeader stage={CA.STAGES[8]} profile={app.profile} currency={app.currency} />
      {!b ? (
        <Callout tone="warn">Net income and equity are needed — complete Stage 2.</Callout>
      ) : (
        <>
          <div className="grid-2 wide-left">
            <Task>
              Valuation comes <b>last</b> — it translates your analysis into numbers. For banks and insurers, <b>P/B versus ROE</b>, dividends and <b>capital generation</b> are usually more informative than an industrial free-cash-flow DCF: their "debt" (deposits, policy liabilities) is raw material, not financing, and regulators decide how much capital can be paid out. Change the assumptions and watch the value move.
            </Task>
            <div className="stack tight">
              <Cfa k="justified_pb" />
              <p className="muted small">This tool does not tell you whether to buy or sell. A gap between your value and the market price is a hypothesis to test.</p>
            </div>
          </div>
          <Methods app={app} ans={ans} />
          {b.perShare ? <Multiples app={app} ans={ans} b={b} /> : <PeerMultiples app={app} ans={ans} b={b} />}
          <Playground app={app} ans={ans} b={b} price={b.perShare ? ans.price || null : null} />
          <Conclusion app={app} ans={ans} b={b} />
        </>
      )}
      <StageFooter app={app} n={N} criteria={criteria(app, ans)} />
    </div>
  );
}

function Methods({ app, ans }) {
  const [chosen, setChosen] = useState(ans.methods || []);
  const [why, setWhy] = useState(ans.methods_why || "");
  const [warn, setWarn] = useState(null);
  const submit = () => {
    if (chosen.length < 2 || chosen.length > 3 || CA.wordCount(why) < 12) return setWarn("Choose two or three methods and explain in at least 12 words.");
    setWarn(null);
    app.recordAttempt(N, "methods", "valuation_methods", !chosen.some((k) => UNSUITED.has(k)));
    upd(app, (a) => Object.assign(a, { methods: chosen, methods_why: why.trim(), methods_submitted: true }));
  };
  const picked = new Set(ans.methods || []);
  const good = [...picked].filter((k) => SUITED.has(k));
  return (
    <section className="section">
      <div className="section-head"><h2>1 · Which methods fit this company?</h2></div>
      <MultiChoice label="Pick the two or three methods you consider most informative" options={V.METHOD_GUIDE.map((m) => ({ value: m.key, label: m.name }))} value={chosen} onChange={setChosen} max={3} />
      <TextArea id="s9-methods-why" label="Why these — and why not the others?" rows={3} value={why} onChange={setWhy} />
      {warn && <Callout tone="warn">{warn}</Callout>}
      <div><Btn kind="primary" id="s9-methods-submit" onClick={submit}>Submit my choice</Btn></div>
      {ans.methods_submitted && (
        <>
          {[...picked].some((k) => UNSUITED.has(k)) && <Callout tone="warn">You included an FCFF-style DCF. For a bank or insurer, cash flow statements do not measure distributable cash, and debt is operating funding — use FCFE defined as distributable capital instead (section 3).</Callout>}
          <Callout tone={good.length ? "success" : "warn"}>{good.length ? `${good.length} of your choices are classic financial-sector methods.` : "None of your choices is a typical financial-sector method — compare with the guide below."}</Callout>
          <Table columns={[{ key: "name", label: "Method" }, { key: "when", label: "When it fits" }, { key: "caution", label: "Watch out for" }]} rows={V.METHOD_GUIDE.map((m) => ({ ...m, _key: m.key }))} />
          <Cfa k="dcf" />
        </>
      )}
    </section>
  );
}

function Multiples({ app, ans, b }) {
  const ccy = app.currency;
  const price = ans.price || null;
  const [inp, setInp] = useState({ pe: ans.pe_in ?? null, pb: ans.pb_in ?? null, dy: ans.dy_in ?? null });
  const [warn, setWarn] = useState(null);
  const correct = price ? { pe: V.pe(price, b.eps), pb: V.pb(price, b.bvps), dy: b.dps ? (V.dividendYield(b.dps, price) || 0) * 100 : null } : null;
  const check = () => {
    if (inp.pe === null || inp.pb === null || (correct.dy !== null && inp.dy === null)) return setWarn("Fill in all multiples.");
    setWarn(null);
    const ok = Object.fromEntries(["pe", "pb", "dy"].map((k) => [k, correct[k] !== null && correct[k] !== undefined ? C.isClose(inp[k], correct[k], 0.02, 0.05) : true]));
    app.recordAttempt(N, "pb", "justified_pb", ok.pb);
    upd(app, (a) => Object.assign(a, { pe_in: inp.pe, pb_in: inp.pb, dy_in: inp.dy, multiples_ok: ok, multiples_done: true }));
  };
  const ok = ans.multiples_ok || {};
  return (
    <section className="section">
      <div className="section-head"><h2>2 · Market multiples</h2></div>
      <p className="muted small">Look up the current share price (stock exchange / financial website). Some companies report in a different currency than their share trades in (e.g. UBS reports in USD, trades in CHF) — use the same currency for price and per-share figures.</p>
      <div className="grid-3">
        <NumberField id="s9-price" label={`Current share price (${ccy})`} value={price} onChange={(v) => upd(app, (a) => { if (v !== a.price) { a.price = v; a.multiples_done = false; } })} />
      </div>
      {!price ? (
        <Callout tone="info">Enter a share price to continue.</Callout>
      ) : (
        <>
          <p>Use your dataset ({b.year}): EPS {ccy} {f2(b.eps)} · equity {C.fmtNum(b.equity)} m · shares {C.fmtNum(b.shares, 1)} m · DPS (latest declared) {b.dps ? f2(b.dps) : "–"}</p>
          <div className="grid-3">
            <NumberField id="s9-pe" label="P/E (×)" value={inp.pe} onChange={(v) => setInp({ ...inp, pe: v })} />
            <NumberField id="s9-pb" label="P/B (×) — compute BVPS first" value={inp.pb} onChange={(v) => setInp({ ...inp, pb: v })} />
            <NumberField id="s9-dy" label="Dividend yield (%)" value={inp.dy} onChange={(v) => setInp({ ...inp, dy: v })} />
          </div>
          {warn && <Callout tone="warn">{warn}</Callout>}
          <div><Btn kind="primary" id="s9-mult-check" onClick={check}>Check my multiples</Btn></div>
          {ans.multiples_done && (
            <>
              <div className="metrics">
                <Metric label="P/E" value={correct.pe ? `${correct.pe.toFixed(2)}×` : "n/m"} help={`${f2(price)} ÷ EPS ${f2(b.eps)}`} />
                <Metric label="P/B" value={correct.pb ? `${correct.pb.toFixed(2)}×` : "n/m"} help={`BVPS = ${C.fmtNum(b.equity)} ÷ ${C.fmtNum(b.shares, 1)} = ${f2(b.bvps)}`} />
                <Metric label="Dividend yield" value={correct.dy !== null ? `${correct.dy.toFixed(2)} %` : "–"} />
              </div>
              <p>{Object.entries(ok).map(([k, v]) => `${k.toUpperCase()}: ${v ? "✓" : "✗"}`).join(" · ")}</p>
              <p className="muted small">BVPS = equity ÷ shares = {f2(b.bvps)}. P/E = price ÷ EPS; P/B = price ÷ BVPS; yield = DPS ÷ price.</p>
              {b.underlying && b.shares ? <p className="muted small">On your underlying earnings from Stage 6 (EPS ≈ {f2(b.underlying / b.shares)}) the P/E would be {(price / (b.underlying / b.shares)).toFixed(2)}× — which one is more meaningful?</p> : null}
              <Cfa k="pe" />
            </>
          )}
        </>
      )}
    </section>
  );
}

function PeerMultiples({ app, ans, b }) {
  const [p, setP] = useState({ pb: ans.peer_pb ?? null, pe: ans.peer_pe ?? null, disc: ans.discount ?? 15 });
  const [warn, setWarn] = useState(null);
  const apply = () => {
    if (!p.pb || !p.pe) return setWarn("Enter both peer multiples.");
    setWarn(null);
    upd(app, (a) => Object.assign(a, { peer_pb: p.pb, peer_pe: p.pe, discount: p.disc, multiples_done: true }));
  };
  const f = 1 - (ans.discount ?? 0) / 100;
  return (
    <section className="section">
      <div className="section-head"><h2>2 · Valuing an unlisted company with peer multiples</h2></div>
      <p className="muted small">No market price exists. Analysts use multiples of listed peers (or of recent transactions — e.g. what an acquirer paid) and intrinsic models.</p>
      <div className="grid-2">
        <NumberField id="s9-peer-pb" label="Peer P/B you looked up (×)" value={p.pb} onChange={(v) => setP({ ...p, pb: v })} />
        <NumberField id="s9-peer-pe" label="Peer P/E you looked up (×)" value={p.pe} onChange={(v) => setP({ ...p, pe: v })} />
      </div>
      <Slider label="Discount for size / illiquidity" value={p.disc} min={0} max={40} step={1} onChange={(v) => setP({ ...p, disc: v })} format={(v) => `${v} %`} />
      {warn && <Callout tone="warn">{warn}</Callout>}
      <div><Btn kind="primary" id="s9-peer-apply" onClick={apply}>Apply peer multiples</Btn></div>
      {ans.multiples_done && (
        <>
          <div className="metrics">
            <Metric label={`Equity value via P/B (${app.currency} m)`} value={C.fmtNum(ans.peer_pb * b.equity * f)} />
            <Metric label={`Equity value via P/E (${app.currency} m)`} value={C.fmtNum(ans.peer_pe * b.ni * f)} />
          </div>
          <p className="muted small">Why do the two differ? Because the company's ROE differs from the peers' — which is exactly what P/B = f(ROE) captures.</p>
        </>
      )}
    </section>
  );
}

function defaults(app, b, saved) {
  const ccy = app.currency;
  const roeD = b.roeAvg3 !== null ? b.roeAvg3 : 10;
  const base = {
    rf: RF_DEFAULT[ccy] ?? 2.0, beta: app.profile.sector === "bank" ? 1.15 : 0.95, erp: 5.5,
    roe: clamp(Math.round(roeD * 10) / 10, 0, 25), payout: clamp(b.payout !== null ? Math.round(b.payout) : 60, 0, 100), g: G_DEFAULT[ccy] ?? 1.5, n: 5, fade: false,
    rwa_g: 3.0, cet1_t: Math.round((b.cet1 || 14) * 10) / 10,
  };
  const out = { ...base, ...(saved || {}) };
  if (out.g1 === undefined || out.g1 === null) out.g1 = Math.round(clamp(V.sustainableGrowth(out.roe / 100, out.payout / 100) * 100, -5, 15) * 10) / 10;
  if (out.rwa_g === null) out.rwa_g = base.rwa_g;
  if (out.cet1_t === null) out.cet1_t = base.cet1_t;
  return out;
}

function Playground({ app, ans, b, price }) {
  const perShare = b.perShare;
  const unit = perShare ? `${app.currency}/share` : `${app.currency} m`;
  const [a, setA] = useState(() => defaults(app, b, ans.live || ans.scenarios?.base?.assumptions));
  const [scen, setScen] = useState("base");
  const [msg, setMsg] = useState(null);
  const timer = useRef(null);
  const set = (k, v) => {
    const next = { ...a, [k]: v };
    setA(next);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => upd(app, (x) => (x.live = next)), 700);
  };
  useEffect(() => () => clearTimeout(timer.current), []);

  const bank = app.profile.sector === "bank" && b.rwa;
  const r = V.capm(a.rf / 100, a.beta, a.erp / 100);
  const G = a.g / 100, ROE = a.roe / 100, P = a.payout / 100;
  const bv = perShare ? b.bvps : b.equity;
  const earn = bv * ROE;
  const d0 = earn * P;
  const gSus = V.sustainableGrowth(ROE, P) * 100;
  const results = [];
  const jpb = V.justifiedPB(ROE, r, G);
  if (jpb !== null) results.push(["Justified P/B × book value", jpb * bv]);
  const jpe = V.justifiedPE(P, r, G);
  if (jpe !== null) results.push(["Justified P/E × normalised earnings", jpe * earn]);
  const ddm = V.gordonDDM(d0, r, G);
  if (ddm !== null) results.push(["Gordon DDM", ddm]);
  const ts = V.twoStageDDM(d0, a.g1 / 100, a.n, G, r);
  if (ts) results.push([`Two-stage DDM (${a.n} yrs at ${a.g1.toFixed(1)} %)`, ts.value]);
  const ri = V.residualIncome(bv, ROE, r, G, P, 10, a.fade);
  if (ri) results.push([`Residual income${a.fade ? " (ROE fades)" : ""}`, ri.value]);
  if (bank) {
    const scale = perShare ? b.shares : 1;
    const fcfe = V.bankDistributableFCFE(earn * scale, b.rwa, a.rwa_g / 100, a.cet1_t / 100) / scale;
    const dcf = V.fcfeDCF(fcfe, a.rwa_g / 100, a.n, G, r);
    if (dcf) results.push(["Capital-generation DCF (FCFE)", dcf.value]);
  }
  const mid = results.length ? median(results.map((x) => x[1])) : null;
  const marketPB = price && perShare ? price / b.bvps : null;
  const points = [];
  if (marketPB) points.push({ name: `${app.profile.short_name} (market)`, roe: b.roeAvg3 ?? a.roe, pb: marketPB });
  points.push({ name: "Your assumption", roe: a.roe, pb: jpb ?? NaN });
  const rVals = [-2, -1, 0, 1, 2].map((d) => r + d / 100);
  const gVals = [-1, -0.5, 0, 0.5, 1].map((d) => Math.max(G + d / 100, 0));
  const grid = V.sensitivityGrid((rr, gg) => {
    const x = V.justifiedPB(ROE, rr, gg);
    return x === null ? null : x * bv;
  }, rVals, gVals);

  const save = () => {
    if (!results.length) return;
    const key = scen || "base";
    upd(app, (x) => {
      x.scenarios ||= {};
      x.scenarios[key] = { assumptions: { ...a, rwa_g: bank ? a.rwa_g : null, cet1_t: bank ? a.cet1_t : null }, r: r * 100, results: Object.fromEntries(results), median: mid, unit };
    });
    setMsg(`${key[0].toUpperCase() + key.slice(1)} case saved.`);
  };
  const sc = ans.scenarios || {};
  const pct = (d) => (v) => `${v.toFixed(d)} %`;

  return (
    <section className="section">
      <div className="section-head"><h2>3 · Assumptions → value (live)</h2></div>
      <div className="grid-2 wide-right">
        <div className="stack tight">
          <h3>Cost of equity (CAPM) <span className="de" lang="de">· Eigenkapitalkosten</span></h3>
          <Slider label="Risk-free rate" value={a.rf} min={0} max={6} step={0.1} onChange={(v) => set("rf", v)} format={pct(1)} />
          <Slider label="Beta" value={a.beta} min={0.4} max={2} step={0.05} onChange={(v) => set("beta", v)} format={(v) => v.toFixed(2)} />
          <Slider label="Equity risk premium" value={a.erp} min={3} max={8} step={0.1} onChange={(v) => set("erp", v)} format={pct(1)} />
          <p>→ cost of equity <b>r = {(r * 100).toFixed(2)} %</b></p>
          <Cfa k="capm" />
          <h3>Profitability, payout and growth</h3>
          <Slider label="Sustainable ROE" value={a.roe} min={0} max={25} step={0.1} onChange={(v) => set("roe", v)} format={pct(1)} help={`Default = ${b.roeBasis || "assumption"} (${(b.roeAvg3 ?? 10).toFixed(1)} %). Adjust for one-offs (Stage 6).`} />
          <Slider label="Payout ratio" value={a.payout} min={0} max={100} step={1} onChange={(v) => set("payout", v)} format={pct(0)} />
          <Slider label="Long-term growth g" value={a.g} min={0} max={4} step={0.1} onChange={(v) => set("g", v)} format={pct(1)} />
          <Slider label="Years of explicit forecast" value={a.n} min={1} max={10} step={1} onChange={(v) => set("n", v)} format={(v) => `${v}`} />
          <Slider label="Near-term dividend growth" value={a.g1} min={-5} max={15} step={0.1} onChange={(v) => set("g1", v)} format={pct(1)} help={`Sustainable growth (1 − payout) × ROE = ${gSus.toFixed(1)} %`} />
          <Toggle label="Let ROE fade to the cost of equity (no lasting advantage)" checked={a.fade} onChange={(v) => set("fade", v)} />
          {bank && (
            <>
              <h3>Capital generation (bank FCFE)</h3>
              <Slider label="RWA growth" value={a.rwa_g} min={-5} max={10} step={0.5} onChange={(v) => set("rwa_g", v)} format={pct(1)} />
              <Slider label="Target CET1 ratio" value={a.cet1_t} min={8} max={20} step={0.1} onChange={(v) => set("cet1_t", v)} format={pct(1)} />
            </>
          )}
        </div>
        <div className="stack">
          {!results.length ? (
            <Callout tone="error">r must be greater than g for these models.</Callout>
          ) : (
            <>
              <Chart spec={Charts.valueBars(results, perShare ? `Value per share (${unit})` : `Equity value (${unit})`, unit, perShare ? price : null)} label="Model values" table={<Table columns={[{ key: "m", label: "Method" }, { key: "v", label: unit, num: true }]} rows={results.map(([m, v]) => ({ _key: m, m, v: f2(v) }))} />} />
              {marketPB ? (
                <>
                  <p className="muted small">Median of your model values: {f2(mid)} vs market price {f2(price)} ({((mid / price - 1) * 100).toFixed(1)} %). A gap is a question — which assumption would have to change to close it?</p>
                  <Callout tone="info" title="Reverse-engineering">At P/B {marketPB.toFixed(2)}× and your r = {(r * 100).toFixed(1)} %, g = {a.g.toFixed(1)} %, the market price implies a sustainable ROE of <b>{(V.impliedRoeFromPB(marketPB, r, G) * 100).toFixed(1)} %</b> (your assumption: {a.roe.toFixed(1)} %).</Callout>
                </>
              ) : null}
              <Chart spec={Charts.pbRoe(r, G, points)} label="ROE vs P/B" />
              <Chart spec={Charts.heatmap(grid, rVals, gVals, "Sensitivity — justified P/B value", unit)} label="Sensitivity grid" />
            </>
          )}
        </div>
      </div>
      <div className="row wrap">
        <Choice label="Save these assumptions as" options={[{ value: "base", label: "Base case" }, { value: "bull", label: "Bull case" }, { value: "bear", label: "Bear case" }]} value={scen} onChange={setScen} />
        <Btn id="s9-save-scen" icon="check" onClick={save} disabled={!results.length}>Save scenario</Btn>
        {msg && <span className="ok-text">{msg}</span>}
      </div>
      {Object.keys(sc).length > 0 && (
        <Table
          columns={[{ key: "s", label: "Scenario" }, { key: "r", label: "Cost of equity %", num: true }, { key: "roe", label: "ROE %", num: true }, { key: "g", label: "g %", num: true }, { key: "m", label: "Median value", num: true }]}
          rows={["bull", "base", "bear"].filter((k) => sc[k]).map((k) => ({ _key: k, s: k[0].toUpperCase() + k.slice(1), r: sc[k].r.toFixed(2), roe: sc[k].assumptions.roe.toFixed(1), g: sc[k].assumptions.g.toFixed(1), m: `${f2(sc[k].median)} ${sc[k].unit}` }))}
        />
      )}
    </section>
  );
}

function Conclusion({ app, ans, b }) {
  const unit = b.perShare ? `${app.currency}/share` : `${app.currency} m`;
  const [text, setText] = useState(ans.conclusion || "");
  const [lo, setLo] = useState(ans.range_lo ?? null);
  const [hi, setHi] = useState(ans.range_hi ?? null);
  const [warn, setWarn] = useState(null);
  const submit = () => {
    if (CA.wordCount(text) < 20 || lo === null || hi === null || lo > hi) return setWarn("Write at least 20 words and give a low and a high value (low ≤ high).");
    setWarn(null);
    upd(app, (a) => Object.assign(a, { conclusion: text.trim(), range_lo: lo, range_hi: hi, conclusion_submitted: true }));
  };
  return (
    <section className="section">
      <div className="section-head"><h2>4 · Your valuation conclusion</h2></div>
      <TextArea id="s9-conclusion" label="Which method do you trust most for this company, why, and which assumption drives the value most?" rows={4} value={text} onChange={setText} />
      <div className="grid-2">
        <NumberField id="s9-lo" label={`Value range — low (${unit})`} value={lo} onChange={setLo} />
        <NumberField id="s9-hi" label={`Value range — high (${unit})`} value={hi} onChange={setHi} />
      </div>
      {warn && <Callout tone="warn">{warn}</Callout>}
      <div><Btn kind="primary" id="s9-conclusion-submit" onClick={submit}>Submit conclusion</Btn></div>
      {ans.conclusion_submitted && (
        <Callout tone="info" title="Checklist for a credible valuation">
          The cost of equity reflects the risks from Stage 7 · sustainable ROE excludes the one-offs from Stage 6 · growth is consistent with payout × ROE · the range is wide enough to reflect your uncertainty · you can name the assumption that would change your mind.
        </Callout>
      )}
    </section>
  );
}
