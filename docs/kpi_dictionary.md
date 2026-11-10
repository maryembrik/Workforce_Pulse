# HR KPI Dictionary — Phase 3

One definition per KPI, used identically in SQL (`sql/schema.sql` → `vw_workforce_kpis`), Python and Power BI (DAX).
Values: `reports/sql_results.md` (query `q00_kpi_summary`).

| KPI | Definition | SQL | Value |
|---|---|---|---|
| Workforce size | Number of employee records | `COUNT(*)` | **1,470** |
| Attrition count | Employees with Attrition = Yes | `SUM(attrition_flag)` | **237** |
| Attrition rate | Attrition count / workforce size | `100.0 * SUM(attrition_flag) / COUNT(*)` | **16.12 %** |
| Retention rate | 100 % − attrition rate | `100 - attrition_rate` | **83.88 %** |
| Average tenure | Mean YearsAtCompany | `AVG(years_at_company)` | **7.01 years** |
| Average monthly income | Mean MonthlyIncome | `AVG(monthly_income)` | **6,503** |
| Overtime prevalence | Employees with OverTime = Yes / workforce size | `100.0 * SUM(overtime_flag) / COUNT(*)` | **28.30 %** |
| Group attrition rate | Leavers in group / employees in group (always reported **with n**) | `GROUP BY` + same formula | see `q04`–`q15` |
| Share of all leavers | Leavers in group / all leavers | window `SUM(SUM(..)) OVER ()` | e.g. R&D = 56.1 % |
| High-risk population | Employees with predicted probability ≥ selected threshold | Phase 5 output | defined in Phase 5 |

## Interpretation rules
1. **Historical ≠ future.** The data is one snapshot with no observation window. "Attrition rate" is the share of
   leavers in the sample, not annual turnover, and "retention rate" is not forward-looking retention.
2. **Rate and volume together.** HR has a 19.05 % rate but only 12 leavers. R&D has a lower rate (13.84 %) but
   133 leavers, i.e. 56 % of all departures. Prioritization needs both numbers.
3. **Predicted risk is a separate KPI.** The high-risk population comes from a model score, is threshold-dependent,
   and must never be presented as "employees who will leave".
4. **Small cells.** Groups below ~30 employees (e.g. `low_satisfaction_count` = 3 or 4, Managers in HR, n = 11)
   are shown but not used for conclusions.

## Headline SQL findings (descriptive, associations only)
- **Overtime:** 30.53 % attrition with overtime vs. 10.44 % without (≈ 2.9×). The gap holds **inside every department**
  (Sales 37.5 vs 13.8 %, R&D 27.3 vs 8.6 %, HR 29.4 vs 15.2 %), so it is not just a department-mix effect.
- **Tenure:** 29.82 % for 0–2 years vs. 8.13 % for 11+ years. Attrition concentrates early in the lifecycle.
- **Roles:** Sales Representatives have the highest rate (39.76 %, n = 83). Laboratory Technicians have the most
  leavers (62). Lab Technicians **with overtime**: 50.0 % (31 of 62).
- **Pay:** < 5k income band 21.76 % vs. 15k+ 3.76 %. Pay is strongly tied to JobLevel, so this partly reflects seniority.
- **Experience:** attrition rises with the number of experience dimensions at the lowest level: 11.05 % (none) →
  18.29 % (one) → 28.89 % (two) → 40.74 % (three, n = 27).
- **Promotion gap:** no clear pattern (16.95 % / 15.07 % / 14.23 %). The "stuck without promotion" hypothesis is
  **not supported** by this simple cut.
