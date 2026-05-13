"""Step 2 — Basic Pipeline: FE → Model Training → Ensemble → Ranking → External Validation.

Refactored from run_hnsc_pipeline.py (108KB) into a generic, disease-agnostic
module. All disease-specific constants (TCGA code, known drugs, target panel,
PRISM tissue filter) are read from the YAML config.

Usage (standalone):
    python step2_basic_pipeline.py --config configs/skcm.yaml

Called by orchestrator:
    run_disease_pipeline.py -> steps.step2_basic_pipeline.run(config)
"""
from __future__ import annotations

import json
import math
import random
import re
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import GroupKFold, KFold
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from .step1_data_collection import PipelinePaths, make_paths, ensure_dirs


# ── Constants (defaults, overridden by config) ───────────────────────

KEY_COLUMNS = {
    "pair_id", "sample_id", "cell_line_name", "model_id",
    "canonical_drug_id", "DRUG_ID", "drug_name",
    "label_regression", "label_binary", "label_main", "label_aux",
    "binary_threshold", "label_main_type", "label_aux_type",
    "ln_IC50", "gdsc_version", "TCGA_DESC", "cohort",
    "PATHWAY_NAME_NORMALIZED", "classification", "drug_bridge_strength",
    "stage3_resolution_status", "canonical_smiles",
    "drug__canonical_smiles", "drug__target_list",
}

STRONG_CONTEXT_COLS = [
    "TCGA_DESC", "PATHWAY_NAME_NORMALIZED", "classification",
    "drug_bridge_strength", "stage3_resolution_status",
]

TARGET_ALIASES = {
    "PI3KALPHA": "PIK3CA", "PI3KBETA": "PIK3CB", "PI3KDELTA": "PIK3CD",
    "PI3KGAMMA": "PIK3CG", "MTORC1": "MTOR", "MTORC2": "MTOR",
    "MEK1": "MAP2K1", "MEK2": "MAP2K2", "ERK2": "MAPK1", "ERK1": "MAPK3",
    "BCLXL": "BCL2L1", "VEGFR": "KDR", "HSP90": "HSP90AA1",
}

STEP6_WEIGHTS = {
    "model": 0.30, "prism": 0.20, "target": 0.15,
    "patient_context": 0.15, "clinical": 0.10, "control_tanimoto": 0.10,
}


def set_step_seed(seed: int) -> int:
    seed = int(seed or 42)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except Exception:
        pass
    return seed

# ── Utility functions ────────────────────────────────────────────────

def clean_gene_name(value: str) -> str:
    return re.sub(r"\s+\(\d+\)$", "", str(value)).strip().upper()

def safe_feature_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip().lower()).strip("_")
    return cleaned or "missing"

def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())

def is_gene_like(value: str) -> bool:
    token = str(value).strip().upper()
    if not token or token in {"NAN", "NA", "NONE", "UNKNOWN"}:
        return False
    if any(ch in token for ch in [" ", "/", ",", "(", ")"]):
        return False
    return bool(re.fullmatch(r"[A-Z0-9-]+", token))

def numeric_feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in KEY_COLUMNS and pd.api.types.is_numeric_dtype(df[c])]

def top_variance_columns(df: pd.DataFrame, cols: list[str], n: int) -> list[str]:
    if not cols or n <= 0:
        return []
    var = df[cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).var(axis=0).sort_values(ascending=False)
    return var.head(min(n, len(var))).index.tolist()

def spearman(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 2:
        return float("nan")
    return float(pd.Series(y_true).rank().corr(pd.Series(y_pred).rank()))

def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2)))

def scale_by_train(X_tr: np.ndarray, X_va: np.ndarray):
    mean = X_tr.mean(axis=0, keepdims=True)
    std = X_tr.std(axis=0, keepdims=True)
    std[std < 1e-6] = 1.0
    return ((X_tr - mean) / std).astype(np.float32), ((X_va - mean) / std).astype(np.float32)

def percentile_score(values: pd.Series) -> pd.Series:
    values = pd.to_numeric(values, errors="coerce").fillna(0.0)
    if values.nunique(dropna=False) <= 1:
        return pd.Series(0.5, index=values.index)
    return (values.rank(method="average", ascending=True) - 1.0) / (len(values) - 1.0)

def mol_from_smiles_or_none(smiles: str):
    value = str(smiles or "").strip()
    if value.lower() in {"", "nan", "none", "<na>", "null"}:
        return None
    mol = Chem.MolFromSmiles(value)
    if mol is None or mol.GetNumAtoms() == 0:
        return None
    return mol

def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    def _default(v):
        if isinstance(v, (np.integer,)): return int(v)
        if isinstance(v, (np.floating,)): return float(v)
        if isinstance(v, np.ndarray): return v.tolist()
        return str(v)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_default), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════════════

