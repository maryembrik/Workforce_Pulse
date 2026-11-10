import sys
from nbbuild import Notebook, SETUP

nb = Notebook()
nb.md("""
# 04 — Attrition Modelling & Explainability
**Workforce Pulse · Phase 5**

**Prediction problem.** Binary classification: `AttritionFlag` (1 = left, 0 = stayed) from workforce attributes.
**Output.** Estimated probability of attrition *in this dataset's historical context*. It is not a forecast of
future departures.

**Pre-registered decisions (fixed before looking at results)**
| Decision | Rule | Why |
|---|---|---|
| Split | 75/25 stratified, `random_state=42`; test set untouched until final evaluation | Honest generalization estimate |
| Primary metric | **PR-AUC** (average precision); no-skill = 0.161 | Minority class focus. Accuracy is misleading (83.9 % for "nobody leaves") |
| Tuning | Grid search, 5-fold × 2 repeated stratified CV on train | Stable estimates on a small dataset |
| Model choice | XGBoost replaces LR **only if** test PR-AUC is higher **and** the paired-bootstrap 95 % CI of the difference excludes 0 | Prefer the simpler, interpretable model unless the complex one is clearly better |
| Threshold | Maximize **F2** on out-of-fold *training* predictions | Use case = supportive HR check-in: a missed leaver costs more than an unnecessary conversation |
| Probabilities | Final model wrapped in sigmoid calibration | Class weighting inflates probabilities, and dashboards show probabilities |
| Features | No IDs, no protected attributes, no undocumented rates (see `docs/feature_dictionary.md`) | Responsible-AI design |
""")

nb.md("## 0. Setup")
nb.code(SETUP + """
import os, json, joblib, time
os.environ["PYTHONPATH"] = str(PROJECT_ROOT)          # parallel workers must import src.*
os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
import mlflow, shap
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, precision_recall_curve, fbeta_score
from sklearn.model_selection import (GridSearchCV, RepeatedStratifiedKFold, StratifiedKFold,
                                     cross_val_predict, train_test_split)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from src.features import PeerSalaryRatio, MODEL_NUMERIC, MODEL_CATEGORICAL
from src.evaluation import classification_metrics, threshold_table
from src.data_dictionary import PROTECTED, ID_COL

SEED = 42
df = pd.read_csv(DATA / "processed" / "hr_featured.csv")
NUMERIC = MODEL_NUMERIC + ["SalaryRatioToLevel"]             # last one created inside the pipeline
INPUT_COLS = MODEL_NUMERIC + MODEL_CATEGORICAL               # columns the pipeline receives
X, y = df[INPUT_COLS], df["AttritionFlag"]
assert not set(PROTECTED) & set(INPUT_COLS)

mlflow.set_tracking_uri(f"sqlite:///{(PROJECT_ROOT / 'mlflow.db').as_posix()}")
mlflow.set_experiment("workforce-pulse-attrition")
print(X.shape, "positives:", y.sum())
""")

nb.md("## 1. Stratified train / test split")
nb.code("""
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=SEED)
pd.DataFrame({"rows": [len(y_tr), len(y_te)], "leavers": [y_tr.sum(), y_te.sum()],
              "rate": [y_tr.mean(), y_te.mean()]}, index=["train", "test"]).round(4)
""")

nb.md("""
## 2. Preprocessing pipeline
`PeerSalaryRatio` (JobLevel medians learned from the training fold) → scale numerics / one-hot categoricals → model.
Every transformation sits **inside** the pipeline, so cross-validation refits it on each training fold and nothing
leaks from validation or test data.
""")
nb.code("""
def make_pipeline(model, scale=True, numeric=None):
    prep = ColumnTransformer([
        ("num", StandardScaler() if scale else "passthrough", numeric or NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore", drop="if_binary", sparse_output=False), MODEL_CATEGORICAL),
    ], verbose_feature_names_out=False)
    return Pipeline([("peer", PeerSalaryRatio()), ("prep", prep), ("model", model)])

cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=2, random_state=SEED)
make_pipeline(LogisticRegression())
""")

