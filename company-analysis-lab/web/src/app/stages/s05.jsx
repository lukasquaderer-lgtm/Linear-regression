// Stage 5 — Financial Statement Investigation (Analyse der Jahresrechnung)
import React, { useState } from "react";
import * as CA from "../../lib/ca.js";
import * as D from "../../lib/data.js";
import * as M from "../../lib/metrics.js";
import * as C from "../../lib/calc.js";
import { Btn, Callout, Cfa, Choice, Coverage, Details, Metric, MultiChoice, StageHeader, Table, Tabs, Task, TextArea, TextInput } from "../ui.jsx";
import { StageFooter } from "../quiz.jsx";

const N = 5;
const MIN = 12;
const N_INV = 3;
const LOCATIONS = ["Income statement", "Balance sheet", "Cash flow statement", "Statement of changes in equity", "Statement of comprehensive income (OCI)", "Notes – accounting policies / changes in standards", "Notes – segment reporting", "Notes – business combinations / acquisitions", "Notes – provisions, litigation, contingent liabilities", "Notes – financial instruments / fair value", "Notes – insurance contracts / reserves", "Risk report / capital management (Pillar 3, SST, SFCR)", "Management report (Lagebericht)", "Auditor's report – key audit matters"];
const EXPECTED = { "one-off": ["Accounting-driven", "One-off"], accounting: ["Accounting-driven", "One-off"], operational: ["Operational", "Recurring"], structural: ["Operational", "One-off"], transitional: ["Both", "Partly"], regulatory: ["Operational", "Partly"], acquisition: ["Both", "One-off"], capital: ["Operational", "Recurring"] };
const OPINIONS = ["Unqualified (clean)", "Qualified", "Adverse", "Disclaimer of opinion"];

function sections(bank) {
  return [
    { key: "is", en: "Income statement", de: "Erfolgsrechnung", shows: "Revenues, expenses and profit over the year." + (bank ? " For banks: net interest income, fees, trading, operating expenses, credit losses." : " For insurers (IFRS 17): insurance revenue, insurance service expenses, insurance finance result, investment result."), look: bank ? ["Which revenue line drives the change?", "Credit loss expense — build or release?", "Any line called 'other' that is unusually large?", "Effective tax rate vs statutory rate"] : ["Insurance service result vs investment result", "Large catastrophe or reserve effects", "Realised gains on investments", "Effective tax rate"], task: "Which line of the income statement explains most of the change in net income in the latest year? Name it, give the size and say why it moved." },
    { key: "bs", en: "Balance sheet", de: "Bilanz", shows: "What the company owns and how it is funded at year-end." + (bank ? " Banks are funded mainly by deposits and debt; equity is a thin layer." : " Insurers' balance sheets are dominated by investments and insurance contract liabilities (IFRS 17: incl. the CSM)."), look: bank ? ["Funding mix: deposits vs wholesale debt", "Loan book vs deposits (liquidity)", "Goodwill and intangibles (deducted from CET1)", "Level 3 assets"] : ["Investment mix (bonds, equities, real estate)", "Insurance liabilities and the CSM", "Unit-linked assets held for policyholders", "Goodwill and intangibles"], task: "How is the balance sheet funded? Describe the two largest liability items and what share of total assets is equity." },
    { key: "cf", en: "Cash flow statement", de: "Geldflussrechnung", shows: "Cash flows from operating, investing and financing activities.", look: bank ? ["Why operating cash flow swings with deposits, loans and trading balances", "Dividends and buybacks in financing cash flows", "Do not use OCF to judge a bank's earnings quality"] : ["Reconciliation from net income to operating cash flow", "Where investment purchases/sales are classified", "Dividends and buybacks"], task: bank ? "Why is a bank's operating cash flow a poor measure of its earnings quality? Use your company's numbers in the answer." : "Reconcile net income to operating cash flow in the latest year: what are the two largest reconciling items?" },
    { key: "soce", en: "Statement of changes in equity", de: "Eigenkapitalnachweis", shows: "Every movement in equity: net income, dividends, share buybacks, other comprehensive income (OCI), FX translation, acquisitions of minorities.", look: ["Dividends paid vs net income", "Share buybacks (treasury shares)", "OCI — unrealised gains/losses", "Transactions with non-controlling interests"], task: "Explain the 'other movements' in the equity roll-forward below — which items does the statement of changes in equity show?" },
    { key: "notes", en: "Notes", de: "Anhang", shows: "Accounting policies, key estimates and judgements, segment information and details behind every line.", look: bank ? ["Significant estimates: expected credit losses, fair value Level 3, provisions, goodwill", "Changes in accounting policies or restatements", "Segment profitability", "Litigation provisions and contingent liabilities"] : ["Significant estimates: insurance liabilities, discount rates, CSM, investment valuation", "Changes in accounting policies (IFRS 17/9 transition)", "Segment profitability", "Sensitivity analyses"], task: "Name the two or three most important accounting estimates or judgements disclosed in the notes, and say why each could change profit." },
    { key: "audit", en: "Auditor's report", de: "Bericht der Revisionsstelle", shows: "The auditor's opinion and the key audit matters (KAMs) — the areas of highest risk of material misstatement.", look: ["Opinion: unqualified, qualified, adverse or disclaimer?", "Key audit matters and how the auditor addressed them", "Emphasis of matter / going concern paragraphs", "Who is the auditor and since when?"], task: "List the key audit matters and explain in one sentence why each is risky for this company." },
  ];
}

