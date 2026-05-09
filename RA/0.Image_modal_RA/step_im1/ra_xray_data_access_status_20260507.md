# RA X-ray Image-Modal Data Access Status

Date: 2026-05-07

## Objective

Run RA image-modal analysis with joint X-ray images because public RA synovial
H&E WSI data were not available.

Target S3 output:

`s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/`

## Priority Dataset: Taiwan Medical AI Portal D07

Dataset page:

`https://data.dmc.nycu.edu.tw/dataset/d07-x-ray`

Title:

`X-Ray Images of the Hands and Feet for Rheumatoid Arthritis`

Portal description:

- DICOM X-ray images of bilateral hands and feet for RA.
- Corresponding scoring files are described as Excel format.
- Tags: Foot, Hand, Rheumatoid Arthritis, X-ray.
- Organization: Taipei Veterans General Hospital.

Downloaded public resources:

- `D07.csv`
- `1-1_x-ray_2020-12-22.pdf`

Local check:

- `D07.csv` rows: 4,639 DICOM index rows.
- Unique patients: 408.
- Unique accession numbers: 1,854.
- Modality: CR 2,004 rows; DX 2,635 rows.
- Study descriptions include bilateral hand and foot studies.

Important blocker:

- `D07.csv` contains WADO retrieve URLs, but they point to private IP addresses
  (`10.221.x.x`) and timed out from the local machine.
- The portal cloud-drive API returned an empty file list for the dataset root in
  the unauthenticated/current session.
- Therefore, the visible CSV/PDF are accessible, but the actual DICOM payload
  still requires portal cloud-drive access or a download task from an authenticated
  session.

## Alternative Dataset: RAM-W1K

Paper/dataset summary found:

- 1,048 wrist conventional radiographs.
- 388 patients.
- Four medical centers.
- 618 images with wrist bone instance segmentation.
- 800 images with Sharp/van der Heijde bone erosion score.

Current status:

- Public descriptive pages were found.
- A direct bulk download URL has not yet been confirmed.
- Use as fallback if Taiwan D07 DICOM access cannot be completed.

## Model Environment

Preferred model:

`microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224`

Reason:

- Biomedical vision-language model.
- Model card includes radiography examples.
- Official usage requires `open_clip_torch` and `transformers`.

Local environment prepared:

`C:\Users\biso8\20260503_final_project\IPF\.venv_img`

Installed/available:

- torch
- torchvision
- pydicom
- pillow
- pandas
- scikit-learn
- open_clip_torch==2.23.0
- transformers==4.35.2

Model weights are not downloaded yet. The main model file is roughly 784 MB and
should be downloaded when X-ray images are available.

## RA Baseline S3 Status

Base S3:

`s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/`

The RA baseline pipeline is present with:

- model inputs
- ML model results
- external validation
- ADMET
- final reports

Selected baseline results:

- Branch: `ra_v3_named_drug_baseline`
- Phases: phase2a, phase2b
- Models: RandomForest, ExtraTrees, LightGBM, XGBoost, CatBoost
- External validation phase: phase2a
- Synovium validation mean same-direction fraction: 0.8525
- Synovium validation mean signed Spearman: 0.7894
- ADMET gate: all five models kept 30/30 top30 candidates
- Toxicity flagged count: 0
- Unique final candidates after union: 17
- Recommended final candidates: 16

Highlighted RA candidate tiers:

- tier1_reference_anchor: 2
- tier2_cross_model_supported: 13
- tier3_core_axis_supported: 1
- tier5_single_model_admet_pass: 1

Key tier1 reference anchors:

- Ruxolitinib
- Tofacitinib

## Next Actions

1. Complete Taiwan D07 portal access for actual DICOM download.
2. If DICOM access opens, download the image files plus Sharp/van der Heijde
   score file.
3. Convert DICOM to PNG in `step_im1`.
4. Extract BiomedCLIP embeddings in `step_im2`.
5. Run K-means k=2/3/4/5 and PCA in `step_im3`.
6. Test cluster association with Sharp/van der Heijde score in `step_im4a`.
7. Connect clusters to RA baseline Top30/ADMET candidates in `step_im4c`.
8. Package and upload final report in `step_im5`.