def load_gdsc(paths: PipelinePaths, tcga_code: str) -> pd.DataFrame:
    gdsc = pd.read_parquet(paths.raw_cache / "gdsc_ic50.parquet").copy()
    gdsc["cell_line_name"] = gdsc["cell_line_name"].astype(str).str.strip()
    gdsc["DRUG_ID"] = pd.to_numeric(gdsc["DRUG_ID"], errors="coerce").astype("Int64")
    gdsc["drug_name"] = gdsc["drug_name"].astype(str).str.strip()
    gdsc["ln_IC50"] = pd.to_numeric(gdsc["ln_IC50"], errors="coerce")
    gdsc = gdsc.dropna(subset=["DRUG_ID", "ln_IC50"]).copy()
    gdsc["DRUG_ID"] = gdsc["DRUG_ID"].astype(int)
    gdsc["TCGA_DESC"] = tcga_code.upper()
    gdsc["gdsc_version"] = "GDSC2"
    gdsc["WEBRELEASE"] = "Y"

    compounds_path = paths.raw_cache / "screened_compounds_rel_8.5.csv"
    if compounds_path.exists():
        compounds = pd.read_csv(compounds_path)
        compounds["DRUG_ID"] = pd.to_numeric(compounds["DRUG_ID"], errors="coerce").astype("Int64")
        compounds = compounds.dropna(subset=["DRUG_ID"]).copy()
        compounds["DRUG_ID"] = compounds["DRUG_ID"].astype(int)
        compounds = compounds.rename(columns={
            "TARGET": "putative_target", "TARGET_PATHWAY": "pathway_name",
            "SCREENING_SITE": "screening_site",
        })
        gdsc = gdsc.merge(
            compounds[["DRUG_ID", "putative_target", "pathway_name", "screening_site"]].drop_duplicates("DRUG_ID"),
            on="DRUG_ID", how="left", suffixes=("", "_compound"),
        )
        for col in ["putative_target", "pathway_name"]:
            compound_col = f"{col}_compound"
            if compound_col in gdsc.columns:
                base = gdsc[col] if col in gdsc.columns else pd.Series("", index=gdsc.index)
                gdsc[col] = base.fillna("").astype(str).mask(
                    base.fillna("").astype(str).str.strip().eq(""),
                    gdsc[compound_col].fillna("").astype(str),
                )
                gdsc = gdsc.drop(columns=[compound_col])
    for col in ["putative_target", "pathway_name", "screening_site"]:
        if col not in gdsc.columns:
            gdsc[col] = ""
        gdsc[col] = gdsc[col].fillna("").astype(str)
    return gdsc.reset_index(drop=True)


def build_cell_line_master(paths: PipelinePaths, gdsc: pd.DataFrame, tcga_code: str) -> pd.DataFrame:
    cohort = pd.read_csv(paths.raw_cache / "cellline_cohort_from_depmap_model.csv")
    cohort["cell_line_name"] = cohort["cell_line_name"].astype(str).str.strip()
    cohort = cohort.rename(columns={
        "ModelID": "model_id", "OncotreeCode": "depmap_oncotree_code",
        "OncotreeSubtype": "depmap_oncotree_subtype", "cohort": "depmap_cohort",
    })
    base = gdsc[["cell_line_name"]].drop_duplicates().copy()
    master = base.merge(cohort, on="cell_line_name", how="left")
    master["sample_id"] = master["cell_line_name"]
    master["model_id"] = master["model_id"].fillna("").astype(str)
    master["is_depmap_mapped"] = master["model_id"].ne("").astype(int)
    crispr_path = paths.raw_cache / "CRISPRGeneEffect.csv"
    if crispr_path.exists():
        crispr_ids = set(pd.read_csv(crispr_path, usecols=[0]).iloc[:, 0].astype(str))
        master["has_crispr_profile"] = master["model_id"].astype(str).isin(crispr_ids).astype(int)
    else:
        master["has_crispr_profile"] = 0
    master["TCGA_DESC"] = tcga_code.upper()
    master["cohort"] = tcga_code.upper()
    master["depmap_primary_disease"] = master.get("depmap_oncotree_subtype", "").fillna("").astype(str)
    keep = [
        "sample_id", "cell_line_name", "model_id", "is_depmap_mapped",
        "has_crispr_profile", "TCGA_DESC", "cohort", "depmap_oncotree_code",
        "depmap_primary_disease",
    ]
    for col in keep:
        if col not in master.columns:
            master[col] = ""
    return master[keep].sort_values("sample_id").reset_index(drop=True)


def build_response_labels(gdsc: pd.DataFrame, cell_master: pd.DataFrame) -> pd.DataFrame:
    labels = gdsc.copy()
    threshold = float(labels["ln_IC50"].quantile(0.3))
    labels["sample_id"] = labels["cell_line_name"]
    labels["canonical_drug_id"] = labels["DRUG_ID"].astype(int).astype(str)
    labels["pair_id"] = labels["sample_id"] + "__" + labels["canonical_drug_id"]
    labels["label_regression"] = labels["ln_IC50"]
    labels["label_binary"] = (labels["label_regression"] <= threshold).astype(int)
    labels["label_main"] = labels["label_regression"]
    labels["label_aux"] = labels["label_binary"]
    labels["label_main_type"] = "regression"
    labels["label_aux_type"] = "binary"
    labels["binary_threshold"] = threshold
    labels = labels.merge(
        cell_master[["sample_id", "model_id", "is_depmap_mapped", "has_crispr_profile"]],
        on="sample_id", how="left",
    )
    labels["has_crispr_profile"] = labels["has_crispr_profile"].fillna(0).astype(int)
    labels = labels[labels["has_crispr_profile"].eq(1)].copy()
    keep = [
        "pair_id", "sample_id", "cell_line_name", "model_id", "is_depmap_mapped",
        "has_crispr_profile", "canonical_drug_id", "DRUG_ID", "drug_name",
        "TCGA_DESC", "gdsc_version", "putative_target", "pathway_name",
        "WEBRELEASE", "label_regression", "label_binary", "label_main",
        "label_aux", "label_main_type", "label_aux_type", "binary_threshold",
    ]
    return labels[keep].reset_index(drop=True)


