// Ratio definitions (exported from lab/ratios.py), computation, diagnosis and DuPont.
import { RATIOS as RATIO_ROWS } from "../generated/data.js";
import * as M from "./metrics.js";
import { value } from "./data.js";
import { isClose } from "./calc.js";

export const RATIOS = Object.fromEntries(RATIO_ROWS.map((r) => [r.key, r]));
export const ALL_SECTORS_LEN = M.SECTORS.length;
export const isCore = (r, sector) => r.core === true || (Array.isArray(r.core) && r.core.includes(sector));

// Ratios whose formula is not simply first ÷ second (mirrors the lambdas in lab/ratios.py).
const FORMULA = {
  fcf_margin: ([ocf, capex, rev]) => [ocf - capex, rev],
  net_debt_ebitda: ([debt, cash, ebit, da]) => [debt - cash, ebit + da],
  roce: ([ebit, eq, debt, cash]) => [ebit, eq + debt - cash],
};

export const combine = (r, vals) => {
  const [a, b] = FORMULA[r.key] ? FORMULA[r.key](vals) : vals;
  if (!b) return null;
  const x = r.unit === "%" ? (a / b) * 100 : a / b;
  return Number.isFinite(x) ? x : null;
};

export const needsPriorYear = (r) => r.inputs.some((i) => i.averaged || i.opening);

export function availableRatios(profile, ds) {
  const ex = new Set(profile.not_applicable || []);
  return RATIO_ROWS.filter(
    (r) =>
      r.sectors.includes(profile.sector) &&
      !r.inputs.some((i) => ex.has(i.metric)) &&
      r.inputs.every((i) => ds.values[i.metric] && ds.years.some((y) => value(ds, i.metric, y) !== null)),
  );
}

export function compute(r, ds, year, currency = "") {
  const required = [], resolved = [], resolvedEnd = [], steps = [], missing = [];
  for (const spec of r.inputs) {
    const name = M.short(spec.metric);
    if (spec.opening) {
      const v0 = value(ds, spec.metric, year - 1);
      required.push({ metric: spec.metric, year: year - 1, value: v0, label: `${name} ${year - 1} (opening)` });
      resolved.push(v0);
      resolvedEnd.push(v0);
      if (v0 === null) missing.push(`${name} ${year - 1}`);
      continue;
    }
    if (spec.averaged) {
      const v0 = value(ds, spec.metric, year - 1), v1 = value(ds, spec.metric, year);
      required.push({ metric: spec.metric, year: year - 1, value: v0, label: `${name} ${year - 1}` });
      required.push({ metric: spec.metric, year, value: v1, label: `${name} ${year}` });
      if (v0 === null) missing.push(`${name} ${year - 1}`);
      if (v1 === null) missing.push(`${name} ${year}`);
      const avg = v0 !== null && v1 !== null ? (v0 + v1) / 2 : null;
      resolved.push(avg);
      resolvedEnd.push(v1);
      if (avg !== null) steps.push(`Average ${name} = (${fmt2(v0)} + ${fmt2(v1)}) ÷ 2 = ${fmt2(avg)}`);
    } else {
      const v1 = value(ds, spec.metric, year);
      required.push({ metric: spec.metric, year, value: v1, label: `${name} ${year}` });
      resolved.push(v1);
      resolvedEnd.push(v1);
      if (v1 === null) missing.push(`${name} ${year}`);
    }
  }
  let val = null, alternative = null;
  if (!missing.length) {
    val = combine(r, resolved);
    if (needsPriorYear(r) && r.inputs.some((i) => i.averaged)) alternative = combine(r, resolvedEnd);
    if (val !== null) steps.push(`${r.text}: inputs ${resolved.map(fmt2).join(" ; ")} → ${formatRatio(val, r, currency)}`);
  }
  return { ratio: r, year, value: val, required, steps, alternative, missing };
}

const fmt2 = (x) => x.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function formatRatio(x, r, currency = "") {
  if (x === null || !Number.isFinite(x)) return "–";
  if (r.unit === "%") return `${x.toFixed(2)} %`;
  if (r.unit === "x") return `${x.toFixed(2)}×`;
  return `${currency} ${fmt2(x)}`.trim();
}

