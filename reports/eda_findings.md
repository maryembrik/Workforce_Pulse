# Exploratory Analysis — Findings (Phase 4)

Source: `notebooks/03_exploratory_analysis.ipynb` · Figures: `reports/figures/03_*`–`11_*` · Driver table: `reports/eda_driver_screen.csv`
All findings are **associations in a fictional dataset**. Rates are historical prevalence. CIs are 95 % Wilson intervals.

## Executive summary
1. **Attrition is an early-career phenomenon.** 29.8 % of employees with 0–2 years' tenure left vs. 8.1 % with 11+ years.
   In years 0–1 it is 34–36 %.
2. **Overtime is the clearest working-condition signal.** 30.5 % vs 10.4 % (risk ratio 2.93, Cramér's V = 0.24).
   The gap persists **within every income band and every tenure band**, so it is not just "overtime workers are junior".
3. **Three roles account for 70 % of departures:** Laboratory Technicians (26.2 %), Sales Executives (24.1 %),
   Research Scientists (19.8 %). Sales Representatives have the highest rate (39.8 %) but a small headcount (n = 83).
4. **Low pay is associated with leaving, mostly through seniority.** Within the same JobLevel, the leaver/stayer pay gap
   is small, except at Level 1 (−10 %) and Level 4 (−19 %, only 5 leavers). Being paid < 90 % of level peers:
   20.1 % attrition vs ~14 % otherwise.
5. **Dissatisfaction accumulates.** No single satisfaction item is strong (V = 0.06–0.12), but attrition rises from
   11.1 % (no item at "low") to 28.9 % (two items at "low").
6. **The promotion-gap hypothesis is not supported.** YearsSinceLastPromotion has a negligible, non-significant association.

## 1. Workforce overview
| Metric | Value |
|---|---|
| Employees | 1,470 in 3 departments, 9 job roles |
| R&D share | 65.4 % of the workforce |
| Median age | 36 |
| Female share | 40.0 % |
| Median tenure | 5 years |
| Median monthly income | 4,919 (mean 6,503: right-skewed) |

## 2. Attrition — where it happens

| Department | n | Rate | 95 % CI | Share of leavers |
|---|---|---|---|---|
| Sales | 446 | 20.6 % | 17.1–24.6 % | 38.8 % |
| Human Resources | 63 | 19.0 % | 11.2–30.4 % | 5.1 % |
| R&D | 961 | 13.8 % | 11.8–16.2 % | **56.1 %** |

The HR interval (11.2–30.4 %) is so wide that HR cannot be called a "high-attrition department" with confidence.

| Job role | n | Rate | Share of leavers |
|---|---|---|---|
| Sales Representative | 83 | **39.8 %** | 13.9 % |
| Laboratory Technician | 259 | 23.9 % | **26.2 %** |
| Human Resources | 52 | 23.1 % | 5.1 % |
| Sales Executive | 326 | 17.5 % | 24.1 % |
| Research Scientist | 292 | 16.1 % | 19.8 % |
| Manufacturing Director | 145 | 6.9 % | 4.2 % |
| Healthcare Representative | 131 | 6.9 % | 3.8 % |
| Manager | 102 | 4.9 % | 2.1 % |
| Research Director | 80 | 2.5 % | 0.8 % |

**Business travel:** Non-travel 8.0 % → Rarely 15.0 % → Frequently 24.9 % (V = 0.13).

**Tenure:** New 29.8 % · Early 13.8 % · Mid 12.3 % · Long 8.1 %. By exact year: 0 → 36.4 % (n = 44), 1 → 34.5 % (n = 171),
2 → 21.3 %, then 10–17 % from year 3 onwards.

## 3. Compensation
- Median income: leavers 3,202 vs stayers 5,204 (rank-biserial r = 0.31, one of the strongest univariate signals).
- Income band: < 5k 21.8 % · 5–10k 11.1 % · 10–15k 13.5 % · 15k+ 3.8 %.
- **Controlled for seniority** (median income within JobLevel, leavers vs stayers):

| JobLevel | n | Level attrition | Leaver pay vs stayer pay |
|---|---|---|---|
| 1 | 543 | **26.3 %** | −10.4 % |
| 2 | 534 | 9.7 % | +0.2 % |
| 3 | 218 | 14.7 % | −1.0 % |
| 4 | 106 | 4.7 % | −19.1 % (5 leavers, unreliable) |
| 5 | 69 | 7.2 % | +1.8 % |

  → Most of the raw income effect is **the entry level (JobLevel 1) leaving more**, not pay differences between peers.
- **Peer positioning** (`SalaryRatioToLevel`): leavers' median 0.96 vs stayers' 1.01 (r = 0.11, p = 0.008, not significant
  after Bonferroni). < 90 % of peers: 20.1 % [16.7–23.9] vs 90–110 %: 14.7 % vs > 110 %: 13.5 %. A modest signal.

## 4. Satisfaction & working conditions
**Overtime (Q4):**

| | n | Rate |
|---|---|---|
| Overtime | 416 | **30.5 %** |
| No overtime | 1,054 | 10.4 % |

χ² = 87.6, p = 8e-21, Cramér's V = 0.244, risk ratio 2.93, +20.1 percentage points.

Controlled comparison — the overtime gap within each band:

| Income band | OT rate | No-OT rate | Ratio | | Tenure band | OT rate | No-OT rate | Ratio |
|---|---|---|---|---|---|---|---|---|
| < 5k | 42.9 % | 13.8 % | 3.1 | | New | **51.0 %** | 20.6 % | 2.5 |
| 5–10k | 21.4 % | 7.0 % | 3.1 | | Early | 28.4 % | 7.8 % | 3.6 |
| 10–15k | 17.3 % | 11.5 % | 1.5 | | Mid | 25.8 % | 7.3 % | 3.5 |
| 15k+ | 9.1 % | 2.0 % | 4.6 | | Long | 10.8 % | 7.2 % | 1.5 |

Half of new employees who work overtime left. This is the strongest combined risk pattern in the EDA.

**Satisfaction (Q5)**, rate at the lowest level vs the other levels:
- Environment satisfaction: Low 25.4 % vs 13.5–15.0 % (V = 0.12)
- Job satisfaction: Low 22.8 % → Very High 11.3 % (V = 0.11)
- Work-life balance: Bad 31.3 % (n = 80) vs 14–18 % (V = 0.11). Not monotonic: "Best" 17.6 % > "Better" 14.2 %.
- Relationship satisfaction: Low 20.7 % vs ~15 % (V = 0.06, not significant)
- Job involvement: V = 0.14 (significant)
- **Breadth of dissatisfaction** (items at level 1): 0 → 11.1 % · 1 → 18.3 % · 2 → 28.9 % · 3 → 40.7 % (n = 27)

## 5. Career development
- Leavers have shorter tenure (median 3 vs 6 years), less time in role (2 vs 3) and with their manager (2 vs 3),
  and fewer total working years (7 vs 10), all with r = 0.27–0.31.
- These variables overlap heavily (ρ 0.72–0.85) and with Age (TotalWorkingYears ρ = 0.66). They describe one
  underlying pattern: **less experienced, earlier-career employees leave more.**
- **Not supported:** YearsSinceLastPromotion (r = 0.08, n.s.), RoleShareOfTenure (r = 0.08, n.s.),
  TrainingTimesLastYear (r = 0.08, n.s.), NumCompaniesWorked (n.s.), PercentSalaryHike (n.s.), PerformanceRating (V ≈ 0).

## 6. Driver screen (univariate, |effect|)
| Tier | Variables |
|---|---|
| Medium (≈ 0.3) | TotalWorkingYears 0.31 · MonthlyIncome 0.31 · YearsAtCompany 0.30 |
| Small-medium (0.2–0.3) | YearsInCurrentRole 0.28 · YearsWithCurrManager 0.27 · *Age 0.27 (protected)* · OverTime 0.24 · JobRole 0.24 · SatisfactionIndex 0.23 · JobLevel 0.22 · StockOptionLevel 0.20 |
| Small (0.1–0.2) | *MaritalStatus 0.18 (protected)* · JobInvolvement 0.14 · BusinessTravel 0.13 · DistanceFromHome 0.12 · EnvironmentSatisfaction 0.12 · JobSatisfaction 0.11 · SalaryRatioToLevel 0.11 · WorkLifeBalance 0.11 · EducationField 0.10 |
| Negligible / n.s. | Department 0.09 · promotion gap · training · RelationshipSatisfaction · NumCompaniesWorked · Education · PercentSalaryHike · *Gender 0.03 (protected)* · undocumented rates · PerformanceRating |

**Notes for modelling and fairness**
- `Age` (0.27) and `MaritalStatus` (0.18) carry real signal. Excluding them costs some predictive power, and their
  information can partly come back through proxies (TotalWorkingYears, JobLevel, income; StockOptionLevel is
  plausibly linked to marital status). Phase 6 must check this.
- `Gender` shows no meaningful association (14.8 % F vs 17.0 % M, V = 0.03).
- `StockOptionLevel` (0.20) is a non-salary compensation signal worth watching in SHAP.

## 7. What EDA cannot tell us
- Causation: e.g. overtime may be a symptom of under-staffing that also drives exits.
- Timing: no dates, so we cannot see whether dissatisfaction came before leaving.
- Multivariate overlap: the screen is univariate. Phase 5 estimates joint contributions.
