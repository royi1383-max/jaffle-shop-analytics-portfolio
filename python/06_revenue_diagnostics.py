"""
Revenue anomaly detection — STL decomposition (trend + weekly seasonality)
with residual z-score flagging.
Usage:
    cd jaffle-shop-main
    python python/06_revenue_diagnostics.py
"""
import sys
from pathlib import Path

import pandas as pd
from statsmodels.tsa.seasonal import STL

sys.path.insert(0, str(Path(__file__).parent))
from utils.db_connector import query

SEP = "\n" + "=" * 65
Z_THRESHOLD = 2.5

df = query("select date_day, sum(total_revenue) as revenue from fct_daily_revenue group by 1 order by 1")
df = df.set_index("date_day")
df.index = pd.DatetimeIndex(df.index).to_period("D").to_timestamp()

stl = STL(df["revenue"], period=7, robust=True)
result = stl.fit()

df["trend"] = result.trend
df["seasonal"] = result.seasonal
df["resid"] = result.resid
df["z_score"] = (df["resid"] - df["resid"].mean()) / df["resid"].std()

anomalies = df[df["z_score"].abs() > Z_THRESHOLD].sort_values("z_score", key=abs, ascending=False)

print(SEP)
print("  REVENUE DECOMPOSITION (STL: trend + weekly seasonality + residual)")
print("=" * 65)
print(f"  Date range: {df.index.min().date()} to {df.index.max().date()} ({len(df)} days)")
print(f"  Anomaly threshold: |z-score| > {Z_THRESHOLD}")
print(f"  Anomalous days found: {len(anomalies)} ({len(anomalies) / len(df):.1%} of days)")

print(SEP)
print("  TOP ANOMALOUS DAYS")
print("=" * 65)
print(anomalies[["revenue", "trend", "resid", "z_score"]].head(15).to_string())

print(SEP)
print("  INTERPRETATION")
print("=" * 65)
spikes = anomalies[anomalies["z_score"] > 0]
drops = anomalies[anomalies["z_score"] < 0]
print(f"  Positive spikes (revenue above trend+seasonal expectation): {len(spikes)}")
print(f"  Negative drops (revenue below expectation): {len(drops)}")
print("  These are candidate dates to investigate for promotions, holidays,")
print("  supply issues, or data quality problems.")
