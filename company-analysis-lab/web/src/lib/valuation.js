// Valuation formulas. Port of lab/valuation.py. Rates are decimals (0.09 = 9 %).
import { METHOD_GUIDE } from "../generated/data.js";

export { METHOD_GUIDE };

const ok = (x) => typeof x === "number" && Number.isFinite(x);

export const safeDiv = (a, b) => (ok(a) && ok(b) && b !== 0 ? a / b : null);
export const pe = (price, eps) => (ok(eps) && eps > 0 ? safeDiv(price, eps) : null);
export const pb = (price, bvps) => (ok(bvps) && bvps > 0 ? safeDiv(price, bvps) : null);
export const dividendYield = (dps, price) => safeDiv(dps, price);
export const capm = (rf, beta, erp) => rf + beta * erp;
export const sustainableGrowth = (roe, payout) => (1 - payout) * roe;
export const justifiedPB = (roe, r, g) => (r <= g ? null : (roe - g) / (r - g));
export const justifiedPE = (payout, r, g, trailing = true) => (r <= g ? null : trailing ? (payout * (1 + g)) / (r - g) : payout / (r - g));
export const impliedRoeFromPB = (pbRatio, r, g) => g + pbRatio * (r - g);
export const gordonDDM = (d0, r, g) => (r <= g ? null : (d0 * (1 + g)) / (r - g));

export function twoStageDDM(d0, g1, years, g2, r) {
  if (r <= g2 || years < 0) return null;
  const dividends = [], pv = [];
  let d = d0;
  for (let t = 1; t <= years; t++) {
    d *= 1 + g1;
    dividends.push(d);
    pv.push(d / (1 + r) ** t);
  }
  const terminal = (d * (1 + g2)) / (r - g2);
  const pvTerminal = terminal / (1 + r) ** years;
  return { dividends, pvDividends: pv, terminal, pvTerminal, value: pv.reduce((a, b) => a + b, 0) + pvTerminal };
}

export function residualIncome(bv0, roe, r, g, payout, years = 10, fadeToR = false) {
  if (r <= g) return null;
  let bv = bv0, total = 0;
  const rows = [];
  for (let t = 1; t <= years; t++) {
    const roeT = fadeToR ? roe + (r - roe) * (t / years) : roe;
    const ri = (roeT - r) * bv;
    const pv = ri / (1 + r) ** t;
    rows.push({ year: t, bvOpen: bv, roe: roeT, residualIncome: ri, pv });
    total += pv;
    bv *= 1 + roeT * (1 - payout);
  }
  const last = rows[rows.length - 1].residualIncome;
  const terminal = fadeToR ? 0 : (last * (1 + g)) / (r - g);
  const pvTerminal = terminal / (1 + r) ** years;
  return { rows, pvRI: total, pvTerminal, value: bv0 + total + pvTerminal };
}

export const fcfeDCF = (fcfe0, gHigh, years, gTerm, r) => twoStageDDM(fcfe0, gHigh, years, gTerm, r);
export const bankDistributableFCFE = (netIncome, rwa, rwaGrowth, cet1Target) => netIncome - rwa * rwaGrowth * cet1Target;

export function sensitivityGrid(fn, rValues, gValues) {
  return rValues.map((r) => gValues.map((g) => {
    const v = fn(r, g);
    return ok(v) ? v : null;
  }));
}
