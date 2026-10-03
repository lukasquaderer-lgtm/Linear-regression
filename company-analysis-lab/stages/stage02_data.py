"""Stage 2 — Collect Financial Data (Finanzdaten erfassen)."""

from __future__ import annotations

import io

import numpy as np
import pandas as pd
import streamlit as st

from lab import data as D
from lab import metrics as M
from lab import ui
from stages.common import AppContext, stage_footer, stage_header

NUMBER = 2
SEV_COLORS = {"error": "#fde2e1", "warning": "#fff1db", "info": "#eef4fb"}


def _groups(app: AppContext) -> dict[str, str]:
    core = set(D.core_metric_keys(app.profile))
    required = set(D.required_metric_keys(app.profile))
    out = {}
    for key in D.applicable_metric_keys(app.profile):
        out[key] = "1 Core" if key in core else ("2 Sector – required" if key in required else "3 Optional")
    for key in app.custom_metrics:
        out[key] = "4 Custom"
    return out


def _unit(app: AppContext, key: str) -> str:
    if key in app.custom_metrics:
        u = app.custom_metrics[key].get("unit", "money")
        return {"money": f"{app.currency} m", "bn": f"{app.currency} bn", "per_share": f"{app.currency}/share", "pct": "%", "shares": "m shares"}.get(u, u)
    return M.unit_label(key, app.currency)


def _full_dataset(app: AppContext) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    values, meta = app.dataset()
    groups = _groups(app)
    values, meta = D.ensure_rows(values, meta, list(groups))
    keys = sorted(groups, key=lambda k: (groups[k], list(M.CATALOG).index(k) if k in M.CATALOG else 999, k))
    extra = [k for k in values.index if k not in groups]  # e.g. imported rows not in catalogue
    for k in extra:
        groups[k] = "4 Custom"
    keys += extra
    return values.loc[keys], meta.reindex(keys).fillna(""), groups


def _criteria(app: AppContext, issues: list[D.Issue], values: pd.DataFrame) -> list[tuple[str, bool]]:
    years = D.year_columns(values)
    errors = [i for i in issues if i.severity == "error"]
    latest = years[-1] if years else None
    core = [k for k in D.core_metric_keys(app.profile)]
    verified = app.progress.get("verified", {})
    n_ver = sum(1 for k in core if latest and verified.get(f"{k}|{latest}"))
    currency_ok = app.profile.get("currency_confirmed", True) or bool(app.progress.get("settings", {}).get("currency_confirmed"))
    return [
        (f"At least 5 fiscal years — {len(years)}", len(years) >= 5),
        (f"No validation errors (missing or impossible values) — {len(errors)} open", not errors),
        (f"Latest year's core figures verified against the annual report — {n_ver}/{len(core)}", latest is not None and n_ver == len(core)),
        ("Reporting currency confirmed", currency_ok),
    ]


