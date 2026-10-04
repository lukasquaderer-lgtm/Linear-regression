// Analyst Training Mode: question bank, grading and spaced repetition. Port of lab/questions.py.
// Levels: 1 identify · 2 calculate · 3 interpret · 4 connect statements · 5 analyst reasoning (free text).
import * as M from "./metrics.js";
import * as C from "./calc.js";
import * as R from "./ratios.js";
import * as V from "./valuation.js";
import { value } from "./data.js";

export const LEVEL_NAMES = { 1: "Identify", 2: "Calculate", 3: "Interpret", 4: "Connect statements", 5: "Analyst reasoning" };

export const CONCEPT_LABELS = {
  revenue_lines: "Revenue and profit lines", business_model: "Business model and earnings drivers", revenue_mix: "Revenue mix (interest vs fees)",
  payout: "Payout ratio and retention", linking_statements: "Linking the financial statements", competitive_advantage: "Competitive advantages",
  statement_location: "Where metrics are reported", balance_sheet_identity: "Balance-sheet identity", data_units: "Units and data hygiene",
  eps_consistency: "EPS, shares and net income", accounting_changes: "Accounting changes and restatements", growth_cagr: "CAGR", yoy_growth: "Year-over-year growth",
  trend_interpretation: "Interpreting trends", ratio_definitions: "Ratio definitions", roe: "Return on equity", roa: "Return on assets", dupont: "DuPont decomposition",
  roe_vs_cost_of_equity: "ROE vs cost of equity", annual_report_navigation: "Navigating the annual report", statement_links: "Equity roll-forward",
  auditor_report: "Auditor's report and key audit matters", cash_flow_banks: "Cash flow statements of banks", operational_vs_accounting: "Operational vs accounting-driven changes",
  one_off_items: "One-off items", underlying_earnings: "Underlying earnings", reserves: "Reserve and provision releases", accruals: "Accrual ratio",
  quality_earnings: "Earnings quality judgement", regulatory_capital: "Regulatory capital ratios", capital_shock: "Capital stress arithmetic", risk_interest: "Interest-rate risk",
  risk_market: "Market risk transmission", risk_prioritisation: "Prioritising risks", peers: "Peer comparability", justified_pb: "ROE and P/B", leverage: "Leverage",
  peer_selection: "Choosing peers", valuation_methods: "Choosing a valuation method", ddm: "Dividend discount model", thesis: "Investment thesis discipline",
  scenario_analysis: "Scenario-weighted value", portfolio: "Portfolio context", sustainable_growth: "Sustainable growth", acquisition_effects: "Acquisition effects", combined_ratio: "Combined ratio",
  cost_structure: "Cost structure and R&D intensity", cash_conversion: "Cash conversion and working capital", debt_capacity: "Debt capacity (net debt ÷ EBITDA, interest cover)",
  risk_currency: "Currency risk", risk_demand: "Demand and cyclical risk", ev_multiples: "Enterprise value and EV/EBITDA", dcf: "DCF on free cash flow (WACC)",
};

export const conceptLabel = (c) => CONCEPT_LABELS[c] || c.replace(/_/g, " ").replace(/^./, (x) => x.toUpperCase());

// ------------------------------------------------------------------ seeded randomness

export function makeRng(seed) {
  let a = (seed >>> 0) || 1;
  const next = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return {
    random: next,
    choice: (arr) => arr[Math.floor(next() * arr.length)],
    shuffle: (arr) => {
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(next() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
      }
      return arr;
    },
  };
}

// ------------------------------------------------------------------ helpers

const years = (ds) => [...(ds?.years || [])].sort((a, b) => a - b);
const val = (ds, k, y) => (ds ? value(ds, k, y) : null);
function latestWith(ds, keys, needPrior = false) {
  for (const y of years(ds).reverse()) {
    if (keys.every((k) => val(ds, k, y) !== null) && (!needPrior || keys.every((k) => val(ds, k, y - 1) !== null))) return y;
  }
  return null;
}
const money = (x, ccy) => `${ccy} ${C.fmtNum(x)} m`;
const f2 = (x) => x.toFixed(2);
const pctS = (x) => `${x.toFixed(1)} %`;

function mc(id, stage, level, concept, prompt, correct, wrong, rng, explanation = "") {
  const options = rng.shuffle([correct, ...wrong]);
  return { id, stage, level, concept, kind: "mc", prompt, options, answer: options.indexOf(correct), explanation, relTol: 0.02, absTol: 0.1, unit: "", modelAnswer: "", review: false };
}
function num(id, stage, level, concept, prompt, answer, unit, explanation, relTol = 0.02, absTol = 0.1) {
  return { id, stage, level, concept, kind: "numeric", prompt, options: [], answer: +answer, explanation, relTol, absTol, unit, modelAnswer: "", review: false };
}
function text(id, stage, level, concept, prompt, modelAnswer) {
  return { id, stage, level, concept, kind: "text", prompt, options: [], answer: null, explanation: "", relTol: 0.02, absTol: 0.1, unit: "", modelAnswer, review: false };
}

const PROFILE_CONCEPT_STAGE = { business_model: 1, combined_ratio: 2, accounting_changes: 3, one_off_items: 5, acquisition_effects: 5, linking_statements: 5, valuation_methods: 9 };

function profileQuestion(ctx, stage, level, rng) {
  const items = (ctx.profile.quiz || []).filter((q) => PROFILE_CONCEPT_STAGE[q.concept] === stage && q.level === level);
  if (!items.length) return null;
  const q = rng.choice(items);
  const correct = q.options[q.answer];
  return mc(`profile-${ctx.profile.id}-${q.concept}-${level}`, stage, level, q.concept, q.prompt, correct, q.options.filter((_, i) => i !== q.answer), rng, q.explanation || "");
}

// ------------------------------------------------------------------ templates

export const TEMPLATES = [];
const T = (id, stage, level, concepts, build) => TEMPLATES.push({ id, stage, level, concepts, build });

// ---------------------------------------------------------------- Stage 1
T("s1-revenue-line", 1, 1, ["revenue_lines"], (ctx, rng) =>
  ctx.sector === "bank"
    ? mc("s1-revenue-line-bank", 1, 1, "revenue_lines", "Which income-statement line captures what a bank earns on loans and securities after paying interest on deposits and debt?", "Net interest income (Zinserfolg)", ["Net fee and commission income", "Trading income", "Other operating income"], rng, "Net interest income = interest income − interest expense. Fees come from services; trading from market-making and FX.")
    : mc("s1-revenue-line-ins", 1, 1, "revenue_lines", "Under IFRS 17, which line shows what an insurer earns for providing insurance cover in the period?", "Insurance revenue (Versicherungsumsatz)", ["Gross written premiums", "Net investment income", "Insurance finance expenses"], rng, "Insurance revenue reflects services provided in the period and excludes investment components; gross written premiums is a volume measure."));
T("s1-profile-l1", 1, 1, ["business_model"], (ctx, rng) => profileQuestion(ctx, 1, 1, rng));
T("s1-payout", 1, 2, ["payout"], (ctx, rng) => {
  const y = latestWith(ctx.values, ["eps", "dps"]);
  if (y !== null && val(ctx.values, "eps", y) > 0) {
    const eps = val(ctx.values, "eps", y), dps = val(ctx.values, "dps", y), ans = (dps / eps) * 100;
    return num(`s1-payout-${y}`, 1, 2, "payout", `How much of its profit does ${ctx.name} hand back as dividends? In ${y} diluted EPS was ${ctx.currency} ${f2(eps)} and the dividend per share ${ctx.currency} ${f2(dps)}. Calculate the payout ratio in %.`, ans, "%", `Payout = DPS ÷ EPS = ${f2(dps)} ÷ ${f2(eps)} = ${ans.toFixed(1)} %.`);
  }
  const eps = rng.choice([4.0, 5.5, 8.0, 12.0]);
  const dps = Math.round(eps * rng.choice([0.4, 0.5, 0.6, 0.7]) * 100) / 100;
  return num("s1-payout-generic", 1, 2, "payout", `A company reports diluted EPS of ${f2(eps)} and proposes a dividend of ${f2(dps)} per share. What is the payout ratio in %?`, (dps / eps) * 100, "%", `Payout = DPS ÷ EPS = ${f2(dps)} ÷ ${f2(eps)} = ${((dps / eps) * 100).toFixed(1)} %.`);
});
T("s1-revenue-mix", 1, 2, ["revenue_mix"], (ctx, rng) => {
  if (ctx.sector === "bank") {
    const y = latestWith(ctx.values, ["fee_income", "revenue"]);
    if (y !== null) {
      const fee = val(ctx.values, "fee_income", y), rev = val(ctx.values, "revenue", y);
      return num(`s1-feeshare-${y}`, 1, 2, "revenue_mix", `${ctx.name} ${y}: net fee and commission income ${money(fee, ctx.currency)}, total operating income ${money(rev, ctx.currency)}. What share of operating income comes from fees (%)?`, (fee / rev) * 100, "%", `Fee share = ${C.fmtNum(fee)} ÷ ${C.fmtNum(rev)} = ${((fee / rev) * 100).toFixed(1)} %.`);
    }
    const [nii, fee, trd] = rng.choice([[4200, 5100, 1700], [300, 520, 80], [6500, 19000, 9000]]);
    const tot = nii + fee + trd;
    return num("s1-feeshare-generic", 1, 2, "revenue_mix", `A bank earns net interest income of ${C.fmtNum(nii)}, fees of ${C.fmtNum(fee)} and trading income of ${C.fmtNum(trd)} (total ${C.fmtNum(tot)}). What share of operating income comes from fees (%)?`, (fee / tot) * 100, "%", `${C.fmtNum(fee)} ÷ ${C.fmtNum(tot)} = ${((fee / tot) * 100).toFixed(1)} %. A high fee share means less capital-intensive, more market-sensitive earnings.`);
  }
  const [sav, risk, fee] = rng.choice([[600, 250, 400], [900, 300, 700], [450, 150, 500]]);
  const tot = sav + risk + fee;
  return num("s1-feeshare-ins", 1, 2, "revenue_mix", `A life insurer's operating result comes from the savings result ${sav}, the risk result ${risk} and the fee result ${fee} (total ${tot}). What share comes from the fee result (%)?`, (fee / tot) * 100, "%", `${fee} ÷ ${tot} = ${((fee / tot) * 100).toFixed(1)} %. Fee income needs little solvency capital.`);
});
T("s1-interpret", 1, 3, ["business_model"], (ctx, rng) =>
  profileQuestion(ctx, 1, 3, rng) ||
  (ctx.sector === "bank"
    ? mc("s1-interpret-bank", 1, 3, "business_model", "Most of a wealth manager's fees are 'recurring' — charged as a percentage of client assets. What happens to these fees if markets fall 20 % and no client leaves?", "They fall roughly in line with client assets — earnings are market-sensitive even without outflows", ["They stay flat because no client left", "They rise because clients trade more", "They are unaffected because they are contractual fixed fees"], rng, "Asset-based fees scale with the value of assets under management.")
    : mc("s1-interpret-ins", 1, 3, "business_model", "Why do a reinsurer's profits swing more from year to year than a life insurer's?", "Large natural catastrophes hit P&C reinsurance results in irregular years", ["Reinsurers do not invest their premiums", "Reinsurers report under cash accounting", "Life insurers have no investment risk"], rng, "Catastrophe losses are lumpy; life business earns more stable spread and fee income.")));
