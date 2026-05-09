# Final Project Data Pipeline

This repository contains the lightweight, GitHub-safe handoff package for the 11-disease drug repurposing and image-modal workflows.

Large assets such as raw WSI, DICOM images, UNI2/BiomedCLIP/CT-CLIP embeddings, parquet shards, and trained model binaries remain in S3:

`s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/`

## Folder Map

| Folder | Disease / Workflow | Main Contents |
| --- | --- | --- |
| `BRCA/` | Breast cancer | Image-modal clinical, clustering, survival, drug interpretation summaries |
| `LUNG/` | LUAD / lung cancer | LUAD image-modal outputs, reports, scripts, selected supporting inputs |
| `Liver/` | LIHC / liver cancer | LIHC image-modal outputs and generated analysis artifacts |
| `Colon/` | COAD / colon cancer | COAD image-modal downstream outputs |
| `STAD/` | Stomach cancer | STAD image-modal downstream outputs |
| `PDAC/` | PAAD / pancreatic cancer | PDAC/PAAD image-modal, reports, scripts, ADMET summaries |
| `HNSC/` | Head and neck cancer | HNSC image-modal, reports, scripts, validation summaries |
| `IPF/` | Idiopathic pulmonary fibrosis | CT/image-modal outputs, drug results, validation, metadata |
| `PAH/` | Pulmonary arterial hypertension | CT/image-modal outputs, drug results, validation, metadata |
| `Psoriasis/` | Psoriasis | BiomedCLIP image-modal outputs and HISTAI UNI2 feasibility manifests |
| `RA/` | Rheumatoid arthritis | X-ray image-modal outputs, drug results, validation summaries |
| `pipeline/` | Automated workflow pipeline | Orchestrator, 11 configs, step modules, utilities |

## What Is Included

- Reproducible workflow code and configs
- Step-level CSV/JSON/Markdown summaries
- PCA/Kaplan-Meier/report figures where lightweight
- Top drug, ADMET, 4-tier, and cluster-drug linkage outputs
- S3 manifest and feasibility summaries

## What Is Not Included

- Raw WSI/DICOM/clinical image files
- Large embedding arrays (`.npy`, `.npz`) and parquet shards
- Trained model binary/checkpoint files
- Large raw API dumps and intermediate prediction matrices

Use the S3 bucket above as the source of truth for heavy artifacts.