def build_drug_master(paths: PipelinePaths, labels: pd.DataFrame) -> pd.DataFrame:
    catalog_path = paths.raw_cache / "drug_features_catalog.parquet"
    if catalog_path.exists():
        catalog = pd.read_parquet(catalog_path).copy()
        catalog["DRUG_ID"] = pd.to_numeric(catalog["DRUG_ID"], errors="coerce").astype("Int64")
        catalog = catalog.dropna(subset=["DRUG_ID"]).copy()
        catalog["DRUG_ID"] = catalog["DRUG_ID"].astype(int)
        if "DRUG_NAME" in catalog.columns:
            catalog = catalog.rename(columns={"DRUG_NAME": "drug_name"})
        catalog["canonical_drug_id"] = catalog["DRUG_ID"].astype(str)
        catalog["drug_name"] = catalog["drug_name"].fillna("").astype(str)
        catalog["canonical_smiles"] = catalog["canonical_smiles"].fillna("").astype(str)
        catalog["has_smiles"] = pd.to_numeric(catalog["has_smiles"], errors="coerce").fillna(0).astype(int)
    else:
        catalog = pd.DataFrame(columns=["DRUG_ID", "drug_name", "canonical_drug_id", "canonical_smiles", "has_smiles", "match_source"])

    label_drugs = labels[["DRUG_ID", "drug_name", "putative_target", "pathway_name"]].drop_duplicates("DRUG_ID")
    master = label_drugs.merge(catalog, on=["DRUG_ID", "drug_name"], how="left")
    master["canonical_drug_id"] = master["DRUG_ID"].astype(str)
    master["drug_name"] = master["drug_name"].fillna("").astype(str)
    master["drug_name_norm"] = master["drug_name"].map(normalize_name)
    master["canonical_smiles"] = master["canonical_smiles"].fillna("").astype(str)
    master["has_smiles"] = (master["canonical_smiles"].str.len() > 0).astype(int)
    master["match_source"] = master.get("match_source", pd.Series("unmatched")).fillna("unmatched").astype(str)
    master["target_pathway"] = master["pathway_name"].fillna("").astype(str)
    master["target"] = master["putative_target"].fillna("").astype(str)
    return master.sort_values("canonical_drug_id").reset_index(drop=True)


def load_target_mapping(paths: PipelinePaths, drug_master: pd.DataFrame) -> pd.DataFrame:
    target_path = paths.raw_cache / "drug_target_mapping.parquet"
    if not target_path.exists():
        return pd.DataFrame(columns=["canonical_drug_id", "target_gene_symbol"])
    tm = pd.read_parquet(target_path).copy()
    tm["canonical_drug_id"] = tm["canonical_drug_id"].astype(str).str.strip()
    tm["target_gene_symbol"] = tm["target_gene_symbol"].astype(str).str.strip()
    valid_drugs = set(drug_master["canonical_drug_id"].astype(str))
    tm = tm[tm["canonical_drug_id"].isin(valid_drugs)].copy()
    return tm.drop_duplicates().reset_index(drop=True)


def build_sample_crispr(paths: PipelinePaths, cell_master: pd.DataFrame, max_features: int) -> pd.DataFrame:
    model_ids = cell_master.loc[cell_master["model_id"].astype(str).ne(""), "model_id"].astype(str).tolist()
    crispr_path = paths.raw_cache / "CRISPRGeneEffect.csv"
    if not crispr_path.exists():
        return cell_master[["sample_id"]].assign(sample__has_crispr_profile=0)
    crispr = pd.read_csv(crispr_path, index_col=0)
    crispr.index = crispr.index.astype(str)
    present = [m for m in model_ids if m in crispr.index]
    if not present:
        return cell_master[["sample_id"]].assign(sample__has_crispr_profile=0)

    sub = crispr.loc[present].apply(pd.to_numeric, errors="coerce")
    sub.columns = [clean_gene_name(c) for c in sub.columns]
    sub = sub.loc[:, ~sub.columns.duplicated()]
    var = sub.var(axis=0).sort_values(ascending=False)
    keep = var.head(min(max_features, len(var))).index.tolist()
    sub = sub[keep].copy()
    sub.columns = ["sample__crispr__" + c for c in sub.columns]
    sub["model_id"] = sub.index.astype(str)
    mapping = cell_master[["sample_id", "model_id"]].copy()
    mapping["model_id"] = mapping["model_id"].astype(str)
    out = mapping.merge(sub, on="model_id", how="left")
    out["sample__has_crispr_profile"] = out.iloc[:, 2:].notna().any(axis=1).astype(int)
    return out.drop(columns=["model_id"])


