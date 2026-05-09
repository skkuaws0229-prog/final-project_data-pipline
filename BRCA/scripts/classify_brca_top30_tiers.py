#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd


WORKSPACE = Path(__file__).resolve().parent.parent
OUT_DIR = WORKSPACE / "20260428_new_BRCA_data"
TOP30_CSV = OUT_DIR / "brca_directive_top30_unique_candidates.csv"
VALIDATION_CSV = OUT_DIR / "brca_directive_ensemble_validation_summary.csv"


TIER_DEFINITIONS = {
    1: {
        "tier_name": "유방암 치료제",
        "validation_goal": "유방암 치료 맥락의 positive control 확인",
    },
    2: {
        "tier_name": "유방암 적응증 확장 연구 치료제",
        "validation_goal": "유방암 임상연구/적응증 확장 가능성 확인",
    },
    3: {
        "tier_name": "유방암 비사용 치료제",
        "validation_goal": "타 적응증 치료제의 신규 repurposing 탐색",
    },
    4: {
        "tier_name": "화합물 또는 미지 약물",
        "validation_goal": "비승인 화합물/보충제/실험용 물질 분리",
    },
}


TIER_MAP = {
    "ascorbate (vitamin C)": (4, "보충제 성격의 비항암 물질로, 치료제군과 분리 필요"),
    "N-acetyl cysteine": (4, "보충제/항산화 물질로, 치료제보다는 artifact 후보 성격이 큼"),
    "glutathione": (4, "내인성 항산화 물질로 치료제보다는 대사성 보조물질 성격이 강함"),
    "alpha-lipoic acid": (4, "보충제 성격이 강한 물질로 유방암 치료제 tier와 분리"),
    "CZC24832": (4, "승인 치료제가 아닌 연구용 저분자 화합물"),
    "BEN": (4, "현재 명칭만으로 승인 치료제로 확인되지 않는 실험성/미지 후보"),
    "CCT007093": (4, "승인 치료제가 아닌 연구용 저분자 화합물"),
    "A-366": (4, "승인 치료제가 아닌 연구용 저분자 화합물"),
    "THR-101": (4, "승인 치료제로 정착되지 않은 개발/실험 단계 후보"),
    "GSK2830371": (4, "승인 치료제가 아닌 연구용 저분자 화합물"),
    "SB216763": (4, "승인 치료제가 아닌 연구용 저분자 화합물"),
    "MIRA-1": (4, "승인 치료제가 아닌 연구용 저분자 화합물"),
    "PRIMA-1MET": (4, "개발 코드명 기반 후보로 승인 치료제군과 분리"),
    "PCI-34051": (4, "승인 치료제가 아닌 연구용 저분자 화합물"),
    "AZD1208": (4, "개발 코드명 기반 후보로 승인 치료제군과 분리"),
    "JNK Inhibitor VIII": (4, "연구용 inhibitor 명칭으로 임상 치료제군과 분리"),
    "ML323": (4, "승인 치료제가 아닌 연구용 저분자 화합물"),
    "GSK2801": (4, "승인 치료제가 아닌 연구용 저분자 화합물"),
    "LY2109761": (4, "개발 코드명 기반 후보로 승인 치료제군과 분리"),
    "5-Fluorouracil": (1, "NCI breast cancer approved drug list에 포함되는 유방암 치료제"),
    "Cyclophosphamide": (1, "NCI breast cancer approved drug list 및 AC/FEC/CMF 조합에 포함되는 유방암 치료제"),
    "Temozolomide": (2, "타 적응증 치료제이며 TNBC/전이성 유방암 임상연구 기록이 확인됨"),
    "Oxaliplatin": (2, "타 적응증 승인 치료제이며 재발/전이성 유방암 임상연구 기록이 확인됨"),
    "Ruxolitinib": (2, "타 적응증 승인 치료제이며 유방암/전암성 유방병변 임상연구 기록이 확인됨"),
    "Veliparib": (2, "유방암 특히 BRCA 연관/삼중음성 유방암에서 다수 임상연구가 확인된 치료 후보"),
    "Motesanib": (2, "유방암 병용요법 임상연구가 확인된 개발 치료 후보"),
    "Dacarbazine": (3, "승인 치료제이지만 현재 기준 유방암 직접 치료/확장 임상 근거는 뚜렷하지 않음"),
    "Fludarabine": (3, "승인 치료제이지만 유방암 직접 치료제보다 혈액암/전처치 맥락이 중심"),
    "Nelarabine": (3, "승인 치료제이지만 적응증은 T-ALL/T-LBL로 유방암 사용 근거가 뚜렷하지 않음"),
    "Lenalidomide": (3, "승인 치료제이지만 현재 확인된 주 적응증은 혈액암 계열로 유방암 직접 사용 근거가 제한적"),
}


