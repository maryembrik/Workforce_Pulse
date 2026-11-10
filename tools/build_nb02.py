import sys
from nbbuild import Notebook, SETUP

nb = Notebook()
nb.md("""
# 02 — Data Preparation & Feature Engineering
**Workforce Pulse · Phase 2**

**Objective.** Turn the validated raw extract into two analytical datasets:

| File | Content | Used by |
|---|---|---|
| `data/processed/hr_cleaned.csv` | Raw columns minus constants, trimmed text, binary flags | SQL (Phase 3), audit |
| `data/processed/hr_featured.csv` | Cleaned + engineered business features | EDA, Power BI, modelling |

All logic lives in `src/features.py` so the notebook, the model pipeline and any future refresh use **the same code**.

**Leakage rule.** Row-wise features (bands, flags, indices) only use the employee's own record → safe to compute on
the full dataset. The peer-referenced salary ratio uses *other* employees → computed on the full data here for
**descriptive** use only; the model learns it from the training split inside the pipeline (`PeerSalaryRatio`).
""")
nb.md("## 0. Setup")
nb.code(SETUP + """
from src.features import (clean, add_row_features, add_peer_salary_ratio, CONSTANT_COLS,
                          UNDOCUMENTED_RATE_COLS, SATISFACTION_ITEMS, MODEL_NUMERIC, MODEL_CATEGORICAL)
from src.data_dictionary import PROTECTED, ID_COL

raw = pd.read_csv(DATA / "raw" / "WA_Fn-UseC_-HR-Employee-Attrition.csv", encoding="utf-8-sig")
raw.shape
""")

nb.md("""
## 1. Cleaning
Phase 1 found no missing values, duplicates or invalid codes, so cleaning is deliberately light. We still apply each
step **defensively** so a future extract with problems would be handled by the same code.

| Step | Why |
|---|---|
| Trim text values | Protects joins / group-bys from `"Sales "` vs `"Sales"` |
| Drop `EmployeeCount`, `Over18`, `StandardHours` | Constant (Phase 1 evidence) |
| Drop exact duplicates | Defensive (0 found) |
| `AttritionFlag` = 1 if Attrition = Yes | Numeric target for SQL sums and models |
| `OvertimeFlag` = 1 if OverTime = Yes | Numeric indicator for KPIs |
""")
nb.code("""
cleaned = clean(raw)
print("Shape before:", raw.shape, "-> after:", cleaned.shape)
print("Dropped columns:", sorted(set(raw.columns) - set(cleaned.columns)))
print("Added columns:  ", sorted(set(cleaned.columns) - set(raw.columns)))
""")
nb.code("""
# Validation: flags must agree exactly with their source columns
assert (cleaned.AttritionFlag == (cleaned.Attrition == "Yes")).all()
assert (cleaned.OvertimeFlag == (cleaned.OverTime == "Yes")).all()
assert cleaned[ID_COL].is_unique and cleaned.isna().sum().sum() == 0
print("Attrition count:", cleaned.AttritionFlag.sum(), "| Overtime count:", cleaned.OvertimeFlag.sum())
""")

nb.md("""
## 2. Feature engineering
Each feature answers a business question from `docs/business_requirements.md`. Full definitions are in
`docs/feature_dictionary.md`.

### A. Tenure band — *Where in the employee lifecycle does attrition concentrate?*
### B. Age band — *EDA and fairness audit only, never a model feature*
### C. Income band — *Management-friendly salary slabs for reporting*
### D. Satisfaction index — *One experience score for dashboards*
The four items (Job, Environment, Relationship satisfaction, Work-life balance) are all 1–4 scales, so they are already
comparable; we average them and rescale to 0–1. **Equal weighting is a design assumption**, not a validated instrument.
`LowSatisfactionCount` counts how many of the four items are at the lowest level (1).
### E. Career progression — *Are people stuck?*
`RoleShareOfTenure` = YearsInCurrentRole / YearsAtCompany (defined as 1.0 when tenure is 0, i.e. first role).
`YearsSincePromotionBand` groups promotion gaps into 0–1, 2–4, 5+ years.
### F. Salary relative to JobLevel peers — *Is the employee paid below comparable colleagues?*
We compare with the **median of the same JobLevel**, not the department average: Phase 1 showed JobLevel and income
are almost the same signal (ρ = 0.92), so a department average mostly measures seniority mix. A ratio of 0.8 means
"earns 20 % less than the typical employee at the same level". Median is used because income is right-skewed.
""")
nb.code("""
featured = add_peer_salary_ratio(add_row_features(cleaned))
new_cols = [c for c in featured.columns if c not in cleaned.columns]
featured[new_cols].head()
""")

