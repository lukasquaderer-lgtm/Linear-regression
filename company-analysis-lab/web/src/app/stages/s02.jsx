// Stage 2 — Collect Financial Data (Finanzdaten erfassen)
import React, { useMemo, useRef, useState } from "react";
import * as CA from "../../lib/ca.js";
import * as D from "../../lib/data.js";
import * as M from "../../lib/metrics.js";
import * as C from "../../lib/calc.js";
import { Btn, Callout, Cfa, Choice, Metric, Select, StageHeader, Table, Tabs, Task, TextInput } from "../ui.jsx";
import { StageFooter } from "../quiz.jsx";
import { offerDownload, copyText } from "../store.js";

const N = 2;
const XLSX_URL = "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js";

function groupsFor(app, ds) {
  const core = new Set(D.coreMetricKeys(app.profile));
  const req = new Set(D.requiredMetricKeys(app.profile));
  const g = {};
  for (const k of D.applicableMetricKeys(app.profile)) g[k] = core.has(k) ? 1 : req.has(k) ? 2 : 3;
  for (const k of Object.keys(app.custom)) g[k] = 4;
  for (const k of Object.keys(ds.values)) if (!(k in g)) g[k] = 4;
  return g;
}
const GROUP_NAME = { 1: "Core", 2: "Sector – required", 3: "Optional", 4: "Custom" };

export function fullDataset(app) {
  const g = groupsFor(app, app.ds);
  const ds = D.ensureRows(app.ds, Object.keys(g));
  const keys = Object.keys(ds.values).sort((a, b) => (g[a] || 4) - (g[b] || 4) || (M.ORDER.indexOf(a) + 1 || 999) - (M.ORDER.indexOf(b) + 1 || 999) || a.localeCompare(b));
  return { ds, keys, groups: g };
}

export function stage2Criteria(app, ds, issues) {
  const years = ds.years;
  const errors = issues.filter((i) => i.severity === "error").length;
  const latest = years[years.length - 1];
  const core = D.coreMetricKeys(app.profile);
  const nVer = core.filter((k) => app.doc.verified?.[`${k}|${latest}`]).length;
  const curOk = app.profile.currency_confirmed !== false || Boolean(app.doc.settings?.currencyConfirmed);
  return [
    [`At least 5 fiscal years — ${years.length}`, years.length >= 5],
    [`No validation errors (missing or impossible values) — ${errors} open`, errors === 0],
    [`Latest year's core figures verified against the annual report — ${nVer}/${core.length}`, latest !== undefined && nVer === core.length],
    ["Reporting currency confirmed", curOk],
  ];
}

export default function Stage2({ app }) {
  const { profile, currency } = app;
  const { ds, keys, groups } = useMemo(() => fullDataset(app), [app.ds, app.custom, profile]); // eslint-disable-line
  const issues = useMemo(() => D.validate(ds, profile), [ds, profile]);
  const [tab, setTab] = useState("edit");
  const count = (s) => issues.filter((i) => i.severity === s).length;
  const acc = Object.entries(profile.accounting || {});

  return (
    <div className="page">
      <StageHeader stage={CA.STAGES[1]} profile={profile} currency={currency} />
      <div className="grid-2 wide-left">
        <div className="stack">
          <Task>
            Build a clean, verified 5-year dataset. <b>(1)</b> Fill every missing industry-specific figure from the annual reports. <b>(2)</b> Check the latest year's core figures against the annual report and tick them as verified. <b>(3)</b> Clear every validation error. Amounts are in <b>millions</b> of the reporting currency unless the unit says otherwise; enter ratios in percent (14.3, not 0.143).
          </Task>
          <p className="muted small"><b>Data source:</b> {profile.data_source}</p>
          <Cfa k="data_collection" />
        </div>
        <div className="card">
          <h3>Accounting basis by year <span className="de" lang="de">· Rechnungslegung</span></h3>
          {acc.length ? (
            <Table columns={[{ key: "y", label: "Year" }, { key: "b", label: "Basis" }]} rows={acc.map(([y, b]) => ({ y, b, _key: y }))} />
          ) : <p className="muted">Not specified.</p>}
          {acc.slice(1).map(([y, b], i) => (b !== acc[i][1] ? <Callout key={y} tone="warn">Accounting break between {acc[i][0]} and {y}: {acc[i][1]} → {b}. Do not compare levels across it without adjustment.</Callout> : null))}
          {profile.accounting_notes && <p className="muted small">{profile.accounting_notes}</p>}
          <CurrencyBox app={app} />
        </div>
      </div>
      <div className="metrics">
        <Metric label="Fiscal years" value={ds.years.length} />
        <Metric label="Errors" value={count("error")} />
        <Metric label="Warnings" value={count("warning")} />
        <Metric label="Notes" value={count("info")} />
      </div>
      <Tabs value={tab} onChange={setTab} tabs={[{ id: "edit", label: "Data table" }, { id: "check", label: "Validation" }, { id: "verify", label: "Verify vs annual report" }, { id: "import", label: "Import / export" }, { id: "glossary", label: "Glossary EN · DE" }]} />
      <div className="tab-panel">
        {tab === "edit" && <Editor app={app} ds={ds} keys={keys} groups={groups} />}
        {tab === "check" && <Validation app={app} ds={ds} keys={keys} issues={issues} />}
        {tab === "verify" && <Verify app={app} ds={ds} keys={keys.filter((k) => groups[k] <= 2)} groups={groups} />}
        {tab === "import" && <ImportExport app={app} ds={ds} />}
        {tab === "glossary" && <Glossary app={app} />}
      </div>
      <StageFooter app={app} n={N} criteria={stage2Criteria(app, ds, issues)} />
    </div>
  );
}

