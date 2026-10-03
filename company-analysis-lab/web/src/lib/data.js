// Company datasets: shape, metric sets, validation and CSV/Excel import.
// Port of lab/data.py. A dataset is {years:[2021..], values:{key:{"2021":num|null}}, meta:{key:{source,note}}}.
import { COMPANIES } from "../generated/data.js";
import * as M from "./metrics.js";

export const BUILTIN = COMPANIES.map((c) => c.profile.id);

export function builtinCompany(id) {
  return COMPANIES.find((c) => c.profile.id === id) || null;
}

export function withDefaults(profile) {
  return {
    required_extra: [],
    not_applicable: [],
    events: [],
    business_reference: {},
    top_risks_reference: [],
    audit_focus: [],
    quiz: [],
    accounting: {},
    peers_suggested: [],
    short_name: profile.name,
    ...profile,
  };
}

export function slugify(name) {
  const s = String(name).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  return s || "company";
}

// ------------------------------------------------------------------ metric sets

export function applicableMetricKeys(profile) {
  const ex = new Set(profile.not_applicable || []);
  return M.metricsForSector(profile.sector).map((m) => m.key).filter((k) => !ex.has(k));
}

export function requiredMetricKeys(profile) {
  const ex = new Set(profile.not_applicable || []);
  const keys = M.requiredMetrics(profile.sector).map((m) => m.key);
  for (const k of profile.required_extra || []) if (!keys.includes(k)) keys.push(k);
  return keys.filter((k) => !ex.has(k));
}

export function coreMetricKeys(profile) {
  const ex = new Set(profile.not_applicable || []);
  return Object.values(M.CATALOG).filter((m) => m.core && !ex.has(m.key)).map((m) => m.key);
}

// ------------------------------------------------------------------ dataset helpers

export function cloneDataset(ds) {
  return JSON.parse(JSON.stringify(ds));
}

export function emptyDataset(keys, years) {
  const values = {};
  const meta = {};
  for (const k of keys) {
    values[k] = Object.fromEntries(years.map((y) => [String(y), null]));
    meta[k] = { source: "To collect from the annual report", note: "" };
  }
  return { years: [...years], values, meta };
}

export function starterDataset(id) {
  const c = builtinCompany(id);
  return c ? { years: [...c.years], values: cloneDataset(c.values), meta: cloneDataset(c.meta) } : null;
}

export function ensureRows(ds, keys) {
  const out = cloneDataset(ds);
  for (const k of keys) {
    if (!out.values[k]) {
      out.values[k] = Object.fromEntries(out.years.map((y) => [String(y), null]));
      out.meta[k] = { source: "To collect from the annual report", note: "" };
    }
  }
  return out;
}

export const isNum = (x) => typeof x === "number" && Number.isFinite(x);

export function value(ds, key, year) {
  const v = ds?.values?.[key]?.[String(year)];
  return isNum(v) ? v : null;
}

/** Array of [year, value] pairs (values may be null). */
export function series(ds, key) {
  return ds.years.map((y) => [y, value(ds, key, y)]);
}

export function clean(pairs) {
  return pairs.filter(([, v]) => v !== null);
}

export function orderKeys(keys) {
  const idx = (k) => (M.ORDER.includes(k) ? M.ORDER.indexOf(k) : 10000);
  return [...keys].sort((a, b) => idx(a) - idx(b) || a.localeCompare(b));
}

// ------------------------------------------------------------------ validation

export const SEVERITY_ORDER = { error: 0, warning: 1, info: 2 };
const n2 = (x) => x.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const n0 = (x) => x.toLocaleString("en-US", { maximumFractionDigits: 0 });
const fmtYears = (ys) => ys.join(", ");

