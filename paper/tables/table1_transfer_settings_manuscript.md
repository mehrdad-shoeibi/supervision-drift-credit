**Table 1. Locked transfer settings and target-context composition.**

| Context | Setting | Source | Target | Train n | Test n | Train default rate | Test default rate |
|---|---|---|---|---|---|---|---|
| in_domain | In-domain reference within the source setting | Source setting held-out fold | Source setting held-out fold | 107843 | 26961 | 0.155958 | 0.155966 |
| temporal | Temporal transfer: train on 2013 loan vintage, evaluate on 2016 loan vintage | 2013 loan vintage | 2016 loan vintage | 134804 | 293057 | 0.155960 | 0.232818 |
| cross_segment | Cross-segment transfer: train on 2013 debt consolidation segment, evaluate on 2013 credit card segment | 2013 debt consolidation loan-purpose segment | 2013 credit card loan-purpose segment | 80634 | 32804 | 0.163641 | 0.131966 |

Source: paper/tables/table1_transfer_settings_draft.csv
