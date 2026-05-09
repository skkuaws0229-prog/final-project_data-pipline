#!/usr/bin/env python3
"""
Step 7.2: Select Final Top 15 Drugs and Categorize
- Select ADMET PASS drugs
- Categorize by lung cancer usage status
- Generate final recommendations
"""

import pandas as pd
import json
from pathlib import Path

# Known lung cancer drug categories (based on FDA approval and clinical use)
LUNG_CANCER_CATEGORIES = {
    'current_use': [
        'Paclitaxel', 'Docetaxel', 'Vinorelbine', 'Topotecan',
        'Pemetrexed', 'Gemcitabine', 'Etoposide', 'Carboplatin',
        'Cisplatin', 'Erlotinib', 'Gefitinib', 'Osimertinib',
        'Alectinib', 'Crizotinib', 'Pembrolizumab', 'Nivolumab',
        'Atezolizumab', 'Durvalumab', 'Bevacizumab', 'Ramucirumab',
        'Necitumumab', 'Savolitinib'
    ],
    'research': [
        'Palbociclib', 'Temsirolimus', 'Entinostat', 'Romidepsin',
        'Cediranib', 'Alisertib', 'Rapamycin', 'Ulixertinib',
        'Tanespimycin', 'OTX015', 'Epirubicin', 'Vinblastine'
    ]
}

def categorize_drug(drug_name, n_trials):
    """Categorize drug by lung cancer usage status."""

    if drug_name in LUNG_CANCER_CATEGORIES['current_use']:
        return 'FDA_APPROVED_LUNG'
    elif drug_name in LUNG_CANCER_CATEGORIES['research']:
        return 'RESEARCH_PHASE'
    elif n_trials > 0:
        return 'CLINICAL_TRIAL'
    else:
        return 'REPURPOSING_CANDIDATE'

def select_top15(df):
    """Select top 15 ADMET PASS drugs."""

    print("="*80)
    print("STEP 7.2: SELECT FINAL TOP 15")
    print("="*80)

    # Filter ADMET PASS or WARNING (exclude FAIL)
    df_pass = df[df['admet_status'].isin(['PASS', 'WARNING'])].copy()

    print(f"\nADMET PASS/WARNING: {len(df_pass)}/{len(df)} drugs")

    # Select Top 15
    df_top15 = df_pass.head(15).copy()

    # Categorize
    df_top15['usage_category'] = df_top15.apply(
        lambda row: categorize_drug(row['drug_name'], row['n_clinical_trials']),
        axis=1
    )

    # Add recommendation priority
    category_priority = {
        'FDA_APPROVED_LUNG': 1,
        'RESEARCH_PHASE': 2,
        'CLINICAL_TRIAL': 3,
        'REPURPOSING_CANDIDATE': 4
    }

    df_top15['priority'] = df_top15['usage_category'].map(category_priority)
    df_top15 = df_top15.sort_values(['priority', 'final_rank']).reset_index(drop=True)
    df_top15['recommendation_rank'] = range(1, len(df_top15) + 1)

    return df_top15, df_pass

def print_final_recommendations(df_top15):
    """Print final recommendations."""

    print(f"\n{'='*80}")
    print("FINAL TOP 15 DRUG RECOMMENDATIONS FOR LUNG CANCER")
    print(f"{'='*80}")

    for category in ['FDA_APPROVED_LUNG', 'RESEARCH_PHASE', 'CLINICAL_TRIAL', 'REPURPOSING_CANDIDATE']:
        df_cat = df_top15[df_top15['usage_category'] == category]
        if len(df_cat) > 0:
            print(f"\n{category} ({len(df_cat)} drugs):")
            print("─" * 80)

            display_cols = ['recommendation_rank', 'drug_name', 'multi_objective_score',
                          'confidence', 'n_clinical_trials', 'admet_status']

            for idx, row in df_cat.iterrows():
                print(f"  #{row['recommendation_rank']:2d}. {row['drug_name']:20s} "
                      f"(Score: {row['multi_objective_score']:.3f}, "
                      f"Conf: {row['confidence']:3.0f}%, "
                      f"Trials: {row['n_clinical_trials']:3.0f}, "
                      f"ADMET: {row['admet_status']})")

    # Summary by category
    print(f"\n{'='*80}")
    print("CATEGORY SUMMARY")
    print(f"{'='*80}")

    for category in ['FDA_APPROVED_LUNG', 'RESEARCH_PHASE', 'CLINICAL_TRIAL', 'REPURPOSING_CANDIDATE']:
        count = len(df_top15[df_top15['usage_category'] == category])
        print(f"  {category:30s}: {count:2d} drugs")

def main():
    # Load ADMET filtered data
    df = pd.read_csv('results/lung_drugs_with_admet.csv')

    print(f"Total drugs: {len(df)}")
    print(f"ADMET status distribution:")
    print(df['admet_status'].value_counts())

    # Select Top 15
    df_top15, df_pass = select_top15(df)

    # Save Top 15
    df_top15.to_csv('results/lung_final_top15.csv', index=False)
    print(f"\n✓ Saved: results/lung_final_top15.csv")

    # Save all PASS drugs
    df_pass.to_csv('results/lung_all_admet_pass.csv', index=False)
    print(f"✓ Saved: results/lung_all_admet_pass.csv")

    # Print recommendations
    print_final_recommendations(df_top15)

    # Save summary
    category_counts = df_top15['usage_category'].value_counts().to_dict()

    summary = {
        'total_candidates': len(df),
        'admet_pass': len(df_pass),
        'top_15_selected': len(df_top15),
        'category_distribution': category_counts,
        'top_5_recommendations': df_top15.head(5)[
            ['recommendation_rank', 'drug_name', 'usage_category',
             'multi_objective_score', 'confidence', 'n_clinical_trials']
        ].to_dict('records')
    }

    with open('results/lung_final_top15_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n✓ Saved: results/lung_final_top15_summary.json")

    print(f"\n{'='*80}")
    print("TOP 15 SELECTION COMPLETE")
    print(f"{'='*80}")

    return df_top15, summary

if __name__ == '__main__':
    df_top15, summary = main()
