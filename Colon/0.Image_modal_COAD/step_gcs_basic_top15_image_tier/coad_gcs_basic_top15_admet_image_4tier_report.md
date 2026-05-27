# COAD GCS Basic Top15 Image/Tier Finalization

This file combines the new GCS basic pipeline ADMET top15 with the existing COAD image-modal 4-tier evidence.
Tier values copied here are protocol priors, not newly verified current regulatory claims.

## Summary

- ADMET top15 rows: 15
- Image-modal matched rows: 3
- Image-modal unmatched rows: 12
- Existing cluster-evidence matched rows: 3

## Top15

| Rank | Drug | ADMET score | Image match | Provisional tier | Status |
|---:|---|---:|---|---|---|
| 1 | MG-132 | 0.986054 | no | Needs image-modal remapping | needs_image_modal_mapping_and_current_regulatory_verification |
| 2 | PD0325901 | 0.960374 | yes | Tier2 | needs_current_regulatory_verification |
| 3 | Irinotecan | 0.947075 | yes | Tier1 | needs_current_regulatory_verification |
| 4 | BI-2536 | 0.941293 | no | Needs image-modal remapping | needs_image_modal_mapping_and_current_regulatory_verification |
| 5 | CCT-018159 | 0.925340 | no | Needs image-modal remapping | needs_image_modal_mapping_and_current_regulatory_verification |
| 6 | YK-4-279 | 0.907143 | no | Needs image-modal remapping | needs_image_modal_mapping_and_current_regulatory_verification |
| 7 | Avagacestat | 0.887381 | no | Needs image-modal remapping | needs_image_modal_mapping_and_current_regulatory_verification |
| 8 | Trametinib | 0.872415 | yes | Tier2 | needs_current_regulatory_verification |
| 9 | Fulvestrant | 0.854524 | no | Needs image-modal remapping | needs_image_modal_mapping_and_current_regulatory_verification |
| 10 | Schweinfurthin A | 0.818980 | no | Needs image-modal remapping | needs_image_modal_mapping_and_current_regulatory_verification |
| 11 | Mycophenolic acid | 0.812075 | no | Needs image-modal remapping | needs_image_modal_mapping_and_current_regulatory_verification |
| 12 | Gemcitabine | 0.802041 | no | Needs image-modal remapping | needs_image_modal_mapping_and_current_regulatory_verification |
| 13 | Elesclomol | 0.795748 | no | Needs image-modal remapping | needs_image_modal_mapping_and_current_regulatory_verification |
| 14 | AZD8055 | 0.792857 | no | Needs image-modal remapping | needs_image_modal_mapping_and_current_regulatory_verification |
| 15 | Ulixertinib | 0.784524 | no | Needs image-modal remapping | needs_image_modal_mapping_and_current_regulatory_verification |

## Next Action

Run image-modal drug-cluster remapping for the 12 unmatched GCS basic top15 drugs before using the table as a final image-aware recommendation set.
