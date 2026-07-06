"""
Churn model — Logistic Regression + Random Forest, explained with SHAP.
Usage:
    cd jaffle-shop-main
    python python/04_churn_model.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils.churn_model import train_and_evaluate

SEP = "\n" + "=" * 65

results = train_and_evaluate()

print(SEP)
print("  CHURN LABEL")
print("=" * 65)
print(f"  Churn rate (30-day holdout window): {results['churn_rate']:.1%}")
print(f"  Train rows: {results['n_train']}   Test rows: {results['n_test']}")
print("  Note: the original 90-day-from-dataset-end definition produced")
print("  only 1 churned customer out of 935 (this customer base orders")
print("  every 3-6 days, and the dataset ends while still fully active).")
print("  Rebuilt with a genuine 30-day holdout window instead - see")
print("  models/marts/analytics/_analytics_models.yml for details.")

print(SEP)
print("  FEATURE SELECTION - a second issue found during development")
print("=" * 65)
print("  A first pass included days_since_last_order / orders_last_30_days")
print("  / orders_prior_30_days / order_frequency_trend and scored ~100%")
print("  ROC-AUC - too good to trust. Those features all derive from the")
print("  same pre-cutoff recency window the label checks against: a")
print("  customer with 0 orders in the 30 days before cutoff has a 97%")
print("  chance of 0 after too (customers who go quiet here essentially")
print("  never come back). That's a near-tautological restatement of the")
print("  label, not an early-warning signal, so those 4 features were")
print("  dropped. The model below uses only lifetime/behavioral features.")

print(SEP)
print("  LOGISTIC REGRESSION (class_weight=balanced)")
print("=" * 65)
for k, v in results["logreg_metrics"].items():
    print(f"  {k:<12} {v:.3f}")

print(SEP)
print("  RANDOM FOREST (class_weight=balanced, used for scoring)")
print("=" * 65)
for k, v in results["rf_metrics"].items():
    print(f"  {k:<12} {v:.3f}")
print()
print("  Still very high - food_item_pct/drink_item_pct/avg_order_value")
print("  dominate. Churned customers skew ~33% food-heavy vs. 18% for")
print("  retained ones, with lower average order value: an occasional-")
print("  treat buying pattern is a real, interpretable churn signal here.")
print("  Scores this high are still cleaner than most real-world churn")
print("  models get - likely because this is synthetic data generated")
print("  from a small number of consistent customer archetypes, which is")
print("  more separable than noisy real purchase behavior. Worth stating")
print("  explicitly rather than presenting it as production-grade accuracy.")

print(SEP)
print("  TOP FEATURES BY MEAN |SHAP VALUE| (Random Forest)")
print("=" * 65)
for feat, val in results["mean_abs_shap"].items():
    print(f"  {feat:<28} {val:.4f}")

print(SEP)
print("  TOP 10 AT-RISK CUSTOMERS (highest predicted churn probability)")
print("=" * 65)
top_risk = results["predictions_df"].sort_values("churn_probability", ascending=False).head(10)
print(top_risk[["customer_name", "churn_probability", "is_churned"]].to_string(index=False))