export function changesFor(ds) {
  const exclude = ["operating_cash_flow", "total_liabilities"];
  let ch = C.unusualChanges(ds, { exclude });
  if (ch.length < N_INV) {
    const seen = new Set(ch.map((c) => `${c.metric}|${c.year}`));
    ch = [...ch, ...C.unusualChanges(ds, { rel: 8, pp: 1, exclude }).filter((c) => !seen.has(`${c.metric}|${c.year}`))];
  }
  return ch.slice(0, 8);
}

export default function Stage5({ app }) {
  const { profile, currency } = app;
  const ans = app.doc.stages?.[N]?.answers || {};
  const secs = sections(profile.sector === "bank");
  const changes = changesFor(app.ds);
  const [tab, setTab] = useState("parts");
  const doneSecs = secs.filter((s) => CA.wordCount(ans.sections?.[s.key]) >= MIN).length;
  const inv = Object.values(ans.investigations || {}).filter((v) => v.submitted).length;
  const need = Math.min(N_INV, changes.length);
  const criteria = [
    [`All six parts of the annual report worked through — ${doneSecs}/6`, doneSecs === 6],
    ["Audit opinion type identified", Boolean(ans.auditOpinion)],
    [`Unusual changes investigated — ${inv}/${need}`, inv >= need],
  ];
  return (
    <div className="page">
      <StageHeader stage={CA.STAGES[4]} profile={profile} currency={currency} />
      <div className="grid-2 wide-left">
        <Task>
          Headline numbers are where analysis <b>starts</b>. Open the annual report and work through each part below, then investigate the unusual changes the app found in your dataset: <b>what caused it, is it operational or accounting-driven, recurring or one-off, and where can you verify it?</b>
        </Task>
        <Cfa k="statement_links" />
      </div>
      <Tabs value={tab} onChange={setTab} tabs={[{ id: "parts", label: "Work through the annual report" }, { id: "inv", label: `Investigate unusual changes (${changes.length})` }]} />
      <div className="tab-panel">
        {tab === "parts" ? <Parts app={app} secs={secs} ans={ans} /> : <Investigations app={app} changes={changes} ans={ans} />}
      </div>
      <StageFooter app={app} n={N} criteria={criteria} />
    </div>
  );
}

const upd = (app, fn) => app.update((d) => {
  const s = (d.stages[N] ||= {});
  s.answers ||= {};
  fn(s.answers);
});

function Parts({ app, secs, ans }) {
  const firstOpen = secs.find((s) => CA.wordCount(ans.sections?.[s.key]) < MIN)?.key;
  return (
    <div className="stack">
      {secs.map((s) => <Part key={s.key} app={app} s={s} saved={ans.sections?.[s.key] || ""} open={s.key === firstOpen} ans={ans} />)}
    </div>
  );
}

