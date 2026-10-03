// Stage 8 — Peer Comparison (Peer-Vergleich)
import React, { useEffect, useState } from "react";
import * as CA from "../../lib/ca.js";
import * as D from "../../lib/data.js";
import * as M from "../../lib/metrics.js";
import * as R from "../../lib/ratios.js";
import { Btn, Callout, Cfa, Choice, Coverage, Select, StageHeader, Table, Task, TextArea } from "../ui.jsx";
import { Chart, C as Charts } from "../charts.jsx";
import { StageFooter } from "../quiz.jsx";

const N = 8;
const PREDICT = ["Target higher", "Peer higher", "About the same"];

export function comparisonSet(a, b) {
  const common = [
    { key: "roe", kind: "ratio", label: "Return on equity", unit: "%", why: "Profitability for shareholders — comparable across sectors." },
    { key: "payout", kind: "ratio", label: "Dividend payout ratio", unit: "%", why: "How much profit is distributed." },
    { key: "net_income", kind: "indexed", label: "Net income growth (indexed)", unit: "index", why: "Growth path, independent of size and currency." },
    { key: "total_equity", kind: "indexed", label: "Book value growth (indexed)", unit: "index", why: "Growth of shareholders' equity." },
  ];
  if (a === "bank" && b === "bank") return [common[0], { key: "roa", kind: "ratio", label: "Return on assets", unit: "%", why: "Profitability per unit of balance sheet." }, { key: "cost_income", kind: "ratio", label: "Cost/income ratio", unit: "%", why: "Efficiency (lower is better)." }, { key: "cet1_ratio", kind: "metric", label: "CET1 ratio", unit: "%", why: "Capital strength — note different regulatory regimes (Swiss TBTF vs EEA CRR)." }, { key: "leverage", kind: "ratio", label: "Financial leverage", unit: "×", why: "How much ROE comes from leverage." }, { key: "fee_share", kind: "ratio", label: "Fee income share", unit: "%", why: "Business mix: capital-light fees vs interest." }, { key: "nii_share", kind: "ratio", label: "Net interest income share", unit: "%", why: "Sensitivity to interest rates." }, ...common.slice(1)];
  if (a === "insurer" && b === "insurer") return [common[0], { key: "roa", kind: "ratio", label: "Return on assets", unit: "%", why: "Profitability per unit of balance sheet (depends on unit-linked assets)." }, { key: "solvency_ratio", kind: "metric", label: "Solvency ratio", unit: "%", why: "Capital strength — SST and Solvency II ratios are not identical frameworks." }, { key: "leverage", kind: "ratio", label: "Financial leverage", unit: "×", why: "Balance-sheet leverage." }, { key: "investment_share", kind: "ratio", label: "Investment income share", unit: "%", why: "Dependence on investment returns." }, { key: "combined_ratio", kind: "metric", label: "Combined ratio", unit: "%", why: "Only meaningful if both write P&C business." }, ...common.slice(1)];
  return [...common, { key: "equity_ratio", kind: "ratio", label: "Equity / total assets", unit: "%", why: "Rough leverage — but bank and insurer balance sheets are structurally different." }];
}

export function seriesFor(item, ds) {
  if (item.kind === "ratio") return D.clean(R.ratioSeries(ds, item.key));
  const s = D.clean(D.series(ds, item.key));
  if (item.kind === "indexed") return s.length && s[0][1] > 0 ? s.map(([y, v]) => [y, (v / s[0][1]) * 100]) : [];
  return s;
}

const upd = (app, fn) => app.update((d) => {
  const s = (d.stages[N] ||= {});
  s.answers ||= {};
  fn(s.answers);
});

