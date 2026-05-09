#!/usr/bin/env python3
"""
aggregate_lincs_to_drug_level.py
─────────────────────────────────
Aggregate LINCS signature-level data to drug-level for build_pair_features.

Input:
  - lincs_lung.parquet (25,265 signatures × 12,336 cols)
    Columns: sig_id, pert_id, pert_iname, pert_dose, ... + 12,328 genes

  - drug_features.parquet (295 drugs × 5 cols)
    Columns: canonical_drug_id, smiles, canonical_smiles_raw, drug_name_norm, has_smiles

Output:
  - lincs_lung_drug_level.parquet (N drugs × 12,329 cols)
    Columns: canonical_drug_id + 12,328 gene expression values (mean per drug)

Process:
  1. Load both files
  2. Normalize pert_iname to match drug_name_norm
  3. Match LINCS drugs to GDSC canonical_drug_id
  4. Group by canonical_drug_id and compute mean gene expression
  5. Save drug-level parquet

Author: Claude Code
Date: 2026-04-17
"""

import argparse
import json
import pandas as pd
import numpy as np
from pathlib import Path
import sys


def normalize_drug_name(name: str) -> str:
    """Aggressive normalization: alphanumeric only (matches Stage 1 analysis)."""
    if pd.isna(name):
        return ""
    return "".join(ch for ch in str(name).lower().strip() if ch.isalnum())


def parse_args():
    p = argparse.ArgumentParser(description="Aggregate LINCS signatures to drug level")
    p.add_argument("--lincs-sig-uri", required=True,
                   help="LINCS signature-level parquet (lincs_lung.parquet)")
    p.add_argument("--drug-features-uri", required=True,
                   help="Drug features parquet with canonical_drug_id")
    p.add_argument("--output-uri", required=True,
                   help="Output drug-level LINCS parquet")
    p.add_argument("--report-uri", default=None,
                   help="Optional JSON report output")
    return p.parse_args()