function Part({ app, s, saved, open, ans }) {
  const [text, setText] = useState(saved);
  const [warn, setWarn] = useState(null);
  const done = CA.wordCount(saved) >= MIN;
  const save = () => {
    if (CA.wordCount(text) < MIN) return setWarn(`Write at least ${MIN} words.`);
    setWarn(null);
    upd(app, (a) => (a.sections = { ...(a.sections || {}), [s.key]: text.trim() }));
  };
  return (
    <Details open={open} status={done ? "done" : "todo"} summary={`${s.en} · ${s.de}`}>
      <p><b>What it shows:</b> {s.shows}</p>
      <p><b>What to look for:</b></p>
      <ul>{s.look.map((l) => <li key={l}>{l}</li>)}</ul>
      {s.key === "soce" && <Rollforward app={app} />}
      {s.key === "cf" && <CashVsProfit app={app} />}
      {s.key === "notes" && <Cfa k="notes" />}
      {s.key === "audit" && (
        <>
          <Cfa k="auditor" />
          <Choice label="Type of audit opinion in the latest annual report" options={OPINIONS} value={ans.auditOpinion} onChange={(v) => upd(app, (a) => (a.auditOpinion = v))} />
        </>
      )}
      <TextArea id={`s5-sec-${s.key}`} label={`Your task: ${s.task}`} rows={4} value={text} onChange={setText} />
      {warn && <Callout tone="warn">{warn}</Callout>}
      <div><Btn id={`s5-save-${s.key}`} onClick={save}>Save</Btn></div>
      {done && s.key === "audit" && app.profile.audit_focus?.length > 0 && (
        <Callout tone="info" title="Typical key audit matters for this company (compare with what you found)">
          <ul>{app.profile.audit_focus.map((k) => <li key={k}>{k}</li>)}</ul>
        </Callout>
      )}
      {s.key === "audit" && ans.auditOpinion && ans.auditOpinion !== OPINIONS[0] && <Callout tone="warn">A modified opinion is rare for large listed financial groups — double-check the opinion paragraph.</Callout>}
    </Details>
  );
}

function Rollforward({ app }) {
  const rows = app.ds.years.slice(1).map((y) => [y, C.impliedOtherEquityMovements(app.ds, y)]).filter(([, r]) => r);
  if (!rows.length) return null;
  const n = (x) => C.fmtNum(x);
  return (
    <>
      <p><b>Equity roll-forward from your dataset</b> (dividends ≈ prior-year DPS × shares)</p>
      <Table columns={[{ key: "y", label: "Year" }, { key: "o", label: "Opening equity", num: true }, { key: "ni", label: "+ Net income", num: true }, { key: "d", label: "− Dividends (est.)", num: true }, { key: "x", label: "± Other movements", num: true }, { key: "c", label: "= Closing equity", num: true }]}
        rows={rows.map(([y, r]) => ({ _key: y, y, o: n(r.opening), ni: n(r.netIncome), d: n(-r.dividends), x: n(r.other), c: n(r.closing) }))} />
      <p className="muted small">Large 'other movements' = buybacks, OCI (e.g. unrealised bond losses), FX translation, acquisitions of minorities, share-based payments. Find them in the statement of changes in equity.</p>
    </>
  );
}

function CashVsProfit({ app }) {
  const has = D.clean(D.series(app.ds, "operating_cash_flow")).length >= 2;
  if (!has) return null;
  return (
    <>
      <Table columns={[{ key: "y", label: "Year" }, { key: "ni", label: "Net income", num: true }, { key: "ocf", label: "Operating cash flow", num: true }]} rows={app.ds.years.map((y) => ({ _key: y, y, ni: C.fmtNum(D.value(app.ds, "net_income", y)), ocf: C.fmtNum(D.value(app.ds, "operating_cash_flow", y)) }))} />
      <Cfa k="accruals" />
    </>
  );
}

function Investigations({ app, changes, ans }) {
  const [idx, setIdx] = useState(0);
  if (!changes.length) return <Callout tone="info">No large changes found in your dataset — complete more metrics in Stage 2.</Callout>;
  const label = (c) => (c.signFlip ? "sign change" : Number.isFinite(c.change) ? `${c.change >= 0 ? "+" : "−"}${Math.abs(c.change).toFixed(1)} ${c.unit}` : "large change");
  const c = changes[Math.min(idx, changes.length - 1)];
  const key = `${c.metric}|${c.year}`;
  return (
    <div className="split">
      <nav className="side-list" aria-label="Unusual changes">
        <p className="muted small">Investigate at least {Math.min(N_INV, changes.length)}. Ranked by size and importance. The analyst notes appear after you submit.</p>
        {changes.map((ch, i) => (
          <button key={`${ch.metric}|${ch.year}`} type="button" className={`side-item ${i === idx ? "active" : ""}`} onClick={() => setIdx(i)}>
            <span className={`status-dot ${ans.investigations?.[`${ch.metric}|${ch.year}`]?.submitted ? "done" : "todo"}`} />
            <span>{M.short(ch.metric, app.custom)} {ch.year}: {label(ch)}</span>
          </button>
        ))}
      </nav>
      <div className="split-main">
        <Investigation key={key} app={app} c={c} saved={ans.investigations?.[key] || {}} changeLabel={label(c)} />
      </div>
    </div>
  );
}