export default function Stage8({ app }) {
  const { profile, currency } = app;
  const ans = app.doc.stages?.[N]?.answers || {};
  const others = app.companies.filter((c) => c.profile.id !== profile.id);
  const suggested = (profile.peers_suggested || []).filter((p) => others.some((c) => c.profile.id === p));
  const peerId = others.some((c) => c.profile.id === ans.peerId) ? ans.peerId : suggested[0] || others[0]?.profile.id;
  useEffect(() => {
    if (peerId) app.loadDoc(peerId);
    if (peerId && peerId !== ans.peerId) upd(app, (a) => (a.peerId = peerId));
  }, [peerId]); // eslint-disable-line react-hooks/exhaustive-deps
  const peer = others.find((c) => c.profile.id === peerId)?.profile;
  const pds = peerId ? app.datasetFor(peerId) : null;
  const criteria = [
    ["Peer selected and comparability assessed", Boolean(ans.peerId) && Boolean(ans.comparabilityNote)],
    ["Predictions made before seeing the comparison", Boolean(ans.predicted)],
    ["Biggest difference explained", CA.wordCount(ans.explanation) >= 25],
  ];
  if (!peer || !pds) return <div className="page"><Callout tone="info">Add another company first.</Callout></div>;
  const peerCcy = app.docs[peerId]?.settings?.currency || peer.currency;
  const nameA = profile.short_name, nameB = peer.short_name;
  const items = comparisonSet(profile.sector, peer.sector).filter((it) => seriesFor(it, app.ds).length >= 2 || seriesFor(it, pds).length >= 2);
  const predItems = items.filter((i) => i.kind !== "indexed").slice(0, 3);

  const accA = [...new Set(Object.values(profile.accounting || {}))].sort().join(", ");
  const accB = [...new Set(Object.values(peer.accounting || {}))].sort().join(", ");
  const rows = [
    ["Business model", profile.subsector, peer.subsector, profile.sector === peer.sector],
    ["Sector", profile.sector, peer.sector, profile.sector === peer.sector],
    ["Reporting currency", currency, peerCcy, currency === peerCcy],
    ["Accounting basis", accA, accB, accA === accB],
    ["Listed", profile.listed ? "yes" : "no", peer.listed ? "yes" : "no", profile.listed === peer.listed],
    ["Regulator / regime", profile.capital_regime, peer.capital_regime, profile.capital_regime === peer.capital_regime],
  ];
  const gaps = D.requiredMetricKeys(peer).filter((k) => !D.clean(D.series(pds, k)).length);

  return (
    <div className="page">
      <StageHeader stage={CA.STAGES[7]} profile={profile} currency={currency} />
      <div className="grid-2 wide-left">
        <Task>Choose a peer, check how comparable it really is, <b>predict</b> where the two differ — then look at the side-by-side 5-year trends. The app only compares metrics that make sense for the pair (a bank's CET1 ratio is not comparable with an insurer's solvency ratio).</Task>
        <Cfa k="peers" />
      </div>
      <Select id="s8-peer" label="Peer company" value={peerId} options={others.map((c) => ({ value: c.profile.id, label: `${c.profile.short_name} · ${c.profile.sector}${suggested.includes(c.profile.id) ? "  (suggested)" : ""}` }))} onChange={(v) => upd(app, (a) => { a.peerId = v; a.predicted = false; a.predictions = {}; })} />
      <section className="section">
        <div className="section-head"><h2>1 · How comparable are they?</h2></div>
        <Table columns={[{ key: "d", label: "Dimension" }, { key: "a", label: nameA }, { key: "b", label: nameB }, { key: "s", label: "Same?" }]} rows={rows.map(([d, a, b, same]) => ({ _key: d, d, a: a || "–", b: b || "–", s: same ? "✓" : "⚠" }))} />
        {profile.sector !== peer.sector && <Callout tone="warn">Cross-sector comparison: only ROE, payout, growth and simple leverage are shown. Capital ratios (CET1 vs solvency) measure different things.</Callout>}
        {peerCcy !== currency && <Callout tone="info">Different reporting currencies: compare ratios and indexed growth, never absolute amounts.</Callout>}
        {gaps.length > 0 && <p className="muted small">Peer data gaps: {gaps.map((k) => M.short(k)).join(", ")} — switch to {nameB} and complete its Stage 2 to fill them.</p>}
        <Note app={app} saved={ans.comparabilityNote || ""} />
      </section>
      <section className="section">
        <div className="section-head"><h2>2 · Predict first</h2></div>
        {!ans.predicted ? <Predict app={app} items={predItems} /> : <p className="muted">Predictions locked: {predItems.map((i) => `${i.label}: ${ans.predictions?.[i.key] || "—"}`).join(" · ")}</p>}
      </section>
      {ans.predicted && <Reveal app={app} items={items} pds={pds} nameA={nameA} nameB={nameB} ans={ans} />}
      <StageFooter app={app} n={N} criteria={criteria} />
    </div>
  );
}

function Note({ app, saved }) {
  const [t, setT] = useState(saved);
  const [warn, setWarn] = useState(null);
  return (
    <div className="stack tight">
      <TextArea id="s8-note" label="Which differences limit this comparison, and how will you deal with them?" rows={3} value={t} onChange={setT} />
      {warn && <Callout tone="warn">{warn}</Callout>}
      <div><Btn id="s8-note-save" onClick={() => (CA.wordCount(t) < 10 ? setWarn("Write at least 10 words.") : (setWarn(null), upd(app, (a) => (a.comparabilityNote = t.trim()))))}>Save</Btn>{saved && <span className="ok-text"> Saved.</span>}</div>
    </div>
  );
}

