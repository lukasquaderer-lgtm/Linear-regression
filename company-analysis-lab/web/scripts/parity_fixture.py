"""Write the Python reference results that tests/parity.test.mjs compares the JS port with.

    python3 scripts/parity_fixture.py /tmp/parity.json
    PARITY_FILE=/tmp/parity.json npm test
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lab import calculations as C  # noqa: E402
from lab import data as D  # noqa: E402
from lab import ratios as R  # noqa: E402


def num(x):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else float(x)


def main(target: str) -> None:
    out = {}
    for p in D.list_companies():
        cid = p["id"]
        v, meta = D.load_starter(cid)
        v2, _ = D.ensure_rows(v, meta, D.required_metric_keys(p))
        years = D.year_columns(v)
        out[cid] = {
            "issues": [[i.severity, i.metric, i.year] for i in D.validate(v2, p)],
            "trends": {k: C.classify_trend(D.series(v, k), k).label for k in v.index},
            "unusual": [[u["metric"], u["year"]] for u in C.unusual_changes(v)[:10]],
            "ratios": {k: {str(y): num(R.compute(r, v, y).value) for y in years} for k, r in R.RATIOS.items()},
            "roll": {str(y): num((C.implied_other_equity_movements(v, y) or {}).get("other")) for y in years},
        }
    Path(target).write_text(json.dumps(out), encoding="utf-8")
    print(f"wrote {target} ({len(out)} companies)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "parity.json")
