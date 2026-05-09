# LUNG Reproduction Environment

- Date: 2026-04-29
- Scope: minimum environment to rerun current `Step5 -> Step6 -> Step7`

## Required tools

- `python3` 3.11 or 3.12
- `aws` CLI v2
- `git`

## Required Python packages

- `pandas`
- `numpy`
- `scipy`
- `scikit-learn`
- `pyarrow`
- `rdkit`

## Optional tools

- `nextflow`
- Java runtime for Nextflow

> Optional tools are only needed if someone wants to rebuild earlier FE stages.
> Current Step5-Step7 rerun does not require re-running the FE workflow.

## Install example

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install pandas numpy scipy scikit-learn pyarrow rdkit
```

## Runtime assumptions

- The teammate has the same repo checked out locally.
- The S3 bootstrap is restored into the workspace root so the relative paths used by the current scripts remain valid.
- Current reproduction target is `All Lung`, not `NSCLC-only`.
