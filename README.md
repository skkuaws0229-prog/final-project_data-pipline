# Final Project Data Pipeline

> A reproducible, multi-disease biomedical data pipeline for image-modal analysis, drug candidate prioritization, ADMET filtering, knowledge-graph integration, and deployment-ready validation artifacts.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![AWS](https://img.shields.io/badge/AWS-S3%20%7C%20SageMaker%20%7C%20Step%20Functions-FF9900?logo=amazonaws&logoColor=white)](https://aws.amazon.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-ready-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Neo4j](https://img.shields.io/badge/Neo4j-graph%20ready-4581C3?logo=neo4j&logoColor=white)](https://neo4j.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Why This Repository Exists

Biomedical AI projects often fail at the handoff stage: results are scattered across notebooks, large image assets cannot live in Git, model outputs are hard to trace, and downstream services need normalized data rather than experiment folders.

This repository packages the reproducible part of that workflow:

- disease-level pipeline code and configuration
- image-modal downstream analysis summaries
- drug ranking, ADMET, and validation artifacts
- normalized database and graph import assets
- backend/API handoff documents
- S3-aware execution plans for large assets

Large raw data such as WSI, DICOM, embedding shards, model checkpoints, and high-volume intermediate arrays are intentionally kept outside Git and referenced through S3 manifests.

## Project Scope

The repository covers 11 disease tracks:

| Folder | Disease Area | Main Assets |
| --- | --- | --- |
| `BRCA/` | Breast cancer | Image-modal clinical analysis, clustering, survival, drug interpretation |
| `LUNG/` | Lung adenocarcinoma | LUAD image-modal outputs, reports, supporting inputs |
| `Liver/` | Liver cancer / LIHC | LIHC image-modal outputs and generated analysis summaries |
| `Colon/` | Colorectal cancer / COAD | COAD image-modal downstream analysis and shared curated inputs |
| `STAD/` | Stomach adenocarcinoma | STAD clustering, survival, and drug-linkage outputs |
| `OV/` | Ovarian cancer | OV baseline pipeline assets and validation results |
| `PDAC/` | Pancreatic cancer / PAAD | PDAC/PAAD image-modal results, reports, ADMET summaries |
| `HNSC/` | Head and neck cancer | HNSC image-modal results, reports, external validation |
| `IPF/` | Idiopathic pulmonary fibrosis | CT/image-modal outputs, drug results, model metadata |
| `PAH/` | Pulmonary arterial hypertension | CT/image-modal outputs and disease-specific artifacts |
| `Psoriasis/` | Psoriasis | BiomedCLIP/HISTAI-related outputs, model results, reports |
| `RA/` | Rheumatoid arthritis | X-ray image-modal results, drug ranking, external validation |

## What Is Inside

```text
.
|-- pipeline/                    # Shared disease pipeline runner, configs, steps, utilities
|-- pipeline/sagemaker/           # AWS SageMaker, Lambda, Step Functions execution assets
|-- drug_service_db_v1/           # Normalized DB tables, PostgreSQL loader, Neo4j graph import
|-- drug_service_backend_v1/      # Backend/API handoff assets and service implementation
|-- docs/                         # Validation notes, API contracts, frontend/backend handoff docs
|-- S3_DATA_INDEX.md              # External data location and access notes
|-- REPOSITORY_FILE_MANIFEST.csv  # File inventory for audit and handoff
|-- <disease>/                    # Disease-specific outputs, reports, scripts, and manifests
```

## Pipeline Capabilities

- Multi-disease execution through YAML configs in `pipeline/configs/`
- Image-modal analysis flow: collection, embedding, clustering, clinical association, drug linkage, reporting
- Drug candidate prioritization with ADMET-aware filtering and tiering
- External validation artifacts for selected disease tracks
- PostgreSQL normalization for service-ready tabular data
- Neo4j graph import assets for disease-drug-target-evidence exploration
- AWS-oriented execution plan for large-scale runs
- Frontend/backend/API validation documents for product handoff

## Quick Start

Clone the repository:

```powershell
git clone https://github.com/skkuaws0229-prog/final-project_data-pipline.git
cd final-project_data-pipline
```

Run a dry-run pipeline check for one disease:

```powershell
python pipeline/run_disease_pipeline.py --config pipeline/configs/04_coad.yaml --dry-run
```

Inspect the local-agent execution guide:

```powershell
Get-Content pipeline/README_local_agent.md
```

For AWS/SageMaker execution details:

```powershell
Get-Content pipeline/sagemaker/README_sagemaker.md
```

## Data Boundary

This repository is designed as a lightweight, reproducible handoff package. It includes code, configs, schemas, reports, small validation assets, manifests, and service-ready normalized data.

It does not include:

- raw WSI, DICOM, or clinical image archives
- high-volume embedding arrays such as `.npy`, `.npz`, or large parquet shards
- trained model checkpoints and binary artifacts
- local virtual environments or `node_modules`
- database volumes or service runtime state
- API keys, cloud credentials, Hugging Face tokens, or other secrets

Primary large-data location:

```text
s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/
```

See `S3_DATA_INDEX.md` for repository-level S3 references and disease-specific access notes.

## Reproducibility Modes

### Git-only mode

Use this mode when you only have the repository contents.

You can:

- inspect disease folder structure and final artifacts
- review summary reports, CSV/JSON outputs, and validation notes
- run dry-run checks for disease configs
- validate API/database/graph handoff materials
- understand the pipeline design and execution contract

### Full-data mode

Use this mode when you also have access to the external S3 data.

You can:

- regenerate image embeddings and large intermediate outputs
- run heavier disease pipelines end to end
- reproduce large image-modal processing stages
- launch AWS/SageMaker jobs using the provided execution assets
- rebuild service-ready outputs from upstream artifacts

## Important Documents

| Document | Purpose |
| --- | --- |
| `pipeline/README_local_agent.md` | Local agent execution protocol |
| `pipeline/sagemaker/README_sagemaker.md` | AWS/SageMaker execution guide |
| `pipeline/sagemaker/automation_protocol.md` | Shared local/AWS operation rules |
| `docs/frontend_api_handoff_workflow_v1.md` | Frontend API handoff workflow |
| `docs/backend_db_integrity_frontend_handoff_v1.md` | Backend/database integrity handoff |
| `docs/rag_bedrock_retrieval_contract_v1.md` | Retrieval context contract for LLM/RAG integration |
| `drug_service_db_v1/README.md` | Database normalization and loading overview |
| `drug_service_backend_v1/README.md` | Backend service overview |
| `REPOSITORY_FILE_MANIFEST.csv` | Auditable repository file inventory |

## Suggested Review Path

1. Start with this README.
2. Open `REPOSITORY_FILE_MANIFEST.csv` to understand the full file inventory.
3. Review `S3_DATA_INDEX.md` for external data boundaries.
4. Inspect `pipeline/configs/` to see disease-level execution definitions.
5. Read `pipeline/README_local_agent.md` for local execution.
6. Read `pipeline/sagemaker/README_sagemaker.md` for AWS execution.
7. Explore `drug_service_db_v1/` and `drug_service_backend_v1/` for productization assets.

## Security Notes

The repository was structured to avoid committing sensitive runtime material. In particular, cloud credentials, model hub tokens, private keys, API keys, and local environment folders should remain outside Git.

Before publishing derivative work, run your own secret scan and confirm that any private S3 bucket names, patient-level raw data, and regulated clinical data are handled according to your institution's policy.

## License

This project is released under the MIT License. See [LICENSE](LICENSE).

## Star This Project

If this repository helps you organize biomedical AI pipelines, reproduce disease-specific drug prioritization workflows, or build a handoff package for clinical AI services, a star helps others discover it too.