function CurrencyBox({ app }) {
  const { profile } = app;
  if (profile.currency_confirmed !== false) return <p className="muted small">Reporting currency: <b>{app.currency}</b> (from the annual report).</p>;
  const s = app.doc.settings || {};
  return (
    <div className="stack tight">
      <p><b>Confirm the reporting currency</b> — check the annual report's cover or the statement headers.</p>
      <Select id="s2-currency" label="Reporting currency" value={app.currency} options={["CHF", "EUR", "USD", "GBP"].map((c) => ({ value: c, label: c }))} onChange={(v) => app.update((d) => (d.settings = { ...d.settings, currency: v }))} />
      <label className="check"><input type="checkbox" checked={Boolean(s.currencyConfirmed)} onChange={(e) => app.update((d) => (d.settings = { ...d.settings, currencyConfirmed: e.target.checked }))} /> I checked this in the annual report</label>
    </div>
  );
}

function CellInput({ value, onChange, label }) {
  const [focus, setFocus] = useState(false);
  const [text, setText] = useState(value === null || value === undefined ? "" : String(value));
  const decimals = value === null || value === undefined ? 0 : Math.min(3, (String(value).split(".")[1] || "").length);
  const shown = focus ? text : value === null || value === undefined ? "" : C.fmtNum(value, decimals);
  return (
    <input
      className={`cell ${value === null || value === undefined ? "empty" : ""}`}
      aria-label={label}
      inputMode="decimal"
      placeholder="–"
      value={shown}
      onFocus={() => { setText(value === null || value === undefined ? "" : String(value)); setFocus(true); }}
      onBlur={() => setFocus(false)}
      onChange={(e) => { setText(e.target.value); onChange(D.parseNumber(e.target.value)); }}
    />
  );
}

