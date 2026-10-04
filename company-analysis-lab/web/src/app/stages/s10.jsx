// Stage 10 — Investment Thesis (Investment-These). No buy/sell verdict.
import React, { useEffect, useRef, useState } from "react";
import * as CA from "../../lib/ca.js";
import { Btn, Callout, Cfa, Coverage, Details, StageHeader, Task, TextArea, TextInput } from "../ui.jsx";
import { StageFooter } from "../quiz.jsx";
import { copyText, offerDownload } from "../store.js";
import { riskTypes } from "./s07.jsx";

const N = 10;
const MIN = 12;
const SECTIONS = [
  ["summary", "Business summary", "Geschäftsmodell in Kürze"],
  ["trend", "Financial trend", "Finanzielle Entwicklung"],
  ["capital", "Capital strength", "Kapitalstärke"],
  ["valuation", "Valuation", "Bewertung"],
  ["change", "What would change my thesis?", "Was würde meine These ändern?"],
];
const CASES = [["bull", "Bull case"], ["base", "Base case"], ["bear", "Bear case"]];

function prefill(app) {
  const s = app.doc.stages || {};
  const s1 = s[1]?.answers || {}, s7 = s[7]?.answers || {}, s9 = s[9]?.answers || {};
  const names = Object.fromEntries(["bank", "insurer", "corporate"].flatMap((sec) => riskTypes(sec)).map((r) => [r.key, r.en]));
  const top = s7.top3 || {};
  const risks = (top.keys || []).map((k) => `${names[k] || k}: ${top.why?.[k] || ""}`);
  const valuation = s9.conclusion_submitted ? `Value range ${s9.range_lo} – ${s9.range_hi}. ${s9.conclusion || ""}` : "";
  return { summary: s1.summary || "", risks, valuation };
}

export function criteria(ans) {
  const t = ans.thesis || {};
  const three = (xs) => Array.isArray(xs) && xs.length === 3 && xs.every((x) => CA.wordCount(x) >= 5);
  return [
    ["Summary, financial trend, capital strength, valuation and thesis-breakers written", SECTIONS.every(([k]) => CA.wordCount(t[k]) >= MIN)],
    ["Three reasons the company could perform well", three(t.reasons)],
    ["Three major risks", three(t.risks)],
    ["Bull, base and bear cases", CASES.every(([k]) => CA.wordCount(t[`case_${k}`]) >= 8)],
    ["Answered: what else would you need before allocating CHF 10,000?", CA.wordCount(t.chf10k) >= 25 && Boolean(ans.submitted)],
  ];
}

export function thesisMarkdown(app, t, date = new Date().toISOString().slice(0, 10)) {
  const L = [`# Investment thesis — ${app.profile.name}`, "", `_Prepared with Analyst Lab · ${date} · reporting currency ${app.currency}_`, ""];
  L.push("## Business summary", t.summary || "", "", "## Three reasons the company could perform well");
  (t.reasons || []).forEach((r, i) => L.push(`${i + 1}. ${r}`));
  L.push("", "## Three major risks");
  (t.risks || []).forEach((r, i) => L.push(`${i + 1}. ${r}`));
  for (const [k, en] of SECTIONS.slice(1, 4)) L.push("", `## ${en}`, t[k] || "");
  L.push("", "## Scenarios");
  for (const [k, label] of CASES) L.push(`**${label}:** ${t[`case_${k}`] || ""}`, "");
  L.push("## What would change my thesis?", t.change || "", "", "## Before allocating CHF 10,000 I would still need", t.chf10k || "", "", "_This document is a learning exercise and not investment advice._");
  return L.join("\n");
}

const upd = (app, fn) => app.update((d) => {
  const s = (d.stages[N] ||= {});
  s.answers ||= {};
  fn(s.answers);
});

