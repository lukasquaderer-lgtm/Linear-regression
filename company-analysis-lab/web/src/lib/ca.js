// Stage registry, gating and text-feedback helpers. Port of lab/company_analysis.py.

export const STAGES = [
  { n: 1, key: "business", en: "Understand the Business", de: "Geschäftsmodell verstehen", goal: "Explain what the company does and how it makes money — in your own words." },
  { n: 2, key: "data", en: "Collect Financial Data", de: "Finanzdaten erfassen", goal: "Build and verify a clean 5-year dataset from the annual reports." },
  { n: 3, key: "trends", en: "Historical Trend Analysis", de: "Historische Trendanalyse", goal: "Calculate growth, judge each trend and explain why it happened." },
  { n: 4, key: "ratios", en: "Ratio Analysis", de: "Kennzahlenanalyse", goal: "Calculate the key ratios yourself and interpret them." },
  { n: 5, key: "statements", en: "Financial Statement Investigation", de: "Analyse der Jahresrechnung", goal: "Investigate unusual changes in the annual report — not just headline numbers." },
  { n: 6, key: "quality", en: "Quality of Earnings", de: "Qualität der Gewinne", goal: "Separate recurring, cash-backed earnings from one-offs and accounting effects." },
  { n: 7, key: "risk", en: "Risk Analysis", de: "Risikoanalyse", goal: "Map the risks and identify the three that matter most for value." },
  { n: 8, key: "peers", en: "Peer Comparison", de: "Peer-Vergleich", goal: "Compare with a peer on the metrics that are actually comparable." },
  { n: 9, key: "valuation", en: "Valuation", de: "Bewertung", goal: "Value the equity with methods that fit a financial institution." },
  { n: 10, key: "thesis", en: "Investment Thesis", de: "Investment-These", goal: "Pull everything together into a thesis with scenarios — no buy/sell verdict." },
];

export const stageState = (progress, n) => progress?.stages?.[n] || {};
export const stageComplete = (progress, n) => Boolean(stageState(progress, n).completed);
export const quizDone = (progress, n) => {
  const s = stageState(progress, n);
  return Boolean(s.quizCompletedOnce || s.quiz?.finished);
};
export const stagePassed = (progress, n, training) => stageComplete(progress, n) && (!training || quizDone(progress, n));
export const isUnlocked = (progress, n, training, unlockAll = false) => unlockAll || n === 1 || stagePassed(progress, n - 1, training);
export function currentStage(progress, training) {
  for (const s of STAGES) if (!stagePassed(progress, s.n, training)) return s.n;
  return 10;
}
export const overallProgress = (progress, training) => STAGES.filter((s) => stagePassed(progress, s.n, training)).length / STAGES.length;

// ------------------------------------------------------------------ text feedback

const ABBREVIATIONS = ["e.g.", "i.e.", "z.B.", "z. B.", "d.h.", "bzw.", "inkl.", "ca.", "Inc.", "Ltd.", "AG.", "vs.", "etc.", "approx.", "Nr.", "u.a."];

export function sentenceCount(text) {
  let t = (text || "").trim();
  if (!t) return 0;
  for (const a of ABBREVIATIONS) t = t.split(a).join(a.replace(/\./g, ""));
  const parts = t.split(/(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9"“(])/);
  return parts.filter((p) => p.split(/\s+/).filter(Boolean).length >= 3).length;
}

export const wordCount = (text) => (text || "").split(/\s+/).filter(Boolean).length;

function matches(text, keyword) {
  const kw = keyword.trim().toLowerCase();
  if (!kw) return false;
  if (kw.length <= 3 && /^[a-z0-9&]+$/.test(kw)) {
    // short tokens (ib, us, fee, nii) need word boundaries; allow a plural ending ("fees")
    return new RegExp(`(?<![a-z0-9])${kw}(?:s|es)?(?![a-z0-9])`).test(text);
  }
  return text.includes(kw); // longer stems match inside words (zins → Zinsen, Zinserfolg)
}

export function keywordCoverage(text, keyPoints) {
  const low = " " + (text || "").toLowerCase() + " ";
  const covered = [], missed = [];
  for (const kp of keyPoints || []) ((kp.keywords || []).some((k) => matches(low, k)) ? covered : missed).push(kp.point);
  return [covered, missed];
}

export const EXPLANATION_DRIVERS = [
  { point: "Interest rates / monetary policy", keywords: ["interest", "zins", "rate", "snb", "fed", "ecb", "ezb", "monetary"] },
  { point: "Acquisition, disposal or change in scope", keywords: ["acqui", "übernahme", "uebernahme", "merger", "fusion", "disposal", "verkauf", "divest", "scope", "konsolidier", "credit suisse"] },
  { point: "Accounting change or restatement", keywords: ["ifrs", "gaap", "accounting", "rechnungslegung", "restat", "standard", "oci"] },
  { point: "One-off item (gain, loss, provision, impairment)", keywords: ["one-off", "one off", "einmal", "non-recurring", "impair", "wertminder", "provision", "rückstell", "rueckstell", "goodwill", "litigation", "restructur"] },
  { point: "Markets / client assets / volumes", keywords: ["market", "markt", "asset", "volume", "volumen", "client", "kunde", "inflow", "zufluss", "aum"] },
  { point: "Costs and efficiency", keywords: ["cost", "kosten", "expense", "aufwand", "efficien", "effizien", "headcount", "personal"] },
  { point: "Capital actions (buybacks, dividends)", keywords: ["buyback", "rückkauf", "rueckkauf", "dividend", "share count", "aktien"] },
  { point: "Currency effects", keywords: ["fx", "currency", "währung", "waehrung", "franc", "franken", "dollar", "euro", "translation"] },
  { point: "Catastrophes, claims or reserves (insurers)", keywords: ["catastroph", "katastroph", "claims", "schäden", "schaeden", "reserve", "hurricane", "covid", "pandemic"] },
];

export function eventsFor(profile, metric = null, year = null) {
  return (profile.events || []).filter((ev) => (year === null || ev.year === year) && (metric === null || !ev.metrics?.length || ev.metrics.includes(metric)));
}

export const NATURE_LABEL = { "one-off": "One-off", accounting: "Accounting-driven", operational: "Operational", structural: "Structural", transitional: "Transitional", regulatory: "Regulatory", acquisition: "Acquisition", capital: "Capital management" };
