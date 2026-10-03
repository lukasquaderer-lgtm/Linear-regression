"""Tiny helpers for building the notebooks from plain Python source."""
import textwrap
import nbformat as nbf

REPO = "lukasquaderer-lgtm/Linear-regression"
SETUP = '''# Setup: run this cell first (Shift + Enter). Works in Jupyter, VS Code and Google Colab.
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)   # hide library deprecation notices

# Use the local data folder if it exists, otherwise read the CSVs straight from GitHub (e.g. in Colab)
DATA = next((p for p in ["../data/", "../../data/"] if Path(p).exists()), "https://raw.githubusercontent.com/%s/master/data/")
pd.set_option("display.precision", 4)
plt.rcParams["figure.figsize"] = (8, 4)

# Answer checker: after an exercise, check("01.1") tells you whether your answer is right
import sys
if Path("../checks.py").exists():
    sys.path.insert(0, "..")  # solution notebooks live one folder down
try:
    from checks import check, check_all
except ImportError:  # in Colab: fetch the checker from GitHub
    import urllib.request
    urllib.request.urlretrieve("https://raw.githubusercontent.com/%s/master/notebooks/checks.py", "checks.py")
    from checks import check, check_all
print("Ready. Data folder:", DATA)''' % (REPO, REPO)


def md(s):
    return nbf.v4.new_markdown_cell(textwrap.dedent(s).strip())


def code(s):
    return nbf.v4.new_code_cell(textwrap.dedent(s).strip())


def header(fname, title, intro):
    badge = (f"[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)]"
             f"(https://colab.research.google.com/github/{REPO}/blob/master/notebooks/{fname})")
    return [md(f"# {title}\n\n{badge}\n\n" + textwrap.dedent(intro).strip()), code(SETUP)]


def exercise(n, text, hint=None, key=None):
    body = f"### Exercise {n}\n\n" + textwrap.dedent(text).strip()
    if hint:
        body += f"\n\n<details><summary>Hint</summary>\n\n{textwrap.dedent(hint).strip()}\n\n</details>"
    cells = [md(body), code("# Your code here\n")]
    if key:
        cells.append(code(f'check("{key}");   # run me after your code: ✅ correct, ❌ try again, ⬜ not answered yet'))
    return cells


def build(fname, cells):
    nb = nbf.v4.new_notebook()
    nb.cells = cells
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    return nb
