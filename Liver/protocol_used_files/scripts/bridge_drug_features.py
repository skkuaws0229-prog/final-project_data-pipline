#!/usr/bin/env python3
"""
Bridge drug_catalog -> drug_features (team4 schema).

Converts the output of build_drug_catalog.py (6 cols) to the team4
drug_features.parquet schema (5 cols), filtered by labels drug set.

Process:
  1. Load catalog (from build_drug_catalog.py output)
  2. Load labels to get unique drug IDs
  3. Filter catalog: keep only drugs present in labels
  4. Transform to team4 schema (5 columns)
  5. Validate: labels drugs ⊆ catalog drugs (no missing)

Output schema (matches Lung drug_features.parquet):
  - canonical_drug_id    : str
  - canonical_smiles     : str (or NaN if has_smiles=0)
  - canonical_smiles_raw : str (copy of canonical_smiles, team4 convention)
  - drug_name_norm       : str
  - has_smiles           : int (0 or 1)
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog-uri', required=True, type=Path,
                   help='Path to drug_catalog_colon.parquet')
    p.add_argument('--labels-uri', required=True, type=Path,
                   help='Path to labels.parquet')
    p.add_argument('--output-uri', required=True, type=Path,
                   help='Output: drug_features.parquet (team4 schema)')
    p.add_argument('--report-uri', required=True, type=Path,
                   help='Output: bridge report JSON')
    return p.parse_args()


def main():
    args = parse_args()

    log("=" * 70)
    log("Step 2-5-B: Bridge drug_catalog -> drug_features")
    log("=" * 70)

    # --- Load ---
    log("Loading catalog...")
    catalog = pd.read_parquet(args.catalog_uri)
    log(f"  Catalog: {catalog.shape}")
    log(f"  Columns: {catalog.columns.tolist()}")

    log("Loading labels...")
    labels = pd.read_parquet(args.labels_uri)
    log(f"  Labels: {labels.shape}")

    # --- Extract labels drug set ---
    labels_drugs = set(labels['canonical_drug_id'].astype(str))
    catalog_drugs = set(catalog['DRUG_ID'].astype(str))

    log("")
    log("Drug set analysis:")
    log(f"  Labels unique drugs:  {len(labels_drugs)}")
    log(f"  Catalog drugs:        {len(catalog_drugs)}")
    log(f"  Intersection:         {len(labels_drugs & catalog_drugs)}")
    log(f"  Labels only (missing in catalog): {len(labels_drugs - catalog_drugs)}")
    log(f"  Catalog only:         {len(catalog_drugs - labels_drugs)}")

    # --- Validate: labels ⊆ catalog ---
    missing = labels_drugs - catalog_drugs
    if missing:
        log("")
        log(f"✗ ERROR: {len(missing)} labels drugs missing from catalog")
        log(f"Missing drug IDs (first 20): {sorted(missing)[:20]}")
        sys.exit(1)

    log("")
    log("✓ All labels drugs present in catalog")

    # --- Filter catalog ---
    log("")
    log("Filtering catalog to labels drug set...")
    catalog_str = catalog.copy()
    catalog_str['DRUG_ID_str'] = catalog_str['DRUG_ID'].astype(str)
    filtered = catalog_str[catalog_str['DRUG_ID_str'].isin(labels_drugs)].copy()
    log(f"  Filtered rows: {len(filtered)}")

    # --- Transform to team4 schema ---
    log("")
    log("Transforming to team4 schema...")
    features = pd.DataFrame({
        'canonical_drug_id': filtered['DRUG_ID'].astype(str),
        'canonical_smiles': filtered['canonical_smiles'],
        'canonical_smiles_raw': filtered['canonical_smiles'],  # team4 convention
        'drug_name_norm': filtered['drug_name_norm'],
        'has_smiles': filtered['has_smiles'].astype(int)
    })

    # Sort for reproducibility
    features = features.sort_values('canonical_drug_id').reset_index(drop=True)

    # --- Validation ---
    log("")
    log("Validation:")
    features_drugs = set(features['canonical_drug_id'])

    if features_drugs != labels_drugs:
        log(f"  ✗ Drug set mismatch: features({len(features_drugs)}) vs labels({len(labels_drugs)})")
        sys.exit(1)

    if features['canonical_drug_id'].duplicated().any():
        log("  ✗ Duplicate canonical_drug_id")
        sys.exit(1)

    log(f"  ✓ Drug set exact match: {len(features)}")
    log("  ✓ No duplicates")

    # --- Stats ---
    has_smiles_1 = int((features['has_smiles'] == 1).sum())
    has_smiles_0 = int((features['has_smiles'] == 0).sum())
    smiles_non_null = int(features['canonical_smiles'].notna().sum())

    log("")
    log("Statistics:")
    log(f"  Total:           {len(features)}")
    log(f"  has_smiles=1:    {has_smiles_1} ({has_smiles_1/len(features)*100:.2f}%)")
    log(f"  has_smiles=0:    {has_smiles_0} ({has_smiles_0/len(features)*100:.2f}%)")
    log(f"  SMILES non-null: {smiles_non_null}")

    # Consistency check: has_smiles=1 should match canonical_smiles non-null
    inconsistent = ((features['has_smiles'] == 1) & features['canonical_smiles'].isna()).sum()
    if inconsistent > 0:
        log(f"  ⚠ Inconsistency: {inconsistent} rows have has_smiles=1 but canonical_smiles=NaN")

    # --- Save ---
    args.output_uri.parent.mkdir(parents=True, exist_ok=True)
    args.report_uri.parent.mkdir(parents=True, exist_ok=True)

    features.to_parquet(args.output_uri, index=False)
    log("")
    log(f"Saved: {args.output_uri}")
    log(f"  Shape: {features.shape}")
    log(f"  Columns: {features.columns.tolist()}")

    # --- Report ---
    import json
    report = {
        'timestamp': datetime.now().isoformat(),
        'input': {
            'catalog_uri': str(args.catalog_uri),
            'catalog_shape': list(catalog.shape),
            'labels_uri': str(args.labels_uri),
            'labels_shape': list(labels.shape)
        },
        'drug_set_analysis': {
            'labels_drugs': len(labels_drugs),
            'catalog_drugs': len(catalog_drugs),
            'intersection': len(labels_drugs & catalog_drugs),
            'labels_only': len(labels_drugs - catalog_drugs),
            'catalog_only': len(catalog_drugs - labels_drugs)
        },
        'output': {
            'shape': list(features.shape),
            'columns': features.columns.tolist(),
            'has_smiles_1': has_smiles_1,
            'has_smiles_0': has_smiles_0,
            'smiles_coverage_pct': round(has_smiles_1 / len(features) * 100, 2)
        },
        'validation': {
            'drug_set_exact_match': True,
            'no_duplicates': True,
            'smiles_consistency_issues': int(inconsistent)
        },
        'comparison_with_lung': {
            'lung_shape': [295, 5],
            'lung_has_smiles_1': 243,
            'lung_has_smiles_0': 52,
            'lung_smiles_coverage_pct': 82.37
        }
    }

    with open(args.report_uri, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log(f"Report saved: {args.report_uri}")

    log("")
    log("=" * 70)
    log("Step 2-5-B completed successfully")
    log("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