T("s1-link", 1, 4, ["linking_statements"], (ctx, rng) =>
  ctx.sector === "bank"
    ? mc("s1-link-bank", 1, 4, "linking_statements", "A bank's customer deposits grow strongly while loans stay flat. Where does the extra money end up, and what happens to net interest income if central-bank rates then fall?", "In cash at the central bank and liquid securities (balance sheet); NII falls as the yield on that liquidity drops", ["In equity; NII rises", "In goodwill; NII is unaffected", "In the cash flow statement only; NII rises"], rng, "Deposits are liabilities funding assets — surplus deposits are parked in liquidity whose yield moves with policy rates.")
    : mc("s1-link-ins", 1, 4, "linking_statements", "An insurer collects premiums today and pays claims years later. Where does that money sit in the meantime, and which income-statement line does it feed?", "In investments (balance sheet), producing investment income (income statement)", ["In equity, producing fee income", "In goodwill, producing insurance revenue", "Off balance sheet, producing nothing"], rng, "The 'float' is invested — matched by insurance liabilities on the other side of the balance sheet."));
T("s1-moat", 1, 5, ["competitive_advantage"], (ctx) => {
  const ref = ctx.profile.business_reference?.advantages?.reference || "";
  const extra = ctx.sector === "bank"
    ? "For a bank: falling net new money, a shrinking fee margin (fees ÷ average client assets), rising cost/income, loss of market share in key regions."
    : "For an insurer: falling new-business margins or CSM growth, rising lapse rates, a deteriorating combined ratio, losing market share in core lines.";
  return text("s1-moat", 1, 5, "competitive_advantage", `Choose the competitive advantage of ${ctx.name} you think is most durable. Which numbers in the annual report, tracked over several years, would show you that it is eroding?`, `Reference advantages: ${ref} Evidence of erosion — ${extra} A good answer names one specific advantage, the metric that measures it, and the direction that would worry you.`);
});

// ---------------------------------------------------------------- Stage 2
const STATEMENT_OF = {
  revenue: "Income statement", net_income: "Income statement", operating_expenses: "Income statement", net_interest_income: "Income statement", fee_income: "Income statement", eps: "Income statement",
  insurance_revenue: "Income statement", investment_income: "Income statement", insurance_service_result: "Income statement",
  total_assets: "Balance sheet", total_liabilities: "Balance sheet", total_equity: "Balance sheet", customer_loans: "Balance sheet", customer_deposits: "Balance sheet",
  operating_cash_flow: "Cash flow statement",
  cet1_capital: "Regulatory disclosure (Pillar 3 / SFCR)", rwa: "Regulatory disclosure (Pillar 3 / SFCR)", cet1_ratio: "Regulatory disclosure (Pillar 3 / SFCR)", solvency_ratio: "Regulatory disclosure (Pillar 3 / SFCR)",
  aum: "Management report / key figures", net_new_money: "Management report / key figures", gross_premiums: "Management report / key figures",
  gross_profit: "Income statement", ebit: "Income statement", rnd_expense: "Income statement", interest_expense: "Income statement",
  capex: "Cash flow statement", depreciation_amortisation: "Cash flow statement", free_cash_flow: "Management report / key figures",
  cash: "Balance sheet", total_debt: "Balance sheet", inventories: "Balance sheet", receivables: "Balance sheet",
};
const STATEMENT_OPTIONS = ["Income statement", "Balance sheet", "Cash flow statement", "Regulatory disclosure (Pillar 3 / SFCR)", "Management report / key figures"];
T("s2-where", 2, 1, ["statement_location"], (ctx, rng) => {
  const keys = Object.keys(STATEMENT_OF).filter((k) => M.CATALOG[k].sectors.includes(ctx.sector) && !(ctx.profile.not_applicable || []).includes(k));
  const key = rng.choice(keys);
  const correct = STATEMENT_OF[key];
  const m = M.CATALOG[key];
  return mc(`s2-where-${key}`, 2, 1, "statement_location", `Where would you primarily look up '${m.en} · ${m.de}'?`, correct, STATEMENT_OPTIONS.filter((o) => o !== correct).slice(0, 3), rng, `${m.en}: ${m.statement || correct}.`);
});
T("s2-profile-l1", 2, 1, ["combined_ratio"], (ctx, rng) => profileQuestion(ctx, 2, 1, rng));
T("s2-identity", 2, 2, ["balance_sheet_identity"], (ctx, rng) => {
  const y = latestWith(ctx.values, ["total_assets", "total_equity"]);
  if (y !== null) {
    const a = val(ctx.values, "total_assets", y), e = val(ctx.values, "total_equity", y);
    return num(`s2-identity-${y}`, 2, 2, "balance_sheet_identity", `${ctx.name} ${y}: total assets ${money(a, ctx.currency)}, shareholders' equity ${money(e, ctx.currency)}. Ignoring non-controlling interests, what are total liabilities (${ctx.currency} m)?`, a - e, `${ctx.currency} m`, `Assets = liabilities + equity → liabilities = ${C.fmtNum(a)} − ${C.fmtNum(e)} = ${C.fmtNum(a - e)}. (Minority interests would sit between the two.)`, 0.005, 1);
  }
  const [a, e] = rng.choice([[25000, 2100], [220000, 7500], [130000, 23000]]);
  return num("s2-identity-generic", 2, 2, "balance_sheet_identity", `Total assets are ${C.fmtNum(a)} and shareholders' equity ${C.fmtNum(e)}. What are total liabilities?`, a - e, "", `${C.fmtNum(a)} − ${C.fmtNum(e)} = ${C.fmtNum(a - e)}.`, 0.005, 1);
});
T("s2-units", 2, 3, ["data_units"], (ctx, rng) => mc("s2-units", 2, 3, "data_units", "Your dataset shows equity of 85'079 (USD m) for a bank. A colleague's spreadsheet shows 85.1 for the same year and the same company. What is the most likely explanation?", "The colleague's sheet is in billions, yours in millions — always label units", ["The colleague used a different company", "The bank restated equity by 99.9 %", "One of you used per-share values"], rng, "Unit mismatches (m vs bn, % vs decimal) are the most common data-entry error. That is why every row in Stage 2 carries a unit."));
T("s2-eps", 2, 4, ["eps_consistency"], (ctx, rng) => {
  const y = latestWith(ctx.values, ["net_income", "eps"]);
  if (y !== null && val(ctx.values, "eps", y) > 0) {
    const ni = val(ctx.values, "net_income", y), eps = val(ctx.values, "eps", y);
    return num(`s2-eps-${y}`, 2, 4, "eps_consistency", `${ctx.name} ${y}: net income attributable to shareholders ${money(ni, ctx.currency)} (income statement) and diluted EPS ${ctx.currency} ${f2(eps)}. What diluted share count (millions) do these two numbers imply?`, ni / eps, "m shares", `Shares ≈ net income ÷ EPS = ${C.fmtNum(ni)} ÷ ${f2(eps)} = ${C.fmtNum(ni / eps, 1)} m. Compare with the EPS note — a big gap means a different earnings basis or a data error.`, 0.01);
  }
  const [ni, eps] = rng.choice([[1200, 42.0], [7500, 2.3], [165, 5.4]]);
  return num("s2-eps-generic", 2, 4, "eps_consistency", `Net income is ${C.fmtNum(ni)} m and diluted EPS ${f2(eps)}. Implied diluted share count (millions)?`, ni / eps, "m shares", `${C.fmtNum(ni)} ÷ ${f2(eps)} = ${C.fmtNum(ni / eps, 1)} m.`, 0.01);
});
T("s2-basis", 2, 5, ["accounting_changes"], (ctx) => {
  const bases = [...new Set(Object.values(ctx.profile.accounting || {}))];
  if (bases.length > 1) return text("s2-basis", 2, 5, "accounting_changes", `Your ${ctx.name} dataset mixes accounting bases: ${bases.join(", ")}. How does this affect trend analysis, and what would you do about it?`, "Figures before and after a change in standards are not comparable (e.g. IFRS 17 removes savings components from revenue and moves future profit into the CSM; US GAAP vs IFRS measure equity differently). Use restated comparatives where the company provides them, mark the break in charts, compare growth only within the same basis, and prefer ratios/KPIs that are less affected (e.g. solvency ratio, dividends). State the limitation explicitly.");
  return text("s2-basis-vendor", 2, 5, "accounting_changes", `Part of your ${ctx.name} dataset came from a data vendor. Give two reasons why vendor figures can differ from the annual report, and say which source you treat as authoritative.`, "Vendors standardise line items to an industrial template (mapping a bank's 'operating income' to 'gross profit'), may use different definitions (attributable vs total net income, basic vs diluted EPS), mix restated and original figures, or convert currencies. The audited annual report is authoritative; the vendor is a cross-check.");
});