function Predict({ app, items }) {
  const [p, setP] = useState({});
  const [why, setWhy] = useState("");
  const [warn, setWarn] = useState(null);
  const lock = () => {
    if (items.some((i) => !p[i.key]) || CA.wordCount(why) < 10) return setWarn("Answer every prediction and give a reason (≥ 10 words).");
    upd(app, (a) => {
      a.predicted = true;
      a.predictions = p;
      a.predictionWhy = why.trim();
    });
  };
  return (
    <div className="stack">
      <p className="muted">Based on what you know about both business models — before looking at the numbers.</p>
      {items.map((i) => <Choice key={i.key} label={`${i.label}: which is higher in the latest year?`} options={PREDICT} value={p[i.key]} onChange={(v) => setP({ ...p, [i.key]: v })} />)}
      <TextArea id="s8-why" label="Why do you expect these differences?" rows={3} value={why} onChange={setWhy} />
      {warn && <Callout tone="warn">{warn}</Callout>}
      <div><Btn kind="primary" icon="lock" id="s8-lock" onClick={lock}>Lock in my predictions</Btn></div>
      <Callout tone="info">The comparison appears after you lock in your predictions.</Callout>
    </div>
  );
}

function Reveal({ app, items, pds, nameA, nameB, ans }) {
  const [expl, setExpl] = useState(ans.explanation || "");
  const [warn, setWarn] = useState(null);
  const summary = [];
  for (const it of items) {
    const sa = Object.fromEntries(seriesFor(it, app.ds)), sb = Object.fromEntries(seriesFor(it, pds));
    const common = Object.keys(sa).filter((y) => y in sb).sort();
    if (!common.length) continue;
    const y = common[common.length - 1];
    const a = sa[y], b = sb[y];
    const actual = Math.abs(a - b) <= 0.05 * Math.max(Math.abs(a), Math.abs(b), 1e-9) ? "About the same" : a > b ? "Target higher" : "Peer higher";
    summary.push({ _key: it.key, m: it.label, y, a: a.toFixed(2), b: b.toFixed(2), p: ans.predictions?.[it.key] || "—", act: actual });
  }
  const preds = summary.filter((r) => r.p !== "—");
  const hits = preds.filter((r) => r.p === r.act).length;
  const [cov, miss] = CA.keywordCoverage(ans.explanation || "", [
    { point: "Business model / mix", keywords: ["business model", "mix", "fee", "wealth", "reinsur", "life", "geschäftsmodell"] },
    { point: "Capital and leverage", keywords: ["capital", "kapital", "leverage", "cet1", "solvency", "solvenz"] },
    { point: "Accounting differences", keywords: ["ifrs", "gaap", "accounting", "rechnungslegung"] },
    { point: "One-off effects", keywords: ["one-off", "einmal", "goodwill", "acquisition", "restructur"] },
    { point: "Link to valuation (P/B, ROE vs cost of equity)", keywords: ["p/b", "price-to-book", "valuation", "bewertung", "cost of equity", "multiple"] },
  ]);
  return (
    <>
      <section className="section">
        <div className="section-head"><h2>3 · Side by side — 5-year trends</h2></div>
        <Table columns={[{ key: "m", label: "Metric" }, { key: "y", label: "Year" }, { key: "a", label: nameA, num: true }, { key: "b", label: nameB, num: true }, { key: "p", label: "Your prediction" }, { key: "act", label: "Actual" }]} rows={summary} />
        <p className="muted small">Predictions correct: {hits}/{preds.length}. Misses are the interesting part — what did you not know?</p>
        <div className="grid-2">
          {items.map((it) => {
            const series = {};
            const sa = seriesFor(it, app.ds), sb = seriesFor(it, pds);
            if (sa.length) series[nameA] = sa;
            if (sb.length) series[nameB] = sb;
            return (
              <div key={it.key}>
                <Chart spec={Charts.compare(series, it.label, it.unit, { [nameA]: 0, [nameB]: 1 })} label={it.label} />
                <p className="muted small">{it.why}</p>
              </div>
            );
          })}
        </div>
      </section>
      <section className="section">
        <div className="section-head"><h2>4 · Explain the biggest difference</h2></div>
        <TextArea id="s8-explain" label="Which difference matters most for valuation, and what explains it (business model, capital, accounting, one-offs)?" rows={4} value={expl} onChange={setExpl} />
        {warn && <Callout tone="warn">{warn}</Callout>}
        <div><Btn kind="primary" id="s8-explain-submit" onClick={() => (CA.wordCount(expl) < 25 ? setWarn("Write at least 25 words.") : (setWarn(null), upd(app, (a) => (a.explanation = expl.trim()))))}>Submit</Btn></div>
        {CA.wordCount(ans.explanation) >= 25 && (
          <>
            <Coverage covered={cov} missed={miss} />
            <Cfa k="justified_pb" />
          </>
        )}
      </section>
    </>
  );
}
