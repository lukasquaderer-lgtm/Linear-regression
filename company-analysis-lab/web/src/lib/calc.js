// Growth, CAGR, averages, trend classification, unusual changes. Port of lab/calculations.py.
// Series are arrays of [year, value|null] pairs.
import * as M from "./metrics.js";
import { value } from "./data.js";

const fin = (x) => typeof x === "number" && Number.isFinite(x);

export function yoyGrowth(s) {
  return s.map(([y, v], i) => {
    const prev = i ? s[i - 1][1] : null;
    return [y, fin(v) && fin(prev) && prev > 0 ? (v / prev - 1) * 100 : null];
  });
}

export function yoyChange(s) {
  return s.map(([y, v], i) => [y, i && fin(v) && fin(s[i - 1][1]) ? v - s[i - 1][1] : null]);
}

export function cagr(start, end, years) {
  if (!fin(start) || !fin(end) || years <= 0 || start <= 0 || end <= 0) return null;
  return ((end / start) ** (1 / years) - 1) * 100;
}

export function seriesCagr(s) {
  const c = s.filter(([, v]) => fin(v));
  if (c.length < 2) return [null, null, null];
  const [y0, v0] = c[0];
  const [y1, v1] = c[c.length - 1];
  return [cagr(v0, v1, y1 - y0), y0, y1];
}

export function isClose(user, correct, rel = 0.02, absTol = 0.15) {
  if (!fin(user) || !fin(correct)) return false;
  return Math.abs(user - correct) <= Math.max(absTol, rel * Math.abs(correct));
}

const mean = (a) => a.reduce((p, q) => p + q, 0) / a.length;

export function classifyTrend(s, key, custom) {
  const m = M.get(key);
  const c = s.filter(([, v]) => fin(v));
  if (c.length < 3) return { label: "insufficient data", direction: "flat", reasons: ["Fewer than three data points — no reliable trend."], stats: {} };
  const x = c.map(([yy]) => +yy);
  const y = c.map(([, v]) => v);
  const xm = mean(x), ym = mean(y);
  const slope = x.reduce((p, xi, i) => p + (xi - xm) * (y[i] - ym), 0) / x.reduce((p, xi) => p + (xi - xm) ** 2, 0);
  const level = mean(y.map(Math.abs)) || 1;
  const isRatio = M.unitOf(key, custom) === "pct";
  const slopeNorm = isRatio ? slope : (slope / level) * 100;
  const flatBand = isRatio ? 0.5 : 2.0;
  const diffs = y.slice(1).map((v, i) => v - y[i]);
  const thr = isRatio ? 0.1 : 0.005 * level;
  const signs = diffs.filter((d) => Math.abs(d) > thr).map(Math.sign);
  let reversals = 0;
  for (let i = 1; i < signs.length; i++) if (signs[i] !== signs[i - 1]) reversals++;
  const std = Math.sqrt(mean(y.map((v) => (v - ym) ** 2)));
  const cv = std / level;
  const maxDiff = Math.max(...diffs.map(Math.abs));
  const swing = isRatio ? maxDiff : maxDiff / level;
  const unit = isRatio ? "pp per year" : "% of the average level per year";
  const firstLast = isRatio ? y[y.length - 1] - y[0] : y[0] > 0 ? (y[y.length - 1] / y[0] - 1) * 100 : null;
  const stats = { slope: slopeNorm, reversals, cv, unit, firstLast };
  const sgn = (v) => (v >= 0 ? "+" : "") + v.toFixed(1);
  const reasons = [`Fitted trend: ${sgn(slopeNorm)} ${unit}.`];
  if (fin(firstLast)) reasons.push(`First to last year: ${sgn(firstLast)}${isRatio ? " pp" : " %"}.`);
  if (reversals >= 2 && (swing > (isRatio ? 2.0 : 0.25) || cv > 0.3)) {
    reasons.push(`The series changed direction ${reversals} times with large swings — no clean trend.`);
    return { label: "volatile", direction: "mixed", reasons, stats };
  }
  if (!isRatio && y.some((v) => v <= 0) && y.some((v) => v > 0)) reasons.push("The series crosses zero — growth rates are not meaningful; judge the level.");
  if (Math.abs(slopeNorm) < flatBand) {
    reasons.push(`Within ±${flatBand} ${unit} — treated as stable.`);
    return { label: "stable", direction: "flat", reasons, stats };
  }
  const direction = slopeNorm > 0 ? "up" : "down";
  const better = M.higherIsBetter(key, custom);
  if (better === null) return { label: direction === "up" ? "growing" : "shrinking", direction, reasons: [...reasons, "Neither good nor bad by itself — ask what drives it."], stats };
  const good = (direction === "up") === Boolean(better);
  if (!better) reasons.push("Lower is better for this metric.");
  return { label: good ? "improving" : "deteriorating", direction, reasons, stats };
}

