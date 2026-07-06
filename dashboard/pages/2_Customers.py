import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / "python"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb

st.set_page_config(page_title="Customers", page_icon="👥", layout="wide")

DB_PATH = str(Path(__file__).parents[2] / "jaffle_shop.duckdb")

@st.cache_data
def load(sql):
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(sql).fetchdf()
    con.close()
    return df

from utils.plotting_theme import SEGMENT_COLORS

st.title("👥 Customer Analytics")
tab1, tab2, tab3 = st.tabs(["Cohort Retention", "Lifetime Value", "Segmentation (RFM)"])

# ── TAB 1: COHORT HEATMAP ─────────────────────────────────────────
with tab1:
    cohorts = load("""
    SELECT cohort_month,
           months_since_first_order,
           ROUND(retention_rate * 100, 1) AS retention_pct,
           cohort_size,
           active_customers
    FROM fct_cohorts
    WHERE months_since_first_order <= 11
    """)
    cohorts["cohort_label"] = pd.to_datetime(cohorts["cohort_month"]).dt.strftime("%b %Y")

    pivot = cohorts.pivot(
        index="cohort_label",
        columns="months_since_first_order",
        values="retention_pct",
    )
    pivot.columns = [f"M{c}" for c in pivot.columns]

    fig = px.imshow(
        pivot, text_auto=True,
        color_continuous_scale="Blues",
        aspect="auto",
        title="Cohort Retention Heatmap — % of cohort still active at month N",
        labels={"color": "Retention %", "x": "Months since first order", "y": "Acquisition cohort"},
    )
    fig.update_coloraxes(cmin=50, cmax=100)
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

    # Average retention curve
    avg_curve = cohorts.groupby("months_since_first_order").agg(
        avg_retention=("retention_pct", "mean"),
        cohorts_included=("cohort_label", "count"),
    ).reset_index()

    fig2 = px.line(
        avg_curve, x="months_since_first_order", y="avg_retention",
        markers=True,
        labels={"months_since_first_order": "Months since first order",
                "avg_retention": "Avg Retention %"},
        title="Average Retention Curve (across all cohorts)",
        color_discrete_sequence=["#4C78A8"],
    )
    fig2.add_hline(y=90, line_dash="dot", line_color="green",
                   annotation_text="90% threshold")
    fig2.update_yaxes(range=[0, 105])
    st.plotly_chart(fig2, use_container_width=True)

    st.info("""
    **Key insight:** Retention stays above 94% through month 6.
    This synthetic dataset shows extremely healthy retention — in a real business,
    benchmark month-1 retention above 30–40% as strong performance.
    """)

