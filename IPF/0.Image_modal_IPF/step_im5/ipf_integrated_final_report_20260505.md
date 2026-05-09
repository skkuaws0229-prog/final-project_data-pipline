# IPF AI Drug Repurposing - Integrated Image Modal Report

## 1. Base Pipeline Context
- Base pipeline Step 1-7 completed before image modal.
- Final 15 drugs are read from `step7_admet_final_15_tiered_20260504.csv`.
- Image modal is used for OSIC HRCT patient subtype discovery and MoA stratification hypothesis.

## 2. Image Modal Summary
- Data: OSIC Pulmonary Fibrosis Progression, 176 baseline CT patients.
- Encoder: CT-CLIP v2, XPU inference on Intel Arc.
- Embedding: 512d per patient.
- Clustering: best K=2, silhouette=0.1957.

## 3. Clinical Association
- Association results are saved in `step_im4a/im4a_clinical_association_summary.csv`.
- Progression distribution is saved in `step_im4a/im4a_progression_distribution.csv`.

## 4. Image Modal Validation
- Rapid progression target: bottom quartile of FVC slope.
- Best OSIC CV result: clinical_only / LogisticRegression AUC=0.594.

## 5. Cluster-Drug Stratification Hypothesis
- Cluster profiles and drug mappings are MoA/pathway based.
- Outputs: `step_im4c/im4c_cluster_drug_mapping.csv`, `step_im4c/im4c_mapping_rationale.csv`.

## 6. Limitations
- GEO patients and OSIC patients are not the same people.
- CT-CLIP was not trained specifically for IPF subtype labels.
- Drug mapping is hypothesis-level; no CT-based drug response labels are available.
- IM-1 uses DICOM volumes clipped to lung window and resized for CT-CLIP inference.
