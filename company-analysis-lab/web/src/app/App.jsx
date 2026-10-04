import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as D from "../lib/data.js";
import * as M from "../lib/metrics.js";
import * as CA from "../lib/ca.js";
import * as Q from "../lib/questions.js";
import { COMPANIES } from "../generated/data.js";
import { createStore, offerDownload, copyText } from "./store.js";
import { Btn, Icon, Toggle, Select, TextInput, Callout } from "./ui.jsx";
import { ThemeProvider } from "./charts.jsx";
import { STAGE_VIEWS } from "./stages/index.js";
import { Review } from "./quiz.jsx";

const UNLOCK_ALL = typeof location !== "undefined" && location.hash === "#unlock-all";

export const emptyDoc = (companyId) => ({ v: 1, companyId, stages: {}, verified: {}, verifiedRef: {}, settings: {}, customMetrics: {}, dataset: null });

const docKey = (id) => `c_${id}`;

export default function App() {
  const store = useMemo(() => createStore((s) => setSaveState(s)), []);
  const [saveState, setSaveState] = useState({ mode: "local", state: "idle" });
  const [booted, setBooted] = useState(false);
  const [learner, setLearner] = useState(Q.emptyLearner());
  const [docs, setDocs] = useState({});
  const [companyId, setCompanyId] = useState(COMPANIES[0].profile.id);
  const [view, setView] = useState({ kind: "stage", n: null });
  const [navOpen, setNavOpen] = useState(false);
  const dirty = useRef({});

  // ---------------------------------------------------------------- boot
  useEffect(() => {
    let alive = true;
    (async () => {
      await store.init();
      const l = { ...Q.emptyLearner(), ...((await store.load("learner")) || {}) };
      l.settings = { ...Q.emptyLearner().settings, ...(l.settings || {}) };
      const ids = [...COMPANIES.map((c) => c.profile.id), ...(l.customCompanies || []).map((c) => c.profile.id)];
      const cid = ids.includes(l.settings.lastCompany) ? l.settings.lastCompany : ids[0];
      const d = (await store.load(docKey(cid))) || emptyDoc(cid);
      if (!alive) return;
      setLearner(l);
      setDocs({ [cid]: { ...emptyDoc(cid), ...d } });
      setCompanyId(cid);
      setBooted(true);
    })();
    return () => {
      alive = false;
    };
  }, [store]);

  // ---------------------------------------------------------------- persistence on change
  const firstLearner = useRef(true);
  useEffect(() => {
    if (!booted) return;
    if (firstLearner.current) {
      firstLearner.current = false;
      return;
    }
    store.save("learner", { ...learner, history: (learner.history || []).slice(-200) });
  }, [learner, booted, store]);
  useEffect(() => {
    if (!booted) return;
    for (const id of Object.keys(dirty.current)) {
      if (docs[id]) store.save(docKey(id), docs[id]);
    }
    dirty.current = {};
  }, [docs, booted, store]);

  // ---------------------------------------------------------------- companies
  const companies = useMemo(() => [...COMPANIES, ...(learner.customCompanies || [])].map((c) => ({ ...c, profile: D.withDefaults(c.profile) })), [learner.customCompanies]);
  const company = companies.find((c) => c.profile.id === companyId) || companies[0];
  const profile = company.profile;
  const doc = docs[companyId] || emptyDoc(companyId);
  const training = learner.settings.trainingMode !== false;

  const loadDoc = useCallback(
    async (id) => {
      if (docs[id]) return docs[id];
      const d = { ...emptyDoc(id), ...((await store.load(docKey(id))) || {}) };
      setDocs((prev) => (prev[id] ? prev : { ...prev, [id]: d }));
      return d;
    },
    [docs, store],
  );

  const switchCompany = async (id) => {
    await loadDoc(id);
    setCompanyId(id);
    setView({ kind: "stage", n: null });
    setNavOpen(false);
    setLearner((l) => ({ ...l, settings: { ...l.settings, lastCompany: id } }));
    window.scrollTo?.(0, 0);
  };

  // ---------------------------------------------------------------- mutation helpers
  const update = useCallback(
    (fn, id = companyId) => {
      setDocs((prev) => {
        const next = structuredClone(prev[id] || emptyDoc(id));
        fn(next);
        dirty.current[id] = true;
        return { ...prev, [id]: next };
      });
    },
    [companyId],
  );
  const updateLearner = useCallback((fn) => {
    setLearner((prev) => {
      const next = structuredClone(prev);
      fn(next);
      return next;
    });
  }, []);

  const startDataset = (c) => {
    if (D.BUILTIN.includes(c.profile.id)) return D.starterDataset(c.profile.id);
    return { years: [...c.years], values: structuredClone(c.values), meta: structuredClone(c.meta) };
  };
  const customKeys = Object.keys(doc.customMetrics || {});
  const ds = useMemo(() => D.ensureRows(doc.dataset || startDataset(company), [...D.requiredMetricKeys(profile), ...customKeys]), [doc.dataset, company, profile, customKeys.join("|")]);

  const datasetFor = useCallback(
    (id) => {
      const c = companies.find((x) => x.profile.id === id);
      if (!c) return null;
      const d = docs[id];
      return D.ensureRows(d?.dataset || startDataset(c), D.requiredMetricKeys(c.profile));
    },
    [companies, docs],
  );

  const currentN = CA.currentStage(doc, training);
  const n = view.n && CA.isUnlocked(doc, view.n, training, UNLOCK_ALL) ? view.n : currentN;
  const go = (k) => {
    setView({ kind: "stage", n: k });
    setNavOpen(false);
    window.scrollTo?.(0, 0);
  };

  const app = {
    profile,
    doc,
    learner,
    ds,
    currency: doc.settings?.currency || profile.currency,
    custom: doc.customMetrics || {},
    training,
    companies,
    update,
    updateLearner,
    go,
    loadDoc,
    datasetFor,
    docs,
    saveDataset: (next) => update((d) => (d.dataset = next)),
    // Feed a first attempt from the stage work (not only quizzes) into spaced repetition.
    recordAttempt: (stage, onceKey, concept, correct) => {
      if (doc.stages?.[stage]?.recorded?.includes(onceKey)) return;
      update((d) => {
        const s = (d.stages[stage] ||= {});
        s.recorded = [...new Set([...(s.recorded || []), onceKey])];
      });
      updateLearner((l) => Q.record(l, concept, correct ? "correct" : "wrong"));
    },
  };

  if (!booted) {
    return (
      <div className="boot">
        <div className="boot-mark">AL</div>
        <p>Loading your workspace…</p>
      </div>
    );
  }

  const StageView = STAGE_VIEWS[n];
  return (
    <ThemeProvider>
      <div className="shell">
        <aside className={navOpen ? "nav open" : "nav"}>
          <div className="brand">
            <div className="brand-mark">AL</div>
            <div>
              <div className="brand-name">Analyst Lab</div>
              <div className="brand-sub">Equity analysis of Swiss &amp; Liechtenstein companies</div>
            </div>
            <button type="button" className="nav-toggle" aria-expanded={navOpen} onClick={() => setNavOpen((o) => !o)}>
              {navOpen ? "Close" : "Stages"}
            </button>
          </div>
          <div className="nav-body">
            <Select id="company-select" label="Company" value={companyId} options={companies.map((c) => ({ value: c.profile.id, label: `${c.profile.short_name} · ${M.sectorName(c.profile.sector)}` }))} onChange={switchCompany} />
            <Toggle id="training-toggle" label="Analyst Training Mode" checked={training} onChange={(v) => updateLearner((l) => (l.settings.trainingMode = v))} />
            <div className="progress" aria-label="Progress">
              <div className="progress-bar" style={{ width: `${CA.overallProgress(doc, training) * 100}%` }} />
            </div>
            <div className="nav-caption">
              {Math.round(CA.overallProgress(doc, training) * 10)}/10 stages on {profile.short_name}
              {UNLOCK_ALL && " · all stages unlocked"}
            </div>
            <nav className="stage-nav" aria-label="Stages">
              {CA.STAGES.map((s) => {
                const unlocked = CA.isUnlocked(doc, s.n, training, UNLOCK_ALL);
                const passed = CA.stagePassed(doc, s.n, training);
                const active = view.kind === "stage" && n === s.n;
                return (
                  <button key={s.n} type="button" id={`nav-${s.n}`} className={`nav-item${active ? " active" : ""}${passed ? " passed" : ""}`} disabled={!unlocked} onClick={() => go(s.n)} aria-current={active ? "step" : undefined}>
                    <span className="nav-num">{passed ? <Icon name="check" size={14} /> : unlocked ? s.n : <Icon name="lock" size={13} />}</span>
                    <span className="nav-label">{s.en}</span>
                  </button>
                );
              })}
            </nav>
            <div className="nav-group">
              <button type="button" id="nav-review" className={`nav-item${view.kind === "review" ? " active" : ""}`} onClick={() => { setView({ kind: "review" }); setNavOpen(false); }}>
                <span className="nav-num"><Icon name="spark" size={14} /></span>
                <span className="nav-label">Concept review</span>
              </button>
              <button type="button" id="nav-workspace" className={`nav-item${view.kind === "workspace" ? " active" : ""}`} onClick={() => { setView({ kind: "workspace" }); setNavOpen(false); }}>
                <span className="nav-num"><Icon name="book" size={14} /></span>
                <span className="nav-label">Workspace &amp; companies</span>
              </button>
            </div>
            <SaveBadge s={saveState} />
          </div>
        </aside>
        <main className="main" id="main">
          {view.kind === "review" && <Review app={app} />}
          {view.kind === "workspace" && <Workspace app={app} store={store} switchCompany={switchCompany} setDocs={setDocs} saveState={saveState} />}
          {view.kind === "stage" && <StageView key={`${companyId}-${n}`} app={app} />}
          <footer className="foot">
            Learning tool — not investment advice. Starter figures are unverified; check every number against the annual report.
          </footer>
        </main>
      </div>
    </ThemeProvider>
  );
}

