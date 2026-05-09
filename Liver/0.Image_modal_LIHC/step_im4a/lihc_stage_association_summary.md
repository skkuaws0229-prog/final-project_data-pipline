# LIHC image cluster stage association summary

Source file: `cluster_statistical_tests.csv`

## Main clinical association results

| Variable | Chi-square | p-value | dof | Interpretation |
|---|---:|---:|---:|---|
| AJCC_PATHOLOGIC_TUMOR_STAGE | 54.169800814186175 | 4.864524890004894e-06 | 16 | Significant |
| PATH_T_STAGE | 72.16648331403258 | 4.15246861610943e-09 | 16 | Strongly significant |
| PATH_N_STAGE | 15.360915746646944 | 0.0040083179253249 | 4 | Significant |
| GRADE | 13.798054743179524 | 0.0871832831612524 | 8 | Not significant; trend only |
| molecular_subtype | 12.892037789967205 | 0.0447827929567493 | 6 | Significant |

## Report-ready sentence

LIHC image clusters showed a significant association with AJCC pathologic tumor
stage (chi-square = 54.17, p = 4.86e-06), with the strongest association
observed for pathologic T stage (chi-square = 72.17, p = 4.15e-09).
Pathologic N stage was also significant (chi-square = 15.36, p = 0.0040),
whereas grade was not statistically significant (p = 0.087).

## Notes

TERT promoter availability, TERT mRNA expression, and TERT copy-number analyses
were added separately. Stage association should be interpreted together with
the TERT-augmented clinical, mutation, expression, CNA, survival, and
drug-cluster outputs.