// ---------------------------------------------------------------- Stage 3
T("s3-cagr-def", 3, 1, ["growth_cagr"], (ctx, rng) => mc("s3-cagr-def", 3, 1, "growth_cagr", "Net income grew at a 4-year CAGR of 5 %. What does that mean?", "The constant annual growth rate that turns the first year's value into the last year's value", ["Net income grew by 5 % in each of the four years", "The average of the four yearly growth rates was 5 %", "Net income is 5 % higher than four years ago"], rng, "CAGR is a geometric average: (end ÷ start)^(1/n) − 1. Individual years can differ wildly."));
T("s3-cagr", 3, 2, ["growth_cagr"], (ctx, rng) => {
  const cands = [];
  for (const key of ["net_income", "total_equity", "revenue", "dps", "eps", "aum", "total_assets"]) {
    const s = ctx.values.values[key] ? years(ctx.values).map((y) => [y, val(ctx.values, key, y)]).filter(([, v]) => v !== null) : [];
    if (s.length >= 3 && s[0][1] > 0 && s[s.length - 1][1] > 0) cands.push([key, s]);
  }
  if (cands.length) {
    const [key, s] = rng.choice(cands);
    const [y0, v0] = s[0], [y1, v1] = s[s.length - 1];
    const ans = C.cagr(v0, v1, y1 - y0);
    return num(`s3-cagr-${key}`, 3, 2, "growth_cagr", `${ctx.name}: ${M.short(key)} was ${C.fmtNum(v0, 2)} in ${y0} and ${C.fmtNum(v1, 2)} in ${y1}. Calculate the CAGR in %.`, ans, "%", `CAGR = (${C.fmtNum(v1, 2)} ÷ ${C.fmtNum(v0, 2)})^(1/${y1 - y0}) − 1 = ${ans.toFixed(2)} %.`, 0.02, 0.1);
  }
  const [a, b, n] = rng.choice([[100, 146.4, 4], [2000, 2600, 4], [50, 41, 3]]);
  const ans = C.cagr(a, b, n);
  return num("s3-cagr-generic", 3, 2, "growth_cagr", `A metric went from ${a} to ${b} over ${n} years. CAGR in %?`, ans, "%", `(${b} ÷ ${a})^(1/${n}) − 1 = ${ans.toFixed(2)} %.`);
});
T("s3-yoy", 3, 2, ["yoy_growth"], (ctx, rng) => {
  const pairs = [];
  for (const key of ["net_income", "revenue", "total_equity", "eps"]) {
    for (const y of years(ctx.values).slice(1)) {
      const a = val(ctx.values, key, y - 1), b = val(ctx.values, key, y);
      if (a && b && a > 0) pairs.push([key, y, a, b]);
    }
  }
  if (pairs.length) {
    const [key, y, a, b] = rng.choice(pairs);
    const ans = (b / a - 1) * 100;
    return num(`s3-yoy-${key}-${y}`, 3, 2, "yoy_growth", `${ctx.name}: ${M.short(key)} ${y - 1} = ${C.fmtNum(a, 2)}, ${y} = ${C.fmtNum(b, 2)}. Year-over-year growth in %?`, ans, "%", `(${C.fmtNum(b, 2)} ÷ ${C.fmtNum(a, 2)}) − 1 = ${C.fmtPct(ans, 2, true)}.`);
  }
  return num("s3-yoy-generic", 3, 2, "yoy_growth", "Revenue went from 480 to 516. Growth in %?", 7.5, "%", "516 ÷ 480 − 1 = 7.5 %.");
});
T("s3-margin", 3, 3, ["trend_interpretation"], (ctx, rng) => {
  const ys = years(ctx.values).filter((y) => val(ctx.values, "revenue", y) !== null && val(ctx.values, "net_income", y) !== null);
  if (ys.length >= 3) {
    const y0 = ys[0], y1 = ys[ys.length - 1];
    const gr = C.cagr(val(ctx.values, "revenue", y0), val(ctx.values, "revenue", y1), y1 - y0);
    const gn = C.cagr(val(ctx.values, "net_income", y0), val(ctx.values, "net_income", y1), y1 - y0);
    if (gr !== null && gn !== null && Math.abs(gr - gn) > 0.5) {
      const rose = "It rose — profit grew faster than revenue";
      const fell = "It fell — profit grew more slowly than revenue (costs, losses or taxes rose faster)";
      const correct = gn > gr ? rose : fell;
      return mc(`s3-margin-${ctx.profile.id}`, 3, 3, "trend_interpretation", `From ${y0} to ${y1}, ${ctx.name}'s revenue grew at ${gr.toFixed(1)} % a year and net income at ${gn.toFixed(1)} % a year. What happened to the net profit margin?`, correct, [gn > gr ? fell : rose, "It cannot change if both grow", "It doubled"], rng, "Margin = net income ÷ revenue. If the numerator grows faster than the denominator, the margin rises.");
    }
  }
  return mc("s3-margin-generic", 3, 3, "trend_interpretation", "Revenue grew at 5 % a year while net income fell at 3 % a year. What does it tell you?", "Margins are compressing — investigate costs, credit losses, taxes or one-offs", ["The company is becoming more efficient", "Nothing — growth rates of different lines are unrelated", "The share count must have fallen"], rng);
});
T("s3-profile-l3", 3, 3, ["accounting_changes"], (ctx, rng) => {
  for (const lvl of [2, 4, 3]) {
    const q = profileQuestion(ctx, 3, lvl, rng);
    if (q) return { ...q, level: 3 };
  }
  return null;
});
T("s3-equity-roll", 3, 4, ["linking_statements"], (ctx) => {
  for (const y of years(ctx.values).reverse()) {
    const r = C.impliedOtherEquityMovements(ctx.values, y);
    if (r && r.dividendsKnown) {
      return num(`s3-roll-${y}`, 3, 4, "linking_statements", `${ctx.name} ${y}: equity rose from ${money(r.opening, ctx.currency)} to ${money(r.closing, ctx.currency)}. Net income was ${money(r.netIncome, ctx.currency)} and dividends paid about ${money(r.dividends, ctx.currency)} (prior-year DPS × shares). How large were all OTHER equity movements combined (buybacks, OCI, FX, acquisitions…)? Enter a negative number for a reduction (${ctx.currency} m).`, r.other, `${ctx.currency} m`, `ΔEquity − (net income − dividends) = (${C.fmtNum(r.closing)} − ${C.fmtNum(r.opening)}) − (${C.fmtNum(r.netIncome)} − ${C.fmtNum(r.dividends)}) = ${C.fmtNum(r.other)}. Find the components in the statement of changes in equity.`, 0.03, Math.max(1, Math.abs(r.closing) * 0.002));
    }
  }
  return num("s3-roll-generic", 3, 4, "linking_statements", "Opening equity 10'000, net income 900, dividends paid 450, closing equity 10'150. Other movements combined?", -300, "", "10'150 − 10'000 − 900 + 450 = −300.", 0.02, 1);
});
T("s3-reverse", 3, 5, ["trend_interpretation"], (ctx) => text("s3-reverse", 3, 5, "trend_interpretation", `Which trend you analysed for ${ctx.name} is most likely to reverse in the next two years? Explain the mechanism, not just the direction.`, (ctx.sector === "bank" ? "Banks: net interest income after central-bank rate cuts (SNB at 0 %), credit-loss releases that cannot repeat, cost savings that are front-loaded, one-off gains (e.g. negative goodwill) dropping out. " : "Insurers: reserve releases or a benign catastrophe year that will not repeat, investment yields after rate moves, accounting effects from IFRS 17 transition, buyback-driven EPS growth. ") + "A strong answer names the metric, the driver behind the past trend, why that driver changes, and which number you would monitor."));

// ---------------------------------------------------------------- Stage 4
T("s4-identify", 4, 1, ["ratio_definitions"], (ctx, rng) => {
  const choices = [["Net income ÷ average shareholders' equity", "Return on equity (ROE)"], ["Net income ÷ average total assets", "Return on assets (ROA)"], ["Average total assets ÷ average equity", "Financial leverage (equity multiplier)"], ["Operating expenses ÷ operating income", "Cost/income ratio"], ["Dividend per share ÷ EPS", "Payout ratio"]];
  const [formula, correct] = rng.choice(choices);
  return mc(`s4-identify-${correct.slice(0, 10)}`, 4, 1, "ratio_definitions", `Which ratio is defined as: ${formula}?`, correct, choices.map((c) => c[1]).filter((c) => c !== correct).slice(0, 3), rng);
});
T("s4-calc", 4, 2, ["roa", "roe"], (ctx, rng) => {
  const opts = [];
  for (const key of ["roa", "roe"]) {
    const rd = R.RATIOS[key];
    const y = latestWith(ctx.values, rd.inputs.map((i) => i.metric), true);
    if (y !== null) opts.push([key, y]);
  }
  if (opts.length) {
    const [key, y] = rng.choice(opts);
    const res = R.compute(R.RATIOS[key], ctx.values, y, ctx.currency);
    if (res.value !== null) {
      const nums = res.required.map((rn) => `${rn.label}: ${C.fmtNum(rn.value)}`).join("; ");
      return num(`s4-${key}-${y}`, 4, 2, key, `${ctx.name} ${y}. ${nums}. Calculate ${R.RATIOS[key].en} using average balances (in %).`, res.value, "%", res.steps.join(" → "), 0.02, 0.05);
    }
  }
  return num("s4-roe-generic", 4, 2, "roe", "Net income 1'200; equity 10'000 at the start and 11'000 at the end of the year. ROE on average equity (%)?", (1200 / 10500) * 100, "%", "Average equity = 10'500 → ROE = 1'200 ÷ 10'500 = 11.43 %.", 0.02, 0.05);
});
T("s4-dupont-interpret", 4, 3, ["dupont"], (ctx, rng) => mc("s4-dupont-int", 4, 3, "dupont", "A bank's ROE rose from 8 % to 11 % while its ROA stayed unchanged. What explains the increase?", "Higher financial leverage (more assets per unit of equity)", ["Higher net profit margin", "Lower cost/income ratio", "Higher dividend payout"], rng, "ROE = ROA × leverage. If ROA is flat, leverage must have risen — higher ROE but thinner capital buffer."));
T("s4-dupont-calc", 4, 4, ["dupont"], (ctx) => {
  for (const y of years(ctx.values).reverse()) {
    const d = R.dupont(ctx.values, y);
    if (d) return num(`s4-dupont-${y}`, 4, 4, "dupont", `${ctx.name} ${y}: ROA (on average assets) = ${d.roa.toFixed(3)} % and financial leverage (average assets ÷ average equity) = ${f2(d.leverage)}×. Using DuPont, what is ROE (%)?`, d.roa * d.leverage, "%", `ROE = ROA × leverage = ${d.roa.toFixed(3)} % × ${f2(d.leverage)} = ${(d.roa * d.leverage).toFixed(2)} %. This connects the income statement (net income) with the balance sheet (assets, equity).`, 0.02, 0.1);
  }
  return num("s4-dupont-generic", 4, 4, "dupont", "ROA 0.6 %, leverage 18×. ROE (%)?", 10.8, "%", "0.6 % × 18 = 10.8 %.");
});
T("s4-value", 4, 5, ["roe_vs_cost_of_equity"], (ctx) => text("s4-value", 4, 5, "roe_vs_cost_of_equity", `Compare ${ctx.name}'s latest ROE with a cost of equity of roughly 9–10 %. Is it creating value for shareholders? Name three levers management could pull to raise ROE — and the risk each lever brings.`, "Value is created when ROE exceeds the cost of equity (then P/B > 1 is justified). Levers: (1) higher margins/revenue (pricing, fee growth) — competitive risk; (2) cost cuts (lower cost/income) — execution and franchise risk; (3) more leverage or returning excess capital via buybacks — lower capital buffer, regulatory limits; also mix shift to capital-light businesses. Adjust ROE for one-offs before judging."));