def classify_drug(name: str) -> tuple[int, str]:
    if name in TIER_MAP:
        return TIER_MAP[name]
    return 4, "현 시점 근거만으로 승인 치료제/유방암 임상연구 치료제로 분류하기 어려워 화합물/미지 약물로 우선 분리"


def build_summary_md(
    tiered: pd.DataFrame,
    validation: pd.DataFrame,
) -> str:
    winner = "A"
    counts = (
        tiered.groupby(["tier", "tier_name"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("tier")
    )

    lines = [
        "# BRCA Current Status",
        "",
        "- Status date: 2026-04-28",
        "- Ensemble directive applied: `BRCA_ensemble_directive.md`",
        "- Current ensemble winner: **A안**",
        "- Current tier classification status: **redefined by breast-cancer treatment / breast-trial / non-breast-therapy / compound criteria**",
        "",
        "## Ensemble Validation",
        "",
        "| Config | Eval Mode | Spearman | RMSE | Mean Component Std |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for _, row in validation.sort_values(["eval_mode", "config"]).iterrows():
        lines.append(
            f"| {row['config']} | {row['eval_mode']} | {row['spearman']:.4f} | "
            f"{row['rmse']:.4f} | {row['component_pred_std_mean']:.4f} |"
        )

    lines += [
        "",
        "## Tier Count",
        "",
        "| Tier | Name | Count |",
        "| --- | --- | ---: |",
    ]
    for _, row in counts.iterrows():
        lines.append(f"| {int(row['tier'])} | {row['tier_name']} | {int(row['count'])} |")

    for tier in [1, 2, 3, 4]:
        sub = tiered[tiered["tier"] == tier].copy()
        if sub.empty:
            continue
        lines += [
            "",
            f"## Tier {tier}",
            "",
            f"- Definition: {TIER_DEFINITIONS[tier]['tier_name']}",
            f"- Validation goal: {TIER_DEFINITIONS[tier]['validation_goal']}",
            "",
            "| Rank | Drug | Score | Confidence | Note |",
            "| --- | --- | ---: | --- | --- |",
        ]
        for _, row in sub.sort_values("rank").iterrows():
            lines.append(
                f"| {int(row['rank'])} | {row['drug_name']} | {row['drug_level_score']:.4f} | "
                f"{row['confidence_grade']} | {row['tier_rationale']} |"
            )

    lines += [
        "",
        "## Classification Notes",
        "",
        "- Tier 1: 실제 유방암 치료제로 사용되거나 NCI breast cancer approved list에 포함된 약물",
        "- Tier 2: 유방암 임상연구 또는 적응증 확장 시도가 확인된 치료제/치료 후보",
        "- Tier 3: 치료제이지만 현재 기준 유방암 직접 사용 근거가 제한적인 약물",
        "- Tier 4: 승인 치료제로 보기 어려운 화합물, 보충제, 실험용 inhibitor, 또는 미지 후보",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    top30 = pd.read_csv(TOP30_CSV)
    validation = pd.read_csv(VALIDATION_CSV)

    tiers = top30["drug_name"].map(classify_drug)
    top30["tier"] = [t[0] for t in tiers]
    top30["tier_rationale"] = [t[1] for t in tiers]
    top30["tier_name"] = top30["tier"].map(lambda t: TIER_DEFINITIONS[t]["tier_name"])
    top30["tier_validation_goal"] = top30["tier"].map(lambda t: TIER_DEFINITIONS[t]["validation_goal"])
    top30["classification_status"] = "tier_definition_revised_20260428"

    ordered_cols = [
        "rank",
        "tier",
        "tier_name",
        "tier_validation_goal",
        "canonical_drug_id",
        "drug_name",
        "selected_config",
        "ensemble_method",
        "drug_level_score",
        "prediction_std_mean",
        "confidence_grade",
        "n_samples",
        "tier_rationale",
        "classification_status",
        "canonical_smiles",
    ]
    tiered = top30[ordered_cols].copy()

    tiered_csv = OUT_DIR / "brca_directive_top30_tiered_candidates.csv"
    tiered_json = OUT_DIR / "brca_directive_top30_tiered_candidates.json"
    summary_md = OUT_DIR / "brca_current_status_20260428.md"

    tiered.to_csv(tiered_csv, index=False)
    tiered.to_json(tiered_json, orient="records", indent=2, force_ascii=False)
    summary_md.write_text(build_summary_md(tiered, validation), encoding="utf-8")

    print(f"wrote: {tiered_csv}")
    print(f"wrote: {tiered_json}")
    print(f"wrote: {summary_md}")


if __name__ == "__main__":
    main()
