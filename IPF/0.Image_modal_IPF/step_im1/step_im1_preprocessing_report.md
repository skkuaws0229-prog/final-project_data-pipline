# Step IM-1 OSIC Preprocessing Report
Date: 20260505

## Input
- Dataset: OSIC Pulmonary Fibrosis Progression (Kaggle)
- Source: `kagglehub_cache/competitions/osic-pulmonary-fibrosis-progression`

## Clinical
- Clinical rows: 1549
- Patients: 176
- Progression threshold: FVC_slope <= -7.5885 mL/week
- Progression labels: {"slow": 132, "rapid": 44}
- Sex counts: {"Male": 139, "Female": 37}
- Smoking status counts: {"Ex-smoker": 118, "Never smoked": 49, "Currently smokes": 9}

## DICOM Volumes
- Patients processed: 176
- Slice count median: 98.0
- Slice count min/max: 12 / 1018
- Total saved volume bytes: 23216256928
- Saved volume format: int16 HU clipped to [-1000, 400]
- Saved volume shape: original DICOM stack shape `[z, y, x]`

## CT-CLIP Note
- Full CT-CLIP tensor `480 x 480 x 240` is not materialized for all patients in IM-1.
- It will be generated on demand during IM-2 smoke test/full embedding extraction to avoid a large intermediate footprint.
- For CT-CLIP pretrained distribution, IM-2 will use repo-style HU window `[-1000, 1000]` and spacing/crop settings.

## Runtime
- Elapsed seconds: 475.8

## Output Files
- `volumes/*.npy`
- `osic_clinical_baseline.csv`
- `osic_volume_metadata.csv`
- `osic_preprocessing_manifest.json`