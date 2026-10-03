import pandas as pd
import pytest

from lab import ratios as R


@pytest.fixture
def values():
    return pd.DataFrame(
        {
            2024: {"net_income": 900.0, "total_equity": 10000.0, "total_assets": 200000.0, "revenue": 4000.0, "operating_expenses": 2600.0, "eps": 3.0, "dps": 1.5},
            2025: {"net_income": 1100.0, "total_equity": 11000.0, "total_assets": 220000.0, "revenue": 4400.0, "operating_expenses": 2750.0, "eps": 3.6, "dps": 1.8},
        }
    )


def test_roe_uses_average_equity(values):
    res = R.compute(R.RATIOS["roe"], values, 2025)
    assert res.value == pytest.approx(1100 / 10500 * 100)
    assert res.alternative == pytest.approx(1100 / 11000 * 100)
    assert [rn.label for rn in res.required][0].startswith("Net income")


def test_roa_leverage_and_dupont_consistency(values):
    roa = R.compute(R.RATIOS["roa"], values, 2025).value
    lev = R.compute(R.RATIOS["leverage"], values, 2025).value
    roe = R.compute(R.RATIOS["roe"], values, 2025).value
    assert roa * lev == pytest.approx(roe)
    d = R.dupont(values, 2025)
    assert d["net_margin"] * d["asset_turnover"] * d["leverage"] == pytest.approx(d["roe"])


def test_missing_prior_year(values):
    res = R.compute(R.RATIOS["roe"], values, 2024)
    assert res.value is None and res.missing


def _inputs(res):
    return {f"{rn.metric}|{rn.year}": rn.value for rn in res.required}


def test_diagnose_correct(values):
    res = R.compute(R.RATIOS["roe"], values, 2025)
    assert R.diagnose(res, _inputs(res), round(res.value, 2)).correct


def test_diagnose_year_end_convention(values):
    res = R.compute(R.RATIOS["roe"], values, 2025)
    d = R.diagnose(res, _inputs(res), 10.0)
    assert not d.correct and "year-end" in d.headline


def test_diagnose_decimal_and_inverted(values):
    res = R.compute(R.RATIOS["net_margin"], values, 2025)
    assert "decimal" in R.diagnose(res, _inputs(res), res.value / 100).headline
    assert "Inverted" in R.diagnose(res, _inputs(res), 4400 / 1100 * 100).headline


def test_diagnose_wrong_inputs_right_method(values):
    res = R.compute(R.RATIOS["net_margin"], values, 2025)
    inputs = _inputs(res)
    inputs["net_income|2025"] = 900.0
    d = R.diagnose(res, inputs, 900 / 4400 * 100)
    assert d.headline.startswith("Wrong inputs")


def test_available_ratios_respects_sector_and_not_applicable(values):
    bank = {"sector": "bank", "not_applicable": []}
    keys = [r.key for r in R.available_ratios(bank, values)]
    assert "cost_income" in keys and "insurance_margin" not in keys
    ins = {"sector": "insurer", "not_applicable": ["dps"]}
    keys = [r.key for r in R.available_ratios(ins, values)]
    assert "cost_income" not in keys and "payout" not in keys