def render(app: AppContext) -> None:
    stage_header(app, NUMBER)
    p = app.profile
    values, meta, groups = _full_dataset(app)
    issues = D.validate(values, p, app.custom_metrics)

    left, right = st.columns([3, 2], gap="large")
    with left:
        ui.task_box(
            "Build a clean, verified 5-year dataset. "
            "<b>(1)</b> Fill every missing industry-specific figure from the annual reports. "
            "<b>(2)</b> Check the latest year's core figures against the annual report and tick them as verified. "
            "<b>(3)</b> Clear every validation error. Amounts are in <b>millions</b> of the reporting currency unless the unit says otherwise; enter ratios in percent (14.3, not 0.143)."
        )
        st.caption(f"**Data source:** {p.get('data_source', '–')}")
        ui.cfa_box("data_collection")
    with right:
        with st.container(border=True):
            st.markdown("**Accounting basis by year** · <span class='al-de'>Rechnungslegung</span>", unsafe_allow_html=True)
            acc = p.get("accounting", {})
            if acc:
                st.dataframe(pd.DataFrame({"Year": list(acc), "Basis": list(acc.values())}), hide_index=True, height=215)
                for (y0, b0), (y1, b1) in zip(list(acc.items()), list(acc.items())[1:]):
                    if b0 != b1:
                        st.warning(f"Accounting break between {y0} and {y1}: {b0} → {b1}. Do not compare levels across it without adjustment.", icon=":material/warning:")
            if p.get("accounting_notes"):
                st.caption(p["accounting_notes"])
            _currency_box(app)

    errors = sum(i.severity == "error" for i in issues)
    warnings = sum(i.severity == "warning" for i in issues)
    infos = sum(i.severity == "info" for i in issues)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fiscal years", len(D.year_columns(values)), border=True)
    c2.metric("Errors", errors, border=True)
    c3.metric("Warnings", warnings, border=True)
    c4.metric("Notes", infos, border=True)

    tab_edit, tab_check, tab_verify, tab_import, tab_glossary = st.tabs(
        ["Data table", "Validation", "Verify vs annual report", "Import CSV / Excel", "Glossary EN · DE"]
    )
    with tab_edit:
        _editor(app, values, meta, groups)
    with tab_check:
        _validation(app, values, issues, groups)
    with tab_verify:
        _verification(app, values, groups)
    with tab_import:
        _import(app, values, meta)
    with tab_glossary:
        _glossary(app, groups)

    stage_footer(app, NUMBER, _criteria(app, issues, values))


# ----------------------------------------------------------------------------- pieces


def _bump() -> None:
    """New widget keys for the editors after the underlying data changed."""
    st.session_state["s2-ver"] = st.session_state.get("s2-ver", 0) + 1


def _currency_box(app: AppContext) -> None:
    p = app.profile
    settings = app.progress.setdefault("settings", {})
    if p.get("currency_confirmed", True):
        st.caption(f"Reporting currency: **{app.currency}** (from the annual report).")
        return
    st.markdown("**Confirm the reporting currency** — check the annual report's cover or the statement headers.")
    options = ["CHF", "EUR", "USD", "GBP"]
    cur = st.selectbox("Reporting currency", options, index=options.index(app.currency) if app.currency in options else 0, key="s2-currency")
    ok = st.checkbox("I checked this in the annual report", value=bool(settings.get("currency_confirmed")), key="s2-currency-ok")
    if cur != settings.get("currency") or ok != bool(settings.get("currency_confirmed")):
        settings["currency"] = cur
        settings["currency_confirmed"] = ok
        app.save()
        st.rerun()


