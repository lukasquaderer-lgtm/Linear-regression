// Metric catalogue — generated from lab/metrics.py, plus label helpers.
import { METRICS, ALIASES, SECTORS as SECTOR_LIST, SECTOR_NAMES } from "../generated/data.js";

export const SECTORS = SECTOR_LIST;
export const sectorName = (sector) => SECTOR_NAMES[sector] || (sector ? sector[0].toUpperCase() + sector.slice(1) : "");
export const isTrend = (m, sector) => Boolean(m.trend_metric || (m.trend_for || []).includes(sector));
export const isRequired = (m, sector) => m.sectors.includes(sector) && Boolean(m.core || m.sector_required || (m.required_for || []).includes(sector));
export const CATALOG = Object.fromEntries(METRICS.map((m) => [m.key, m]));
export const ORDER = METRICS.map((m) => m.key);

export const get = (key) => CATALOG[key] || null;

export function metricsForSector(sector) {
  return METRICS.filter((m) => m.sectors.includes(sector));
}

export function requiredMetrics(sector) {
  return metricsForSector(sector).filter((m) => isRequired(m, sector));
}

const UNIT_LABEL = { money: (c) => `${c} m`, bn: (c) => `${c} bn`, per_share: (c) => `${c} per share`, pct: () => "%", shares: () => "m shares" };

export function unitLabel(key, currency, custom) {
  const m = CATALOG[key];
  const unit = m ? m.unit : custom?.[key]?.unit;
  const f = UNIT_LABEL[unit];
  return f ? f(currency) : "";
}

export function unitOf(key, custom) {
  return CATALOG[key]?.unit || custom?.[key]?.unit || "money";
}

export function short(key, custom) {
  if (CATALOG[key]) return CATALOG[key].en;
  if (custom?.[key]) return custom[key].en || key;
  return key;
}

export function german(key, custom) {
  if (CATALOG[key]) return CATALOG[key].de;
  return custom?.[key]?.de || "";
}

export function higherIsBetter(key, custom) {
  if (CATALOG[key]) return CATALOG[key].higher_is_better;
  const h = custom?.[key]?.higher_is_better;
  return h === undefined ? true : h;
}

export function resolveAlias(name) {
  const raw = String(name).trim();
  if (CATALOG[raw]) return raw;
  let norm = raw.toLowerCase().replace(/[_-]/g, " ");
  norm = [...norm].filter((ch) => /[\p{L}\p{N} /]/u.test(ch)).join("");
  norm = norm.split(/\s+/).filter(Boolean).join(" ");
  if (ALIASES[norm]) return ALIASES[norm];
  for (const sep of ["(", "["]) {
    if (raw.includes(sep)) return resolveAlias(raw.split(sep)[0]);
  }
  return null;
}
