"""Model evaluation and fairness helpers for Workforce Pulse."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,
                             confusion_matrix, f1_score, precision_score, recall_score,
                             roc_auc_score)
from statsmodels.stats.proportion import proportion_confint


def classification_metrics(y_true, proba, threshold: float = 0.5) -> dict:
    y_true = np.asarray(y_true)
    pred = (np.asarray(proba) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        "threshold": threshold,
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall": recall_score(y_true, pred, zero_division=0),
        "f1": f1_score(y_true, pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, proba),
        "pr_auc": average_precision_score(y_true, proba),
        "brier": brier_score_loss(y_true, proba),
        "flag_rate": pred.mean(),
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
    }


def threshold_table(y_true, proba, thresholds=None) -> pd.DataFrame:
    thresholds = np.round(np.arange(0.10, 0.81, 0.05), 2) if thresholds is None else thresholds
    rows = [classification_metrics(y_true, proba, t) for t in thresholds]
    return pd.DataFrame(rows)[["threshold", "precision", "recall", "f1", "flag_rate", "tp", "fp", "fn", "tn"]]


def _rate_ci(k: int, n: int):
    if n == 0:
        return (np.nan, np.nan)
    return proportion_confint(k, n, alpha=0.05, method="wilson")


def group_fairness(y_true, proba, groups, threshold: float) -> pd.DataFrame:
    """Per-group error profile with 95% Wilson intervals for the rates."""
    d = pd.DataFrame({"y": np.asarray(y_true), "p": np.asarray(proba), "g": np.asarray(groups)})
    d["pred"] = (d.p >= threshold).astype(int)
    rows = []
    for g, s in d.groupby("g", observed=True):
        pos, neg = s[s.y == 1], s[s.y == 0]
        k_flag, k_tp, k_fp, k_fn = s.pred.sum(), pos.pred.sum(), neg.pred.sum(), (1 - pos.pred).sum()
        row = {
            "group": g, "n": len(s), "actual_leavers": len(pos),
            "base_rate": s.y.mean(),
            "mean_predicted_risk": s.p.mean(),
            "flag_rate": k_flag / len(s),
            "recall_TPR": k_tp / len(pos) if len(pos) else np.nan,
            "FPR": k_fp / len(neg) if len(neg) else np.nan,
            "FNR": k_fn / len(pos) if len(pos) else np.nan,
            "precision": k_tp / k_flag if k_flag else np.nan,
        }
        row["flag_rate_CI"] = _rate_ci(k_flag, len(s))
        row["recall_CI"] = _rate_ci(k_tp, len(pos))
        row["FPR_CI"] = _rate_ci(k_fp, len(neg))
        rows.append(row)
    return pd.DataFrame(rows)
