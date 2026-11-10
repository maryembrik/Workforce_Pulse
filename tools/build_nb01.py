import sys
import nbformat as nbf

out_path = sys.argv[1]
nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: C.append(nbf.v4.new_code_cell(s.strip()))

md("""
# 01 — Data Understanding
**Workforce Pulse · Phase 1 · HR Attrition & Retention Insights**

**Objective.** Understand the IBM HR dataset *before* writing any transformation or modeling code:
its structure, data quality, target balance and the business meaning of every column.

**Business context (simulation).** We act as a Data Analyst in a People Data & Systems team.
HR management wants to understand attrition and explore retention strategies
(see `docs/business_requirements.md`, questions Q1–Q7).

> ⚠️ The IBM dataset is **fictional**, created by IBM data scientists for demonstration. Nothing here
> describes the behaviour of a real workforce.

**Outputs of this notebook**
- Dataset profile (shape, types, missing, duplicates, cardinality)
- Target distribution and the "accuracy trap" baseline
- Constant / identifier / protected column detection
- Domain validity and logical consistency checks
- `reports/data_quality_table.csv` → basis for `reports/data_quality_report.md`
""")

md("## 0. Setup")
code("""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))
from src.data_dictionary import COLUMNS, ORDINAL_LABELS, PROTECTED, TARGET, ID_COL

RAW_PATH = PROJECT_ROOT / "data" / "raw" / "WA_Fn-UseC_-HR-Employee-Attrition.csv"
FIG_DIR = PROJECT_ROOT / "reports" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 200)
sns.set_theme(style="whitegrid")
print("Project root:", PROJECT_ROOT)
""")

md("""
## 1. Load the CSV
The file starts with a UTF-8 byte-order mark (BOM). Reading it with plain `utf-8` would silently rename
the first column to `\\ufeffAge`, so we use `utf-8-sig`. This is a small but real data-ingestion detail.
""")
code("""
df = pd.read_csv(RAW_PATH, encoding="utf-8-sig")
assert df.columns[0] == "Age", f"Unexpected first column: {df.columns[0]!r}"
print("Loaded:", RAW_PATH.name)
""")

md("## 2. First and last records")
code("df.head()")
code("df.tail()")

md("## 3. Dimensions\nExpected from the documentation: **1,470 rows × 35 columns**.")
code("""
n_rows, n_cols = df.shape
print(f"Rows: {n_rows:,}  |  Columns: {n_cols}")
assert (n_rows, n_cols) == (1470, 35), "Dataset does not match the documented shape"
""")

md("""
## 4. Numerical vs categorical columns
Note: several *numeric* columns are actually **ordinal survey scales** (1–4 or 1–5), e.g. `JobSatisfaction`.
Storing them as integers is fine, but we must not interpret their distances as exact quantities.
""")
code("""
cat_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
num_cols = df.select_dtypes(include="number").columns.tolist()
ord_cols = list(ORDINAL_LABELS)
print(f"Categorical ({len(cat_cols)}):", cat_cols)
print(f"\\nNumerical ({len(num_cols)}):", num_cols)
print(f"\\n  of which documented ordinal scales ({len(ord_cols)}):", ord_cols)
""")

md("## 5. Data types")
code("df.info()")
code("df.describe().T")
code("df.describe(include=['object', 'string']).T")

md("## 6. Missing values")
code("""
missing = df.isna().sum()
print("Total missing cells:", int(missing.sum()))
missing[missing > 0]
""")
code("""
# Also check for 'disguised' missing values in text columns (empty strings, 'NA', '?', whitespace)
suspicious = {c: df[c].str.strip().isin(["", "NA", "N/A", "?", "null", "None"]).sum() for c in cat_cols}
{k: int(v) for k, v in suspicious.items() if v > 0} or "No disguised missing values found"
""")

md("""
## 7. Duplicates
Two checks: fully duplicated rows, and duplicated employee identifiers (a duplicated ID with different values
would be a more serious integrity problem than an exact duplicate row).
""")
code("""
print("Fully duplicated rows:          ", int(df.duplicated().sum()))
print("Duplicated EmployeeNumber values:", int(df[ID_COL].duplicated().sum()))
print("Duplicates ignoring the ID column:", int(df.drop(columns=ID_COL).duplicated().sum()))
""")

