# Fairness & Responsible AI Report — Phase 6

Notebook: `notebooks/05_fairness_evaluation.ipynb` · Disparity table: `reports/fairness_disparities.csv`
Figures: `figures/19_fairness_audit.png`, `figures/20_risk_distribution_by_group.png`

> **Ethical boundary.** Workforce Pulse is a research / decision-support prototype built on fictional data. Its scores
> must never be used to rank or select employees for dismissal, promotion, pay, or any other employment decision,
> and must never trigger an action without human review.

## 1. What was excluded and what was audited
| | Attributes |
|---|---|
| Excluded from model features | Age, Gender, MaritalStatus (plus the derived AgeBand) |
| Kept in a separate audit view, joined only after scoring | Age / AgeBand, Gender, MaritalStatus |
| Audit data | Out-of-fold predictions for all 1,470 employees (more stable than the 59-leaver test set) |
| Operating threshold | 0.14 (recall-oriented, see `model_report.md`) |

## 2. Results by group (95 % Wilson CIs in brackets)

### Gender — no material disparity
| Group | n | Leavers | Actual rate | Flag rate | Recall | FPR | Precision |
|---|---|---|---|---|---|---|---|
| Female | 588 | 87 | 14.8 % | 40.3 % [36–44] | 0.83 [0.73–0.89] | 0.33 | 0.30 |
| Male | 882 | 150 | 17.0 % | 37.4 % [34–41] | 0.77 [0.69–0.83] | 0.29 | 0.35 |

Flag-rate ratio 1.08 (within the 0.8–1.25 screen). Recall and FPR intervals overlap. **Proxy test:** model features
predict gender at ROC-AUC 0.50, i.e. no gender information is recoverable.

### Marital status — disparity driven by a proxy
| Group | n | Leavers | Actual rate | Flag rate | Recall | FPR | Precision |
|---|---|---|---|---|---|---|---|
| Single | 470 | 120 | 25.5 % | 49.4 % [45–54] | 0.85 [0.78–0.90] | 0.37 | 0.44 |
| Married | 673 | 84 | 12.5 % | 36.3 % [33–40] | 0.67 [0.56–0.76] | 0.32 | 0.23 |
| Divorced | 327 | 33 | 10.1 % | 27.8 % [23–33] | 0.88 [0.73–0.95] | 0.21 | 0.32 |

- Single employees are flagged 1.36× as often as Married (**outside** the screen). Their actual attrition is 2.05×,
  so the model **under**-reflects the real gap (mean predicted 21.9 % vs actual 25.5 %) rather than inflating it.
- **Equal-opportunity gap:** the model misses 33 % of Married leavers vs 15 % of Single leavers.
- **Proxy:** model features predict "Single" at ROC-AUC **0.93**. The cause is a data artifact: **all 470 Single
  employees have StockOptionLevel = 0**, i.e. no Single employee holds any stock options.
  StockOptionLevel alone reaches AUC 0.92 and is the model's 3rd most important feature.
- **Within the same overtime status and tenure band**, Single employees are still flagged more often than
  Married ones (e.g. no overtime, Early tenure: 43.6 % vs 30.8 %), partly matching their higher actual rates in those cells.

### Age — the strongest disparity
| Age band | n | Leavers | Actual rate | Mean score | Flag rate | Recall | FPR |
|---|---|---|---|---|---|---|---|
| Under 25 | 97 | 38 | 39.2 % | 29.2 % | 66.0 % [56–75] | 0.89 | **0.51** [0.38–0.63] |
| 25–34 | 554 | 112 | 20.2 % | 18.4 % | 41.3 % | 0.85 | 0.30 |
| 35–44 | 505 | 51 | 10.1 % | 14.8 % | 37.0 % | 0.75 | 0.33 |
| 45–54 | 245 | 25 | 10.2 % | 11.7 % | 28.2 % | **0.60** [0.41–0.77] | 0.25 |
| 55+ | 69 | 11 | 15.9 % | 11.2 % | 26.1 % | **0.45** [0.21–0.72] | 0.22 |

