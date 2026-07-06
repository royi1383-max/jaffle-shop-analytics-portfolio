import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / "python"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import duckdb

st.set_page_config(page_title="Locations", page_icon="📍", layout="wide")

DB_PATH = str(Path(__file__).parents[2] / "jaffle_shop.duckdb")

@st.cache_data
def load(sql):
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(sql).fetchdf()
    con.close()
    return df

st.title("📍 Location Benchmarking")

lp = load("SELECT * FROM fct_location_performance")
loc_monthly = load("""
SELECT date_trunc('month', o.ordered_at) AS month,
       l.location_name,
       COUNT(o.order_id)                 AS orders,
       ROUND(SUM(o.order_total), 0)      AS revenue,
       ROUND(AVG(o.order_total), 2)      AS aov,
       COUNT(DISTINCT o.customer_id)     AS customers,
       datediff('month', l.opened_date, date_trunc('month', o.ordered_at)) AS months_since_open
FROM orders o JOIN locations l USING (location_id)
GROUP BY 1,2,l.opened_date ORDER BY 1
""")
loc_monthly["month"] = pd.to_datetime(loc_monthly["month"])

tab1, tab2, tab3 = st.tabs(["Comparison", "Over Time", "Spider Chart"])

# ── TAB 1: SIDE BY SIDE ───────────────────────────────────────────
with tab1:
    col1, col2, col3 = st.columns(3)

    philly = lp[lp["location_name"] == "Philadelphia"].iloc[0]
    bk     = lp[lp["location_name"] == "Brooklyn"].iloc[0]

    with col1:
        st.metric("Philadelphia — Revenue", f"${philly['total_revenue']:,.0f}")
        st.metric("Philadelphia — Orders",  f"{philly['total_orders']:,}")
        st.metric("Philadelphia — AOV",     f"${philly['avg_order_value']:.2f}")
        st.metric("Philadelphia — Rev/Month", f"${philly['revenue_per_month_open']:,.0f}")
    with col2:
        st.metric("Brooklyn — Revenue",     f"${bk['total_revenue']:,.0f}",
                  delta=f"{(bk['total_revenue']/philly['total_revenue']-1)*100:.0f}% vs Philly")
        st.metric("Brooklyn — Orders",      f"{bk['total_orders']:,}",
                  delta=f"{(bk['total_orders']/philly['total_orders']-1)*100:.0f}%")
        st.metric("Brooklyn — AOV",         f"${bk['avg_order_value']:.2f}",
                  delta=f"{(bk['avg_order_value']/philly['avg_order_value']-1)*100:.0f}%")
        st.metric("Brooklyn — Rev/Month",   f"${bk['revenue_per_month_open']:,.0f}",
                  delta=f"{(bk['revenue_per_month_open']/philly['revenue_per_month_open']-1)*100:.0f}%")
    with col3:
        st.info("""
        **Philadelphia** has been open 107 months and generates **$4,215/month**.

        **Brooklyn** has been open 101 months and generates **$2,183/month** —
        about **48% less per month** despite similar age.

        **Key question:** Is Brooklyn underperforming due to market size,
        operations, or product mix?
        """)

    # Grouped bar
    metrics = ["total_orders", "avg_order_value", "new_customer_order_pct",
               "food_revenue_pct", "drink_revenue_pct"]
    lp_melt = lp.melt(id_vars="location_name", value_vars=metrics,
                       var_name="metric", value_name="value")
    label_map = {
        "total_orders":            "Total Orders",
        "avg_order_value":         "Avg Order Value ($)",
        "new_customer_order_pct":  "New Customer Order %",
        "food_revenue_pct":        "Food Revenue %",
        "drink_revenue_pct":       "Drink Revenue %",
    }
    lp_melt["metric"] = lp_melt["metric"].map(label_map)

    fig = px.bar(
        lp_melt, x="metric", y="value", color="location_name",
        barmode="group",
        color_discrete_sequence=["#4C78A8", "#F58518"],
        labels={"value": "Value", "metric": "", "location_name": "Location"},
        title="Key Metrics Comparison",
    )
    st.plotly_chart(fig, use_container_width=True)

# ── TAB 2: OVER TIME ──────────────────────────────────────────────
with tab2:
    fig2 = px.line(
        loc_monthly, x="month", y="revenue",
        color="location_name", markers=True,
        color_discrete_sequence=["#4C78A8", "#F58518"],
        labels={"revenue": "Monthly Revenue ($)", "month": "",
                "location_name": "Location"},
        title="Monthly Revenue by Location",
    )
    fig2.update_layout(hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig3 = px.line(
            loc_monthly, x="months_since_open", y="revenue",
            color="location_name", markers=True,
            color_discrete_sequence=["#4C78A8", "#F58518"],
            labels={"revenue": "Monthly Revenue ($)",
                    "months_since_open": "Months since opening",
                    "location_name": "Location"},
            title="Revenue vs. Store Age (normalized)",
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        fig4 = px.line(
            loc_monthly, x="month", y="aov",
            color="location_name", markers=True,
            color_discrete_sequence=["#4C78A8", "#F58518"],
            labels={"aov": "Avg Order Value ($)", "month": "",
                    "location_name": "Location"},
            title="Avg Order Value Trend",
        )
        fig4.update_layout(hovermode="x unified")
        st.plotly_chart(fig4, use_container_width=True)

# ── TAB 3: SPIDER / RADAR CHART ───────────────────────────────────
with tab3:
    st.caption("Radar chart normalizes each metric to 0–1 scale for fair comparison.")

    dims = {
        "Revenue":          "total_revenue",
        "Orders":           "total_orders",
        "AOV":              "avg_order_value",
        "Rev/Month":        "revenue_per_month_open",
        "New Cust %":       "new_customer_order_pct",
    }

    # Normalize 0-1
    radar_df = lp[["location_name"] + list(dims.values())].copy()
    for col in dims.values():
        col_max = radar_df[col].max()
        col_min = radar_df[col].min()
        if col_max > col_min:
            radar_df[col] = (radar_df[col] - col_min) / (col_max - col_min)
        else:
            radar_df[col] = 1.0

    categories = list(dims.keys())
    colors = ["#4C78A8", "#F58518"]

    def _hex_to_rgba(hex_color: str, alpha: float = 0.2) -> str:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    fig5 = go.Figure()
    for i, row in radar_df.iterrows():
        vals = [row[v] for v in dims.values()]
        vals_closed = vals + [vals[0]]
        cats_closed = categories + [categories[0]]
        fig5.add_trace(go.Scatterpolar(
            r=vals_closed, theta=cats_closed,
            fill="toself", name=row["location_name"],
            line=dict(color=colors[i % len(colors)]),
            fillcolor=_hex_to_rgba(colors[i % len(colors)]),
        ))
    fig5.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="Location Performance Radar (normalized)",
        height=480,
    )
    st.plotly_chart(fig5, use_container_width=True)