// ---------------------------------------------------------------- Stage 5
const WHERE_ITEMS = [["details of goodwill impairment testing", "Notes to the financial statements"], ["the key audit matters", "Auditor's report"], ["dividends paid and share buybacks during the year", "Statement of changes in equity"], ["the reconciliation of net income to operating cash flow", "Cash flow statement"], ["unrealised gains and losses that bypass net income (OCI)", "Statement of comprehensive income"]];
const WHERE_OPTIONS = ["Notes to the financial statements", "Auditor's report", "Statement of changes in equity", "Cash flow statement", "Statement of comprehensive income"];
T("s5-where", 5, 1, ["annual_report_navigation"], (ctx, rng) => {
  const [item, correct] = rng.choice(WHERE_ITEMS);
  return mc(`s5-where-${item.slice(0, 12)}`, 5, 1, "annual_report_navigation", `Where in the annual report do you find ${item}?`, correct, WHERE_OPTIONS.filter((o) => o !== correct).slice(0, 3), rng);
});
T("s5-roll", 5, 2, ["statement_links"], (ctx, rng) => {
  const o = rng.choice([8000, 12000, 25000]);
  const ni = Math.round(o * rng.choice([0.08, 0.1, 0.12]));
  const div = Math.round(ni * 0.5);
  const bb = rng.choice([0, 200, 500]);
  const oci = rng.choice([-600, -150, 120, 300]);
  const c = o + ni - div - bb + oci;
  const s = (x) => (x >= 0 ? "+" : "−") + C.fmtNum(Math.abs(x));
  return num(`s5-roll-${o}-${oci}`, 5, 2, "statement_links", `Opening equity ${C.fmtNum(o)}; net income ${C.fmtNum(ni)}; dividends paid ${C.fmtNum(div)}; share buybacks ${C.fmtNum(bb)}; other comprehensive income ${s(oci)}. What is closing equity?`, c, "", `${C.fmtNum(o)} + ${C.fmtNum(ni)} − ${C.fmtNum(div)} − ${C.fmtNum(bb)} ${s(oci)} = ${C.fmtNum(c)}. Every movement appears in the statement of changes in equity.`, 0.02, 0.5);
});
T("s5-kam", 5, 3, ["auditor_report"], (ctx, rng) => {
  const focus = ctx.profile.audit_focus?.length ? ctx.profile.audit_focus : ["Valuation of insurance contract liabilities"];
  const item = rng.choice(focus);
  return mc(`s5-kam-${[...item].reduce((p, ch) => p + ch.charCodeAt(0), 0) % 997}`, 5, 3, "auditor_report", `A key audit matter in ${ctx.name}'s auditor's report is: '${item}'. What should it tell you as an analyst?`, "The area involves significant judgement or estimation — read the related note, its assumptions and sensitivities", ["The auditor found an error that was not corrected", "The figure is guaranteed to be accurate", "The company will restate its accounts"], rng, "Key audit matters flag the highest-risk areas; they are not qualifications. A qualified opinion would be stated in the opinion paragraph.");
});
T("s5-profile-l3", 5, 3, ["one_off_items", "acquisition_effects"], (ctx, rng) => profileQuestion(ctx, 5, 3, rng));
T("s5-bank-cf", 5, 4, ["cash_flow_banks"], (ctx, rng) =>
  ctx.sector === "bank"
    ? mc("s5-bank-cf", 5, 4, "cash_flow_banks", "A bank reports positive net income but a large negative operating cash flow. Why is this usually NOT a red flag?", "Operating cash flow of banks is dominated by changes in loans, deposits and trading balances, not by earnings quality", ["Banks never collect their interest in cash", "Negative cash flow always means fraud", "Net income is not audited for banks"], rng, "For banks, lending and deposit-taking are operating activities — growing the loan book 'consumes' operating cash.")
    : mc("s5-ins-cf", 5, 4, "cash_flow_banks", "A life insurer's operating cash flow swings between strongly positive and negative while net income is stable. Most likely reason?", "Investment purchases/sales and policyholder flows (premiums, surrenders) are partly classified as operating cash flows", ["Net income is wrong", "The insurer stopped paying claims", "Depreciation changed"], rng));
T("s5-profile-l4", 5, 4, ["linking_statements"], (ctx, rng) => profileQuestion(ctx, 5, 4, rng));
T("s5-investigate", 5, 5, ["operational_vs_accounting"], (ctx) => {
  const changes = C.unusualChanges(ctx.values);
  if (changes.length) {
    const ch = changes[0];
    const evs = (ctx.profile.events || []).filter((e) => e.year === ch.year && (!e.metrics?.length || e.metrics.includes(ch.metric)));
    const model = evs.map((e) => `${e.title}: ${e.detail} Verify in: ${e.where_to_verify}`).join(" ") || "Start from the management report, then the relevant note; check whether the change is due to volumes/prices (operational), a change in standards or estimates (accounting), or a non-recurring event; verify in the statement of changes in equity, the segment note and the auditor's key audit matters.";
    const changeTxt = Number.isFinite(ch.change) ? `${ch.change >= 0 ? "+" : ""}${ch.change.toFixed(1)} ${ch.unit}` : "a sign change";
    return text(`s5-investigate-${ch.metric}-${ch.year}`, 5, 5, "operational_vs_accounting", `${ctx.name}'s ${M.short(ch.metric)} moved ${changeTxt} in ${ch.year}. Is the change operational or accounting-driven, recurring or one-off — and exactly where in the annual report would you verify it?`, model);
  }
  return text("s5-investigate-generic", 5, 5, "operational_vs_accounting", "Pick the largest change in your dataset. Operational or accounting-driven? Recurring or one-off? Where would you verify it?", "Name the driver, classify it, and cite the specific note or statement that proves it.");
});

// ---------------------------------------------------------------- Stage 6
T("s6-nonrec", 6, 1, ["one_off_items"], (ctx, rng) => mc("s6-nonrec", 6, 1, "one_off_items", "Which item is most likely non-recurring?", "Gain on the sale of a subsidiary", ["Net interest income", "Recurring asset-management fees", "Personnel expenses"], rng, "Disposal gains, negative goodwill, litigation settlements and restructuring charges are typical one-offs."));
T("s6-underlying", 6, 2, ["underlying_earnings"], (ctx, rng) => {
  const y = latestWith(ctx.values, ["net_income"]);
  let ni = y !== null ? val(ctx.values, "net_income", y) : 1000;
  ni = ni && ni > 0 ? ni : 1000;
  const gain = Math.round(Math.abs(ni) * rng.choice([0.1, 0.15, 0.2]));
  const tax = rng.choice([0.15, 0.2, 0.25]);
  const ans = ni - gain * (1 - tax);
  return num(`s6-underlying-${gain}`, 6, 2, "underlying_earnings", `Suppose ${ctx.name}'s reported net income of ${money(ni, ctx.currency)} includes a one-off pre-tax gain of ${money(gain, ctx.currency)}, taxed at ${(tax * 100).toFixed(0)} %. What is underlying net income (${ctx.currency} m)?`, ans, `${ctx.currency} m`, `Underlying = ${C.fmtNum(ni)} − ${C.fmtNum(gain)} × (1 − ${tax.toFixed(2)}) = ${C.fmtNum(ans)}. Remove one-offs after tax.`, 0.005, 1);
});
T("s6-reserves", 6, 3, ["reserves"], (ctx, rng) =>
  ctx.sector === "insurer"
    ? mc("s6-reserves-ins", 6, 3, "reserves", "An insurer's profit rises mainly because it released reserves set aside for prior-year claims. How should you view that profit?", "Lower quality — it depends on past estimates being too cautious and cannot be relied on to recur", ["Higher quality — it is cash income", "Neutral — reserves have no effect on profit", "It means the insurer wrote more business"], rng, "Prior-year reserve development changes earnings without new business; repeated releases can also signal earlier over-reserving used for smoothing.")
    : mc("s6-reserves-bank", 6, 3, "reserves", "A bank's profit rises because it released credit-loss allowances (a negative credit loss expense). How should you view that profit?", "Lower quality — the release cannot recur indefinitely and depends on management's model assumptions", ["Higher quality — releases are recurring", "Neutral — allowances never affect profit", "It means loans grew faster"], rng));
T("s6-accruals", 6, 4, ["accruals"], (ctx) => {
  for (const y of years(ctx.values).reverse()) {
    const ni = val(ctx.values, "net_income", y), ocf = val(ctx.values, "operating_cash_flow", y), a0 = val(ctx.values, "total_assets", y - 1), a1 = val(ctx.values, "total_assets", y);
    if ([ni, ocf, a0, a1].every((x) => x !== null)) {
      const ans = ((ni - ocf) / ((a0 + a1) / 2)) * 100;
      const note = ctx.sector === "bank" ? " For a bank this number says little — OCF is driven by balance-sheet flows." : "";
      return num(`s6-accr-${y}`, 6, 4, "accruals", `${ctx.name} ${y}: net income ${money(ni, ctx.currency)}, operating cash flow ${money(ocf, ctx.currency)}, total assets ${money(a0, ctx.currency)} (opening) and ${money(a1, ctx.currency)} (closing). Calculate the cash-flow accrual ratio (%).`, ans, "%", `(NI − OCF) ÷ average assets = (${C.fmtNum(ni)} − ${C.fmtNum(ocf)}) ÷ ${C.fmtNum((a0 + a1) / 2)} = ${ans.toFixed(3)} %.${note}`, 0.02, 0.02);
    }
  }
  return num("s6-accr-generic", 6, 4, "accruals", "NI 500, OCF 200, average assets 10'000. Accrual ratio (%)?", 3.0, "%", "(500 − 200) ÷ 10'000 = 3 %.");
});
T("s6-judge", 6, 5, ["quality_earnings"], (ctx) => text("s6-judge", 6, 5, "quality_earnings", `Rate the quality of ${ctx.name}'s latest earnings (high / medium / low) and justify it with two pieces of evidence from your analysis.`, ctx.sector === "bank" ? "For a bank look at: share of recurring fees vs trading, credit-loss charges vs through-the-cycle levels, one-offs (negative goodwill, litigation, restructuring), tax effects (DTA recognition), and whether profit converts into CET1 capital and distributions." : "For an insurer look at: reserve releases, catastrophe losses vs budget, realised investment gains, IFRS 17 effects (CSM release, assumption changes), tax effects, and whether profit converts into solvency capital and cash remittances/dividends."));

