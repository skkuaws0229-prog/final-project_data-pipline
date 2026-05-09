#!/usr/bin/env python3
"""
LIHC external validation (independent mode, CPTAC excluded).

Builds a Top30 evidence table from staged external sources and explicitly marks
the CPTAC source as excluded-by-request.
"""

from __future__ import annotations

import argparse
import json
import re
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def split_genes(value: Any) -> list[str]:
    """Normalize TARGET field into unique gene symbols."""
    text = str(value or "").replace("|", ";").replace(",", ";")
    out: list[str] = []
    for token in text.split(";"):
        g = re.sub(r"[^A-Za-z0-9_-]+", "", token.strip().upper())
        if g:
            out.append(g)
    return sorted(set(out))


def normalize_name(value: Any) -> str:
    """Lowercase alphanumeric normalization for fuzzy name matching."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def prism_evidence_set(depmap_dir: Path) -> set[str]:
    """Return normalized LIHC PRISM drug names."""
    ref = depmap_dir / "lihc_drug_names_reference_20260427.csv"
    if not ref.is_file():
        return set()
    df = pd.read_csv(ref)
    if "drug_name" not in df.columns:
        return set()
    return {normalize_name(v) for v in df["drug_name"].dropna().tolist() if str(v).strip()}


def clinical_trials_text(clinical_dir: Path) -> str:
    """Concatenate all staged clinicaltrials json text payloads."""
    if not clinical_dir.is_dir():
        return ""
    chunks: list[str] = []
    for p in sorted(clinical_dir.glob("*.json")):
        chunks.append(p.read_text(encoding="utf-8", errors="ignore").lower())
    return "\n".join(chunks)


def cosmic_cgc_genes(cosmic_dir: Path) -> set[str]:
    """Load Cancer Gene Census gene symbols from COSMIC tar payload."""
    tar_path = cosmic_dir / "Cosmic_CancerGeneCensus_Tsv_v103_GRCh38.tar"
    if not tar_path.is_file():
        return set()
    gene_set: set[str] = set()
    with tarfile.open(tar_path, "r") as tf:
        member = next((m for m in tf.getmembers() if m.name.endswith(".tsv.gz")), None)
        if member is None:
            return set()
        extracted = tf.extractfile(member)
        if extracted is None:
            return set()
        df = pd.read_csv(extracted, sep="\t", compression="gzip")
    gene_col = None
    for cand in ("Gene Symbol", "GENE_SYMBOL"):
        if cand in df.columns:
            gene_col = cand
            break
    if gene_col is None:
        return set()
    for g in df[gene_col].dropna().astype(str):
        clean = re.sub(r"[^A-Za-z0-9_-]+", "", g.strip().upper())
        if clean:
            gene_set.add(clean)
    return gene_set


def load_geo_expression_matrix(geo_dir: Path) -> tuple[pd.DataFrame, float]:
    """
    Build merged GEO expression matrix (rows=gene_symbol, cols=samples) and global median.
    """
    mats: list[pd.DataFrame] = []
    for name in (
        "GSE14520-GPL3921_series_matrix_tumor_matrix_lihc_20260427.csv",
        "GSE14520-GPL571_series_matrix_tumor_matrix_lihc_20260427.csv",
    ):
        p = geo_dir / name
        if not p.is_file():
            continue
        df = pd.read_csv(p)
        if "gene_symbol" not in df.columns:
            continue
        sample_cols = [c for c in df.columns if c not in {"ID_REF", "gene_symbol"}]
        if not sample_cols:
            continue
        sub = df[["gene_symbol"] + sample_cols].copy()
        sub["gene_symbol"] = sub["gene_symbol"].astype(str).str.upper().str.strip()
        sub = sub.loc[sub["gene_symbol"].ne("")]
        sub = sub.groupby("gene_symbol", as_index=True)[sample_cols].mean(numeric_only=True)
        mats.append(sub.apply(pd.to_numeric, errors="coerce"))

    if not mats:
        return pd.DataFrame(), np.nan
    merged = pd.concat(mats, axis=1, join="outer")
    global_median = float(np.nanmedian(merged.to_numpy())) if merged.size else np.nan
    return merged, global_median


def geo_target_signal(genes: list[str], expr_mat: pd.DataFrame, global_median: float) -> tuple[bool, float, str]:
    """Return GEO evidence bool, target expression percentile, matched genes string."""
    if expr_mat.empty or not np.isfinite(global_median):
        return False, np.nan, ""
    matches = [g for g in genes if g in expr_mat.index]
    if not matches:
        return False, np.nan, ""
    values = expr_mat.loc[matches].mean(axis=0)
    pct = float((values >= global_median).mean()) if len(values) else np.nan
    return bool(np.isfinite(pct) and pct >= 0.30), pct, ";".join(matches)


def fetch_symbol_to_ensembl(symbols: set[str]) -> dict[str, str]:
    """
    Resolve HGNC symbols -> Ensembl gene IDs via MyGene.info.
    Keeps first resolved ENSG per symbol.
    """
    if not symbols:
        return {}
    out: dict[str, str] = {}
    chunk: list[str] = []
    symbol_list = sorted(symbols)
    for sym in symbol_list:
        chunk.append(sym)
        if len(chunk) < 200:
            continue
        _merge_symbol_chunk(chunk, out)
        chunk = []
    if chunk:
        _merge_symbol_chunk(chunk, out)
    return out


def _merge_symbol_chunk(symbols: list[str], out: dict[str, str]) -> None:
    for sym in symbols:
        if not sym or sym in out:
            continue
        params = urllib.parse.urlencode(
            {"q": sym, "fields": "symbol,ensembl.gene", "species": "human", "size": 5}
        )
        url = f"https://mygene.info/v3/query?{params}"
        with urllib.request.urlopen(url, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        for hit in payload.get("hits", []):
            hit_sym = str(hit.get("symbol", "")).upper().strip()
            if hit_sym != sym:
                continue
            ens = hit.get("ensembl")
            gene_id = ""
            if isinstance(ens, dict):
                gene_id = str(ens.get("gene", "")).strip()
            elif isinstance(ens, list):
                for item in ens:
                    if isinstance(item, dict) and str(item.get("gene", "")).strip():
                        gene_id = str(item["gene"]).strip()
                        break
            if gene_id.startswith("ENSG"):
                out[sym] = gene_id
                break


def opentargets_assoc_layer(ot_dir: Path, top: pd.DataFrame) -> pd.DataFrame:
    """
    Compute LIHC OpenTargets support by TARGET genes.
    diseaseId pattern for liver/HCC is matched from disease IDs by regex fallback.
    """
    assoc_dir = ot_dir / "association_overall_direct"
    assoc_seed = ot_dir / "association_overall_direct_part00000.snappy.parquet"
    if assoc_dir.is_dir():
        assoc = pd.read_parquet(assoc_dir)
    elif assoc_seed.is_file():
        assoc = pd.read_parquet(assoc_seed)
    else:
        return pd.DataFrame(
            {
                "canonical_drug_id": top["canonical_drug_id"].astype(str),
                "opentargets_has_evidence": False,
                "opentargets_support_score": np.nan,
                "opentargets_target_ids": "",
                "opentargets_status": "PENDING_DATA",
            }
        )

    required = {"diseaseId", "targetId", "score", "evidenceCount"}
    if not required.issubset(set(assoc.columns)):
        return pd.DataFrame(
            {
                "canonical_drug_id": top["canonical_drug_id"].astype(str),
                "opentargets_has_evidence": False,
                "opentargets_support_score": np.nan,
                "opentargets_target_ids": "",
                "opentargets_status": "INVALID_SCHEMA",
            }
        )

    disease_series = assoc["diseaseId"].astype(str)
    known_liver_ids = {"EFO_0000182", "MONDO_0007254", "MONDO_0004992", "DOID_684"}
    liver_mask = disease_series.isin(known_liver_ids) | disease_series.str.contains(
        r"liver|hepato|hcc", case=False, regex=True, na=False
    )
    liver_ids = set(disease_series.loc[liver_mask].unique().tolist())
    if not liver_ids:
        liver_ids = {"DOID_684"}

    top_genes: set[str] = set()
    for target in top["TARGET"].fillna(""):
        top_genes.update(split_genes(target))
    sym2ens = fetch_symbol_to_ensembl(top_genes)

    rows: list[dict[str, Any]] = []
    for r in top.itertuples(index=False):
        genes = split_genes(getattr(r, "TARGET", ""))
        target_ids = sorted({sym2ens[g] for g in genes if g in sym2ens})
        if target_ids:
            sub = assoc.loc[
                assoc["diseaseId"].astype(str).isin(liver_ids)
                & assoc["targetId"].astype(str).isin(target_ids)
            ]
        else:
            sub = pd.DataFrame()
        score = float(pd.to_numeric(sub["score"], errors="coerce").max()) if not sub.empty else np.nan
        has_ev = bool(np.isfinite(score) and score > 0)
        rows.append(
            {
                "canonical_drug_id": str(getattr(r, "canonical_drug_id")),
                "opentargets_has_evidence": has_ev,
                "opentargets_support_score": score,
                "opentargets_target_ids": ";".join(target_ids),
                "opentargets_status": "OK",
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--result-tag", default="20260428_liver_step4_cv5_gc_sc")
    args = ap.parse_args()

    root = args.project_root.resolve()
    result_tag = args.result_tag
    results_dir = root / "results" / result_tag
    external_root = root / "external_validation" / result_tag
    sources_dir = external_root / "sources"
    reports_dir = external_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    top_path = results_dir / "lihc_top30_directive_ensemble_with_names.csv"
    if not top_path.is_file():
        raise FileNotFoundError(f"Top30 file not found: {top_path}")
    top = pd.read_csv(top_path)
    top["canonical_drug_id"] = top["canonical_drug_id"].astype(str)

    prism_names = prism_evidence_set(sources_dir / "depmap_prism")
    ct_text = clinical_trials_text(sources_dir / "clinicaltrials")
    cgc_genes = cosmic_cgc_genes(sources_dir / "cosmic")
    geo_expr, geo_global_median = load_geo_expression_matrix(sources_dir / "geo_gse14520")
    ot_layer = opentargets_assoc_layer(sources_dir / "opentargets", top)
    ot_map = {
        str(r["canonical_drug_id"]): r
        for r in ot_layer.to_dict(orient="records")
    }

    rows: list[dict[str, Any]] = []
    for r in top.itertuples(index=False):
        drug_name = str(getattr(r, "DRUG_NAME", "")).strip()
        drug_norm = normalize_name(drug_name)
        genes = split_genes(getattr(r, "TARGET", ""))
        cosmic_matches = sorted([g for g in genes if g in cgc_genes])
        ct_count = int(ct_text.count(drug_name.lower())) if drug_name else 0
        geo_has, geo_pct, geo_match = geo_target_signal(genes, geo_expr, geo_global_median)
        ot_row = ot_map.get(str(getattr(r, "canonical_drug_id")), {})

        rows.append(
            {
                "rank": int(getattr(r, "rank")),
                "canonical_drug_id": str(getattr(r, "canonical_drug_id")),
                "drug_name": drug_name,
                "target_genes": ";".join(genes),
                "pred_ic50_mean": float(getattr(r, "pred_ic50_mean")),
                "prism_has_evidence": bool(drug_norm in prism_names),
                "prism_status": "OK" if prism_names else "PENDING_DATA",
                "clinical_trial_mention_count": ct_count,
                "clinical_trials_has_evidence": bool(ct_count > 0),
                "clinical_trials_status": "OK" if ct_text else "PENDING_DATA",
                "geo_has_evidence": geo_has,
                "geo_status": "OK" if not geo_expr.empty else "PENDING_DATA",
                "geo_support_score": geo_pct,
                "geo_target_match_genes": geo_match,
                "opentargets_has_evidence": bool(ot_row.get("opentargets_has_evidence", False)),
                "opentargets_status": str(ot_row.get("opentargets_status", "PENDING_DATA")),
                "opentargets_support_score": ot_row.get("opentargets_support_score", np.nan),
                "opentargets_target_ids": str(ot_row.get("opentargets_target_ids", "")),
                "cosmic_has_evidence": bool(len(cosmic_matches) > 0),
                "cosmic_status": "OK" if cgc_genes else "PENDING_DATA",
                "cosmic_cgc_target_matches": ";".join(cosmic_matches),
                "cptac_has_evidence": False,
                "cptac_status": "EXCLUDED_BY_REQUEST",
            }
        )

    external = pd.DataFrame(rows)
    out_csv = external_root / "top30_external_validation_lihc_cptac_excluded.csv"
    external.to_csv(out_csv, index=False)

    summary = {
        "result_tag": result_tag,
        "mode": "CPTAC_EXCLUDED",
        "top30_rows": int(len(external)),
        "source_status": {
            "prism": str(external["prism_status"].mode().iloc[0]),
            "clinical_trials": str(external["clinical_trials_status"].mode().iloc[0]),
            "geo": str(external["geo_status"].mode().iloc[0]),
            "opentargets": str(external["opentargets_status"].mode().iloc[0]),
            "cosmic": str(external["cosmic_status"].mode().iloc[0]),
            "cptac": "EXCLUDED_BY_REQUEST",
        },
        "supported_rows": {
            "prism": int(external["prism_has_evidence"].fillna(False).astype(bool).sum()),
            "clinical_trials": int(external["clinical_trials_has_evidence"].fillna(False).astype(bool).sum()),
            "geo": int(external["geo_has_evidence"].fillna(False).astype(bool).sum()),
            "opentargets": int(external["opentargets_has_evidence"].fillna(False).astype(bool).sum()),
            "cosmic": int(external["cosmic_has_evidence"].fillna(False).astype(bool).sum()),
            "cptac": 0,
        },
        "outputs": {
            "external_csv": str(out_csv.relative_to(root)),
        },
    }
    out_json = external_root / "external_validation_lihc_cptac_excluded_summary.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# LIHC External Validation Run (CPTAC Excluded)",
        "",
        f"- result_tag: `{result_tag}`",
        "- mode: `CPTAC_EXCLUDED`",
        "- cptac_status: `EXCLUDED_BY_REQUEST`",
        "",
        "## Source Status",
        f"- PRISM: `{summary['source_status']['prism']}`",
        f"- ClinicalTrials: `{summary['source_status']['clinical_trials']}`",
        f"- GEO: `{summary['source_status']['geo']}`",
        f"- OpenTargets: `{summary['source_status']['opentargets']}`",
        f"- COSMIC: `{summary['source_status']['cosmic']}`",
        "- CPTAC: `EXCLUDED_BY_REQUEST`",
        "",
        "## Supported Rows (Top30)",
        f"- PRISM: `{summary['supported_rows']['prism']}`",
        f"- ClinicalTrials: `{summary['supported_rows']['clinical_trials']}`",
        f"- GEO: `{summary['supported_rows']['geo']}`",
        f"- OpenTargets: `{summary['supported_rows']['opentargets']}`",
        f"- COSMIC: `{summary['supported_rows']['cosmic']}`",
        "- CPTAC: `0` (excluded)",
        "",
        "## Outputs",
        f"- CSV: `{summary['outputs']['external_csv']}`",
        f"- JSON: `{out_json.relative_to(root)}`",
    ]
    out_md = reports_dir / "external_validation_run_lihc_cptac_excluded.md"
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
