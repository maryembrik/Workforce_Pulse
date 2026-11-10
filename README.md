# Workforce Pulse — HR Attrition & Retention Insights

People Analytics · Predictive Analytics · Business Intelligence · Responsible AI

> Portfolio simulation built on the fictional **IBM HR Analytics Employee Attrition & Performance** dataset
> (1,470 employees, 35 columns). It is not a real HR system, and its findings do not describe any real organization.

**Status:** Phases 1–6 complete (data → SQL → EDA → model → fairness). Phase 7 (Power BI) and Phase 8 (management deck) in progress.

## Business problem
HR management wants to know how many employees leave, where attrition concentrates, which workforce characteristics
are associated with leaving, whether attrition risk can be estimated, and which retention scenarios are worth exploring.
See [docs/business_requirements.md](docs/business_requirements.md).

## Architecture
```
IBM HR CSV ─► Ingestion & quality (pandas) ─► Analytical layer (features, SQL: SQLite/PostgreSQL)
                                                    ├─► EDA & KPIs
                                                    └─► ML: LogReg vs XGBoost · SHAP · MLflow ─► Fairness audit
                                                                            └─► Power BI data pack ─► Dashboard & simulator
```

## Key results
| Question | Finding (association, not causation) |
|---|---|
| Attrition rate | **16.1 %** (237 / 1,470), historical snapshot |
| Where | Sales 20.6 % · HR 19.0 % (n = 63) · R&D 13.8 %, but R&D holds **56 %** of all leavers. Highest role rate: Sales Representatives 39.8 %. 70 % of leavers are Lab Technicians, Sales Executives or Research Scientists |
| When | **29.8 %** in the first 2 years vs 8.1 % after 11+ years |
| Overtime | **30.5 % vs 10.4 %** (2.9×). The gap holds within every department, income band and tenure band. New hires with overtime: 51 % |
| Satisfaction | Builds up: 11 % with no dimension at "low" → 29 % with two → 41 % with three |
| Pay | Driven mainly by entry level (JobLevel 1: 26 %). Paid < 90 % of level peers: 20 % vs ~14 % |
| Not supported | Promotion gap (alone), training, performance rating, salary hike, gender |
| Predictive model | Calibrated Logistic Regression, **test PR-AUC 0.58** (no-skill 0.16), ROC-AUC 0.80. XGBoost was not better (bootstrap CI of difference [−0.10, +0.04]). Recall 68 % at the selected threshold |
| Fairness | Gender: no disparity. MaritalStatus: StockOptionLevel encodes "Single" (every Single = level 0); removing it restores parity for −0.035 PR-AUC. Age: young stayers over-flagged, older leavers under-detected |

## Repository
| Path | Content |
|---|---|
| [notebooks/](notebooks/) | `01_data_understanding` → `02_data_preparation` → `03_exploratory_analysis` → `04_attrition_modeling` → `05_fairness_evaluation` |
| [src/](src/) | `data_dictionary.py` · `features.py` (cleaning, features, leakage-safe transformer) · `evaluation.py` · `load_db.py` · `export_powerbi.py` |
| [sql/](sql/) | `schema.sql` (PostgreSQL-compatible, with constraints + KPI view) · `hr_analysis.sql` (16 queries, window functions, CASE, UNION) |
| [reports/](reports/) | [data quality](reports/data_quality_report.md) · [SQL results](reports/sql_results.md) · [EDA findings](reports/eda_findings.md) · [model report](reports/model_report.md) · [fairness report](reports/fairness_report.md) · figures |
| [docs/](docs/) | [requirements](docs/business_requirements.md) · [feature dictionary](docs/feature_dictionary.md) · [KPI dictionary](docs/kpi_dictionary.md) · [plan](docs/project_plan_2_days.md) |
| [powerbi/](powerbi/) | [build guide](powerbi/POWERBI_GUIDE.md) · `measures.dax` · theme · data pack (generated) |
| [models/](models/) | `model_config.json` (parameters, threshold, metrics, selection evidence). The `.joblib` artifact is git-ignored |
| `tools/` | Notebook builders (notebooks are authored as Python for reviewable diffs), SQL runner |

## Methodology highlights
- **Leakage control:** all preprocessing, including the peer-salary feature, lives inside the sklearn pipeline and is refit per CV fold.
- **Decision rules set before results:** model selection (bootstrap CI), threshold (max F2 on training out-of-fold predictions only).
- **Interpretability over complexity:** the simpler model won. MonthlyIncome was dropped from the LR after SHAP revealed
  collinearity-driven sign flips; the decision was made on training CV, not on the test set.
- **Honest scores:** every employee in the export is scored by a model that never saw them (5-fold out-of-fold).
- **Responsible AI:** protected attributes excluded from features but audited, with a proxy analysis and a measured mitigation trade-off.

## Reproduce
```bash
python -m venv .venv
.venv\Scripts\activate                       # Windows
pip install -r requirements.txt
# put WA_Fn-UseC_-HR-Employee-Attrition.csv (Kaggle) in data/raw/
powershell tools\run_nb.ps1 tools\build_nb01.py notebooks\01_data_understanding.ipynb
powershell tools\run_nb.ps1 tools\build_nb02.py notebooks\02_data_preparation.ipynb
python -m src.load_db                        # SQLite; set DATABASE_URL for PostgreSQL
python tools\run_sql.py
powershell tools\run_nb.ps1 tools\build_nb03.py notebooks\03_exploratory_analysis.ipynb
powershell tools\run_nb.ps1 tools\build_nb04.py notebooks\04_attrition_modeling.ipynb
powershell tools\run_nb.ps1 tools\build_nb05.py notebooks\05_fairness_evaluation.ipynb
python -m src.export_powerbi
mlflow ui --backend-store-uri sqlite:///mlflow.db   # experiment history
```

## Limitations
Fictional cross-sectional data (no dates, so no time-to-leave). 237 positives, so subgroup estimates are uncertain. All
findings are associations. The model is a decision-support prototype and must not be used for individual employment
decisions (see [fairness report](reports/fairness_report.md) §5 for deployment prerequisites, including GDPR and the EU AI Act).
