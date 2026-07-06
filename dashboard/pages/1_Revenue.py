import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / "python"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import duckdb

st.set_page_config(page_title="Revenue", page_icon="📈", layout="wide")

DB_PATH = str(Path(__file__).parents[2] / "jaffle_shop.duckdb")

@st.cache_data
def load(sql):
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(sql).fetchdf()
    con.close()
    return df

start = st.session_state.get("start_date", "2024-09-01")
end   = st.session_state.get("end_date",   "2025-08-31")
locs  = st.session_state.get("selected_locs", ["Philadelphia", "Brooklyn"])
loc_filter = ", ".join(f"'{l}'" for l in locs)

st.title("📈 Revenue Deep Dive")
tab1, tab2, tab3, tab4 = st.tabs(["Trends", "By Location", "By Product", "Diagnostics"])

# ── TAB 1: TRENDS ─────────────────────────────────────────────────
with tab1:
    weekly = load(f"""
    SELECT
        date_trunc('week', o.ordered_at)    AS week,
        ROUND(SUM(o.order_total), 0)        AS revenue,
        COUNT(o.order_id)                   AS orders,
        ROUND(AVG(o.order_total), 2)        AS aov
    FROM orders o JOIN locations l USING (location_id)
    WHERE o.ordered_at BETWEEN '{start}' AND '{end}'
      AND l.location_name IN ({loc_filter})
    GROUP BY 1 ORDER BY 1
    """)
    weekly["week"] = pd.to_datetime(weekly["week"])
    weekly["ma4"]  = weekly["revenue"].rolling(4).mean().round(0)
    weekly["wow"]  = weekly["revenue"].pct_change().mul(100).round(1)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weekly["week"], y=weekly["revenue"],
        name="Weekly revenue", fill="tozeroy",
        line=dict(color="#4C78A8"), fillcolor="rgba(76,120,168,0.15)",
    ))
    fig.add_trace(go.Scatter(
        x=weekly["week"], y=weekly["ma4"],
        name="4-week moving avg",
        line=dict(color="#E45756", dash="dash", width=2),
    ))
    fig.update_layout(title="Weekly Revenue + 4-Week Moving Average",
                      hovermode="x unified", height=380)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig2 = px.bar(
            weekly.dropna(subset=["wow"]),
            x="week", y="wow",
            color=weekly.dropna(subset=["wow"])["wow"].apply(
                lambda x: "positive" if x >= 0 else "negative"),
            color_discrete_map={"positive": "#54A24B", "negative": "#E45756"},
            labels={"wow": "WoW Growth %", "week": ""},
            title="Week-over-Week Growth %",
        )
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        dow = load(f"""
        SELECT dayname(ordered_at) AS day,
               dayofweek(ordered_at) AS n,
               ROUND(AVG(order_total),2) AS aov,
               COUNT(*) AS orders
        FROM orders o JOIN locations l USING (location_id)
        WHERE o.ordered_at BETWEEN '{start}' AND '{end}'
          AND l.location_name IN ({loc_filter})
        GROUP BY 1,2 ORDER BY 2
        """)
        fig3 = px.bar(dow, x="day", y="orders", color="aov",
                      color_continuous_scale="Blues",
                      title="Orders by Day of Week (color = AOV)",
                      labels={"orders": "Avg Daily Orders", "day": "", "aov": "AOV $"},
                      text=dow["aov"].apply(lambda x: f"${x}"))
        fig3.update_traces(textposition="outside")
        st.plotly_chart(fig3, use_container_width=True)