function Editor({ app, ds, keys, groups }) {
  const [draft, setDraft] = useState(() => D.cloneDataset(ds));
  const [dirty, setDirty] = useState(false);
  const [msg, setMsg] = useState(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [custom, setCustom] = useState({ en: "", de: "", unit: "money", better: "better" });
  const req = new Set(D.requiredMetricKeys(app.profile));
  const years = draft.years;

  const setCell = (k, y, v) => {
    setDraft((d) => ({ ...d, values: { ...d.values, [k]: { ...d.values[k], [String(y)]: v } } }));
    setDirty(true);
  };
  const setMeta = (k, field, v) => {
    setDraft((d) => ({ ...d, meta: { ...d.meta, [k]: { ...(d.meta[k] || {}), [field]: v } } }));
    setDirty(true);
  };
  const save = () => {
    let changed = 0;
    const next = D.cloneDataset(draft);
    const unverify = [];
    for (const k of Object.keys(next.values)) {
      for (const y of next.years) {
        const a = D.value(ds, k, y), b = D.value(next, k, y);
        if (a !== b && !(a !== null && b !== null && Math.abs(a - b) < 1e-9)) {
          changed++;
          unverify.push(`${k}|${y}`);
          const src = next.meta[k]?.source || "";
          if (b !== null && (!src || src.startsWith("To collect"))) next.meta[k] = { ...(next.meta[k] || {}), source: "Entered by you from the annual report" };
        }
      }
    }
    app.update((d) => {
      d.dataset = next;
      for (const key of unverify) delete d.verified[key];
    });
    setDirty(false);
    setMsg(`Saved — ${changed} value(s) changed.`);
  };
  const applyYears = (next) => {
    app.saveDataset(next);
    setDraft(D.cloneDataset(next));
    setDirty(false);
  };
  const addYear = (y) => {
    const next = D.cloneDataset(draft);
    next.years = [...new Set([...next.years, y])].sort((a, b) => a - b);
    for (const k of Object.keys(next.values)) next.values[k][String(y)] ??= null;
    applyYears(next);
  };
  const removeYear = (y) => {
    const next = D.cloneDataset(draft);
    next.years = next.years.filter((x) => x !== y);
    for (const k of Object.keys(next.values)) delete next.values[k][String(y)];
    applyYears(next);
  };
  const addCustom = () => {
    if (!custom.en.trim()) return setMsg("Enter an English name for the new metric.");
    const key = "custom_" + D.slugify(custom.en);
    app.update((d) => {
      d.customMetrics = { ...d.customMetrics, [key]: { en: custom.en.trim(), de: custom.de.trim(), unit: custom.unit, higher_is_better: { better: true, worse: false, neutral: null }[custom.better] } };
      const base = d.dataset || D.cloneDataset(ds);
      d.dataset = D.ensureRows(base, [key]);
      d.dataset.meta[key] = { source: "Entered by you", note: "" };
    });
    setDraft((dr) => D.ensureRows(dr, [key]));
    setCustom({ en: "", de: "", unit: "money", better: "better" });
    setMsg(`Added ${custom.en.trim()}.`);
  };
  const reset = () => {
    app.update((d) => {
      d.dataset = null;
      d.verified = {};
    });
    setConfirmReset(false);
    setDirty(false);
    setMsg("Dataset reset to the starter data.");
    setTimeout(() => setDraft(D.cloneDataset(fullDataset(app).ds)), 0);
  };

  return (
    <div className="stack">
      <p className="muted small">★ = required. Edit cells directly, then <b>Save dataset</b>. Values you change lose their 'verified' tick. Units are shown per row.</p>
      <div className="table-wrap tall">
        <table className="table data-grid">
          <thead>
            <tr>
              <th>Metric · Kennzahl</th>
              <th>Unit</th>
              {years.map((y) => <th key={y} className="num">{y}</th>)}
              <th>Source</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {keys.filter((k) => draft.values[k]).map((k, i, arr) => (
              <React.Fragment key={k}>
                {(i === 0 || groups[arr[i - 1]] !== groups[k]) && (
                  <tr className="group-row"><td colSpan={years.length + 4}>{GROUP_NAME[groups[k]] || "Other"}</td></tr>
                )}
                <tr>
                  <th scope="row" className="metric-cell">
                    {req.has(k) && <span className="req" title="Required">★</span>} {M.short(k, app.custom)}
                    <span className="de" lang="de"> · {M.german(k, app.custom)}</span>
                  </th>
                  <td className="unit">{M.unitLabel(k, app.currency, app.custom)}</td>
                  {years.map((y) => (
                    <td key={y} className="num"><CellInput label={`${M.short(k, app.custom)} ${y}`} value={draft.values[k]?.[String(y)] ?? null} onChange={(v) => setCell(k, y, v)} /></td>
                  ))}
                  <td><input className="cell text" aria-label={`Source for ${M.short(k)}`} value={draft.meta[k]?.source || ""} onChange={(e) => setMeta(k, "source", e.target.value)} /></td>
                  <td><input className="cell text" aria-label={`Note for ${M.short(k)}`} value={draft.meta[k]?.note || ""} onChange={(e) => setMeta(k, "note", e.target.value)} /></td>
                </tr>
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
      {msg && <Callout tone="success">{msg}</Callout>}
      <div className="row">
        <Btn kind="primary" id="s2-save" disabled={!dirty} onClick={save}>Save dataset</Btn>
        <Btn onClick={() => addYear((years[years.length - 1] || 2025) + 1)}>Add fiscal year {(years[years.length - 1] || 2025) + 1}</Btn>
        <Btn onClick={() => addYear((years[0] || 2021) - 1)}>Add earlier year {(years[0] || 2021) - 1}</Btn>
        {years.length > 1 && <Btn onClick={() => removeYear(years[0])}>Remove {years[0]}</Btn>}
        {!confirmReset ? <Btn onClick={() => setConfirmReset(true)}>Reset to starter data…</Btn> : (
          <>
            <Btn kind="danger" onClick={reset}>Yes, discard my edits</Btn>
            <Btn onClick={() => setConfirmReset(false)}>Cancel</Btn>
          </>
        )}
      </div>
      {dirty && <Callout tone="warn">You have unsaved changes in the table.</Callout>}
      <details className="details">
        <summary>Add an industry-specific or custom metric</summary>
        <div className="details-body grid-3">
          <TextInput id="custom-en" label="English name (CFA terminology)" value={custom.en} onChange={(v) => setCustom({ ...custom, en: v })} placeholder="e.g. Liquidity coverage ratio" />
          <TextInput id="custom-de" label="German name" value={custom.de} onChange={(v) => setCustom({ ...custom, de: v })} placeholder="e.g. Liquiditätsdeckungsquote" />
          <Select id="custom-unit" label="Unit" value={custom.unit} onChange={(v) => setCustom({ ...custom, unit: v })} options={[{ value: "money", label: `${app.currency} m` }, { value: "bn", label: `${app.currency} bn` }, { value: "pct", label: "%" }, { value: "per_share", label: "per share" }, { value: "shares", label: "m shares" }]} />
          <Select id="custom-better" label="Higher is…" value={custom.better} onChange={(v) => setCustom({ ...custom, better: v })} options={[{ value: "better", label: "better" }, { value: "worse", label: "worse" }, { value: "neutral", label: "neutral" }]} />
          <div><Btn onClick={addCustom}>Add metric</Btn></div>
        </div>
      </details>
    </div>
  );
}

function Validation({ app, ds, keys, issues }) {
  const [show, setShow] = useState(["error", "warning", "info"]);
  const req = new Set(D.requiredMetricKeys(app.profile));
  const cell = {};
  for (const i of issues) if (i.year !== null) {
    const k = `${i.metric}|${i.year}`;
    if (!cell[k] || D.SEVERITY_ORDER[i.severity] < D.SEVERITY_ORDER[cell[k]]) cell[k] = i.severity;
  }
  const rows = issues.filter((i) => show.includes(i.severity));
  return (
    <div className="stack">
      <p><b>Flagged dataset</b> — <span className="sev sev-error">red</span> missing required or impossible value · <span className="sev sev-warning">amber</span> implausible or inconsistent · <span className="sev sev-info">blue</span> worth a look</p>
      <div className="table-wrap tall">
        <table className="table">
          <thead><tr><th>Metric</th>{ds.years.map((y) => <th key={y} className="num">{y}</th>)}</tr></thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k}>
                <th scope="row" className="metric-cell">{M.short(k, app.custom)}</th>
                {ds.years.map((y) => {
                  const v = D.value(ds, k, y);
                  const sev = cell[`${k}|${y}`] || (v === null && req.has(k) ? "error" : null);
                  return <td key={y} className={`num ${sev ? "sev-cell sev-" + sev : ""}`}>{v === null ? <span className={req.has(k) ? "missing" : "muted"}>missing</span> : C.fmtNum(v, Math.abs(v) < 100 ? 2 : 0)}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="row">
        <b>Issues</b>
        {["error", "warning", "info"].map((s) => (
          <label key={s} className={show.includes(s) ? "pill on" : "pill"}>
            <input type="checkbox" checked={show.includes(s)} onChange={() => setShow(show.includes(s) ? show.filter((x) => x !== s) : [...show, s])} />
            <span>{s[0].toUpperCase() + s.slice(1)}</span>
          </label>
        ))}
      </div>
      {issues.length === 0 ? <Callout tone="success">No issues found.</Callout> : (
        <Table columns={[{ key: "sev", label: "Severity", render: (r) => <span className={`sev sev-${r.severity}`}>{r.severity}</span> }, { key: "m", label: "Metric" }, { key: "y", label: "Year" }, { key: "message", label: "Issue" }]} rows={rows.map((i, n) => ({ ...i, m: i.metric === "—" ? "Dataset" : M.short(i.metric, app.custom), y: i.year || "", _key: n }))} />
      )}
      <details className="details">
        <summary>What do the checks test?</summary>
        <div className="details-body">
          <ul>
            <li><b>Completeness</b> — core metrics for every year; sector metrics at least for the latest three years.</li>
            <li><b>Impossible values</b> — negative assets or dividends, ratios outside 0–100 %, etc.</li>
            <li><b>Plausibility</b> — e.g. a CET1 ratio of 60 % or a solvency ratio below 100 %.</li>
            <li><b>Accounting identities</b> — assets = liabilities + equity (+ minorities); EPS × shares ≈ net income; CET1 capital ÷ RWA ≈ CET1 ratio.</li>
            <li><b>Unit errors</b> — decimals entered as percent, millions entered as billions, jumps by a factor of five or more.</li>
          </ul>
        </div>
      </details>
    </div>
  );
}

function Verify({ app, ds, keys }) {
  const [ver, setVer] = useState(() => ({ ...(app.doc.verified || {}) }));
  const [refs, setRefs] = useState(() => ({ ...(app.doc.verifiedRef || {}) }));
  const [saved, setSaved] = useState(false);
  const toggle = (k, y) => {
    const key = `${k}|${y}`;
    setVer((v) => ({ ...v, [key]: !v[key] }));
    setSaved(false);
  };
  const save = () => {
    app.update((d) => {
      d.verified = Object.fromEntries(Object.entries(ver).filter(([key, on]) => {
        const [k, y] = key.split("|");
        return on && D.value(ds, k, +y) !== null;
      }));
      d.verifiedRef = refs;
    });
    setSaved(true);
  };
  return (
    <div className="stack">
      <p className="muted">Open the annual report, find each figure and tick it when it matches your dataset. Note the page or note number — you will need it again in Stage 5. Required: every <b>core</b> figure for the latest year.</p>
      <div className="table-wrap tall">
        <table className="table">
          <thead><tr><th>Metric</th>{ds.years.map((y) => <th key={y} className="num">{y}</th>)}<th>Annual report reference</th></tr></thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k}>
                <th scope="row" className="metric-cell">{M.short(k, app.custom)}</th>
                {ds.years.map((y) => {
                  const empty = D.value(ds, k, y) === null;
                  return (
                    <td key={y} className="num">
                      <input type="checkbox" aria-label={`Verified ${M.short(k)} ${y}`} disabled={empty} checked={!empty && Boolean(ver[`${k}|${y}`])} onChange={() => toggle(k, y)} />
                    </td>
                  );
                })}
                <td><input className="cell text" aria-label={`Reference for ${M.short(k)}`} placeholder="e.g. AR 2025 p. 187, note 12" value={refs[k] || ""} onChange={(e) => { setRefs({ ...refs, [k]: e.target.value }); setSaved(false); }} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="row">
        <Btn kind="primary" id="s2-verify-save" onClick={save}>Save verification</Btn>
        {saved && <span className="ok-text">Saved.</span>}
      </div>
    </div>
  );
}

function loadXLSX() {
  if (window.XLSX) return Promise.resolve(window.XLSX);
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = XLSX_URL;
    s.onload = () => resolve(window.XLSX);
    s.onerror = () => reject(new Error("The Excel reader could not load. Save the sheet as CSV and import that instead."));
    document.head.appendChild(s);
  });
}

function ImportExport({ app, ds }) {
  const [imp, setImp] = useState(null);
  const [err, setErr] = useState(null);
  const [mode, setMode] = useState("Overwrite existing values");
  const [msg, setMsg] = useState(null);
  const fileRef = useRef(null);

  const onFile = async (file) => {
    setErr(null);
    setImp(null);
    try {
      let res;
      if (/\.(xlsx|xlsm|xls)$/i.test(file.name)) {
        const XLSX = await loadXLSX();
        const wb = XLSX.read(await file.arrayBuffer(), { type: "array" });
        const rows = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, raw: true, defval: null });
        res = D.importRows(rows, false);
      } else {
        res = D.importText(await file.text(), file.name);
      }
      setImp({ ...res, name: file.name });
    } catch (e) {
      setErr(e.message || "Could not read the file.");
    }
  };
  const apply = () => {
    const merged = D.mergeImport(ds, imp, mode.startsWith("Overwrite"));
    for (const k of Object.keys(imp.rows)) merged.meta[k] = { ...(merged.meta[k] || {}), source: `Imported from ${imp.name}` };
    app.update((d) => {
      d.dataset = merged;
      for (const label of imp.unmapped) {
        const key = D.slugify(label);
        d.customMetrics = { ...d.customMetrics, [key]: d.customMetrics?.[key] || { en: label, de: "", unit: "money", higher_is_better: true } };
      }
    });
    setMsg(`Imported ${Object.keys(imp.rows).length} rows from ${imp.name}.`);
    setImp(null);
  };
  const exportCSV = async () => {
    const csv = D.toCSV(ds, app.currency, app.custom);
    const r = await offerDownload(`${app.profile.id}_financials.csv`, csv);
    if (r === "unavailable") setMsg((await copyText(csv)) ? "Downloads are not available here — the CSV was copied to your clipboard." : "Downloads and the clipboard are not available in this view.");
    else if (r === "saved") setMsg("CSV saved.");
  };

  return (
    <div className="stack">
      <div className="card">
        <h3>Import from CSV or Excel</h3>
        <p className="muted small">Accepted layouts: (a) wide — first column metric names, then one column per year; (b) years as rows — first column 'year', then one column per metric; (c) long — columns 'metric', 'year', 'value'. English or German labels are recognised (e.g. 'Net income', 'Konzerngewinn', 'CET1 ratio'); Swiss and German number formats (1'234.5, 1.234,5, (12)) are parsed.</p>
        <div className="row">
          <Btn icon="down" onClick={() => fileRef.current?.click()}>Choose a file…</Btn>
          <input ref={fileRef} id="s2-file" type="file" hidden accept=".csv,.tsv,.txt,.xlsx,.xls,.xlsm" onChange={(e) => e.target.files[0] && onFile(e.target.files[0])} />
        </div>
        {err && <Callout tone="error">{err}</Callout>}
        {imp && (
          <div className="stack">
            <Callout tone="success">Read {Object.keys(imp.rows).length} rows × {imp.years.length} years from {imp.name} ({imp.orientation} layout).</Callout>
            {Object.keys(imp.mapped).length > 0 && <p className="small">Recognised: {Object.entries(imp.mapped).map(([l, k]) => `${l} → ${M.short(k)}`).join(" · ")}</p>}
            {imp.unmapped.length > 0 && <Callout tone="warn">Not recognised — added as custom metrics: {imp.unmapped.join(", ")}</Callout>}
            <Table columns={[{ key: "k", label: "Metric" }, ...imp.years.map((y) => ({ key: String(y), label: String(y), num: true }))]} rows={Object.entries(imp.rows).map(([k, r]) => ({ k: M.short(k), ...Object.fromEntries(imp.years.map((y) => [String(y), r[String(y)] === null || r[String(y)] === undefined ? "–" : C.fmtNum(r[String(y)], 2)])), _key: k }))} />
            <Choice label="How to combine" options={["Overwrite existing values", "Only fill empty cells"]} value={mode} onChange={setMode} />
            <Btn kind="primary" onClick={apply}>Apply import</Btn>
          </div>
        )}
        {msg && <Callout tone="success">{msg}</Callout>}
      </div>
      <div className="card">
        <h3>Export</h3>
        <p className="muted small">The current dataset with English and German labels, units, sources and notes.</p>
        <Btn icon="down" onClick={exportCSV}>Download dataset as CSV</Btn>
      </div>
    </div>
  );
}

function Glossary({ app }) {
  const rows = D.applicableMetricKeys(app.profile).map((k) => {
    const m = M.CATALOG[k];
    return { en: m.en, de: m.de, unit: M.unitLabel(k, app.currency), where: m.statement, what: m.description, _key: k };
  });
  return <Table columns={[{ key: "en", label: "English (CFA)" }, { key: "de", label: "Deutsch" }, { key: "unit", label: "Unit" }, { key: "where", label: "Where to find it" }, { key: "what", label: "What it tells you" }]} rows={rows} />;
}