def main():
    args = parse_args()

    print("=" * 70)
    print("LINCS Signature → Drug Level Aggregation")
    print("=" * 70)

    # ─────────────────────────────────────────────────────────────
    # STEP 1: Load LINCS signatures
    # ─────────────────────────────────────────────────────────────
    print("\n[1/5] Loading LINCS signatures ...")
    lincs_df = pd.read_parquet(args.lincs_sig_uri)
    print(f"  Shape: {lincs_df.shape}")
    print(f"  Columns (first 20): {lincs_df.columns.tolist()[:20]}")

    # Identify metadata and gene columns
    meta_cols = ['sig_id', 'pert_id', 'pert_iname', 'pert_dose', 'pert_dose_unit',
                 'pert_time', 'pert_time_unit', 'cell_id']
    meta_existing = [c for c in meta_cols if c in lincs_df.columns]
    gene_cols = [c for c in lincs_df.columns if c not in meta_existing]

    print(f"  Metadata columns: {len(meta_existing)}")
    print(f"  Gene columns: {len(gene_cols)}")
    print(f"  Unique pert_iname: {lincs_df['pert_iname'].nunique()}")

    # ─────────────────────────────────────────────────────────────
    # STEP 2: Load drug features (GDSC canonical_drug_id mapping)
    # ─────────────────────────────────────────────────────────────
    print("\n[2/5] Loading drug features ...")
    drug_df = pd.read_parquet(args.drug_features_uri)
    print(f"  Shape: {drug_df.shape}")
    print(f"  Columns: {drug_df.columns.tolist()}")
    print(f"  Unique canonical_drug_id: {drug_df['canonical_drug_id'].nunique()}")

    # ─────────────────────────────────────────────────────────────
    # STEP 3: Match LINCS pert_iname to GDSC drug_name_norm
    # ─────────────────────────────────────────────────────────────
    print("\n[3/5] Matching LINCS drugs to GDSC ...")

    # Normalize both sides
    lincs_df['pert_iname_norm'] = lincs_df['pert_iname'].apply(normalize_drug_name)
    drug_df['drug_name_norm_clean'] = drug_df['drug_name_norm'].apply(normalize_drug_name)

    # Create mapping: pert_iname_norm → canonical_drug_id
    drug_map = drug_df.set_index('drug_name_norm_clean')['canonical_drug_id'].to_dict()

    # Map LINCS to canonical_drug_id
    lincs_df['canonical_drug_id'] = lincs_df['pert_iname_norm'].map(drug_map)

    # Filter to matched drugs only
    matched_df = lincs_df[lincs_df['canonical_drug_id'].notna()].copy()

    print(f"  Total LINCS signatures: {len(lincs_df)}")
    print(f"  Matched signatures: {len(matched_df)} ({len(matched_df)/len(lincs_df)*100:.1f}%)")
    print(f"  Unique matched drugs: {matched_df['canonical_drug_id'].nunique()}")
    print(f"  GDSC total drugs: {drug_df['canonical_drug_id'].nunique()}")
    print(f"  Match rate: {matched_df['canonical_drug_id'].nunique()}/{drug_df['canonical_drug_id'].nunique()} "
          f"({matched_df['canonical_drug_id'].nunique()/drug_df['canonical_drug_id'].nunique()*100:.1f}%)")

    if len(matched_df) == 0:
        print("\n❌ ERROR: No drugs matched! Check drug name normalization.")
        sys.exit(1)

    # Show matched drug examples
    print("\n  Matched drugs (first 10):")
    matched_drugs = matched_df.groupby('canonical_drug_id')['pert_iname'].first().head(10)
    for drug_id, name in matched_drugs.items():
        count = (matched_df['canonical_drug_id'] == drug_id).sum()
        print(f"    {drug_id}: {name} ({count} signatures)")

    # ─────────────────────────────────────────────────────────────
    # STEP 4: Aggregate to drug level (mean per drug)
    # ─────────────────────────────────────────────────────────────
    print("\n[4/5] Aggregating to drug level (mean) ...")

    # Select only canonical_drug_id + gene columns
    agg_df = matched_df[['canonical_drug_id'] + gene_cols].copy()

    # Ensure gene columns are numeric
    for col in gene_cols:
        agg_df[col] = pd.to_numeric(agg_df[col], errors='coerce')

    # Group by canonical_drug_id and compute mean
    print(f"  Computing mean across {len(gene_cols)} genes for {agg_df['canonical_drug_id'].nunique()} drugs ...")
    drug_level = agg_df.groupby('canonical_drug_id', as_index=False).mean()

    print(f"  Output shape: {drug_level.shape}")
    print(f"  Drugs: {len(drug_level)}")
    print(f"  Genes: {len(gene_cols)}")

    # Verify no missing values in aggregated data
    null_count = drug_level[gene_cols].isnull().sum().sum()
    print(f"  Missing values: {null_count}")

    if null_count > 0:
        print("  ⚠️ Filling missing values with 0.0 ...")
        drug_level[gene_cols] = drug_level[gene_cols].fillna(0.0)

    # ─────────────────────────────────────────────────────────────
    # STEP 5: Save output
    # ─────────────────────────────────────────────────────────────
    print(f"\n[5/5] Saving to {args.output_uri} ...")

    # Ensure output directory exists
    output_path = Path(args.output_uri)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save parquet
    drug_level.to_parquet(args.output_uri, index=False)
    file_size = output_path.stat().st_size / 1e6
    print(f"  ✓ Saved: {file_size:.2f} MB")

    # ─────────────────────────────────────────────────────────────
    # Generate report
    # ─────────────────────────────────────────────────────────────
    report = {
        "input_lincs_signatures": len(lincs_df),
        "input_unique_pert_iname": int(lincs_df['pert_iname'].nunique()),
        "gdsc_total_drugs": int(drug_df['canonical_drug_id'].nunique()),
        "matched_signatures": len(matched_df),
        "matched_unique_drugs": int(matched_df['canonical_drug_id'].nunique()),
        "match_rate_percent": round(matched_df['canonical_drug_id'].nunique() /
                                    drug_df['canonical_drug_id'].nunique() * 100, 2),
        "output_drugs": len(drug_level),
        "output_genes": len(gene_cols),
        "output_shape": list(drug_level.shape),
        "missing_values": int(null_count),
        "output_file_mb": round(file_size, 2),
        "matched_drug_examples": {
            str(drug_id): {
                "name": str(matched_df[matched_df['canonical_drug_id']==drug_id]['pert_iname'].iloc[0]),
                "n_signatures": int((matched_df['canonical_drug_id']==drug_id).sum())
            }
            for drug_id in matched_df['canonical_drug_id'].unique()[:10]
        }
    }

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Input signatures:    {report['input_lincs_signatures']:,}")
    print(f"  Input unique drugs:  {report['input_unique_pert_iname']:,}")
    print(f"  GDSC total drugs:    {report['gdsc_total_drugs']}")
    print(f"  Matched signatures:  {report['matched_signatures']:,}")
    print(f"  Matched drugs:       {report['matched_unique_drugs']}")
    print(f"  Match rate:          {report['match_rate_percent']:.1f}%")
    print(f"  Output shape:        {report['output_drugs']} drugs × {report['output_genes']} genes")
    print(f"  Output file:         {report['output_file_mb']:.2f} MB")
    print("=" * 70)

    # Save report
    if args.report_uri:
        report_path = Path(args.report_uri)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(args.report_uri, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n✓ Report saved: {args.report_uri}")

    print("\n✓ Done!")


if __name__ == "__main__":
    main()