def _editor(app: AppContext, values: pd.DataFrame, meta: pd.DataFrame, groups: dict[str, str]) -> None:
    years = D.year_columns(values)
    required = set(D.required_metric_keys(app.profile))
    table = pd.DataFrame(index=values.index)
    table["Group"] = [groups.get(k, "4 Custom")[2:] for k in values.index]
    table["Metric · Kennzahl"] = [M.label(k, app.custom_metrics).replace(" · ", "  ·  ") for k in values.index]
    table["Unit"] = [_unit(app, k) for k in values.index]
    table["Req."] = ["★" if k in required else "" for k in values.index]
    for y in years:
        table[str(y)] = values[y].astype(float)
    table["Source"] = meta["source"].astype(str)
    table["Note"] = meta["note"].astype(str)

    st.caption("★ = required. Edit cells directly, then **Save dataset**. Hover a column header for help. Values you change lose their 'verified' tick.")
    with st.form("s2-editor-form", border=False):
        edited = st.data_editor(
            table,
            hide_index=True,
            num_rows="fixed",
            placeholder="–",
            height=min(38 * (len(table) + 1) + 3, 760),
            disabled=["Group", "Metric · Kennzahl", "Unit", "Req."],
            column_config={
                "Group": st.column_config.TextColumn(width="small"),
                "Metric · Kennzahl": st.column_config.TextColumn(width="large"),
                "Unit": st.column_config.TextColumn(width="small"),
                "Req.": st.column_config.TextColumn(width=40),
                **{str(y): st.column_config.NumberColumn(str(y), format="localized", help=f"Fiscal year {y}") for y in years},
                "Source": st.column_config.TextColumn(width="medium"),
                "Note": st.column_config.TextColumn(width="medium"),
            },
            key=f"s2-editor-{st.session_state.get('s2-ver', 0)}",
        )
        saved = st.form_submit_button("Save dataset", type="primary", icon=":material/save:")
    if saved:
        new_values = values.copy()
        for y in years:
            new_values[y] = pd.to_numeric(edited[str(y)], errors="coerce").astype(float).values
        new_meta = pd.DataFrame({"source": edited["Source"].fillna("").astype(str).values, "note": edited["Note"].fillna("").astype(str).values}, index=values.index)
        changed = 0
        verified = app.progress.setdefault("verified", {})
        for k in values.index:
            for y in years:
                a, b = values.at[k, y], new_values.at[k, y]
                if not ((pd.isna(a) and pd.isna(b)) or (not pd.isna(a) and not pd.isna(b) and np.isclose(a, b))):
                    changed += 1
                    verified.pop(f"{k}|{y}", None)
                    if not pd.isna(b) and (str(new_meta.at[k, "source"]).startswith("To collect") or not new_meta.at[k, "source"]):
                        new_meta.at[k, "source"] = "Entered by you from the annual report"
        D.save_working(app.company_id, new_values, new_meta)
        app.save()
        st.toast(f"Saved — {changed} value(s) changed.", icon=":material/save:")
        _bump()
        st.rerun()

    c1, c2, c3 = st.columns(3)
    with c1:
        nxt = (years[-1] + 1) if years else M.DEFAULT_YEARS[0]
        if st.button(f"Add fiscal year {nxt}", icon=":material/add:", key="s2-add-year"):
            values[nxt] = np.nan
            D.save_working(app.company_id, values, meta)
            _bump()
            st.rerun()
    with c2:
        if years and st.button(f"Add earlier year {years[0] - 1}", icon=":material/history:", key="s2-add-early"):
            values.insert(0, years[0] - 1, np.nan)
            D.save_working(app.company_id, values[sorted(values.columns)], meta)
            _bump()
            st.rerun()
    with c3:
        with st.popover("Remove a year", icon=":material/remove:"):
            y = st.selectbox("Year", years, key="s2-remove-year")
            if st.button("Remove", key="s2-remove-btn"):
                D.save_working(app.company_id, values.drop(columns=[y]), meta)
                _bump()
                st.rerun()

    with st.expander("Add an industry-specific or custom metric", icon=":material/playlist_add:"):
        st.caption("For example: invested assets, CSM, LCR, leverage ratio, new-business margin, Solvency II own funds …")
        with st.form("s2-custom"):
            en = st.text_input("English name (CFA terminology)")
            de = st.text_input("German name")
            unit = st.selectbox("Unit", ["money", "bn", "pct", "per_share", "shares"], format_func=lambda u: {"money": f"{app.currency} m", "bn": f"{app.currency} bn", "pct": "%", "per_share": "per share", "shares": "m shares"}[u])
            better = st.selectbox("Higher is…", ["better", "worse", "neutral"])
            if st.form_submit_button("Add metric"):
                if not en.strip():
                    st.error("Enter an English name.")
                else:
                    key = "custom_" + D.slugify(en)
                    app.custom_metrics[key] = {"en": en.strip(), "de": de.strip(), "unit": unit, "higher_is_better": {"better": True, "worse": False, "neutral": None}[better]}
                    vals, met = D.ensure_rows(values, meta, [key])
                    met.at[key, "source"] = "Entered by you"
                    D.save_working(app.company_id, vals, met)
                    app.save()
                    _bump()
                    st.rerun()

    with st.popover("Reset to starter data", icon=":material/restart_alt:"):
        st.write("Discard all your edits to this dataset and reload the starter file?")
        if st.button("Yes, reset dataset", key="s2-reset"):
            D.reset_working(app.company_id)
            app.progress["verified"] = {}
            app.save()
            _bump()
            st.rerun()