export function validate(ds, profile) {
  const issues = [];
  const add = (severity, metric, year, message) => issues.push({ severity, metric, year, message });
  const years = [...ds.years].sort((a, b) => a - b);
  if (years.length < 5) add("error", "—", null, `Only ${years.length} fiscal years — the analysis needs at least 5.`);
  if (years.length && years.some((y, i) => y !== years[0] + i)) add("warning", "—", null, "Years are not consecutive — growth rates between gaps are misleading.");

  const required = new Set(requiredMetricKeys(profile));
  const core = new Set(coreMetricKeys(profile));
  const latest3 = years.slice(-3);
  const keys = orderKeys([...new Set([...required, ...Object.keys(ds.values)])]);

  for (const key of keys) {
    const missing = years.filter((y) => value(ds, key, y) === null);
    if (!missing.length) continue;
    if (core.has(key)) add("error", key, null, `Missing for ${fmtYears(missing)} (required for every year).`);
    else if (required.has(key)) {
      const recent = missing.filter((y) => latest3.includes(y));
      if (recent.length) add("error", key, null, `Missing for ${fmtYears(recent)} (needed at least for the latest three years).`);
      const older = missing.filter((y) => !latest3.includes(y));
      if (older.length) add("warning", key, null, `Missing for ${fmtYears(older)} — fill in for a full 5-year trend.`);
    } else if (missing.length < years.length) add("info", key, null, `Partly filled (missing ${fmtYears(missing)}).`);
  }

  for (const key of Object.keys(ds.values)) {
    const m = M.get(key);
    if (!m) continue;
    for (const y of years) {
      const x = value(ds, key, y);
      if (x === null) continue;
      const [lo, hi] = m.hard;
      if ((lo !== null && x < lo) || (hi !== null && x > hi)) {
        add("error", key, y, `${n2(x)} is impossible for ${m.en} (allowed range ${lo ?? "−∞"} to ${hi ?? "∞"}).`);
        continue;
      }
      if (m.unit === "pct" && Math.abs(x) > 0 && Math.abs(x) < 1 && (m.plausible[0] || 0) >= 1) {
        add("warning", key, y, `${x} looks like a decimal — enter percentages as 14.3, not 0.143.`);
        continue;
      }
      const [plo, phi] = m.plausible;
      if ((plo !== null && x < plo) || (phi !== null && x > phi)) {
        add("warning", key, y, `${n2(x)} is outside the usual range for ${m.en} (${plo ?? "…"} to ${phi ?? "…"}) — double-check.`);
      }
      if (m.unit === "bn" && Math.abs(x) > 20000) add("warning", key, y, `${n0(x)} bn is very large — this metric is in billions. Did you enter millions?`);
    }
  }

  for (const y of years) {
    const v = (k) => value(ds, k, y);
    const a = v("total_assets"), l = v("total_liabilities"), e = v("total_equity");
    const ni = v("net_income"), eps = v("eps"), sh = v("shares_outstanding"), rev = v("revenue");
    if (a !== null && l !== null && e !== null && a > 0) {
      const gap = a - l - e;
      const rel = e ? Math.abs(gap) / Math.abs(e) : Infinity;
      if (rel > 0.15 && Math.abs(gap) > 0.001 * a) add("error", "total_assets", y, `Assets (${n0(a)}) ≠ liabilities + equity (${n0(l + e)}); gap ${n0(gap)}. Check units or a typo.`);
      else if (rel > 0.02) add("info", "total_equity", y, `Assets − liabilities − equity = ${n0(gap)} — usually non-controlling interests (minority interests). Fine if so.`);
    }
    if (l !== null && a !== null && l > a) add("warning", "total_liabilities", y, "Liabilities exceed assets (negative equity) — verify.");
    if (ni !== null && eps !== null && ni !== 0 && eps !== 0 && Math.sign(ni) !== Math.sign(eps)) add("warning", "eps", y, "EPS and net income have opposite signs.");
    if (ni !== null && eps !== null && sh && ni) {
      const implied = eps * sh;
      if (Math.abs(implied - ni) / Math.abs(ni) > 0.1) add("warning", "eps", y, `EPS × shares = ${n0(implied)} but net income = ${n0(ni)} (>10 % apart). Check the share count unit (millions) or the EPS basis.`);
    }
    const dps = v("dps");
    if (dps !== null && eps !== null && eps > 0 && dps > eps) add("info", "dps", y, `Dividend (${dps}) exceeds EPS (${eps}) — payout above 100 %. Sustainable?`);
    if (ni !== null && rev !== null && rev > 0 && ni > rev) add("info", "net_income", y, "Net income exceeds revenue — usually a gain outside revenue (e.g. negative goodwill or a disposal gain). Investigate in Stage 5.");
    const c1 = v("cet1_capital"), rwa = v("rwa"), ratio = v("cet1_ratio");
    if (c1 !== null && rwa && ratio !== null) {
      const calc = (c1 / rwa) * 100;
      if (Math.abs(calc - ratio) > 0.3) add("warning", "cet1_ratio", y, `CET1 capital ÷ RWA = ${calc.toFixed(1)} % but the CET1 ratio entered is ${ratio.toFixed(1)} %.`);
    }
    if (rwa !== null && a !== null && rwa > a) add("warning", "rwa", y, "RWA exceed total assets — unusual (RWA density > 100 %).");
    const opex = v("operating_expenses"), ci = v("cost_income_ratio");
    if (opex !== null && rev && ci !== null) {
      const calc = (opex / rev) * 100;
      if (Math.abs(calc - ci) > 3) add("info", "cost_income_ratio", y, `Operating expenses ÷ revenue = ${calc.toFixed(1)} % vs reported ${ci.toFixed(1)} % — the company may use an adjusted definition.`);
    }
  }

  for (const key of Object.keys(ds.values)) {
    const m = M.get(key);
    if (!m || !["money", "bn"].includes(m.unit) || ["operating_cash_flow", "net_new_money", "credit_loss_expense"].includes(key)) continue;
    const s = clean(series(ds, key));
    for (let i = 1; i < s.length; i++) {
      const [y0, x0] = s[i - 1];
      const [y1, x1] = s[i];
      if (x0 && Math.abs(x1 / x0) > 5 && Math.abs(x1) > 0) add("info", key, y1, `Changed by a factor of ${Math.abs(x1 / x0).toFixed(1)} vs ${y0} — unit error, or a genuine event to investigate?`);
    }
  }

  issues.sort((p, q) => SEVERITY_ORDER[p.severity] - SEVERITY_ORDER[q.severity] || String(p.metric).localeCompare(String(q.metric)) || (p.year || 0) - (q.year || 0));
  return issues;
}