function Investigation({ app, c, saved, changeLabel }) {
  const [f, setF] = useState({ cause: saved.cause || "", nature: saved.nature || null, recur: saved.recur || null, where: saved.where || [], ref: saved.ref || "" });
  const [warn, setWarn] = useState(null);
  const key = `${c.metric}|${c.year}`;
  const acc = app.profile.accounting || {};
  const b0 = acc[String(c.year - 1)], b1 = acc[String(c.year)];
  const submit = () => {
    if (CA.wordCount(f.cause) < MIN || !f.nature || !f.recur || !f.where.length) return setWarn(`Explain the cause (≥ ${MIN} words), classify it twice and pick at least one place to verify it.`);
    setWarn(null);
    upd(app, (a) => (a.investigations = { ...(a.investigations || {}), [key]: { ...f, cause: f.cause.trim(), submitted: true } }));
    const evs = CA.eventsFor(app.profile, c.metric, c.year);
    if (evs.length) {
      const [en, er] = EXPECTED[evs[0].nature] || ["Both", "Partly"];
      const okN = f.nature === en || f.nature === "Both" || en === "Both";
      const okR = f.recur === er || f.recur === "Partly" || er === "Partly";
      app.recordAttempt(N, `inv-${key}`, "operational_vs_accounting", okN && okR);
    }
  };
  return (
    <div className="stack">
      <h2 className="metric-title">{M.short(c.metric, app.custom)} · {c.year - 1} → {c.year}</h2>
      <div className="metrics">
        <Metric label={String(c.year - 1)} value={C.fmtMetric(c.from, c.metric, app.currency, app.custom)} />
        <Metric label={String(c.year)} value={C.fmtMetric(c.to, c.metric, app.currency, app.custom)} />
        <Metric label="Change" value={changeLabel} />
      </div>
      {b0 && b1 && b0 !== b1 && <Callout tone="warn">Hint: the accounting basis changed between these years ({b0} → {b1}).</Callout>}
      <TextArea id={`s5-cause-${key}`} label="What caused this number to change?" rows={4} value={f.cause} onChange={(v) => setF({ ...f, cause: v })} />
      <div className="grid-2">
        <Choice label="Is the change operational or accounting-driven?" options={["Operational", "Accounting-driven", "Both", "Not sure yet"]} value={f.nature} onChange={(v) => setF({ ...f, nature: v })} />
        <Choice label="Is it recurring or one-off?" options={["Recurring", "One-off", "Partly"]} value={f.recur} onChange={(v) => setF({ ...f, recur: v })} />
      </div>
      <MultiChoice label="Where in the annual report could you verify this?" options={LOCATIONS} value={f.where} onChange={(v) => setF({ ...f, where: v })} />
      <TextInput id={`s5-ref-${key}`} label="Page / note reference (optional)" value={f.ref} onChange={(v) => setF({ ...f, ref: v })} />
      {warn && <Callout tone="warn">{warn}</Callout>}
      <div><Btn kind="primary" id="s5-inv-submit" onClick={submit}>{saved.submitted ? "Update my investigation" : "Submit my investigation"}</Btn></div>
      {saved.submitted && <InvFeedback app={app} c={c} inv={saved} />}
    </div>
  );
}

function InvFeedback({ app, c, inv }) {
  const evs = CA.eventsFor(app.profile, c.metric, c.year);
  const [cov, miss] = CA.keywordCoverage(inv.cause, CA.EXPLANATION_DRIVERS);
  return (
    <div className="stack">
      <h3>Feedback</h3>
      <Coverage covered={cov} missed={miss.slice(0, 4)} labelCovered="Your explanation covers" labelMissed="Other common drivers" />
      {!evs.length ? (
        <Callout tone="info">No analyst note for this change. Test your hypothesis: (1) does the management report confirm it? (2) does the segment note show where it happened? (3) is there a matching item in the statement of changes in equity or the notes? If two sources agree, your explanation is probably right.</Callout>
      ) : evs.map((ev) => {
        const [en, er] = EXPECTED[ev.nature] || ["Both", "Partly"];
        const ok = (inv.nature === en || inv.nature === "Both" || en === "Both") && (inv.recur === er || inv.recur === "Partly" || er === "Partly");
        return (
          <div className="card" key={ev.title}>
            <p><b>Analyst note — {ev.year}: {ev.title}</b> · <em>{CA.NATURE_LABEL[ev.nature]}</em></p>
            <p>{ev.detail}</p>
            <p><b>Where to verify:</b> {ev.where_to_verify}</p>
            <p>Your classification: <b>{inv.nature} / {inv.recur}</b> · analyst view: <b>{en} / {er}</b> {ok ? "✓" : "— think again about why they differ"}</p>
          </div>
        );
      })}
    </div>
  );
}