// ---------------------------------------------------------------- Stage 7
T("s7-capital", 7, 1, ["regulatory_capital"], (ctx, rng) =>
  ctx.sector === "bank"
    ? mc("s7-cet1", 7, 1, "regulatory_capital", "What does a bank's CET1 ratio primarily protect against?", "Unexpected losses that would otherwise make the bank insolvent", ["Daily cash outflows (liquidity)", "Rising cost/income ratios", "Currency translation differences"], rng, "CET1 is loss-absorbing equity relative to risk-weighted assets — a solvency measure. Liquidity is covered by LCR/NSFR.")
    : mc("s7-solv", 7, 1, "regulatory_capital", "An insurer reports a solvency ratio of 180 %. What does it mean?", "Available capital is 1.8× the regulatory required capital", ["The insurer can pay 180 % of its claims", "Assets are 180 % of liabilities", "Profit is 180 % of premiums"], rng));
T("s7-shock", 7, 2, ["capital_shock"], (ctx, rng) => {
  if (ctx.sector === "bank") {
    const y = latestWith(ctx.values, ["cet1_capital", "rwa"]);
    let c1 = 1500, rwa = 10000, loss = 300;
    if (y !== null) {
      c1 = val(ctx.values, "cet1_capital", y);
      rwa = val(ctx.values, "rwa", y);
      loss = Math.round(c1 * rng.choice([0.1, 0.15]));
    }
    const ans = ((c1 - loss) / rwa) * 100;
    return num(`s7-shock-${loss}`, 7, 2, "capital_shock", `CET1 capital is ${C.fmtNum(c1)} and RWA ${C.fmtNum(rwa)} (${ctx.currency} m). An after-tax loss of ${C.fmtNum(loss)} hits CET1 (RWA unchanged). What is the new CET1 ratio (%)?`, ans, "%", `(${C.fmtNum(c1)} − ${C.fmtNum(loss)}) ÷ ${C.fmtNum(rwa)} = ${ans.toFixed(2)} % (before: ${((c1 / rwa) * 100).toFixed(2)} %).`, 0.02, 0.05);
  }
  const [avail, req] = rng.choice([[18000, 9000], [5000, 2500], [900, 450]]);
  const shock = Math.round(avail * 0.15);
  const ans = ((avail - shock) / req) * 100;
  return num(`s7-shock-ins-${avail}`, 7, 2, "capital_shock", `An insurer has available capital of ${C.fmtNum(avail)} and required capital of ${C.fmtNum(req)}. A market shock reduces available capital by ${C.fmtNum(shock)} (required unchanged). New solvency ratio (%)?`, ans, "%", `(${C.fmtNum(avail)} − ${C.fmtNum(shock)}) ÷ ${C.fmtNum(req)} = ${ans.toFixed(1)} % (before: ${((avail / req) * 100).toFixed(0)} %).`);
});
T("s7-rates", 7, 3, ["risk_interest"], (ctx, rng) =>
  ctx.sector === "bank"
    ? mc("s7-rates-bank", 7, 3, "risk_interest", "A deposit-rich Swiss bank sees the SNB cut its policy rate to 0 %. What is the most likely effect?", "Net interest income falls because deposit margins shrink (deposit rates cannot go much below zero)", ["Net interest income rises because funding is cheaper", "Fee income falls to zero", "RWA double"], rng)
    : mc("s7-rates-ins", 7, 3, "risk_interest", "A life insurer has long-dated guaranteed savings products. Which interest-rate scenario hurts it most?", "Persistently low or falling rates — reinvestment yields fall below the guaranteed rates", ["Rising rates — it can reinvest at higher yields", "Rates do not matter for life insurers", "Only a flat yield curve at 5 %"], rng));
T("s7-market", 7, 4, ["risk_market"], (ctx, rng) => mc("s7-market", 7, 4, "risk_market", `Equity markets fall 15 %. Through which statements does this reach ${ctx.name}?`, "Income statement (lower asset-based fees / investment results) and balance sheet / capital (lower asset values, solvency or CET1)", ["Only the cash flow statement", "Only the notes", "Nowhere — market risk is borne entirely by clients"], rng, "Market risk reaches earnings via fees and investment income and reaches capital via valuations — connect both statements."));
T("s7-prioritise", 7, 5, ["risk_prioritisation"], (ctx) => text("s7-prioritise", 7, 5, "risk_prioritisation", `Take your top three risks for ${ctx.name}. For each, say whether it affects value mainly through future earnings (ROE), through capital (book value, payouts) or through the cost of equity — and what early-warning indicator you would track.`, "E.g. regulatory capital rules → capital/ROE (track draft rules, CET1 target); market downturn → earnings via fees (track AuM, net new money); catastrophe/reserve risk → earnings and capital (track nat cat losses vs budget, prior-year development); interest rates → NII or spread (track rate sensitivity disclosures). Risks that raise uncertainty also raise the cost of equity."));

// ---------------------------------------------------------------- Stage 8
T("s8-ratios", 8, 1, ["peers"], (ctx, rng) => mc("s8-ratios", 8, 1, "peers", "Why compare UBS and LLB on ratios (ROE, cost/income, CET1 ratio) rather than on absolute figures like net income?", "They differ hugely in size and report in different currencies (USD vs CHF) — ratios normalise for scale and currency", ["Absolute figures are not audited", "Ratios are always higher", "Net income is not comparable between any two banks"], rng));
T("s8-gap", 8, 2, ["roe"], (ctx) => {
  if (ctx.peerValues && ctx.peerProfile) {
    const rd = R.RATIOS.roe;
    for (const y of years(ctx.values).reverse()) {
      const a = R.compute(rd, ctx.values, y);
      const b = ctx.peerValues.years.includes(y) ? R.compute(rd, ctx.peerValues, y) : null;
      if (a.value !== null && b && b.value !== null) {
        const ans = a.value - b.value;
        return num(`s8-gap-${y}`, 8, 2, "roe", `${y}: ${ctx.name} net income ${money(a.required[0].value, ctx.currency)}, average equity ${money((a.required[1].value + a.required[2].value) / 2, ctx.currency)}; ${ctx.peerProfile.short_name} net income ${C.fmtNum(b.required[0].value)}, average equity ${C.fmtNum((b.required[1].value + b.required[2].value) / 2)} (${ctx.peerProfile.currency} m). By how many percentage points does ${ctx.name}'s ROE exceed the peer's? (Negative if lower.)`, ans, "pp", `${a.value.toFixed(2)} % − ${b.value.toFixed(2)} % = ${ans >= 0 ? "+" : ""}${ans.toFixed(2)} pp. Currencies cancel out in a ratio.`, 0.02, 0.1);
      }
    }
  }
  return num("s8-gap-generic", 8, 2, "roe", "Bank A: NI 900, average equity 7'500. Bank B: NI 160, average equity 2'200. ROE difference A − B (pp)?", (900 / 7500) * 100 - (160 / 2200) * 100, "pp", "12.00 % − 7.27 % = 4.73 pp.", 0.02, 0.1);
});
T("s8-pbroe", 8, 3, ["justified_pb"], (ctx, rng) => mc("s8-pbroe", 8, 3, "justified_pb", "Bank A: ROE 14 %, P/B 1.8. Bank B: ROE 6 %, P/B 0.7. Cost of equity ≈ 10 % for both. Is this pattern consistent?", "Yes — the market pays above book only for banks expected to earn more than their cost of equity", ["No — P/B should be the same for all banks", "No — the lower-ROE bank should trade at a higher P/B", "It is random"], rng));
T("s8-capital", 8, 4, ["leverage"], (ctx, rng) => mc("s8-capital", 8, 4, "leverage", "Your peer shows a higher ROE but a lower CET1 ratio and higher leverage. What must you check before concluding it is 'better'?", "Whether its higher ROE comes from leverage (less capital per unit of risk) rather than better profitability — compare ROA and risk-adjusted returns", ["Nothing — higher ROE is always better", "Only the dividend yield", "Whether it has more employees"], rng));
T("s8-select", 8, 5, ["peer_selection"], () => text("s8-select", 8, 5, "peer_selection", "Is the peer you selected truly comparable? Name two differences (business model, accounting, currency, size, regulation) that limit the comparison, and how you adjusted for them.", "E.g. UBS vs LLB: global vs regional, USD vs CHF, investment bank exposure, TBTF regime vs EEA rules. Swiss Life vs Swiss Re: life/pensions vs reinsurance, CHF vs USD, different risk drivers (rates vs catastrophes). Roche vs Novartis: diagnostics plus pharma vs pure pharma, CHF vs USD, different patent cliffs and 'core' definitions. GKB vs LLB: Swiss bank GAAP vs IFRS, cantonal guarantee. Compare ratios, index trends to 100, compare within the same accounting basis and acknowledge the residual differences."));

