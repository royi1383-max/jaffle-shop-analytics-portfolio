import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / "python"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb

st.set_page_config(page_title="Products", page_icon="🥪", layout="wide")

DB_PATH = str(Path(__file__).parents[2] / "jaffle_shop.duckdb")

@st.cache_data
def load(sql):
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(sql).fetchdf()
    con.close()
    return df

st.title("🥪 Product Performance")

products = load("SELECT * FROM fct_supply_cogs ORDER BY gross_margin_pct DESC")
perf     = load("SELECT * FROM fct_product_performance ORDER BY month, product_id")
perf["month"] = pd.to_datetime(perf["month"])

tab1, tab2, tab3 = st.tabs(["BCG Matrix", "Margin & Costs", "Trends Over Time"])

# ── TAB 1: BCG MATRIX ─────────────────────────────────────────────
with tab1:
    med_rev    = products["total_revenue"].median()
    med_margin = products["gross_margin_pct"].median()

    products["quadrant"] = products.apply(
        lambda r: (
            "⭐ Star"        if r.total_revenue > med_rev and r.gross_margin_pct > med_margin else
            "🐄 Cash Cow"    if r.total_revenue > med_rev and r.gross_margin_pct <= med_margin else
            "❓ Question Mark" if r.total_revenue <= med_rev and r.gross_margin_pct > med_margin else
            "🐕 Dog"
        ), axis=1
    )

    fig = px.scatter(
        products,
        x="total_revenue", y="gross_margin_pct",
        size="units_sold",
        color="quadrant",
        hover_name="product_name",
        hover_data={"product_type": True, "units_sold": True,
                    "perishable_pct_of_revenue": ":.1f"},
        color_discrete_sequence=["#54A24B", "#4C78A8", "#F58518", "#E45756"],
        labels={
            "total_revenue":     "Total Revenue ($)",
            "gross_margin_pct":  "Gross Margin %",
            "quadrant":          "BCG Quadrant",
        },
        title="BCG Product Matrix — Revenue vs. Gross Margin",
        size_max=45,
    )
    fig.add_hline(y=med_margin, line_dash="dot", line_color="gray",
                  annotation_text=f"Median margin {med_margin:.0f}%",
                  annotation_position="right")
    fig.add_vline(x=med_rev, line_dash="dot", line_color="gray",
                  annotation_text=f"Median ${med_rev:,.0f}",
                  annotation_position="top right")

    # Label each dot
    for _, row in products.iterrows():
        fig.add_annotation(
            x=row["total_revenue"], y=row["gross_margin_pct"],
            text=row["product_name"].split(" ")[0],
            showarrow=False, yshift=14,
            font=dict(size=10, color="gray"),
        )
    fig.update_layout(height=520)
    st.plotly_chart(fig, use_container_width=True)

    # Quadrant summary
    quad_summary = products.groupby("quadrant").agg(
        products=("product_name", "count"),
        total_revenue=("total_revenue", "sum"),
        avg_margin=("gross_margin_pct", "mean"),
    ).reset_index()
    quad_summary["avg_margin"]    = quad_summary["avg_margin"].round(1)
    quad_summary["total_revenue"] = quad_summary["total_revenue"].round(0)

    strategy = {
        "⭐ Star":          "Invest & protect — core revenue and margin drivers",
        "🐄 Cash Cow":      "Optimize supply costs — high volume, margin pressure",
        "❓ Question Mark": "Bundle with high-volume items to grow sales",
        "🐕 Dog":           "Review pricing or reduce supply cost or consider cutting",
    }
    quad_summary["strategy"] = quad_summary["quadrant"].map(strategy)
    st.dataframe(quad_summary, use_container_width=True, hide_index=True)

# ── TAB 2: MARGIN & COSTS ─────────────────────────────────────────
with tab2:
    col1, col2 = st.columns(2)
    with col1:
        fig2 = px.bar(
            products.sort_values("gross_margin_pct"),
            x="gross_margin_pct", y="product_name",
            color="product_type",
            orientation="h",
            color_discrete_map={"food": "#F58518", "beverage": "#4C78A8"},
            text=products.sort_values("gross_margin_pct")["gross_margin_pct"].apply(
                lambda x: f"{x:.1f}%"),
            labels={"gross_margin_pct": "Gross Margin %", "product_name": ""},
            title="Gross Margin Ranking",
        )
        fig2.update_traces(textposition="outside")
        fig2.update_layout(showlegend=True)
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        cost_melt = products.melt(
            id_vars=["product_name", "product_type"],
            value_vars=["total_perishable_cost", "total_non_perishable_cost"],
            var_name="cost_type", value_name="cost",
        )
        cost_melt["cost_type"] = cost_melt["cost_type"].map({
            "total_perishable_cost":     "🔴 Perishable",
            "total_non_perishable_cost": "🔵 Non-perishable",
        })
        fig3 = px.bar(
            cost_melt,
            x="product_name", y="cost", color="cost_type",
            color_discrete_map={
                "🔴 Perishable": "#E45756",
                "🔵 Non-perishable": "#72B7B2",
            },
            barmode="stack",
            labels={"cost": "Total Supply Cost ($)", "product_name": "",
                    "cost_type": ""},
            title="Supply Cost — Perishable vs. Non-Perishable",
        )
        fig3.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig3, use_container_width=True)

    # Perishable risk table
    st.subheader("Perishable Risk Ranking")
    st.caption("Products with high perishable cost % are most exposed to waste/demand volatility.")
    risk = products[["product_name", "product_type", "gross_margin_pct",
                      "perishable_pct_of_revenue", "total_revenue"]].copy()
    risk.columns = ["Product", "Type", "Gross Margin %",
                    "Perishable % of Revenue", "Total Revenue ($)"]
    risk = risk.sort_values("Perishable % of Revenue", ascending=False)
    st.dataframe(risk, use_container_width=True, hide_index=True)

# ── TAB 3: TRENDS ─────────────────────────────────────────────────
with tab3:
    selected_products = st.multiselect(
        "Select products",
        options=perf["product_name"].unique().tolist(),
        default=perf["product_name"].unique().tolist()[:5],
    )
    filtered = perf[perf["product_name"].isin(selected_products)]

    fig4 = px.line(
        filtered, x="month", y="total_revenue",
        color="product_name", markers=True,
        labels={"total_revenue": "Monthly Revenue ($)", "month": "",
                "product_name": "Product"},
        title="Monthly Revenue by Product",
    )
    fig4.update_layout(hovermode="x unified")
    st.plotly_chart(fig4, use_container_width=True)

    fig5 = px.line(
        filtered, x="month", y="gross_margin_pct",
        color="product_name", markers=True,
        labels={"gross_margin_pct": "Gross Margin %", "month": "",
                "product_name": "Product"},
        title="Gross Margin % Trend by Product",
    )
    fig5.update_layout(hovermode="x unified")
    fig5.update_yaxes(range=[0, 100])
    st.plotly_chart(fig5, use_container_width=True)
