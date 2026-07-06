"""
Shared churn model — trains Logistic Regression + Random Forest on
fct_customer_churn_features and returns predictions + SHAP explanations.

Imported by both python/04_churn_model.py (terminal report) and
dashboard/pages/6_Predictions.py (interactive view), so the model is
trained exactly once and both surfaces stay consistent.
"""
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from utils.db_connector import query

# Deliberately excludes days_since_last_order, orders_last_30_days,
# orders_prior_30_days, and order_frequency_trend. All four are derived
# from the same pre-cutoff recency window the churn label is checking
# against the future of — a customer with 0 orders in the 30 days before
# the cutoff has a 97% chance of also having 0 in the 30 days after, since
# customers who go quiet in this dataset essentially never come back. That
# makes those features near-tautological restatements of the label, not
# genuine early-warning signals, and a model trained on them scores a
# suspicious ~100% (which is how this was caught). The features below are
# lifetime/behavioral rather than recency-window snapshots, so the model
# has to find real signal instead of just re-detecting "already inactive."
FEATURE_COLS = [
    "count_lifetime_orders",
    "lifetime_spend",
    "avg_order_value",
    "avg_days_between_orders",
    "stddev_days_between_orders",
    "food_item_pct",
    "drink_item_pct",
]
TARGET_COL = "is_churned"


def load_features() -> pd.DataFrame:
    return query(f"select customer_id, customer_name, {', '.join(FEATURE_COLS)}, {TARGET_COL} "
                 f"from fct_customer_churn_features")


def train_and_evaluate(random_state: int = 42) -> dict:
    df = load_features()

    # avg/stddev_days_between_orders are null for customers with only one
    # order in the train window (no gap to compute) — impute with the
    # median rather than dropping them, since that would bias out
    # low-frequency (higher-churn-risk) customers.
    X = df[FEATURE_COLS].copy()
    imputer = SimpleImputer(strategy="median")
    X_imputed = pd.DataFrame(imputer.fit_transform(X), columns=FEATURE_COLS, index=X.index)
    y = df[TARGET_COL].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X_imputed, y, test_size=0.25, random_state=random_state, stratify=y
    )

    # Logistic Regression — scaled, class_weight balanced for the 18/82 split
    logreg = Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=random_state)),
    ])
    logreg.fit(X_train, y_train)
    logreg_proba = logreg.predict_proba(X_test)[:, 1]
    logreg_pred = logreg.predict(X_test)

    # Random Forest — handles non-linear interactions, also class-weighted
    rf = RandomForestClassifier(
        n_estimators=300, max_depth=6, class_weight="balanced",
        random_state=random_state, n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    rf_proba = rf.predict_proba(X_test)[:, 1]
    rf_pred = rf.predict(X_test)

    def _metrics(y_true, y_pred, y_proba) -> dict:
        return {
            "precision": precision_score(y_true, y_pred, zero_division=0),
            "recall":    recall_score(y_true, y_pred, zero_division=0),
            "f1":        f1_score(y_true, y_pred, zero_division=0),
            "roc_auc":   roc_auc_score(y_true, y_proba),
        }

    logreg_metrics = _metrics(y_test, logreg_pred, logreg_proba)
    rf_metrics = _metrics(y_test, rf_pred, rf_proba)

    # SHAP on the Random Forest — TreeExplainer is exact and fast for trees
    explainer = shap.TreeExplainer(rf)
    shap_values = explainer.shap_values(X_test)
    # shap_values is (n_samples, n_features, n_classes) in recent SHAP versions
    if isinstance(shap_values, list):
        shap_for_churn = shap_values[1]
    elif shap_values.ndim == 3:
        shap_for_churn = shap_values[:, :, 1]
    else:
        shap_for_churn = shap_values
    mean_abs_shap = pd.Series(
        np.abs(shap_for_churn).mean(axis=0), index=FEATURE_COLS
    ).sort_values(ascending=False)

    # Full-dataset churn probability (for the dashboard's at-risk list) —
    # scored with the Random Forest since it outperforms on recall in
    # practice for this feature set.
    full_proba = rf.predict_proba(X_imputed)[:, 1]
    predictions_df = df[["customer_id", "customer_name", TARGET_COL]].copy()
    predictions_df["churn_probability"] = full_proba

    return {
        "logreg_metrics": logreg_metrics,
        "rf_metrics": rf_metrics,
        "mean_abs_shap": mean_abs_shap,
        "predictions_df": predictions_df,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "churn_rate": y.mean(),
    }