def _highlight(values: pd.DataFrame, issues: list[D.Issue], required: set[str], custom: dict) -> pd.io.formats.style.Styler:
    years = D.year_columns(values)
    cell_sev: dict[tuple[str, int], str] = {}
    for i in issues:
        if i.year is not None:
            prev = cell_sev.get((i.metric, i.year))
            if prev is None or D.SEVERITY_ORDER[i.severity] < D.SEVERITY_ORDER[prev]:
                cell_sev[(i.metric, i.year)] = i.severity
    disp = values[years].copy()
    disp.columns = [str(y) for y in years]
    disp.index = [M.short(k, custom) for k in values.index]
    keys = list(values.index)

    def colour(_):
        out = pd.DataFrame("", index=disp.index, columns=disp.columns)
        for r, k in enumerate(keys):
            for c, y in enumerate(years):
                sev = cell_sev.get((k, y))
                if sev:
                    out.iat[r, c] = f"background-color: {SEV_COLORS[sev]}"
                elif pd.isna(values.at[k, y]) and k in required:
                    out.iat[r, c] = "background-color: #fde2e1; color: #b42323"
                elif pd.isna(values.at[k, y]):
                    out.iat[r, c] = "color: #9aa3ad"
        return out

    shown = disp.apply(lambda col: col.map(lambda x: "missing" if pd.isna(x) else f"{x:,.2f}"))
    return shown.style.apply(colour, axis=None).set_properties(**{"text-align": "right"})


def _validation(app: AppContext, values: pd.DataFrame, issues: list[D.Issue], groups: dict[str, str]) -> None:
    required = set(D.required_metric_keys(app.profile))
    st.markdown("**Flagged dataset** — red: missing required value or impossible value · amber: implausible / inconsistent · blue: worth a look")
    st.dataframe(_highlight(values, issues, required, app.custom_metrics), height=min(36 * (len(values) + 1) + 3, 720))
    st.markdown("**Issues**")
    if not issues:
        st.success("No issues found.", icon=":material/verified:")
        return
    frame = D.issues_frame(issues, app.custom_metrics)
    sev = st.segmented_control("Show", ["Error", "Warning", "Info"], selection_mode="multi", default=["Error", "Warning", "Info"], key="s2-sev")
    st.dataframe(frame[frame["Severity"].isin(sev or [])], hide_index=True, column_config={"Issue": st.column_config.TextColumn(width="large")})
    with st.expander("What do the checks test?", icon=":material/help:"):
        st.markdown(
            "- **Completeness** — core metrics for every year; sector metrics at least for the latest three years.\n"
            "- **Impossible values** — negative assets or dividends, ratios outside 0–100 %, etc.\n"
            "- **Plausibility** — e.g. a CET1 ratio of 60 % or a solvency ratio below 100 %.\n"
            "- **Accounting identities** — assets = liabilities + equity (+ minorities); EPS × shares ≈ net income; CET1 capital ÷ RWA ≈ CET1 ratio.\n"
            "- **Unit errors** — decimals entered as percent, millions entered as billions, jumps by a factor of five or more."
        )


def _verification(app: AppContext, values: pd.DataFrame, groups: dict[str, str]) -> None:
    years = D.year_columns(values)
    if not years:
        st.info("Add fiscal years first.")
        return
    keys = [k for k in values.index if groups.get(k, "").startswith(("1", "2"))]
    verified = app.progress.setdefault("verified", {})
    refs = app.progress.setdefault("verified_ref", {})
    st.caption(
        "Open the annual report, find each figure and tick it when it matches your dataset. Note the page or note number — "
        "you will need it again in Stage 5. Required: every **core** figure for the latest year."
    )
    grid = pd.DataFrame(index=keys)
    grid["Metric"] = [M.short(k, app.custom_metrics) for k in keys]
    grid["Group"] = [groups.get(k, "")[2:] for k in keys]
    for y in years:
        grid[str(y)] = [bool(verified.get(f"{k}|{y}")) for k in keys]
    grid["Annual report reference"] = [refs.get(k, "") for k in keys]
    with st.form("s2-verify-form", border=False):
        edited = st.data_editor(
            grid,
            hide_index=True,
            disabled=["Metric", "Group"],
            column_config={**{str(y): st.column_config.CheckboxColumn(str(y), help=f"Verified for {y}") for y in years},
                           "Annual report reference": st.column_config.TextColumn(help="e.g. 'AR 2025 p. 187, note 12'", width="medium")},
            key=f"s2-verify-editor-{st.session_state.get('s2-ver', 0)}",
        )
        if st.form_submit_button("Save verification", type="primary", icon=":material/fact_check:"):
            for k in keys:
                for y in years:
                    flag = bool(edited.loc[k, str(y)]) if k in edited.index else False
                    if flag and pd.isna(values.at[k, y]):
                        flag = False  # cannot verify an empty cell
                    if flag:
                        verified[f"{k}|{y}"] = True
                    else:
                        verified.pop(f"{k}|{y}", None)
                refs[k] = str(edited.loc[k, "Annual report reference"] or "")
            app.save()
            _bump()
            st.rerun()


