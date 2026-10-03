"""Performance metrics for a series of periodic (e.g. daily) returns."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _as_series(returns) -> pd.Series:
    r = pd.Series(returns, dtype=float).dropna()
    if r.empty:
        raise ValueError("returns is empty after dropping missing values")
    return r


def annualized_return(returns, periods: int = 252) -> float:
    """Geometric (compound) annual return."""
    r = _as_series(returns)
    return float((1 + r).prod() ** (periods / len(r)) - 1)


def annualized_vol(returns, periods: int = 252) -> float:
    """Sample standard deviation scaled by sqrt(periods)."""
    r = _as_series(returns)
    return float(r.std(ddof=1) * np.sqrt(periods))


def sharpe_ratio(returns, rf: float = 0.0, periods: int = 252) -> float:
    """Annualised Sharpe ratio; rf is an annual risk-free rate."""
    r = _as_series(returns) - rf / periods
    return float(r.mean() / r.std(ddof=1) * np.sqrt(periods))


def max_drawdown(returns) -> float:
    """Largest peak-to-trough loss of cumulative wealth, as a negative number (0 if none)."""
    r = _as_series(returns)
    wealth = np.concatenate([[1.0], (1 + r).cumprod().to_numpy()])
    return float((wealth / np.maximum.accumulate(wealth) - 1).min())


def summary(returns, rf: float = 0.0, periods: int = 252) -> pd.Series:
    """All headline metrics in one Series."""
    return pd.Series({
        "ann. return": annualized_return(returns, periods),
        "ann. vol": annualized_vol(returns, periods),
        "Sharpe": sharpe_ratio(returns, rf, periods),
        "max drawdown": max_drawdown(returns),
    })