// ---------------------------------------------------------------- Stage 9
T("s9-method", 9, 1, ["valuation_methods"], (ctx, rng) => mc("s9-method", 9, 1, "valuation_methods", "Which valuation approach is generally LEAST appropriate for a bank?", "A free-cash-flow-to-the-firm (FCFF) DCF", ["Price-to-book vs ROE", "A dividend discount model", "A residual income model"], rng, "For banks debt is raw material (deposits), not financing; operating cash flow is not meaningful — so FCFF breaks down."));
T("s9-profile", 9, 1, ["valuation_methods"], (ctx, rng) => {
  for (const lvl of [3, 1, 2]) {
    const q = profileQuestion(ctx, 9, lvl, rng);
    if (q) return { ...q, level: 1 };
  }
  return null;
});
T("s9-jpb", 9, 2, ["justified_pb"], (ctx, rng) => {
  const [roe, r, g] = rng.choice([[0.12, 0.09, 0.02], [0.08, 0.1, 0.02], [0.15, 0.1, 0.03], [0.1, 0.085, 0.015]]);
  const ans = V.justifiedPB(roe, r, g);
  return num(`s9-jpb-${roe}-${r}`, 9, 2, "justified_pb", `Sustainable ROE ${(roe * 100).toFixed(1)} %, cost of equity ${(r * 100).toFixed(1)} %, long-run growth ${(g * 100).toFixed(1)} %. Justified P/B (×)?`, ans, "×", `(ROE − g) ÷ (r − g) = (${roe.toFixed(3)} − ${g.toFixed(3)}) ÷ (${r.toFixed(3)} − ${g.toFixed(3)}) = ${ans.toFixed(2)}×.`, 0.02, 0.02);
});
T("s9-pb-below", 9, 3, ["justified_pb"], (ctx, rng) => mc("s9-pb-below", 9, 3, "justified_pb", "A bank trades at 0.7× book value. What is the market implicitly saying?", "It expects the bank to earn an ROE below its cost of equity (or doubts the book value)", ["The bank is certainly cheap and will rise", "The bank has no debt", "The dividend yield must be zero"], rng, "Implied ROE = g + P/B × (r − g). P/B < 1 ⇒ implied ROE < r. Whether that is too pessimistic is your analysis — not a buy signal."));
T("s9-ddm", 9, 4, ["ddm"], (ctx, rng) => {
  const y = latestWith(ctx.values, ["dps"]);
  let d0 = y !== null ? val(ctx.values, "dps", y) : null;
  d0 = d0 && d0 > 0 ? d0 : 2.5;
  const [r, g] = rng.choice([[0.08, 0.03], [0.09, 0.025], [0.075, 0.02]]);
  const ans = V.gordonDDM(d0, r, g);
  return num(`s9-ddm-${r}-${g}`, 9, 4, "ddm", `Last dividend D₀ = ${ctx.currency} ${f2(d0)}. Dividends grow ${(g * 100).toFixed(1)} % forever; cost of equity ${(r * 100).toFixed(1)} %. Gordon growth value per share?`, ans, ctx.currency, `V₀ = D₀ × (1 + g) ÷ (r − g) = ${f2(d0)} × ${(1 + g).toFixed(3)} ÷ ${(r - g).toFixed(3)} = ${f2(ans)}. Note how sensitive it is to r − g.`, 0.01, 0.1);
});
T("s9-why", 9, 5, ["valuation_methods"], (ctx) => text("s9-why", 9, 5, "valuation_methods", `Why might a P/B–ROE or dividend/capital-generation approach be more informative than a traditional FCFF DCF for ${ctx.name}?`, "Because for financials the balance sheet is the business: deposits/insurance liabilities are operating items, not financing; cash flow statements do not measure distributable cash; regulators cap distributions via capital requirements. Value therefore depends on sustainable ROE vs cost of equity (P/B) and on how much capital can be distributed after meeting capital targets (DDM / excess capital). DCF only works if you redefine FCFE as distributable capital."));

// ---------------------------------------------------------------- Stage 10
T("s10-breaker", 10, 1, ["thesis"], (ctx, rng) => mc("s10-breaker", 10, 1, "thesis", "What is a 'thesis breaker'?", "A specific, observable development that would prove your investment thesis wrong", ["The target price", "A broker's recommendation", "The last dividend payment"], rng));
T("s10-ev", 10, 2, ["scenario_analysis"], (ctx, rng) => {
  const [bear, base, bull] = rng.choice([[60, 90, 120], [20, 30, 42], [400, 560, 700]]);
  const p = rng.choice([[0.25, 0.5, 0.25], [0.3, 0.5, 0.2], [0.2, 0.6, 0.2]]);
  const ans = bear * p[0] + base * p[1] + bull * p[2];
  const pc = (x) => `${Math.round(x * 100)}%`;
  return num(`s10-ev-${bear}-${p[0]}`, 10, 2, "scenario_analysis", `Bear ${bear} (probability ${pc(p[0])}), base ${base} (${pc(p[1])}), bull ${bull} (${pc(p[2])}). Probability-weighted value?`, ans, "", `${bear}×${p[0]} + ${base}×${p[1]} + ${bull}×${p[2]} = ${ans.toFixed(1)}.`, 0.02, 0.1);
});
T("s10-portfolio", 10, 3, ["portfolio"], (ctx, rng) => mc("s10-portfolio", 10, 3, "portfolio", "Before allocating money to any single stock, which consideration is about YOU rather than the company?", "Your risk tolerance, time horizon, existing exposures and diversification", ["The CET1 ratio", "The combined ratio", "The auditor's opinion"], rng));
T("s10-growth", 10, 4, ["sustainable_growth"], (ctx, rng) => {
  const [roe, payout] = rng.choice([[0.12, 0.6], [0.1, 0.5], [0.15, 0.7]]);
  const ans = V.sustainableGrowth(roe, payout) * 100;
  return num(`s10-g-${roe}-${payout}`, 10, 4, "sustainable_growth", `ROE ${(roe * 100).toFixed(0)} %, payout ratio ${(payout * 100).toFixed(0)} %. Sustainable growth rate (%)?`, ans, "%", `g = (1 − payout) × ROE = ${(1 - payout).toFixed(2)} × ${(roe * 100).toFixed(0)} % = ${ans.toFixed(1)} %. It links the income statement (ROE), dividend policy and balance-sheet growth.`);
});
T("s10-final", 10, 5, ["thesis"], (ctx) => text("s10-final", 10, 5, "thesis", `Write the one sentence that would make you abandon your thesis on ${ctx.name}, including the number and the time frame.`, "A good thesis breaker is specific and measurable, e.g. 'If the CET1 ratio target rises above X % and buybacks stop in 2026', 'If net new money is negative for two consecutive years', 'If sales of the top three brands fall more than 15 % in 2026 after generic entry' or 'If net debt ÷ EBITDA exceeds 3× after acquisitions'."));


