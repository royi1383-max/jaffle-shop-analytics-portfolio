"""
Jaffle Shop Analytics Dashboard
Main entry point — run with:
    streamlit run dashboard/app.py --server.port 8503
"""
import streamlit as st

st.set_page_config(
    page_title="Jaffle Shop Analytics",
    page_icon="🥪",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "python"))

import duckdb
import pandas as pd

DB_PATH = str(Path(__file__).parents[1] / "jaffle_shop.duckdb")


@st.cache_data
def load(sql: str) -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(sql).fetchdf()
    con.close()
    return df


# ── Sidebar filters ───────────────────────────────────────────────
with st.sidebar:
    st.image("https://i.imgur.com/4KeKvtH.png", width=60) if False else None
    st.title("🥪 Jaffle Shop")
    st.caption("Analytics Portfolio · dbt + Python + Streamlit")
    st.divider()

    date_range = st.date_input(
        "Date range",
        value=(pd.Timestamp("2024-09-01"), pd.Timestamp("2025-08-31")),
        min_value=pd.Timestamp("2024-09-01"),
        max_value=pd.Timestamp("2025-08-31"),
    )
    start_date = str(date_range[0]) if len(date_range) == 2 else "2024-09-01"
    end_date   = str(date_range[1]) if len(date_range) == 2 else "2025-08-31"

    locations = load("SELECT location_name FROM locations ORDER BY 1")["location_name"].tolist()
    selected_locs = st.multiselect("Locations", locations, default=locations)
    if not selected_locs:
        selected_locs = locations

    st.divider()
    st.caption("Phase: dbt + Python + Streamlit")

st.session_state["start_date"]    = start_date
st.session_state["end_date"]      = end_date
st.session_state["selected_locs"] = selected_locs
st.session_state["DB_PATH"]       = DB_PATH
st.session_state["load"]          = load

# ── Overview (home page) ──────────────────────────────────────────
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

loc_filter = ", ".join(f"'{l}'" for l in selected_locs)

overview = load(f"""
SELECT
    COUNT(DISTINCT o.customer_id)              AS customers,
    COUNT(o.order_id)                          AS orders,
    ROUND(SUM(o.order_total), 0)               AS revenue,
    ROUND(AVG(o.order_total), 2)               AS aov,
    ROUND(SUM(o.order_total - o.order_cost)
          / NULLIF(SUM(o.order_total), 0) * 100, 1) AS margin_pct
FROM orders o
JOIN locations l USING (location_id)
WHERE o.ordered_at BETWEEN '{start_date}' AND '{end_date}'
  AND l.location_name IN ({loc_filter})
""").iloc[0]

prev = load(f"""
SELECT
    ROUND(SUM(order_total), 0) AS revenue,
    COUNT(order_id)            AS orders
FROM orders o
JOIN locations l USING (location_id)
WHERE o.ordered_at BETWEEN
    CAST('{start_date}' AS DATE) - INTERVAL 1 YEAR
    AND CAST('{end_date}' AS DATE) - INTERVAL 1 YEAR
  AND l.location_name IN ({loc_filter})
""").iloc[0]

st.title("Executive Overview")

c1, c2, c3, c4, c5 = st.columns(5)

# The dataset only spans one year (Sep 2024 - Aug 2025), so "prior period"
# (same range, shifted back a year) falls entirely outside it and SUM()
# returns NULL/NaN — checking `if prev['revenue']` doesn't catch that, since
# NaN is truthy in Python. Use pd.notna() so the delta is hidden instead of
# showing a broken "nan%".
has_prior_revenue = pd.notna(prev["revenue"]) and prev["revenue"] > 0
has_prior_orders  = pd.notna(prev["orders"])  and prev["orders"]  > 0

c1.metric("Revenue",       f"${overview['revenue']:,.0f}",
          delta=f"{((overview['revenue']-prev['revenue'])/prev['revenue']*100):.0f}% vs prior period" if has_prior_revenue else None,
          help="No prior-period data available — the dataset doesn't extend back a full year." if not has_prior_revenue else None)
c2.metric("Orders",        f"{overview['orders']:,}",
          delta=f"{((overview['orders']-prev['orders'])/prev['orders']*100):.0f}%" if has_prior_orders else None,
          help="No prior-period data available — the dataset doesn't extend back a full year." if not has_prior_orders else None)