export default function Stage10({ app }) {
  const ans = app.doc.stages?.[N]?.answers || {};
  const [t, setT] = useState(() => {
    const pre = prefill(app);
    const saved = ans.thesis || {};
    const risks = saved.risks || [...pre.risks, "", "", ""].slice(0, 3);
    return { summary: pre.summary, valuation: pre.valuation, ...saved, reasons: saved.reasons || ["", "", ""], risks };
  });
  const [warn, setWarn] = useState(null);
  const [dl, setDl] = useState(null);
  const timer = useRef(null);
  const latest = useRef(t);
  const save = (next) => upd(app, (a) => (a.thesis = next));
  const set = (k, v) => {
    const next = { ...latest.current, [k]: v };
    latest.current = next;
    setT(next);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => save(next), 600);
  };
  const setIdx = (k, i, v) => set(k, latest.current[k].map((x, j) => (j === i ? v : x)));
  useEffect(() => () => {
    if (timer.current) {
      clearTimeout(timer.current);
      save(latest.current);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = () => {
    clearTimeout(timer.current);
    timer.current = null;
    const clean = { ...latest.current, reasons: latest.current.reasons.map((x) => x.trim()), risks: latest.current.risks.map((x) => x.trim()) };
    const missing = criteria({ thesis: clean, submitted: true }).filter(([, ok]) => !ok).map(([l]) => l);
    if (missing.length) {
      save(clean);
      return setWarn(`Still incomplete: ${missing.join("; ")}. (Sections need ≥ ${MIN} words, reasons/risks ≥ 5, cases ≥ 8, the final answer ≥ 25.)`);
    }
    setWarn(null);
    upd(app, (a) => Object.assign(a, { thesis: clean, submitted: true, submitted_at: new Date().toISOString() }));
  };

  const md = ans.submitted ? thesisMarkdown(app, ans.thesis || t) : "";
  const download = async () => {
    const r = await offerDownload(`thesis_${app.profile.id}.md`, md);
    if (r === "saved") setDl({ tone: "success", text: "Thesis saved." });
    else if (r === "unavailable" || r === "error") setDl((await copyText(md)) ? { tone: "info", text: "Downloads are not available here — the Markdown was copied to your clipboard instead." } : { tone: "warn", text: "Downloads and clipboard are unavailable here — copy the text from the preview below." });
  };
  const done = CA.stageComplete(app.doc, N);

  return (
    <div className="page">
      <StageHeader stage={CA.STAGES[9]} profile={app.profile} currency={app.currency} />
      <div className="grid-2 wide-left">
        <Task>
          Finish like an analyst: a thesis that someone else could read in two minutes and check against reality later. Earlier answers are pre-filled where available — <b>condense and sharpen them</b>. There is deliberately no "buy" or "sell" button: the purpose is to make your reasoning, scenarios and uncertainties explicit.
        </Task>
        <Cfa k="thesis" />
      </div>
      <section className="section stack">
        <Head en="Business summary" de="Geschäftsmodell in Kürze" />
        <TextArea id="s10-summary" rows={4} value={t.summary} onChange={(v) => set("summary", v)} />
        <Head en="Three reasons the company could perform well" de="Drei Gründe für eine gute Entwicklung" />
        {[0, 1, 2].map((i) => <TextInput key={i} id={`s10-r${i}`} label={`Reason ${i + 1}`} value={t.reasons[i]} onChange={(v) => setIdx("reasons", i, v)} />)}
        <Head en="Three major risks" de="Drei Hauptrisiken" />
        {[0, 1, 2].map((i) => <TextInput key={i} id={`s10-k${i}`} label={`Risk ${i + 1}`} value={t.risks[i]} onChange={(v) => setIdx("risks", i, v)} />)}
        {SECTIONS.slice(1, 4).map(([k, en, de]) => (
          <div key={k}>
            <Head en={en} de={de} />
            <TextArea id={`s10-${k}`} rows={3} value={t[k]} onChange={(v) => set(k, v)} />
          </div>
        ))}
        <Head en="Scenarios" de="Szenarien" />
        <div className="grid-3">
          {CASES.map(([k, label]) => <TextArea key={k} id={`s10-c-${k}`} label={label} rows={5} value={t[`case_${k}`]} onChange={(v) => set(`case_${k}`, v)} placeholder="What has to happen? Which numbers move? Rough value?" />)}
        </div>
        <Head en={SECTIONS[4][1]} de={SECTIONS[4][2]} />
        <TextArea id="s10-change" rows={3} value={t.change} onChange={(v) => set("change", v)} placeholder="Specific, measurable thesis-breakers (number + time frame)." />
        <h3 className="big-q">If you had CHF 10,000 to allocate, what additional information would you need before making an investment decision?</h3>
        <TextArea id="s10-chf" rows={5} value={t.chf10k} onChange={(v) => set("chf10k", v)} />
        {warn && <Callout tone="warn">{warn}</Callout>}
        <div><Btn kind="primary" id="s10-submit" onClick={submit}>Submit my investment thesis</Btn></div>
      </section>
      {ans.submitted && (
        <section className="section stack">
          <Reflection text={ans.thesis?.chf10k || ""} />
          <div className="row wrap">
            <Btn id="s10-download" icon="down" onClick={download}>Download my thesis (Markdown)</Btn>
            <Btn kind="ghost" icon="copy" onClick={async () => setDl((await copyText(md)) ? { tone: "success", text: "Copied to clipboard." } : { tone: "warn", text: "Clipboard unavailable — copy from the preview." })}>Copy</Btn>
          </div>
          {dl && <Callout tone={dl.tone}>{dl.text}</Callout>}
          <Details summary="Preview">
            <pre className="md-preview">{md}</pre>
          </Details>
        </section>
      )}
      <StageFooter app={app} n={N} criteria={criteria(ans)} />
      {done && <Callout tone="success" title="Analysis complete">You have completed the full analysis of {app.profile.name}. Pick another company — or a peer — and do it again: the second time you will be much faster.</Callout>}
    </div>
  );
}

const Head = ({ en, de }) => <h3>{en} <span className="de" lang="de">· {de}</span></h3>;

function Reflection({ text }) {
  const [cov, miss] = CA.keywordCoverage(text, [
    { point: "Your own objectives, time horizon and risk tolerance", keywords: ["objective", "ziel", "horizon", "horizont", "risk tolerance", "risikotoleranz", "risikobereitschaft", "goal"] },
    { point: "Your existing portfolio and diversification", keywords: ["portfolio", "diversif", "exposure", "allocation", "allokation", "concentration"] },
    { point: "Latest results, guidance and news since the annual report", keywords: ["latest", "quarter", "quartal", "guidance", "news", "update", "half-year", "halbjahr"] },
    { point: "Valuation versus peers and consensus expectations", keywords: ["peer", "consensus", "konsens", "multiple", "analyst"] },
    { point: "Costs, taxes and currency", keywords: ["cost", "kosten", "fee", "tax", "steuer", "currency", "währung", "waehrung", "fx"] },
    { point: "Liquidity / tradability of the shares", keywords: ["liquidity", "liquidität", "liquiditaet", "trading volume", "unlisted", "nicht kotiert", "tradab"] },
    { point: "Management, governance and capital-return plans", keywords: ["management", "governance", "buyback", "rückkauf", "dividend policy", "capital return"] },
  ]);
  return (
    <>
      <h3>Reflection on your last answer</h3>
      <Coverage covered={cov} missed={miss} labelCovered="You thought about" labelMissed="Professionals would also consider" />
      <Cfa k="portfolio" />
      <p className="muted small">Remember: this tool does not tell you whether to buy or sell. A good thesis tells you what to watch — and when you were wrong.</p>
    </>
  );
}
