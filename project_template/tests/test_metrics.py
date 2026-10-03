import numpy as np
import pandas as pd
import pytest

from quantproject import annualized_return, annualized_vol, max_drawdown, sharpe_ratio


def test_vol_matches_definition():
    r = np.array([0.01, -0.02, 0.015, 0.0, -0.005])
    assert annualized_vol(r) == pytest.approx(np.std(r, ddof=1) * np.sqrt(252))


def test_drawdown_known_path():
    assert max_drawdown([0.10, -0.50, 0.20]) == pytest.approx(-0.5)
    assert max_drawdown([0.05, 0.05]) == 0.0
    assert max_drawdown([-0.1, -0.1]) == pytest.approx(0.81 - 1)   # losses from the start count


def test_return_of_constant_growth():
    daily = (1.10) ** (1 / 252) - 1
    assert annualized_return(np.full(504, daily)) == pytest.approx(0.10)


def test_sharpe_sign():
    rng = np.random.default_rng(0)
    assert sharpe_ratio(rng.normal(0.001, 0.01, 1000)) > 0


def test_empty_input_raises():
    with pytest.raises(ValueError):
        annualized_vol(pd.Series([np.nan, np.nan]))