nb.md("## 3. Baseline — no-skill model")
nb.code("""
dummy = make_pipeline(DummyClassifier(strategy="prior")).fit(X_tr, y_tr)
p_dummy = dummy.predict_proba(X_te)[:, 1]
print(f"Dummy (predicts prevalence): PR-AUC={average_precision_score(y_te, p_dummy):.3f}  "
      f"ROC-AUC={roc_auc_score(y_te, p_dummy):.3f}")
print(f"'Nobody leaves' accuracy on test: {(y_te == 0).mean():.3f}  <- with recall 0")
""")

nb.md("""
## 4. Model 1 — Logistic Regression (interpretable baseline)
L2-regularized (handles the correlated tenure / pay variables). Class weighting is a tuned option, not an assumption.
""")
nb.code("""
lr_grid = GridSearchCV(
    make_pipeline(LogisticRegression(max_iter=5000)),
    {"model__C": [0.01, 0.03, 0.1, 0.3, 1, 3], "model__class_weight": [None, "balanced"]},
    scoring={"pr_auc": "average_precision", "roc_auc": "roc_auc"}, refit="pr_auc", cv=cv, n_jobs=-1)
t0 = time.time(); lr_grid.fit(X_tr, y_tr)
print(f"{time.time()-t0:.0f}s  best params:", lr_grid.best_params_)
lr_cv = pd.DataFrame(lr_grid.cv_results_)[["param_model__C", "param_model__class_weight", "mean_test_pr_auc",
                                            "std_test_pr_auc", "mean_test_roc_auc"]]
lr_cv.sort_values("mean_test_pr_auc", ascending=False).head(6).round(4)
""")

nb.md("""
### 4b. Collinearity diagnostic → interpretable LR variant
*Decision added after the first SHAP review; made on training CV only, never on the test set.*

The first run's SHAP plot showed **higher MonthlyIncome increasing risk** while higher JobLevel and SalaryRatioToLevel
decreased it. That is the signature of collinearity (Phase 1: income–JobLevel ρ = 0.92, and SalaryRatioToLevel =
income / level median), not a business pattern. Coefficients split and offset each other.

Variant: drop `MonthlyIncome` from the LR's model inputs. Pay is still represented as **seniority (JobLevel) ×
relative pay (SalaryRatioToLevel)**, which is also easier to explain to HR. Rule: keep the simpler variant unless its CV
PR-AUC is lower by more than one standard error of the full model's CV estimate.
""")
nb.code("""
LR_NUMERIC_NO_INCOME = [c for c in NUMERIC if c != "MonthlyIncome"]
lr2_grid = GridSearchCV(
    make_pipeline(LogisticRegression(max_iter=5000), numeric=LR_NUMERIC_NO_INCOME),
    {"model__C": [0.01, 0.03, 0.1, 0.3, 1, 3], "model__class_weight": [None, "balanced"]},
    scoring={"pr_auc": "average_precision", "roc_auc": "roc_auc"}, refit="pr_auc", cv=cv, n_jobs=-1)
lr2_grid.fit(X_tr, y_tr)
n_splits = cv.get_n_splits()
full_mean = lr_grid.best_score_; full_se = lr_grid.cv_results_["std_test_pr_auc"][lr_grid.best_index_] / np.sqrt(n_splits)
lite_mean = lr2_grid.best_score_
USE_LITE = lite_mean >= full_mean - full_se
print(f"LR with income:    CV PR-AUC {full_mean:.4f} (SE {full_se:.4f})  params {lr_grid.best_params_}")
print(f"LR without income: CV PR-AUC {lite_mean:.4f}               params {lr2_grid.best_params_}")
print("Use interpretable variant:", USE_LITE)
if USE_LITE:
    lr_grid = lr2_grid
LR_NUMERIC = LR_NUMERIC_NO_INCOME if USE_LITE else NUMERIC
""")

