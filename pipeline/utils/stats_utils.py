from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import chi2_contingency


def chi_square(df: pd.DataFrame, group_col: str, value_col: str) -> dict[str, Any]:
    table = pd.crosstab(df[group_col], df[value_col].fillna("Unknown"))
    if table.shape[0] < 2 or table.shape[1] < 2:
        return {"variable": value_col, "test": "chi_square", "p_value": math.nan, "statistic": math.nan, "dof": math.nan}
    chi2, p_value, dof, _ = chi2_contingency(table)
    return {"variable": value_col, "test": "chi_square", "p_value": float(p_value), "statistic": float(chi2), "dof": int(dof)}


def continuous_tests(df: pd.DataFrame, group_col: str, value_col: str) -> list[dict[str, Any]]:
    work = df[[group_col, value_col]].copy()
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    groups = [g[value_col].dropna().to_numpy() for _, g in work.dropna().groupby(group_col)]
    groups = [g for g in groups if len(g) > 0]
    rows: list[dict[str, Any]] = []
    if len(groups) < 2:
        return [{"variable": value_col, "test": "continuous", "p_value": math.nan, "statistic": math.nan}]
    if len(groups) == 2:
        stat, p_value = stats.ttest_ind(groups[0], groups[1], equal_var=False)
        rows.append({"variable": value_col, "test": "welch_t_test", "p_value": float(p_value), "statistic": float(stat)})
    stat, p_value = stats.f_oneway(*groups)
    rows.append({"variable": value_col, "test": "one_way_anova", "p_value": float(p_value), "statistic": float(stat)})
    stat, p_value = stats.kruskal(*groups)
    rows.append({"variable": value_col, "test": "kruskal_wallis", "p_value": float(p_value), "statistic": float(stat)})
    return rows


def logrank_by_cluster(df: pd.DataFrame, time_col: str, event_col: str, group_col: str) -> dict[str, Any]:
    try:
        from lifelines.statistics import multivariate_logrank_test
    except Exception as exc:  # pragma: no cover
        return {"test": "logrank", "p_value": math.nan, "error": str(exc)}
    work = df[[time_col, event_col, group_col]].dropna().copy()
    if work.empty or work[group_col].nunique() < 2:
        return {"test": "logrank", "p_value": math.nan, "n": int(len(work))}
    result = multivariate_logrank_test(work[time_col], work[group_col], work[event_col])
    return {"test": "logrank", "p_value": float(result.p_value), "statistic": float(result.test_statistic), "n": int(len(work))}

