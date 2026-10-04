import io

import numpy as np
import pandas as pd
import pytest

from lab import data as D
from lab import metrics as M

COMPANIES = ["ubs", "llb", "gkb", "swiss_life", "swiss_re", "prismalife", "roche", "novartis", "hilti"]


def test_all_companies_load():
    ids = [c["id"] for c in D.list_companies()]
    assert set(ids) >= set(COMPANIES)
    for cid in COMPANIES:
        p = D.load_profile(cid)
        v, meta = D.load_starter(cid)
        assert p["sector"] in M.SECTORS
        assert D.year_columns(v) == [2021, 2022, 2023, 2024, 2025]
        assert set(v.index) <= set(M.CATALOG), f"{cid} has unknown metric keys"
        for key in ("what_it_does", "how_money", "segments", "customers", "markets", "advantages", "threats"):
            assert key in p["business_reference"], f"{cid} lacks reference for {key}"


def test_every_metric_is_bilingual():
    for m in M.CATALOG.values():
        assert m.en and m.de and m.en != m.de


def test_starter_balance_sheets_are_consistent():
    for cid in ("ubs", "llb", "gkb", "swiss_life", "swiss_re", "roche", "novartis"):
        p = D.load_profile(cid)
        v, _ = D.load_starter(cid)
        errors = [i for i in D.validate(v, p) if i.metric == "total_assets" and i.severity == "error"]
        assert not errors, errors


def test_validation_flags_missing_impossible_and_units():
    p = D.load_profile("ubs")
    v, meta = D.load_starter("ubs")
    v, meta = D.ensure_rows(v, meta, D.required_metric_keys(p))
    v.at["dps", 2024] = -1  # impossible
    v.at["cet1_ratio", 2025] = 0.143  # decimal instead of percent
    v.at["total_assets", 2022] = 1104.364  # unit slip (bn instead of m)
    msgs = [(i.severity, i.metric, i.year, i.message) for i in D.validate(v, p)]
    assert any(s == "error" and m == "revenue" for s, m, y, _ in msgs), "missing revenue must be an error"
    assert any(s == "error" and m == "dps" and y == 2024 for s, m, y, _ in msgs)
    assert any(m == "cet1_ratio" and "decimal" in t for s, m, y, t in msgs)
    assert any(m == "total_assets" and y == 2022 and s == "error" for s, m, y, t in msgs)


def test_validation_passes_complete_dataset():
    from conftest import fill_ubs

    p = D.load_profile("ubs")
    v, meta = D.load_starter("ubs")
    v, meta = D.ensure_rows(v, meta, D.required_metric_keys(p))
    fill_ubs(v)
    assert not [i for i in D.validate(v, p) if i.severity == "error"]


def test_eps_shares_consistency_check():
    p = D.load_profile("llb")
    v, _ = D.load_starter("llb")
    v.at["shares_outstanding", 2025] = 30439  # thousands instead of millions
    assert any(i.metric == "eps" and i.year == 2025 for i in D.validate(v, p))


def test_required_metrics_respect_profile():
    pl = D.load_profile("prismalife")
    req = D.required_metric_keys(pl)
    assert "eps" not in req and "solvency_ratio" in req and "gross_premiums" in req
    sr = D.load_profile("swiss_re")
    assert "combined_ratio" in D.required_metric_keys(sr)


@pytest.mark.parametrize(
    "raw,decimal_comma,expected",
    [("1'234.5", False, 1234.5), ("1,234.5", False, 1234.5), ("1.234,5", True, 1234.5), ("(12)", False, -12.0), ("14.3 %", False, 14.3), ("–", False, np.nan), (7, False, 7.0)],
)
def test_parse_number(raw, decimal_comma, expected):
    out = D.parse_number(raw, decimal_comma)
    assert (np.isnan(out) and np.isnan(expected)) or out == pytest.approx(expected)


def test_import_wide_german_semicolon():
    text = "Kennzahl;2021;2022\nKonzerngewinn;129,9;147,5\nCET1 ratio (%);21,1;20,5\nMy KPI;1;2\n"
    df, rep = D.import_table(text.encode(), "x.csv")
    assert df.at["net_income", 2022] == pytest.approx(147.5)
    assert df.at["cet1_ratio", 2021] == pytest.approx(21.1)
    assert rep.unmapped == ["My KPI"] and "my_kpi" in df.index