nb.md("## 3. Validate engineered features")
nb.code("""
# Bands must cover every employee (no NaN from pd.cut edges)
for c in ["TenureBand", "AgeBand", "IncomeBand", "YearsSincePromotionBand"]:
    assert featured[c].notna().all(), c
    print(f"{c:24s}", featured[c].value_counts(sort=False).to_dict())
""")
nb.code("""
# Bands must agree with their source ranges
chk = featured.groupby("TenureBand", observed=True)["YearsAtCompany"].agg(["min", "max", "count"])
display(chk)
featured.groupby("IncomeBand", observed=True)["MonthlyIncome"].agg(["min", "max", "count"])
""")
nb.code("""
# Index ranges
desc = featured[["SatisfactionIndex", "LowSatisfactionCount", "RoleShareOfTenure", "SalaryRatioToLevel"]].describe().T
assert featured.SatisfactionIndex.between(0, 1).all()
assert featured.RoleShareOfTenure.between(0, 1).all()
desc
""")
nb.code("""
# Peer medians used (descriptive version, full dataset)
featured.groupby("JobLevel")["MonthlyIncome"].agg(n="count", median="median", min="min", max="max")
""")
nb.code("""
# Does the salary ratio add information beyond JobLevel / MonthlyIncome? (low correlation with JobLevel = good)
featured[["SalaryRatioToLevel", "MonthlyIncome", "JobLevel", "TotalWorkingYears", "Age"]].corr(method="spearman").round(2)
""")
nb.code("""
fig, axes = plt.subplots(1, 3, figsize=(14, 3.6))
sns.histplot(featured.SatisfactionIndex, bins=13, ax=axes[0]); axes[0].set_title("Satisfaction index (0-1)")
sns.histplot(featured.RoleShareOfTenure, bins=20, ax=axes[1]); axes[1].set_title("Share of tenure in current role")
sns.histplot(featured.SalaryRatioToLevel, bins=30, ax=axes[2]); axes[2].set_title("Salary / JobLevel median")
plt.tight_layout(); plt.savefig(FIG_DIR / "02_engineered_features.png", dpi=150); plt.show()
""")

nb.md("""
## 4. Model feature set
What enters the model (Phase 5) and what is deliberately left out.
""")
nb.code("""
excluded = {
    "identifier": [ID_COL],
    "protected (audit only)": PROTECTED + ["AgeBand"],
    "undocumented rates": UNDOCUMENTED_RATE_COLS,
    "target / target-derived": ["Attrition", "AttritionFlag"],
    "duplicate encodings / reporting-only": ["OvertimeFlag", "TenureBand", "IncomeBand", "YearsSincePromotionBand",
                                              "SatisfactionIndex", "LowSatisfactionCount", "JobLevelMedianIncome",
                                              "SalaryRatioToLevel (recomputed in-pipeline)"],
}
for k, v in excluded.items():
    print(f"{k:38s} {v}")
print(f"\\nModel numeric ({len(MODEL_NUMERIC)}) + SalaryRatioToLevel:", MODEL_NUMERIC)
print(f"Model categorical ({len(MODEL_CATEGORICAL)}):", MODEL_CATEGORICAL)
assert not set(PROTECTED) & set(MODEL_NUMERIC + MODEL_CATEGORICAL)
""")

nb.md("## 5. Save outputs")
nb.code("""
(DATA / "processed").mkdir(parents=True, exist_ok=True)
cleaned.to_csv(DATA / "processed" / "hr_cleaned.csv", index=False)
featured.to_csv(DATA / "processed" / "hr_featured.csv", index=False)
print("hr_cleaned.csv ", cleaned.shape)
print("hr_featured.csv", featured.shape)
""")
nb.save(sys.argv[1])
