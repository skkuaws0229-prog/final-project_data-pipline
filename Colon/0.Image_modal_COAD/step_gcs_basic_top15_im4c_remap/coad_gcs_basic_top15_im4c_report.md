# COAD GCS Basic Top15 IM4c Remap

Existing im1/im2/im3/im4a/im4b outputs were reused. Only the new ADMET top15 drug set was remapped to image-modal clusters.
Tier values are protocol/provisional labels and still need current regulatory or clinical-trial verification before final clinical interpretation.

## Summary

- Top15 drugs: 15
- Image clusters reused: 4
- Cluster-drug links: 60
- Prior image-modal tier matches carried forward: 3

## Drug-Level Ranking

| ADMET rank | Drug | Tier | Best match | Pathway | Status |
|---:|---|---|---:|---|---|
| 3 | Irinotecan | Tier1 | 8 | DNA replication | protocol_prior_needs_current_regulatory_verification |
| 2 | PD0325901 | Tier2 | 6 | ERK MAPK signaling | protocol_prior_needs_current_regulatory_verification |
| 8 | Trametinib | Tier2 | 6 | ERK MAPK signaling | protocol_prior_needs_current_regulatory_verification |
| 15 | Ulixertinib | Tier3 | 6 | ERK MAPK signaling | provisional_im4c_remap_needs_current_regulatory_verification |
| 1 | MG-132 | Tier3 | 5 | Protein stability and degradation | provisional_im4c_remap_needs_current_regulatory_verification |
| 12 | Gemcitabine | Tier3 | 5 | DNA replication | provisional_im4c_remap_needs_current_regulatory_verification |
| 14 | AZD8055 | Tier3 | 5 | PI3K/MTOR signaling | provisional_im4c_remap_needs_current_regulatory_verification |
| 5 | CCT-018159 | Tier3 | 4 | Protein stability and degradation | provisional_im4c_remap_needs_current_regulatory_verification |
| 13 | Elesclomol | Tier3 | 4 | Protein stability and degradation | provisional_im4c_remap_needs_current_regulatory_verification |
| 4 | BI-2536 | Tier4 | 1 | Cell cycle | provisional_im4c_remap_needs_current_regulatory_verification |
| 6 | YK-4-279 | Tier4 | 1 | Other | provisional_im4c_remap_needs_current_regulatory_verification |
| 7 | Avagacestat | Tier4 | 1 | Other | provisional_im4c_remap_needs_current_regulatory_verification |
| 9 | Fulvestrant | Tier4 | 1 | Hormone-related | provisional_im4c_remap_needs_current_regulatory_verification |
| 10 | Schweinfurthin A | Tier4 | 1 | Unclassified | provisional_im4c_remap_needs_current_regulatory_verification |
| 11 | Mycophenolic acid | Tier4 | 1 | Unclassified | provisional_im4c_remap_needs_current_regulatory_verification |

## Agentic AI / Orchestrator Insertion Points

- Preflight agent: verify that im2 embeddings, im3 clusters, im4a clinical tables, and top15 candidates are present and schema-compatible.
- Evidence agent: collect current approval, guideline, clinical-trial, PubMed, and mechanism evidence for Tier1-4 verification.
- Safety agent: review ADMET hard-fail flags, PAINS/Lipinski issues, and known toxicity signals before final ranking.
- Report agent: synthesize cluster-specific hypotheses and flag weak or unsupported cluster-drug links for human review.
