# Feature Dictionary — Phase 2

Code: `src/features.py` · Notebook: `notebooks/02_data_preparation.ipynb` · Output: `data/processed/hr_featured.csv` (1,470 × 43)

## Cleaning outputs (`hr_cleaned.csv`, 1,470 × 34)

| Feature | Formula | Type | In model | Notes |
|---|---|---|---|---|
| `AttritionFlag` | 1 if `Attrition` = "Yes" else 0 | int | **Target** | 237 ones |
| `OvertimeFlag` | 1 if `OverTime` = "Yes" else 0 | int | No (model uses `OverTime` one-hot, same info) | 416 ones; for SQL/DAX sums |
| *(dropped)* | `EmployeeCount`, `Over18`, `StandardHours` | — | — | Constant |

## Engineered features

| Feature | Formula | Business interpretation | Type | In model | Known limitations |
|---|---|---|---|---|---|
| `TenureBand` | `YearsAtCompany` cut at 0–2 / 3–5 / 6–10 / 11+ → New, Early, Mid, Long | Lifecycle stage | category | No (raw years used) | Band edges are a convention. Counts: 342 / 434 / 448 / 246 |
| `AgeBand` | `Age` cut at <25, 25–34, 35–44, 45–54, 55+ | Demographic group | category | **Never** (protected) | Audit/EDA only. Smallest groups: Under 25 = 97, 55+ = 69 |
| `IncomeBand` | `MonthlyIncome` in [0,5k), [5k,10k), [10k,15k), 15k+ | Salary slab for reporting | category | No | Currency/period not documented by IBM |
| `SatisfactionIndex` | (mean of JobSat, EnvSat, RelSat, WLB − 1) / 3 | Overall employee experience, 0 = all "low", 1 = all "best" | float 0–1 | No (components used) | **Equal weights are an assumption**, not a validated scale. WLB labels (Bad…Best) differ from the satisfaction labels |
| `LowSatisfactionCount` | Number of the 4 items at level 1 | Breadth of dissatisfaction | int 0–4 | No | Same assumption |
| `RoleShareOfTenure` | `YearsInCurrentRole / YearsAtCompany`; 1.0 when tenure = 0 | Share of company time spent in the current role (high = little internal movement) | float 0–1 | **Yes** | For new hires it is trivially 1.0. Interpret together with tenure |
| `YearsSincePromotionBand` | `YearsSinceLastPromotion` cut at 0–1 / 2–4 / 5+ | Promotion gap | category | No (raw years used) | Counts 938 / 272 / 260 |
| `JobLevelMedianIncome` | Median `MonthlyIncome` of the employee's JobLevel | Peer reference pay | float | No | Computed on all 1,470 rows (descriptive use) |
| `SalaryRatioToLevel` | `MonthlyIncome / JobLevelMedianIncome` | Pay vs. same-level peers (0.8 = 20 % below typical peer) | float | **Yes**, recomputed in-pipeline from **training data only** (`PeerSalaryRatio`) to prevent leakage | JobLevel is a coarse peer group (no role/location). Spearman ρ with JobLevel = −0.06 → adds information beyond seniority |

### Design decision: JobLevel peers instead of department average
The original plan proposed salary relative to the **department** average. Phase 1 showed JobLevel and MonthlyIncome
are almost the same signal (ρ = 0.92). A department average mixes juniors and seniors, so "below department average"
mostly means "junior". Comparing with the **median of the same JobLevel** isolates pay positioning from seniority.
The median is used because income is right-skewed (mean 6,503 vs median 4,919).

## Model feature set (Phase 5)

**Numeric (21):** DistanceFromHome, Education, EnvironmentSatisfaction, JobInvolvement, JobLevel, JobSatisfaction,
MonthlyIncome, NumCompaniesWorked, PercentSalaryHike, PerformanceRating, RelationshipSatisfaction, StockOptionLevel,
TotalWorkingYears, TrainingTimesLastYear, WorkLifeBalance, YearsAtCompany, YearsInCurrentRole,
YearsSinceLastPromotion, YearsWithCurrManager, RoleShareOfTenure, SalaryRatioToLevel (in-pipeline).

**Categorical (5, one-hot):** BusinessTravel, Department, EducationField, JobRole, OverTime.

**Excluded:** EmployeeNumber (ID) · Age, Gender, MaritalStatus, AgeBand (protected, audit only) ·
DailyRate, HourlyRate, MonthlyRate (undocumented, ρ≈0 with pay) · reporting-only bands and indices (duplicate encodings).

> Satisfaction items enter the model as their original 1–4 codes (treated as numeric). This assumes roughly equal
> spacing between levels, which is a common, documented simplification for Likert-type items.
