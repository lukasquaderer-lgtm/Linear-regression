// Compares the JS port with the Python implementation on every bundled dataset.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import * as D from "../src/lib/data.js";
import * as C from "../src/lib/calc.js";
import * as R from "../src/lib/ratios.js";
import { COMPANIES } from "../src/generated/data.js";

const file = process.env.PARITY_FILE;
test("parity with Python", { skip: !file }, () => {
  const py = JSON.parse(fs.readFileSync(file, "utf8"));
  for (const c of COMPANIES) {
    const id = c.profile.id;
    const p = D.withDefaults(c.profile);
    const ds = D.starterDataset(id);
    const ds2 = D.ensureRows(ds, D.requiredMetricKeys(p));
    const exp = py[id];
    assert.deepEqual(D.validate(ds2, p).map((i) => [i.severity, i.metric, i.year]), exp.issues, `${id} issues`);
    for (const k of Object.keys(ds.values)) assert.equal(C.classifyTrend(D.series(ds, k), k).label, exp.trends[k], `${id} trend ${k}`);
    assert.deepEqual(C.unusualChanges(ds).slice(0, 10).map((u) => [u.metric, u.year]), exp.unusual, `${id} unusual`);
    for (const [rk, byYear] of Object.entries(exp.ratios)) {
      for (const [y, v] of Object.entries(byYear)) {
        const js = R.compute(R.RATIOS[rk], ds, +y).value;
        if (v === null) assert.equal(js, null, `${id} ${rk} ${y}`);
        else assert.ok(Math.abs(js - v) < 1e-9 * Math.max(1, Math.abs(v)), `${id} ${rk} ${y}: ${js} vs ${v}`);
      }
    }
    for (const [y, v] of Object.entries(exp.roll)) {
      const r = C.impliedOtherEquityMovements(ds, +y);
      if (v === null) assert.equal(r?.other ?? null, null);
      else assert.ok(Math.abs(r.other - v) < 1e-6, `${id} roll ${y}`);
    }
  }
});