// ------------------------------------------------------------------ import

/** Parse numbers as written in annual reports: 1'234.5 · 1,234.5 · 1.234,5 · (123) · 14.3 % · –. */
export function parseNumber(x, decimalComma = false) {
  if (x === null || x === undefined) return null;
  if (typeof x === "number") return Number.isFinite(x) ? x : null;
  let t = String(x).trim().replace(/[’   '%]/g, "");
  if (["", "-", "–", "—", "n/a", "na", "nan", "None"].includes(t)) return null;
  const negative = t.startsWith("(") && t.endsWith(")");
  t = t.replace(/[()]/g, "").replace(/[−–]/g, "-");
  t = decimalComma ? t.replace(/\./g, "").replace(",", ".") : t.replace(/,/g, "");
  if (!/^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i.test(t)) return null;
  const v = parseFloat(t);
  return negative ? -v : v;
}

function looksLikeYear(x) {
  const s = String(x).trim().replace(/\.0$/, "");
  return /^\d{4}$/.test(s) && +s >= 1990 && +s <= 2100;
}

/** Minimal RFC-4180 CSV parser (quotes, embedded separators, CRLF). */
export function parseCSV(text, sep) {
  const rows = [];
  let row = [], field = "", inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else inQ = false;
      } else field += c;
    } else if (c === '"') inQ = true;
    else if (c === sep) { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += c;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.some((c) => String(c).trim() !== ""));
}

/**
 * Turn a 2-D table (array of rows, first row = header) into {years, rows:{key:{year:val}}, mapped, unmapped, orientation}.
 * Layouts: wide (metric | 2021 | 2022 …), transposed (year | revenue | net_income …), long (metric | year | value).
 */