- **Proxy:** model features predict "Age ≥ 35" at ROC-AUC **0.83**, mainly through TotalWorkingYears (0.82 alone),
  JobLevel and income.
- **Two opposite harms:**
  - Young employees who *stay* are wrongly flagged half the time (FPR 0.51 for under-25s).
  - Older employees who *leave* are often missed: recall 0.60 (45–54) and 0.45 (55+). The 55+ group has 15.9 % actual
    attrition (retirement is a plausible, unmodelled reason), but the model gives it the lowest mean score (11.2 %).
- Older-band estimates rest on 25 and 11 leavers: the intervals are wide. The pattern is consistent but not precisely measured.

## 3. Mitigation experiment: remove StockOptionLevel
Same model configuration, same out-of-fold procedure, same threshold:

| | Current model | Without StockOptionLevel |
|---|---|---|
| PR-AUC (OOF, all 1,470) | 0.625 | 0.590 |
| ROC-AUC | 0.830 | 0.816 |
| Flag rate Single / Married / Divorced | 49.4 / 36.3 / 27.8 % | 39.4 / 39.1 / 39.1 % |
| Single ÷ Married flag ratio | 1.36 | **1.01** |
| Recall Single / Married / Divorced | 0.85 / 0.67 / 0.88 | 0.80 / 0.69 / 0.88 |

Removing the proxy restores marital-status parity in flag rates at a cost of −0.035 PR-AUC. It does **not** remove
age effects, because the age proxy (TotalWorkingYears) is a legitimate experience variable.

## 4. Assessment
| Attribute | Disparity found | Main mechanism | Severity |
|---|---|---|---|
| Gender | None material | — | Low |
| MaritalStatus | Flag ratio 1.36; Married leavers missed more | StockOptionLevel ≈ marital-status encoding (data artifact) | Medium: fixable at moderate cost |
| Age | Young stayers over-flagged (FPR 0.51); older leavers under-detected (recall 0.45–0.60) | Experience / tenure variables + real age gradient in attrition | **High**: structural, not removable by dropping one feature |

Excluding protected attributes from the features was **necessary but not sufficient**. Without this audit, the
marital-status proxy and the age pattern would have gone unnoticed.

## 5. Recommendations before any real-world use
1. **Prefer the variant without StockOptionLevel** for anything that touches individuals. A 0.035 PR-AUC loss is a
   reasonable price for removing a near-direct encoding of marital status. This is a governance decision for
   HR, Legal and the Works Council, not a modelling decision.
2. **Use scores at group level** (team, role, department) to target workload and engagement programs, rather than as
   individual flags. Group-level use reduces individual harm from false positives.
3. **Do not use a single threshold blindly across age groups.** Review whether any individual-level outreach is equally
   valuable to all employees regardless of score (e.g. universal stay interviews for the first 2 years).
4. **Model the 55+ group separately or add retirement eligibility** as an explicit, documented variable if real data allows.
5. **Before deployment:** legal review (GDPR Art. 22 and Art. 35 DPIA, EU AI Act: employment-related AI systems are
   classified high-risk), employee transparency notice, works-council consultation, human-in-the-loop sign-off.
6. **Monitoring:** recompute this audit (flag rate, recall, FPR, calibration by group, with CIs) at every model refresh,
   with alert thresholds agreed in advance.

## 6. Limitations of this audit
- Fictional data: disparities describe IBM's synthetic sample, not a real organization.
- Only three protected attributes are available. Others (ethnicity, disability, nationality) cannot be audited.
- Small leaver counts in several groups (55+: 11, 45–54: 25, Divorced: 33) produce wide intervals.
- Group metrics are evaluated one attribute at a time. Intersections (e.g. young + female) were not tested for lack of sample size.
- Fairness criteria conflict: with different base rates, equal flag rates, equal recall and equal precision cannot all
  hold at once. The criterion to prioritize depends on the use case and must be agreed with stakeholders.
