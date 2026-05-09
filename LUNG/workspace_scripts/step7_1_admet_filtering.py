#!/usr/bin/env python3
"""
Step 7.1: ADMET Filtering
- Apply ADMET gate to Top 41 drugs
- Tier 1 Hard Fail: Immediate disqualification
- Tier 2 Soft Flag: Warning (clinical monitoring needed)
- Tier 3 Context: Information only (cancer drugs have special considerations)
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski

def load_gdsc_smiles():
    """Load SMILES from GDSC annotation."""

    print(f"\n{'─'*80}")
    print("LOADING GDSC DRUG ANNOTATIONS")
    print(f"{'─'*80}")

    annotation_file = 'curated_data/gdsc2/GDSC2_fitted_dose_response_24Jul22.xlsx'

    if not Path(annotation_file).exists():
        # Try alternative location
        annotation_file = 'curated_data/gdsc2/Screened_Compounds.xlsx'

    if Path(annotation_file).exists():
        df = pd.read_excel(annotation_file, sheet_name=0)
        print(f"✓ Loaded: {len(df)} compounds")

        # Get DRUG_ID and SMILES columns
        id_col = [c for c in df.columns if 'DRUG' in c.upper() and 'ID' in c.upper()][0]
        smiles_col = [c for c in df.columns if 'SMILES' in c.upper()][0]

        df_smiles = df[[id_col, smiles_col]].copy()
        df_smiles.columns = ['canonical_drug_id', 'SMILES']
        df_smiles = df_smiles.dropna(subset=['SMILES'])

        return df_smiles

    feature_file = Path('data/drug_features.parquet')
    if feature_file.exists():
        print(f"✓ Loading fallback SMILES from: {feature_file}")
        df = pd.read_parquet(feature_file)
        if {'canonical_drug_id', 'canonical_smiles'}.issubset(df.columns):
            df_smiles = df[['canonical_drug_id', 'canonical_smiles']].copy()
            df_smiles.columns = ['canonical_drug_id', 'SMILES']
            df_smiles = df_smiles.dropna(subset=['SMILES'])
            return df_smiles

    print(f"⚠ GDSC annotation not found, will use input ranking / ADMET matches only")
    return None

def calculate_lipinski_violations(smiles):
    """Calculate Lipinski Rule of Five violations."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        violations = 0
        mw = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        hbd = Descriptors.NumHDonors(mol)
        hba = Descriptors.NumHAcceptors(mol)

        if mw > 500:
            violations += 1
        if logp > 5:
            violations += 1
        if hbd > 5:
            violations += 1
        if hba > 10:
            violations += 1

        return violations
    except:
        return None

