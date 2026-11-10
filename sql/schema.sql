-- =====================================================================
-- Workforce Pulse — analytical schema
-- Target: PostgreSQL 14+. Also runs unchanged on SQLite 3.35+ (used locally).
-- Create the database first (PostgreSQL):  CREATE DATABASE workforce_pulse;
-- Load data with:  python -m src.load_db            (SQLite, default)
--                  DATABASE_URL=postgresql://user:pwd@localhost/workforce_pulse python -m src.load_db
-- =====================================================================

DROP VIEW IF EXISTS vw_workforce_kpis;
DROP TABLE IF EXISTS employees;

CREATE TABLE employees (
    -- identifier
    employee_number              INTEGER      PRIMARY KEY,

    -- target
    attrition                    VARCHAR(3)   NOT NULL CHECK (attrition IN ('Yes', 'No')),
    attrition_flag               SMALLINT     NOT NULL CHECK (attrition_flag IN (0, 1)),

    -- workforce profile (age, gender, marital_status are PROTECTED: audit only)
    age                          SMALLINT     NOT NULL CHECK (age BETWEEN 16 AND 80),
    gender                       VARCHAR(10)  NOT NULL,
    marital_status               VARCHAR(10)  NOT NULL,
    education                    SMALLINT     NOT NULL CHECK (education BETWEEN 1 AND 5),
    education_field              VARCHAR(30)  NOT NULL,

    -- organizational
    department                   VARCHAR(30)  NOT NULL,
    job_role                     VARCHAR(30)  NOT NULL,
    job_level                    SMALLINT     NOT NULL CHECK (job_level BETWEEN 1 AND 5),

    -- compensation
    monthly_income               INTEGER      NOT NULL CHECK (monthly_income > 0),
    daily_rate                   INTEGER,     -- undocumented, not used in analysis
    hourly_rate                  INTEGER,     -- undocumented, not used in analysis
    monthly_rate                 INTEGER,     -- undocumented, not used in analysis
    stock_option_level           SMALLINT     NOT NULL CHECK (stock_option_level BETWEEN 0 AND 3),
    percent_salary_hike          SMALLINT     NOT NULL,

    -- satisfaction (1 = Low .. 4 = Very High; work_life_balance 1 = Bad .. 4 = Best)
    environment_satisfaction     SMALLINT     NOT NULL CHECK (environment_satisfaction BETWEEN 1 AND 4),
    job_involvement              SMALLINT     NOT NULL CHECK (job_involvement BETWEEN 1 AND 4),
    job_satisfaction             SMALLINT     NOT NULL CHECK (job_satisfaction BETWEEN 1 AND 4),
    relationship_satisfaction    SMALLINT     NOT NULL CHECK (relationship_satisfaction BETWEEN 1 AND 4),
    work_life_balance            SMALLINT     NOT NULL CHECK (work_life_balance BETWEEN 1 AND 4),

    -- work conditions
    over_time                    VARCHAR(3)   NOT NULL CHECK (over_time IN ('Yes', 'No')),
    overtime_flag                SMALLINT     NOT NULL CHECK (overtime_flag IN (0, 1)),
    business_travel              VARCHAR(20)  NOT NULL,
    distance_from_home           SMALLINT     NOT NULL CHECK (distance_from_home >= 0),

    -- performance
    performance_rating           SMALLINT     NOT NULL CHECK (performance_rating BETWEEN 1 AND 4),

    -- career development
    num_companies_worked         SMALLINT     NOT NULL CHECK (num_companies_worked >= 0),
    total_working_years          SMALLINT     NOT NULL CHECK (total_working_years >= 0),
    training_times_last_year     SMALLINT     NOT NULL CHECK (training_times_last_year >= 0),
    years_at_company             SMALLINT     NOT NULL CHECK (years_at_company >= 0),
    years_in_current_role        SMALLINT     NOT NULL CHECK (years_in_current_role >= 0),
    years_since_last_promotion   SMALLINT     NOT NULL CHECK (years_since_last_promotion >= 0),
    years_with_curr_manager      SMALLINT     NOT NULL CHECK (years_with_curr_manager >= 0),

    -- engineered (see docs/feature_dictionary.md)
    tenure_band                  VARCHAR(20)  NOT NULL,
    age_band                     VARCHAR(10)  NOT NULL,
    income_band                  VARCHAR(10)  NOT NULL,
    satisfaction_index           NUMERIC(6,4) NOT NULL CHECK (satisfaction_index BETWEEN 0 AND 1),
    low_satisfaction_count       SMALLINT     NOT NULL CHECK (low_satisfaction_count BETWEEN 0 AND 4),
    role_share_of_tenure         NUMERIC(6,4) NOT NULL CHECK (role_share_of_tenure BETWEEN 0 AND 1),
    years_since_promotion_band   VARCHAR(10)  NOT NULL,
    job_level_median_income      NUMERIC(10,2) NOT NULL,
    salary_ratio_to_level        NUMERIC(6,4) NOT NULL,

    -- business-rule integrity (validated in Phase 1)
    CHECK (years_in_current_role   <= years_at_company),
    CHECK (years_with_curr_manager <= years_at_company),
    CHECK (years_at_company        <= total_working_years)
);

CREATE INDEX ix_employees_department ON employees (department);
CREATE INDEX ix_employees_job_role   ON employees (job_role);

-- One-row KPI view, reusable by BI tools.
CREATE VIEW vw_workforce_kpis AS
SELECT
    COUNT(*)                                                    AS workforce_size,
    SUM(attrition_flag)                                         AS attrition_count,
    ROUND(100.0 * SUM(attrition_flag) / COUNT(*), 2)            AS attrition_rate_pct,
    ROUND(100.0 - 100.0 * SUM(attrition_flag) / COUNT(*), 2)    AS retention_rate_pct,
    ROUND(AVG(years_at_company * 1.0), 2)                       AS avg_tenure_years,
    ROUND(AVG(monthly_income * 1.0), 0)                         AS avg_monthly_income,
    ROUND(100.0 * SUM(overtime_flag) / COUNT(*), 2)             AS overtime_prevalence_pct
FROM employees;
