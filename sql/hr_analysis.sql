-- =====================================================================
-- Workforce Pulse — HR analytical queries (Phase 3)
-- Portable SQL: PostgreSQL 14+ and SQLite 3.35+.
-- Each query starts with "-- name: <id>" so tools/run_sql.py can run and report it.
-- Rates are historical prevalence in this fictional snapshot, NOT annualized turnover.
-- =====================================================================

-- name: q00_kpi_summary
-- Business question Q1: headline workforce KPIs.
SELECT * FROM vw_workforce_kpis;

-- name: q01_total_employees
SELECT COUNT(*) AS total_employees FROM employees;

-- name: q02_employees_left
SELECT SUM(attrition_flag) AS employees_left FROM employees;

-- name: q03_overall_attrition_rate
SELECT ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2) AS attrition_rate_pct
FROM employees;

-- name: q04_attrition_by_department
-- Q2: always show the denominator next to the rate.
SELECT
    department,
    COUNT(*)                                          AS total_employees,
    SUM(attrition_flag)                               AS employees_left,
    ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2)  AS attrition_rate_pct,
    ROUND(100.0 * SUM(attrition_flag) / SUM(SUM(attrition_flag)) OVER (), 2) AS share_of_all_leavers_pct
FROM employees
GROUP BY department
ORDER BY attrition_rate_pct DESC;

-- name: q05_attrition_by_job_role
-- Q2: rate vs. volume — a role can have a high rate but few leavers.
SELECT
    job_role,
    department,
    COUNT(*)                                          AS total_employees,
    SUM(attrition_flag)                               AS employees_left,
    ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2)  AS attrition_rate_pct,
    RANK() OVER (ORDER BY 1.0 * SUM(attrition_flag) / COUNT(*) DESC) AS rate_rank,
    RANK() OVER (ORDER BY SUM(attrition_flag) DESC)                 AS volume_rank
FROM employees
GROUP BY job_role, department
ORDER BY attrition_rate_pct DESC;

-- name: q06_attrition_by_tenure_band
SELECT
    tenure_band,
    COUNT(*)                                          AS total_employees,
    SUM(attrition_flag)                               AS employees_left,
    ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2)  AS attrition_rate_pct
FROM employees
GROUP BY tenure_band
ORDER BY MIN(years_at_company);

-- name: q07_income_by_department
-- Compensation context: average pay, range, and leaver vs. stayer pay per department.
SELECT
    department,
    COUNT(*)                                                         AS total_employees,
    ROUND(AVG(monthly_income * 1.0), 0)                              AS avg_monthly_income,
    ROUND(AVG(CASE WHEN attrition_flag = 1 THEN monthly_income END), 0) AS avg_income_leavers,
    ROUND(AVG(CASE WHEN attrition_flag = 0 THEN monthly_income END), 0) AS avg_income_stayers,
    MIN(monthly_income)                                              AS min_income,
    MAX(monthly_income)                                              AS max_income
FROM employees
GROUP BY department
ORDER BY avg_monthly_income DESC;

-- name: q08_attrition_by_overtime
-- Q4: overtime vs. attrition.
SELECT
    over_time,
    COUNT(*)                                          AS total_employees,
    SUM(attrition_flag)                               AS employees_left,
    ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2)  AS attrition_rate_pct
FROM employees
GROUP BY over_time
ORDER BY over_time DESC;

-- name: q09_overtime_by_department
-- Q4 follow-up: where is overtime concentrated, and does the OT gap hold inside each department?
SELECT
    department,
    ROUND(100.0 * SUM(overtime_flag) / COUNT(*), 2)                               AS overtime_prevalence_pct,
    ROUND(100.0 * SUM(CASE WHEN overtime_flag = 1 THEN attrition_flag END)
                / NULLIF(SUM(overtime_flag), 0), 2)                               AS attrition_rate_ot_pct,
    ROUND(100.0 * SUM(CASE WHEN overtime_flag = 0 THEN attrition_flag END)
                / NULLIF(SUM(1 - overtime_flag), 0), 2)                           AS attrition_rate_no_ot_pct
FROM employees
GROUP BY department
ORDER BY overtime_prevalence_pct DESC;

-- name: q10_attrition_by_satisfaction
-- Q5: one long table across the four experience dimensions (1 = lowest level).
SELECT 'JobSatisfaction' AS dimension, job_satisfaction AS level, COUNT(*) AS total_employees,
       ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2) AS attrition_rate_pct
FROM employees GROUP BY job_satisfaction
UNION ALL
SELECT 'EnvironmentSatisfaction', environment_satisfaction, COUNT(*),
       ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2)
FROM employees GROUP BY environment_satisfaction
UNION ALL
SELECT 'RelationshipSatisfaction', relationship_satisfaction, COUNT(*),
       ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2)
FROM employees GROUP BY relationship_satisfaction
UNION ALL
SELECT 'WorkLifeBalance', work_life_balance, COUNT(*),
       ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2)
FROM employees GROUP BY work_life_balance
ORDER BY dimension, level;

-- name: q11_attrition_by_low_satisfaction_breadth
-- Q5: does attrition rise with the NUMBER of experience dimensions rated at the lowest level?
SELECT
    low_satisfaction_count,
    COUNT(*)                                          AS total_employees,
    SUM(attrition_flag)                               AS employees_left,
    ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2)  AS attrition_rate_pct
FROM employees
GROUP BY low_satisfaction_count
ORDER BY low_satisfaction_count;

-- name: q12_attrition_by_promotion_gap
-- Career progression indicator 1.
SELECT
    years_since_promotion_band,
    COUNT(*)                                          AS total_employees,
    SUM(attrition_flag)                               AS employees_left,
    ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2)  AS attrition_rate_pct
FROM employees
GROUP BY years_since_promotion_band
ORDER BY MIN(years_since_last_promotion);

-- name: q13_career_profile_leavers_vs_stayers
-- Career progression indicator 2: average career metrics by outcome.
SELECT
    attrition,
    COUNT(*)                                                 AS employees,
    ROUND(AVG(years_at_company * 1.0), 2)                    AS avg_years_at_company,
    ROUND(AVG(years_in_current_role * 1.0), 2)               AS avg_years_in_role,
    ROUND(AVG(years_since_last_promotion * 1.0), 2)          AS avg_years_since_promotion,
    ROUND(AVG(years_with_curr_manager * 1.0), 2)             AS avg_years_with_manager,
    ROUND(AVG(total_working_years * 1.0), 2)                 AS avg_total_working_years,
    ROUND(AVG(job_level * 1.0), 2)                           AS avg_job_level,
    ROUND(AVG(salary_ratio_to_level * 1.0), 3)               AS avg_salary_ratio_to_level
FROM employees
GROUP BY attrition;

-- name: q14_attrition_by_income_band
SELECT
    income_band,
    COUNT(*)                                          AS total_employees,
    SUM(attrition_flag)                               AS employees_left,
    ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2)  AS attrition_rate_pct
FROM employees
GROUP BY income_band
ORDER BY MIN(monthly_income);

-- name: q15_hotspots_role_x_overtime
-- Combined view: role x overtime cells with at least 30 employees (avoid tiny-cell noise).
SELECT
    job_role,
    over_time,
    COUNT(*)                                          AS total_employees,
    SUM(attrition_flag)                               AS employees_left,
    ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2)  AS attrition_rate_pct
FROM employees
GROUP BY job_role, over_time
HAVING COUNT(*) >= 30
ORDER BY attrition_rate_pct DESC
LIMIT 10;
