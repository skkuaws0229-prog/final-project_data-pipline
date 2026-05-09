#!/usr/bin/env python3
"""
Feature Selection for drug repurposing pipeline.

Lung pipeline의 FS 로직을 100% 재현한 스크립트.
(Lung `feature_selection_log.json`, `feature_categories.json`, `final_columns.json` 기반)

입력:
    - features.parquet (Nextflow FE 산출물)
    - pair_features_newfe_v2.parquet (Nextflow FE 산출물)

출력:
    - features_slim.parquet: FS 완료된 최종 features
    - feature_selection_log.json: 단계별 제거 수 기록
    - feature_categories.json: 카테고리별 컬럼 목록
    - final_columns.json: 최종 선택된 컬럼 목록
    - selection_log_init.json: 초기 분류 스냅샷 (Lung 호환)
    - merged_temp.parquet: merge 중간 산출물
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ==============================================================================
# Categorization
# ==============================================================================

METADATA_COLS = ['sample_id', 'canonical_drug_id']

PREFIX_RULES = [
    ('gene', 'sample__crispr__'),
    ('morgan', 'drug_morgan_'),
    ('lincs', 'lincs_'),
    ('target', 'target_'),
    ('drug_desc', 'drug_desc_'),
]

DRUG_OTHER_EXACT = {'drug_has_valid_smiles'}


def categorize_columns(columns):
    cats = {
        'keep_cols': [],
        'gene_cols': [],
        'morgan_cols': [],
        'lincs_cols': [],
        'target_cols': [],
        'pathway_cols': [],
        'drug_desc_cols': [],
        'other_feature_cols': [],
    }

    for c in columns:
        if c in METADATA_COLS:
            cats['keep_cols'].append(c)
            continue

        matched = False
        for cat, prefix in PREFIX_RULES:
            if c.startswith(prefix):
                cats[f'{cat}_cols'].append(c)
                matched = True
                break

        if matched:
            continue

        if c.startswith('drug__') or c in DRUG_OTHER_EXACT:
            cats['other_feature_cols'].append(c)
            continue

        cats['other_feature_cols'].append(c)

    return cats


# ==============================================================================
# Filters
# ==============================================================================

def filter_low_variance(df, cols, threshold=0.01):
    if not cols:
        return [], 0

    sub = df[cols]
    variances = sub.var(axis=0, skipna=True)
    kept = variances[variances > threshold].index.tolist()
    removed = len(cols) - len(kept)
    return kept, removed


def filter_high_correlation(df, cols, threshold=0.95):
    if not cols or len(cols) < 2:
        return cols, 0

    sub = df[cols]
    corr = sub.corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    to_drop = [c for c in upper.columns if any(upper[c] > threshold)]
    kept = [c for c in cols if c not in to_drop]
    removed = len(to_drop)
    return kept, removed


# ==============================================================================
# Main pipeline
# ==============================================================================

def run_feature_selection(
    features_path,
    pair_features_path,
    output_dir,
    low_var_threshold=0.01,
    high_corr_threshold=0.95,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f'[1/6] Loading data...')
    features = pd.read_parquet(features_path)
    pair_features = pd.read_parquet(pair_features_path)
    print(f'  features.parquet      : {features.shape}')
    print(f'  pair_features.parquet : {pair_features.shape}')

    print(f'\n[2/6] Merging on {METADATA_COLS}...')
    merged = features.merge(
        pair_features,
        on=METADATA_COLS,
        how='inner',
    )
    print(f'  merged shape: {merged.shape}')

    merged_path = output_dir / 'merged_temp.parquet'
    merged.to_parquet(merged_path, index=False)
    print(f'  saved: {merged_path}')

    print(f'\n[3/6] Categorizing columns...')
    cats = categorize_columns(merged.columns)
    for k, v in cats.items():
        print(f'  {k}: {len(v)}')

    cat_output = {
        'gene_cols': cats['gene_cols'],
        'morgan_cols': cats['morgan_cols'],
        'lincs_cols': cats['lincs_cols'],
        'target_cols': cats['target_cols'],
        'pathway_cols': cats['pathway_cols'],
        'drug_desc_cols': cats['drug_desc_cols'],
        'keep_cols': cats['keep_cols'],
        'other_feature_cols': cats['other_feature_cols'],
    }
    with open(output_dir / 'feature_categories.json', 'w') as f:
        json.dump(cat_output, f, indent=2)

    init_log = {
        'initial_shape': list(merged.shape),
        'initial_counts': {
            'gene': len(cats['gene_cols']),
            'morgan': 0,
            'lincs': len(cats['lincs_cols']),
            'target': len(cats['target_cols']),
            'pathway': len(cats['pathway_cols']),
            'drug_desc': len(cats['drug_desc_cols']),
            'other': len(cats['morgan_cols']) + len(cats['other_feature_cols']),
        },
        'steps': [],
    }
    with open(output_dir / 'selection_log_init.json', 'w') as f:
        json.dump(init_log, f, indent=2)

    print(f'\n[4/6] Feature Selection...')
    log_steps = []

    gene_cols = cats['gene_cols']
    gene_after_lv, gene_lv_removed = filter_low_variance(
        merged, gene_cols, threshold=low_var_threshold
    )
    log_steps.append({
        'step': 'gene_low_variance',
        'threshold': low_var_threshold,
        'before': len(gene_cols),
        'removed': gene_lv_removed,
        'after': len(gene_after_lv),
    })
    print(f'  gene low_variance({low_var_threshold}): '
          f'{len(gene_cols)} -> {len(gene_after_lv)} (-{gene_lv_removed})')

    gene_final, gene_hc_removed = filter_high_correlation(
        merged, gene_after_lv, threshold=high_corr_threshold
    )
    log_steps.append({
        'step': 'gene_high_correlation',
        'threshold': high_corr_threshold,
        'before': len(gene_after_lv),
        'removed': gene_hc_removed,
        'after': len(gene_final),
    })
    print(f'  gene high_correlation({high_corr_threshold}): '
          f'{len(gene_after_lv)} -> {len(gene_final)} (-{gene_hc_removed})')

    morgan_cols = cats['morgan_cols']
    morgan_after_lv, morgan_lv_removed = filter_low_variance(
        merged, morgan_cols, threshold=low_var_threshold
    )
    log_steps.append({
        'step': 'morgan_low_variance',
        'threshold': low_var_threshold,
        'before': len(morgan_cols),
        'removed': morgan_lv_removed,
        'after': len(morgan_after_lv),
    })
    print(f'  morgan low_variance({low_var_threshold}): '
          f'{len(morgan_cols)} -> {len(morgan_after_lv)} (-{morgan_lv_removed})')

    morgan_final, morgan_hc_removed = filter_high_correlation(
        merged, morgan_after_lv, threshold=high_corr_threshold
    )
    log_steps.append({
        'step': 'morgan_high_correlation',
        'threshold': high_corr_threshold,
        'before': len(morgan_after_lv),
        'removed': morgan_hc_removed,
        'after': len(morgan_final),
    })
    print(f'  morgan high_correlation({high_corr_threshold}): '
          f'{len(morgan_after_lv)} -> {len(morgan_final)} (-{morgan_hc_removed})')

    other_keep = (
        cats['lincs_cols']
        + cats['target_cols']
        + cats['pathway_cols']
        + cats['drug_desc_cols']
        + cats['other_feature_cols']
    )
    log_steps.append({
        'step': 'other_keep_all',
        'kept_categories': ['lincs', 'target', 'pathway', 'drug_desc', 'drug_other'],
        'before': len(other_keep),
        'removed': 0,
        'after': len(other_keep),
    })
    print(f'  lincs/target/pathway/drug_desc/drug_other keep_all: {len(other_keep)}')

    print(f'\n[5/6] Assembling final features_slim...')
    final_cols = cats['keep_cols'] + gene_final + morgan_final + other_keep
    features_slim = merged[final_cols].copy()
    print(f'  final shape: {features_slim.shape}')

    features_slim_path = output_dir / 'features_slim.parquet'
    features_slim.to_parquet(features_slim_path, index=False)
    print(f'  saved: {features_slim_path}')

    print(f'\n[6/6] Saving logs...')

    fs_log = {
        'initial_shape': list(merged.shape),
        'initial_counts': {
            'gene': len(cats['gene_cols']),
            'morgan': len(cats['morgan_cols']),
            'lincs': len(cats['lincs_cols']),
            'target': len(cats['target_cols']),
            'pathway': len(cats['pathway_cols']),
            'drug_desc': len(cats['drug_desc_cols']),
            'drug_other': len(cats['other_feature_cols']),
        },
        'steps': log_steps,
        'final_counts': {
            'gene': len(gene_final),
            'morgan': len(morgan_final),
            'other': len(other_keep),
            'total_features': len(gene_final) + len(morgan_final) + len(other_keep),
        },
        'thresholds': {
            'low_variance': low_var_threshold,
            'high_correlation': high_corr_threshold,
        },
    }
    with open(output_dir / 'feature_selection_log.json', 'w') as f:
        json.dump(fs_log, f, indent=2)

    final_out = {
        'metadata': cats['keep_cols'],
        'gene_final': gene_final,
        'morgan_final': morgan_final,
        'other_keep': other_keep,
    }
    with open(output_dir / 'final_columns.json', 'w') as f:
        json.dump(final_out, f, indent=2)

    print(f'\n=== Summary ===')
    print(f'Input  : merged {merged.shape}')
    print(f'Output : features_slim {features_slim.shape}')
    print(f'Files  :')
    print(f'  - features_slim.parquet')
    print(f'  - feature_selection_log.json')
    print(f'  - feature_categories.json')
    print(f'  - selection_log_init.json')
    print(f'  - final_columns.json')
    print(f'  - merged_temp.parquet')


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--features', required=True)
    p.add_argument('--pair-features', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--low-var-threshold', type=float, default=0.01)
    p.add_argument('--high-corr-threshold', type=float, default=0.95)
    return p.parse_args()


def main():
    args = parse_args()
    run_feature_selection(
        features_path=args.features,
        pair_features_path=args.pair_features,
        output_dir=args.output_dir,
        low_var_threshold=args.low_var_threshold,
        high_corr_threshold=args.high_corr_threshold,
    )


if __name__ == '__main__':
    main()