nb.md("""
## 5. Model 2 — XGBoost (non-linear)
`scale_pos_weight` (≈ 5.2 = negatives / positives) is the tree-model equivalent of class weighting, tuned on/off.
Shallow trees and a small learning rate limit overfitting on 1,100 training rows.
""")
nb.code("""
spw = (y_tr == 0).sum() / (y_tr == 1).sum()
xgb_grid = GridSearchCV(
    make_pipeline(XGBClassifier(eval_metric="logloss", tree_method="hist", subsample=0.8, colsample_bytree=0.8,
                                random_state=SEED, n_jobs=1), scale=False),
    {"model__max_depth": [2, 3, 4], "model__learning_rate": [0.03, 0.1], "model__n_estimators": [200, 400],
     "model__min_child_weight": [1, 5], "model__scale_pos_weight": [1, round(spw, 2)]},
    scoring={"pr_auc": "average_precision", "roc_auc": "roc_auc"}, refit="pr_auc", cv=cv, n_jobs=-1)
t0 = time.time(); xgb_grid.fit(X_tr, y_tr)
print(f"{time.time()-t0:.0f}s  best params:", xgb_grid.best_params_)
xgb_cv = pd.DataFrame(xgb_grid.cv_results_)
xgb_cv[["params", "mean_test_pr_auc", "std_test_pr_auc", "mean_test_roc_auc"]].sort_values(
    "mean_test_pr_auc", ascending=False).head(6).round(4)
""")

nb.md("## 6. Objective comparison on the untouched test set")
nb.code("""
models = {"LogisticRegression": lr_grid.best_estimator_, "XGBoost": xgb_grid.best_estimator_}
p_test = {k: m.predict_proba(X_te)[:, 1] for k, m in models.items()}
rows = []
for name, grid in [("LogisticRegression", lr_grid), ("XGBoost", xgb_grid)]:
    i = grid.best_index_
    m = classification_metrics(y_te, p_test[name], 0.5)
    rows.append({"model": name, "cv_pr_auc": grid.cv_results_["mean_test_pr_auc"][i],
                 "cv_pr_auc_sd": grid.cv_results_["std_test_pr_auc"][i],
                 "cv_roc_auc": grid.cv_results_["mean_test_roc_auc"][i],
                 "test_pr_auc": m["pr_auc"], "test_roc_auc": m["roc_auc"], "test_brier": m["brier"]})
rows.append({"model": "Dummy (prevalence)", "test_pr_auc": average_precision_score(y_te, p_dummy),
             "test_roc_auc": 0.5, "test_brier": classification_metrics(y_te, p_dummy)["brier"]})
comparison = pd.DataFrame(rows).set_index("model")
comparison.round(4)
""")
nb.code("""
# Paired bootstrap of the test PR-AUC difference (XGBoost - LR)
rng = np.random.default_rng(SEED)
yt, pl, px = y_te.to_numpy(), p_test["LogisticRegression"], p_test["XGBoost"]
diffs = []
for _ in range(2000):
    idx = rng.integers(0, len(yt), len(yt))
    if yt[idx].sum() == 0: continue
    diffs.append(average_precision_score(yt[idx], px[idx]) - average_precision_score(yt[idx], pl[idx]))
diffs = np.array(diffs)
ci = np.percentile(diffs, [2.5, 97.5])
obs = average_precision_score(yt, px) - average_precision_score(yt, pl)
xgb_wins = obs > 0 and ci[0] > 0
SELECTED = "XGBoost" if xgb_wins else "LogisticRegression"
print(f"PR-AUC difference XGB - LR = {obs:+.4f}, 95% bootstrap CI [{ci[0]:+.4f}, {ci[1]:+.4f}]")
print(f"P(XGB better) in bootstrap = {(diffs > 0).mean():.2f}")
print("Selected model by pre-registered rule:", SELECTED)
""")
nb.code("""
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
for name, p in p_test.items():
    pr, rc, _ = precision_recall_curve(y_te, p)
    axes[0].plot(rc, pr, label=f"{name} (AP={average_precision_score(y_te, p):.3f})")
    frac, mean_pred = calibration_curve(y_te, p, n_bins=8, strategy="quantile")
    axes[1].plot(mean_pred, frac, marker="o", label=name)
axes[0].axhline(y_te.mean(), ls="--", color="grey", label=f"No skill ({y_te.mean():.3f})")
axes[0].set(xlabel="Recall", ylabel="Precision", title="Precision-Recall (test set)"); axes[0].legend()
axes[1].plot([0, 1], [0, 1], ls="--", color="grey")
axes[1].set(xlabel="Mean predicted probability", ylabel="Observed attrition rate", title="Calibration before calibrating (test)")
axes[1].legend()
plt.tight_layout(); plt.savefig(FIG_DIR / "12_model_comparison.png", dpi=150); plt.show()
""")

