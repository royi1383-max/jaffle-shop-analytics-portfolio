"""
Interactive data exploration — run to see key findings from the dataset.
Usage:
    cd jaffle-shop-main
    python python/explore_data.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from utils.db_connector import query

SEP = "\n" + "=" * 65

# ── 1. OVERVIEW ──────────────────────────────────────────────────
print(SEP)
print("  1. DATASET OVERVIEW")
print("=" * 65)

overview = query("""
SELECT
    COUNT(DISTINCT customer_id)                         AS customers,
    COUNT(DISTINCT order_id)                            AS orders,
    (SELECT COUNT(*) FROM order_items)                  AS line_items,
    COUNT(DISTINCT location_id)                         AS active_locations,
    MIN(ordered_at)                                     AS first_order,
    MAX(ordered_at)                                     AS last_order,
    ROUND(SUM(order_total), 2)                          AS total_revenue,
    ROUND(AVG(order_total), 2)                          AS avg_order_value,
    ROUND(SUM(order_total) / COUNT(DISTINCT customer_id), 2) AS avg_ltv
FROM orders
""")
for col, val in overview.iloc[0].items():
    print(f"  {col:<30} {val}")

# ── 2. REVENUE TREND (monthly) ───────────────────────────────────
print(SEP)
print("  2. MONTHLY REVENUE TREND")
print("=" * 65)

monthly = query("""
SELECT
    date_trunc('month', ordered_at)         AS month,
    COUNT(order_id)                         AS orders,
    ROUND(SUM(order_total), 0)              AS revenue,
    ROUND(AVG(order_total), 2)              AS aov,
    COUNT(DISTINCT customer_id)             AS unique_customers
FROM orders
GROUP BY 1
ORDER BY 1
""")
print(monthly.to_string(index=False))

# ── 3. CUSTOMERS ─────────────────────────────────────────────────
print(SEP)
print("  3. CUSTOMER BREAKDOWN")
print("=" * 65)

customers = query("""
SELECT
    customer_type,
    COUNT(*)                                AS customer_count,
    ROUND(AVG(lifetime_spend), 2)           AS avg_ltv,
    ROUND(AVG(count_lifetime_orders), 1)    AS avg_orders,
    SUM(lifetime_spend)                     AS total_revenue
FROM customers
WHERE count_lifetime_orders IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC
""")
print(customers.to_string(index=False))

churn = query("""
SELECT
    is_churned,
    COUNT(*) AS customers,
    ROUND(AVG(lifetime_spend), 2) AS avg_ltv,
    ROUND(AVG(days_since_last_order), 0) AS avg_days_since_order
FROM fct_customer_churn_features
GROUP BY 1
ORDER BY 1
""")
print("\n  Churn breakdown (>90 days = churned):")
print(churn.to_string(index=False))

# ── 4. COHORT RETENTION (first 6 months) ─────────────────────────
print(SEP)
print("  4. COHORT RETENTION — first 6 months average")
print("=" * 65)

cohort_avg = query("""
SELECT
    months_since_first_order                AS month_n,
    COUNT(DISTINCT cohort_month)            AS cohorts,
    ROUND(AVG(retention_rate) * 100, 1)    AS avg_retention_pct
FROM fct_cohorts
WHERE months_since_first_order <= 6
GROUP BY 1
ORDER BY 1
""")
print(cohort_avg.to_string(index=False))

# ── 5. PRODUCTS ──────────────────────────────────────────────────
print(SEP)
print("  5. PRODUCT PERFORMANCE (all time)")
print("=" * 65)

products = query("""
SELECT
    product_name,
    product_type,
    units_sold,
    ROUND(total_revenue, 0)     AS revenue,
    ROUND(gross_margin_pct, 1)  AS margin_pct,
    ROUND(perishable_pct_of_revenue, 1) AS perishable_risk_pct
FROM fct_supply_cogs
ORDER BY gross_margin_pct DESC
""")
print(products.to_string(index=False))

# ── 6. LOCATIONS ─────────────────────────────────────────────────
print(SEP)
print("  6. LOCATION BENCHMARKING")
print("=" * 65)

locations = query("""
SELECT
    location_name,
    total_orders,
    ROUND(total_revenue, 0)             AS revenue,
    ROUND(avg_order_value, 2)           AS aov,
    months_open,
    ROUND(revenue_per_month_open, 0)    AS rev_per_month,
    ROUND(gross_margin_pct, 1)          AS margin_pct
FROM fct_location_performance
JOIN (
    SELECT location_id, ROUND(total_gross_profit / NULLIF(total_revenue,0)*100,1) AS gross_margin_pct
    FROM fct_location_performance
) gm USING (location_id)
ORDER BY revenue_rank
""")
print(locations.to_string(index=False))

# ── 7. ORDER COMPOSITION ─────────────────────────────────────────
print(SEP)
print("  7. ORDER COMPOSITION")
print("=" * 65)

composition = query("""
SELECT
    CASE
        WHEN is_food_order AND NOT is_drink_order THEN 'Food only'
        WHEN is_drink_order AND NOT is_food_order THEN 'Drink only'
        WHEN is_food_order AND is_drink_order     THEN 'Mixed (food+drink)'
        ELSE 'Unknown'
    END AS order_type,
    COUNT(*) AS orders,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct,
    ROUND(AVG(order_total), 2) AS avg_order_value
FROM orders
GROUP BY 1
ORDER BY 2 DESC
""")
print(composition.to_string(index=False))

print(SEP)
print("  Run complete. All numbers are from the live DuckDB database.")
print("=" * 65)
