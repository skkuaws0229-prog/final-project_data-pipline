#!/usr/bin/env python3
"""
Step 7-1: ADMET Gate (초이 프로토콜 방식)

22개 ADMET assay + Tanimoto similarity 매칭 + Safety Score.

방법론 (초이 원본 준수):
  1. Top 30 약물 SMILES 로드
  2. 22개 TDC ADMET assay 라이브러리 로드 (로컬 CSV)
  3. Morgan Fingerprint + Tanimoto 매칭 (exact/close_analog/analog)
  4. Safety Score 계산 (assay 가중치 기반)
  5. Verdict: PASS (>=6) / WARNING (>=4) / FAIL (<4)

입력:
  - results/colon_top30_drugs_ensemble.csv
  - data/drug_features.parquet (SMILES)
  - curated_data/admet/tdc_admet_group/admet_group/ (22 assays)

출력:
  - results/colon_drugs_with_admet.csv
  - results/colon_admet_summary.json
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, DataStructs, Descriptors, FilterCatalog

    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False
    print("WARNING: RDKit not installed. ADMET analysis will be limited.")


# --- 22개 ADMET Assay 정의 (초이 원본) ---

ADMET_ASSAYS = {
    "ames": {"category": "Toxicity", "name": "Ames Mutagenicity", "weight": -2.0, "good_value": 0},
    "dili": {"category": "Toxicity", "name": "DILI (Liver Injury)", "weight": -2.0, "good_value": 0},
    "herg": {"category": "Toxicity", "name": "hERG Cardiotoxicity", "weight": -1.5, "good_value": 0},
    "ld50_zhu": {"category": "Toxicity", "name": "Acute Toxicity (LD50)", "weight": 1.0, "good_direction": "high"},
    "bioavailability_ma": {"category": "Absorption", "name": "Oral Bioavailability", "weight": 1.0, "good_value": 1},
    "bbb_martins": {"category": "Distribution", "name": "BBB Penetration", "weight": 0.5, "good_value": None},
    "caco2_wang": {"category": "Absorption", "name": "Caco-2 Permeability", "weight": 0.5, "good_direction": "high"},
    "hia_hou": {"category": "Absorption", "name": "HIA (Intestinal Absorption)", "weight": 0.5, "good_value": 1},
    "pgp_broccatelli": {"category": "Absorption", "name": "P-gp Inhibitor", "weight": -0.5, "good_value": 0},
    "ppbr_az": {"category": "Distribution", "name": "Plasma Protein Binding", "weight": 0.3, "good_direction": "low"},
    "vdss_lombardo": {"category": "Distribution", "name": "Volume of Distribution", "weight": 0.3, "good_direction": None},
    "cyp2c9_veith": {"category": "Metabolism", "name": "CYP2C9 Inhibitor", "weight": -0.5, "good_value": 0},
    "cyp2d6_veith": {"category": "Metabolism", "name": "CYP2D6 Inhibitor", "weight": -0.5, "good_value": 0},
    "cyp3a4_veith": {"category": "Metabolism", "name": "CYP3A4 Inhibitor", "weight": -0.5, "good_value": 0},
    "cyp2c9_substrate_carbonmangels": {"category": "Metabolism", "name": "CYP2C9 Substrate", "weight": 0.2, "good_value": None},
    "cyp2d6_substrate_carbonmangels": {"category": "Metabolism", "name": "CYP2D6 Substrate", "weight": 0.2, "good_value": None},
    "cyp3a4_substrate_carbonmangels": {"category": "Metabolism", "name": "CYP3A4 Substrate", "weight": 0.2, "good_value": None},
    "clearance_hepatocyte_az": {"category": "Excretion", "name": "Hepatocyte Clearance", "weight": 0.5, "good_direction": None},
    "clearance_microsome_az": {"category": "Excretion", "name": "Microsome Clearance", "weight": 0.5, "good_direction": None},
    "half_life_obach": {"category": "Excretion", "name": "Half-Life", "weight": 0.5, "good_direction": "high"},
    "lipophilicity_astrazeneca": {"category": "Properties", "name": "Lipophilicity (logD)", "weight": 0.3, "good_direction": None},
    "solubility_aqsoldb": {"category": "Properties", "name": "Aqueous Solubility", "weight": 0.5, "good_direction": "high"},
}

SIMILARITY_THRESHOLDS = {
    "exact": 1.0,
    "close_analog": 0.85,
    "analog": 0.70,
}


# --- RDKit 함수 ---

def get_fingerprint(smiles):
    """Morgan fingerprint (radius=2, 2048 bits)"""
    if not HAS_RDKIT or not smiles or pd.isna(smiles):
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            return AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    except Exception:
        pass
    return None


def calculate_descriptors(smiles):
    """RDKit 물리화학적 descriptor 계산"""
    if not HAS_RDKIT or not smiles or pd.isna(smiles):
        return {}
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {}
        return {
            "mw": round(Descriptors.MolWt(mol), 2),
            "logp": round(Descriptors.MolLogP(mol), 2),
            "hbd": Descriptors.NumHDonors(mol),
            "hba": Descriptors.NumHAcceptors(mol),
            "tpsa": round(Descriptors.TPSA(mol), 2),
            "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
        }
    except Exception:
        return {}


def check_pains(smiles):
    """PAINS 필터"""
    if not HAS_RDKIT or not smiles or pd.isna(smiles):
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        params = FilterCatalog.FilterCatalogParams()
        params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
        catalog = FilterCatalog.FilterCatalog(params)
        return catalog.HasMatch(mol)
    except Exception:
        return None


# --- 데이터 로드 ---

def load_top_drugs(results_dir, base_dir):
    """Top 30 약물 + SMILES 로드"""
    df = pd.read_csv(results_dir / "colon_top30_drugs_ensemble.csv")
    print(f"  Top drugs: {len(df)}")

    # SMILES 매핑
    feat_path = base_dir / "data" / "drug_features.parquet"
    if feat_path.exists():
        drug_feat = pd.read_parquet(feat_path, columns=["canonical_drug_id", "canonical_smiles"])
        drug_feat = drug_feat.drop_duplicates("canonical_drug_id")
        df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
        drug_feat["canonical_drug_id"] = drug_feat["canonical_drug_id"].astype(str)
        df = df.merge(drug_feat, on="canonical_drug_id", how="left", suffixes=("", "_feat"))

    smiles_col = None
    for col in ["canonical_smiles", "canonical_smiles_feat"]:
        if col in df.columns:
            smiles_col = col
            break

    has_smiles = df[smiles_col].notna().sum() if smiles_col else 0
    print(f"  SMILES available: {has_smiles}/{len(df)}")

    return df, smiles_col


def load_assay_libraries(admet_dir):
    """22개 ADMET assay 라이브러리 로드 (로컬 CSV)"""
    admet_base = admet_dir / "tdc_admet_group" / "admet_group"
    libraries = {}

    for assay_name, assay_info in ADMET_ASSAYS.items():
        assay_path = admet_base / assay_name
        if not assay_path.exists():
            print(f"  ⚠️ Missing: {assay_name}")
            continue

        # train_val + test 합치기
        dfs = []
        for csv_name in ["train_val.csv", "test.csv"]:
            csv_path = assay_path / csv_name
            if csv_path.exists():
                dfs.append(pd.read_csv(csv_path))

        if not dfs:
            continue

        combined = pd.concat(dfs, ignore_index=True)

        # Drug 컬럼 = SMILES, Y = 값
        if "Drug" not in combined.columns or "Y" not in combined.columns:
            continue

        # fingerprint 사전 계산
        valid_rows = []
        for _, row in combined.iterrows():
            fp = get_fingerprint(row["Drug"])
            if fp is not None:
                valid_rows.append({"smiles": row["Drug"], "y": row["Y"], "fp": fp})

        libraries[assay_name] = {
            "info": assay_info,
            "data": valid_rows,
            "total": len(combined),
            "with_fp": len(valid_rows),
        }

    print(f"  Loaded {len(libraries)}/22 assay libraries")
    return libraries


# --- Tanimoto 매칭 ---

def perform_tanimoto_matching(drugs_df, smiles_col, assay_libraries):
    """각 약물을 22개 assay 라이브러리와 Tanimoto 매칭"""
    results = {}

    for idx, row in drugs_df.iterrows():
        drug_name = row.get("DRUG_NAME", row.get("drug_name_norm", f"drug_{idx}"))
        smiles = row.get(smiles_col, "")
        drug_fp = get_fingerprint(smiles)

        drug_result = {
            "drug_name": drug_name,
            "smiles": smiles,
            "assays": {},
            "n_exact": 0,
            "n_close_analog": 0,
            "n_analog": 0,
            "n_total_matches": 0,
        }

        if drug_fp is None:
            results[drug_name] = drug_result
            continue

        for assay_name, lib in assay_libraries.items():
            best_sim = 0.0
            best_value = None
            best_type = None

            for entry in lib["data"]:
                sim = DataStructs.TanimotoSimilarity(drug_fp, entry["fp"])
                if sim > best_sim:
                    best_sim = sim
                    best_value = entry["y"]

            # threshold 판정
            if best_sim >= SIMILARITY_THRESHOLDS["exact"]:
                best_type = "exact"
                drug_result["n_exact"] += 1
            elif best_sim >= SIMILARITY_THRESHOLDS["close_analog"]:
                best_type = "close_analog"
                drug_result["n_close_analog"] += 1
            elif best_sim >= SIMILARITY_THRESHOLDS["analog"]:
                best_type = "analog"
                drug_result["n_analog"] += 1

            if best_type:
                drug_result["n_total_matches"] += 1
                drug_result["assays"][assay_name] = {
                    "similarity": round(best_sim, 4),
                    "value": best_value,
                    "match_type": best_type,
                    "assay_name": lib["info"]["name"],
                }

        results[drug_name] = drug_result

    return results


# --- Safety Score ---

def calculate_safety_scores(match_results, drugs_df, smiles_col):
    """초이 방식 Safety Score 계산"""
    rows = []

    for drug_name, result in match_results.items():
        safety_score = 5.0  # 기본점

        for assay_name, match in result["assays"].items():
            assay_info = ADMET_ASSAYS[assay_name]
            value = match["value"]
            weight = assay_info["weight"]

            if value is not None:
                good_value = assay_info.get("good_value")
                good_direction = assay_info.get("good_direction")

                if good_value is not None:
                    # 이진 분류: good_value 와 일치하면 +, 아니면 weight 적용
                    if value == good_value:
                        contribution = abs(weight) * 0.5  # 좋은 결과 보너스
                    else:
                        contribution = weight  # 나쁜 결과 페널티
                elif good_direction == "high":
                    contribution = weight * 0.5
                elif good_direction == "low":
                    contribution = weight * 0.5
                else:
                    contribution = 0  # neutral

                safety_score += contribution

        # Verdict
        if safety_score >= 6.0:
            verdict = "PASS"
        elif safety_score >= 4.0:
            verdict = "WARNING"
        else:
            verdict = "FAIL"

        # RDKit descriptors
        smiles = result["smiles"]
        desc = calculate_descriptors(smiles)
        pains = check_pains(smiles)

        # drug row 에서 추가 정보
        drug_row = drugs_df[drugs_df.get("DRUG_NAME", drugs_df.get("drug_name_norm", pd.Series())) == drug_name]
        if len(drug_row) == 0:
            drug_row_dict = {}
        else:
            drug_row_dict = drug_row.iloc[0].to_dict()

        rows.append(
            {
                "rank": drug_row_dict.get("rank", 0),
                "drug_name": drug_name,
                "canonical_drug_id": drug_row_dict.get("canonical_drug_id", ""),
                "pred_ic50_mean": drug_row_dict.get("pred_ic50_mean", 0),
                "target": drug_row_dict.get("TARGET", ""),
                "target_pathway": drug_row_dict.get("TARGET_PATHWAY", ""),
                "smiles": smiles,
                "safety_score": round(safety_score, 4),
                "verdict": verdict,
                "n_total_matches": result["n_total_matches"],
                "n_exact": result["n_exact"],
                "n_close_analog": result["n_close_analog"],
                "n_analog": result["n_analog"],
                "pains_alert": pains,
                **desc,  # mw, logp, hbd, hba, tpsa, rotatable_bonds
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("safety_score", ascending=False).reset_index(drop=True)
    return df


# --- Main ---

def main():
    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / "results"
    admet_dir = base_dir / "curated_data" / "admet"

    print("=" * 80)
    print("Step 7-1: ADMET Gate (Choi Protocol — 22 Assays + Tanimoto)")
    print("=" * 80)

    if not HAS_RDKIT:
        print("\n❌ RDKit required for ADMET analysis. Install with:")
        print("   pip install rdkit --break-system-packages")
        return

    # 1. Top drugs
    print("\n[1] Top drugs + SMILES 로드")
    drugs_df, smiles_col = load_top_drugs(results_dir, base_dir)

    # 2. Assay libraries
    print("\n[2] 22개 ADMET assay 라이브러리 로드")
    assay_libraries = load_assay_libraries(admet_dir)

    # 3. Tanimoto matching
    print("\n[3] Tanimoto 매칭 (22 assays × 30 drugs)")
    print("  이 단계는 시간이 걸릴 수 있습니다...")
    match_results = perform_tanimoto_matching(drugs_df, smiles_col, assay_libraries)

    # 매칭 통계
    for drug_name, result in match_results.items():
        print(
            f"  {drug_name:25s}: {result['n_total_matches']:2d}/22 matched "
            f"(exact={result['n_exact']}, close={result['n_close_analog']}, analog={result['n_analog']})"
        )

    # 4. Safety Score
    print("\n[4] Safety Score 계산")
    df_scored = calculate_safety_scores(match_results, drugs_df, smiles_col)

    # 5. 통계
    print("\n[5] 통계")
    verdict_counts = df_scored["verdict"].value_counts().to_dict()
    print(f"  Verdict: {verdict_counts}")
    print(
        f"  Safety Score: mean={df_scored['safety_score'].mean():.2f}, "
        f"min={df_scored['safety_score'].min():.2f}, max={df_scored['safety_score'].max():.2f}"
    )
    print(f"  Avg matches: {df_scored['n_total_matches'].mean():.1f}/22")

    pains_count = df_scored["pains_alert"].sum() if "pains_alert" in df_scored.columns else 0
    print(f"  PAINS alerts: {pains_count}")

    # 6. 저장
    print("\n[6] 저장")

    csv_path = results_dir / "colon_drugs_with_admet.csv"
    df_scored.to_csv(csv_path, index=False)
    print(f"  ✅ {csv_path}")

    summary = {
        "step": "Step 7-1 ADMET Gate (Choi Protocol)",
        "method": "22 ADMET assays + Tanimoto similarity matching",
        "thresholds": SIMILARITY_THRESHOLDS,
        "total_drugs": len(df_scored),
        "verdict_counts": verdict_counts,
        "avg_safety_score": round(df_scored["safety_score"].mean(), 4),
        "avg_matches": round(df_scored["n_total_matches"].mean(), 2),
        "assays_loaded": len(assay_libraries),
        "pains_alerts": int(pains_count) if pains_count else 0,
        "rdkit_available": HAS_RDKIT,
        "status_detail": [],
    }

    name_col = "DRUG_NAME" if "DRUG_NAME" in drugs_df.columns else "drug_name_norm"
    for _, row in df_scored.iterrows():
        summary["status_detail"].append(
            {
                "rank": int(row.get("rank", 0)),
                "drug": row["drug_name"],
                "safety_score": row["safety_score"],
                "verdict": row["verdict"],
                "matches": int(row["n_total_matches"]),
                "mw": row.get("mw"),
                "logp": row.get("logp"),
                "tpsa": row.get("tpsa"),
            }
        )

    # match_results 도 저장 (상세 assay 결과)
    results_detail = {}
    for drug_name, result in match_results.items():
        results_detail[drug_name] = {
            "n_total_matches": result["n_total_matches"],
            "n_exact": result["n_exact"],
            "n_close_analog": result["n_close_analog"],
            "n_analog": result["n_analog"],
            "assays": result["assays"],
        }
    summary["match_details"] = results_detail

    json_path = results_dir / "colon_admet_summary.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  ✅ {json_path}")

    # 7. 요약
    print("\n" + "=" * 80)
    print("ADMET Gate Summary (Choi Protocol)")
    print("=" * 80)
    print("  Method: 22 ADMET assays + Tanimoto matching (≥0.70)")
    print(f"  Assays loaded: {len(assay_libraries)}/22")
    print(f"  Avg matches per drug: {df_scored['n_total_matches'].mean():.1f}")
    print()
    print(
        f"  Verdict: PASS={verdict_counts.get('PASS',0)}, "
        f"WARNING={verdict_counts.get('WARNING',0)}, "
        f"FAIL={verdict_counts.get('FAIL',0)}"
    )
    print(f"  Avg Safety Score: {df_scored['safety_score'].mean():.2f}")
    print()

    print(
        f"{'Rank':>4} {'Drug':25s} {'Score':>7} {'Verdict':>8} {'Match':>5} "
        f"{'MW':>7} {'LogP':>6} {'TPSA':>7} {'PAINS':>6}"
    )
    print("-" * 95)
    for _, row in df_scored.iterrows():
        v_icon = "✅" if row["verdict"] == "PASS" else "⚠️" if row["verdict"] == "WARNING" else "❌"
        p_icon = "⚠️" if row.get("pains_alert") else "✅" if row.get("pains_alert") is not None else "?"
        print(
            f"#{int(row.get('rank',0)):3d} {row['drug_name']:25s} {row['safety_score']:>7.2f} {v_icon:>8} "
            f"{int(row['n_total_matches']):>5}/22 {row.get('mw','?'):>7} {row.get('logp','?'):>6} "
            f"{row.get('tpsa','?'):>7} {p_icon:>6}"
        )

    print("\n✅ Step 7-1 완료!")


if __name__ == "__main__":
    main()
