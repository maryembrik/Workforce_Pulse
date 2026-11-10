"""Cleaning and feature engineering for Workforce Pulse.

Two kinds of features:
* Row-wise features (bands, flags, indices) depend only on the employee's own record,
  so they can be computed on the full dataset without leakage.
* Peer-referenced features (salary vs. JobLevel peers) depend on other employees.
  For modelling they are learned on the training split only, via `PeerSalaryRatio`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

CONSTANT_COLS = ["EmployeeCount", "Over18", "StandardHours"]

# Undocumented rate columns: excluded from the model after Phase 1 showed they do not
# track MonthlyIncome or JobLevel (see reports/data_quality_report.md).
UNDOCUMENTED_RATE_COLS = ["DailyRate", "HourlyRate", "MonthlyRate"]

SATISFACTION_ITEMS = ["JobSatisfaction", "EnvironmentSatisfaction",
                      "RelationshipSatisfaction", "WorkLifeBalance"]

TENURE_BINS = [-1, 2, 5, 10, np.inf]
TENURE_LABELS = ["New (0-2y)", "Early (3-5y)", "Mid (6-10y)", "Long (11y+)"]

AGE_BINS = [0, 24, 34, 44, 54, np.inf]
AGE_LABELS = ["Under 25", "25-34", "35-44", "45-54", "55+"]

INCOME_BINS = [0, 5000, 10000, 15000, np.inf]
INCOME_LABELS = ["<5k", "5k-10k", "10k-15k", "15k+"]


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy: constants dropped, text trimmed, binary target added."""
    df = raw.copy()
    obj = df.select_dtypes(include=["object", "string"]).columns
    df[obj] = df[obj].apply(lambda s: s.str.strip())
    df = df.drop(columns=[c for c in CONSTANT_COLS if c in df.columns])
    df = df.drop_duplicates()
    df["AttritionFlag"] = df["Attrition"].map({"Yes": 1, "No": 0}).astype(int)
    df["OvertimeFlag"] = df["OverTime"].map({"Yes": 1, "No": 0}).astype(int)
    return df


def add_row_features(df: pd.DataFrame) -> pd.DataFrame:
    """Row-wise engineered features (no information from other employees)."""
    out = df.copy()
    out["TenureBand"] = pd.cut(out["YearsAtCompany"], TENURE_BINS, labels=TENURE_LABELS)
    out["AgeBand"] = pd.cut(out["Age"], AGE_BINS, labels=AGE_LABELS)            # audit / EDA only
    out["IncomeBand"] = pd.cut(out["MonthlyIncome"], INCOME_BINS, labels=INCOME_LABELS, right=False)

    # Satisfaction index: all four items are 1-4 scales -> mean, rescaled to 0-1.
    # Equal weights are a design assumption, not a validated HR instrument.
    out["SatisfactionIndex"] = ((out[SATISFACTION_ITEMS].mean(axis=1) - 1) / 3).round(4)
    out["LowSatisfactionCount"] = (out[SATISFACTION_ITEMS] == 1).sum(axis=1)

    # Share of company tenure spent in the current role. YearsAtCompany == 0 implies the
    # employee is in their first role, so the share is defined as 1.0.
    out["RoleShareOfTenure"] = np.where(
        out["YearsAtCompany"] > 0, out["YearsInCurrentRole"] / out["YearsAtCompany"].clip(lower=1), 1.0
    ).round(4)
    out["YearsSincePromotionBand"] = pd.cut(
        out["YearsSinceLastPromotion"], [-1, 1, 4, np.inf], labels=["0-1y", "2-4y", "5y+"]
    )
    return out


def add_peer_salary_ratio(df: pd.DataFrame, reference: pd.DataFrame | None = None) -> pd.DataFrame:
    """Salary relative to the median of JobLevel peers (descriptive use: reference = df)."""
    ref = df if reference is None else reference
    med = ref.groupby("JobLevel")["MonthlyIncome"].median()
    out = df.copy()
    out["JobLevelMedianIncome"] = out["JobLevel"].map(med)
    out["SalaryRatioToLevel"] = (out["MonthlyIncome"] / out["JobLevelMedianIncome"]).round(4)
    return out


class PeerSalaryRatio(BaseEstimator, TransformerMixin):
    """Leakage-safe version for pipelines: medians learned in fit() on training data only."""

    def fit(self, X, y=None):
        self.medians_ = X.groupby("JobLevel")["MonthlyIncome"].median()
        self.global_median_ = X["MonthlyIncome"].median()
        return self

    def transform(self, X):
        X = X.copy()
        ref = X["JobLevel"].map(self.medians_).fillna(self.global_median_)
        X["SalaryRatioToLevel"] = X["MonthlyIncome"] / ref
        return X

    def get_feature_names_out(self, input_features=None):
        return np.append(np.asarray(input_features, dtype=object), "SalaryRatioToLevel")


# ---- Model feature specification -------------------------------------------------------
MODEL_CATEGORICAL = ["BusinessTravel", "Department", "EducationField", "JobRole", "OverTime"]
MODEL_NUMERIC = [
    "DistanceFromHome", "Education", "EnvironmentSatisfaction", "JobInvolvement", "JobLevel",
    "JobSatisfaction", "MonthlyIncome", "NumCompaniesWorked", "PercentSalaryHike",
    "PerformanceRating", "RelationshipSatisfaction", "StockOptionLevel", "TotalWorkingYears",
    "TrainingTimesLastYear", "WorkLifeBalance", "YearsAtCompany", "YearsInCurrentRole",
    "YearsSinceLastPromotion", "YearsWithCurrManager", "RoleShareOfTenure",
]
# SalaryRatioToLevel is appended inside the pipeline by PeerSalaryRatio.