def build_disease_context(paths: PipelinePaths, tcga_code: str) -> pd.DataFrame:
    """Load TCGA expression data and compute disease signature (top-variance genes)."""
    code = tcga_code.upper()
    expr_path = paths.raw_cache / f"TCGA.{code}.sampleMap_HiSeqV2.gz"
    if not expr_path.exists():
        expr_path = paths.raw_cache / f"TCGA.{code}.sampleMap_HiSeqV2"
    if not expr_path.exists():
        print(f"[Step2] TCGA expression not found for {code}, returning empty context")
        return pd.DataFrame(columns=["gene_symbol", "mean_expr", "std_expr", "median_expr"])

    expr = pd.read_csv(expr_path, sep="\t", index_col=0)
    tumor_cols = [c for c in expr.columns if len(c.split("-")) >= 4 and c.split("-")[3][:2] in ("01", "06")]
    if not tumor_cols:
        tumor_cols = expr.columns.tolist()

    sub = expr[tumor_cols].apply(pd.to_numeric, errors="coerce")
    sig = pd.DataFrame({
        "gene_symbol": sub.index.astype(str),
        "mean_expr": sub.mean(axis=1).values,
        "std_expr": sub.std(axis=1).values,
        "median_expr": sub.median(axis=1).values,
    })
    sig = sig.dropna(subset=["mean_expr"]).sort_values("std_expr", ascending=False).reset_index(drop=True)
    return sig


def build_sample_features(cell_master: pd.DataFrame, sample_crispr: pd.DataFrame) -> pd.DataFrame:
    out = cell_master[["sample_id"]].drop_duplicates().merge(sample_crispr, on="sample_id", how="left")
    return out.fillna(0.0)


def build_drug_features(paths, drug_master, target_mapping, max_lincs: int):
    out = drug_master[["canonical_drug_id", "drug_name", "canonical_smiles", "has_smiles"]].copy()

    # Morgan fingerprint
    fps = []
    for _, row in out.iterrows():
        mol = mol_from_smiles_or_none(row["canonical_smiles"])
        if mol is not None:
            bits = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
            arr = np.zeros(2048, dtype=np.int8)
            DataStructs.ConvertToNumpyArray(bits, arr)
            fps.append(arr)
        else:
            fps.append(np.zeros(2048, dtype=np.int8))
    fp_df = pd.DataFrame(fps, columns=[f"drug__morgan_{i}" for i in range(2048)], index=out.index)
    out = pd.concat([out, fp_df], axis=1)
    out["drug_has_valid_smiles"] = out["has_smiles"]
    out["drug__canonical_smiles"] = out["canonical_smiles"]

    # Target list
    tgt = target_mapping.groupby("canonical_drug_id")["target_gene_symbol"].apply(lambda x: "|".join(sorted(set(x)))).reset_index()
    tgt.columns = ["canonical_drug_id", "drug__target_list"]
    out = out.merge(tgt, on="canonical_drug_id", how="left")
    out["drug__target_list"] = out["drug__target_list"].fillna("")

    # LINCS
    lincs_path = paths.raw_cache / "lincs_drug_signature_normalized.parquet"
    lincs_full = None
    if lincs_path.exists():
        lincs = pd.read_parquet(lincs_path)
        lincs["canonical_drug_id"] = lincs["canonical_drug_id"].astype(str)
        lincs_cols = [c for c in lincs.columns if c != "canonical_drug_id"]
        if len(lincs_cols) > max_lincs:
            var = lincs[lincs_cols].apply(pd.to_numeric, errors="coerce").var().sort_values(ascending=False)
            lincs_cols = var.head(max_lincs).index.tolist()
        lincs_sub = lincs[["canonical_drug_id"] + lincs_cols].copy()
        lincs_sub.columns = ["canonical_drug_id"] + [f"lincs__{c}" for c in lincs_cols]
        out = out.merge(lincs_sub, on="canonical_drug_id", how="left")
        lincs_full = lincs

    return out.fillna(0.0), lincs_full


def build_pair_features(labels, target_mapping, disease_sig, lincs_full):
    out = labels[["pair_id", "sample_id", "canonical_drug_id", "drug_name"]].copy()

    # Target overlap with disease signature top genes
    top_genes = set(disease_sig.head(500)["gene_symbol"].tolist()) if not disease_sig.empty else set()
    drug_targets = target_mapping.groupby("canonical_drug_id")["target_gene_symbol"].apply(set).to_dict()

    overlaps = []
    for _, row in out.iterrows():
        tgts = drug_targets.get(row["canonical_drug_id"], set())
        resolved = set()
        for t in tgts:
            resolved.add(TARGET_ALIASES.get(t.upper(), t.upper()))
        overlaps.append(len(resolved & top_genes))
    out["pair__target_disease_overlap"] = overlaps
    return out


def assemble_train_table(labels, sample_features, drug_features, pair_features):
    out = labels.copy()
    out = out.merge(sample_features, on="sample_id", how="left")
    out = out.merge(
        drug_features.drop(columns=["drug_name"], errors="ignore"),
        on="canonical_drug_id", how="left",
    )
    out = out.merge(
        pair_features.drop(columns=["sample_id", "canonical_drug_id", "drug_name"], errors="ignore"),
        on="pair_id", how="left",
    )
    return out.fillna(0.0)


