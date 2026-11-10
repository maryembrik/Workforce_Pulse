# Attrition Model Report — Phase 5

Notebook: `notebooks/04_attrition_modeling.ipynb` · Config: `models/model_config.json` · Tracking: `mlflow ui --backend-store-uri sqlite:///mlflow.db`
Predictions: `data/predictions/employee_attrition_predictions.csv` · Scenarios: `data/predictions/scenario_sensitivity.csv`

## 1. Problem and setup
- **Task:** binary classification of `AttritionFlag` (237 leavers / 1,470 = 16.1 %).
- **Inputs:** 25 work-related columns. Excluded: ID, protected attributes (Age, Gender, MaritalStatus), undocumented
  rate columns. `SalaryRatioToLevel` is recomputed inside the pipeline from training folds only.
- **Split:** 75/25 stratified (train 1,102 / 178 leavers; test 368 / 59 leavers). Tuning: 5-fold × 2 repeated stratified CV.
- **Primary metric:** PR-AUC (no-skill = 0.16). Accuracy is reported but never used for decisions.

## 2. Model comparison

| Model | CV PR-AUC (± sd) | CV ROC-AUC | Test PR-AUC | Test ROC-AUC | Test Brier |
|---|---|---|---|---|---|
| Dummy (prevalence) | — | — | 0.160 | 0.500 | 0.135 |
| **Logistic Regression** (C = 0.3, no class weights, no MonthlyIncome) | 0.665 ± 0.072 | 0.843 | **0.581** | 0.805 | 0.100 |
| XGBoost (depth 2, lr 0.03, 400 trees, min_child_weight 5, no class weights) | 0.634 ± 0.084 | 0.836 | 0.549 | 0.809 | 0.102 |

- **Selection rule (set before results):** XGBoost only if better on test PR-AUC **and** the paired-bootstrap 95 % CI of
  the difference excludes 0. Observed XGB − LR = −0.032, CI [−0.103, +0.043], P(XGB better) = 0.21
  → **Logistic Regression selected**. A non-linear model does not add measurable value on this dataset.
- **Class weighting** was a tuned option and lost for both models: unweighted models ranked better.
- **CV vs test gap** (0.665 → 0.581) is within the fold-to-fold variability (sd 0.07) of a 59-leaver test set.

### Design decision: interpretable LR variant (no MonthlyIncome)
The first SHAP review showed **higher income increasing risk** while JobLevel and SalaryRatioToLevel decreased it,
with offsetting signs caused by collinearity (income–JobLevel ρ = 0.92). We compared the two LR variants on
**training CV only**: without MonthlyIncome, CV PR-AUC was 0.665 vs 0.679, a gap smaller than one standard error
(0.022), so the simpler, explainable variant was kept. Pay is represented as seniority (JobLevel) × relative pay
(SalaryRatioToLevel). Agreement between LR and XGBoost feature rankings rose from ρ = 0.77 to **0.88**.

## 3. Calibration
The unweighted LR was already well calibrated. Sigmoid calibration changed little: Brier 0.0998 → 0.0998,
mean predicted 0.146 vs actual 0.160 on test. Scores can be read as approximate probabilities.

## 4. Operating threshold and risk bands
Chosen on **out-of-fold training predictions**, then applied unchanged to the test set.

| Cut-off | Rule | Test precision | Test recall | Share flagged |
|---|---|---|---|---|
| **0.14** (operating) | max F2 (recall weighted 2×) | 0.339 | **0.678** (40 of 59) | 32.1 % |
| 0.32 (High band) | lowest cut-off with train-OOF precision ≥ 60 % | 0.537 | 0.492 | 14.7 % |
| 0.50 (default, for reference) | — | 0.750 | 0.305 | 6.5 % |

**Why recall-oriented:** the intended use is a supportive check-in (stay interview, workload review). A missed
at-risk employee costs more than an unnecessary conversation. If the use case changed (e.g. costly interventions),
the threshold must be re-chosen.