# ── TAB 2: BY LOCATION ────────────────────────────────────────────
with tab2:
    loc_monthly = load(f"""
    SELECT date_trunc('month', o.ordered_at) AS month,
           l.location_name,
           ROUND(SUM(o.order_total), 0)      AS revenue,
           COUNT(o.order_id)                 AS orders,
           ROUND(AVG(o.order_total), 2)      AS aov
    FROM orders o JOIN locations l USING (location_id)
    WHERE o.ordered_at BETWEEN '{start}' AND '{end}'
      AND l.location_name IN ({loc_filter})
    GROUP BY 1,2 ORDER BY 1
    """)
    loc_monthly["month"] = pd.to_datetime(loc_monthly["month"])

    fig4 = px.line(loc_monthly, x="month", y="revenue",
                   color="location_name", markers=True,
                   labels={"revenue": "Monthly Revenue ($)", "month": "",
                           "location_name": "Location"},
                   title="Monthly Revenue by Location",
                   color_discrete_sequence=["#4C78A8", "#F58518"])
    fig4.update_layout(hovermode="x unified")
    st.plotly_chart(fig4, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        lp = load("SELECT * FROM fct_location_performance")
        fig5 = px.bar(lp, x="location_name",
                      y=["total_revenue", "total_cost"],
                      barmode="group",
                      color_discrete_map={"total_revenue": "#4C78A8",
                                          "total_cost": "#E45756"},
                      labels={"value": "$", "variable": "", "location_name": ""},
                      title="Total Revenue vs. Cost")
        st.plotly_chart(fig5, use_container_width=True)

    with col2:
        fig6 = px.bar(lp, x="location_name",
                      y="revenue_per_month_open",
                      color="location_name",
                      color_discrete_sequence=["#4C78A8", "#F58518"],
                      text=lp["revenue_per_month_open"].apply(lambda x: f"${x:,.0f}"),
                      labels={"revenue_per_month_open": "Revenue / Month ($)",
                              "location_name": ""},
                      title="Age-Normalized Revenue (per month open)")
        fig6.update_layout(showlegend=False)
        fig6.update_traces(textposition="outside")
        st.plotly_chart(fig6, use_container_width=True)

# ── TAB 3: BY PRODUCT ─────────────────────────────────────────────
with tab3:
    prod_monthly = load(f"""
    SELECT date_trunc('month', oi.ordered_at) AS month,
           oi.product_name,
           oi.is_food_item,
           ROUND(SUM(oi.product_price), 0)    AS revenue,
           COUNT(oi.order_item_id)             AS units
    FROM order_items oi
    JOIN orders o USING (order_id)
    JOIN locations l USING (location_id)
    WHERE oi.ordered_at BETWEEN '{start}' AND '{end}'
      AND l.location_name IN ({loc_filter})
    GROUP BY 1,2,3 ORDER BY 1
    """)
    prod_monthly["month"] = pd.to_datetime(prod_monthly["month"])

    fig7 = px.area(prod_monthly, x="month", y="revenue",
                   color="product_name",
                   labels={"revenue": "Monthly Revenue ($)",
                           "month": "", "product_name": "Product"},
                   title="Revenue by Product (stacked area)")
    fig7.update_layout(hovermode="x unified")
    st.plotly_chart(fig7, use_container_width=True)

    # Treemap
    prod_total = load("""
    SELECT product_name,
           CASE WHEN is_food_item THEN 'Food' ELSE 'Beverage' END AS category,
           ROUND(SUM(product_price), 0)  AS revenue,
           COUNT(order_item_id)          AS units
    FROM order_items GROUP BY 1,2
    """)
    fig8 = px.treemap(
        prod_total, path=["category", "product_name"],
        values="revenue", color="revenue",
        color_continuous_scale="Blues",
        title="Revenue Treemap — Category → Product",
    )
    st.plotly_chart(fig8, use_container_width=True)

# ── TAB 4: DIAGNOSTICS ────────────────────────────────────────────
with tab4:
    st.subheader("Revenue Change Decomposition")
    st.caption("Why did revenue change? Splitting into Volume effect vs. Price (AOV) effect.")

    monthly_diag = load(f"""
    SELECT date_trunc('month', o.ordered_at) AS month,
           COUNT(o.order_id)                 AS orders,
           ROUND(AVG(o.order_total), 4)      AS aov,
           ROUND(SUM(o.order_total), 2)      AS revenue
    FROM orders o JOIN locations l USING (location_id)
    WHERE o.ordered_at BETWEEN '{start}' AND '{end}'
      AND l.location_name IN ({loc_filter})
    GROUP BY 1 ORDER BY 1
    """)
    monthly_diag["month"] = pd.to_datetime(monthly_diag["month"])
    monthly_diag["prev_orders"] = monthly_diag["orders"].shift(1)
    monthly_diag["prev_aov"]    = monthly_diag["aov"].shift(1)
    monthly_diag["volume_effect"] = (
        (monthly_diag["orders"] - monthly_diag["prev_orders"])
        * monthly_diag["prev_aov"]
    ).round(0)
    monthly_diag["price_effect"] = (
        (monthly_diag["aov"] - monthly_diag["prev_aov"])
        * monthly_diag["prev_orders"]
    ).round(0)
    monthly_diag["month_label"] = monthly_diag["month"].dt.strftime("%b %Y")

    decomp = monthly_diag.dropna(subset=["volume_effect"]).melt(
        id_vars="month_label",
        value_vars=["volume_effect", "price_effect"],
        var_name="effect", value_name="value"
    )
    decomp["effect"] = decomp["effect"].map({
        "volume_effect": "Volume (more/fewer orders)",
        "price_effect":  "Price (AOV change)",
    })

    fig9 = px.bar(
        decomp, x="month_label", y="value", color="effect",
        barmode="group",
        color_discrete_map={
            "Volume (more/fewer orders)": "#4C78A8",
            "Price (AOV change)":         "#F58518",
        },
        labels={"value": "Revenue Impact ($)", "month_label": "",
                "effect": "Driver"},
        title="Revenue Change = Volume Effect + Price Effect",
    )
    fig9.add_hline(y=0, line_color="gray", line_dash="dot")
    st.plotly_chart(fig9, use_container_width=True)

    st.caption("""
    **How to read:** A positive Volume bar means more orders drove revenue up.
    A positive Price bar means higher AOV drove it up. Negative = drag.
    """)