def test_import_long_transposed_and_excel():
    df, rep = D.import_table(b"metric,year,value\nnet_income,2024,167.1\nTotal assets,2024,27773\n", "y.csv")
    assert rep.orientation == "long" and df.at["total_assets", 2024] == 27773
    df, rep = D.import_table(b"year,Revenue,Net income\n2023,541.8,164.6\n2024,556.6,167.1\n", "z.csv")
    assert rep.orientation == "transposed" and df.at["revenue", 2024] == pytest.approx(556.6)
    buf = io.BytesIO()
    pd.DataFrame({"metric": ["eps", "dps"], "2024": [5.44, 2.8]}).to_excel(buf, index=False)
    df, rep = D.import_table(buf.getvalue(), "w.xlsx")
    assert df.at["dps", 2024] == pytest.approx(2.8)


def test_import_rejects_files_without_years():
    with pytest.raises(ValueError):
        D.import_table(b"a,b\nx,y\n", "bad.csv")


def test_merge_import_overwrite_and_fill():
    v = pd.DataFrame({2024: [1.0, np.nan]}, index=["net_income", "revenue"])
    imp = pd.DataFrame({2024: [2.0, 5.0], 2025: [3.0, 6.0]}, index=["net_income", "revenue"])
    assert D.merge_import(v, imp, overwrite=True).at["net_income", 2024] == 2.0
    filled = D.merge_import(v, imp, overwrite=False)
    assert filled.at["net_income", 2024] == 1.0 and filled.at["revenue", 2024] == 5.0 and 2025 in filled.columns


def test_working_copy_roundtrip_keeps_starter_clean():
    v, meta = D.load_starter("llb")
    v.at["net_income", 2025] = 999.0
    D.save_working("llb", v, meta)
    assert D.load_working("llb")[0].at["net_income", 2025] == 999.0
    assert D.load_starter("llb")[0].at["net_income", 2025] != 999.0
    D.reset_working("llb")
    assert D.load_working("llb")[0].at["net_income", 2025] != 999.0


def test_create_company(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "DATASETS_DIR", tmp_path / "companies")
    (tmp_path / "companies").mkdir()
    cid = D.create_company("Test Bank AG", "bank", "CHF", "Switzerland")
    assert cid == "test_bank_ag"
    p = D.load_profile(cid)
    v, _ = D.load_starter(cid)
    assert p["sector"] == "bank" and set(D.required_metric_keys(p)) <= set(v.index)


def test_corporate_required_metrics_and_validation():
    p = D.load_profile("roche")
    req = D.required_metric_keys(p)
    for key in ("ebit", "operating_cash_flow", "capex", "depreciation_amortisation", "total_debt", "cash"):
        assert key in req
    assert "aum" not in D.applicable_metric_keys(p), "AuM is a financial-sector metric"
    v, meta = D.load_starter("roche")
    v, meta = D.ensure_rows(v, meta, req + ["gross_profit", "free_cash_flow"])
    assert not [i for i in D.validate(v, p) if i.severity == "error"], "Roche starter data should have no errors"
    v.at["capex", 2024] = -5009  # sign error
    v.at["gross_profit", 2023] = 70000  # above revenue
    v.at["total_debt", 2022] = 90000  # above liabilities
    v.at["free_cash_flow", 2025] = 5000  # own definition far from OCF − capex
    msgs = [(i.severity, i.metric, i.year) for i in D.validate(v, p)]
    assert ("error", "capex", 2024) in msgs
    assert ("error", "gross_profit", 2023) in msgs
    assert ("error", "total_debt", 2022) in msgs
    assert ("info", "free_cash_flow", 2025) in msgs


def test_unlisted_corporate_excludes_per_share_metrics():
    p = D.load_profile("hilti")
    assert p["sector"] == "corporate" and not p["listed"]
    assert not {"eps", "dps", "shares_outstanding"} & set(D.required_metric_keys(p))
