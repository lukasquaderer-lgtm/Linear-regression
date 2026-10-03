// Shared UI components.
import React, { useEffect, useId, useRef, useState } from "react";
import { CFA } from "../generated/data.js";
import { parseNumber } from "../lib/data.js";
import * as M from "../lib/metrics.js";

export function Icon({ name, size = 16 }) {
  const p = {
    check: "M4 10.5l4 4 8-9",
    lock: "M6 9V6.5a4 4 0 0 1 8 0V9 M5 9h10v8H5z",
    arrow: "M4 10h12 M11 5l5 5-5 5",
    down: "M10 3v10 M5 9l5 5 5-5 M4 17h12",
    copy: "M7 7h9v10H7z M4 4h9v2 M4 4v10h2",
    dot: "M10 10m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0",
    half: "M10 4a6 6 0 0 1 0 12z M10 4a6 6 0 0 0 0 12",
    ring: "M10 4a6 6 0 1 1 0 12a6 6 0 1 1 0-12",
    book: "M4 4h5a2 2 0 0 1 2 2v11a2 2 0 0 0-2-2H4z M16 4h-5a2 2 0 0 0-2 2v11a2 2 0 0 1 2-2h5z",
    spark: "M10 3v4 M10 13v4 M3 10h4 M13 10h4",
  }[name];
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="icon">
      <path d={p} />
    </svg>
  );
}

export function Btn({ kind = "secondary", children, icon, ...rest }) {
  return (
    <button type="button" className={`btn btn-${kind}`} {...rest}>
      {icon && <Icon name={icon} />}
      <span>{children}</span>
    </button>
  );
}

export function StageHeader({ stage, profile, currency }) {
  const chips = [profile.subsector || profile.sector, `Reporting currency: ${currency}`, profile.listed ? `Listed: ${profile.exchange_ticker || "yes"}` : "Not listed"];
  return (
    <header className="stage-head">
      <div className="kicker">
        Stage {stage.n} of 10 · <span lang="de">{stage.de}</span>
      </div>
      <h1>
        {stage.en} <span className="head-co">— {profile.name}</span>
      </h1>
      <p className="head-goal">{stage.goal}</p>
      <div className="chips">
        {chips.map((c) => (
          <span key={c} className="chip">{c}</span>
        ))}
      </div>
    </header>
  );
}

export function PageHeader({ kicker, title, sub, chips = [] }) {
  return (
    <header className="stage-head">
      <div className="kicker">{kicker}</div>
      <h1>{title}</h1>
      {sub && <p className="head-goal">{sub}</p>}
      <div className="chips">
        {chips.map((c) => (
          <span key={c} className="chip">{c}</span>
        ))}
      </div>
    </header>
  );
}

export function Task({ children, kicker = "Your task" }) {
  return (
    <div className="task">
      <div className="eyebrow">{kicker}</div>
      <div className="task-body">{children}</div>
    </div>
  );
}

export function Cfa({ k }) {
  const n = CFA[k];
  if (!n) return null;
  return (
    <aside className="cfa">
      <div className="eyebrow accent">CFA Connection · {n[0]}</div>
      <p>{n[1]}</p>
    </aside>
  );
}

export function Callout({ tone = "info", title, children }) {
  return (
    <div className={`callout callout-${tone}`} role={tone === "error" ? "alert" : undefined}>
      {title && <strong className="callout-title">{title}</strong>}
      <div>{children}</div>
    </div>
  );
}

export function Checklist({ items }) {
  return (
    <ul className="checklist">
      {items.map(([label, ok]) => (
        <li key={label} className={ok ? "ok" : ""}>
          <span className="mark">{ok ? <Icon name="check" size={14} /> : <Icon name="ring" size={14} />}</span>
          {label}
        </li>
      ))}
    </ul>
  );
}

export function Bilingual({ k, custom }) {
  return (
    <>
      <span>{M.short(k, custom)}</span> <span className="de" lang="de">· {M.german(k, custom)}</span>
    </>
  );
}

