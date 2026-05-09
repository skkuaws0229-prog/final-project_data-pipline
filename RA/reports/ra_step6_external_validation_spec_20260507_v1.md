# RA Step6 External Validation Spec (2026-05-07)

This spec fixes the next RA branch transition after Step5 ML for the named-drug baseline branch:

- branch root: `ra_team_protocol_reproduction_v3_named_drug_baseline`
- Step3 named-drug universe: `127` drugs
- Step4 named-drug inputs: `phase2a` and `phase2b` both available
- Step5 ML: completed locally via SageMaker bundle outputs

The goal of this document is to keep RA Step6 aligned with the non-cancer kickoff documents instead of deriving validation rules ad hoc from the older all-compound branch.

## 1. Validation intent

RA external validation should remain tissue-aware and should not mix synovium and blood casually.

Primary objective:
- validate whether the RA named-drug baseline ranking is consistent with synovial-tissue disease biology

Secondary objective:
- attach weaker blood-side support without letting it override synovial evidence

## 2. Cohort roles

### Primary synovial signature source

1. `GSE89408`
   - role: main RA synovium disease signature backbone
   - design note: large synovial biopsy cohort
   - comparison axis:
     - RA vs healthy synovium
     - RA vs OA synovium
   - local source:
     - `data/ra_source_staging/geo/GSE89408/GSE89408_series_matrix.txt.gz`
     - `data/ra_source_staging/geo/GSE89408/GSE89408_GEO_count_matrix_rename.txt.gz`

### Synovial external validation cohorts

2. `GSE55235`
   - role: first independent synovial validation
   - comparison axis:
     - healthy vs OA vs RA
   - local source:
     - `data/ra_source_staging/geo/GSE55235/GSE55235_series_matrix.txt.gz`

3. `GSE55457`
   - role: second independent synovial validation
   - comparison axis:
     - healthy vs OA vs RA
   - local source:
     - `data/ra_source_staging/geo/GSE55457/GSE55457_series_matrix.txt.gz`

### Blood-side support cohort

4. `GSE93272`
   - role: blood-side external support only
   - rule:
     - do not merge with synovial signature construction
     - do not let blood agreement outrank synovial disagreement
   - local source:
     - `data/ra_source_staging/geo/GSE93272/GSE93272_series_matrix.txt.gz`

### Metadata-only future axis

5. `AMP_RA_SDY998`
   - role: future orthogonal validation axis
   - current status:
     - metadata available
     - raw/result acquisition blocked by authentication
   - blocking note:
     - keep outside executable Step6 until authenticated acquisition is resolved

## 3. Platform handling rules

- `GSE89408` uses a count matrix and should be converted to gene-level expression directly.
- `GSE55235` and `GSE55457` are `GPL96` microarrays and require `GPL96.annot.gz`.
- `GSE93272` is `GPL570` microarray and requires `GPL570.annot.gz`.
- Probe-to-gene mapping must be cohort-local and explicit.
- Validation summaries should preserve accession-level provenance.

## 4. Step6 scoring rules

### Synovial route

For each candidate drug/model:

1. keep Step5 ranking unchanged
2. annotate whether the candidate drug is a direct RA treatment anchor or same-axis anchor
3. score synovial validation support using:
   - RA vs healthy agreement
   - RA vs OA agreement
   - reproducibility across `GSE89408`, `GSE55235`, `GSE55457`

### Blood route

- `GSE93272` should be a support-only route.
- It can strengthen confidence if aligned with synovium.
- It must not rescue candidates that fail synovial logic.

## 5. Output expectations

When RA Step6 is implemented, expected outputs should mirror the psoriasis pattern while staying RA-specific:

- `step6_ra_external_validation_<stamp>/reports/ra_step6_validation_cohort_catalog_<stamp>.csv`
- `step6_ra_external_validation_<stamp>/reports/ra_step6_model_validation_summary_<stamp>.csv`
- `step6_ra_external_validation_<stamp>/reports/ra_step6_model_top30_validation_report_<stamp>.csv`
- `step6_ra_external_validation_<stamp>/validation_cohort/*.csv`
- `step6_ra_external_validation_<stamp>/model_outputs/phase2a_<model>_top30_validated.csv`

Recommended first-pass scope:
- use `phase2a` as the main RA validation surface
- keep `phase2b` as a secondary comparison only, since Step5 results favored `phase2a`

## 6. Current blocker boundary

Executable Step6 can proceed for the GEO backbone cohorts listed above.

Blocked for now:
- AMP RA raw/result follow-up requiring authentication

This means:
- RA Step6 implementation should start with GEO synovium + blood support
- AMP RA should remain a documented future extension, not a hidden missing input

## 7. Immediate next implementation step

Implement RA Step6 in this order:

1. parse `GSE89408`, `GSE55235`, `GSE55457`, `GSE93272` into gene-level cohort tables
2. define RA synovium validation summary rules
3. annotate Step5 named-drug baseline top30 outputs without reranking
4. keep blood support in a separate column family from synovial support
