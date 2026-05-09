#!/usr/bin/env python3
"""
Flatten Step 4 metric JSONs (ml / dl / graph) under ``results/<RESULT_TAG>/``.

**Approval table (fixed):** one wide row per (family, stem, model) with
``sp_cv5``, ``sp_groupcv``, ``sp_scaffoldcv`` (validation Spearman means)
and ``gap_cv5``, ``gap_groupcv``, ``gap_scaffoldcv`` (train−val gap means).

Also writes the full long-format extract as ``*_long.csv`` for audit.

Reads ``<stem>_<eval_mode>.json`` (holdout, cv5, groupcv, scaffoldcv).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

KNOWN_EVAL_SUFFIXES: tuple[str, ...] = ("holdout", "cv5", "groupcv", "scaffoldcv")

# Fixed columns for human sign-off before Step 5 ensemble (5-fold = cv5 in repo naming).
REVIEW_EVAL_MODES: tuple[str, ...] = ("cv5", "groupcv", "scaffoldcv")


def split_stem_eval(filename_stem: str) -> tuple[str, str] | None:
    """Split ``stad_numeric_ml_v1_groupcv`` -> (``stad_numeric_ml_v1``, ``groupcv``)."""
    for em in KNOWN_EVAL_SUFFIXES:
        suf = "_" + em
        if filename_stem.endswith(suf):
            return filename_stem[: -len(suf)], em
    return None


def _warn_txt(payload: dict[str, Any]) -> str | None:
    oc = payload.get("overfitting_check")
    if isinstance(oc, dict) and oc.get("warning"):
        return str(oc["warning"])
    sc = payload.get("stability_check")
    if isinstance(sc, dict) and sc.get("warning"):
        return str(sc["warning"])
    return None


def rows_from_json(path: Path, family: str) -> list[dict[str, Any]]:
    parsed = split_stem_eval(path.stem)
    if parsed is None:
        return []
    stem_prefix, eval_mode = parsed
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for model_name, payload in raw.items():
        if not isinstance(payload, dict):
            continue
        summ = payload.get("summary") or {}
        rows.append(
            {
                "family": family,
                "stem": stem_prefix,
                "eval_mode": eval_mode,
                "model": model_name,
                "train_spearman_mean": summ.get("train_spearman_mean"),
                "val_spearman_mean": summ.get("val_spearman_mean"),
                "train_spearman_std": summ.get("train_spearman_std"),
                "val_spearman_std": summ.get("val_spearman_std"),
                "gap_spearman_mean": summ.get("gap_spearman_mean"),
                "diagnostic": _warn_txt(payload),
                "json_file": path.name,
            }
        )
    return rows


def gather_long(project_root: Path, result_tag: str) -> pd.DataFrame:
    root = project_root / "results" / result_tag
    all_rows: list[dict[str, Any]] = []
    for family in ("ml", "dl", "graph"):
        sub = root / family
        if not sub.is_dir():
            continue
        for path in sorted(sub.glob("*.json")):
            all_rows.extend(rows_from_json(path, family))
    if not all_rows:
        return pd.DataFrame()
    df = pd.DataFrame(all_rows)
    sort_cols = [c for c in ("family", "stem", "eval_mode", "model") if c in df.columns]
    return df.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)


def build_wide_review(df_long: pd.DataFrame) -> pd.DataFrame:
    """Pivot to sp_/gap_ columns for cv5, groupcv, scaffoldcv only."""
    sub = df_long[df_long["eval_mode"].isin(REVIEW_EVAL_MODES)].copy()
    if sub.empty:
        return pd.DataFrame()
    idx = ["family", "stem", "model"]
    sp = sub.pivot_table(index=idx, columns="eval_mode", values="val_spearman_mean", aggfunc="first")
    gap = sub.pivot_table(index=idx, columns="eval_mode", values="gap_spearman_mean", aggfunc="first")
    sp = sp.rename(columns={m: f"sp_{m}" for m in sp.columns})
    gap = gap.rename(columns={m: f"gap_{m}" for m in gap.columns})
    wide = sp.join(gap, how="outer")
    wide = wide.reset_index()
    front = list(idx)
    # Fixed column order: Spearman block then gap block (same eval order).
    ordered: list[str] = []
    for m in REVIEW_EVAL_MODES:
        c = f"sp_{m}"
        if c in wide.columns:
            ordered.append(c)
    for m in REVIEW_EVAL_MODES:
        c = f"gap_{m}"
        if c in wide.columns:
            ordered.append(c)
    extra = [c for c in wide.columns if c not in front + ordered]
    wide = wide[front + ordered + extra]
    return wide.sort_values(idx, kind="mergesort").reset_index(drop=True)


def write_md_preview(df: pd.DataFrame, path: Path, max_rows: int) -> None:
    prev = df.head(max_rows) if max_rows > 0 else df
    lines = [
        "# Step 4 metrics review",
        "",
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"- Rows in full CSV: {len(df)}",
        "",
    ]
    if len(df) > len(prev):
        lines.append(f"_Showing first {len(prev)} rows; open CSV for full table._")
        lines.append("")
    lines.append(prev.to_markdown(index=False))
    lines.append("")
    lines.append(
        "_Columns: **sp_cv5** = 5-fold CV validation Spearman; **sp_groupcv**, **sp_scaffoldcv** = "
        "same for GroupCV / ScaffoldCV; **gap_*** = mean train−val Spearman gap per eval mode._"
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description="Summarize Step 4 ML/DL/Graph metric JSONs into one table.")
    p.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root containing results/ and reports/ (default: STAD repo root).",
    )
    p.add_argument("--result-tag", required=True, help="Under results/<tag>/")
    p.add_argument(
        "--max-print-rows",
        type=int,
        default=60,
        help="Rows printed to stdout (0 = print full frame). Default 60.",
    )
    p.add_argument(
        "--md-preview-rows",
        type=int,
        default=80,
        help="Rows included in the Markdown sidecar (0 = all). Default 80.",
    )
    args = p.parse_args()
    project_root = args.project_root.resolve()
    df_long = gather_long(project_root, args.result_tag)
    reports = project_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    csv_wide_path = reports / f"step4_metrics_review_{args.result_tag}.csv"
    csv_long_path = reports / f"step4_metrics_review_{args.result_tag}_long.csv"
    md_path = reports / f"step4_metrics_review_{args.result_tag}.md"

    if df_long.empty:
        msg = (
            f"No metric JSON rows found under {project_root / 'results' / args.result_tag} "
            f"(expected ml|dl|graph/*_<eval>.json)."
        )
        print(msg, flush=True)
        csv_wide_path.write_text(msg + "\n", encoding="utf-8")
        md_path.write_text(f"# Step 4 metrics review\n\n_{msg}_\n", encoding="utf-8")
        raise SystemExit(1)

    df_long.to_csv(csv_long_path, index=False)
    df_wide = build_wide_review(df_long)
    if df_wide.empty:
        msg = (
            f"No rows for eval modes {list(REVIEW_EVAL_MODES)} — check that cv5 / groupcv / scaffoldcv "
            f"JSONs exist under results/{args.result_tag}/."
        )
        print(msg, flush=True)
        csv_wide_path.write_text(msg + "\n", encoding="utf-8")
        md_path.write_text(f"# Step 4 metrics review (wide)\n\n_{msg}_\n", encoding="utf-8")
        raise SystemExit(1)

    df_wide.to_csv(csv_wide_path, index=False)
    write_md_preview(df_wide, md_path, args.md_preview_rows if args.md_preview_rows > 0 else len(df_wide))

    print(f"[summarize_step4_metrics_stad] Wrote wide approval table: {csv_wide_path}", flush=True)
    print(f"[summarize_step4_metrics_stad] Wrote long extract: {csv_long_path}", flush=True)
    print(f"[summarize_step4_metrics_stad] Wrote {md_path}", flush=True)
    print("", flush=True)
    print(
        "Columns: sp_cv5 = 5-fold CV val Spearman | sp_groupcv | sp_scaffoldcv | "
        "gap_* = mean train−val Spearman gap per mode.",
        flush=True,
    )
    print("", flush=True)
    cap = None if args.max_print_rows == 0 else args.max_print_rows
    with pd.option_context("display.max_rows", cap, "display.width", 240, "display.max_columns", 20):
        print(df_wide.to_string(index=False))
    print("", flush=True)
    print(
        "[summarize_step4_metrics_stad] Review the wide CSV, then run Step 5 ensemble when satisfied.",
        flush=True,
    )


if __name__ == "__main__":
    main()
