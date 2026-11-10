import sys
from nbbuild import Notebook, SETUP

nb = Notebook()
nb.md("""
# 05 — Fairness Evaluation
**Workforce Pulse · Phase 6 · Responsible AI**

**Design.** `Age`, `Gender` and `MaritalStatus` were **excluded from the model's features**. They are held in a separate
audit view and joined to the model's predictions **only here**, after scoring.

**Questions**
1. Does the model flag groups at different rates, and do those differences track real differences in attrition?
2. Does it **miss** leavers (false negatives) or **wrongly flag** stayers (false positives) more in some groups?
3. Are probabilities equally well calibrated across groups?
4. Can the model's features act as **proxies** for protected attributes?

**Data.** Out-of-fold predictions for all 1,470 employees (each scored by a model that never saw them) are used instead
of the 368-row test set: subgroup estimates would otherwise rest on a handful of leavers. Rates have 95 % Wilson CIs.

> Ethical boundary: this model is a research / decision-support prototype. It must never autonomously rank employees
> for dismissal, promotion, pay or any other employment decision.
""")
nb.md("## 0. Setup")
nb.code(SETUP + """
import json
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from src.evaluation import group_fairness
from src.features import MODEL_NUMERIC, MODEL_CATEGORICAL

cfg = json.loads((PROJECT_ROOT / "models" / "model_config.json").read_text())
THRESHOLD = cfg["threshold"]
pred = pd.read_csv(DATA / "predictions" / "employee_attrition_predictions.csv")
audit = pd.read_csv(DATA / "processed" / "hr_featured.csv")[["EmployeeNumber", "Age", "AgeBand", "Gender", "MaritalStatus"]]
d = pred.merge(audit, on="EmployeeNumber", validate="one_to_one")
AGE_ORDER = ["Under 25", "25-34", "35-44", "45-54", "55+"]
print("Model:", cfg["selected_model"], "| threshold:", THRESHOLD, "| rows:", len(d))
""")

nb.md("""
## 1. Group-level error profile
| Metric | Fairness question |
|---|---|
| base_rate | How often did this group actually leave? (context for everything else) |
| flag_rate | How often does the model flag this group? (demographic parity) |
| recall_TPR | Of actual leavers, how many are caught? (equal opportunity) |
| FPR | Of stayers, how many are wrongly flagged? |
| FNR | Of leavers, how many are missed? |
| precision | Of flagged employees, how many actually left? (predictive parity) |
""")
nb.code("""
def audit_table(col, order=None):
    t = group_fairness(d.AttritionFlag, d.PredictedProbability, d[col], THRESHOLD).set_index("group")
    if order: t = t.reindex(order)
    fmt = lambda ci: f"[{ci[0]:.2f}, {ci[1]:.2f}]"
    for c in ["flag_rate_CI", "recall_CI", "FPR_CI"]:
        t[c] = t[c].map(fmt)
    return t

results = {"Gender": audit_table("Gender"), "MaritalStatus": audit_table("MaritalStatus", ["Single", "Married", "Divorced"]),
           "AgeBand": audit_table("AgeBand", AGE_ORDER)}
for k, t in results.items():
    print(f"\\n=== {k} ===")
    display(t.round(3))
""")

nb.md("""
## 2. Disparity summary
Relative to the largest group in each attribute (reference):
- **Flag-rate ratio:** group flag rate / reference flag rate. Below 0.8 or above 1.25 is used as a *screening* signal,
  borrowed from the four-fifths heuristic. It is not a legal test here.
- **Base-rate ratio:** the same ratio for **actual** attrition. If the flag-rate ratio ≈ base-rate ratio, the model
  mirrors real outcome differences rather than adding new ones.
- **TPR gap / FPR gap:** percentage-point differences in recall and false positive rate.
""")
nb.code("""
rows = []
for attr, t in results.items():
    ref = t["n"].idxmax()
    for g, r in t.iterrows():
        rows.append({"attribute": attr, "group": g, "reference": ref, "n": r.n, "leavers": r.actual_leavers,
                     "base_rate_ratio": r.base_rate / t.loc[ref, "base_rate"],
                     "flag_rate_ratio": r.flag_rate / t.loc[ref, "flag_rate"],
                     "TPR_gap_pp": 100 * (r.recall_TPR - t.loc[ref, "recall_TPR"]),
                     "FPR_gap_pp": 100 * (r.FPR - t.loc[ref, "FPR"]),
                     "calibration_gap_pp": 100 * (r.mean_predicted_risk - r.base_rate)})
disp = pd.DataFrame(rows)
disp["parity_screen"] = np.where(disp.flag_rate_ratio.between(0.8, 1.25), "within", "OUTSIDE")
disp["small_group"] = disp.leavers < 30
disp.to_csv(PROJECT_ROOT / "reports" / "fairness_disparities.csv", index=False)
disp.round(3)
""")