nb.md("""
## 7. Probability calibration of the selected model
Sigmoid (Platt) calibration fitted with internal 5-fold CV on the training data only.
Ranking (PR-AUC / ROC-AUC) should barely change. Brier score and the calibration curve show whether probabilities became honest.
""")
nb.code("""
best_pipe = models[SELECTED]
cal_model = CalibratedClassifierCV(best_pipe, method="sigmoid", cv=StratifiedKFold(5, shuffle=True, random_state=SEED))
cal_model.fit(X_tr, y_tr)
p_cal = cal_model.predict_proba(X_te)[:, 1]
pd.DataFrame({
    "uncalibrated": {"pr_auc": average_precision_score(y_te, p_test[SELECTED]), "roc_auc": roc_auc_score(y_te, p_test[SELECTED]),
                     "brier": classification_metrics(y_te, p_test[SELECTED])["brier"], "mean_pred": p_test[SELECTED].mean()},
    "calibrated": {"pr_auc": average_precision_score(y_te, p_cal), "roc_auc": roc_auc_score(y_te, p_cal),
                   "brier": classification_metrics(y_te, p_cal)["brier"], "mean_pred": p_cal.mean()},
    "actual": {"mean_pred": y_te.mean()}}).round(4)
""")

nb.md("""
## 8. Threshold selection (training data only)
Out-of-fold calibrated predictions on the **training** set → choose the threshold that maximizes F2 → apply it,
unchanged, to the test set.
""")
nb.code("""
skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
p_oof_tr = cross_val_predict(CalibratedClassifierCV(best_pipe, method="sigmoid", cv=5), X_tr, y_tr,
                             cv=skf, method="predict_proba", n_jobs=-1)[:, 1]
grid_t = np.round(np.arange(0.05, 0.81, 0.01), 2)
f2 = [fbeta_score(y_tr, (p_oof_tr >= t).astype(int), beta=2) for t in grid_t]
THRESHOLD = float(grid_t[int(np.argmax(f2))])
print(f"F2-optimal threshold on training OOF predictions: {THRESHOLD}")
tt = threshold_table(y_te, p_cal, np.round(np.arange(0.10, 0.61, 0.05), 2))
tt.round(3)
""")
nb.code("""
fig, ax = plt.subplots(figsize=(9, 4.5))
tt_fine = threshold_table(y_te, p_cal, np.round(np.arange(0.05, 0.81, 0.01), 2))
for c in ["precision", "recall", "f1", "flag_rate"]:
    ax.plot(tt_fine.threshold, tt_fine[c], label=c)
ax.axvline(THRESHOLD, color="black", ls="--", label=f"selected = {THRESHOLD}")
ax.axvline(0.5, color="grey", ls=":", label="default 0.5")
ax.set(xlabel="Threshold", ylabel="Value", title="Threshold trade-off (calibrated model, test set)"); ax.legend()
plt.tight_layout(); plt.savefig(FIG_DIR / "13_threshold_tradeoff.png", dpi=150); plt.show()
""")

nb.md("## 9. Final test-set evaluation at the selected threshold")
nb.code("""
final_test = classification_metrics(y_te, p_cal, THRESHOLD)
default_test = classification_metrics(y_te, p_cal, 0.5)
pd.DataFrame({f"selected ({THRESHOLD})": final_test, "default (0.5)": default_test}).round(4)
""")
nb.code("""
from sklearn.metrics import ConfusionMatrixDisplay
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for ax, t in zip(axes, [THRESHOLD, 0.5]):
    ConfusionMatrixDisplay.from_predictions(y_te, (p_cal >= t).astype(int), display_labels=["Stayed", "Left"],
                                            cmap="Oranges", ax=ax, colorbar=False)
    ax.set_title(f"Threshold {t}")
plt.tight_layout(); plt.savefig(FIG_DIR / "14_confusion_matrices.png", dpi=150); plt.show()
""")