def add_strong_context_and_smiles_features(train, target_mapping):
    out = train.copy()
    summary: dict[str, Any] = {"strong_context": {}, "smiles": {}}

    # One-hot encode pathway/classification columns
    onehot_total = 0
    for col in STRONG_CONTEXT_COLS:
        if col in out.columns:
            vals = out[col].fillna("").astype(str)
            unique = [v for v in vals.unique() if v]
            for v in unique[:20]:
                feat_name = f"ctx__{safe_feature_name(col)}__{safe_feature_name(v)}"
                out[feat_name] = (vals == v).astype(int)
                onehot_total += 1
    summary["strong_context"]["onehot_dim_for_ml"] = onehot_total

    # SMILES SVD
    smiles_col = "drug__canonical_smiles" if "drug__canonical_smiles" in out.columns else "canonical_smiles"
    smiles = out[smiles_col].fillna("").astype(str)
    valid = smiles[smiles.str.len() > 0]
    svd_dim = 0
    if len(valid) > 10:
        try:
            tfidf = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), max_features=2000)
            X_tfidf = tfidf.fit_transform(smiles)
            n_comp = min(32, X_tfidf.shape[1], X_tfidf.shape[0])
            if n_comp > 1:
                svd = TruncatedSVD(n_components=n_comp, random_state=42)
                X_svd = svd.fit_transform(X_tfidf)
                for i in range(n_comp):
                    out[f"smiles_svd_{i}"] = X_svd[:, i].astype(np.float32)
                svd_dim = n_comp
        except Exception as e:
            print(f"[Step2] SMILES SVD failed: {e}")
    summary["smiles"]["svd_dim"] = svd_dim
    return out, summary


def build_slim_table(train, max_crispr: int, max_lincs: int):
    feature_cols = numeric_feature_columns(train)

    # Limit CRISPR and LINCS features by variance
    crispr_cols = [c for c in feature_cols if c.startswith("sample__crispr__")]
    lincs_cols = [c for c in feature_cols if c.startswith("lincs__")]
    other_cols = [c for c in feature_cols if c not in crispr_cols and c not in lincs_cols]

    keep_crispr = top_variance_columns(train, crispr_cols, max_crispr)
    keep_lincs = top_variance_columns(train, lincs_cols, max_lincs)
    feature_names = other_cols + keep_crispr + keep_lincs

    meta_cols = [c for c in train.columns if c in KEY_COLUMNS]
    slim = train[meta_cols + feature_names].copy()
    summary = {
        "total_features": len(feature_names),
        "crispr_features": len(keep_crispr),
        "lincs_features": len(keep_lincs),
        "other_features": len(other_cols),
    }
    return slim, feature_names, summary


# ═══════════════════════════════════════════════════════════════════════
# MODEL TRAINING
# ═══════════════════════════════════════════════════════════════════════

class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float):
        super().__init__()
        self.block = nn.Sequential(nn.Linear(dim, dim), nn.ReLU(), nn.Dropout(dropout), nn.Linear(dim, dim))
        self.act = nn.ReLU()
    def forward(self, x):
        return self.act(x + self.block(x))

class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 128, num_blocks: int = 3, dropout: float = 0.1):
        super().__init__()
        self.input = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.ReLU(), nn.Dropout(dropout))
        self.blocks = nn.ModuleList([ResidualBlock(hidden_dim, dropout) for _ in range(num_blocks)])
        self.output = nn.Linear(hidden_dim, 1)
    def forward(self, x):
        x = self.input(x)
        for b in self.blocks:
            x = b(x)
        return self.output(x)


def fit_lightgbm(X_tr, y_tr, X_va, seed):
    import lightgbm as lgb
    m = lgb.LGBMRegressor(objective="regression", n_estimators=180, learning_rate=0.05,
                           num_leaves=31, subsample=0.85, colsample_bytree=0.85,
                           random_state=seed, verbosity=-1)
    m.fit(X_tr, y_tr)
    return m.predict(X_va).astype(np.float32)

def fit_xgboost(X_tr, y_tr, X_va, seed):
    from xgboost import XGBRegressor
    m = XGBRegressor(objective="reg:squarederror", tree_method="hist", n_estimators=180,
                      learning_rate=0.05, max_depth=5, subsample=0.85, colsample_bytree=0.85,
                      reg_lambda=1.0, random_state=seed, n_jobs=4)
    m.fit(X_tr, y_tr)
    return m.predict(X_va).astype(np.float32)

def fit_catboost(X_tr, y_tr, X_va, seed):
    from catboost import CatBoostRegressor
    m = CatBoostRegressor(iterations=180, learning_rate=0.05, depth=5, random_seed=seed,
                           verbose=0, task_type="CPU")
    m.fit(X_tr, y_tr)
    return m.predict(X_va).astype(np.float32)

