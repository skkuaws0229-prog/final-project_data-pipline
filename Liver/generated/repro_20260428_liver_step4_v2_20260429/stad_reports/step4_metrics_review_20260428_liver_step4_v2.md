# Step 4 metrics review

- Generated: 2026-04-28T22:47:37
- Rows in full CSV: 45

| family   | stem                                 | model                |     sp_cv5 |   sp_groupcv |   sp_scaffoldcv |     gap_cv5 |   gap_groupcv |   gap_scaffoldcv |
|:---------|:-------------------------------------|:---------------------|-----------:|-------------:|----------------:|------------:|--------------:|-----------------:|
| dl       | stad_numeric_context_smiles_dl_v1    | DL_MLP_1024_512_256  |  0.797284  |   0.508374   |       0.409497  |  0.0292667  |    0.311246   |       0.396966   |
| dl       | stad_numeric_context_smiles_dl_v1    | DL_MLP_2x1024        |  0.802406  |   0.52539    |       0.39463   |  0.0249916  |    0.284134   |       0.367208   |
| dl       | stad_numeric_context_smiles_dl_v1    | DL_MLP_2x512         |  0.795627  |   0.5377     |       0.425937  |  0.028676   |    0.290043   |       0.355362   |
| dl       | stad_numeric_context_smiles_dl_v1    | DL_MLP_3x512         |  0.790515  |   0.531802   |       0.387955  |  0.0283009  |    0.28398    |       0.341993   |
| dl       | stad_numeric_context_smiles_dl_v1    | DL_MLP_ResidualStyle |  0.786353  |   0.499022   |       0.399199  |  0.0302186  |    0.25371    |       0.389429   |
| dl       | stad_numeric_context_smiles_dl_v1    | DL_MLP_SELU_3x256    |  0.832214  |   0.516585   |       0.372222  |  0.03528    |    0.302302   |       0.168954   |
| dl       | stad_numeric_context_smiles_dl_v1    | DL_MLP_WideNarrow    |  0.795639  |   0.522918   |       0.419083  |  0.0283815  |    0.285283   |       0.37088    |
| dl       | stad_numeric_dl_v1                   | DL_MLP_1024_512_256  |  0.800686  |   0.443149   |       0.414361  |  0.0292263  |    0.179815   |       0.209602   |
| dl       | stad_numeric_dl_v1                   | DL_MLP_2x1024        |  0.791286  |   0.500866   |       0.403014  |  0.0284669  |    0.234482   |       0.256143   |
| dl       | stad_numeric_dl_v1                   | DL_MLP_2x512         |  0.769928  |   0.519188   |       0.401431  |  0.0271214  |    0.287768   |       0.362576   |
| dl       | stad_numeric_dl_v1                   | DL_MLP_3x512         |  0.804321  |   0.488514   |       0.420665  |  0.0332608  |    0.230783   |       0.201154   |
| dl       | stad_numeric_dl_v1                   | DL_MLP_ResidualStyle |  0.802613  |   0.510564   |       0.388416  |  0.0269976  |    0.299168   |       0.332318   |
| dl       | stad_numeric_dl_v1                   | DL_MLP_SELU_3x256    |  0.820439  |   0.519246   |       0.347646  |  0.0358381  |    0.312079   |       0.31754    |
| dl       | stad_numeric_dl_v1                   | DL_MLP_WideNarrow    |  0.785825  |   0.520864   |       0.404074  |  0.0348691  |    0.277811   |       0.367743   |
| dl       | stad_numeric_smiles_dl_v1            | DL_MLP_1024_512_256  |  0.805144  |   0.501851   |       0.406615  |  0.0311735  |    0.226125   |       0.329434   |
| dl       | stad_numeric_smiles_dl_v1            | DL_MLP_2x1024        |  0.797353  |   0.485519   |       0.396871  |  0.0251406  |    0.216729   |       0.426403   |
| dl       | stad_numeric_smiles_dl_v1            | DL_MLP_2x512         |  0.8       |   0.509761   |       0.406797  |  0.0263573  |    0.230853   |       0.396263   |
| dl       | stad_numeric_smiles_dl_v1            | DL_MLP_3x512         |  0.803532  |   0.514951   |       0.382444  |  0.0300401  |    0.27819    |       0.320437   |
| dl       | stad_numeric_smiles_dl_v1            | DL_MLP_ResidualStyle |  0.804216  |   0.521902   |       0.426702  |  0.0284343  |    0.247012   |       0.233655   |
| dl       | stad_numeric_smiles_dl_v1            | DL_MLP_SELU_3x256    |  0.820559  |   0.458188   |       0.386329  |  0.0376861  |    0.20653    |       0.255924   |
| dl       | stad_numeric_smiles_dl_v1            | DL_MLP_WideNarrow    |  0.800041  |   0.511025   |       0.396062  |  0.0282949  |    0.278101   |       0.420965   |
| graph    | stad_numeric_context_smiles_graph_v1 | GAT                  |  0.088543  |   0.175499   |       0.006982  | -0.00715295 |   -0.0343841  |      -0.0455623  |
| graph    | stad_numeric_context_smiles_graph_v1 | GraphSAGE            |  0.119143  |   0.199469   |       0.0092231 | -0.0207707  |   -0.0076625  |       0.0899868  |
| graph    | stad_numeric_graph_v1                | GAT                  |  0.0877798 |  -0.00269414 |       0.010622  |  0.023151   |    0.0161695  |       0.0618799  |
| graph    | stad_numeric_graph_v1                | GraphSAGE            |  0.12251   |   0.0845792  |       0.126563  |  0.0208048  |   -0.00166643 |       0.0182896  |
| graph    | stad_numeric_smiles_graph_v1         | GAT                  | -0.0656008 |   0.0844764  |      -0.0428965 | -0.00907968 |    0.0121818  |       0.0746396  |
| graph    | stad_numeric_smiles_graph_v1         | GraphSAGE            |  0.168688  |   0.239235   |       0.0114344 |  0.0176947  |   -0.00943232 |       0.00453831 |
| ml       | stad_numeric_context_smiles_ml_v1    | CatBoost             |  0.857881  |   0.522525   |       0.463755  |  0.108653   |    0.450808   |       0.510225   |
| ml       | stad_numeric_context_smiles_ml_v1    | ExtraTrees           |  0.850138  |   0.463702   |       0.435197  |  0.149862   |    0.536298   |       0.564803   |
| ml       | stad_numeric_context_smiles_ml_v1    | LightGBM             |  0.857197  |   0.459498   |       0.416798  |  0.141424   |    0.539425   |       0.582045   |
| ml       | stad_numeric_context_smiles_ml_v1    | RandomForest         |  0.85063   |   0.472961   |       0.44089   |  0.133169   |    0.510795   |       0.542738   |
| ml       | stad_numeric_context_smiles_ml_v1    | SVR_RBF              |  0.40039   |   0.358231   |       0.329697  |  0.00393339 |    0.0416743  |       0.0737025  |
| ml       | stad_numeric_context_smiles_ml_v1    | XGBoost              |  0.857038  |   0.494882   |       0.456314  |  0.138387   |    0.502485   |       0.541223   |
| ml       | stad_numeric_ml_v1                   | CatBoost             |  0.857234  |   0.539351   |       0.459651  |  0.101815   |    0.427526   |       0.507423   |
| ml       | stad_numeric_ml_v1                   | ExtraTrees           |  0.849458  |   0.465116   |       0.428214  |  0.150542   |    0.534884   |       0.571786   |
| ml       | stad_numeric_ml_v1                   | LightGBM             |  0.857654  |   0.498094   |       0.400038  |  0.139582   |    0.499884   |       0.597629   |
| ml       | stad_numeric_ml_v1                   | RandomForest         |  0.851234  |   0.493129   |       0.421058  |  0.132546   |    0.490623   |       0.562561   |
| ml       | stad_numeric_ml_v1                   | SVR_RBF              |  0.400393  |   0.358327   |       0.329767  |  0.00389666 |    0.0414779  |       0.0735555  |
| ml       | stad_numeric_ml_v1                   | XGBoost              |  0.85926   |   0.513487   |       0.448388  |  0.134238   |    0.482583   |       0.547626   |
| ml       | stad_numeric_smiles_ml_v1            | CatBoost             |  0.859056  |   0.540053   |       0.467632  |  0.101405   |    0.42733    |       0.499137   |
| ml       | stad_numeric_smiles_ml_v1            | ExtraTrees           |  0.849671  |   0.455875   |       0.421132  |  0.150329   |    0.544125   |       0.578868   |
| ml       | stad_numeric_smiles_ml_v1            | LightGBM             |  0.856656  |   0.485996   |       0.407679  |  0.140613   |    0.512033   |       0.59002    |
| ml       | stad_numeric_smiles_ml_v1            | RandomForest         |  0.8513    |   0.492373   |       0.420435  |  0.132536   |    0.491393   |       0.563153   |
| ml       | stad_numeric_smiles_ml_v1            | SVR_RBF              |  0.400435  |   0.358222   |       0.329699  |  0.00388891 |    0.0416315  |       0.073692   |
| ml       | stad_numeric_smiles_ml_v1            | XGBoost              |  0.858999  |   0.504303   |       0.4518    |  0.134546   |    0.491895   |       0.544488   |

_Columns: **sp_cv5** = 5-fold CV validation Spearman; **sp_groupcv**, **sp_scaffoldcv** = same for GroupCV / ScaffoldCV; **gap_*** = mean train−val Spearman gap per eval mode._