Risk bands on all 1,470 employees (out-of-fold, each scored by a model that never saw them):

| Band | Rule | Employees | Actual leavers | Actual rate | Mean score |
|---|---|---|---|---|---|
| High | p ≥ 0.32 | 250 | 135 | 54.0 % | 0.51 |
| Elevated | 0.14 ≤ p < 0.32 | 317 | 52 | 16.4 % | 0.21 |
| Low | p < 0.14 | 903 | 50 | 5.5 % | 0.05 |

The High band holds 17 % of employees but 57 % of leavers. The Low band still contains 50 leavers: the model misses people.
Out-of-fold performance over all 1,470: PR-AUC 0.625, ROC-AUC 0.830.

## 5. Explainability (SHAP, test set)
Global importance, mean |SHAP| in log-odds: OverTime 0.62 · TotalWorkingYears 0.59 · StockOptionLevel 0.42 ·
EnvironmentSatisfaction 0.41 · YearsSinceLastPromotion 0.36 · JobInvolvement 0.33 · NumCompaniesWorked 0.32 ·
JobSatisfaction 0.32 · YearsWithCurrManager 0.28 · DistanceFromHome 0.27.

| Direction | Features |
|---|---|
| Push the score **up** | Overtime · fewer total working years · StockOptionLevel 0 · low environment/job satisfaction · low job involvement · longer time since promotion · more previous employers · longer commute · frequent travel · Laboratory Technician role |
| Push the score **down** | More experience · stock options · long time with the same manager · higher satisfaction/involvement |

Notes:
- **YearsSinceLastPromotion** had no univariate association (Phase 4) but matters **holding tenure constant**: among
  employees with similar tenure, a longer promotion gap is associated with higher risk. It overlaps with tenure
  variables, so treat it as a lead to investigate, not a finding.
- **StockOptionLevel** is a near-perfect proxy for marital status in this dataset (see `fairness_report.md`).
- Individual waterfalls: `figures/18_shap_waterfall_highest.png` (score 0.96, an employee who left: overtime, low
  involvement, early career) and `..._median.png` (score 0.07).
- Per-employee `TopRiskFactors` in the predictions file = the three largest positive SHAP contributions of the final model.

> **SHAP ≠ causation.** SHAP describes how the model uses features. It does not show that changing a feature would
> change whether a person stays.

## 6. Model sensitivity scenarios (for the Power BI simulator)
Final model, one input changed per scenario, everything else unchanged:

| Scenario | Employees affected | Mean score now → scenario | Sum of score changes |
|---|---|---|---|
| Overtime removed | 416 | 0.281 → 0.107 | −72.7 |
| Environment satisfaction +1 (from ≤ 2) | 571 | 0.202 → 0.163 | −22.7 |
| Job satisfaction +1 (from ≤ 2) | 569 | 0.201 → 0.164 | −20.8 |
| Work-life balance +1 (from ≤ 2) | 424 | 0.189 → 0.160 | −12.2 |
| Salary raised to ≥ 90 % of level median | 479 | 0.198 → 0.188 | −4.7 |

"Sum of score changes" is how much the **model's expected-leaver count** moves. It is **not** a number of
employees retained: the model learned associations, and overtime may stand in for workload or staffing problems
that would not vanish just because overtime is banned.

## 7. Limitations
- Fictional cross-sectional data with no time dimension: we cannot predict *when* someone leaves.
- 237 positives: subgroup metrics and the test estimate are noisy (59 test leavers; CV fold sd of PR-AUC ≈ 0.07).
- Satisfaction items are treated as numeric (equal spacing assumed).
- In a real deployment, monitor: input drift, calibration, PR-AUC/recall once outcomes are known, and the fairness metrics in Phase 6.

## 8. Artifacts
`models/attrition_model.joblib` (calibrated LR pipeline, refit on all data, git-ignored) · `models/model_config.json`
(parameters, threshold, bands, metrics, selection evidence) · MLflow runs: LR grid search, XGBoost grid search, final calibrated model.
