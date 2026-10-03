"""Plotly charts in one consistent style.

Design rules (applied everywhere):
* one y-axis per chart — never dual axes; two measures → two charts
* thin 2 px lines, ≥ 8 px markers, hairline solid gridlines, recessive axes
* categorical colours in a fixed, colour-blind-validated order; colour follows the
  company, not its rank
* diverging blue/red only for sign (growth up/down), sequential blue for magnitude
* hover tooltips on every chart; the UI adds a table view next to each chart
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SURFACE = "#fcfcfb"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
POS = "#2a78d6"  # diverging: increase
NEG = "#e34948"  # diverging: decrease
NEUTRAL = "#c3c2b7"
SEQ_BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'


def _base(fig: go.Figure, title: str | None = None, height: int = 320, yaxis_title: str = "", showlegend: bool = False) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0, "xanchor": "left", "font": {"size": 15, "color": INK}} if title else None,
        height=height,
        margin={"l": 8, "r": 16, "t": 44 if title else 12, "b": 48 if showlegend else 8},
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": FONT, "size": 12, "color": INK2},
        showlegend=showlegend,
        legend={"orientation": "h", "yanchor": "top", "y": -0.2, "xanchor": "left", "x": 0, "font": {"color": INK2}},
        hoverlabel={"bgcolor": "#ffffff", "bordercolor": AXIS, "font": {"family": FONT, "color": INK}},
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS, tickcolor=AXIS, ticks="outside", tickfont={"color": MUTED}, type="category")
    fig.update_yaxes(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=True, zerolinecolor=AXIS, zerolinewidth=1, linecolor=AXIS, tickfont={"color": MUTED}, title={"text": yaxis_title, "font": {"color": MUTED, "size": 11}}, separatethousands=True)
    return fig


def history_line(s: pd.Series, title: str, unit: str, color: str = SERIES[0]) -> go.Figure:
    """Single-metric history with markers and an end-point label."""
    clean = s.dropna()
    fig = go.Figure()
    # NB: no layout annotations on category axes — Plotly reads numeric-looking strings as category indices.
    labels = [""] * max(len(clean) - 1, 0) + ([f"<b>{clean.values[-1]:,.1f}</b>"] if len(clean) else [])
    fig.add_trace(
        go.Scatter(
            x=[str(i) for i in clean.index],
            y=clean.values,
            mode="lines+markers+text",
            text=labels,
            textposition="top center",
            textfont={"color": INK, "size": 12},
            line={"color": color, "width": 2},
            marker={"size": 9, "color": color, "line": {"color": SURFACE, "width": 2}},
            name=title,
            hovertemplate="%{y:,.2f} " + unit + "<extra></extra>",
            cliponaxis=False,
        )
    )
    fig = _base(fig, title, yaxis_title=unit)
    fig.update_yaxes(rangemode="normal")
    return fig


def growth_bars(g: pd.Series, title: str, unit: str = "%") -> go.Figure:
    """Year-over-year changes; blue = increase, red = decrease (sign only, not good/bad)."""
    clean = g.dropna()
    colors = [POS if v >= 0 else NEG for v in clean.values]
    fig = go.Figure(
        go.Bar(
            x=[str(i) for i in clean.index],
            y=clean.values,
            marker={"color": colors, "line": {"width": 0}, "cornerradius": 4},
            width=0.5,
            hovertemplate="%{y:+.1f} " + unit + "<extra></extra>",
            name=title,
        )
    )
    fig = _base(fig, title, height=240, yaxis_title=unit)
    fig.update_layout(bargap=0.4, hovermode="closest")
    return fig


def compare_lines(series: dict[str, pd.Series], title: str, unit: str, colors: dict[str, str] | None = None) -> go.Figure:
    """Two or more companies on one metric (same unit). Colours follow the company."""
    fig = go.Figure()
    for i, (name, s) in enumerate(series.items()):
        clean = s.dropna()
        color = (colors or {}).get(name, SERIES[i % len(SERIES)])
        labels = [""] * max(len(clean) - 1, 0) + ([f"  {name}"] if len(clean) else [])
        fig.add_trace(
            go.Scatter(
                x=[str(x) for x in clean.index],
                y=clean.values,
                mode="lines+markers+text",
                text=labels,
                textposition="middle right",
                textfont={"color": INK2, "size": 11},
                name=name,
                line={"color": color, "width": 2},
                marker={"size": 9, "color": color, "line": {"color": SURFACE, "width": 2}},
                hovertemplate=f"{name}: " + "%{y:,.2f} " + unit + "<extra></extra>",
                cliponaxis=False,
            )
        )
    fig = _base(fig, title, yaxis_title=unit, showlegend=len(series) > 1)
    fig.update_layout(margin={"r": 80}, height=340 if len(series) > 1 else 320)
    return fig


def indexed_lines(series: dict[str, pd.Series], title: str, colors: dict[str, str] | None = None) -> go.Figure:
    """Index each series to 100 in its first year — compares growth across currencies/sizes."""
    indexed = {}
    for name, s in series.items():
        clean = s.dropna()
        if len(clean) and clean.iloc[0] > 0:
            indexed[name] = clean / clean.iloc[0] * 100
    return compare_lines(indexed, title, "index (first year = 100)", colors)


def waterfall(steps: list[tuple[str, float, str]], title: str, unit: str) -> go.Figure:
    """Bridge chart. steps: (label, value, measure) with measure in {'absolute','relative','total'}."""
    fig = go.Figure(
        go.Waterfall(
            x=[s[0] for s in steps],
            y=[s[1] for s in steps],
            measure=[s[2] for s in steps],
            connector={"line": {"color": AXIS, "width": 1}},
            increasing={"marker": {"color": POS}},
            decreasing={"marker": {"color": NEG}},
            totals={"marker": {"color": "#52514e"}},
            hovertemplate="%{x}: %{y:,.0f} " + unit + "<extra></extra>",
            textposition="outside",
            text=[f"{s[1]:,.0f}" for s in steps],
        )
    )
    fig = _base(fig, title, height=360, yaxis_title=unit)
    fig.update_layout(hovermode="closest")
    return fig


def risk_matrix(risks: list[dict], title: str = "Risk matrix — likelihood × impact") -> go.Figure:
    """Risks on a 5×5 grid. Background shade = likelihood × impact (sequential blue)."""
    z = np.array([[l * i for l in range(1, 6)] for i in range(1, 6)], dtype=float)
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[1, 2, 3, 4, 5],
            y=[1, 2, 3, 4, 5],
            colorscale=[[0, "#f3f6fa"], [0.5, SEQ_BLUE[2]], [1, SEQ_BLUE[6]]],
            showscale=False,
            hoverinfo="skip",
            xgap=2,
            ygap=2,
        )
    )
    # numbered markers (the table next to the chart maps numbers to risks); spread points that share a cell
    seen: dict[tuple[int, int], int] = {}
    offsets = [(0, 0), (-0.25, 0), (0.25, 0), (0, 0.25), (0, -0.25), (-0.25, 0.25), (0.25, 0.25), (-0.25, -0.25), (0.25, -0.25)]
    xs, ys, nums, names = [], [], [], []
    for i, r in enumerate(risks, start=1):
        key = (int(r["likelihood"]), int(r["impact"]))
        k = seen.get(key, 0)
        seen[key] = k + 1
        dx, dy = offsets[k % len(offsets)]
        xs.append(key[0] + dx)
        ys.append(key[1] + dy)
        nums.append(str(r.get("id", i)))
        names.append(r["name"])
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            text=nums,
            customdata=names,
            textposition="middle center",
            textfont={"color": "#ffffff", "size": 11},
            marker={"size": 22, "color": INK, "line": {"color": SURFACE, "width": 2}},
            hovertemplate="%{customdata}<br>Likelihood %{x:.0f} · Impact %{y:.0f}<extra></extra>",
        )
    )
    fig = _base(fig, title, height=440)
    fig.update_xaxes(type="linear", range=[0.5, 5.5], tickvals=[1, 2, 3, 4, 5], ticktext=["1 rare", "2", "3", "4", "5 likely"], title={"text": "Likelihood", "font": {"color": MUTED}})
    fig.update_yaxes(range=[0.5, 5.7], tickvals=[1, 2, 3, 4, 5], ticktext=["1 minor", "2", "3", "4", "5 severe"], showgrid=False, zeroline=False, title={"text": "Impact on value", "font": {"color": MUTED}})
    fig.update_layout(hovermode="closest")
    return fig


def value_bars(items: list[tuple[str, float]], title: str, unit: str, reference: float | None = None, reference_label: str = "Market price") -> go.Figure:
    """Horizontal bars for valuation outputs, with an optional reference line (e.g. share price)."""
    labels = [i[0] for i in items]
    vals = [i[1] for i in items]
    fig = go.Figure(
        go.Bar(
            y=labels,
            x=vals,
            orientation="h",
            marker={"color": SERIES[0], "cornerradius": 4},
            width=0.5,
            text=[f"{v:,.1f}" for v in vals],
            textposition="outside",
            textfont={"color": INK2},
            hovertemplate="%{y}: %{x:,.2f} " + unit + "<extra></extra>",
        )
    )
    fig = _base(fig, title, height=90 + 46 * len(items), yaxis_title="")
    fig.update_yaxes(type="category", showgrid=False, autorange="reversed", tickfont={"color": INK2})
    fig.update_xaxes(type="linear", showgrid=True, gridcolor=GRID, title={"text": unit, "font": {"color": MUTED}})
    if reference is not None and np.isfinite(reference):
        fig.add_vline(x=reference, line={"color": INK, "width": 1.5})
        fig.add_annotation(x=reference, y=1.02, yref="paper", text=f"{reference_label} {reference:,.2f}", showarrow=False, font={"color": INK, "size": 11}, xanchor="left", xshift=4)
    fig.update_layout(hovermode="closest")
    return fig


def sensitivity_heatmap(grid: np.ndarray, r_values: list[float], g_values: list[float], title: str, unit: str) -> go.Figure:
    """Value per share across cost of equity (rows) and growth (columns). Sequential blue = magnitude."""
    text = [[("–" if not np.isfinite(v) else f"{v:,.0f}") for v in row] for row in grid]
    fig = go.Figure(
        go.Heatmap(
            z=grid,
            x=[f"g {g * 100:.1f} %" for g in g_values],
            y=[f"r {r * 100:.1f} %" for r in r_values],
            colorscale=[[0, SEQ_BLUE[0]], [1, SEQ_BLUE[10]]],
            text=text,
            texttemplate="%{text}",
            textfont={"size": 11},
            hovertemplate="%{y} · %{x}: %{z:,.2f} " + unit + "<extra></extra>",
            xgap=2,
            ygap=2,
            colorbar={"title": {"text": unit, "font": {"color": MUTED}}, "thickness": 10},
        )
    )
    fig = _base(fig, title, height=330)
    fig.update_yaxes(showgrid=False, autorange="reversed")
    fig.update_layout(hovermode="closest")
    return fig


def small_line(s: pd.Series, title: str, unit: str, color: str = SERIES[0]) -> go.Figure:
    fig = history_line(s, title, unit, color)
    fig.update_layout(height=230)
    return fig


def pb_roe_chart(r: float, g: float, points: list[dict], title: str = "ROE vs P/B — the value-creation line") -> go.Figure:
    """Justified P/B = (ROE − g)/(r − g) as a line; companies as points (ROE in %, P/B in ×)."""
    roe = np.linspace(0, 0.25, 101)
    line = (roe - g) / (r - g) if r > g else np.full_like(roe, np.nan)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=roe * 100, y=line, mode="lines", line={"color": MUTED, "width": 2}, name="Justified P/B",
                             hovertemplate="ROE %{x:.1f} % → justified P/B %{y:.2f}×<extra></extra>"))
    positions = ["top left", "bottom right", "top right", "bottom left"]
    for i, p in enumerate(points):
        fig.add_trace(go.Scatter(x=[p["roe"]], y=[p["pb"]], mode="markers+text", text=[p["name"]], textposition=positions[i % len(positions)],
                                 marker={"size": 13, "color": SERIES[i % len(SERIES)], "line": {"color": SURFACE, "width": 2}},
                                 textfont={"color": INK, "size": 12}, name=p["name"],
                                 hovertemplate=p["name"] + ": ROE %{x:.1f} %, P/B %{y:.2f}×<extra></extra>"))
    fig = _base(fig, title, height=400, yaxis_title="P/B (×)", showlegend=True)
    top = max([2.5] + [p["pb"] * 1.3 for p in points if p.get("pb") == p.get("pb") and p.get("pb") is not None])
    fig.update_yaxes(range=[0, top])
    fig.update_layout(legend={"orientation": "h", "yanchor": "top", "y": -0.3, "xanchor": "left", "x": 0}, margin={"b": 90})
    fig.update_xaxes(type="linear", title={"text": "Return on equity (%)", "font": {"color": MUTED}}, showgrid=True, gridcolor=GRID)
    fig.add_vline(x=r * 100, line={"color": AXIS, "width": 1})
    fig.add_annotation(x=r * 100, y=1, yref="paper", text=f"cost of equity {r * 100:.1f} %", showarrow=False, xanchor="left", xshift=4, font={"color": MUTED, "size": 11})
    fig.update_layout(hovermode="closest")
    return fig
