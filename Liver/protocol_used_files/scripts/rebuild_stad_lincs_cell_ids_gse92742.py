#!/usr/bin/env python3
"""
Rebuild ``configs/stad_lincs_cell_ids.json`` from **GSE92742 only** ``cell_info`` + ``sig_info``.

Reads raw gz under ``curated_data/lincs/GSE92742/`` (read-only). Writes:
  - ``configs/stad_lincs_cell_ids.json`` — usable ``cell_id`` values with ``trt_cp`` in sig_info
  - ``reports/lincs/stad_lincs_cell_id_review.csv``
  - ``reports/lincs/stad_lincs_cell_id_qc.json``
  - ``logs/rebuild_stad_lincs_cell_ids_<ts>.log``

Input / output shapes:
  - Input: gzipped TSVs (cell_info ~hundreds of rows; sig_info hundreds of thousands of rows).
  - Output: JSON list length = count of usable cells; CSV one row per input candidate + discovery rows;
    QC JSON with counts and grouping summaries.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

# Reference (Colon): ../20260420_new_pre_project_biso_Colon/scripts/extract_lincs_gctx.py


def normalize_cell_token(s: str) -> str:
    """Normalize for fuzzy cell_id comparison (Lung/Colon name policy aligned)."""
    t = str(s).strip().upper()
    t = re.sub(r"\s+", "", t)
    for ch in ("-", "_", ".", "/"):
        t = t.replace(ch, "")
    return t


def log_line(path: Path, msg: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}", flush=True)


def load_json_candidates(path: Path) -> List[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cells = data.get("cell_ids")
    if not isinstance(cells, list) or not cells:
        raise ValueError(f"{path}: cell_ids must be a non-empty list")
    return [str(x).strip() for x in cells if str(x).strip()]


def build_cell_info_maps(df: pd.DataFrame) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """exact cell_id -> cell_id; normalized -> list of cell_id (for collision detection)."""
    exact: Dict[str, str] = {}
    norm_map: Dict[str, List[str]] = defaultdict(list)
    for cid in df["cell_id"].astype(str).unique():
        exact[cid] = cid
        norm_map[normalize_cell_token(cid)].append(cid)
    return exact, dict(norm_map)


def alias_suggestions_for_name(
    name: str,
    norm_map: Dict[str, List[str]],
    all_norms: Sequence[str],
    all_cell_ids: Sequence[str],
    k: int = 8,
) -> str:
    """
    Map difflib close tokens to concrete cell_id strings (review only; never auto-assign).

    1) normalized token space (relaxed cutoff)
    2) raw cell_id string space (catches e.g. TYRO3_MKN45 style ids if any)
    """
    nn = normalize_cell_token(name)
    resolved: List[str] = []

    close_norm = difflib.get_close_matches(nn, list(all_norms), n=k, cutoff=0.72)
    for cn in close_norm:
        resolved.extend(str(x) for x in norm_map.get(cn, []))

    close_raw = difflib.get_close_matches(name, list(all_cell_ids), n=k, cutoff=0.65)
    for cid in close_raw:
        resolved.append(str(cid))

    seen = set()
    out: List[str] = []
    for x in resolved:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return "|".join(out)


def match_candidate_to_cell_info(
    name: str,
    exact: Dict[str, str],
    norm_map: Dict[str, List[str]],
    all_norms: Sequence[str],
) -> Tuple[Optional[str], str, str]:
    """
    Returns (matched_cell_id or None, match_type, note).
    match_type: exact | normalized | unmatched | ambiguous_normalized
    """
    if name in exact:
        return name, "exact", ""
    nn = normalize_cell_token(name)
    hits = norm_map.get(nn, [])
    if len(hits) == 1:
        return hits[0], "normalized", ""
    if len(hits) > 1:
        return None, "ambiguous_normalized", f"cell_info hits={hits}"
    close = difflib.get_close_matches(nn, list(all_norms), n=5, cutoff=0.82)
    if close:
        return None, "unmatched", f"suggested_norms={close}"
    return None, "unmatched", "no close normalized match in cell_info"


def load_sig_trt_cp_counts(sig_path: Path, log_path: Path) -> pd.Series:
    log_line(log_path, f"I/O read sig_info (trt_cp only) columns pert_type,cell_id <- {sig_path}")
    usecols = ["pert_type", "cell_id"]
    sig = pd.read_csv(sig_path, sep="\t", compression="gzip", usecols=usecols, low_memory=False)
    tr = sig[sig["pert_type"] == "trt_cp"]
    vc = tr["cell_id"].value_counts()
    log_line(log_path, f"sig_info trt_cp rows={len(tr):,} unique cell_id={vc.shape[0]}")
    return vc


def stomach_cell_ids_from_cell_info(df: pd.DataFrame) -> List[str]:
    """cell_info rows whose primary_site or subtype mentions stomach/gastric."""
    ps = df["primary_site"].astype(str).str.contains(r"stomach|gastric", case=False, na=False)
    st = df["subtype"].astype(str).str.contains(r"stomach|gastric", case=False, na=False)
    sub = df[ps | st]
    return sorted(sub["cell_id"].astype(str).unique().tolist())


@dataclass
class ReviewRow:
    input_name: str
    normalized_input: str
    matched_cell_id: str
    match_type: str
    in_cell_info: bool
    in_sig_info_trt_cp: bool
    trt_cp_signature_count: int
    note: str
    alias_suggestions: str = ""
    row_kind: str = "candidate"  # candidate | stomach_discovery


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-root", type=Path, default=None)
    p.add_argument("--gse", type=str, default="GSE92742")
    p.add_argument(
        "--candidates-json",
        type=Path,
        default=None,
        help=(
            "JSON with cell_ids candidate list (read-only). "
            "Default: configs/stad_lincs_cell_ids_candidates_seed.json so reruns stay reproducible."
        ),
    )
    args = p.parse_args()

    root = (args.project_root or Path(__file__).resolve().parent.parent).resolve()
    gse: str = args.gse
    lincs_dir = root / "curated_data" / "lincs" / gse
    cell_info = lincs_dir / f"{gse}_Broad_LINCS_cell_info.txt.gz"
    sig_info = lincs_dir / f"{gse}_Broad_LINCS_sig_info.txt.gz"
    cand_path = (
        args.candidates_json or (root / "configs" / "stad_lincs_cell_ids_candidates_seed.json")
    ).resolve()

    ts = time.strftime("%Y%m%d_%H%M%S")
    log_path = root / "logs" / f"rebuild_stad_lincs_cell_ids_{ts}.log"
    log_line(log_path, f"START project_root={root} gse={gse}")

    if not cell_info.is_file():
        raise FileNotFoundError(f"Missing cell_info: {cell_info}")
    if not sig_info.is_file():
        raise FileNotFoundError(f"Missing sig_info: {sig_info}")

    log_line(log_path, f"I/O read cell_info <- {cell_info}")
    cell_df = pd.read_csv(cell_info, sep="\t", compression="gzip", low_memory=False)
    if "cell_id" not in cell_df.columns:
        raise ValueError("cell_info missing cell_id column")

    exact_map, norm_map = build_cell_info_maps(cell_df)
    all_cell_ids_sorted = sorted(cell_df["cell_id"].astype(str).unique().tolist())
    all_norms = sorted({normalize_cell_token(x) for x in all_cell_ids_sorted})

    sig_counts = load_sig_trt_cp_counts(sig_info, log_path)
    sig_cell_set = set(sig_counts.index.astype(str))

    candidates = load_json_candidates(cand_path)
    log_line(log_path, f"Loaded {len(candidates)} candidate names from {cand_path}")

    review_rows: List[ReviewRow] = []

    for name in candidates:
        nn = normalize_cell_token(name)
        matched, mtype, note = match_candidate_to_cell_info(name, exact_map, norm_map, all_norms)
        in_ci = matched is not None
        cnt = int(sig_counts.get(matched, 0)) if matched else 0
        in_sig = matched is not None and matched in sig_cell_set and cnt > 0
        alias = (
            alias_suggestions_for_name(name, norm_map, all_norms, all_cell_ids_sorted)
            if matched is None
            else ""
        )
        review_rows.append(
            ReviewRow(
                input_name=name,
                normalized_input=nn,
                matched_cell_id=matched or "",
                match_type=mtype,
                in_cell_info=in_ci,
                in_sig_info_trt_cp=in_sig,
                trt_cp_signature_count=cnt,
                note=note,
                alias_suggestions=alias,
                row_kind="candidate",
            )
        )

    # Discovery: stomach/gastric annotation in cell_info plate
    stomach_ids = stomach_cell_ids_from_cell_info(cell_df)
    log_line(log_path, f"cell_info stomach|gastric annotated cell_id count={len(stomach_ids)} -> {stomach_ids}")
    for cid in stomach_ids:
        if cid in {c.input_name for c in review_rows if c.row_kind == "candidate"}:
            continue
        nn = normalize_cell_token(cid)
        cnt = int(sig_counts.get(cid, 0))
        in_sig = cid in sig_cell_set and cnt > 0
        review_rows.append(
            ReviewRow(
                input_name=f"(discovery){cid}",
                normalized_input=nn,
                matched_cell_id=cid,
                match_type="discovery_cell_info",
                in_cell_info=True,
                in_sig_info_trt_cp=in_sig,
                trt_cp_signature_count=cnt,
                note="primary_site or subtype mentions stomach/gastric",
                alias_suggestions="",
                row_kind="stomach_discovery",
            )
        )

    # Final usable = matched_cell_id from rows where in_cell_info and in_sig_info_trt_cp
    usable: List[str] = sorted(
        {
            r.matched_cell_id
            for r in review_rows
            if r.matched_cell_id and r.in_cell_info and r.in_sig_info_trt_cp
        }
    )

    out_json = root / "configs" / "stad_lincs_cell_ids.json"
    out_review = root / "reports" / "lincs" / "stad_lincs_cell_id_review.csv"
    out_qc = root / "reports" / "lincs" / "stad_lincs_cell_id_qc.json"

    out_review.parent.mkdir(parents=True, exist_ok=True)
    rev_df = pd.DataFrame([r.__dict__ for r in review_rows])
    rev_df.to_csv(out_review, index=False)
    log_line(log_path, f"I/O write {out_review}")

    cand_rows = [r for r in review_rows if r.row_kind == "candidate"]
    matched_in_ci = sum(1 for r in cand_rows if r.in_cell_info)
    matched_in_sig = sum(1 for r in cand_rows if r.in_sig_info_trt_cp)
    auto_ok = [
        r
        for r in cand_rows
        if r.match_type in ("exact", "normalized") and r.in_cell_info and r.in_sig_info_trt_cp
    ]
    need_review = [
        r
        for r in cand_rows
        if r.match_type == "ambiguous_normalized"
        or r.match_type == "unmatched"
        or (r.in_cell_info and not r.in_sig_info_trt_cp and r.matched_cell_id)
    ]
    no_sig_after_match = [r for r in cand_rows if r.in_cell_info and not r.in_sig_info_trt_cp and r.matched_cell_id]
    no_data = [r for r in cand_rows if not r.in_cell_info]

    counts_by_cell = {cid: int(sig_counts[cid]) for cid in usable}

    qc: Dict[str, Any] = {
        "gse": gse,
        "cell_info_path": str(cell_info),
        "sig_info_path": str(sig_info),
        "expected_candidates": len(candidates),
        "matched_in_cell_info": matched_in_ci,
        "matched_in_sig_info_trt_cp": matched_in_sig,
        "final_usable_cells": len(usable),
        "final_usable_cell_ids": usable,
        "cells_with_signature_counts": counts_by_cell,
        "stomach_primary_site_cell_ids_in_cell_info": stomach_ids,
        "summary_groups": {
            "자동 매칭 성공": [
                {
                    "input": r.input_name,
                    "matched_cell_id": r.matched_cell_id,
                    "trt_cp_signature_count": r.trt_cp_signature_count,
                    "match_type": r.match_type,
                }
                for r in auto_ok
            ],
            "리뷰 필요": [
                {
                    "input": r.input_name,
                    "match_type": r.match_type,
                    "matched_cell_id": r.matched_cell_id,
                    "alias_suggestions": r.alias_suggestions,
                    "note": r.note,
                }
                for r in need_review
            ],
            "실제 시그니처 없음_플레이트에 cell은 있으나 trt_cp 없음": [
                {"input": r.input_name, "matched_cell_id": r.matched_cell_id}
                for r in no_sig_after_match
            ],
            "실제 데이터 부재_cell_info에 없음": [
                {"input": r.input_name, "alias_suggestions": r.alias_suggestions, "note": r.note}
                for r in no_data
            ],
        },
        "notes": {
            "plate_coverage": (
                "GSE92742 cell_info contains exactly one stomach primary_site line (AGS). "
                "Other historical gastric candidates are absent from this L1000 plate — "
                "not fixable by alias/normalize alone; use GSE70138 or another assay if those lines are required."
            ),
        },
    }
    out_qc.write_text(json.dumps(qc, indent=2, ensure_ascii=False), encoding="utf-8")
    log_line(log_path, f"I/O write {out_qc}")

    payload = {
        "cell_ids": usable,
        "selection_criteria": (
            f"GSE92742 only: cell_id must appear in {gse} cell_info match path AND have "
            "pert_type==trt_cp signatures in sig_info. Rebuilt by scripts/rebuild_stad_lincs_cell_ids_gse92742.py"
        ),
        "gse": gse,
        "candidates_seed": str(cand_path.relative_to(root)) if cand_path.is_relative_to(root) else str(cand_path),
        "review_table": str(out_review.relative_to(root)),
        "qc_report": str(out_qc.relative_to(root)),
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    log_line(log_path, f"I/O write {out_json}")

    log_line(
        log_path,
        "UNMATCHED (no cell_info id): "
        + ", ".join(r.input_name for r in no_data),
    )
    log_line(
        log_path,
        "ALIAS_SUGGESTIONS (embedded in review note column for unmatched)",
    )
    log_line(log_path, f"DONE usable_cell_ids={usable}")
    print(json.dumps({"final_usable_cell_ids": usable, "qc_report": str(out_qc)}, indent=2))


if __name__ == "__main__":
    main()