# ── TAB 2: LTV DISTRIBUTION ───────────────────────────────────────
with tab2:
    ltv = load("""
    SELECT customer_id, lifetime_spend, count_lifetime_orders,
           customer_type,
           CASE
               WHEN lifetime_spend < 200  THEN '< $200'
               WHEN lifetime_spend < 500  THEN '$200–500'
               WHEN lifetime_spend < 1000 THEN '$500–1K'
               ELSE '> $1K'
           END AS ltv_bucket
    FROM customers
    WHERE lifetime_spend IS NOT NULL AND lifetime_spend > 0
    """)

    col1, col2 = st.columns(2)
    with col1:
        median_spend = ltv["lifetime_spend"].median()
        mean_spend = ltv["lifetime_spend"].mean()

        # Median and mean sit close together on this scale — putting both as
        # line annotations collided into an unreadable jumble no matter how
        # they were staggered, at any chart width. Showing them as metrics
        # above the chart instead of on it sidesteps the problem entirely.
        mcol1, mcol2 = st.columns(2)
        mcol1.metric("Median lifetime spend", f"${median_spend:,.0f}")
        mcol2.metric("Mean lifetime spend", f"${mean_spend:,.0f}")

        fig3 = px.histogram(
            ltv, x="lifetime_spend", nbins=50,
            color_discrete_sequence=["#4C78A8"],
            title="Customer LTV Distribution",
            labels={"lifetime_spend": "Lifetime Spend ($)", "count": "Customers"},
        )
        fig3.add_vline(x=median_spend, line_dash="dash", line_color="#F58518")
        fig3.add_vline(x=mean_spend, line_dash="dot", line_color="#E45756")
        st.plotly_chart(fig3, use_container_width=True)
        st.caption(
            "💡 The mean sits well above the median — a small number of very "
            "high-spend customers pull the average up. Use the median as the "
            "'typical' customer, and see the Pareto curve below for how "
            "concentrated that high-end spend really is."
        )

    with col2:
        bucket_summary = ltv.groupby("ltv_bucket").agg(
            customers=("customer_id", "count"),
            total_revenue=("lifetime_spend", "sum"),
        ).reset_index()
        bucket_summary["revenue_pct"] = (
            bucket_summary["total_revenue"] / bucket_summary["total_revenue"].sum() * 100
        ).round(1)
        bucket_order = ["< $200", "$200–500", "$500–1K", "> $1K"]
        bucket_summary["ltv_bucket"] = pd.Categorical(
            bucket_summary["ltv_bucket"], categories=bucket_order, ordered=True
        )
        bucket_summary = bucket_summary.sort_values("ltv_bucket")

        fig4 = px.bar(
            bucket_summary, x="ltv_bucket", y="customers",
            color="revenue_pct", color_continuous_scale="Blues",
            text=bucket_summary["revenue_pct"].apply(lambda x: f"{x:.0f}% rev"),
            title="Customers & Revenue by LTV Bucket",
            labels={"customers": "# Customers", "ltv_bucket": "LTV Bucket",
                    "revenue_pct": "% of Revenue"},
        )
        fig4.update_traces(textposition="outside")
        st.plotly_chart(fig4, use_container_width=True)

    # Pareto analysis
    ltv_sorted = ltv.sort_values("lifetime_spend", ascending=False).reset_index(drop=True)
    ltv_sorted["cum_revenue_pct"] = (
        ltv_sorted["lifetime_spend"].cumsum()
        / ltv_sorted["lifetime_spend"].sum() * 100
    ).round(1)
    ltv_sorted["customer_pct"] = (
        (ltv_sorted.index + 1) / len(ltv_sorted) * 100
    ).round(1)

    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(
        x=ltv_sorted["customer_pct"], y=ltv_sorted["cum_revenue_pct"],
        fill="tozeroy", line=dict(color="#4C78A8"), name="Actual",
        fillcolor="rgba(76,120,168,0.2)",
    ))
    fig5.add_shape(type="line", x0=0, y0=0, x1=100, y1=100,
                   line=dict(dash="dot", color="gray"))
    fig5.add_vline(x=20, line_dash="dash", line_color="#E45756",
                   annotation_text="Top 20% of customers")
    pareto_val = ltv_sorted[ltv_sorted["customer_pct"] <= 20]["cum_revenue_pct"].max()
    fig5.add_annotation(x=20, y=pareto_val + 3,
                        text=f"→ {pareto_val:.0f}% of revenue", showarrow=False,
                        font=dict(color="#E45756"))
    fig5.update_layout(
        title="Pareto Curve — Top Customers Drive Disproportionate Revenue",
        xaxis_title="Cumulative % of Customers (ranked by spend)",
        yaxis_title="Cumulative % of Revenue",
        showlegend=False, height=380,
    )
    st.plotly_chart(fig5, use_container_width=True)
    st.info(
        f"💡 The top 20% of customers by spend account for **{pareto_val:.0f}% of total "
        f"revenue** — the closer the blue curve hugs the top-left corner, the more "
        f"revenue is concentrated in a small group. A perfectly equal business (every "
        f"customer spends the same) would follow the dotted diagonal exactly."
    )

