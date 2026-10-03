// Plotly charts that read their colours from the page's CSS tokens (light and dark).
// Rules: one y-axis per chart, thin 2px lines, ≥ 8px markers, hairline solid grid,
// fixed categorical order (colour follows the company), blue/red only for sign.
import React, { useEffect, useRef, useState, useContext, createContext } from "react";

const ThemeCtx = createContext(0);

function readTokens() {
  const cs = getComputedStyle(document.documentElement);
  const v = (n) => cs.getPropertyValue(n).trim();
  return {
    surface: v("--chart-surface"), grid: v("--chart-grid"), axis: v("--chart-axis"), ink: v("--ink"), ink2: v("--ink-2"), muted: v("--muted"),
    series: [1, 2, 3, 4, 5, 6, 7, 8].map((i) => v(`--series-${i}`)), pos: v("--chart-pos"), neg: v("--chart-neg"), seq: [v("--seq-0"), v("--seq-1"), v("--seq-2")],
    font: v("--font-body"),
  };
}

export function ThemeProvider({ children }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const bump = () => setTick((t) => t + 1);
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    mq?.addEventListener?.("change", bump);
    const mo = new MutationObserver(bump);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "class"] });
    return () => {
      mq?.removeEventListener?.("change", bump);
      mo.disconnect();
    };
  }, []);
  return <ThemeCtx.Provider value={tick}>{children}</ThemeCtx.Provider>;
}

function base(t, { title, height = 300, yTitle = "", legend = false } = {}) {
  return {
    title: title ? { text: title, x: 0, xanchor: "left", font: { size: 14, color: t.ink, family: t.font } } : undefined,
    height,
    margin: { l: 8, r: 16, t: title ? 40 : 12, b: legend ? 56 : 8 },
    paper_bgcolor: t.surface,
    plot_bgcolor: t.surface,
    font: { family: t.font, size: 12, color: t.ink2 },
    showlegend: legend,
    legend: { orientation: "h", yanchor: "top", y: -0.2, xanchor: "left", x: 0, font: { color: t.ink2 } },
    hoverlabel: { bgcolor: t.surface, bordercolor: t.axis, font: { family: t.font, color: t.ink } },
    hovermode: "x unified",
    xaxis: { showgrid: false, linecolor: t.axis, tickcolor: t.axis, ticks: "outside", tickfont: { color: t.muted }, type: "category", automargin: true },
    yaxis: { showgrid: true, gridcolor: t.grid, gridwidth: 1, zeroline: true, zerolinecolor: t.axis, zerolinewidth: 1, linecolor: t.axis, tickfont: { color: t.muted }, title: { text: yTitle, font: { color: t.muted, size: 11 } }, separatethousands: true, automargin: true },
  };
}

const clean = (pairs) => pairs.filter(([, v]) => v !== null && Number.isFinite(v));

