import pytest

from lab import valuation as V


def test_multiples():
    assert V.pe(30, 2.5) == pytest.approx(12)
    assert V.pe(30, -1) is None
    assert V.pb(30, 25) == pytest.approx(1.2)
    assert V.dividend_yield(1.5, 30) == pytest.approx(0.05)


def test_capm_and_growth():
    assert V.capm(0.01, 1.2, 0.05) == pytest.approx(0.07)
    assert V.sustainable_growth(0.12, 0.6) == pytest.approx(0.048)


def test_justified_pb_and_implied_roe_roundtrip():
    pb = V.justified_pb(0.12, 0.09, 0.02)
    assert pb == pytest.approx(10 / 7)
    assert V.implied_roe_from_pb(pb, 0.09, 0.02) == pytest.approx(0.12)
    assert V.justified_pb(0.12, 0.02, 0.03) is None  # r <= g
    assert V.justified_pb(0.09, 0.09, 0.02) == pytest.approx(1.0)  # ROE = r → P/B = 1


def test_gordon_and_two_stage():
    assert V.gordon_ddm(2.0, 0.08, 0.03) == pytest.approx(2.06 / 0.05)
    ts = V.two_stage_ddm(2.0, 0.03, 5, 0.03, 0.08)
    assert ts["value"] == pytest.approx(V.gordon_ddm(2.0, 0.08, 0.03), rel=1e-9)


def test_residual_income_equals_book_value_when_roe_equals_r():
    ri = V.residual_income(100.0, 0.09, 0.09, 0.02, 0.5)
    assert ri["value"] == pytest.approx(100.0)
    higher = V.residual_income(100.0, 0.12, 0.09, 0.02, 0.5)
    faded = V.residual_income(100.0, 0.12, 0.09, 0.02, 0.5, fade_to_r=True)
    assert higher["value"] > faded["value"] > 100.0


def test_bank_fcfe_and_sensitivity():
    assert V.bank_distributable_fcfe(1000, 20000, 0.05, 0.14) == pytest.approx(860)
    grid = V.sensitivity_grid(lambda r, g: V.justified_pb(0.12, r, g), [0.08, 0.10], [0.02, 0.09])
    assert grid.shape == (2, 2)
    assert grid[0, 1] != grid[0, 1]  # NaN where r <= g
