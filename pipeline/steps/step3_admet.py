"""Step 3 — ADMET Gate: RDKit descriptors + TDC 22-assay nearest-neighbor filter.

Applies Lipinski/PAINS/RDKit checks and TDC ADMET assay predictions
to the Top N candidates from Step 2, producing a filtered list.

Usage (standalone):
    python step3_admet.py --config configs/skcm.yaml

Called by orchestrator:
    run_disease_pipeline.py -> steps.step3_admet.run(config)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem, Crippen, Descriptors, FilterCatalog, Lipinski, rdMolDescriptors

from .step1_data_collection import PipelinePaths, make_paths, ensure_dirs


RDLogger.DisableLog("rdApp.warning")


# ── ADMET Assay Definitions ──────────────────────────────────────────

ADMET_ASSAYS = {
    "ames": {"type": "binary", "good": 0, "hard_bad": 1},
    "dili": {"type": "binary", "good": 0, "hard_bad": 1},
    "herg": {"type": "binary", "good": 0, "hard_bad": 1},
    "hia_hou": {"type": "binary", "good": 1},
    "bioavailability_ma": {"type": "binary", "good": 1},
    "pgp_broccatelli": {"type": "binary", "good": 0},
    "caco2_wang": {"type": "regression", "good_direction": "high", "threshold": -5.15},
    "half_life_obach": {"type": "regression", "good_direction": "high", "threshold": 3.0},
    "solubility_aqsoldb": {"type": "regression", "good_direction": "high"},
    "lipophilicity_astrazeneca": {"type": "regression", "ideal_range": (-0.4, 5.6)},
    "clearance_hepatocyte_az": {"type": "regression", "good_direction": "low"},
    "clearance_microsome_az": {"type": "regression", "good_direction": "low"},
    "vdss_lombardo": {"type": "regression"},
    "ppbr_az": {"type": "regression"},
    "ld50_zhu": {"type": "regression", "good_direction": "high"},
    "cyp2c9_veith": {"type": "binary", "good": 0},
    "cyp2d6_veith": {"type": "binary", "good": 0},
    "cyp3a4_veith": {"type": "binary", "good": 0},
    "cyp2c9_substrate_carbonmangels": {"type": "binary"},
    "cyp2d6_substrate_carbonmangels": {"type": "binary"},
    "cyp3a4_substrate_carbonmangels": {"type": "binary"},
    "bbb_martins": {"type": "binary"},
}


# ── Utility ──────────────────────────────────────────────────────────

def mol_from_smiles_or_none(smiles: str):
    value = str(smiles or "").strip()
    if value.lower() in {"", "nan", "none", "<na>", "null"}:
        return None
    mol = Chem.MolFromSmiles(value)
    if mol is None or mol.GetNumAtoms() == 0:
        return None
    return mol


def make_pains_catalog():
    params = FilterCatalog.FilterCatalogParams()
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_A)
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_B)
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_C)
    return FilterCatalog.FilterCatalog(params)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    def _default(v):
        if isinstance(v, (np.integer,)): return int(v)
        if isinstance(v, (np.floating,)): return float(v)
        if isinstance(v, np.ndarray): return v.tolist()
        return str(v)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_default), encoding="utf-8")


# ── RDKit Descriptors ────────────────────────────────────────────────

def compute_candidate_rdkit(drug_id: str, smiles: str, mol, pains) -> dict[str, Any]:
    if mol is None:
        return {
            "canonical_drug_id": drug_id,
            "rdkit_valid_smiles": 0, "mol_weight": np.nan, "logp": np.nan,
            "tpsa": np.nan, "hbd": np.nan, "hba": np.nan, "rot_bonds": np.nan,
            "pains_alert_count": np.nan, "lipinski_violations": np.nan,
        }
    mw = float(Descriptors.MolWt(mol))
    logp = float(Crippen.MolLogP(mol))
    hbd = int(Lipinski.NumHDonors(mol))
    hba = int(Lipinski.NumHAcceptors(mol))
    violations = int(mw > 500) + int(logp > 5) + int(hbd > 5) + int(hba > 10)
    return {
        "canonical_drug_id": drug_id,
        "rdkit_valid_smiles": 1, "mol_weight": mw, "logp": logp,
        "tpsa": float(rdMolDescriptors.CalcTPSA(mol)),
        "hbd": hbd, "hba": hba,
        "rot_bonds": int(Lipinski.NumRotatableBonds(mol)),
        "pains_alert_count": int(len(pains.GetMatches(mol))) if pains else 0,
        "lipinski_violations": violations,
    }


# ── ADMET Assay Lookup ───────────────────────────────────────────────

def admet_good_flag(y: float, cfg: dict[str, Any]) -> int:
    if cfg.get("type") == "binary" and "good" in cfg:
        return int(round(y) == int(cfg["good"]))
    if "threshold" in cfg and cfg.get("good_direction") == "high":
        return int(y >= float(cfg["threshold"]))
    if "threshold" in cfg and cfg.get("good_direction") == "low":
        return int(y <= float(cfg["threshold"]))
    if "ideal_range" in cfg:
        low, high = cfg["ideal_range"]
        return int(float(low) <= y <= float(high))
    return 0


def lookup_admet_assays(candidates: pd.DataFrame, admet_dir: Path) -> pd.DataFrame:
    rows = [{"canonical_drug_id": str(v)} for v in candidates["canonical_drug_id"]]
    out = pd.DataFrame(rows)

    mols = {
        str(row["canonical_drug_id"]): mol_from_smiles_or_none(str(row.get("canonical_smiles", "") or ""))
        for _, row in candidates.iterrows()
    }
    fps = {
        drug_id: AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
        for drug_id, mol in mols.items() if mol is not None
    }

    for assay, cfg in ADMET_ASSAYS.items():
        assay_path = admet_dir / assay / "train_val.csv"
        if not assay_path.exists():
            continue
        ref = pd.read_csv(assay_path)
        ref["mol"] = ref["Drug"].map(lambda s: mol_from_smiles_or_none(str(s)))
        ref = ref[ref["mol"].notna()].copy()
        if ref.empty:
            continue
        ref["fp"] = ref["mol"].map(lambda m: AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048))

        assay_rows = []
        for drug_id, fp in fps.items():
            sims = [DataStructs.TanimotoSimilarity(fp, ref_fp) for ref_fp in ref["fp"]]
            if not sims:
                assay_rows.append({"canonical_drug_id": drug_id})
                continue
            best_idx = int(np.argmax(sims))
            y = float(ref.iloc[best_idx]["Y"])
            sim = float(sims[best_idx])
            good = admet_good_flag(y, cfg)
            assay_rows.append({
                "canonical_drug_id": drug_id,
                f"admet_{assay}_nearest_y": y,
                f"admet_{assay}_nearest_similarity": sim,
                f"admet_{assay}_good_flag": good if sim >= 0.70 else 0,
            })
        out = out.merge(pd.DataFrame(assay_rows), on="canonical_drug_id", how="left")
    return out


# ── ADMET Gate ───────────────────────────────────────────────────────

def apply_admet_gate(candidates: pd.DataFrame, admet_dir: Path) -> pd.DataFrame:
    out = candidates.copy()
    out["canonical_drug_id"] = out["canonical_drug_id"].astype(str)
    pains = make_pains_catalog()

    # RDKit descriptors
    rdkit_rows = []
    for _, row in out.iterrows():
        smiles = str(row.get("canonical_smiles", "") or "")
        mol = mol_from_smiles_or_none(smiles)
        rdkit_rows.append(compute_candidate_rdkit(row["canonical_drug_id"], smiles, mol, pains))
    rdkit = pd.DataFrame(rdkit_rows)
    if "canonical_drug_id" in rdkit.columns:
        rdkit["canonical_drug_id"] = rdkit["canonical_drug_id"].astype(str)
    out = out.merge(rdkit, on="canonical_drug_id", how="left")

    # Assay lookup
    assay_lookup = lookup_admet_assays(out, admet_dir)
    if "canonical_drug_id" in assay_lookup.columns:
        assay_lookup["canonical_drug_id"] = assay_lookup["canonical_drug_id"].astype(str)
    out = out.merge(assay_lookup, on="canonical_drug_id", how="left")

    # Hard fail logic
    hard_fail = (
        (out["rdkit_valid_smiles"] == 0) |
        (out["pains_alert_count"].fillna(99) > 0) |
        (out["lipinski_violations"].fillna(99) > 2)
    )
    for assay, cfg in ADMET_ASSAYS.items():
        pred_col = f"admet_{assay}_nearest_y"
        sim_col = f"admet_{assay}_nearest_similarity"
        if pred_col not in out.columns:
            continue
        confident = out[sim_col].fillna(0.0) >= 0.70
        if "hard_bad" in cfg:
            hard_fail = hard_fail | (confident & (out[pred_col].round().astype("Int64") == int(cfg["hard_bad"])))

    out["admet_strict_pass"] = ~hard_fail
    good_cols = [c for c in out.columns if c.endswith("_good_flag")]
    out["admet_good_signal_count"] = out[good_cols].sum(axis=1) if good_cols else 0
    out["admet_adjusted_score"] = out["final_selection_score"] - 0.04 * out["lipinski_violations"].fillna(3)
    out.loc[~out["admet_strict_pass"], "admet_adjusted_score"] -= 0.25

    # Sort and rank
    out = out.sort_values(
        ["admet_strict_pass", "admet_adjusted_score", "final_selection_score"],
        ascending=[False, False, False],
    )
    out["admet_filtered_rank"] = np.arange(1, len(out) + 1)
    return out


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC INTERFACE
# ═══════════════════════════════════════════════════════════════════════

def run(config: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    """Entry point called by orchestrator.

    Args:
        config: Parsed YAML config with keys:
            - disease / tcga_code
            - project_root
            - admet_top_n: how many ADMET-passed drugs to keep (default: 15)
    """
    raw = config.get("tcga_code", config.get("disease", "UNKNOWN"))
    if isinstance(raw, dict):
        tcga_code = str(raw.get("code", raw.get("name", "UNKNOWN"))).upper()
    else:
        tcga_code = str(raw).upper()
    if dry_run:
        project_root = Path(config.get("project_root", f"./{tcga_code}_pipeline"))
        return {
            "status": "dry_run",
            "step": "step3_admet",
            "disease": tcga_code,
            "project_root": str(project_root),
            "admet_top_n": config.get("admet_top_n", 15),
        }
    project_root = Path(config.get("project_root", f"./{tcga_code}_pipeline"))
    admet_top_n = config.get("admet_top_n", 15)

    paths = make_paths(project_root)
    ensure_dirs(paths)

    # Load candidates from Step 2
    candidates_path = paths.final_selection / "selected_drugs_top_n.csv"
    if not candidates_path.exists():
        # Fallback: try drug scores parquet
        candidates_path = paths.final_selection / "final_drug_scores.parquet"
        if candidates_path.exists():
            candidates = pd.read_parquet(candidates_path).head(50)
        else:
            raise FileNotFoundError(f"No candidates found. Run Step 2 first. Tried {paths.final_selection}")
    else:
        candidates = pd.read_csv(candidates_path)

    print(f"[Step3] Applying ADMET gate to {len(candidates)} candidates ...", flush=True)

    # Find ADMET data directory
    admet_dir = paths.raw_cache / "admet/tdc_admet_group/admet_group"
    if not admet_dir.exists():
        # Try alternative location
        admet_dir = paths.raw_cache / "admet"
        if not admet_dir.exists():
            print("[Step3] WARNING: ADMET data not found. Skipping assay lookup.")
            admet_dir = Path("/tmp/empty_admet")
            admet_dir.mkdir(exist_ok=True)

    # Apply gate
    result = apply_admet_gate(candidates, admet_dir)

    # Save results
    result.to_csv(paths.final_selection / "admet_candidate_gate.csv", index=False)
    passed = result[result["admet_strict_pass"]].copy()
    passed.head(admet_top_n).to_csv(paths.final_selection / f"admet_filtered_top{admet_top_n}.csv", index=False)

    summary = {
        "step": "step3_admet",
        "disease": tcga_code,
        "total_candidates": int(len(candidates)),
        "admet_pass": int(passed["admet_strict_pass"].sum()) if "admet_strict_pass" in passed.columns else int(len(passed)),
        "admet_fail": int(len(result)) - int(len(passed)),
        "top_n_saved": min(admet_top_n, len(passed)),
        "top5_passed": passed.head(5)[["drug_name", "admet_adjusted_score"]].to_dict("records") if not passed.empty else [],
    }
    write_json(paths.final_selection / "admet_summary.json", summary)
    print(f"[Step3] Complete. {summary['admet_pass']} passed, {summary['admet_fail']} failed.", flush=True)
    return summary


if __name__ == "__main__":
    import argparse, yaml
    parser = argparse.ArgumentParser(description="Step 3: ADMET Gate")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config) as f:
        config = yaml.safe_load(f)
    run(config)