nb.md("""
## 10. Experiment tracking (MLflow)
One run per candidate model plus the final calibrated model. View with:
`mlflow ui --backend-store-uri sqlite:///mlflow.db`
""")
nb.code("""
for name, grid in [("LogisticRegression", lr_grid), ("XGBoost", xgb_grid)]:
    with mlflow.start_run(run_name=f"{name}-gridsearch"):
        mlflow.log_params({k.replace("model__", ""): v for k, v in grid.best_params_.items()})
        mlflow.log_params({"cv": "RepeatedStratifiedKFold(5x2)", "test_size": 0.25, "seed": SEED,
                           "n_features_in": len(INPUT_COLS)})
        mlflow.log_metrics({f"cv_{k}": v for k, v in comparison.loc[name, ["cv_pr_auc", "cv_pr_auc_sd", "cv_roc_auc"]].items()})
        mlflow.log_metrics({k: v for k, v in comparison.loc[name, ["test_pr_auc", "test_roc_auc", "test_brier"]].items()})
with mlflow.start_run(run_name=f"FINAL-{SELECTED}-calibrated"):
    mlflow.log_params({"model": SELECTED, "calibration": "sigmoid", "threshold": THRESHOLD,
                       "threshold_rule": "max F2 on train OOF", "selection_rule": "XGB only if bootstrap CI > 0",
                       "lr_monthly_income_dropped": USE_LITE})
    mlflow.log_metrics({f"test_{k}": float(v) for k, v in final_test.items() if k != "threshold"})
    mlflow.log_metric("bootstrap_prauc_diff_xgb_minus_lr", float(obs))
    mlflow.log_artifact(str(FIG_DIR / "12_model_comparison.png"))
    mlflow.log_artifact(str(FIG_DIR / "13_threshold_tradeoff.png"))
print(mlflow.search_runs()[["tags.mlflow.runName", "metrics.test_pr_auc", "metrics.test_roc_auc"]].head())
""")

nb.md("""
## 11. SHAP explainability
SHAP values explain the **selected model's** raw output (log-odds), computed on the transformed test features.
Sigmoid calibration is monotonic, so the direction and ranking of contributions are unchanged.

> SHAP shows how the model *uses* a feature, not what would happen if we changed it. A large SHAP value for
> OverTime does **not** prove that removing overtime would retain an employee.
""")
nb.code("""
prep = best_pipe[:-1]
est = best_pipe[-1]
feat_names = list(prep.named_steps["prep"].get_feature_names_out())
Xt_tr = pd.DataFrame(prep.transform(X_tr), columns=feat_names)
Xt_te = pd.DataFrame(prep.transform(X_te), columns=feat_names)
if SELECTED == "XGBoost":
    explainer = shap.TreeExplainer(est)
else:
    explainer = shap.LinearExplainer(est, Xt_tr)
sv = explainer(Xt_te)
# display unscaled values for readability in plots
Xt_te_raw = best_pipe.named_steps["peer"].transform(X_te).reset_index(drop=True)
importance = pd.Series(np.abs(sv.values).mean(0), index=feat_names).sort_values(ascending=False)
importance.head(15).round(4)
""")
nb.code("""
plt.figure()
shap.plots.beeswarm(sv, max_display=15, show=False)
plt.title(f"SHAP summary — {SELECTED} (test set)"); plt.tight_layout()
plt.savefig(FIG_DIR / "15_shap_summary.png", dpi=150, bbox_inches="tight"); plt.show()
plt.figure()
shap.plots.bar(sv, max_display=15, show=False)
plt.title("Mean |SHAP| — global importance"); plt.tight_layout()
plt.savefig(FIG_DIR / "16_shap_importance.png", dpi=150, bbox_inches="tight"); plt.show()
""")
nb.code("""
# Agreement check: does the other model rank features similarly?
other = "XGBoost" if SELECTED == "LogisticRegression" else "LogisticRegression"
op = models[other]
o_names = list(op[:-1].named_steps["prep"].get_feature_names_out())
o_X_tr = pd.DataFrame(op[:-1].transform(X_tr), columns=o_names)
o_X_te = pd.DataFrame(op[:-1].transform(X_te), columns=o_names)
o_exp = shap.TreeExplainer(op[-1]) if other == "XGBoost" else shap.LinearExplainer(op[-1], o_X_tr)
o_imp = pd.Series(np.abs(o_exp(o_X_te).values).mean(0), index=o_names)
agree = pd.DataFrame({SELECTED: importance.rank(ascending=False), other: o_imp.rank(ascending=False)}).sort_values(SELECTED)
print("Spearman rank agreement of global importance:", round(agree.corr(method="spearman").iloc[0, 1], 3))
agree.head(10)
""")
nb.code("""
top3 = [f for f in importance.index if f in NUMERIC][:3]
fig, axes = plt.subplots(1, 3, figsize=(16, 4.2))
for ax, f in zip(axes, top3):
    col = feat_names.index(f)
    ax.scatter(Xt_te_raw[f], sv.values[:, col], s=10, alpha=.6, color="#DD8452")
    ax.axhline(0, color="grey", lw=1); ax.set(xlabel=f, ylabel="SHAP value (log-odds)", title=f"Dependence: {f}")
plt.tight_layout(); plt.savefig(FIG_DIR / "17_shap_dependence.png", dpi=150); plt.show()
""")
nb.code("""
# Individual explanations: highest-scored test record and a typical (median-score) record
order = np.argsort(p_cal)
for label, i in [("highest", order[-1]), ("median", order[len(order) // 2])]:
    print(f"{label}: EmployeeNumber={df.loc[X_te.index[i], ID_COL]}, calibrated p={p_cal[i]:.3f}, actual={y_te.iloc[i]}")
    plt.figure()
    shap.plots.waterfall(sv[i], max_display=10, show=False)
    plt.title(f"Why this record scored {p_cal[i]:.2f} ({label} risk in test set)")
    plt.tight_layout(); plt.savefig(FIG_DIR / f"18_shap_waterfall_{label}.png", dpi=150, bbox_inches="tight"); plt.show()
""")

