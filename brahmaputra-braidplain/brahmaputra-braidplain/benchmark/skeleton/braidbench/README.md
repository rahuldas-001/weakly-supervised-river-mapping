# braidbench

Multi-class, multi-temporal benchmark for braided river geomorphic units.
Classes: background, water, bare bar, vegetated bar.

Status: in development. Not yet released.

---

## Working in Colab with a proper repo

Code lives here. Data lives in Drive during development and on Zenodo at release.
Notebooks are thin drivers, not the codebase.

### Bootstrap cell

Every notebook starts with exactly this, and nothing else in the setup line:

```python
!pip -q install "git+https://github.com/<user>/braidbench.git@main#egg=braidbench[train]"

import braidbench
from braidbench import colab, config

COMMIT = colab.setup()          # mounts Drive, initialises Earth Engine
CFG    = config.load()          # reads configs/default.yaml
print(f"braidbench {braidbench.__version__} @ {COMMIT}")
```

For active development, clone in editable mode instead so edits are picked up:

```python
!git clone -q https://github.com/<user>/braidbench.git /content/braidbench
!pip -q install -e /content/braidbench
```

### The rule

If a notebook cell defines a function, it belongs in `src/braidbench/`.
Notebooks call functions, display figures, and record decisions. Nothing else.

This matters because ESSD reviewers read the repository. A repo of nine
notebooks with 11,000-character cells cannot be reviewed; a package with thin
drivers can.

---

## Repository layout

```
configs/          all parameters, one file, version controlled
src/braidbench/   the actual code
notebooks/        thin drivers, outputs stripped
scripts/          command-line entry points for long jobs
docs/             class definitions, annotation protocol, split rationale
```

Data directories are gitignored. `config.data_root` resolves to the Drive folder
on Colab and `./data` locally; override with `BRAIDBENCH_DATA`.

---

## Notebook hygiene

Install the output stripper once, per clone:

```bash
pip install nbstripout
nbstripout --install --attributes .gitattributes
```

This strips outputs on commit automatically. Without it the repo accumulates
base64 image blobs and every diff is unreadable.

---

## Secrets

Earth Engine project ID and any credentials are read from environment variables
or Colab secrets (`userdata.get("EE_PROJECT")`). They are never committed.
`configs/default.yaml` has `ee_project: null` deliberately.

---

## Reproducibility

`colab.setup()` returns the git commit hash. Write it into the metadata of every
artefact produced. When a number in the paper is questioned, the commit that
produced it should be recoverable.

Dependencies are pinned in `pyproject.toml`. Before submission, freeze exact
versions into `requirements-lock.txt`.

---

## Data release

Working data stays in Drive. It is not committed, not in git-lfs, and not in the
repo in any form. At release the dataset goes to Zenodo under CC BY 4.0 with a
DOI, and the repo links to it. ESSD requires the DOI to exist at submission.

---

## Known issues carried over from the prototype pipeline

- The original `create_splits()` assigned tiles randomly while tiles overlapped
  by 10%. This leaks ground truth between train and test. Replaced by spatial
  block splitting in `splits.py`. Any metric computed before this fix is
  optimistic by an unknown margin.
- Class 2 was named `active_bar`. Renamed to `bare_bar`: the classifier detects
  absence of vegetation, not sediment mobility.
