#!/usr/bin/env python3
"""
Step 7.0: Remove Duplicate Drugs from Final Ranking
- Remove Docetaxel duplicate (keep highest score)
- Adjust ranking to maintain Top 10
"""

import pandas as pd
import json
from pathlib import Path

def remove_duplicates():
    """Remove duplicate drugs from final ranking."""

    print("="*80)
    print("STEP 7.0: REMOVE DUPLICATE DRUGS")
    print("="*80)

    # Load final ranking
    df = pd.read_csv('results/lung_final_drug_ranking_with_scores.csv')

    print(f"\nOriginal: {len(df)} drugs")
    print(f"\nDuplicate check (by drug_name):")
    duplicates = df[df.duplicated(subset=['drug_name'], keep=False)]
    if len(duplicates) > 0:
        dup_sorted = duplicates.sort_values('drug_name')
        print(dup_sorted[['final_rank', 'canonical_drug_id', 'drug_name',
                         'multi_objective_score', 'confidence']].to_string(index=False))

    # Remove duplicates by drug_name (keep highest multi_objective_score)
    df_sorted = df.sort_values(['drug_name', 'multi_objective_score'],
                                ascending=[True, False])
    df_dedup = df_sorted.drop_duplicates(subset=['drug_name'], keep='first')

    # Re-rank
    df_dedup = df_dedup.sort_values('multi_objective_score', ascending=False).reset_index(drop=True)
    df_dedup['final_rank'] = range(1, len(df_dedup) + 1)

    print(f"\nAfter deduplication: {len(df_dedup)} drugs")
    print(f"Removed: {len(df) - len(df_dedup)} duplicates")

    # Save deduplicated ranking
    df_dedup.to_csv('results/lung_final_drug_ranking_dedup.csv', index=False)
    print(f"\n✓ Saved: results/lung_final_drug_ranking_dedup.csv")

    # Print new Top 10
    print(f"\n{'='*80}")
    print("NEW TOP 10 (After Deduplication)")
    print(f"{'='*80}")

    top10 = df_dedup.head(10)
    display_cols = ['final_rank', 'drug_name', 'multi_objective_score', 'confidence',
                    'n_clinical_trials', 'rank_2b', 'rank_2c']
    display_cols = [col for col in display_cols if col in top10.columns]
    print(top10[display_cols].to_string(index=False))

    # Update summary
    summary = {
        'total_drugs': len(df_dedup),
        'duplicates_removed': int(len(df) - len(df_dedup)),
        'validation_sources': 4,
        'avg_confidence': float(df_dedup['confidence'].mean()),
        'avg_validation_score': float(df_dedup['validation_score'].mean()),
        'high_confidence_drugs': int(len(df_dedup[df_dedup['confidence'] >= 75])),
        'top_10_drugs': df_dedup.head(10)[['drug_name', 'multi_objective_score', 'confidence']].to_dict('records')
    }

    with open('results/lung_final_ranking_dedup_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n✓ Saved: results/lung_final_ranking_dedup_summary.json")

    return df_dedup, summary

if __name__ == '__main__':
    df_dedup, summary = remove_duplicates()

    print(f"\n{'='*80}")
    print("DEDUPLICATION COMPLETE")
    print(f"{'='*80}")