function SaveBadge({ s }) {
  const where = s.mode === "account" ? "Saved to your Claude account" : s.mode === "local" ? "Saved in this browser only" : "Not saved — storage unavailable";
  const state = s.state === "saving" || s.state === "dirty" ? "Saving…" : s.state === "error" ? "Last save failed — keep this tab open and try again" : where;
  return (
    <div className={`save-badge ${s.mode}`} role="status">
      <span className="save-dot" />
      {state}
    </div>
  );
}

// -------------------------------------------------------------------- workspace page

function Workspace({ app, store, switchCompany, setDocs, saveState }) {
  const [msg, setMsg] = useState(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [form, setForm] = useState({ name: "", sector: "bank", currency: "CHF", country: "", listed: true });
  const fileRef = useRef(null);
  const { profile, doc } = app;

  const exportJSON = async () => {
    const blob = JSON.stringify({ format: "analyst-lab-export/1", exported: new Date().toISOString(), companyId: profile.id, doc, learner: app.learner }, null, 2);
    const r = await offerDownload(`analyst-lab-${profile.id}.json`, blob);
    if (r === "unavailable") setMsg({ tone: "warn", text: (await copyText(blob)) ? "Downloads are not available here — your export was copied to the clipboard instead." : "Downloads and clipboard are both unavailable in this view." });
    else if (r === "saved") setMsg({ tone: "success", text: "Export saved." });
  };
  const importJSON = async (file) => {
    try {
      const data = JSON.parse(await file.text());
      if (data.format !== "analyst-lab-export/1" || !data.doc || !data.companyId) throw new Error("This file is not an Analyst Lab export.");
      app.update((d) => Object.assign(d, data.doc), data.companyId);
      setMsg({ tone: "success", text: `Restored your work on ${data.companyId}.` });
      await switchCompany(data.companyId);
    } catch (e) {
      setMsg({ tone: "error", text: e.message || "Could not read the file." });
    }
  };
  const reset = () => {
    setDocs((prev) => ({ ...prev, [profile.id]: emptyDoc(profile.id) }));
    store.remove(`c_${profile.id}`);
    setConfirmReset(false);
    setMsg({ tone: "success", text: `All your work on ${profile.short_name} was deleted.` });
  };
  const addCompany = async () => {
    if (!form.name.trim()) return setMsg({ tone: "error", text: "Enter a company name." });
    const base = D.slugify(form.name);
    let id = base, i = 2;
    while (app.companies.some((c) => c.profile.id === id)) id = `${base}_${i++}`;
    const p = {
      id, name: form.name.trim(), short_name: form.name.trim(), sector: form.sector, subsector: "", country: form.country, headquarters: "", listed: form.listed,
      exchange_ticker: "", currency: form.currency, currency_confirmed: true, fiscal_year_end: "31 December", accounting: {}, accounting_notes: "", regulator: "", capital_regime: "",
      investor_relations: "", annual_report_hint: "Find the latest annual report on the company's investor-relations website.", data_source: "Entered by you.",
      required_extra: [], not_applicable: form.listed ? [] : ["eps", "dps", "shares_outstanding", "share_price"],
    };
    const dsNew = D.emptyDataset(D.requiredMetricKeys(D.withDefaults(p)), [2021, 2022, 2023, 2024, 2025]);
    app.updateLearner((l) => (l.customCompanies = [...(l.customCompanies || []), { profile: p, ...dsNew }]));
    setForm({ ...form, name: "" });
    setMsg({ tone: "success", text: `${p.name} added. Start with Stage 1.` });
    setTimeout(() => switchCompany(id), 0);
  };

  return (
    <div className="page">
      <header className="stage-head">
        <div className="kicker">Workspace</div>
        <h1>Your work and companies</h1>
        <p className="head-goal">Back up or restore your analysis, start a company from scratch, or reset one.</p>
      </header>
      {msg && <Callout tone={msg.tone}>{msg.text}</Callout>}
      <div className="grid-2">
        <div className="card">
          <h3>Where your work is kept</h3>
          <p>
            {saveState.mode === "account"
              ? "Everything you enter is saved privately to your Claude account for this artifact. Nobody else who opens the page can see it."
              : saveState.mode === "local"
                ? "Your work is saved in this browser only. It stays here if you reload, but it will not follow you to another device. Export a backup if it matters."
                : "This view cannot save anything. Export your work before you close the page."}
          </p>
          <div className="row">
            <Btn kind="primary" icon="down" onClick={exportJSON}>Export {profile.short_name} (JSON)</Btn>
            <Btn onClick={() => fileRef.current?.click()}>Restore an export…</Btn>
            <input ref={fileRef} type="file" accept=".json,application/json" hidden onChange={(e) => e.target.files[0] && importJSON(e.target.files[0])} />
          </div>
        </div>
        <div className="card">
          <h3>Reset {profile.short_name}</h3>
          <p>Deletes your answers, quizzes and data edits for this company. Your concept-review history stays.</p>
          {!confirmReset ? (
            <Btn onClick={() => setConfirmReset(true)}>Reset this company…</Btn>
          ) : (
            <div className="row">
              <Btn kind="danger" onClick={reset}>Yes, delete my work on {profile.short_name}</Btn>
              <Btn onClick={() => setConfirmReset(false)}>Cancel</Btn>
            </div>
          )}
        </div>
      </div>
      <div className="card">
        <h3>Add a company</h3>
        <p className="muted">Creates an empty template. You collect every figure yourself in Stage 2.</p>
        <div className="grid-3">
          <TextInput id="new-name" label="Company name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
          <Select id="new-sector" label="Sector" value={form.sector} options={M.SECTORS.map((s) => ({ value: s, label: M.sectorName(s) }))} onChange={(v) => setForm({ ...form, sector: v })} />
          <Select id="new-ccy" label="Reporting currency" value={form.currency} options={["CHF", "EUR", "USD", "GBP"].map((c) => ({ value: c, label: c }))} onChange={(v) => setForm({ ...form, currency: v })} />
          <TextInput id="new-country" label="Country" value={form.country} onChange={(v) => setForm({ ...form, country: v })} />
          <Toggle id="new-listed" label="Listed on a stock exchange" checked={form.listed} onChange={(v) => setForm({ ...form, listed: v })} />
        </div>
        <Btn kind="primary" onClick={addCompany}>Create company</Btn>
      </div>
    </div>
  );
}
