import numpy as np
import pandas as pd
import pytest

from quantproject import run_backtest


@pytest.fixture
def returns():
    idx = pd.bdate_range("2020-01-01", "2022-12-31")
    rng = np.random.default_rng(1)
    return pd.DataFrame(rng.normal(0, 0.01, (len(idx), 3)), index=idx, columns=list("ABC"))


def test_equal_weight_without_costs_matches_mean(returns):
    bt = run_backtest(returns, lambda h: np.full(3, 1 / 3), lookback=60, cost_bps=0)
    np.testing.assert_allclose(bt["return"], returns.loc[bt.index].mean(axis=1))


def test_no_look_ahead(returns):
    seen = []
    def spy(hist):
        seen.append(hist.index.max())
        return np.full(3, 1 / 3)
    bt = run_backtest(returns, spy, lookback=60)
    first_trade = bt.index.min()
    assert seen[0] < first_trade          # weights were decided before the first return they earn


def test_bad_weights_rejected(returns):
    with pytest.raises(ValueError):
        run_backtest(returns, lambda h: np.array([1.0, 1.0, 1.0]), lookback=60)
