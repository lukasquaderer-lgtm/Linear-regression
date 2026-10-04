// Stage 1 — Understand the Business (Geschäftsmodell verstehen)
import React, { useState } from "react";
import * as CA from "../../lib/ca.js";
import { Btn, Callout, Cfa, Coverage, Details, StageHeader, Task, TextArea } from "../ui.jsx";
import { StageFooter } from "../quiz.jsx";
import { useAnswers, st } from "./common.js";

const N = 1;
const MIN_WORDS = 10;
export const QUESTIONS = [
  { key: "what_it_does", en: "What does the company actually do?", de: "Was macht das Unternehmen konkret?", hint: "Annual report: 'At a glance', the CEO/Chair letter and the strategy section.", think: { bank: "Is it a universal bank, a wealth manager, a retail bank? Which activity defines it?", insurer: "Life, non-life, reinsurance? Savings products or pure risk cover? Does it also manage assets for others?", corporate: "Which products or services? Who uses them and for what? Which division or product line defines the company?" } },
  { key: "how_money", en: "How does it make money?", de: "Wie verdient es Geld?", hint: "Income statement plus the notes on revenues (interest, fees, trading — insurance revenue, investment result — or sales by product and region).", think: { bank: "Split operating income into interest, fees and trading. Which is largest? Which is most stable? What drives each one?", insurer: "Underwriting result vs investment result vs fees. Who bears the investment risk? Where does the 'float' come from?", corporate: "Product sales, services, licences or royalties? One-off sales or recurring revenue? What sets the price — patents, brand, cost?" } },
  { key: "segments", en: "What are its major business segments?", de: "Welches sind die wichtigsten Geschäftssegmente?", hint: "Segment reporting note (IFRS 8 'Operating segments') and the divisional sections of the management report.", think: { bank: "List each segment and note which one earns the most profit — not just revenue.", insurer: "List each segment (by line of business or geography) and its share of profit.", corporate: "List each division or segment with its share of sales and of operating profit — margins often differ a lot." } },
  { key: "customers", en: "Who are its customers?", de: "Wer sind die Kunden?", hint: "Strategy section and divisional descriptions; distribution channels.", think: { bank: "Private, wealthy, corporate, institutional? Through which channels?", insurer: "Individuals, companies (group life), other insurers (reinsurance)? Via own agents, brokers, banks?", corporate: "Consumers, professionals, businesses or governments? Who decides, who uses and who pays? Direct sales or distributors?" } },
  { key: "markets", en: "Which countries / markets does it operate in?", de: "In welchen Ländern / Märkten ist es tätig?", hint: "Geographic information in the segment note; operating income or invested assets by region.", think: { bank: "Where are the clients, where is the booking centre, where are the profits?", insurer: "Where are premiums written, and where are the peak risks?", corporate: "Where are sales earned and where are the costs incurred? Which currency mismatch does that create?" } },
  { key: "advantages", en: "What are its major competitive advantages?", de: "Was sind die wichtigsten Wettbewerbsvorteile?", hint: "Strategy section and market-position claims — note them now and test them with numbers in later stages.", think: { bank: "Scale, brand, client relationships, cost position, capital strength, regulatory licences?", insurer: "Scale and diversification, distribution control, underwriting expertise, capital strength, ratings?", corporate: "Patents, brand, technology, cost position, switching costs, distribution network, scale?" } },
  { key: "threats", en: "What could threaten the business model?", de: "Was könnte das Geschäftsmodell bedrohen?", hint: "Risk report / 'risk factors', outlook section, regulatory developments.", think: { bank: "Interest rates, regulation, competition, technology, reputation, market downturns?", insurer: "Catastrophes, interest rates, longevity, regulation, pricing cycle, competition?", corporate: "Competition, patent expiry, price regulation, the economic cycle, input costs, currency, technology shifts?" } },
];

