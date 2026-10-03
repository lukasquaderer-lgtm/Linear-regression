import { test } from "node:test";
import assert from "node:assert/strict";
import * as D from "../src/lib/data.js";
import * as C from "../src/lib/calc.js";
import * as R from "../src/lib/ratios.js";
import * as V from "../src/lib/valuation.js";
import * as Q from "../src/lib/questions.js";
import * as CA from "../src/lib/ca.js";
import { COMPANIES } from "../src/generated/data.js";

const ctxFor = (id) => {
  const p = D.withDefaults(D.builtinCompany(id).profile);
  return { profile: p, values: D.starterDataset(id), currency: p.currency, name: p.short_name, sector: p.sector };
};

test("every stage builds five progressive questions for every company", () => {
  for (const c of COMPANIES) {
    const ctx = ctxFor(c.profile.id);
    for (let stage = 1; stage <= 10; stage++) {
      const qs = Q.buildQuiz(stage, ctx, Q.emptyLearner(), stage * 7);
      assert.deepEqual(qs.map((q) => q.level), [1, 2, 3, 4, 5], `${c.profile.id} stage ${stage}`);
      for (const q of qs) {
        assert.ok(q.prompt && q.concept);
        if (q.kind === "mc") assert.ok(q.answer >= 0 && q.answer < q.options.length && new Set(q.options).size === q.options.length);
        if (q.kind === "numeric") assert.ok(Number.isFinite(q.answer), q.id);
        if (q.kind === "text") assert.ok(q.modelAnswer);
      }
    }
  }
});

test("spaced repetition", () => {
  const L = Q.emptyLearner();
  Q.record(L, "dupont", "wrong");
  Q.record(L, "growth_cagr", "correct");
  assert.deepEqual(Q.dueConcepts(L), []);
  L.quizCounter = 1;
  assert.deepEqual(Q.dueConcepts(L), ["dupont"]);
  const qs = Q.buildQuiz(6, ctxFor("ubs"), L, 3);
  assert.equal(qs[0].concept, "dupont");
  assert.ok(qs[0].review);
  for (let i = 0; i < 3; i++) Q.record(L, "dupont", "correct");
  L.quizCounter = 50;
  assert.ok(!Q.dueConcepts(L).includes("dupont"));
});

test("grading", () => {
  assert.ok(Q.grade({ kind: "mc", answer: 1 }, 1));
  assert.ok(!Q.grade({ kind: "mc", answer: 1 }, 0));
  assert.ok(Q.grade({ kind: "numeric", answer: 10, relTol: 0.02, absTol: 0.1 }, 10.05));
  assert.equal(Q.grade({ kind: "text" }, "x"), null);
});

test("import: German CSV, long, transposed", () => {
  const a = D.importText("Kennzahl;2021;2022\nKonzerngewinn;129,9;147,5\nCET1 ratio (%);21,1;20,5\nMy KPI;1;2\n");
  assert.equal(a.rows.net_income["2022"], 147.5);
  assert.equal(a.rows.cet1_ratio["2021"], 21.1);
  assert.deepEqual(a.unmapped, ["My KPI"]);
  const b = D.importText("metric,year,value\nnet_income,2024,167.1\nTotal assets,2024,27773\n");
  assert.equal(b.orientation, "long");
  assert.equal(b.rows.total_assets["2024"], 27773);
  const c = D.importText('year,Revenue,Net income\n2023,"541.8",164.6\n2024,556.6,(12)\n');
  assert.equal(c.orientation, "transposed");
  assert.equal(c.rows.net_income["2024"], -12);
  assert.throws(() => D.importText("a,b\nx,y\n"));
  assert.equal(D.parseNumber("1'234.5"), 1234.5);
  assert.equal(D.parseNumber("1.234,5", true), 1234.5);
  assert.equal(D.parseNumber("–"), null);
});

test("ratio diagnosis", () => {
  const ds = { years: [2024, 2025], values: { net_income: { 2024: 900, 2025: 1100 }, total_equity: { 2024: 10000, 2025: 11000 } }, meta: {} };
  const res = R.compute(R.RATIOS.roe, ds, 2025);
  const inputs = Object.fromEntries(res.required.map((r) => [`${r.metric}|${r.year}`, r.value]));
  assert.ok(R.diagnose(res, inputs, +res.value.toFixed(2)).correct);
  assert.match(R.diagnose(res, inputs, 10.0).headline, /year-end/);
  assert.match(R.diagnose(res, inputs, res.value / 100).headline, /decimal/);
});

test("valuation identities", () => {
  assert.equal(V.justifiedPB(0.09, 0.09, 0.02), 1);
  assert.ok(Math.abs(V.residualIncome(100, 0.09, 0.09, 0.02, 0.5).value - 100) < 1e-9);
  assert.ok(Math.abs(V.twoStageDDM(2, 0.03, 5, 0.03, 0.08).value - V.gordonDDM(2, 0.08, 0.03)) < 1e-9);
  assert.ok(Math.abs(V.impliedRoeFromPB(V.justifiedPB(0.12, 0.09, 0.02), 0.09, 0.02) - 0.12) < 1e-12);
});

test("text helpers", () => {
  assert.equal(CA.sentenceCount("UBS is a bank. It earns fees, e.g. on assets. It is Swiss."), 3);
  const [cov, miss] = CA.keywordCoverage("We earn fees and interest", [{ point: "Fees", keywords: ["fee"] }, { point: "IB", keywords: ["ib"] }]);
  assert.deepEqual(cov, ["Fees"]);
  assert.deepEqual(miss, ["IB"]);
  assert.equal(C.fmtNum(1234567.891, 1), "1'234'567.9");
});