nb.md("## 3. Visual audit")
nb.code("""
fig, axes = plt.subplots(3, 3, figsize=(17, 12))
for row, (attr, t) in enumerate(results.items()):
    x = np.arange(len(t)); labels = [f"{g}\\n(n={n}, left={l})" for g, n, l in zip(t.index, t.n, t.actual_leavers)]
    axes[row, 0].bar(x - 0.2, t.base_rate, 0.4, label="actual attrition", color="#4C72B0")
    axes[row, 0].bar(x + 0.2, t.flag_rate, 0.4, label="model flag rate", color="#DD8452")
    axes[row, 0].set_title(f"{attr}: actual vs flagged"); axes[row, 0].legend(fontsize=8)
    for ax, m, ttl in [(axes[row, 1], "recall_TPR", "Recall (TPR)"), (axes[row, 2], "FPR", "False positive rate")]:
        lo = [float(s.strip("[]").split(",")[0]) for s in t[m.split("_")[0] + "_CI" if m == "FPR" else "recall_CI"]]
        hi = [float(s.strip("[]").split(",")[1]) for s in t[m.split("_")[0] + "_CI" if m == "FPR" else "recall_CI"]]
        ax.bar(x, t[m], color="#999999")
        ax.errorbar(x, t[m], yerr=[t[m] - lo, np.array(hi) - t[m]], fmt="none", ecolor="black", capsize=3)
        ax.set_title(f"{attr}: {ttl} (95% CI)")
    for ax in axes[row]:
        ax.set_xticks(x, labels, fontsize=7.5); ax.set_ylim(0, 1)
plt.tight_layout(); plt.savefig(FIG_DIR / "19_fairness_audit.png", dpi=150); plt.show()
""")
nb.code("""
fig, axes = plt.subplots(1, 3, figsize=(17, 4))
for ax, (col, order) in zip(axes, [("Gender", None), ("MaritalStatus", ["Single", "Married", "Divorced"]), ("AgeBand", AGE_ORDER)]):
    sns.boxplot(data=d, x=col, y="PredictedProbability", order=order, ax=ax, color="#DD8452", showfliers=False)
    ax.axhline(THRESHOLD, ls="--", color="black", lw=1); ax.set_title(f"Predicted risk distribution by {col}")
plt.tight_layout(); plt.savefig(FIG_DIR / "20_risk_distribution_by_group.png", dpi=150); plt.show()
""")

nb.md("""
## 4. Proxy analysis
If the model's **input features** can predict a protected attribute, excluding that attribute does not stop the model
from encoding it. We train a simple classifier: *model features → protected attribute*, and report cross-validated
ROC-AUC (0.5 = no information, 1.0 = perfect proxy). For Age we predict "age 35 or older".
""")
nb.code("""
feat = pd.read_csv(DATA / "processed" / "hr_featured.csv")
Xp = feat[MODEL_NUMERIC + MODEL_CATEGORICAL + ["SalaryRatioToLevel"]]
proxy_pipe = make_pipeline(
    ColumnTransformer([("num", StandardScaler(), MODEL_NUMERIC + ["SalaryRatioToLevel"]),
                       ("cat", OneHotEncoder(handle_unknown="ignore"), MODEL_CATEGORICAL)]),
    LogisticRegression(max_iter=3000))
targets = {"Gender = Female": feat.Gender == "Female", "MaritalStatus = Single": feat.MaritalStatus == "Single",
           "Age >= 35": feat.Age >= 35}
cvp = StratifiedKFold(5, shuffle=True, random_state=42)
proxy = pd.DataFrame({k: {"positives": int(v.sum()),
                          "cv_roc_auc": cross_val_score(proxy_pipe, Xp, v.astype(int), cv=cvp, scoring="roc_auc").mean()}
                      for k, v in targets.items()}).T
proxy.round(3)
""")
nb.code("""
# Which single features carry the most protected-attribute information?
def single_feature_auc(target):
    out = {}
    for c in MODEL_NUMERIC + ["SalaryRatioToLevel"]:
        from sklearn.metrics import roc_auc_score
        a = roc_auc_score(target.astype(int), feat[c]); out[c] = max(a, 1 - a)
    return pd.Series(out).sort_values(ascending=False).head(4).round(3)
pd.DataFrame({k: single_feature_auc(v).reset_index().apply(lambda r: f"{r['index']} ({r[0]})", axis=1)
              for k, v in targets.items()})
""")