export default function Stage1({ app }) {
  const { profile, currency } = app;
  const [form, set, commit] = useAnswers(app, N);
  const [warn, setWarn] = useState([]);
  const submitted = Boolean(st(app, N).submitted?.business);
  const nAnswered = QUESTIONS.filter((q) => CA.wordCount(form[q.key]) >= MIN_WORDS).length;
  const nSent = CA.sentenceCount(form.summary);

  const submit = () => {
    const w = [];
    const short = QUESTIONS.filter((q) => CA.wordCount(form[q.key]) < MIN_WORDS).map((q) => q.en);
    if (short.length) w.push(`Expand these answers to at least ${MIN_WORDS} words: ${short.join("; ")}`);
    if (nSent < 3 || nSent > 5) w.push(`Your summary has ${nSent} sentence(s) — write 3 to 5.`);
    setWarn(w);
    commit(w.length ? null : (s) => (s.submitted = { ...(s.submitted || {}), business: true }));
  };

  return (
    <div className="page">
      <StageHeader stage={CA.STAGES[0]} profile={profile} currency={currency} />
      <div className="grid-2 wide-left">
        <div className="stack">
          <Task>
            Open the latest annual report and answer each question <b>in your own words</b>. Write what you understood, not what you copied. You will only see the analyst reference <b>after</b> you submit.
          </Task>
          <Cfa k="business_model" />
        </div>
        <div className="card facts">
          <h3>Company facts <span className="de" lang="de">· Unternehmensdaten</span></h3>
          <dl>
            <dt>Headquarters</dt><dd>{[profile.headquarters, profile.country].filter(Boolean).join(", ") || "–"}</dd>
            <dt>Listing</dt><dd>{profile.exchange_ticker || (profile.listed ? "Listed" : "Not listed")}</dd>
            <dt>Reporting currency</dt><dd>{currency}</dd>
            <dt>Regulator</dt><dd>{profile.regulator || "–"}</dd>
            <dt>Capital regime</dt><dd>{profile.capital_regime || "–"}</dd>
            <dt>Accounting</dt><dd>{[...new Set(Object.values(profile.accounting || {}))].join(", ") || "–"}</dd>
          </dl>
          {profile.investor_relations && (
            <p><a href={profile.investor_relations} target="_blank" rel="noopener noreferrer">Open investor relations ↗</a></p>
          )}
          <p className="muted small">{profile.annual_report_hint}</p>
        </div>
      </div>

      <section className="section">
        <div className="section-head"><h2>1 · Seven questions about the business</h2></div>
        <div className="stack">
          {QUESTIONS.map((q, i) => (
            <TextArea key={q.key} id={`s1-${q.key}`} rows={3} label={<><b>{i + 1}. {q.en}</b> <span className="de" lang="de">· {q.de}</span></>} help={`Where to look: ${q.hint}`} placeholder={q.think[profile.sector]} value={form[q.key]} onChange={(v) => set(q.key, v)} />
          ))}
        </div>
      </section>
      <section className="section">
        <div className="section-head"><h2>2 · The business in your own words <span className="de" lang="de">· Das Geschäft in eigenen Worten</span></h2></div>
        <TextArea id="s1-summary" rows={5} help="3–5 sentences, as if explaining the company to a colleague who has never heard of it: what it does, how it earns money, for whom, where, and what makes it special." value={form.summary} onChange={(v) => set("summary", v)} hint={`${nSent} sentences · ${CA.wordCount(form.summary)} words`} />
        {warn.map((w) => <Callout key={w} tone="warn">{w}</Callout>)}
        <Btn kind="primary" id="s1-submit" onClick={submit}>{submitted ? "Update my answers" : "Submit my answers"}</Btn>
      </section>

      {submitted && <Feedback profile={profile} form={form} />}

      <StageFooter app={app} n={N} criteria={[
        [`All seven questions answered in your own words (≥ ${MIN_WORDS} words each) — ${nAnswered}/7`, nAnswered === 7],
        [`Business summary of 3–5 sentences — currently ${nSent}`, nSent >= 3 && nSent <= 5],
        ["Submitted and compared with the analyst reference", submitted],
      ]} />
    </div>
  );
}

function Feedback({ profile, form }) {
  const ref = profile.business_reference || {};
  if (!Object.keys(ref).length) {
    return <Callout tone="info">No reference notes exist for this company yet. Compare your answers with the annual report's own description and with a peer.</Callout>;
  }
  const allPoints = [...(ref.what_it_does?.key_points || []), ...(ref.how_money?.key_points || [])];
  const [sc, sm] = CA.keywordCoverage(form.summary, allPoints);
  return (
    <section className="section">
      <div className="section-head"><h2>3 · Compare with the analyst reference</h2></div>
      <p className="muted">Keyword matching gives a rough first check (English and German). Read the reference and judge for yourself what you missed — or what you saw that the reference does not mention.</p>
      <div className="stack">
        {QUESTIONS.map((q) => {
          const r = ref[q.key];
          if (!r) return null;
          const [cov, miss] = CA.keywordCoverage(form[q.key], r.key_points);
          return (
            <Details key={q.key} status={miss.length ? "half" : "done"} summary={`${q.en} — ${cov.length}/${cov.length + miss.length} key points`}>
              <p><em>Your answer:</em> {form[q.key]}</p>
              <Coverage covered={cov} missed={miss} />
              <Callout tone="info" title="Analyst reference">{r.reference}</Callout>
            </Details>
          );
        })}
        <div className="card">
          <h3>Your summary</h3>
          <p>{form.summary}</p>
          <Coverage covered={sc} missed={sm} labelCovered="Your summary mentions" labelMissed="A complete summary would also mention" />
        </div>
        <Cfa k="industry_analysis" />
        {profile.id === "prismalife" && <p className="muted small">PrismaLife reference notes are based on limited public information — your own knowledge of the company may be more accurate.</p>}
      </div>
    </section>
  );
}