// ---------------------------------------------------------------- non-financial companies
// Same questions as the `ctx.sector == "corporate"` branches in lab/questions.py, swapped in per template.
const CORP = {
  "s1-revenue-line": { build: (ctx, rng) => mc("s1-revenue-line-corp", 1, 1, "revenue_lines", "Which income-statement line shows the profit from a company's operations before interest and taxes?", "Operating result / EBIT (Betriebsergebnis)", ["Net income", "Gross profit", "Operating cash flow"], rng, "EBIT = sales − operating costs (cost of goods sold, R&D, selling, administration). Gross profit comes before operating costs, net income after interest and tax; cash flow is a different statement.") },
  "s1-revenue-mix": {
    concepts: ["cost_structure"],
    build: (ctx, rng) => {
      let y = latestWith(ctx.values, ["rnd_expense", "revenue"]);
      if (y !== null) {
        const rnd = val(ctx.values, "rnd_expense", y), rev = val(ctx.values, "revenue", y);
        return num(`s1-rnd-${y}`, 1, 2, "cost_structure", `${ctx.name} ${y}: R&D expense ${money(rnd, ctx.currency)}, revenue ${money(rev, ctx.currency)}. What share of revenue goes into research and development (%)?`, (rnd / rev) * 100, "%", `R&D intensity = ${C.fmtNum(rnd)} ÷ ${C.fmtNum(rev)} = ${((rnd / rev) * 100).toFixed(1)} %. Big pharma reinvests about 18–25 % of sales, industrials about 3–8 %.`);
      }
      y = latestWith(ctx.values, ["ebit", "revenue"]);
      if (y !== null) {
        const ebit = val(ctx.values, "ebit", y), rev = val(ctx.values, "revenue", y);
        return num(`s1-ebitm-${y}`, 1, 2, "cost_structure", `${ctx.name} ${y}: operating result (EBIT) ${money(ebit, ctx.currency)}, revenue ${money(rev, ctx.currency)}. What share of revenue is left as operating profit (EBIT margin, %)?`, (ebit / rev) * 100, "%", `EBIT margin = ${C.fmtNum(ebit)} ÷ ${C.fmtNum(rev)} = ${((ebit / rev) * 100).toFixed(1)} %. Everything else went into production, R&D, selling and administration.`);
      }
      const [rnd, rev] = rng.choice([[13000, 60000], [450, 6300], [9000, 45000]]);
      return num("s1-rnd-generic", 1, 2, "cost_structure", `A company spends ${C.fmtNum(rnd)} on R&D with sales of ${C.fmtNum(rev)}. R&D intensity (%)?`, (rnd / rev) * 100, "%", `${C.fmtNum(rnd)} ÷ ${C.fmtNum(rev)} = ${((rnd / rev) * 100).toFixed(1)} %.`);
    },
  },
  "s1-interpret": {
    build: (ctx, rng) => {
      const q = profileQuestion(ctx, 1, 3, rng);
      if (q) return q;
      const y = latestWith(ctx.values, ["rnd_expense", "revenue"]);
      const pharma = (ctx.profile.subsector || "").toLowerCase().includes("pharma") || (y !== null && val(ctx.values, "rnd_expense", y) / val(ctx.values, "revenue", y) > 0.1);
      return pharma
        ? mc("s1-interpret-pharma", 1, 3, "business_model", "A blockbuster drug loses its US patent protection. What typically happens to its US sales?", "They fall sharply within one to two years as generics or biosimilars launch at much lower prices", ["They stay stable because doctors are loyal to the brand", "They rise because more patients can afford it", "Nothing changes until the European patent expires"], rng, "Loss of exclusivity can erase 50–90 % of a brand's sales; erosion is slower for biologics than for small molecules, but still large.")
        : mc("s1-interpret-cyclical", 1, 3, "business_model", "A tool maker with a large direct sales force sees sales fall 5 % in a construction downturn. Why can its operating profit fall much more?", "Many costs are fixed (sales force, R&D, plants), so lower sales hit profit disproportionately — operating leverage", ["Because taxes rise when sales fall", "Because depreciation rises with sales", "It cannot — profit always falls in proportion to sales"], rng, "With high fixed costs, a small change in sales causes a large change in operating profit — in both directions.");
    },
  },
  "s1-link": { build: (ctx, rng) => mc("s1-link-corp", 1, 4, "linking_statements", "A company grows sales 10 %, but customers pay more slowly and it builds up inventories. What happens to net income and operating cash flow?", "Net income rises with sales, but operating cash flow lags because working capital absorbs cash", ["Both rise by exactly 10 %", "Operating cash flow rises faster than net income", "Net income falls because inventories are expensed immediately"], rng, "Receivables and inventories are balance-sheet assets: building them up uses cash that the income statement does not show.") },
  "s1-moat": {
    build: (ctx) => {
      const ref = ctx.profile.business_reference?.advantages?.reference || "";
      return text("s1-moat", 1, 5, "competitive_advantage", `Choose the competitive advantage of ${ctx.name} you think is most durable. Which numbers in the annual report, tracked over several years, would show you that it is eroding?`, `Reference advantages: ${ref} Evidence of erosion — For a non-financial company: falling gross or operating margins, loss of market share, rising discounts or rebates, R&D spending that no longer produces launches, a shrinking share of recurring revenue. A good answer names one specific advantage, the metric that measures it, and the direction that would worry you.`);
    },
  },
  "s3-reverse": { build: (ctx) => text("s3-reverse", 3, 5, "trend_interpretation", `Which trend you analysed for ${ctx.name} is most likely to reverse in the next two years? Explain the mechanism, not just the direction.`, "Non-financials: sales of a product nearing patent expiry, margins helped by temporary pricing or cheap inputs, currency effects that reverse, one-off gains (disposals, spin-offs) dropping out, EPS growth driven by debt-funded buybacks. A strong answer names the metric, the driver behind the past trend, why that driver changes, and which number you would monitor.") },
  "s4-identify": {
    build: (ctx, rng) => {
      const choices = [["Net income ÷ average shareholders' equity", "Return on equity (ROE)"], ["EBIT ÷ revenue", "EBIT margin (operating margin)"], ["(Financial debt − cash) ÷ EBITDA", "Net debt ÷ EBITDA"], ["Operating cash flow ÷ net income", "Cash conversion"], ["Dividend per share ÷ EPS", "Payout ratio"]];
      const [formula, correct] = rng.choice(choices);
      return mc(`s4-identify-${correct.slice(0, 10)}`, 4, 1, "ratio_definitions", `Which ratio is defined as: ${formula}?`, correct, choices.map((c) => c[1]).filter((c) => c !== correct).slice(0, 3), rng);
    },
  },
  "s4-dupont-interpret": { build: (ctx, rng) => mc("s4-dupont-int-corp", 4, 3, "dupont", "A company's ROE rose from 15 % to 20 % while its ROA stayed unchanged. What explains the increase?", "Higher financial leverage — for example debt-funded buybacks shrank equity", ["A higher EBIT margin", "Faster asset turnover", "A higher dividend payout"], rng, "ROE = ROA × leverage. If ROA is flat, leverage must have risen — ROE improved without the business becoming more profitable.") },
  "s4-value": { build: (ctx) => text("s4-value-corp", 4, 5, "roe_vs_cost_of_equity", `Compare ${ctx.name}'s latest ROE and ROCE with a cost of equity of roughly 7–8 % (WACC about 6–7 %). Is it creating value for shareholders? Name three levers management could pull to raise returns — and the risk each lever brings.`, "Value is created when returns exceed the cost of capital (ROCE above the pre-tax WACC, ROE above the cost of equity). Levers: (1) pricing and mix (higher gross margin) — competition and price-regulation risk; (2) cost efficiency (lower R&D or selling costs as % of sales) — risk of under-investing in innovation; (3) asset efficiency (less working capital, higher asset turnover) — supply risk; (4) leverage and buybacks — financial risk and rating pressure. Adjust ROE for one-offs and for buyback-shrunk equity before judging.") },
  "s5-bank-cf": { concepts: ["cash_conversion"], build: (ctx, rng) => mc("s5-corp-cf", 5, 4, "cash_conversion", "A company's net income rose for two years while its operating cash flow fell. What should you check first?", "Working capital — receivables and inventories growing faster than sales (aggressive revenue recognition or weak demand)", ["Nothing — cash flow and profit are unrelated", "Whether the dividend was raised", "Whether depreciation fell"], rng, "Rising profit with falling cash is the classic accrual warning sign. Check the change in working capital in the cash flow statement and days sales outstanding.") },
  "s6-nonrec": { build: (ctx, rng) => mc("s6-nonrec", 6, 1, "one_off_items", "Which item is most likely non-recurring?", "Gain on the sale of a subsidiary", ["Sales of the main product line", "Recurring service fees", "Personnel expenses"], rng, "Disposal gains, negative goodwill, litigation settlements and restructuring charges are typical one-offs.") },
  "s6-reserves": { build: (ctx, rng) => mc("s6-reserves-corp", 6, 3, "reserves", "A company's operating profit rises mainly because it released a litigation provision booked in earlier years. How should you view that profit?", "Lower quality — the release is non-recurring and depends on management's earlier estimate", ["Higher quality — it is cash income", "Neutral — provisions never affect profit", "It shows that sales grew"], rng, "Provision releases go through the income statement without new business; repeated releases can mean earlier over-provisioning used to smooth profit.") },
  "s6-accruals": {
    build: (ctx, rng, base) => {
      const q = base(ctx, rng);
      return q && q.id !== "s6-accr-generic" ? { ...q, explanation: `${q.explanation} For a non-financial company this is a key quality signal — large positive accruals mean profit is running ahead of cash.` } : q;
    },
  },
  "s6-judge": { build: (ctx) => text("s6-judge", 6, 5, "quality_earnings", `Rate the quality of ${ctx.name}'s latest earnings (high / medium / low) and justify it with two pieces of evidence from your analysis.`, "For a non-financial company look at: cash conversion (operating cash flow vs net income) over several years, working-capital trends (receivables and inventories vs sales), capitalised costs (development, software), impairments and 'core'/'adjusted' exclusions that recur every year, one-off gains (disposals, spin-offs), tax effects, and whether free cash flow covers dividends and buybacks.") },
  "s7-capital": { concepts: ["debt_capacity"], build: (ctx, rng) => mc("s7-debt", 7, 1, "debt_capacity", "Which ratio do credit analysts look at first to judge whether a non-financial company can carry its debt?", "Net debt ÷ EBITDA", ["Price-to-book", "CET1 ratio", "Combined ratio"], rng, "Net debt ÷ EBITDA ≈ years of operating cash earnings needed to repay debt; interest cover (EBIT ÷ interest) complements it. CET1 and the combined ratio belong to banks and insurers.") },
  "s7-shock": {
    concepts: ["debt_capacity"],
    build: (ctx, rng) => {
      let y = latestWith(ctx.values, ["total_debt", "cash", "ebit", "depreciation_amortisation"]);
      let nd = null, ebitda = null;
      if (y !== null) {
        nd = val(ctx.values, "total_debt", y) - val(ctx.values, "cash", y);
        ebitda = val(ctx.values, "ebit", y) + val(ctx.values, "depreciation_amortisation", y);
      }
      if (!nd || nd <= 0 || !ebitda || ebitda <= 0) [nd, ebitda, y] = [6000, 3000, null];
      const drop = rng.choice([20, 25, 30]);
      const ans = nd / (ebitda * (1 - drop / 100));
      const intro = y !== null ? `${ctx.name} ${y}: net debt ${money(nd, ctx.currency)} and EBITDA ${money(ebitda, ctx.currency)}.` : `Net debt is ${C.fmtNum(nd)} and EBITDA ${C.fmtNum(ebitda)}.`;
      return num(`s7-lev-${drop}`, 7, 2, "debt_capacity", `${intro} In a downturn EBITDA falls by ${drop} % while net debt stays the same. What is net debt ÷ EBITDA afterwards (×)?`, ans, "×", `${C.fmtNum(nd)} ÷ (${C.fmtNum(ebitda)} × ${(1 - drop / 100).toFixed(2)}) = ${f2(ans)}× (before: ${f2(nd / ebitda)}×). Leverage ratios worsen in downturns even without new debt.`, 0.02, 0.02);
    },
  },
  "s7-rates": { concepts: ["risk_currency"], build: (ctx, rng) => mc("s7-fx", 7, 3, "risk_currency", "A Swiss company sells 90 % of its products abroad but has most of its costs in Switzerland. The franc strengthens 10 %. What happens?", "Reported sales and margins fall: foreign sales translate into fewer francs while Swiss costs stay the same", ["Nothing — currency effects cancel out", "Margins rise because imports become cheaper", "Only the balance sheet is affected"], rng, "That is transaction exposure (revenues and costs in different currencies) — it changes margins. Translation exposure only changes reported figures. Compare growth in local currencies with growth in CHF.") },
  "s7-market": { concepts: ["risk_demand"], build: (ctx, rng) => mc("s7-demand", 7, 4, "risk_demand", `Demand in ${ctx.name}'s main market falls 15 % in a downturn. Through which statements does this reach the company?`, "Income statement (lower sales; profit falls faster because of fixed costs) and cash flow / balance sheet (inventories pile up, possible impairments, higher net debt ÷ EBITDA)", ["Only the income statement — the balance sheet is unaffected", "Only the cash flow statement", "Nowhere — customers bear the risk"], rng, "Demand risk reaches profit through operating leverage and reaches the balance sheet through working capital, impairments and leverage ratios.") },
  "s7-prioritise": { build: (ctx) => text("s7-prioritise", 7, 5, "risk_prioritisation", `Take your top three risks for ${ctx.name}. For each, say whether it affects value mainly through future earnings (ROE), through capital (book value, payouts) or through the cost of equity — and what early-warning indicator you would track.`, "E.g. patent expiry → earnings (track the product's sales, generic launches, pipeline approvals); drug-pricing reform → earnings and cost of equity (track legislation and price negotiations); currency → earnings (track growth in local currencies vs CHF); construction cycle → earnings and cash (track order intake, inventories); leverage after acquisitions → capital and cost of equity (track net debt ÷ EBITDA, rating). Risks that raise uncertainty also raise the cost of equity.") },
  "s8-ratios": { build: (ctx, rng) => mc("s8-ratios-corp", 8, 1, "peers", `Why compare ${ctx.name} with its peers on margins, ROE and net debt ÷ EBITDA rather than on absolute profit?`, "Companies differ in size and reporting currency (e.g. Roche in CHF, Novartis in USD) — ratios normalise for scale and currency", ["Absolute figures are not audited", "Ratios are always higher", "Net income is never comparable between companies"], rng) },
  "s8-pbroe": { concepts: ["ev_multiples"], build: (ctx, rng) => mc("s8-ev", 8, 3, "ev_multiples", "Company A: EBIT margin 30 %, sales growth 6 %, EV/EBITDA 14×. Company B: EBIT margin 12 %, growth 2 %, EV/EBITDA 8×. Is this pattern consistent?", "Yes — higher margins, growth and returns justify a higher multiple of the same earnings", ["No — all companies should trade on the same multiple", "No — the slower-growing company should trade higher", "It is random"], rng, "Multiples price expected growth, profitability and risk. A low multiple is not 'cheap' unless the market misjudges those drivers.") },
  "s8-capital": { build: (ctx, rng) => mc("s8-capital-corp", 8, 4, "leverage", "Your peer shows a higher ROE but much higher net debt ÷ EBITDA after years of debt-funded buybacks. What must you check before concluding it is 'better'?", "Whether its ROE is inflated by a small equity base — compare ROCE, margins and leverage", ["Nothing — higher ROE is always better", "Only the dividend yield", "Whether it has more employees"], rng) },
  "s9-method": { build: (ctx, rng) => mc("s9-method-corp", 9, 1, "valuation_methods", "Which valuation approach is generally LEAST informative for a pharma or industrial company?", "Price-to-book vs ROE — book value leaves out internally developed intangibles and shrinks with buybacks", ["A free-cash-flow (FCFF) DCF at the WACC", "EV/EBITDA versus peers", "P/E on normalised earnings"], rng, "Patents, brands and know-how built in-house are not on the balance sheet, so book value understates the asset base; cash-flow and earnings methods capture them.") },
  "s9-jpb": {
    concepts: ["ev_multiples"],
    build: (ctx, rng) => {
      const m = rng.choice([8, 10, 12, 14]);
      const y = latestWith(ctx.values, ["ebit", "depreciation_amortisation", "total_debt", "cash", "shares_outstanding"]);
      if (y !== null && ctx.profile.listed) {
        const ebitda = val(ctx.values, "ebit", y) + val(ctx.values, "depreciation_amortisation", y);
        const nd = val(ctx.values, "total_debt", y) - val(ctx.values, "cash", y);
        const sh = val(ctx.values, "shares_outstanding", y);
        if (ebitda > 0 && sh) {
          const ans = (m * ebitda - nd) / sh;
          return num(`s9-ev-${y}-${m}`, 9, 2, "ev_multiples", `${ctx.name} ${y}: EBITDA ${money(ebitda, ctx.currency)}, net debt ${money(nd, ctx.currency)}, ${C.fmtNum(sh, 1)} m shares. Apply a peer EV/EBITDA of ${m}×. Equity value per share (${ctx.currency})?`, ans, ctx.currency, `EV = ${m} × ${C.fmtNum(ebitda)} = ${C.fmtNum(m * ebitda)}; equity = EV − net debt = ${C.fmtNum(m * ebitda - nd)}; per share = ÷ ${C.fmtNum(sh, 1)} = ${C.fmtNum(ans, 2)}.`, 0.01, 0.1);
        }
      }
      const [ebitda, nd, sh] = [2000, 3000, 100];
      const ans = (m * ebitda - nd) / sh;
      return num(`s9-ev-generic-${m}`, 9, 2, "ev_multiples", `EBITDA ${C.fmtNum(ebitda)}, net debt ${C.fmtNum(nd)}, ${sh} m shares, peer EV/EBITDA ${m}×. Equity value per share?`, ans, "", `(${m} × ${C.fmtNum(ebitda)} − ${C.fmtNum(nd)}) ÷ ${sh} = ${C.fmtNum(ans, 2)}.`, 0.01, 0.1);
    },
  },
  "s9-pb-below": { concepts: ["ev_multiples"], build: (ctx, rng) => mc("s9-ev-below", 9, 3, "ev_multiples", "A company trades at 6× EV/EBITDA while its peers trade at 12×. What is the market implicitly saying?", "It expects lower growth or margins, higher risk or hidden liabilities — or doubts the earnings", ["The company is certainly cheap and will rise", "The company has no debt", "Its dividend yield must be zero"], rng, "A low multiple is a hypothesis to test, not a buy signal: check growth, margins, leverage, one-offs in EBITDA and debt-like items (pensions, litigation).") },
  "s9-ddm": {
    concepts: ["dcf"],
    build: (ctx, rng) => {
      let y = latestWith(ctx.values, ["operating_cash_flow", "capex"]);
      let fcf = y !== null ? val(ctx.values, "operating_cash_flow", y) - val(ctx.values, "capex", y) : null;
      if (!fcf || fcf <= 0) [fcf, y] = [1000, null];
      const [w, g] = rng.choice([[0.075, 0.02], [0.08, 0.025], [0.07, 0.015]]);
      const ans = (fcf * (1 + g)) / (w - g);
      const intro = y !== null ? `${ctx.name} ${y}: free cash flow to the firm (operating cash flow − capex) ${money(fcf, ctx.currency)}.` : `Free cash flow to the firm last year was ${C.fmtNum(fcf)}.`;
      return num(`s9-fcff-${w}-${g}`, 9, 4, "dcf", `${intro} It grows ${(g * 100).toFixed(1)} % a year forever; the WACC is ${(w * 100).toFixed(1)} %. What is the enterprise value (${ctx.currency} m)?`, ans, `${ctx.currency} m`, `EV = FCFF₀ × (1 + g) ÷ (WACC − g) = ${C.fmtNum(fcf)} × ${(1 + g).toFixed(3)} ÷ ${(w - g).toFixed(3)} = ${C.fmtNum(ans)}. Subtract net debt to get equity value.`, 0.01, 0.1);
    },
  },
  "s9-why": { build: (ctx) => text("s9-why-corp", 9, 5, "valuation_methods", `Why is a free-cash-flow DCF at the WACC, cross-checked with EV/EBITDA, more informative than P/B for ${ctx.name}? Which two assumptions drive the DCF value most, and how would you sanity-check them?`, "For non-financials value comes from the cash the operating business generates for all capital providers; debt is financing, not raw material, so discounting FCFF at the WACC and deducting net debt is coherent. Book value omits internally built intangibles (patents, brands, know-how) and shrinks with buybacks, so P/B says little. The WACC and terminal growth dominate (the terminal value is often 60–80 % of enterprise value): sanity-check them against peers' multiples (the EV/EBITDA your DCF implies), long-run nominal GDP growth and the growth rate the market price implies.") },
};