def _import(app: AppContext, values: pd.DataFrame, meta: pd.DataFrame) -> None:
    st.markdown("**Import from CSV or Excel**")
    st.caption(
        "Accepted layouts: (a) wide — first column metric names, then one column per year; (b) years as rows — first column 'year', then one column per metric; "
        "(c) long — columns 'metric', 'year', 'value'. Metric names in English or German are recognised (e.g. 'Net income', 'Konzerngewinn', 'CET1 ratio')."
    )
    up = st.file_uploader("Upload file", type=["csv", "xlsx", "xls"], key="s2-upload")
    if up is not None:
        try:
            imported, report = D.import_table(up.getvalue(), up.name)
        except Exception as exc:  # pandas raises many types for malformed files
            st.error(f"Could not read the file: {exc}")
            imported = None
        if imported is not None:
            st.success(f"Read {len(imported)} rows × {len(report.years)} years ({report.orientation} layout).")
            if report.mapped:
                st.markdown("Recognised: " + ", ".join(f"`{k}` → {M.short(v)}" for k, v in report.mapped.items()))
            if report.unmapped:
                st.warning("Not recognised — will be added as custom metrics: " + ", ".join(f"`{u}`" for u in report.unmapped))
            st.dataframe(imported, height=250)
            mode = st.radio("How to combine", ["Overwrite existing values", "Only fill empty cells"], horizontal=True, key="s2-import-mode")
            if st.button("Apply import", type="primary", key="s2-import-apply", icon=":material/upload:"):
                merged = D.merge_import(values, imported, overwrite=mode.startswith("Overwrite"))
                new_meta = meta.reindex(merged.index).fillna("")
                for k in imported.index:
                    new_meta.at[k, "source"] = f"Imported from {up.name}"
                for k in report.unmapped:
                    key = D.slugify(k)
                    app.custom_metrics.setdefault(key, {"en": k, "de": "", "unit": "money", "higher_is_better": True})
                D.save_working(app.company_id, merged, new_meta)
                app.save()
                _bump()
                st.rerun()

    st.markdown("**Download**")
    out = values.copy()
    out.columns = [str(c) for c in out.columns]
    out.insert(0, "label_en", [M.short(k, app.custom_metrics) for k in out.index])
    out.insert(1, "label_de", [M.get(k).de if M.get(k) else app.custom_metrics.get(k, {}).get("de", "") for k in out.index])
    csv = out.to_csv().encode("utf-8")
    c1, c2 = st.columns(2)
    c1.download_button("Dataset as CSV", csv, file_name=f"{app.company_id}_financials.csv", mime="text/csv", icon=":material/download:")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        out.to_excel(xw, sheet_name="financials")
    c2.download_button("Dataset as Excel", buf.getvalue(), file_name=f"{app.company_id}_financials.xlsx", icon=":material/download:")


def _glossary(app: AppContext, groups: dict[str, str]) -> None:
    rows = []
    for k in D.applicable_metric_keys(app.profile):
        m = M.CATALOG[k]
        rows.append({"English (CFA)": m.en, "Deutsch": m.de, "Unit": M.unit_label(k, app.currency), "Where to find it": m.statement, "What it tells you": m.description})
    st.dataframe(pd.DataFrame(rows), hide_index=True, column_config={"What it tells you": st.column_config.TextColumn(width="large")})