nb.md("""
## 5. Conditional check: is the MaritalStatus / Age disparity explained by legitimate features?
Within the same overtime status and tenure band, does the model still flag Single (or younger) employees more?
If the gap shrinks a lot, the disparity mostly runs through work-related features. If it persists, the model
is encoding the protected attribute through proxies.
""")
nb.code("""
d2 = d.merge(feat[["EmployeeNumber", "OverTime", "TenureBand"]], on="EmployeeNumber")
d2["Young"] = np.where(d2.Age < 30, "Under 30", "30+")
def strat(attr):
    g = d2.groupby(["OverTime", "TenureBand", attr]).agg(n=("PredictedClass", "size"), flag_rate=("PredictedClass", "mean"),
                                                       base_rate=("AttritionFlag", "mean")).reset_index()
    return g[g.n >= 20].pivot_table(index=["OverTime", "TenureBand"], columns=attr, values=["flag_rate", "base_rate"]).round(3)
display(strat("MaritalStatus"))
strat("Young")
""")
nb.md("""
## 6. Mitigation experiment: remove the strongest proxy
In this dataset **every Single employee has StockOptionLevel = 0** (see crosstab), so StockOptionLevel is close to a
direct encoding of marital status. We refit the selected model configuration **without StockOptionLevel**, using the
same out-of-fold procedure and threshold, and compare: (a) predictive performance, (b) marital-status disparities.
This is an *experiment*, not an automatic fix: removing a proxy can lower accuracy without removing the disparity.
""")
nb.code("""
display(pd.crosstab(feat.MaritalStatus, feat.StockOptionLevel))
import os; os.environ["PYTHONPATH"] = str(PROJECT_ROOT)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.metrics import average_precision_score, roc_auc_score
from src.features import PeerSalaryRatio

def oof_scores(numeric):
    pipe = Pipeline([("peer", PeerSalaryRatio()),
                     ("prep", ColumnTransformer([("num", StandardScaler(), numeric),
                                                 ("cat", OneHotEncoder(handle_unknown="ignore", drop="if_binary"), MODEL_CATEGORICAL)])),
                     ("model", LogisticRegression(max_iter=5000, C=cfg["hyperparameters"]["C"],
                                                  class_weight=cfg["hyperparameters"]["class_weight"]))])
    Xm = feat[MODEL_NUMERIC + MODEL_CATEGORICAL]
    return cross_val_predict(CalibratedClassifierCV(pipe, method="sigmoid", cv=5), Xm, feat.AttritionFlag,
                             cv=StratifiedKFold(5, shuffle=True, random_state=42), method="predict_proba", n_jobs=-1)[:, 1]

base_numeric = cfg["model_numeric_features"]
variants = {"current model": d.set_index("EmployeeNumber").loc[feat.EmployeeNumber, "PredictedProbability"].to_numpy(),
            "without StockOptionLevel": oof_scores([c for c in base_numeric if c != "StockOptionLevel"])}
rows = []
for name, p in variants.items():
    flag = p >= THRESHOLD
    r = {"variant": name, "PR_AUC": average_precision_score(feat.AttritionFlag, p), "ROC_AUC": roc_auc_score(feat.AttritionFlag, p)}
    for g in ["Single", "Married", "Divorced"]:
        m = feat.MaritalStatus == g
        r[f"flag_{g}"] = flag[m].mean()
        r[f"recall_{g}"] = flag[m & (feat.AttritionFlag == 1)].mean()
    r["flag_ratio_Single/Married"] = r["flag_Single"] / r["flag_Married"]
    rows.append(r)
mitigation = pd.DataFrame(rows).set_index("variant").T
mitigation.round(3)
""")
nb.md("Interpretation and recommendations: `reports/fairness_report.md`.")
nb.save(sys.argv[1])
