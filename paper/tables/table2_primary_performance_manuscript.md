**Table 2. Primary transfer performance across locked evaluation settings.**

In-domain rows are the reference; the difference columns are not applicable (n/a) for those rows.

| Context | Model | Mean AUROC | Mean average precision | Mean Brier | Train default rate | Test default rate | In-domain minus transfer AUROC | Transfer minus in-domain Brier |
|---|---|---|---|---|---|---|---|---|
| in_domain | hgb | 0.652378 | 0.240632 | 0.126771 | 0.155958 | 0.155966 | n/a | n/a |
| in_domain | logreg | 0.636491 | 0.232626 | 0.127833 | 0.155958 | 0.155966 | n/a | n/a |
| in_domain | rf | 0.612104 | 0.209293 | 0.130403 | 0.155958 | 0.155966 | n/a | n/a |
| temporal | hgb | 0.659153 | 0.355216 | 0.175145 | 0.155960 | 0.232818 | -0.006775 | 0.048374 |
| temporal | logreg | 0.653352 | 0.349929 | 0.174711 | 0.155960 | 0.232818 | -0.016861 | 0.046878 |
| temporal | rf | 0.622206 | 0.315663 | 0.179756 | 0.155960 | 0.232818 | -0.010102 | 0.049353 |
| cross_segment | hgb | 0.652969 | 0.210388 | 0.111459 | 0.163641 | 0.131966 | -0.000591 | -0.015312 |
| cross_segment | logreg | 0.640763 | 0.203552 | 0.112271 | 0.163641 | 0.131966 | -0.004272 | -0.015562 |
| cross_segment | rf | 0.613287 | 0.182922 | 0.114510 | 0.163641 | 0.131966 | -0.001183 | -0.015893 |

Source: paper/tables/table2_primary_performance_draft.csv