nb.md("""
## 12. Final model: refit on all data, save artifacts
After evaluation, the selected configuration is refitted (with calibration) on all 1,470 records, which is standard
practice. The reported performance remains the **test-set** estimate above.
""")
nb.code("""
final_model = CalibratedClassifierCV(make_pipeline(best_pipe[-1].__class__(**best_pipe[-1].get_params()),
                                                   scale=SELECTED == "LogisticRegression",
                                                   numeric=LR_NUMERIC if SELECTED == "LogisticRegression" else NUMERIC),
                                     method="sigmoid", cv=StratifiedKFold(5, shuffle=True, random_state=SEED))
final_model.fit(X, y)
(PROJECT_ROOT / "models").mkdir(exist_ok=True)
joblib.dump(final_model, PROJECT_ROOT / "models" / "attrition_model.joblib")
config = {
    "model_version": "1.0.0", "selected_model": SELECTED, "calibration": "sigmoid",
    "hyperparameters": {k.replace("model__", ""): v for k, v in
                        (lr_grid if SELECTED == "LogisticRegression" else xgb_grid).best_params_.items()},
    "threshold": THRESHOLD, "threshold_rule": "max F2 on out-of-fold training predictions",
    "input_features": INPUT_COLS, "engineered_in_pipeline": ["SalaryRatioToLevel"],
    "model_numeric_features": LR_NUMERIC if SELECTED == "LogisticRegression" else NUMERIC,
    "lr_variant": {"monthly_income_dropped": bool(USE_LITE), "cv_pr_auc_with_income": round(float(full_mean), 4),
                   "cv_pr_auc_without_income": round(float(lite_mean), 4),
                   "reason": "collinearity (income-JobLevel rho=0.92) produced sign-flipped, offsetting SHAP"},
    "excluded_protected": PROTECTED, "test_metrics": {k: round(float(v), 4) for k, v in final_test.items()},
    "model_comparison": comparison.round(4).reset_index().to_dict(orient="records"),
    "bootstrap_prauc_diff_xgb_minus_lr": {"observed": round(float(obs), 4), "ci95": [round(float(c), 4) for c in ci]},
    "training_rows": int(len(X)), "random_state": SEED,
}
(PROJECT_ROOT / "models" / "model_config.json").write_text(json.dumps(config, indent=2, default=str))
print(json.dumps({k: config[k] for k in ["selected_model", "threshold", "test_metrics"]}, indent=1))
""")