c3.metric("Customers",     f"{int(overview['customers']):,}")
c4.metric("Avg Order",     f"${overview['aov']:.2f}")
c5.metric("Gross Margin",  f"{overview['margin_pct']:.1f}%")

st.divider()

# Monthly trend
monthly = load(f"""
SELECT
    date_trunc('month', o.ordered_at)      AS month,
    ROUND(SUM(o.order_total), 0)           AS revenue,
    COUNT(o.order_id)                      AS orders,
    COUNT(DISTINCT o.customer_id)          AS customers,
    ROUND(AVG(o.order_total), 2)           AS aov
FROM orders o
JOIN locations l USING (location_id)
WHERE o.ordered_at BETWEEN '{start_date}' AND '{end_date}'
  AND l.location_name IN ({loc_filter})
GROUP BY 1 ORDER BY 1
""")
monthly["month"] = pd.to_datetime(monthly["month"])
monthly["mom_pct"] = monthly["revenue"].pct_change().mul(100).round(1)

col1, col2 = st.columns([3, 1])

with col1:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=monthly["month"], y=monthly["revenue"],
        name="Revenue ($)", marker_color="#4C78A8", opacity=0.85,
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=monthly["month"], y=monthly["orders"],
        name="Orders", line=dict(color="#F58518", width=2.5),
        mode="lines+markers", marker=dict(size=6),
    ), secondary_y=True)
    fig.update_layout(
        title="Monthly Revenue & Order Volume",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.12),
        height=380,
    )
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=False)
    fig.update_yaxes(title_text="Orders",      secondary_y=True, showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("**MoM Growth**")
    for _, row in monthly.dropna(subset=["mom_pct"]).iterrows():
        color = "green" if row["mom_pct"] >= 0 else "red"
        arrow = "▲" if row["mom_pct"] >= 0 else "▼"
        st.markdown(
            f"`{row['month'].strftime('%b %y')}` "
            f"<span style='color:{color}'>{arrow} {row['mom_pct']:.1f}%</span>",
            unsafe_allow_html=True,
        )

st.divider()

# Bottom row: location split + order type
col3, col4 = st.columns(2)

with col3:
    loc_rev = load(f"""
    SELECT l.location_name,
           ROUND(SUM(o.order_total), 0) AS revenue
    FROM orders o JOIN locations l USING (location_id)
    WHERE o.ordered_at BETWEEN '{start_date}' AND '{end_date}'
      AND l.location_name IN ({loc_filter})
    GROUP BY 1
    """)
    fig2 = px.pie(
        loc_rev, values="revenue", names="location_name",
        title="Revenue by Location",
        color_discrete_sequence=["#4C78A8", "#F58518"],
        hole=0.45,
    )
    fig2.update_traces(textinfo="percent+label")
    st.plotly_chart(fig2, use_container_width=True)

with col4:
    order_type = load(f"""
    SELECT
        CASE
            WHEN is_food_order AND is_drink_order     THEN 'Food + Drink'
            WHEN is_food_order AND NOT is_drink_order THEN 'Food only'
            WHEN is_drink_order                       THEN 'Drink only'
            ELSE 'Other'
        END AS order_type,
        COUNT(*)                          AS orders,
        ROUND(AVG(order_total), 2)        AS aov
    FROM orders o JOIN locations l USING (location_id)
    WHERE o.ordered_at BETWEEN '{start_date}' AND '{end_date}'
      AND l.location_name IN ({loc_filter})
    GROUP BY 1
    """)
    fig3 = px.bar(
        order_type.sort_values("orders"),
        x="orders", y="order_type", orientation="h",
        color="aov", color_continuous_scale="Blues",
        text=order_type.sort_values("orders")["aov"].apply(lambda x: f"AOV ${x}"),
        labels={"orders": "# Orders", "order_type": "", "aov": "Avg Order ($)"},
        title="Order Composition (size = AOV)",
    )
    fig3.update_traces(textposition="outside")
    # Headroom on the right so "AOV $X" labels on the longest bar aren't
    # clipped by the plot edge (this was showing as truncated to "AC").
    fig3.update_xaxes(range=[0, order_type["orders"].max() * 1.2])
    st.plotly_chart(fig3, use_container_width=True)