md("## 8. Unique values")
code("""
nunique = df.nunique().sort_values()
nunique.to_frame("n_unique").T
""")
code("""
for c in cat_cols:
    print(f"{c:15s}", df[c].value_counts().to_dict())
""")

md("""
## 9. Target distribution
Expected from documentation: 237 Yes / 1,233 No (~16.1%).

**Why this matters.** With a ~16% positive class, a model that predicts *"everyone stays"* is right
~84% of the time while detecting **zero** leavers. That is why accuracy will not be our main metric in Phase 5.
""")
code("""
target_counts = df[TARGET].value_counts()
target_pct = df[TARGET].value_counts(normalize=True).mul(100).round(2)
target_summary = pd.DataFrame({"count": target_counts, "percent": target_pct})
display(target_summary)

attrition_rate = (df[TARGET] == "Yes").mean()
print(f"Historical attrition rate:          {attrition_rate:.2%}")
print(f"Majority-class ('No') baseline acc.: {1 - attrition_rate:.2%}  <- accuracy trap")
print(f"No-skill PR-AUC baseline:            {attrition_rate:.3f}")
assert target_counts.to_dict() == {"No": 1233, "Yes": 237}
""")
code("""
fig, ax = plt.subplots(figsize=(6, 3.5))
order = ["No", "Yes"]
sns.countplot(data=df, x=TARGET, order=order, hue=TARGET, hue_order=order,
              palette=["#4C72B0", "#DD8452"], legend=False, ax=ax)
for p, lab in zip(ax.patches, order):
    ax.annotate(f"{target_counts[lab]:,}\\n({target_pct[lab]:.1f}%)",
                (p.get_x() + p.get_width() / 2, p.get_height()), ha="center", va="bottom", fontsize=10)
ax.set_title("Attrition distribution (historical, IBM fictional data)")
ax.set_xlabel("Attrition"); ax.set_ylabel("Employees")
ax.set_ylim(0, target_counts.max() * 1.18)
plt.tight_layout()
plt.savefig(FIG_DIR / "01_target_distribution.png", dpi=150)
plt.show()
""")

md("""
## 10. Constant, identifier and irrelevant variables
We detect these **programmatically** rather than trusting the documentation.
""")
code("""
constant_cols = [c for c in df.columns if df[c].nunique(dropna=False) == 1]
id_like_cols = [c for c in df.columns if df[c].nunique() == len(df)]
print("Constant columns:", {c: df[c].iloc[0] for c in constant_cols})
print("Identifier-like columns (unique per row):", id_like_cols)
""")
code("""
# Near-constant: a single value dominates. Not automatically excluded, but worth noting.
dominance = df.apply(lambda s: s.value_counts(normalize=True).iloc[0])
dominance[(dominance >= 0.80) & (dominance < 1)].sort_values(ascending=False).round(3).to_frame("top_value_share")
""")
code("""
# PerformanceRating is documented on a 1-4 scale. Which values are actually used?
df["PerformanceRating"].value_counts().sort_index()
""")

md("""
## 11. Domain validity
Ordinal scales must stay within their documented ranges, and numeric values should be plausible.
""")
code("""
domain_issues = {}
for col, labels in ORDINAL_LABELS.items():
    bad = ~df[col].isin(labels.keys())
    if bad.any():
        domain_issues[col] = int(bad.sum())
print("Out-of-range ordinal values:", domain_issues or "none")

non_negative = ["DistanceFromHome", "MonthlyIncome", "NumCompaniesWorked", "TotalWorkingYears",
                "TrainingTimesLastYear", "YearsAtCompany", "YearsInCurrentRole",
                "YearsSinceLastPromotion", "YearsWithCurrManager", "PercentSalaryHike"]
print("Negative values:", {c: int((df[c] < 0).sum()) for c in non_negative if (df[c] < 0).any()} or "none")
print("Age range:", df["Age"].min(), "-", df["Age"].max())
""")