/** Explain what went right or wrong. userInputs maps "metric|year" → number. */
export function diagnose(res, userInputs, userValue, currency = "") {
  const details = [];
  const r = res.ratio;
  if (res.value === null) return { correct: false, headline: "This ratio cannot be computed — data is missing.", details: [`Missing: ${res.missing.join(", ")}`] };
  const wrong = [];
  for (const rn of res.required) {
    const given = userInputs[`${rn.metric}|${rn.year}`];
    if (given === null || given === undefined) {
      details.push(`You did not enter ${rn.label}.`);
      wrong.push(rn);
    } else if (rn.value !== null && !isClose(given, rn.value, 0.005, 0.005)) {
      details.push(`${rn.label}: you used ${fmt2(given)}, the dataset has ${fmt2(rn.value)}.`);
      wrong.push(rn);
    }
  }
  if (userValue === null || userValue === undefined) return { correct: false, headline: "No result entered.", details };
  const tol = r.unit === "%" ? 0.05 : 0.02;
  if (isClose(userValue, res.value, 0.01, tol)) {
    if (wrong.length) details.push("Your final answer matches, but check the inputs above.");
    return { correct: true, headline: `Correct — ${formatRatio(res.value, r, currency)}.`, details };
  }
  if (res.alternative !== null && isClose(userValue, res.alternative, 0.01, tol)) {
    details.push(`You used year-end balances (${formatRatio(res.alternative, r, currency)}). That is a common shortcut, but CFA convention uses the average of opening and closing balances because the income was earned over the whole year.`);
    return { correct: false, headline: "Close — different convention (year-end instead of average balance).", details };
  }
  if (r.unit === "%" && isClose(userValue * 100, res.value, 0.01, tol)) {
    details.push("You entered a decimal (e.g. 0.12) — enter the ratio in percent (12.0).");
    return { correct: false, headline: "Right number, wrong format (decimal instead of percent).", details };
  }
  const inverted = r.unit === "%" ? (100 * 100) / res.value : 1 / res.value;
  if (res.value && isClose(userValue, inverted, 0.02, tol)) {
    details.push("It looks like you divided the inputs the wrong way round (denominator ÷ numerator).");
    return { correct: false, headline: "Inverted ratio.", details };
  }
  try {
    const vals = r.inputs.map((spec) => {
      const g = (y) => userInputs[`${spec.metric}|${y}`];
      if (spec.opening) return g(res.year - 1);
      if (spec.averaged) return (g(res.year - 1) + g(res.year)) / 2;
      return g(res.year);
    });
    const own = combine(r, vals);
    if (wrong.length && own !== null && isClose(userValue, own, 0.01, tol)) {
      details.push("Your arithmetic is consistent with the numbers you picked — the problem is the inputs.");
      return { correct: false, headline: "Wrong inputs, correct method.", details };
    }
  } catch {
    /* fall through */
  }
  details.push(`Expected ${formatRatio(res.value, r, currency)}; you entered ${formatRatio(userValue, r, currency)}.`);
  return { correct: false, headline: "Not quite — compare your steps with the worked solution.", details };
}

export function dupont(ds, year) {
  const g = (k, y) => value(ds, k, y);
  const ni = g("net_income", year), rev = g("revenue", year);
  const a0 = g("total_assets", year - 1), a1 = g("total_assets", year), e0 = g("total_equity", year - 1), e1 = g("total_equity", year);
  if ([ni, a0, a1, e0, e1].some((x) => x === null)) return null;
  const avgA = (a0 + a1) / 2, avgE = (e0 + e1) / 2;
  const out = { roa: (ni / avgA) * 100, leverage: avgA / avgE, roe: (ni / avgE) * 100 };
  if (rev) {
    out.net_margin = (ni / rev) * 100;
    out.asset_turnover = rev / avgA;
  }
  return out;
}

export function ratioSeries(ds, key) {
  const r = RATIOS[key];
  return ds.years.map((y) => [y, compute(r, ds, y).value]);
}
