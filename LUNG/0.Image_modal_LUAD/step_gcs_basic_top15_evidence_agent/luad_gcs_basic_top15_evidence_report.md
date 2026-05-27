# LUAD GCS Basic Top15 Evidence Agent

Evidence agent started after confirming VM state. This first LUAD pass preserves existing protocol tiers and prepares a review package.

## VM Check

- VM status at evidence-agent start: TERMINATED

## Tier Counts

- Tier1: 3
- Tier2: 4
- Tier3: 3
- Tier4: 5

## Final Evidence Table

| Rank | Drug | Final tier | Evidence grade | Review status |
|---:|---|---|---|---|
| 1 | Docetaxel | Tier1 | current_lung_reference_or_standard_context | evidence_agent_scaffold_needs_human_clinical_signoff |
| 2 | Paclitaxel | Tier1 | current_lung_reference_or_standard_context | evidence_agent_scaffold_needs_human_clinical_signoff |
| 3 | Dactinomycin | Tier3 | repurposing_or_research_candidate | evidence_agent_scaffold_needs_human_clinical_signoff |
| 4 | Entinostat | Tier2 | approved_other_or_lung_research_context | evidence_agent_scaffold_needs_human_clinical_signoff |
| 5 | Venetoclax | Tier2 | approved_other_or_lung_research_context | evidence_agent_scaffold_needs_human_clinical_signoff |
| 6 | Tanespimycin | Tier2 | approved_other_or_lung_research_context | evidence_agent_scaffold_needs_human_clinical_signoff |
| 7 | Bortezomib | Tier2 | approved_other_or_lung_research_context | evidence_agent_scaffold_needs_human_clinical_signoff |
| 8 | Savolitinib | Tier1 | current_lung_reference_or_standard_context | evidence_agent_scaffold_needs_human_clinical_signoff |
| 9 | EPZ004777 | Tier4 | insufficient_or_low_priority_for_repositioning | evidence_agent_scaffold_needs_human_clinical_signoff |
| 10 | Methotrexate | Tier3 | repurposing_or_research_candidate | evidence_agent_scaffold_needs_human_clinical_signoff |
| 11 | Buparlisib | Tier4 | insufficient_or_low_priority_for_repositioning | evidence_agent_scaffold_needs_human_clinical_signoff |
| 12 | Teniposide | Tier3 | repurposing_or_research_candidate | evidence_agent_scaffold_needs_human_clinical_signoff |
| 13 | IOX2 | Tier4 | insufficient_or_low_priority_for_repositioning | evidence_agent_scaffold_needs_human_clinical_signoff |
| 14 | Pictilisib | Tier4 | insufficient_or_low_priority_for_repositioning | evidence_agent_scaffold_needs_human_clinical_signoff |
| 15 | BI-2536 | Tier4 | insufficient_or_low_priority_for_repositioning | evidence_agent_scaffold_needs_human_clinical_signoff |

## Next Evidence-Agent Upgrade

- Refresh current approval and clinical-trial evidence per drug.
- Split Tier2 and Tier3 candidates into repositioning-priority review queues.
- Require human clinical/scientific signoff before DB loading.
