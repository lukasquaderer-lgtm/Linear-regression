"""Reproduce the example: minimum-variance vs equal weight on the course's multi-asset data."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "src"))
from quantproject import run_backtest, summary  # noqa: E402

URL = "https://raw.githubusercontent.com/lukasquaderer-lgtm/Linear-regression/master/data/asset_returns_daily.csv"
local = Path(__file__).parent.parent / "data" / "asset_returns_daily.csv"
rets = pd.read_csv(local if local.exists() else URL, index_col=0, parse_dates=True)


def equal_weight(hist):
    return np.full(hist.shape[1], 1 / hist.shape[1])


def inverse_vol(hist):
    w = 1 / hist.std().to_numpy()
    return w / w.sum()


results = {name: run_backtest(rets, f)["return"] for name, f in [("Equal weight", equal_weight), ("Inverse volatility", inverse_vol)]}
table = pd.DataFrame({k: summary(v, rf=0.005) for k, v in results.items()}).T
print(table.round(3))
Path("reports").mkdir(exist_ok=True)
table.round(4).to_csv(Path("reports") / "example_summary.csv")
print("saved reports/example_summary.csv")