# ── TAB 3: RFM SEGMENTATION ───────────────────────────────────────
with tab3:
    rfm = load("""
    WITH rfm_raw AS (
        SELECT customer_id, customer_name,
               days_since_last_order AS recency_days,
               count_lifetime_orders AS frequency,
               lifetime_spend        AS monetary
        FROM fct_customer_churn_features
        WHERE count_lifetime_orders IS NOT NULL
    ),
    rfm_scored AS (
        SELECT *,
               ntile(5) OVER (ORDER BY recency_days DESC) AS r_score,
               ntile(5) OVER (ORDER BY frequency ASC)     AS f_score,
               ntile(5) OVER (ORDER BY monetary ASC)      AS m_score
        FROM rfm_raw
    )
    SELECT *,
           r_score + f_score + m_score AS rfm_total,
           CASE
               WHEN r_score >= 4 AND f_score >= 4               THEN 'Champions'
               WHEN r_score >= 3 AND f_score >= 3               THEN 'Loyal Customers'
               WHEN r_score >= 4 AND f_score < 3                THEN 'Recent Customers'
               WHEN r_score BETWEEN 2 AND 3 AND f_score >= 3    THEN 'At Risk'
               WHEN r_score < 2 AND f_score >= 3                THEN 'Cannot Lose Them'
               WHEN r_score < 2 AND f_score < 2                 THEN 'Lost'
               ELSE 'Potential Loyalists'
           END AS rfm_segment
    FROM rfm_scored
    """)

    seg_summary = rfm.groupby("rfm_segment").agg(
        customers=("customer_id", "count"),
        avg_spend=("monetary", "mean"),
        total_revenue=("monetary", "sum"),
        avg_recency=("recency_days", "mean"),
    ).reset_index()
    seg_summary["revenue_pct"] = (
        seg_summary["total_revenue"] / seg_summary["total_revenue"].sum() * 100
    ).round(1)
    seg_summary["avg_spend"]   = seg_summary["avg_spend"].round(0)
    seg_summary["avg_recency"] = seg_summary["avg_recency"].round(0)

    col1, col2 = st.columns([2, 1])
    with col1:
        fig6 = px.scatter(
            rfm, x="recency_days", y="frequency",
            color="rfm_segment",
            size="monetary",
            color_discrete_map=SEGMENT_COLORS,
            hover_data={"customer_name": True, "monetary": ":$.0f"},
            labels={"recency_days": "Days since last order (lower = better)",
                    "frequency": "Lifetime orders", "rfm_segment": "Segment"},
            title="RFM Map — Recency vs. Frequency (size = Spend)",
            opacity=0.7,
        )
        fig6.update_layout(height=450)
        st.plotly_chart(fig6, use_container_width=True)

    with col2:
        fig7 = px.bar(
            seg_summary.sort_values("total_revenue", ascending=True),
            x="total_revenue", y="rfm_segment",
            orientation="h",
            color="rfm_segment",
            color_discrete_map=SEGMENT_COLORS,
            text=seg_summary.sort_values("total_revenue")["revenue_pct"].apply(
                lambda x: f"{x:.0f}%"),
            labels={"total_revenue": "Total Revenue ($)", "rfm_segment": ""},
            title="Revenue by Segment",
        )
        fig7.update_layout(showlegend=False, height=450)
        fig7.update_traces(textposition="outside")
        # Extra headroom on the right so the "outside" % labels on the
        # longest bar (Champions) aren't clipped by the plot edge.
        fig7.update_xaxes(range=[0, seg_summary["total_revenue"].max() * 1.18])
        st.plotly_chart(fig7, use_container_width=True)

    top2 = seg_summary.sort_values("revenue_pct", ascending=False).head(2)
    st.info(
        f"💡 **{top2.iloc[0]['rfm_segment']}** and **{top2.iloc[1]['rfm_segment']}** "
        f"together are just {top2['customers'].sum()} of {seg_summary['customers'].sum()} "
        f"customers ({top2['customers'].sum() / seg_summary['customers'].sum():.0%}) but drive "
        f"{top2['revenue_pct'].sum():.0f}% of total revenue — the segment action table below "
        f"prioritizes retaining these two groups above all else."
    )

    st.subheader("Segment Action Table")
    action_map = {
        "Champions":          "🏆 Reward with loyalty program. Upsell premium items.",
        "Loyal Customers":    "💚 Early access to new menu. Referral program.",
        "Potential Loyalists":"🌱 Regular content + mild offers to build habit.",
        "At Risk":            "⚠️ Win-back email with personalized discount.",
        "Cannot Lose Them":   "🚨 Aggressive re-engagement — free item offer.",
        "Recent Customers":   "👋 Onboarding flow, highlight top products.",
        "Lost":               "📋 Exit survey to understand churn reason.",
    }
    action_df = seg_summary[["rfm_segment", "customers", "avg_spend",
                              "revenue_pct", "avg_recency"]].copy()
    action_df["action"] = action_df["rfm_segment"].map(action_map)
    action_df.columns = ["Segment", "Customers", "Avg Spend ($)",
                         "% Revenue", "Avg Days Since Order", "Recommended Action"]
    st.dataframe(
        action_df.sort_values("% Revenue", ascending=False),
        use_container_width=True, hide_index=True,
    )
