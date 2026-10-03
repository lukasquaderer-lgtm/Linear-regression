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
DATA = "../data/" if Path("../data").exists() else "https://raw.githubusercontent.com/%s/master/data/"
pd.set_option("display.precision", 4)
plt.rcParams["figure.figsize"] = (8, 4)
print("Ready. Data folder:", DATA)''' % REPO


def md(s):
    return nbf.v4.new_markdown_cell(textwrap.dedent(s).strip())


def code(s):
    return nbf.v4.new_code_cell(textwrap.dedent(s).strip())


def header(fname, title, intro):
    badge = (f"[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)]"
             f"(https://colab.research.google.com/github/{REPO}/blob/master/notebooks/{fname})")
    return [md(f"# {title}\n\n{badge}\n\n" + textwrap.dedent(intro).strip()), code(SETUP)]


def exercise(n, text, hint=None):
    body = f"### Exercise {n}\n\n" + textwrap.dedent(text).strip()
    if hint:
        body += f"\n\n<details><summary>Hint</summary>\n\n{textwrap.dedent(hint).strip()}\n\n</details>"
    return [md(body), code("# Your code here\n")]


def build(fname, cells):
    nb = nbf.v4.new_notebook()
    nb.cells = cells
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    return nb