def fit_residual_mlp(X_tr, y_tr, X_va, seed):
    torch.manual_seed(seed); np.random.seed(seed)
    X_tr_s, X_va_s = scale_by_train(X_tr, X_va)
    y_mean, y_std = float(y_tr.mean()), float(y_tr.std()) or 1.0
    y_tr_s = ((y_tr - y_mean) / y_std).astype(np.float32)
    ds = TensorDataset(torch.from_numpy(X_tr_s), torch.from_numpy(y_tr_s).unsqueeze(1))
    loader = DataLoader(ds, batch_size=512, shuffle=True)
    model = ResidualMLP(X_tr.shape[1]); opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.MSELoss(); model.train()
    for _ in range(12):
        for bx, by in loader:
            opt.zero_grad(); loss_fn(model(bx), by).backward(); opt.step()
    model.eval()
    with torch.no_grad():
        preds = model(torch.from_numpy(X_va_s)).squeeze(1).cpu().numpy()
    return (preds * y_std + y_mean).astype(np.float32)

def fit_mlp_simple(X_tr, y_tr, X_va, seed):
    """Simple 2-layer MLP without residual connections."""
    torch.manual_seed(seed); np.random.seed(seed)
    X_tr_s, X_va_s = scale_by_train(X_tr, X_va)
    y_mean, y_std = float(y_tr.mean()), float(y_tr.std()) or 1.0
    y_tr_s = ((y_tr - y_mean) / y_std).astype(np.float32)
    ds = TensorDataset(torch.from_numpy(X_tr_s), torch.from_numpy(y_tr_s).unsqueeze(1))
    loader = DataLoader(ds, batch_size=512, shuffle=True)
    model = nn.Sequential(nn.Linear(X_tr.shape[1], 256), nn.ReLU(), nn.Dropout(0.1),
                           nn.Linear(256, 128), nn.ReLU(), nn.Dropout(0.1), nn.Linear(128, 1))
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.MSELoss(); model.train()
    for _ in range(12):
        for bx, by in loader:
            opt.zero_grad(); loss_fn(model(bx), by).backward(); opt.step()
    model.eval()
    with torch.no_grad():
        preds = model(torch.from_numpy(X_va_s)).squeeze(1).cpu().numpy()
    return (preds * y_std + y_mean).astype(np.float32)


MODEL_REGISTRY = {
    "lightgbm": fit_lightgbm,
    "xgboost": fit_xgboost,
    "catboost": fit_catboost,
    "residual_mlp": fit_residual_mlp,
    "mlp": fit_mlp_simple,
}


def train_models(paths, model_names, n_splits=3, random_state=42):
    random_state = set_step_seed(random_state)
    train = pd.read_parquet(paths.slim_inputs / "train_table.parquet")
    feature_names = json.loads((paths.slim_inputs / "feature_names.json").read_text())
    X = train[feature_names].apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy(dtype=np.float32)
    y = train["label_regression"].to_numpy(dtype=np.float32)
    groups = train["canonical_drug_id"].astype(str).to_numpy()
    pair_ids = train["pair_id"].astype(str).to_numpy()

    all_metrics: dict[str, Any] = {"n_rows": int(len(train)), "n_features": int(X.shape[1]), "models": {}}
    all_oof: dict[tuple[str, str], np.ndarray] = {}

    for split_type in ["groupcv", "randomcv"]:
        n = min(n_splits, len(np.unique(groups)) if split_type == "groupcv" else len(y))
        if split_type == "groupcv":
            splits = list(GroupKFold(n_splits=n).split(X, y, groups))
        else:
            splits = list(KFold(n_splits=n, shuffle=True, random_state=random_state).split(X, y))

        for model_name in model_names:
            if model_name not in MODEL_REGISTRY:
                print(f"[Step2] Unknown model: {model_name}, skipping")
                continue
            print(f"[Step2] Training {model_name} / {split_type}", flush=True)
            fit_fn = MODEL_REGISTRY[model_name]
            oof = np.zeros(len(y), dtype=np.float32)
            folds = []
            for fold_idx, (tr, va) in enumerate(splits, start=1):
                if model_name in ("catboost",):
                    preds = fit_fn(X[tr], y[tr], X[va], random_state + fold_idx)
                else:
                    preds = fit_fn(X[tr], y[tr], X[va], random_state + fold_idx)
                oof[va] = preds
                folds.append({"fold": fold_idx, "spearman": spearman(y[va], preds), "rmse": rmse(y[va], preds)})
            metrics = {"spearman": spearman(y, oof), "rmse": rmse(y, oof), "fold_metrics": folds,
                       "split_type": split_type, "model": model_name}
            all_metrics["models"][f"{split_type}__{model_name}"] = metrics
            all_oof[(split_type, model_name)] = oof
            pd.DataFrame({
                "pair_id": pair_ids, "sample_id": train["sample_id"].astype(str),
                "canonical_drug_id": groups, "drug_name": train["drug_name"].astype(str),
                "y_true": y, "y_pred": oof, "split_type": split_type, "model": model_name,
            }).to_parquet(paths.model_runs / f"oof_{split_type}_{model_name}.parquet", index=False)

    # Ensemble (top-3 groupcv by Spearman)
    group_models = []
    for key, payload in all_metrics["models"].items():
        if key.startswith("groupcv__"):
            group_models.append((key.split("__", 1)[1], float(payload["spearman"])))
    group_models = sorted(group_models, key=lambda x: x[1], reverse=True)[:3]
    if group_models:
        raw_w = np.array([max(s, 0.0) for _, s in group_models], dtype=np.float32)
        if raw_w.sum() <= 1e-8:
            raw_w = np.ones(len(group_models), dtype=np.float32)
        weights = raw_w / raw_w.sum()
        pred = sum(w * all_oof[("groupcv", m)] for (m, _), w in zip(group_models, weights))
        ensemble_summary = {
            "models": [{"model": m, "spearman": s, "weight": float(w)} for (m, s), w in zip(group_models, weights)],
            "spearman": spearman(y, pred), "rmse": rmse(y, pred),
        }
        pd.DataFrame({
            "pair_id": pair_ids, "sample_id": train["sample_id"].astype(str),
            "canonical_drug_id": groups, "drug_name": train["drug_name"].astype(str),
            "y_true": y, "y_pred": pred, "split_type": "groupcv", "model": "weighted_top3_ensemble",
        }).to_parquet(paths.model_runs / "oof_groupcv_weighted_top3_ensemble.parquet", index=False)
        all_metrics["groupcv_ensemble"] = ensemble_summary
        write_json(paths.model_runs / "ensemble_summary.json", ensemble_summary)

    write_json(paths.model_runs / "metrics_summary.json", all_metrics)
    return all_metrics


