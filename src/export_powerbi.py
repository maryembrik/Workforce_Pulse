"""Build the Power BI data pack in powerbi/data/.

    python -m src.export_powerbi

Tables
------
fact_employees.csv          1 row per employee: attributes, engineered features, actual outcome, model score & band
scenario_sensitivity.csv    model sensitivity: current vs scenario score per affected employee (many-to-one)
feature_importance.csv      global SHAP importance of the final model with business labels
dim_risk_band.csv           band definitions and sort order
model_metrics.csv           headline model evaluation metrics (test set) for a "model card" visual
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "powerbi" / "data"
OUT.mkdir(parents=True, exist_ok=True)

LABELS = {
    "OverTime_Yes": "Works overtime", "TotalWorkingYears": "Total working years",
    "StockOptionLevel": "Stock option level", "EnvironmentSatisfaction": "Environment satisfaction",
    "YearsSinceLastPromotion": "Years since last promotion", "JobInvolvement": "Job involvement",
    "NumCompaniesWorked": "Number of previous employers", "JobSatisfaction": "Job satisfaction",
    "YearsWithCurrManager": "Years with current manager", "DistanceFromHome": "Distance from home",
    "RelationshipSatisfaction": "Relationship satisfaction", "RoleShareOfTenure": "Share of tenure in current role",
    "BusinessTravel_Travel_Frequently": "Travels frequently", "SalaryRatioToLevel": "Salary vs. job-level peers",
    "WorkLifeBalance": "Work-life balance", "YearsAtCompany": "Years at company",
    "YearsInCurrentRole": "Years in current role", "JobLevel": "Job level", "TrainingTimesLastYear": "Trainings last year",
    "PercentSalaryHike": "Last salary increase %", "Education": "Education level", "PerformanceRating": "Performance rating",
}
CATEGORY = {
    "Work conditions": ["OverTime", "BusinessTravel", "DistanceFromHome", "WorkLifeBalance"],
    "Satisfaction": ["EnvironmentSatisfaction", "JobSatisfaction", "RelationshipSatisfaction", "JobInvolvement"],
    "Career development": ["TotalWorkingYears", "YearsSinceLastPromotion", "NumCompaniesWorked", "YearsWithCurrManager",
                           "RoleShareOfTenure", "YearsAtCompany", "YearsInCurrentRole", "TrainingTimesLastYear"],
    "Compensation": ["StockOptionLevel", "SalaryRatioToLevel", "PercentSalaryHike", "JobLevel"],
    "Organizational": ["JobRole", "Department", "EducationField"],
}


def category_of(feature: str) -> str:
    for cat, cols in CATEGORY.items():
        if any(feature == c or feature.startswith(c + "_") for c in cols):
            return cat
    return "Other"


def main():
    feat = pd.read_csv(ROOT / "data" / "processed" / "hr_featured.csv")
    pred = pd.read_csv(ROOT / "data" / "predictions" / "employee_attrition_predictions.csv")
    cfg = json.loads((ROOT / "models" / "model_config.json").read_text())

    # ---- fact_employees -----------------------------------------------------------------
    keep = ["EmployeeNumber", "Department", "JobRole", "JobLevel", "EducationField", "Education",
            "Gender", "AgeBand", "MaritalStatus",                      # composition / audit only (see guide)
            "BusinessTravel", "OverTime", "OvertimeFlag", "DistanceFromHome",
            "MonthlyIncome", "IncomeBand", "SalaryRatioToLevel", "JobLevelMedianIncome", "StockOptionLevel",
            "PercentSalaryHike", "PerformanceRating",
            "JobSatisfaction", "EnvironmentSatisfaction", "RelationshipSatisfaction", "WorkLifeBalance",
            "JobInvolvement", "SatisfactionIndex", "LowSatisfactionCount",
            "YearsAtCompany", "TenureBand", "YearsInCurrentRole", "YearsSinceLastPromotion",
            "YearsSincePromotionBand", "YearsWithCurrManager", "TotalWorkingYears", "NumCompaniesWorked",
            "TrainingTimesLastYear", "RoleShareOfTenure", "Attrition", "AttritionFlag"]
    fact = feat[keep].merge(
        pred[["EmployeeNumber", "PredictedProbability", "PredictedClass", "RiskBand", "TopRiskFactors", "Split"]],
        on="EmployeeNumber", validate="one_to_one")
    fact["SalaryPosition"] = pd.cut(fact.SalaryRatioToLevel, [0, 0.9, 1.1, 99],
                                    labels=["Below peers (<90%)", "In line (90-110%)", "Above peers (>110%)"])
    fact["TenureBandSort"] = fact.TenureBand.map({"New (0-2y)": 1, "Early (3-5y)": 2, "Mid (6-10y)": 3, "Long (11y+)": 4})
    fact["IncomeBandSort"] = fact.IncomeBand.map({"<5k": 1, "5k-10k": 2, "10k-15k": 3, "15k+": 4})
    fact["AgeBandSort"] = fact.AgeBand.map({"Under 25": 1, "25-34": 2, "35-44": 3, "45-54": 4, "55+": 5})
    fact["RiskBandSort"] = fact.RiskBand.map({"High": 1, "Elevated": 2, "Low": 3})
    fact.to_csv(OUT / "fact_employees.csv", index=False)

    # ---- scenario_sensitivity -----------------------------------------------------------
    scen = pd.read_csv(ROOT / "data" / "predictions" / "scenario_sensitivity.csv")
    scen["ScenarioLabel"] = scen.Scenario.map({
        "overtime_removed": "Overtime removed", "job_satisfaction_up": "Job satisfaction +1",
        "env_satisfaction_up": "Environment satisfaction +1", "wlb_up": "Work-life balance +1",
        "salary_to_peer_median": "Salary to 90% of level median"})
    scen.to_csv(OUT / "scenario_sensitivity.csv", index=False)

    # ---- feature_importance (global SHAP of the final model) -----------------------------
    # Safe: loads only the artifact this project trains itself (notebook 04). Never point this at an untrusted file:
    # joblib/pickle deserialization can execute arbitrary code.
    model = joblib.load(ROOT / "models" / "attrition_model.joblib")
    X = feat[cfg["input_features"]]
    vals, xs = [], []
    for cc in model.calibrated_classifiers_:
        p = cc.estimator
        names = list(p[:-1].named_steps["prep"].get_feature_names_out())
        Xt = pd.DataFrame(p[:-1].transform(X), columns=names)
        vals.append(shap.LinearExplainer(p[-1], Xt)(Xt).values)
        xs.append(Xt)
    sv = np.mean(vals, axis=0)
    Xt = xs[0]
    direction = [np.sign(np.corrcoef(Xt[c], sv[:, i])[0, 1]) if Xt[c].std() > 0 else 0 for i, c in enumerate(names)]
    imp = pd.DataFrame({"Feature": names, "MeanAbsSHAP": np.abs(sv).mean(0).round(4), "Direction": direction})
    imp["FeatureLabel"] = imp.Feature.map(LABELS).fillna(imp.Feature.str.replace("_", " = ", n=1))
    imp["Effect"] = np.where(imp.Direction > 0, "Higher value -> higher risk", "Higher value -> lower risk")
    imp["Category"] = imp.Feature.map(category_of)
    imp = imp.sort_values("MeanAbsSHAP", ascending=False).reset_index(drop=True)
    imp["Rank"] = imp.index + 1
    imp.to_csv(OUT / "feature_importance.csv", index=False)

    # ---- dim_risk_band ------------------------------------------------------------------
    t, h = cfg["threshold"], cfg["high_band_cutoff"]
    pd.DataFrame({
        "RiskBand": ["High", "Elevated", "Low"], "RiskBandSort": [1, 2, 3],
        "Rule": [f"score >= {h}", f"{t} <= score < {h}", f"score < {t}"],
        "Description": ["High-confidence group (train precision >= 60%)",
                        "Flagged by recall-oriented operating threshold",
                        "Not flagged"],
        "Color": ["#C0392B", "#E67E22", "#7F8C8D"]}).to_csv(OUT / "dim_risk_band.csv", index=False)

    # ---- model_metrics ------------------------------------------------------------------
    m = cfg["test_metrics"]
    pd.DataFrame([
        ("Model", cfg["selected_model"] + " (calibrated)"), ("Test PR-AUC", m["pr_auc"]),
        ("No-skill PR-AUC", 0.16), ("Test ROC-AUC", m["roc_auc"]), ("Operating threshold", t),
        ("Recall at threshold", m["recall"]), ("Precision at threshold", m["precision"]),
        ("High-band cut-off", h), ("Brier score", m["brier"]),
    ], columns=["Metric", "Value"]).to_csv(OUT / "model_metrics.csv", index=False)

    for f in sorted(OUT.glob("*.csv")):
        print(f"{f.name:28s} {len(pd.read_csv(f)):>6} rows")


if __name__ == "__main__":
    main()