const IMPORTANCE = { net_income: 1.6, revenue: 1.4, total_equity: 1.4, eps: 1.2, cet1_ratio: 1.3, solvency_ratio: 1.3, total_assets: 1.1, operating_cash_flow: 0.3, net_new_money: 0.5, total_liabilities: 0.6 };

export function unusualChanges(ds, { rel = 25, pp = 2, exclude = [] } = {}) {
  const out = [];
  const years = [...ds.years].sort((a, b) => a - b);
  for (const key of Object.keys(ds.values)) {
    const m = M.get(key);
    if (!m || m.unit === "shares" || key === "share_price" || exclude.includes(key)) continue;
    const w = IMPORTANCE[key] ?? 1;
    for (let i = 1; i < years.length; i++) {
      const a = value(ds, key, years[i - 1]), b = value(ds, key, years[i]);
      if (a === null || b === null) continue;
      if (m.unit === "pct") {
        const change = b - a;
        if (Math.abs(change) >= pp) out.push({ metric: key, year: years[i], from: a, to: b, change, unit: "pp", score: (Math.abs(change) / pp) * w });
      } else {
        if (a === 0) continue;
        const change = a > 0 ? (b / a - 1) * 100 : null;
        const signFlip = a * b < 0;
        if (signFlip || (fin(change) && Math.abs(change) >= rel)) {
          const score = (signFlip ? 10 : Math.min(Math.abs(change) / rel, 8)) * w;
          out.push({ metric: key, year: years[i], from: a, to: b, change, unit: "%", score, signFlip });
        }
      }
    }
  }
  return out.sort((p, q) => q.score - p.score);
}

/** Equity roll-forward: ΔEquity − (net income − dividends paid); dividends ≈ prior-year DPS × shares. */
export function impliedOtherEquityMovements(ds, year) {
  const e0 = value(ds, "total_equity", year - 1), e1 = value(ds, "total_equity", year), ni = value(ds, "net_income", year);
  const dpsPrev = value(ds, "dps", year - 1), shares = value(ds, "shares_outstanding", year);
  if (e0 === null || e1 === null || ni === null) return null;
  const known = dpsPrev !== null && shares !== null;
  const dividends = known ? dpsPrev * shares : 0;
  return { opening: e0, closing: e1, netIncome: ni, dividends, other: e1 - e0 - (ni - dividends), dividendsKnown: known };
}

// ------------------------------------------------------------------ formatting (Swiss style 1'234.5)

export function fmtNum(x, d = 0) {
  if (!fin(x)) return "–";
  const s = Math.abs(x).toFixed(d);
  const [int, dec] = s.split(".");
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, "'");
  return (x < 0 ? "−" : "") + grouped + (dec ? "." + dec : "");
}

export const fmtPct = (x, d = 1, signed = false) => (fin(x) ? `${signed && x >= 0 ? "+" : ""}${x < 0 ? "−" : ""}${Math.abs(x).toFixed(d)} %` : "–");

export function fmtMetric(x, key, currency, custom) {
  if (!fin(x)) return "–";
  const unit = M.unitOf(key, custom);
  if (unit === "pct") return fmtPct(x);
  if (unit === "per_share") return `${currency} ${fmtNum(x, 2)}`;
  if (unit === "bn") return `${currency} ${fmtNum(x, 1)} bn`;
  if (unit === "shares") return `${fmtNum(x, 1)} m`;
  return `${currency} ${fmtNum(x)} m`;
}
