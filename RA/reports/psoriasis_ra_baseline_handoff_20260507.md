# Psoriasis / RA Baseline Branch Handoff (2026-05-07)

This note identifies the current canonical non-cancer baseline branches after the recent cleanup and reruns.

## Canonical branches

### Psoriasis

- branch:
  - [/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata)
- universe:
  - 138 named drugs
- flow:
  - Step0 through Step4 branch-native
  - Step5 rerun on SageMaker
  - Step6, Step6b, Step7 rerun specifically for the baseline branch
- branch README:
  - [README.md](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata/README.md)
- final handoff:
  - [FINAL_HANDOFF_20260507.md](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/psoriasis_team_protocol_reproduction_v2_maxdata/FINAL_HANDOFF_20260507.md)

### Rheumatoid arthritis

- branch:
  - [/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline)
- universe:
  - 127 named drugs
- flow:
  - Step1 and Step2 carried as frozen snapshots
  - Step3 is the explicit named-drug divergence point
  - Step4 through Step7 branch-native
- branch README:
  - [README.md](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline/README.md)
- final handoff:
  - [FINAL_HANDOFF_20260507.md](/Users/skku_aws2_18/team4_project/pre_project/thyroid_pipline/data/ra_team_protocol_reproduction_v3_named_drug_baseline/FINAL_HANDOFF_20260507.md)

## What changed

- Psoriasis no longer uses the middle-universe branch as the canonical handoff surface.
- RA no longer uses the old middle-universe Step4b/Step5 outputs as the canonical handoff surface.
- Both diseases now have a branch-level explanation of what is canonical, what is archival, and where the current Step5-Step7 outputs live.

## Practical reading order

For each disease:

1. branch `README.md`
2. lineage manifest
3. `FINAL_HANDOFF_20260507.md`
4. Step5 summary
5. Step6 summary
6. Step7 summary
