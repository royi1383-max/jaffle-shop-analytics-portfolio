"""
Health check — verifies DuckDB connection and prints row counts for all models.
Run this first to confirm the dbt pipeline ran successfully.

Usage:
    cd jaffle-shop-main
    python python/00_setup.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.db_connector import query

MODELS = {
    "raw": ["raw_customers", "raw_orders", "raw_items", "raw_products", "raw_stores", "raw_supplies"],
    "staging": ["stg_customers", "stg_orders", "stg_order_items", "stg_products", "stg_locations", "stg_supplies"],
    "marts": ["customers", "orders", "order_items", "products", "locations", "supplies"],
    "analytics": ["fct_daily_revenue", "fct_cohorts", "fct_customer_churn_features",
                  "fct_product_performance", "fct_location_performance", "fct_supply_cogs"],
}

EXPECTED = {
    "raw_customers": 935,
    "raw_orders": 61948,
    "raw_items": 90900,
}


def check():
    print("=" * 60)
    print("  Jaffle Shop — DuckDB Health Check")
    print("=" * 60)

    all_ok = True
    for layer, tables in MODELS.items():
        print(f"\n  [{layer.upper()}]")
        for table in tables:
            try:
                df = query(f"SELECT count(*) as n FROM {table}")
                n = df["n"].iloc[0]
                expected = EXPECTED.get(table)
                status = "OK"
                if expected and n != expected:
                    status = f"WARN (expected {expected:,})"
                    all_ok = False
                print(f"    {table:<40} {n:>8,} rows  [{status}]")
            except Exception as e:
                print(f"    {table:<40}          [ERROR: {e}]")
                all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("  All checks passed.")
    else:
        print("  Some checks failed — re-run `dbt run`.")
    print("=" * 60)


if __name__ == "__main__":
    check()
