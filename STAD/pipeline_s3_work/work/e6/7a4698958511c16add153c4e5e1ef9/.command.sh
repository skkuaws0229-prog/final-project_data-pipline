#!/bin/bash -ue
mkdir -p features
python3 /workspace/nextflow/scripts/build_features.py         --sample-feature-uri 'fe_inputs/sample_features.parquet'         --drug-feature-uri 'fe_inputs/drug_features.parquet'         --label-uri 'fe_inputs/labels.parquet'         --out-features features/features.parquet         --out-labels features/labels.parquet         --out-manifest features/manifest.json         --run-id '20260421_stad_fe_v1'
