"""
LTV forecast — BG/NBD (purchase frequency) + Gamma-Gamma (spend), via `lifetimes`.
Usage:
    cd jaffle-shop-main
    python python/05_ltv_forecast.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils.ltv_model import fit_and_forecast

SEP = "\n" + "=" * 65

results = fit_and_forecast(forecast_days=90)
repeat = results["repeat_customers"]
forecast_days = results["forecast_days"]

print(SEP)
print("  RFM SUMMARY (built from full order history)")
print("=" * 65)
print(f"  Total customers: {len(results['summary'])}")
print(f"  Repeat customers (frequency > 0): {len(repeat)}")
print(f"  One-time customers (excluded from Gamma-Gamma): {results['non_repeat_count']}")
print(f"  Frequency/monetary correlation: {results['freq_monetary_corr']:.3f}")
print("  (Gamma-Gamma assumes ~0 correlation - treat CLV as directional, not exact.)")

print(SEP)
print(f"  FORECAST - next {forecast_days} days")
print("=" * 65)
print(repeat[["predicted_avg_order_value", f"expected_purchases_{forecast_days}d", "clv_forecast"]].describe().to_string())

print(SEP)
print("  TOP 10 CUSTOMERS BY FORECASTED LTV")
print("=" * 65)
top_ltv = repeat.sort_values("clv_forecast", ascending=False).head(10)
print(top_ltv[["frequency", "recency", "T", "monetary_value", "clv_forecast"]].to_string())

print(SEP)
print("  TOTAL FORECASTED VALUE")
print("=" * 65)
print(f"  Sum of CLV across all repeat customers ({forecast_days}d): ${repeat['clv_forecast'].sum():,.2f}")
