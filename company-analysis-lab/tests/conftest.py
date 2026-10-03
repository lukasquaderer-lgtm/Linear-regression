import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_workspace(tmp_path, monkeypatch):
    """Every test gets its own empty workspace so the learner's real work is never touched."""
    monkeypatch.setenv("ANALYST_LAB_WORKSPACE", str(tmp_path / "workspace"))
    monkeypatch.delenv("ANALYST_LAB_UNLOCK_ALL", raising=False)
    yield tmp_path / "workspace"


def fill_ubs(values):
    """Complete UBS sector data with round test numbers (not real figures)."""
    fill = {
        "revenue": [35000, 34500, 40800, 48300, 50000],
        "operating_expenses": [25700, 24900, 38400, 41500, 40000],
        "net_interest_income": [6600, 6600, 6500, 6800, 7000],
        "fee_income": [21700, 19000, 22000, 26000, 27500],
        "cet1_ratio": [15.0, 14.2, 14.5, 14.3, 14.4],
        "cost_income_ratio": [70.0, 72.0, 94.0, 85.9, 80.0],
    }
    for k, arr in fill.items():
        for y, x in zip([2021, 2022, 2023, 2024, 2025], arr):
            values.at[k, y] = x
    values.at["eps", 2023] = 8.30
    values.at["dps", 2025] = 1.10
    return values