for (const t of TEMPLATES) {
  const o = CORP[t.id];
  if (!o) continue;
  const base = t.build;
  t.build = (ctx, rng) => (ctx.sector === "corporate" ? o.build(ctx, rng, base) : base(ctx, rng));
  t.concepts = [...new Set([...t.concepts, ...(o.concepts || [])])];
}

// ------------------------------------------------------------------ grading

export function grade(q, response) {
  if (q.kind === "mc") return response !== null && response !== undefined && +response === +q.answer;
  if (q.kind === "numeric") {
    if (response === null || response === undefined || response === "") return false;
    const x = +response;
    return Number.isFinite(x) && C.isClose(x, +q.answer, q.relTol, q.absTol);
  }
  return null;
}

// ------------------------------------------------------------------ spaced repetition (Leitner)

const GAP_QUIZ = { 1: 1, 2: 2, 3: 4, 4: 8, 5: 16 };
const GAP_DAYS = { 1: 0, 2: 1, 3: 3, 4: 7, 5: 21 };

export function emptyLearner() {
  return { settings: { trainingMode: true }, concepts: {}, quizCounter: 0, history: [], customCompanies: [], reviewSession: null };
}

export function record(learner, concept, outcome) {
  const c = (learner.concepts[concept] ||= { box: 1, attempts: 0, correct: 0, wrong: 0, partial: 0 });
  c.attempts++;
  if (outcome === "correct") {
    c.correct++;
    c.box = Math.min(5, c.box + 1);
  } else if (outcome === "partial") c.partial = (c.partial || 0) + 1;
  else {
    c.wrong++;
    c.box = 1;
  }
  c.dueQuiz = (learner.quizCounter || 0) + GAP_QUIZ[c.box];
  c.dueDate = new Date(Date.now() + GAP_DAYS[c.box] * 86400000).toISOString();
  c.lastSeen = new Date().toISOString();
}

export function dueConcepts(learner, limit = null) {
  const now = Date.now();
  const counter = learner.quizCounter || 0;
  const due = [];
  for (const [concept, c] of Object.entries(learner.concepts || {})) {
    if ((c.wrong || 0) + (c.partial || 0) === 0 || (c.box || 1) >= 4) continue;
    const byQuiz = counter >= (c.dueQuiz || 0);
    const byDate = GAP_DAYS[c.box || 1] > 0 && c.dueDate && now >= Date.parse(c.dueDate);
    if (byQuiz || byDate) due.push([c.box || 1, -((c.wrong || 0) - (c.correct || 0)), concept]);
  }
  due.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2].localeCompare(b[2]));
  const out = due.map((d) => d[2]);
  return limit ? out.slice(0, limit) : out;
}

export function conceptTable(learner) {
  return Object.entries(learner.concepts || {})
    .map(([key, c]) => ({
      key,
      concept: conceptLabel(key),
      attempts: c.attempts || 0,
      correct: c.correct || 0,
      wrong: c.wrong || 0,
      accuracy: c.attempts ? ((c.correct || 0) / c.attempts) * 100 : null,
      box: c.box || 1,
      status: (c.box || 1) >= 4 ? "Mastered" : (c.wrong || 0) + (c.partial || 0) ? "Needs review" : "Learning",
    }))
    .sort((a, b) => a.box - b.box || b.wrong - a.wrong);
}

// ------------------------------------------------------------------ quiz builder

export const templatesForConcept = (concept, maxStage = null) => TEMPLATES.filter((t) => t.concepts.includes(concept) && (maxStage === null || t.stage <= maxStage));

function buildQuestion(t, ctx, rng) {
  try {
    return t.build(ctx, rng);
  } catch (e) {
    return null;
  }
}

export function buildQuiz(stage, ctx, learner, seed = Date.now(), nReview = 2) {
  const rng = makeRng(seed);
  const qs = {};
  for (let level = 1; level <= 5; level++) {
    const cands = rng.shuffle(TEMPLATES.filter((t) => t.stage === stage && t.level === level));
    cands.sort((a, b) => (a.id.includes("profile") ? 0 : 1) - (b.id.includes("profile") ? 0 : 1));
    for (const t of cands) {
      const q = buildQuestion(t, ctx, rng);
      if (q) {
        qs[level] = q;
        break;
      }
    }
  }
  const seen = new Set(Object.values(qs).map((q) => q.concept));
  const slots = [1, 2].filter((l) => qs[l]).slice(0, nReview);
  for (const concept of dueConcepts(learner)) {
    if (!slots.length) break;
    if (seen.has(concept)) continue;
    for (const t of templatesForConcept(concept).sort((a, b) => a.level - b.level)) {
      const q = buildQuestion(t, ctx, rng);
      if (q) {
        qs[slots.shift()] = { ...q, review: true };
        seen.add(concept);
        break;
      }
    }
  }
  return Object.keys(qs).map(Number).sort((a, b) => a - b).map((k) => qs[k]);
}

export function buildReview(ctx, learner, n = 5, seed = Date.now()) {
  const rng = makeRng(seed);
  const concepts = dueConcepts(learner);
  if (concepts.length < n) for (const row of conceptTable(learner)) if (!concepts.includes(row.key)) concepts.push(row.key);
  const out = [];
  for (const concept of concepts) {
    if (out.length >= n) break;
    for (const t of rng.shuffle(templatesForConcept(concept))) {
      const q = buildQuestion(t, ctx, rng);
      if (q) {
        out.push({ ...q, review: true });
        break;
      }
    }
  }
  return out;
}
