"""A small, honest backtester: weights decided at each rebalance date use only past data."""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd


def _month_ends(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.groupby([index.year, index.month]).max().to_numpy())


def run_backtest(returns: pd.DataFrame,
                 weight_fn: Callable[[pd.DataFrame], np.ndarray],
                 lookback: int = 252,
                 cost_bps: float = 10.0) -> pd.DataFrame:
    """Rebalance monthly. `weight_fn(history)` receives only returns up to the rebalance date.

    Returns a DataFrame with the daily portfolio return (after costs) and the turnover on rebalance days.
    """
    if not isinstance(returns.index, pd.DatetimeIndex):
        raise TypeError("returns must have a DatetimeIndex")
    ends = _month_ends(returns.index)
    out, prev_w = [], np.zeros(returns.shape[1])
    for this_end, next_end in zip(ends[:-1], ends[1:]):
        hist = returns.loc[:this_end].iloc[-lookback:]
        if len(hist) < lookback:
            continue
        w = np.asarray(weight_fn(hist), dtype=float)
        if w.shape != (returns.shape[1],) or not np.isclose(w.sum(), 1.0):
            raise ValueError("weight_fn must return one weight per asset, summing to 1")
        period = returns.loc[(returns.index > this_end) & (returns.index <= next_end)]
        r = period.to_numpy() @ w
        turnover = np.abs(w - prev_w).sum()
        r[0] -= turnover * cost_bps / 1e4
        out.append(pd.DataFrame({"return": r, "turnover": [turnover] + [0.0] * (len(r) - 1)}, index=period.index))
        prev_w = w
    if not out:
        raise ValueError("not enough history for the chosen lookback")
    return pd.concat(out)