# ═══════════════════════════════════════════════════════════════════════
# RANKING & EXTERNAL VALIDATION
# ═══════════════════════════════════════════════════════════════════════

def aggregate_drug_scores(pair: pd.DataFrame, drug_meta: pd.DataFrame) -> pd.DataFrame:
    meta_defaults = {
        "drug_name": "",
        "canonical_smiles": "",
        "has_smiles": 0,
        "putative_target": "",
        "pathway_name": "",
        "drug__target_list": "",
    }
    drug_meta = drug_meta.copy()
    for col, default in meta_defaults.items():
        if col not in drug_meta.columns:
            drug_meta[col] = default
    agg = pair.groupby("canonical_drug_id").agg(
        mean_y_pred=("y_pred", "mean"),
        mean_y_true=("y_true", "mean"),
        std_y_pred=("y_pred", "std"),
        n_pairs=("pair_id", "size"),
        pred_top5_rate=("pred_top5", "mean"),
        pred_top10_rate=("pred_top10", "mean"),
        pred_top20_rate=("pred_top20", "mean"),
    ).reset_index()
    agg["final_selection_score"] = (
        0.4 * percentile_score(-agg["mean_y_pred"]) +
        0.3 * percentile_score(agg["pred_top20_rate"]) +
        0.2 * percentile_score(agg["pred_top10_rate"]) +
        0.1 * percentile_score(agg["pred_top5_rate"])
    )
    agg = agg.merge(
        drug_meta[["canonical_drug_id", "drug_name", "canonical_smiles", "has_smiles",
                    "putative_target", "pathway_name", "drug__target_list"]].drop_duplicates("canonical_drug_id"),
        on="canonical_drug_id", how="left",
    )
    for col in ["drug_name", "canonical_smiles", "putative_target", "pathway_name", "drug__target_list"]:
        if col not in agg.columns:
            agg[col] = ""
    return agg