nb.md("""
## 13. Export predictions for every employee (out-of-fold)
Each employee is scored by a model trained **without that employee** (5-fold cross-validated calibrated pipeline),
so the exported scores are honest. Risk bands:

Both cut-offs are chosen on **training out-of-fold predictions only**:

| Band | Rule | Meaning |
|---|---|---|
| High | p ≥ `HIGH_CUTOFF` = lowest threshold where training-OOF precision ≥ 60 % | Small, high-confidence group |
| Elevated | `THRESHOLD` (F2) ≤ p < `HIGH_CUTOFF` | Flagged by the recall-oriented operating threshold |
| Low | p < `THRESHOLD` | Not flagged |

`PredictedClass` = 1 for both High and Elevated (i.e. at the operating threshold).

These bands are **analytical categories**, not validated HR risk classifications.
`TopRiskFactors` lists the three features pushing the score up most (SHAP of the final model). They are explanations of
the model, not reasons the employee gave.
""")
nb.code("""
p_oof_all = cross_val_predict(CalibratedClassifierCV(best_pipe, method="sigmoid", cv=5), X, y,
                              cv=StratifiedKFold(5, shuffle=True, random_state=SEED), method="predict_proba", n_jobs=-1)[:, 1]
tr_tab = threshold_table(y_tr, p_oof_tr, grid_t)
HIGH_CUTOFF = float(tr_tab.loc[(tr_tab.precision >= 0.60) & (tr_tab.tp >= 10), "threshold"].min())
assert HIGH_CUTOFF > THRESHOLD
print(f"Operating threshold (F2): {THRESHOLD} | High-band cut-off (train OOF precision >= 60%): {HIGH_CUTOFF}")
band = np.where(p_oof_all >= HIGH_CUTOFF, "High", np.where(p_oof_all >= THRESHOLD, "Elevated", "Low"))
config["high_band_cutoff"] = HIGH_CUTOFF
config["risk_bands"] = {"High": f"p >= {HIGH_CUTOFF}", "Elevated": f"{THRESHOLD} <= p < {HIGH_CUTOFF}", "Low": f"p < {THRESHOLD}"}
(PROJECT_ROOT / "models" / "model_config.json").write_text(json.dumps(config, indent=2, default=str))
print("High-band performance on test set:")
print({k: round(float(v), 3) for k, v in classification_metrics(y_te, p_cal, HIGH_CUTOFF).items()
       if k in ("precision", "recall", "flag_rate", "tp", "fp")})

# Per-employee drivers from the final (full-data) model's base pipeline, averaged over calibration folds
def shap_for(pipe_cal, Xin):
    vals = []
    for cc in pipe_cal.calibrated_classifiers_:
        p = cc.estimator
        names = list(p[:-1].named_steps["prep"].get_feature_names_out())
        Xt = pd.DataFrame(p[:-1].transform(Xin), columns=names)
        e = shap.TreeExplainer(p[-1]) if SELECTED == "XGBoost" else shap.LinearExplainer(p[-1], Xt)
        vals.append(e(Xt).values)
    return np.mean(vals, axis=0), names
sv_all, names_all = shap_for(final_model, X)
raw_all = final_model.calibrated_classifiers_[0].estimator.named_steps["peer"].transform(X)

def readable(feat, row):
    if feat in NUMERIC:
        v = row[feat]
        return f"{feat} = {v:.2f}" if feat in ("SalaryRatioToLevel", "RoleShareOfTenure") else f"{feat} = {int(v)}"
    for c in MODEL_CATEGORICAL:
        if feat.startswith(c + "_"):
            return f"{c} = {row[c]}"
    return feat

top_factors = []
for i in range(len(X)):
    pos = [(names_all[j], sv_all[i, j]) for j in np.argsort(-sv_all[i]) if sv_all[i, j] > 0][:3]
    top_factors.append("; ".join(readable(f, raw_all.iloc[i]) for f, _ in pos))

pred = pd.DataFrame({
    "EmployeeNumber": df[ID_COL], "Attrition": df["Attrition"], "AttritionFlag": y,
    "PredictedProbability": p_oof_all.round(4), "PredictedClass": (p_oof_all >= THRESHOLD).astype(int),
    "RiskBand": band, "Threshold": THRESHOLD, "HighBandCutoff": HIGH_CUTOFF, "TopRiskFactors": top_factors,
    "Split": np.where(df.index.isin(X_te.index), "test", "train"),
})
(DATA / "predictions").mkdir(exist_ok=True)
pred.to_csv(DATA / "predictions" / "employee_attrition_predictions.csv", index=False)
print("OOF PR-AUC (all 1,470):", round(average_precision_score(y, p_oof_all), 4),
      "| ROC-AUC:", round(roc_auc_score(y, p_oof_all), 4))
pred.groupby("RiskBand").agg(employees=("EmployeeNumber", "count"), actual_leavers=("AttritionFlag", "sum"),
                             actual_rate=("AttritionFlag", "mean"), mean_p=("PredictedProbability", "mean")).reindex(
                             ["High", "Elevated", "Low"]).round(3)
""")
nb.code("pred.sort_values('PredictedProbability', ascending=False).head(5)")