export function Section({ title, de, children, aside }) {
  return (
    <section className="section">
      <div className="section-head">
        <h2>
          {title} {de && <span className="de" lang="de">· {de}</span>}
        </h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

export function Card({ children, className = "" }) {
  return <div className={`card ${className}`}>{children}</div>;
}

export function Details({ summary, children, open = false, status }) {
  return (
    <details className="details" open={open}>
      <summary>
        {status !== undefined && <span className={`status-dot ${status}`}>{status === "done" ? <Icon name="check" size={13} /> : status === "half" ? <Icon name="half" size={13} /> : <Icon name="ring" size={13} />}</span>}
        <span>{summary}</span>
      </summary>
      <div className="details-body">{children}</div>
    </details>
  );
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button key={t.id} role="tab" type="button" aria-selected={value === t.id} className={value === t.id ? "tab active" : "tab"} onClick={() => onChange(t.id)}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function Metric({ label, value, help }) {
  return (
    <div className="metric" title={help || undefined}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </div>
  );
}

export function Table({ columns, rows, className = "" }) {
  return (
    <div className="table-wrap">
      <table className={`table ${className}`}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.num ? "num" : ""}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r._key ?? i}>
              {columns.map((c) => (
                <td key={c.key} className={c.num ? "num" : ""}>{c.render ? c.render(r) : r[c.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ------------------------------------------------------------------ form fields

export function TextArea({ label, value, onChange, rows = 4, placeholder, hint, id, help }) {
  const auto = useId();
  const fid = id || auto;
  return (
    <div className="field">
      {label && <label htmlFor={fid}>{label}</label>}
      {help && <div className="field-help">{help}</div>}
      <textarea id={fid} rows={rows} value={value ?? ""} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
      {hint && <div className="field-hint">{hint}</div>}
    </div>
  );
}

export function TextInput({ label, value, onChange, placeholder, id }) {
  const auto = useId();
  const fid = id || auto;
  return (
    <div className="field">
      {label && <label htmlFor={fid}>{label}</label>}
      <input id={fid} type="text" value={value ?? ""} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

const showNum = (v) => (v === null || v === undefined || !Number.isFinite(v) ? "" : String(+v.toFixed(10)));

/** Number input that accepts 1'234.5, 1,234.5 and (12); reports number|null. */
export function NumberField({ label, value, onChange, disabled, id, suffix, compact }) {
  const auto = useId();
  const fid = id || auto;
  const [text, setText] = useState(showNum(value));
  const last = useRef(value);
  useEffect(() => {
    if (value !== last.current) {
      setText(showNum(value));
      last.current = value;
    }
  }, [value]);
  const commit = (t) => {
    const v = parseNumber(t);
    last.current = v;
    onChange(v);
  };
  return (
    <div className={`field ${compact ? "compact" : ""}`}>
      {label && <label htmlFor={fid}>{label}</label>}
      <div className="num-wrap">
        <input id={fid} type="text" inputMode="decimal" className="num-input" value={text} disabled={disabled} onChange={(e) => { setText(e.target.value); commit(e.target.value); }} />
        {suffix && <span className="suffix">{suffix}</span>}
      </div>
    </div>
  );
}

export function Choice({ label, options, value, onChange, name, disabled, vertical }) {
  const auto = useId();
  return (
    <fieldset className="choice" disabled={disabled}>
      {label && <legend>{label}</legend>}
      <div className={vertical ? "choice-opts vertical" : "choice-opts"}>
        {options.map((o) => {
          const v = typeof o === "string" ? o : o.value;
          const l = typeof o === "string" ? o : o.label;
          return (
            <label key={v} className={value === v ? "pill on" : "pill"}>
              <input type="radio" name={name || auto} checked={value === v} onChange={() => onChange(v)} />
              <span>{l}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export function MultiChoice({ label, options, value = [], onChange, max }) {
  return (
    <fieldset className="choice">
      {label && <legend>{label}</legend>}
      <div className="choice-opts">
        {options.map((o) => {
          const v = typeof o === "string" ? o : o.value;
          const l = typeof o === "string" ? o : o.label;
          const on = value.includes(v);
          const full = max && value.length >= max && !on;
          return (
            <label key={v} className={on ? "pill on" : full ? "pill dim" : "pill"}>
              <input type="checkbox" checked={on} disabled={full} onChange={() => onChange(on ? value.filter((x) => x !== v) : [...value, v])} />
              <span>{l}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export function Select({ label, value, options, onChange, id }) {
  const auto = useId();
  const fid = id || auto;
  return (
    <div className="field">
      {label && <label htmlFor={fid}>{label}</label>}
      <select id={fid} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

export function Slider({ label, value, min, max, step, onChange, format = (v) => v, help }) {
  const id = useId();
  return (
    <div className="field slider">
      <div className="slider-head">
        <label htmlFor={id}>{label}</label>
        <output htmlFor={id}>{format(value)}</output>
      </div>
      <input id={id} type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(parseFloat(e.target.value))} />
      {help && <div className="field-hint">{help}</div>}
    </div>
  );
}

export function Toggle({ label, checked, onChange, id }) {
  const auto = useId();
  const fid = id || auto;
  return (
    <label className="toggle" htmlFor={fid}>
      <input id={fid} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="track"><span className="thumb" /></span>
      <span>{label}</span>
    </label>
  );
}

/** ROE = (a)/(b) × 100 rendered as a fraction. */
export function Formula({ lhs, num, den, times }) {
  return (
    <div className="formula" role="math" aria-label={`${lhs} = ${num} divided by ${den}${times ? " times " + times : ""}`}>
      <span className="f-lhs">{lhs}</span>
      <span className="f-eq">=</span>
      <span className="frac">
        <span className="f-num">{num}</span>
        <span className="f-den">{den}</span>
      </span>
      {times && <span className="f-times">× {times}</span>}
    </div>
  );
}

export function Coverage({ covered, missed, labelCovered = "You covered", labelMissed = "Consider adding" }) {
  return (
    <div className="coverage">
      {covered.length > 0 && (
        <p>
          <strong>{labelCovered}:</strong>{" "}
          {covered.map((c) => (
            <span key={c} className="tag tag-ok">✓ {c}</span>
          ))}
        </p>
      )}
      {missed.length > 0 && (
        <p>
          <strong>{labelMissed}:</strong>{" "}
          {missed.map((c) => (
            <span key={c} className="tag">○ {c}</span>
          ))}
        </p>
      )}
    </div>
  );
}

/** Text that commits to the parent after a short pause (keeps typing smooth). */
export function useDraft(value, commit, delay = 400) {
  const [draft, setDraft] = useState(value ?? "");
  const timer = useRef(null);
  const committed = useRef(value ?? "");
  useEffect(() => {
    // only external changes (another stage, a reset) overwrite what the learner is typing
    if ((value ?? "") !== committed.current) {
      committed.current = value ?? "";
      setDraft(value ?? "");
    }
  }, [value]);
  const update = (v) => {
    setDraft(v);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      committed.current = v;
      commit(v);
    }, delay);
  };
  useEffect(() => () => clearTimeout(timer.current), []);
  return [draft, update];
}

export function DraftArea({ value, onCommit, ...rest }) {
  const [draft, setDraft] = useDraft(value, onCommit);
  return <TextArea value={draft} onChange={setDraft} {...rest} />;
}