def rank_and_filter(paths, candidate_limit=30):
    pred_path = paths.model_runs / "oof_groupcv_weighted_top3_ensemble.parquet"
    if not pred_path.exists():
        pred_path = paths.model_runs / "oof_groupcv_lightgbm.parquet"
    preds = pd.read_parquet(pred_path)
    train = pd.read_parquet(paths.slim_inputs / "train_table.parquet")
    drug_meta = pd.read_parquet(paths.standardized / "drug_master.parquet")

    pair = preds.merge(
        train[["pair_id", "drug__canonical_smiles", "drug_has_valid_smiles", "drug__target_list"]].drop_duplicates("pair_id"),
        on="pair_id", how="left",
    )
    pair["pred_rank_within_sample"] = pair.groupby("sample_id")["y_pred"].rank(method="min", ascending=True)
    for k in [5, 10, 20]:
        pair[f"pred_top{k}"] = (pair["pred_rank_within_sample"] <= k).astype(int)

    drug_scores = aggregate_drug_scores(pair, drug_meta)
    drug_scores = drug_scores.sort_values(
        ["final_selection_score", "pred_top20_rate", "mean_y_pred"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    drug_scores["final_rank"] = np.arange(1, len(drug_scores) + 1)

    # Save
    pair.to_parquet(paths.final_selection / "pair_predictions.parquet", index=False)
    drug_scores.to_parquet(paths.final_selection / "final_drug_scores.parquet", index=False)
    selected = drug_scores.head(candidate_limit).copy()
    selected.to_csv(paths.final_selection / "selected_drugs_top_n.csv", index=False)

    write_json(paths.final_selection / "selection_summary.json", {
        "n_pairs": int(pair.shape[0]),
        "n_drugs": int(drug_scores.shape[0]),
        "candidate_limit": candidate_limit,
        "top10": selected.head(10)[["final_rank", "drug_name", "final_selection_score"]].to_dict("records"),
    })
    return drug_scores, pair


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC INTERFACE
# ═══════════════════════════════════════════════════════════════════════

def run(config: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    """Entry point called by orchestrator.

    Args:
        config: Parsed YAML config with keys:
            - disease / tcga_code
            - project_root
            - models: list of model names (default: lightgbm,xgboost,catboost,residual_mlp,mlp)
            - n_splits (default: 3)
            - candidate_limit (default: 30)
            - max_crispr_features (default: 3000)
            - max_lincs_features (default: 768)
    """
    raw = config.get("tcga_code", config.get("disease", "UNKNOWN"))
    if isinstance(raw, dict):
        tcga_code = str(raw.get("code", raw.get("name", "UNKNOWN"))).upper()
    else:
        tcga_code = str(raw).upper()
    project_root = Path(config.get("project_root", f"./{tcga_code}_pipeline"))
    model_names = config.get("models", ["lightgbm", "xgboost", "catboost", "residual_mlp", "mlp"])
    if isinstance(model_names, str):
        model_names = [m.strip() for m in model_names.split(",")]
    n_splits = config.get("n_splits", 3)
    candidate_limit = config.get("candidate_limit", 30)
    max_crispr = config.get("max_crispr_features", 3000)
    max_lincs = config.get("max_lincs_features", 768)

    paths = make_paths(project_root)
    ensure_dirs(paths)
    if dry_run:
        return {
            "status": "dry_run",
            "step": "step2_basic_pipeline",
            "disease": tcga_code,
            "project_root": str(project_root),
            "models": model_names,
            "n_splits": n_splits,
            "candidate_limit": candidate_limit,
        }

    # ── FE ──
    print(f"[Step2] Building features for {tcga_code} ...", flush=True)
    gdsc = load_gdsc(paths, tcga_code)
    cell_master = build_cell_line_master(paths, gdsc, tcga_code)
    response_labels = build_response_labels(gdsc, cell_master)
    drug_master = build_drug_master(paths, response_labels)
    target_mapping = load_target_mapping(paths, drug_master)
    sample_crispr = build_sample_crispr(paths, cell_master, max_crispr)
    disease_sig = build_disease_context(paths, tcga_code)
    sample_features = build_sample_features(cell_master, sample_crispr)
    drug_features, lincs_full = build_drug_features(paths, drug_master, target_mapping, max_lincs)
    pair_features = build_pair_features(response_labels, target_mapping, disease_sig, lincs_full)
    train_table = assemble_train_table(response_labels, sample_features, drug_features, pair_features)
    train_table, ctx_summary = add_strong_context_and_smiles_features(train_table, target_mapping)
    slim_table, feature_names, slim_summary = build_slim_table(train_table, max_crispr, max_lincs)

    # Save intermediates
    gdsc.to_parquet(paths.standardized / "gdsc_response.parquet", index=False)
    cell_master.to_parquet(paths.standardized / "cell_line_master.parquet", index=False)
    response_labels.to_parquet(paths.standardized / "response_labels.parquet", index=False)
    drug_master.to_parquet(paths.standardized / "drug_master.parquet", index=False)
    target_mapping.to_parquet(paths.standardized / "drug_target_mapping.parquet", index=False)
    disease_sig.to_parquet(paths.disease_context / f"{tcga_code.lower()}_signature.parquet", index=False)
    slim_table.to_parquet(paths.slim_inputs / "train_table.parquet", index=False)
    np.save(paths.slim_inputs / "X.npy", slim_table[feature_names].to_numpy(dtype=np.float32))
    np.save(paths.slim_inputs / "y.npy", slim_table["label_regression"].to_numpy(dtype=np.float32))
    write_json(paths.slim_inputs / "feature_names.json", feature_names)

    fe_summary = {
        "gdsc_rows": int(len(gdsc)), "cell_lines": int(len(cell_master)),
        "drugs": int(len(drug_master)), "pairs": int(len(slim_table)),
        "features": int(len(feature_names)), "slim_summary": slim_summary,
    }
    write_json(paths.slim_inputs / "fe_summary.json", fe_summary)
    print(f"[Step2] FE complete: {fe_summary}", flush=True)

    # ── Train ──
    print(f"[Step2] Training {len(model_names)} models ...", flush=True)
    random_state = int(config.get("random_seed", 42) or 42)
    metrics = train_models(paths, model_names, n_splits, random_state=random_state)

    # ── Rank ──
    print(f"[Step2] Ranking and selecting top {candidate_limit} ...", flush=True)
    drug_scores, pair = rank_and_filter(paths, candidate_limit)

    summary = {
        "step": "step2_basic_pipeline",
        "disease": tcga_code,
        "fe": fe_summary,
        "ensemble_spearman": metrics.get("groupcv_ensemble", {}).get("spearman"),
        "top5_drugs": drug_scores.head(5)[["drug_name", "final_selection_score"]].to_dict("records"),
    }
    print(f"[Step2] Complete. Ensemble Spearman: {summary['ensemble_spearman']}", flush=True)
    return summary


if __name__ == "__main__":
    import argparse, yaml
    parser = argparse.ArgumentParser(description="Step 2: Basic Pipeline")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config) as f:
        config = yaml.safe_load(f)
    run(config)