export const C = {
  history: (pairs, title, unit) => (t) => {
    const s = clean(pairs);
    const labels = s.map((_, i) => (i === s.length - 1 ? `<b>${s[i][1].toLocaleString("en-US", { maximumFractionDigits: 1 })}</b>` : ""));
    return {
      data: [{ x: s.map(([y]) => String(y)), y: s.map(([, v]) => v), type: "scatter", mode: "lines+markers+text", text: labels, textposition: "top center", textfont: { color: t.ink, size: 12 }, cliponaxis: false, line: { color: t.series[0], width: 2 }, marker: { size: 9, color: t.series[0], line: { color: t.surface, width: 2 } }, name: title, hovertemplate: `%{y:,.2f} ${unit}<extra></extra>` }],
      layout: base(t, { title, yTitle: unit }),
    };
  },
  growth: (pairs, title, unit) => (t) => {
    const s = clean(pairs);
    const layout = base(t, { title, height: 230, yTitle: unit });
    layout.bargap = 0.4;
    layout.hovermode = "closest";
    return { data: [{ x: s.map(([y]) => String(y)), y: s.map(([, v]) => v), type: "bar", marker: { color: s.map(([, v]) => (v >= 0 ? t.pos : t.neg)), cornerradius: 4 }, width: 0.5, hovertemplate: `%{y:+.1f} ${unit}<extra></extra>` }], layout };
  },
  compare: (seriesByName, title, unit, colorIndex = {}) => (t) => {
    const names = Object.keys(seriesByName);
    const data = names.map((name, i) => {
      const s = clean(seriesByName[name]);
      const color = t.series[colorIndex[name] ?? i];
      return { x: s.map(([y]) => String(y)), y: s.map(([, v]) => v), type: "scatter", mode: "lines+markers+text", name, text: s.map((_, j) => (j === s.length - 1 ? `  ${name}` : "")), textposition: "middle right", textfont: { color: t.ink2, size: 11 }, cliponaxis: false, line: { color, width: 2 }, marker: { size: 9, color, line: { color: t.surface, width: 2 } }, hovertemplate: `${name}: %{y:,.2f} ${unit}<extra></extra>` };
    });
    const layout = base(t, { title, height: names.length > 1 ? 320 : 300, yTitle: unit, legend: names.length > 1 });
    layout.margin.r = 80;
    return { data, layout };
  },
  waterfall: (steps, title, unit) => (t) => {
    const layout = base(t, { title, height: 340, yTitle: unit });
    layout.hovermode = "closest";
    return {
      data: [{ type: "waterfall", x: steps.map((s) => s[0]), y: steps.map((s) => s[1]), measure: steps.map((s) => s[2]), connector: { line: { color: t.axis, width: 1 } }, increasing: { marker: { color: t.pos } }, decreasing: { marker: { color: t.neg } }, totals: { marker: { color: t.ink2 } }, text: steps.map((s) => Math.round(s[1]).toLocaleString("en-US")), textposition: "outside", hovertemplate: `%{x}: %{y:,.0f} ${unit}<extra></extra>` }],
      layout,
    };
  },
  riskMatrix: (risks) => (t) => {
    const z = [1, 2, 3, 4, 5].map((i) => [1, 2, 3, 4, 5].map((l) => l * i));
    const offsets = [[0, 0], [-0.25, 0], [0.25, 0], [0, 0.25], [0, -0.25], [-0.25, 0.25], [0.25, 0.25], [-0.25, -0.25], [0.25, -0.25]];
    const seen = {};
    const pts = risks.map((r) => {
      const k = `${r.likelihood}-${r.impact}`;
      const n = (seen[k] = (seen[k] ?? -1) + 1);
      const [dx, dy] = offsets[n % offsets.length];
      return { x: r.likelihood + dx, y: r.impact + dy, id: String(r.id), name: r.name };
    });
    const layout = base(t, { title: "Risk matrix — likelihood × impact", height: 420 });
    layout.hovermode = "closest";
    layout.xaxis = { ...layout.xaxis, type: "linear", range: [0.5, 5.5], tickvals: [1, 2, 3, 4, 5], ticktext: ["1 rare", "2", "3", "4", "5 likely"], title: { text: "Likelihood", font: { color: t.muted } } };
    layout.yaxis = { ...layout.yaxis, range: [0.5, 5.7], tickvals: [1, 2, 3, 4, 5], ticktext: ["1 minor", "2", "3", "4", "5 severe"], showgrid: false, zeroline: false, title: { text: "Impact on value", font: { color: t.muted } } };
    return {
      data: [
        { type: "heatmap", z, x: [1, 2, 3, 4, 5], y: [1, 2, 3, 4, 5], colorscale: [[0, t.seq[0]], [0.5, t.seq[1]], [1, t.seq[2]]], showscale: false, hoverinfo: "skip", xgap: 2, ygap: 2 },
        { type: "scatter", mode: "markers+text", x: pts.map((p) => p.x), y: pts.map((p) => p.y), text: pts.map((p) => p.id), customdata: pts.map((p) => p.name), textposition: "middle center", textfont: { color: t.surface, size: 11 }, marker: { size: 22, color: t.ink, line: { color: t.surface, width: 2 } }, hovertemplate: "%{customdata}<br>Likelihood %{x:.0f} · Impact %{y:.0f}<extra></extra>" },
      ],
      layout,
    };
  },
  valueBars: (items, title, unit, reference = null, refLabel = "Market price") => (t) => {
    const layout = base(t, { title, height: 90 + 46 * items.length });
    layout.hovermode = "closest";
    layout.yaxis = { ...layout.yaxis, type: "category", showgrid: false, autorange: "reversed", tickfont: { color: t.ink2 }, title: { text: "" } };
    layout.xaxis = { ...layout.xaxis, type: "linear", showgrid: true, gridcolor: t.grid, title: { text: unit, font: { color: t.muted } } };
    if (reference !== null && Number.isFinite(reference)) {
      layout.shapes = [{ type: "line", x0: reference, x1: reference, y0: 0, y1: 1, yref: "paper", line: { color: t.ink, width: 1.5 } }];
      layout.annotations = [{ x: reference, y: 1.02, yref: "paper", text: `${refLabel} ${reference.toFixed(2)}`, showarrow: false, font: { color: t.ink, size: 11 }, xanchor: "left", xshift: 4 }];
    }
    return { data: [{ type: "bar", orientation: "h", y: items.map((i) => i[0]), x: items.map((i) => i[1]), marker: { color: t.series[0], cornerradius: 4 }, width: 0.5, text: items.map((i) => i[1].toFixed(1)), textposition: "outside", textfont: { color: t.ink2 }, cliponaxis: false, hovertemplate: `%{y}: %{x:,.2f} ${unit}<extra></extra>` }], layout };
  },
  heatmap: (grid, rVals, gVals, title, unit) => (t) => {
    const layout = base(t, { title, height: 320 });
    layout.hovermode = "closest";
    layout.yaxis = { ...layout.yaxis, showgrid: false, autorange: "reversed", type: "category" };
    return {
      data: [{ type: "heatmap", z: grid, x: gVals.map((g) => `g ${(g * 100).toFixed(1)} %`), y: rVals.map((r) => `r ${(r * 100).toFixed(1)} %`), colorscale: [[0, t.seq[0]], [1, t.seq[2]]], text: grid.map((row) => row.map((v) => (v === null ? "–" : Math.round(v).toLocaleString("en-US")))), texttemplate: "%{text}", textfont: { size: 11 }, hovertemplate: `%{y} · %{x}: %{z:,.2f} ${unit}<extra></extra>`, xgap: 2, ygap: 2, colorbar: { title: { text: unit, font: { color: t.muted } }, thickness: 10, tickfont: { color: t.muted } } }],
      layout,
    };
  },
  pbRoe: (r, g, points) => (t) => {
    const roe = Array.from({ length: 101 }, (_, i) => (i / 100) * 0.25);
    const line = roe.map((x) => (r > g ? (x - g) / (r - g) : null));
    const layout = base(t, { title: "ROE vs P/B — the value-creation line", height: 400, yTitle: "P/B (×)", legend: true });
    layout.hovermode = "closest";
    const top = Math.max(2.5, ...points.filter((p) => Number.isFinite(p.pb)).map((p) => p.pb * 1.3));
    layout.xaxis = { ...layout.xaxis, type: "linear", showgrid: true, gridcolor: t.grid, title: { text: "Return on equity (%)", font: { color: t.muted } } };
    layout.yaxis = { ...layout.yaxis, range: [0, top] };
    layout.legend.y = -0.3;
    layout.margin.b = 90;
    layout.shapes = [{ type: "line", x0: r * 100, x1: r * 100, y0: 0, y1: 1, yref: "paper", line: { color: t.axis, width: 1 } }];
    layout.annotations = [{ x: r * 100, y: 1, yref: "paper", text: `cost of equity ${(r * 100).toFixed(1)} %`, showarrow: false, xanchor: "left", xshift: 4, font: { color: t.muted, size: 11 } }];
    const pos = ["top left", "bottom right", "top right"];
    return {
      data: [
        { type: "scatter", mode: "lines", x: roe.map((x) => x * 100), y: line, line: { color: t.muted, width: 2 }, name: "Justified P/B", hovertemplate: "ROE %{x:.1f} % → justified P/B %{y:.2f}×<extra></extra>" },
        ...points.map((p, i) => ({ type: "scatter", mode: "markers+text", x: [p.roe], y: [p.pb], text: [p.name], textposition: pos[i % pos.length], marker: { size: 13, color: t.series[i % 8], line: { color: t.surface, width: 2 } }, textfont: { color: t.ink, size: 12 }, name: p.name, hovertemplate: `${p.name}: ROE %{x:.1f} %, P/B %{y:.2f}×<extra></extra>` })),
      ],
      layout,
    };
  },
  bars: (items, title, unit) => (t) => {
    const layout = base(t, { title, height: 90 + 32 * items.length });
    layout.hovermode = "closest";
    layout.yaxis = { ...layout.yaxis, type: "category", showgrid: false, autorange: "reversed", tickfont: { color: t.ink2 }, title: { text: "" } };
    layout.xaxis = { ...layout.xaxis, type: "linear", range: [0, 100], showgrid: true, gridcolor: t.grid, title: { text: unit, font: { color: t.muted } } };
    return { data: [{ type: "bar", orientation: "h", y: items.map((i) => i[0]), x: items.map((i) => i[1]), marker: { color: t.series[0], cornerradius: 4 }, width: 0.55, hovertemplate: `%{y}: %{x:.0f} ${unit}<extra></extra>` }], layout };
  },
};

/** A Plotly chart. `spec` is a function (tokens) → {data, layout}; `table` is the accessible fallback. */
export function Chart({ spec, table = null, label = "Chart" }) {
  const ref = useRef(null);
  const tick = useContext(ThemeCtx);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!window.Plotly) {
      setFailed(true);
      return;
    }
    const { data, layout } = spec(readTokens());
    window.Plotly.react(el, data, layout, { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["lasso2d", "select2d", "toImage"] });
  });
  useEffect(() => () => ref.current && window.Plotly && window.Plotly.purge(ref.current), []);
  return (
    <figure className="chart" aria-label={label}>
      {failed ? <p className="muted small">Charts could not load (the chart library is unavailable). The table below has the same numbers.</p> : <div ref={ref} key={tick} />}
      {table}
    </figure>
  );
}
