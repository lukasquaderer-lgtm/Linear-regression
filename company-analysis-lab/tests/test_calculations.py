import math

import numpy as np
import pandas as pd
import pytest

from lab import calculations as C


def s(vals, start=2021):
    return pd.Series(vals, index=range(start, start + len(vals)), dtype=float)


def test_yoy_growth_basic_and_negative_base():
    g = C.yoy_growth(s([100, 110, -5, 10]))
    assert math.isnan(g[2021])
    assert g[2022] == pytest.approx(10.0)
    assert g[2023] == pytest.approx(-104.5454, rel=1e-4)
    assert math.isnan(g[2024]), "growth from a negative base is not meaningful"


def test_cagr():
    assert C.cagr(100, 146.41, 4) == pytest.approx(10.0, abs=1e-6)
    assert C.cagr(100, 100, 3) == pytest.approx(0.0)
    assert C.cagr(-1, 100, 3) is None
    assert C.cagr(100, 50, 0) is None


def test_series_cagr_uses_first_and_last_available():
    val, y0, y1 = C.series_cagr(s([np.nan, 100, 121, np.nan]))
    assert (y0, y1) == (2022, 2023)
    assert val == pytest.approx(21.0)


def test_average_balance():
    avg = C.average_balance(s([10, 20, 40]))
    assert math.isnan(avg[2021]) and avg[2022] == 15 and avg[2023] == 30


def test_is_close_tolerances():
    assert C.is_close(10.04, 10.0)
    assert not C.is_close(10.5, 10.0)
    assert C.is_close(1000, 1015, rel=0.02)
    assert not C.is_close(None, 1.0)


@pytest.mark.parametrize(
    "vals,key,label",
    [
        ([100, 110, 121, 133, 146], "net_income", "improving"),
        ([100, 90, 81, 73, 66], "net_income", "deteriorating"),
        ([100, 101, 99, 100, 101], "net_income", "stable"),
        ([70, 68, 66, 64, 62], "cost_income_ratio", "improving"),  # lower is better
        ([100, 160, 60, 170, 50], "net_income", "volatile"),
        ([100, 120, 140, 160, 180], "total_assets", "growing"),  # neutral metric
    ],
)
def test_classify_trend(vals, key, label):
    assert C.classify_trend(s(vals), key).label == label


def test_classify_trend_insufficient():
    assert C.classify_trend(s([1, 2]), "net_income").label == "insufficient data"


def test_unusual_changes_ranks_important_metrics():
    df = pd.DataFrame({2021: [100.0, 1000.0, 14.0], 2022: [300.0, 1100.0, 10.0]}, index=["net_income", "total_assets", "cet1_ratio"])
    out = C.unusual_changes(df)
    assert [o["metric"] for o in out] == ["net_income", "cet1_ratio"]
    assert out[1]["unit"] == "pp" and out[1]["change"] == pytest.approx(-4.0)


def test_equity_rollforward():
    df = pd.DataFrame(
        {2024: [1000.0, 100.0, 2.0, 10.0], 2025: [1050.0, 120.0, 2.5, 10.0]},
        index=["total_equity", "net_income", "dps", "shares_outstanding"],
    )
    r = C.implied_other_equity_movements(df, 2025)
    # dividends paid in 2025 = DPS 2024 × shares = 20; other = 50 − (120 − 20) = −50
    assert r["dividends"] == pytest.approx(20)
    assert r["other"] == pytest.approx(-50)


def test_formatting():
    assert C.fmt_num(1234567) == "1'234'567"
    assert C.fmt_pct(12.345) == "12.3 %"
    assert C.fmt_metric(None, "net_income", "CHF") == "–"
