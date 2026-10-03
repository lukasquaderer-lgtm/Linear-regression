"""Shared Streamlit components: styling, headers, callouts, CFA boxes, checklists."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from . import cfa
from . import metrics as M

CSS = """
<style>
:root {
  --al-navy: #0f2540;
  --al-navy-2: #1a3658;
  --al-accent: #1c5cab;
  --al-ink: #0b1f33;
  --al-ink-2: #4a5868;
  --al-muted: #7b8794;
  --al-line: #d6dbe2;
  --al-surface: #ffffff;
  --al-good: #0c7a0c;
  --al-warn: #9a6400;
  --al-bad: #b42323;
}
.block-container { padding-top: 3.6rem; padding-bottom: 4rem; max-width: 1280px; }
h1, h2, h3 { letter-spacing: -0.01em; color: var(--al-ink); }
h2 { font-size: 1.35rem !important; margin-top: 0.6rem !important; }
h3 { font-size: 1.1rem !important; }
[data-testid="stMetricValue"] { font-size: 1.45rem; }
[data-testid="stMetricLabel"] p { color: var(--al-ink-2); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; }

.al-header { background: linear-gradient(90deg, var(--al-navy) 0%, var(--al-navy-2) 100%); color: #fff;
  border-radius: 6px; padding: 18px 22px 16px; margin-bottom: 18px; }
.al-header .al-kicker { color: #9fb7d4; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; }
.al-header .al-title { font-size: 1.55rem; font-weight: 650; margin: 2px 0 2px; color: #fff; }
.al-header .al-sub { color: #c9d6e6; font-size: 0.92rem; }
.al-header .al-chips { margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
.al-chip { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 0.75rem;
  background: rgba(255,255,255,0.10); color: #e6ecf3; border: 1px solid rgba(255,255,255,0.18); }

.al-cfa { border-left: 3px solid var(--al-accent); background: #f3f7fc; padding: 9px 13px; border-radius: 4px; margin: 6px 0 12px; }
.al-cfa .al-cfa-k { font-size: 0.72rem; font-weight: 700; color: var(--al-accent); text-transform: uppercase; letter-spacing: 0.06em; }
.al-cfa .al-cfa-t { font-size: 0.88rem; color: var(--al-ink); }

.al-task { border: 1px solid var(--al-line); background: var(--al-surface); border-radius: 6px; padding: 12px 16px; margin-bottom: 12px; }
.al-task .al-task-k { font-size: 0.72rem; font-weight: 700; color: var(--al-ink-2); text-transform: uppercase; letter-spacing: 0.06em; }
.al-task .al-task-t { font-size: 0.95rem; color: var(--al-ink); }

.al-check { font-size: 0.9rem; margin: 2px 0; color: var(--al-ink); }
.al-check .ok { color: var(--al-good); font-weight: 700; }
.al-check .no { color: var(--al-muted); font-weight: 700; }

.al-de { color: var(--al-muted); font-size: 0.85em; }
.al-level { display:inline-block; font-size: 0.72rem; font-weight: 700; padding: 1px 8px; border-radius: 999px;
  background: #e8eef7; color: var(--al-accent); margin-right: 6px; }
.al-review { display:inline-block; font-size: 0.72rem; font-weight: 700; padding: 1px 8px; border-radius: 999px;
  background: #fff1db; color: var(--al-warn); }
.al-small { font-size: 0.82rem; color: var(--al-ink-2); }
.al-lock { color: var(--al-muted); }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.45rem; }
[data-testid="stSidebar"] .stButton button { justify-content: flex-start; padding-left: 0.6rem; min-height: 2.1rem; }
[data-testid="stSidebar"] .stButton button > div { justify-content: flex-start; width: 100%; }
[data-testid="stSidebar"] .stButton button p { text-align: left; font-size: 0.9rem; }
[data-testid="stSidebar"] .al-side-brand { font-size: 1.15rem; font-weight: 700; color: #fff; margin-bottom: 0; }
[data-testid="stSidebar"] .al-side-sub { font-size: 0.78rem; color: #9fb7d4; margin-top: 0; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(text: str) -> str:
    return html.escape(str(text or ""))


def header(profile: dict, kicker: str, title: str, subtitle: str = "", chips: list[str] | None = None) -> None:
    chip_html = "".join(f'<span class="al-chip">{esc(c)}</span>' for c in (chips or []))
    st.markdown(
        f"""<div class="al-header"><div class="al-kicker">{esc(kicker)}</div>
        <div class="al-title">{esc(title)}</div><div class="al-sub">{esc(subtitle)}</div>
        <div class="al-chips">{chip_html}</div></div>""",
        unsafe_allow_html=True,
    )


def cfa_box(key: str) -> None:
    n = cfa.note(key)
    if not n:
        return
    area, text = n
    st.markdown(
        f'<div class="al-cfa"><div class="al-cfa-k">CFA Connection · {esc(area)}</div><div class="al-cfa-t">{esc(text)}</div></div>',
        unsafe_allow_html=True,
    )


def task_box(text: str, kicker: str = "Your task") -> None:
    st.markdown(f'<div class="al-task"><div class="al-task-k">{esc(kicker)}</div><div class="al-task-t">{text}</div></div>', unsafe_allow_html=True)


def bilingual(metric_key: str, custom: dict | None = None) -> str:
    """Markdown label 'English · *Deutsch*' for a metric."""
    m = M.get(metric_key)
    if m:
        return f"**{m.en}** · <span class='al-de'>{esc(m.de)}</span>"
    if custom and metric_key in custom:
        c = custom[metric_key]
        return f"**{esc(c.get('en', metric_key))}** · <span class='al-de'>{esc(c.get('de', ''))}</span>"
    return f"**{esc(metric_key)}**"


def checklist(items: list[tuple[str, bool]]) -> None:
    rows = "".join(
        f'<div class="al-check"><span class="{"ok" if ok else "no"}">{"✓" if ok else "○"}</span>&nbsp; {esc(label)}</div>' for label, ok in items
    )
    st.markdown(rows, unsafe_allow_html=True)


def level_badge(level: int, name: str, review: bool = False) -> str:
    b = f'<span class="al-level">Level {level} · {esc(name)}</span>'
    if review:
        b += '<span class="al-review">Spaced-repetition review</span>'
    return b


def table_view(df: pd.DataFrame, label: str = "Table view", **kwargs) -> None:
    with st.expander(label, icon=":material/table:"):
        st.dataframe(df, **kwargs)


def coverage_feedback(covered: list[str], missed: list[str], label_covered: str = "You covered", label_missed: str = "Consider adding") -> None:
    if covered:
        st.markdown(f"**{label_covered}:** " + " · ".join(f"✓ {esc(c)}" for c in covered), unsafe_allow_html=True)
    if missed:
        st.markdown(f"**{label_missed}:** " + " · ".join(f"○ {esc(m)}" for m in missed), unsafe_allow_html=True)


def plotly(fig, key: str | None = None) -> None:
    st.plotly_chart(fig, key=key, config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]})
