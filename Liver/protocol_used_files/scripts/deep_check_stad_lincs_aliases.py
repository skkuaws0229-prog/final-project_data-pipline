#!/usr/bin/env python3
"""
Deep alias/metadata check for STAD LINCS candidates on GSE92742.

This script does NOT modify curated_data raw inputs and does NOT touch
rebuild_stad_lincs_cell_ids_gse92742.py. It only reads:
  - curated_data/lincs/GSE92742/GSE92742_Broad_LINCS_cell_info.txt.gz
  - curated_data/lincs/GSE92742/GSE92742_Broad_LINCS_sig_info.txt.gz
and writes a review report:
  - reports/lincs/stad_lincs_alias_deep_check.json
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd


def ts() -> str:
    """Return wall-clock timestamp string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def norm_token(x: str) -> str:
    """Normalize a token for alias/substring comparison."""
    return re.sub(r"[_\-\./\s]", "", str(x).upper())


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"deep_check_stad_lincs_aliases_{time.strftime('%Y%m%d_%H%M%S')}.log"

    def log(msg: str) -> None:
        line = f"[{ts()}] {msg}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    cell_info = root / "curated_data" / "lincs" / "GSE92742" / "GSE92742_Broad_LINCS_cell_info.txt.gz"
    sig_info = root / "curated_data" / "lincs" / "GSE92742" / "GSE92742_Broad_LINCS_sig_info.txt.gz"
    out_json = root / "reports" / "lincs" / "stad_lincs_alias_deep_check.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)

    log(f"I/O read cell_info: {cell_info}")
    ci = pd.read_csv(cell_info, sep="\t", compression="gzip", low_memory=False)
    log(f"I/O read sig_info: {sig_info}")
    sig = pd.read_csv(sig_info, sep="\t", compression="gzip", usecols=["pert_type", "cell_id"], low_memory=False)

    # (1) cell_info column summary
    column_summary: dict[str, dict[str, Any]] = {}
    for col in ci.columns:
        sample_vals = ci[col].dropna().astype(str).unique()[:5].tolist()
        column_summary[str(col)] = {
            "n_unique": int(ci[col].nunique(dropna=True)),
            "sample_values": sample_vals,
        }

    # (2) Broad keyword search across all object columns
    keywords = ["gastric", "stomach", "GI", "intestin"]
    mask = pd.Series(False, index=ci.index)
    text_cols = [c for c in ci.columns if ci[c].dtype == object]
    for col in text_cols:
        s = ci[col].astype(str)
        for kw in keywords:
            mask = mask | s.str.contains(kw, case=False, na=False)
    hits = ci[mask].copy()

    hit_cell_ids = sorted(hits["cell_id"].astype(str).unique().tolist()) if "cell_id" in hits.columns else []

    # Strict stomach/gastric check for recommendation (avoid GI/intestin false positives)
    strict_mask = (
        ci["primary_site"].astype(str).str.contains(r"stomach|gastric", case=False, na=False)
        | ci["subtype"].astype(str).str.contains(r"stomach|gastric", case=False, na=False)
    )
    strict_hits = ci[strict_mask].copy()
    strict_hit_cell_ids = sorted(strict_hits["cell_id"].astype(str).unique().tolist())

    # (3) Substring-based candidate matches
    candidates = ["AGS", "HS746T", "KATOIII", "MKN45", "MKN7", "MKN74", "NCI_N87", "NUGC3", "OCUM1", "SNU16", "SNU216", "SNU5"]
    all_ids = ci["cell_id"].astype(str).tolist()
    candidate_substring_matches: dict[str, list[str]] = {}
    for c in candidates:
        c_norm = norm_token(c)
        contains = []
        for cid in all_ids:
            cid_norm = norm_token(cid)
            if c_norm in cid_norm or cid_norm in c_norm:
                contains.append(cid)
        # dedupe preserving order
        seen = set()
        uniq = []
        for x in contains:
            if x not in seen:
                seen.add(x)
                uniq.append(x)
        candidate_substring_matches[c] = uniq[:10]

    # (4) Non-standard cell_id patterns
    unusual = ci[~ci["cell_id"].astype(str).str.match(r"^[A-Z]+\d+$", na=False)]

    # sig_info trt_cp counts for discovered ids and candidates
    tr = sig[sig["pert_type"] == "trt_cp"]
    tr_counts = tr["cell_id"].astype(str).value_counts()
    tr_counts_dict = {str(k): int(v) for k, v in tr_counts.items()}

    candidate_trt_counts = {c: int(tr_counts_dict.get(c, 0)) for c in candidates}
    hit_trt_counts = {cid: int(tr_counts_dict.get(cid, 0)) for cid in hit_cell_ids}

    stomach_like_new = sorted([cid for cid in strict_hit_cell_ids if cid != "AGS"])

    # Rule-based recommendation
    should_update_seed = len(stomach_like_new) > 0
    recommendation = {
        "new_stomach_like_cell_ids_found": stomach_like_new,
        "should_update_candidates_seed": should_update_seed,
        "action": (
            "add_new_cells_and_rerun_rebuild"
            if should_update_seed
            else "no_new_cells_keep_AGS_only"
        ),
    }

    # Keep JSON compact; include top rows for human review
    hits_preview = hits.head(50).fillna("").astype(str).to_dict(orient="records")

    payload: dict[str, Any] = {
        "generated_at": ts(),
        "inputs": {
            "cell_info": str(cell_info),
            "sig_info": str(sig_info),
        },
        "cell_info_shape": [int(ci.shape[0]), int(ci.shape[1])],
        "sig_info_shape": [int(sig.shape[0]), int(sig.shape[1])],
        "cell_info_columns_summary": column_summary,
        "keyword_config": {
            "keywords": keywords,
            "text_columns_checked": text_cols,
        },
        "broader_keyword_hits": {
            "row_count": int(hits.shape[0]),
            "cell_ids": hit_cell_ids,
            "preview_rows_top50": hits_preview,
        },
        "strict_stomach_gastric_hits_primary_site_or_subtype": {
            "row_count": int(strict_hits.shape[0]),
            "cell_ids": strict_hit_cell_ids,
        },
        "candidate_substring_matches": candidate_substring_matches,
        "non_standard_cell_id_patterns": {
            "count": int(unusual.shape[0]),
            "preview_cell_ids_top50": unusual["cell_id"].astype(str).head(50).tolist(),
        },
        "trt_cp_counts": {
            "candidate_exact_ids": candidate_trt_counts,
            "keyword_hit_cell_ids": hit_trt_counts,
        },
        "recommendation": recommendation,
        "notes": {
            "gse92742_baseline": "Known usable STAD LINCS cell_id was AGS with 362 trt_cp signatures.",
            "raw_policy": "No curated_data files modified.",
        },
    }

    log(f"I/O write report: {out_json}")
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    log("Done deep alias check.")


if __name__ == "__main__":
    main()