md("""
## 12. Logical consistency between tenure variables
Business rules that must hold in a coherent HR record:
1. `YearsInCurrentRole ≤ YearsAtCompany`
2. `YearsWithCurrManager ≤ YearsAtCompany`
3. `YearsSinceLastPromotion ≤ YearsAtCompany`
4. `YearsAtCompany ≤ TotalWorkingYears`
5. `Age − TotalWorkingYears ≥ 14` (plausible working start age)
""")
code("""
rules = {
    "YearsInCurrentRole <= YearsAtCompany": df.YearsInCurrentRole <= df.YearsAtCompany,
    "YearsWithCurrManager <= YearsAtCompany": df.YearsWithCurrManager <= df.YearsAtCompany,
    "YearsSinceLastPromotion <= YearsAtCompany": df.YearsSinceLastPromotion <= df.YearsAtCompany,
    "YearsAtCompany <= TotalWorkingYears": df.YearsAtCompany <= df.TotalWorkingYears,
    "Age - TotalWorkingYears >= 14": (df.Age - df.TotalWorkingYears) >= 14,
}
consistency = pd.DataFrame({"violations": {k: int((~v).sum()) for k, v in rules.items()}})
consistency
""")
code("""
# NumCompaniesWorked = 0 while TotalWorkingYears > YearsAtCompany is a known ambiguity in this dataset:
# does 0 mean "this is the first employer" or is it a coding quirk? We document, we don't 'fix'.
ambiguous = df[(df.NumCompaniesWorked == 0) & (df.TotalWorkingYears > df.YearsAtCompany)]
print("NumCompaniesWorked==0 but prior experience exists:", len(ambiguous))
""")

md("""
## 13. Undocumented compensation columns
`DailyRate`, `HourlyRate` and `MonthlyRate` have no documented definition. If they were genuine pay measures,
they should correlate with `MonthlyIncome` and `JobLevel`. We test that before deciding whether they belong in the model.
""")
code("""
comp = ["MonthlyIncome", "DailyRate", "HourlyRate", "MonthlyRate", "JobLevel", "TotalWorkingYears"]
corr_comp = df[comp].corr(method="spearman").round(2)
corr_comp
""")

md("""
## 14. Redundancy check among numeric columns
Highly correlated pairs (|Spearman ρ| ≥ 0.7) matter for Logistic Regression coefficients and for
interpreting feature importance later. This is a *flag*, not an exclusion rule.
""")
code("""
num_feat = [c for c in num_cols if c not in constant_cols + [ID_COL]]
corr = df[num_feat].corr(method="spearman")
pairs = (corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1)).stack()
         .rename("rho").reset_index().rename(columns={"level_0": "var_1", "level_1": "var_2"}))
high_corr = pairs[pairs.rho.abs() >= 0.7].sort_values("rho", key=abs, ascending=False).round(3)
high_corr
""")

md("""
## 15. Protected attributes and proxy risk
`Age`, `Gender` and `MaritalStatus` are excluded from model features. But removing them does not remove their
information if other features **encode** them. Quick screen: how strongly does each retained numeric feature relate to Age?
""")
code("""
age_proxy = (df[num_feat].corrwith(df["Age"], method="spearman").drop("Age")
             .sort_values(key=abs, ascending=False).round(3).head(6).to_frame("rho_with_Age"))
age_proxy
""")
code("""
# Protected-group sizes: small groups produce unstable fairness estimates in Phase 6.
for c in ["Gender", "MaritalStatus"]:
    display(pd.crosstab(df[c], df[TARGET], margins=True))
""")

md("""
## 16. Business categorization and data quality table
Combines the documented business meaning (`src/data_dictionary.py`) with the measured statistics above.
Exported to `reports/data_quality_table.csv`.
""")
code("""
assert set(COLUMNS) == set(df.columns), set(COLUMNS) ^ set(df.columns)

rows = []
for col in df.columns:
    category, meaning, decision, reason = COLUMNS[col]
    s = df[col]
    rows.append({
        "column": col, "category": category, "dtype": str(s.dtype),
        "missing": int(s.isna().sum()), "n_unique": int(s.nunique()),
        "example_values": ", ".join(map(str, s.drop_duplicates().head(4).tolist())),
        "business_meaning": meaning, "decision": decision, "reason": reason,
    })
dq = pd.DataFrame(rows)
dq.to_csv(PROJECT_ROOT / "reports" / "data_quality_table.csv", index=False)
dq
""")
code("dq.groupby(['category', 'decision']).size().unstack(fill_value=0)")

md("""
## 17. Summary
The written interpretation of these outputs (what we found, what we decided and why) is in
`reports/data_quality_report.md`. Decisions marked **Review** are settled with evidence in `02_data_preparation.ipynb`.
""")

nb["cells"] = C
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, out_path)
print("wrote", out_path)