export function importRows(table, decimalComma = false) {
  if (!table.length) throw new Error("The file is empty.");
  const header = table[0].map((h) => String(h ?? "").trim());
  const lower = header.map((h) => h.toLowerCase());
  const body = table.slice(1);
  let wide = {}; // label -> {year: raw}
  let orientation;
  if (["metric", "year", "value"].every((k) => lower.includes(k))) {
    orientation = "long";
    const im = lower.indexOf("metric"), iy = lower.indexOf("year"), iv = lower.indexOf("value");
    for (const r of body) {
      const y = parseInt(String(r[iy]).trim(), 10);
      if (!Number.isFinite(y)) continue;
      const label = String(r[im]).trim();
      (wide[label] ||= {})[y] = r[iv];
    }
  } else {
    const yearCols = header.map((h, i) => [h, i]).slice(1).filter(([h]) => looksLikeYear(h));
    if (yearCols.length) {
      orientation = "wide";
      for (const r of body) {
        const label = String(r[0] ?? "").trim();
        if (!label) continue;
        wide[label] = Object.fromEntries(yearCols.map(([h, i]) => [parseInt(h, 10), r[i]]));
      }
    } else if (body.length && body.every((r) => looksLikeYear(r[0]))) {
      orientation = "transposed";
      header.slice(1).forEach((label, j) => {
        if (!label) return;
        wide[label] = Object.fromEntries(body.map((r) => [parseInt(String(r[0]), 10), r[j + 1]]));
      });
    } else {
      throw new Error("Could not find year columns. Use 'metric, 2021, 2022, …' (wide), 'year, revenue, net_income, …' (years as rows) or 'metric, year, value' (long).");
    }
  }
  const mapped = {}, unmapped = [], rows = {};
  const yearSet = new Set();
  for (const [label, byYear] of Object.entries(wide)) {
    let key = M.resolveAlias(label);
    if (key === null) { key = slugify(label); unmapped.push(label); } else mapped[label] = key;
    rows[key] = {};
    for (const [y, raw] of Object.entries(byYear)) {
      rows[key][String(y)] = parseNumber(raw, decimalComma);
      yearSet.add(+y);
    }
  }
  return { rows, years: [...yearSet].sort((a, b) => a - b), mapped, unmapped, orientation };
}

export function importText(text, filename = "data.csv") {
  const t = text.replace(/^﻿/, "");
  const sep = (t.match(/;/g) || []).length > (t.match(/,/g) || []).length ? ";" : filename.endsWith(".tsv") ? "\t" : ",";
  return importRows(parseCSV(t, sep), sep === ";");
}

export function mergeImport(ds, imported, overwrite = true) {
  const out = cloneDataset(ds);
  const years = [...new Set([...out.years, ...imported.years])].sort((a, b) => a - b);
  out.years = years;
  for (const k of Object.keys(out.values)) for (const y of years) if (!(String(y) in out.values[k])) out.values[k][String(y)] = null;
  for (const [k, row] of Object.entries(imported.rows)) {
    if (!out.values[k]) {
      out.values[k] = Object.fromEntries(years.map((y) => [String(y), null]));
      out.meta[k] = { source: "", note: "" };
    }
    for (const [y, v] of Object.entries(row)) {
      const cur = out.values[k][y];
      if (overwrite ? v !== null : cur === null || cur === undefined) out.values[k][y] = v ?? cur ?? null;
    }
  }
  return out;
}

export function toCSV(ds, currency, custom) {
  const esc = (s) => (/[",\n;]/.test(String(s)) ? `"${String(s).replace(/"/g, '""')}"` : String(s));
  const lines = [["metric", "label_en", "label_de", "unit", ...ds.years.map(String), "source", "note"].join(",")];
  for (const k of orderKeys(Object.keys(ds.values))) {
    const vals = ds.years.map((y) => (value(ds, k, y) ?? ""));
    lines.push([k, M.short(k, custom), M.german(k, custom), M.unitLabel(k, currency, custom), ...vals, ds.meta?.[k]?.source || "", ds.meta?.[k]?.note || ""].map(esc).join(","));
  }
  return lines.join("\n") + "\n";
}
