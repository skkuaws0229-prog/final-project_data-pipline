# COAD GCS Basic Top15 Evidence Agent

Evidence agent started after confirming the GCP VM was terminated, so no n2-standard-16 compute cost should continue from this workflow.
The table below verifies the provisional im4c tiers against approval, CRC clinical evidence, and CRC preclinical evidence.

## VM Check

- VM status at evidence-agent start: TERMINATED

## Tier Counts

- Tier1: 1
- Tier2: 2
- Tier3: 6
- Tier4: 6

## Final Evidence Table

| Rank | Drug | Final tier | Prior tier | Evidence grade | Tier change | Rationale |
|---:|---|---|---|---|---|---|
| 1 | MG-132 | Tier3 | Tier3 | preclinical_crc | unchanged | Not an approved drug, but MG-132/proteasome inhibition has colon-cancer cell-line evidence. |
| 2 | PD0325901 | Tier3 | Tier2 | crc_clinical_investigational | Tier2 -> Tier3 | Investigational MEK inhibitor with CRC clinical study evidence; not FDA-approved as a marketed drug. |
| 3 | Irinotecan | Tier1 | Tier1 | crc_approved | unchanged | FDA/NCI-listed colorectal cancer therapy; label includes metastatic carcinoma of colon or rectum. |
| 4 | BI-2536 | Tier4 | Tier4 | weak_non_crc_solid_tumor | unchanged | Investigational PLK1 inhibitor with advanced solid-tumor trials, but no strong drug-specific CRC evidence found in this pass. |
| 5 | CCT-018159 | Tier3 | Tier3 | target_pathway_crc_preclinical | unchanged | HSP90 inhibition has CRC cell-line sensitization evidence; CCT-018159 remains investigational. |
| 6 | YK-4-279 | Tier4 | Tier4 | insufficient_crc_evidence | unchanged | No sufficient CRC-specific clinical or preclinical treatment evidence found in this pass. |
| 7 | Avagacestat | Tier4 | Tier4 | class_relevance_not_drug_specific | unchanged | Gamma-secretase/Notch class has CRC relevance, but available CRC clinical evidence is for another GSI rather than avagacestat. |
| 8 | Trametinib | Tier2 | Tier2 | approved_other_crc_research | unchanged | FDA-approved for other BRAF-mutant cancers; CRC case/research evidence exists for MEK/ERK-pathway use but not CRC approval. |
| 9 | Fulvestrant | Tier4 | Tier4 | approved_other_but_crc_drug_evidence_insufficient | unchanged | Approved in breast cancer settings; CRC evidence found here is biomarker-level ESR1 relevance, not fulvestrant treatment evidence. |
| 10 | Schweinfurthin A | Tier4 | Tier4 | insufficient_crc_evidence | unchanged | No sufficient CRC-specific clinical or preclinical treatment evidence found in this pass. |
| 11 | Mycophenolic acid | Tier4 | Tier4 | approved_other_with_negative_crc_signal | unchanged | Mycophenolate products are approved for transplant rejection prophylaxis; colorectal carcinoma-cell evidence suggests resistance/inactivation rather than a clear repurposing signal. |
| 12 | Gemcitabine | Tier2 | Tier3 | approved_other_crc_clinical_research | Tier3 -> Tier2 | FDA-approved for other cancers and has rectal/metastatic colorectal clinical-study evidence, but not listed as CRC-approved therapy. |
| 13 | Elesclomol | Tier3 | Tier3 | preclinical_crc | unchanged | Investigational compound with colorectal cancer in-vitro/in-vivo ferroptosis evidence. |
| 14 | AZD8055 | Tier3 | Tier3 | preclinical_crc | unchanged | Investigational mTORC1/2 inhibitor with colon/CRC preclinical evidence. |
| 15 | Ulixertinib | Tier3 | Tier3 | crc_research_investigational | unchanged | Investigational ERK inhibitor with CRC case/research evidence; not CRC-approved. |

## Agentic AI Orchestration Recommendation

- Preflight agent: verify VM state, input files, top15 uniqueness, and evidence schema completeness.
- Evidence retrieval agent: refresh FDA/NCI/ClinicalTrials/PubMed sources and record retrieval dates.
- Evidence adjudication agent: apply Tier1-4 rules and flag disagreements with prior protocol tiers.
- Human signoff gate: require clinical/scientific review before marking any candidate as final recommendation.