nb.md("""
## 14. Model sensitivity scenarios (input for the Power BI simulator)
For three hypothetical changes, the final model re-scores each affected employee with **one input modified** and
everything else unchanged:

| Scenario | Affected employees | Modification |
|---|---|---|
| `overtime_removed` | OverTime = Yes | OverTime → No |
| `job_satisfaction_up` | JobSatisfaction ≤ 2 | JobSatisfaction + 1 |
| `env_satisfaction_up` | EnvironmentSatisfaction ≤ 2 | EnvironmentSatisfaction + 1 |
| `wlb_up` | WorkLifeBalance ≤ 2 | WorkLifeBalance + 1 |
| `salary_to_peer_median` | SalaryRatioToLevel < 0.9 | MonthlyIncome raised to 90 % of JobLevel median |

`ScoreChange` = scenario score − current score. This is **model sensitivity**: how the *model's* output responds.
It is not an estimate of employees retained, because the model learned associations, not causal effects.
""")
nb.code("""
base_p = final_model.predict_proba(X)[:, 1]
peer = final_model.calibrated_classifiers_[0].estimator.named_steps["peer"]
ratio = peer.transform(X)["SalaryRatioToLevel"]
lvl_med = X["JobLevel"].map(peer.medians_)
scen_defs = {
    "overtime_removed": (X.OverTime == "Yes", lambda d: d.assign(OverTime="No")),
    "job_satisfaction_up": (X.JobSatisfaction <= 2, lambda d: d.assign(JobSatisfaction=d.JobSatisfaction + 1)),
    "env_satisfaction_up": (X.EnvironmentSatisfaction <= 2, lambda d: d.assign(EnvironmentSatisfaction=d.EnvironmentSatisfaction + 1)),
    "wlb_up": (X.WorkLifeBalance <= 2, lambda d: d.assign(WorkLifeBalance=d.WorkLifeBalance + 1)),
    "salary_to_peer_median": (ratio < 0.9, lambda d: d.assign(MonthlyIncome=np.maximum(d.MonthlyIncome, (0.9 * lvl_med[d.index]).round()))),
}
scen_rows = []
for name, (mask, fn) in scen_defs.items():
    Xs = fn(X[mask].copy())
    new_p = final_model.predict_proba(Xs)[:, 1]
    scen_rows.append(pd.DataFrame({"EmployeeNumber": df.loc[mask, ID_COL].to_numpy(), "Scenario": name,
                                   "CurrentScore": base_p[mask.to_numpy()].round(4), "ScenarioScore": new_p.round(4)}))
scen = pd.concat(scen_rows, ignore_index=True)
scen["ScoreChange"] = (scen.ScenarioScore - scen.CurrentScore).round(4)
scen.to_csv(DATA / "predictions" / "scenario_sensitivity.csv", index=False)
scen.groupby("Scenario").agg(employees=("EmployeeNumber", "count"), mean_current=("CurrentScore", "mean"),
                             mean_scenario=("ScenarioScore", "mean"), mean_change=("ScoreChange", "mean"),
                             sum_change=("ScoreChange", "sum")).round(4)
""")
nb.md("Interpretation: `reports/model_report.md`.")
nb.save(sys.argv[1])
