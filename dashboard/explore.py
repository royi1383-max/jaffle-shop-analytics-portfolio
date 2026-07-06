"""
Quick visual exploration of the Jaffle Shop dataset.
Run:  streamlit run dashboard/explore.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "python"))

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

DB_PATH = str(Path(__file__).parents[1] / "jaffle_shop.duckdb")

st.set_page_config(page_title="Jaffle Shop — Data Exploration", layout="wide")


@st.cache_data
def q(sql):
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(sql).fetchdf()
    con.close()
    return df


# ── Header ────────────────────────────────────────────────────────
st.title("Jaffle Shop — Data Exploration")
st.caption("Portfolio project • dbt + DuckDB + Python + Streamlit")

# ── KPI Row ───────────────────────────────────────────────────────
overview = q("""
SELECT
    COUNT(DISTINCT customer_id)   AS customers,
    COUNT(order_id)               AS orders,
    ROUND(SUM(order_total), 0)    AS revenue,
    ROUND(AVG(order_total), 2)    AS aov,
    MIN(ordered_at)               AS first_order,
    MAX(ordered_at)               AS last_order
FROM orders
""").iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", f"${overview['revenue']:,.0f}")
c2.metric("Total Orders",  f"{overview['orders']:,}")
c3.metric("Customers",     f"{int(overview['customers']):,}")
c4.metric("Avg Order Value", f"${overview['aov']:.2f}")

st.caption(
    f"Data range: {str(overview['first_order'])[:10]} → {str(overview['last_order'])[:10]}"
)
st.divider()

# ── Tabs ──────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Revenue Trends",
    "👥 Customers & Cohorts",
    "🥪 Products",
    "📍 Locations",
    "🔍 Raw Data"
])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — REVENUE TRENDS
# ══════════════════════════════════════════════════════════════════
with tab1:
    col_a, col_b = st.columns([2, 1])

    with col_a:
        monthly = q("""
        SELECT
            date_trunc('month', ordered_at)            AS month,
            ROUND(SUM(order_total), 0)                 AS revenue,
            COUNT(order_id)                            AS orders,
            ROUND(AVG(order_total), 2)                 AS aov,
            COUNT(DISTINCT customer_id)                AS unique_customers
        FROM orders
        GROUP BY 1
        ORDER BY 1
        """)
        monthly["month"] = pd.to_datetime(monthly["month"])

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(x=monthly["month"], y=monthly["revenue"],
                   name="Revenue ($)", marker_color="#4C78A8"),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(x=monthly["month"], y=monthly["orders"],
                       name="Orders", line=dict(color="#F58518", width=2),
                       mode="lines+markers"),
            secondary_y=True,
        )
        fig.update_layout(
            title="Monthly Revenue & Order Volume",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            hovermode="x unified",
        )
        fig.update_yaxes(title_text="Revenue ($)", secondary_y=False)
        fig.update_yaxes(title_text="Orders", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        # MoM growth
        monthly["revenue_prev"] = monthly["revenue"].shift(1)
        monthly["mom_growth"] = (
            (monthly["revenue"] - monthly["revenue_prev"])
            / monthly["revenue_prev"] * 100
        ).round(1)
        growth_df = monthly[["month", "revenue", "mom_growth"]].dropna()
        growth_df["month_label"] = growth_df["month"].dt.strftime("%b %Y")

        fig2 = px.bar(
            growth_df,
            x="month_label", y="mom_growth",
            color=growth_df["mom_growth"].apply(lambda x: "positive" if x >= 0 else "negative"),
            color_discrete_map={"positive": "#54A24B", "negative": "#E45756"},
            labels={"mom_growth": "MoM Growth %", "month_label": ""},
            title="Month-over-Month Growth %",
        )
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Day of week
    dow = q("""
    SELECT
        dayname(ordered_at)                 AS day_of_week,
        dayofweek(ordered_at)               AS day_num,
        COUNT(order_id)                     AS orders,
        ROUND(SUM(order_total), 0)          AS revenue,
        ROUND(AVG(order_total), 2)          AS aov
    FROM orders
    GROUP BY 1, 2
    ORDER BY 2
    """)
    fig3 = px.bar(
        dow, x="day_of_week", y="revenue",
        color="aov", color_continuous_scale="Blues",
        labels={"revenue": "Revenue ($)", "day_of_week": "", "aov": "Avg Order ($)"},
        title="Revenue by Day of Week",
        text=dow["aov"].apply(lambda x: f"AOV ${x}"),
    )
    st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════
# TAB 2 — CUSTOMERS & COHORTS
# ══════════════════════════════════════════════════════════════════
with tab2:
    col_a, col_b = st.columns(2)

    with col_a:
        # LTV distribution
        ltv = q("""
        SELECT lifetime_spend
        FROM customers
        WHERE lifetime_spend IS NOT NULL AND lifetime_spend > 0
        """)
        fig4 = px.histogram(
            ltv, x="lifetime_spend", nbins=40,
            labels={"lifetime_spend": "Lifetime Spend ($)", "count": "Customers"},
            title="Customer Lifetime Value Distribution",
            color_discrete_sequence=["#4C78A8"],
        )
        fig4.add_vline(
            x=ltv["lifetime_spend"].median(),
            line_dash="dash", line_color="orange",
            annotation_text=f"Median ${ltv['lifetime_spend'].median():.0f}",
        )
        st.plotly_chart(fig4, use_container_width=True)

    with col_b:
        # Orders per customer
        order_freq = q("""
        SELECT count_lifetime_orders AS n_orders, COUNT(*) AS customers
        FROM customers
        WHERE count_lifetime_orders IS NOT NULL
        GROUP BY 1
        ORDER BY 1
        """)
        fig5 = px.bar(
            order_freq[order_freq["n_orders"] <= 150],
            x="n_orders", y="customers",
            labels={"n_orders": "Number of Orders", "customers": "Customers"},
            title="Orders per Customer Distribution",
            color_discrete_sequence=["#72B7B2"],
        )
        st.plotly_chart(fig5, use_container_width=True)

    # Cohort heatmap
    cohorts = q("""
    SELECT cohort_month, months_since_first_order, ROUND(retention_rate * 100, 1) AS retention_pct
    FROM fct_cohorts
    WHERE months_since_first_order <= 11
    ORDER BY cohort_month, months_since_first_order
    """)
    cohorts["cohort_label"] = pd.to_datetime(cohorts["cohort_month"]).dt.strftime("%b %Y")

    pivot = cohorts.pivot(
        index="cohort_label",
        columns="months_since_first_order",
        values="retention_pct",
    )
    pivot.columns = [f"Month {c}" for c in pivot.columns]

    fig6 = px.imshow(
        pivot,
        text_auto=True,
        color_continuous_scale="Blues",
        aspect="auto",
        title="Cohort Retention Heatmap — % of original cohort still active",
        labels={"color": "Retention %"},
    )
    fig6.update_coloraxes(cmin=0, cmax=100)
    st.plotly_chart(fig6, use_container_width=True)


# ══════════════════════════════════════════════════════════════════
# TAB 3 — PRODUCTS
# ══════════════════════════════════════════════════════════════════
with tab3:
    products = q("SELECT * FROM fct_supply_cogs ORDER BY gross_margin_pct DESC")

    col_a, col_b = st.columns([3, 2])

    with col_a:
        fig7 = px.scatter(
            products,
            x="total_revenue", y="gross_margin_pct",
            size="units_sold", color="product_type",
            hover_name="product_name",
            color_discrete_map={"food": "#F58518", "beverage": "#4C78A8"},
            labels={
                "total_revenue": "Total Revenue ($)",
                "gross_margin_pct": "Gross Margin %",
                "product_type": "Type",
            },
            title="Product Performance — Revenue vs. Margin (size = units sold)",
        )
        # Add quadrant lines at medians
        med_rev = products["total_revenue"].median()
        med_margin = products["gross_margin_pct"].median()
        fig7.add_hline(y=med_margin, line_dash="dot", line_color="gray",
                       annotation_text=f"Median margin {med_margin:.0f}%")
        fig7.add_vline(x=med_rev, line_dash="dot", line_color="gray",
                       annotation_text=f"Median revenue ${med_rev:,.0f}")
        st.plotly_chart(fig7, use_container_width=True)

    with col_b:
        fig8 = px.bar(
            products.sort_values("gross_margin_pct"),
            x="gross_margin_pct", y="product_name",
            color="product_type",
            color_discrete_map={"food": "#F58518", "beverage": "#4C78A8"},
            orientation="h",
            labels={"gross_margin_pct": "Gross Margin %", "product_name": ""},
            title="Margin Ranking",
        )
        st.plotly_chart(fig8, use_container_width=True)

    # Supply cost breakdown
    supply_cols = ["product_name", "product_type",
                   "total_perishable_cost", "total_non_perishable_cost",
                   "total_revenue", "gross_margin_pct"]
    supply_plot = products[supply_cols].melt(
        id_vars=["product_name", "product_type", "total_revenue", "gross_margin_pct"],
        value_vars=["total_perishable_cost", "total_non_perishable_cost"],
        var_name="cost_type", value_name="cost",
    )
    supply_plot["cost_type"] = supply_plot["cost_type"].map({
        "total_perishable_cost": "Perishable",
        "total_non_perishable_cost": "Non-Perishable",
    })
    fig9 = px.bar(
        supply_plot,
        x="product_name", y="cost", color="cost_type",
        color_discrete_map={"Perishable": "#E45756", "Non-Perishable": "#72B7B2"},
        barmode="stack",
        labels={"cost": "Supply Cost ($)", "product_name": "", "cost_type": ""},
        title="Supply Cost Breakdown — Perishable vs. Non-Perishable (total)",
    )
    st.plotly_chart(fig9, use_container_width=True)


# ══════════════════════════════════════════════════════════════════
# TAB 4 — LOCATIONS
# ══════════════════════════════════════════════════════════════════
with tab4:
    loc = q("SELECT * FROM fct_location_performance")

    col_a, col_b = st.columns(2)
    with col_a:
        fig10 = px.bar(
            loc, x="location_name", y=["total_revenue", "total_cost"],
            barmode="stack",
            color_discrete_map={"total_revenue": "#4C78A8", "total_cost": "#E45756"},
            labels={"value": "$", "variable": "", "location_name": ""},
            title="Revenue vs. Cost by Location",
        )
        st.plotly_chart(fig10, use_container_width=True)

    with col_b:
        fig11 = px.bar(
            loc, x="location_name", y="revenue_per_month_open",
            color="location_name",
            labels={"revenue_per_month_open": "Revenue / Month Open ($)", "location_name": ""},
            title="Age-Normalized Revenue (Revenue per Month in Operation)",
            text=loc["revenue_per_month_open"].apply(lambda x: f"${x:,.0f}"),
        )
        fig11.update_layout(showlegend=False)
        st.plotly_chart(fig11, use_container_width=True)

    # Revenue over time by location
    loc_time = q("""
    SELECT
        date_trunc('month', ordered_at)     AS month,
        location_id,
        l.location_name,
        ROUND(SUM(order_total), 0)          AS revenue
    FROM orders o
    LEFT JOIN locations l USING (location_id)
    GROUP BY 1, 2, 3
    ORDER BY 1
    """)
    loc_time["month"] = pd.to_datetime(loc_time["month"])
    fig12 = px.line(
        loc_time, x="month", y="revenue", color="location_name",
        markers=True,
        labels={"revenue": "Monthly Revenue ($)", "month": "", "location_name": "Location"},
        title="Monthly Revenue by Location",
    )
    st.plotly_chart(fig12, use_container_width=True)


# ══════════════════════════════════════════════════════════════════
# TAB 5 — RAW DATA EXPLORER
# ══════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Run your own query")
    default_sql = "SELECT * FROM orders LIMIT 20"
    user_sql = st.text_area("SQL (DuckDB)", value=default_sql, height=80)
    if st.button("Run"):
        try:
            result = q(user_sql)
            st.dataframe(result, use_container_width=True)
            st.caption(f"{len(result):,} rows returned")
        except Exception as e:
            st.error(str(e))

    st.divider()
    st.subheader("Available tables")
    tables = q("""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema IN ('main', 'raw')
    ORDER BY table_schema, table_name
    """)
    st.dataframe(tables, use_container_width=True, hide_index=True)