def check_pains_filters(smiles):
    """Check for PAINS (Pan Assay Interference Structures)."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        # Simple PAINS patterns (subset)
        pains_smarts = [
            '[OH]c1ccc([OH])cc1',  # Catechol
            'C1=CC=CC=C1N=NC1=CC=CC=C1',  # Azo
            '[#6]=[#6]-[#6]=[#6]-[#6]=[#6]',  # Polyene
        ]

        pains_count = 0
        for pattern in pains_smarts:
            patt = Chem.MolFromSmarts(pattern)
            if patt and mol.HasSubstructMatch(patt):
                pains_count += 1

        return pains_count
    except:
        return None

def load_admet_data():
    """Load ADMET prediction data."""

    print(f"\n{'─'*80}")
    print("LOADING ADMET DATA")
    print(f"{'─'*80}")

    admet_data = {}
    admet_base = Path('curated_data/admet/tdc_admet_group/admet_group')

    # Load key ADMET datasets
    admet_datasets = {
        'herg': 'herg',
        'dili': 'dili',
        'ames': 'ames',
        'cyp3a4': 'cyp3a4_veith',
        'bioavailability': 'bioavailability_ma',
        'half_life': 'half_life_obach'
    }

    for key, folder in admet_datasets.items():
        folder_path = admet_base / folder
        if folder_path.exists():
            # Load both train_val and test
            dfs = []
            for split in ['train_val.csv', 'test.csv']:
                file_path = folder_path / split
                if file_path.exists():
                    df = pd.read_csv(file_path)
                    dfs.append(df)

            if dfs:
                df_combined = pd.concat(dfs, ignore_index=True)
                # Standardize column names
                df_combined.columns = ['Drug_ID', 'Drug', 'Y']
                admet_data[key] = df_combined
                print(f"✓ {key}: {len(df_combined)} compounds")

    return admet_data

def match_drugs_to_admet(df_drugs, df_smiles, admet_data):
    """Match drugs to ADMET data by drug name."""

    print(f"\n{'─'*80}")
    print("MATCHING DRUGS TO ADMET DATA")
    print(f"{'─'*80}")

    df_merged = df_drugs.copy()
    df_merged['canonical_drug_id'] = df_merged['canonical_drug_id'].astype(str)

    if 'SMILES' not in df_merged.columns:
        if 'canonical_smiles' in df_merged.columns:
            df_merged['SMILES'] = df_merged['canonical_smiles']
        else:
            df_merged['SMILES'] = None

    # Merge with SMILES if available
    if df_smiles is not None:
        df_smiles = df_smiles.copy()
        df_smiles['canonical_drug_id'] = df_smiles['canonical_drug_id'].astype(str)
        df_merged = df_merged.merge(df_smiles, on='canonical_drug_id', how='left')
        if 'SMILES_x' in df_merged.columns and 'SMILES_y' in df_merged.columns:
            df_merged['SMILES'] = df_merged['SMILES_x'].fillna(df_merged['SMILES_y'])
            df_merged = df_merged.drop(columns=['SMILES_x', 'SMILES_y'])
        print(f"Drugs with SMILES: {df_merged['SMILES'].notna().sum()}/{len(df_merged)}")
    else:
        print(f"Drugs with SMILES from input ranking: {df_merged['SMILES'].notna().sum()}/{len(df_merged)}")

    # Match to ADMET data by drug name (Drug_ID in ADMET files)
    for key, df_admet in admet_data.items():
        matched = []
        smiles_matched = []

        for idx, row in df_merged.iterrows():
            drug_name = row.get('drug_name', '').strip()
            smiles = row.get('SMILES')

            value = None
            matched_smiles = None

            # Try exact name match (case-insensitive)
            if drug_name:
                # Convert Drug_ID to string and handle NaN
                drug_ids_lower = df_admet['Drug_ID'].astype(str).str.lower()
                match = df_admet[drug_ids_lower == drug_name.lower()]
                if len(match) > 0:
                    value = match.iloc[0]['Y']
                    matched_smiles = match.iloc[0]['Drug']  # SMILES

            # Try SMILES match if we have SMILES but no name match
            if value is None and pd.notna(smiles):
                match = df_admet[df_admet['Drug'] == smiles]
                if len(match) > 0:
                    value = match.iloc[0]['Y']
                    matched_smiles = smiles

            matched.append(value)
            smiles_matched.append(matched_smiles)

        df_merged[key] = matched
        df_merged[f'{key}_smiles'] = smiles_matched
        print(f"  {key}: {pd.Series(matched).notna().sum()} matches")

    # Use matched SMILES for structure calculations
    for key in admet_data.keys():
        smiles_col = f'{key}_smiles'
        if smiles_col in df_merged.columns:
            # Fill SMILES column with first matched SMILES
            df_merged['SMILES'] = df_merged['SMILES'].fillna(df_merged[smiles_col])

    return df_merged

def apply_admet_gate(df):
    """Apply ADMET filtering rules."""

    print(f"\n{'='*80}")
    print("APPLYING ADMET GATE")
    print(f"{'='*80}")

    df = df.copy()

    # Calculate Lipinski violations
    if 'SMILES' in df.columns:
        df['lipinski_violations'] = df['SMILES'].apply(
            lambda x: calculate_lipinski_violations(x) if pd.notna(x) else None
        )
        df['pains_count'] = df['SMILES'].apply(
            lambda x: check_pains_filters(x) if pd.notna(x) else None
        )

    # Tier 1: Hard Fail (Immediate Disqualification)
    df['tier1_herg_fail'] = False
    df['tier1_pains_fail'] = False
    df['tier1_lipinski_fail'] = False

    if 'herg' in df.columns:
        df['tier1_herg_fail'] = (df['herg'] > 0.7) & df['herg'].notna()
    if 'pains_count' in df.columns:
        df['tier1_pains_fail'] = (df['pains_count'] > 0) & df['pains_count'].notna()
    if 'lipinski_violations' in df.columns:
        df['tier1_lipinski_fail'] = (df['lipinski_violations'] > 2) & df['lipinski_violations'].notna()

    df['tier1_fail'] = df['tier1_herg_fail'] | df['tier1_pains_fail'] | df['tier1_lipinski_fail']

    # Tier 2: Soft Flag (Warning - Clinical Monitoring)
    df['tier2_herg_warn'] = False
    df['tier2_dili_warn'] = False
    df['tier2_ames_warn'] = False
    df['tier2_cyp3a4_warn'] = False

    if 'herg' in df.columns:
        df['tier2_herg_warn'] = ((df['herg'] >= 0.5) & (df['herg'] <= 0.7)) & df['herg'].notna()
    if 'dili' in df.columns:
        df['tier2_dili_warn'] = (df['dili'] == 1) & df['dili'].notna()
    if 'ames' in df.columns:
        df['tier2_ames_warn'] = (df['ames'] == 1) & df['ames'].notna()
    if 'cyp3a4' in df.columns:
        df['tier2_cyp3a4_warn'] = (df['cyp3a4'] == 1) & df['cyp3a4'].notna()

    df['tier2_warn_count'] = (
        df['tier2_herg_warn'].astype(int) +
        df['tier2_dili_warn'].astype(int) +
        df['tier2_ames_warn'].astype(int) +
        df['tier2_cyp3a4_warn'].astype(int)
    )

    # Tier 3: Context (Information Only - Cancer drug considerations)
    df['tier3_bioavailability'] = df.get('bioavailability', None)
    df['tier3_half_life'] = df.get('half_life', None)

    # Final ADMET Status
    df['admet_status'] = 'UNKNOWN'
    df.loc[~df['tier1_fail'] & (df['tier2_warn_count'] == 0), 'admet_status'] = 'PASS'
    df.loc[~df['tier1_fail'] & (df['tier2_warn_count'] > 0), 'admet_status'] = 'WARNING'
    df.loc[df['tier1_fail'], 'admet_status'] = 'FAIL'

    # Summary
    print(f"\nTier 1 Hard Fail:")
    print(f"  hERG > 0.7: {df['tier1_herg_fail'].sum()}")
    print(f"  PAINS > 0: {df['tier1_pains_fail'].sum()}")
    print(f"  Lipinski violations > 2: {df['tier1_lipinski_fail'].sum()}")
    print(f"  Total FAIL: {df['tier1_fail'].sum()}")

    print(f"\nTier 2 Soft Flag:")
    print(f"  hERG 0.5-0.7: {df['tier2_herg_warn'].sum()}")
    print(f"  DILI: {df['tier2_dili_warn'].sum()}")
    print(f"  Ames: {df['tier2_ames_warn'].sum()}")
    print(f"  CYP3A4: {df['tier2_cyp3a4_warn'].sum()}")

    print(f"\nFinal Status:")
    print(f"  PASS: {(df['admet_status'] == 'PASS').sum()}")
    print(f"  WARNING: {(df['admet_status'] == 'WARNING').sum()}")
    print(f"  FAIL: {(df['admet_status'] == 'FAIL').sum()}")
    print(f"  UNKNOWN: {(df['admet_status'] == 'UNKNOWN').sum()}")

    return df

def main():
    # Load deduplicated ranking
    df_drugs = pd.read_csv('results/lung_final_drug_ranking_dedup.csv')
    df_drugs['canonical_drug_id'] = df_drugs['canonical_drug_id'].astype(str)

    print(f"Total drugs: {len(df_drugs)}")

    # Load SMILES
    df_smiles = load_gdsc_smiles()

    # Load ADMET data
    admet_data = load_admet_data()

    # Match drugs to ADMET (works with or without SMILES)
    df_matched = match_drugs_to_admet(df_drugs, df_smiles, admet_data)

    # Apply ADMET gate
    df_final = apply_admet_gate(df_matched)

    # Save results
    df_final.to_csv('results/lung_drugs_with_admet.csv', index=False)
    print(f"\n✓ Saved: results/lung_drugs_with_admet.csv")

    # Print Top 20 with ADMET status
    print(f"\n{'='*80}")
    print("TOP 20 WITH ADMET STATUS")
    print(f"{'='*80}")

    top20 = df_final.head(20)
    display_cols = ['final_rank', 'drug_name', 'multi_objective_score', 'confidence',
                    'admet_status', 'tier2_warn_count', 'n_clinical_trials']
    print(top20[display_cols].to_string(index=False))

    # Save ADMET summary
    summary = {
        'total_drugs': len(df_final),
        'pass': int((df_final['admet_status'] == 'PASS').sum()),
        'warning': int((df_final['admet_status'] == 'WARNING').sum()),
        'fail': int((df_final['admet_status'] == 'FAIL').sum()),
        'unknown': int((df_final['admet_status'] == 'UNKNOWN').sum()),
        'tier1_hard_fails': {
            'herg': int(df_final['tier1_herg_fail'].sum()),
            'pains': int(df_final['tier1_pains_fail'].sum()),
            'lipinski': int(df_final['tier1_lipinski_fail'].sum())
        }
    }

    with open('results/lung_admet_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n✓ Saved: results/lung_admet_summary.json")

    print(f"\n{'='*80}")
    print("ADMET FILTERING COMPLETE")
    print(f"{'='*80}")

    return df_final

if __name__ == '__main__':
    df_final = main()
