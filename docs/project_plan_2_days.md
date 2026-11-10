# Workforce Pulse — 2-Day Delivery Plan

The original roadmap had 8 phases over 5 days (~25–30 h). To deliver in **2 days (~2 × 9 h)** without
lowering the quality bar, we keep every phase but cut scope *inside* each phase, not the phases themselves.

## Scope decisions (what changes vs. the 5-day plan)

| Area | 5-day plan | 2-day plan | Why it's still defensible |
|---|---|---|---|
| Notebooks | 5 notebooks | 4 notebooks (fairness merged into modeling) | Same analysis, less file overhead |
| `src/` modules | 5 modules | 2 modules (`features.py`, `evaluation.py`) | Only what the notebooks reuse |
| SQL | PostgreSQL install + schema | Portable SQL, run on SQLite; `schema.sql` written for PostgreSQL | PostgreSQL is not installed on this machine; queries are standard SQL and run unchanged on both |
| Models | LR + XGBoost + tuning | LR + XGBoost, small CV grid each | Comparison is the point, not exhaustive tuning |
| MLflow | Full tracking + registry | Local `mlruns/` tracking of params & metrics only | Reproducibility shown, no infra |
| Fairness | Separate report + CIs | Gender / Age-band / MaritalStatus audit with Wilson CIs, short markdown report | Core message intact |
| Power BI | 3 pages, drill-through | 3 pages, What-if params; drill-through only if time allows | Simulator page is the differentiator |
| Deck | 5 slides | 5 slides | Unchanged |

## Day 1 — Data → Insight (≈ 9 h)

| Block | Time | Phase | Output |
|---|---|---|---|
| 1 | 1.5 h | **P1** Business understanding & data profiling | `01_data_understanding.ipynb`, `reports/data_quality_report.md` |
| 2 | 2 h | **P2** Cleaning & feature engineering | `02_data_preparation.ipynb`, `hr_cleaned.csv`, `hr_featured.csv`, `docs/feature_dictionary.md` |
| 3 | 1.5 h | **P3** SQL KPIs | `sql/schema.sql`, `sql/hr_analysis.sql`, `docs/kpi_dictionary.md` |
| 4 | 3 h | **P4** EDA (5 dimensions) | `03_exploratory_analysis.ipynb`, `reports/figures/*.png`, `reports/eda_findings.md` |
| 5 | 1 h | Buffer / review | Every finding traced to a number |

## Day 2 — Model → Decision (≈ 9 h)

| Block | Time | Phase | Output |
|---|---|---|---|
| 1 | 3 h | **P5** LR vs XGBoost, threshold, SHAP, MLflow | `04_attrition_modeling.ipynb`, `employee_attrition_predictions.csv` |
| 2 | 1 h | **P6** Fairness audit | `reports/fairness_report.md` |
| 3 | 3 h | **P7** Power BI (3 pages) | `powerbi/Workforce_Pulse.pbix`, screenshots |
| 4 | 1.5 h | **P8** 5-slide deck + recommendations | `reports/management_summary.pptx/pdf` |
| 5 | 0.5 h | README + final QA | `README.md` |

## Non-negotiable rules (unchanged)
- No invented results — every number in the README/deck comes from a notebook output.
- Accuracy is never the headline metric (majority baseline ≈ 83.9 %).
- Protected attributes (Age, Gender, MaritalStatus) excluded from features, kept only for auditing.
- SHAP = attribution, not causation. Simulator = sensitivity analysis, not "employees saved".
- Fictional IBM data — no claim about real workforce behaviour, and no claim about DHL.

## Biggest schedule risks
1. **Power BI** is the most time-hungry, least automatable piece → start it no later than early afternoon of Day 2.
2. **Environment** (`xgboost`, `shap`, `mlflow` on Python 3.13) → install on Day 1 morning, not Day 2.
