import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / "python"))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import duckdb
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

st.set_page_config(page_title="Segmentation", page_icon="🎯", layout="wide")

DB_PATH = str(Path(__file__).parents[2] / "jaffle_shop.duckdb")

@st.cache_data
def load(sql):
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(sql).fetchdf()
    con.close()
    return df

@st.cache_data
def run_kmeans(n_clusters):
    features = load("""
    SELECT customer_id,
           days_since_last_order  AS recency,
           count_lifetime_orders  AS frequency,
           lifetime_spend         AS monetary,
           food_item_pct
    FROM fct_customer_churn_features
    WHERE count_lifetime_orders IS NOT NULL
      AND lifetime_spend > 0
    """)
    X = features[["recency", "frequency", "monetary", "food_item_pct"]].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    features["cluster"] = km.fit_predict(X_scaled).astype(str)
    features["cluster"] = "Cluster " + features["cluster"]

    inertia = km.inertia_
    sil = silhouette_score(X_scaled, km.labels_) if n_clusters > 1 else 0.0

    return features, inertia, round(sil, 3)

@st.cache_data
def elbow_data():
    features = load("""
    SELECT days_since_last_order AS recency,
           count_lifetime_orders AS frequency,
           lifetime_spend        AS monetary,
           food_item_pct
    FROM fct_customer_churn_features
    WHERE count_lifetime_orders IS NOT NULL AND lifetime_spend > 0
    """).fillna(0)
    X_scaled = StandardScaler().fit_transform(features)
    results = []
    for k in range(2, 9):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        sil = silhouette_score(X_scaled, km.labels_)
        results.append({"k": k, "inertia": km.inertia_, "silhouette": round(sil, 3)})
    return pd.DataFrame(results)

st.title("🎯 Customer Segmentation")
st.caption("Two approaches: RFM (rule-based, interpretable) vs. K-Means (data-driven)")

tab1, tab2, tab3 = st.tabs(["RFM vs K-Means", "K-Means Explorer", "Cluster Profiles"])

# ── TAB 1: COMPARISON ─────────────────────────────────────────────
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("RFM Segmentation")
        st.caption("Rule-based: scores each customer 1–5 on Recency, Frequency, Monetary")
        rfm = load("""
        WITH rfm_raw AS (
            SELECT customer_id,
                   days_since_last_order AS recency_days,
                   count_lifetime_orders AS frequency,
                   lifetime_spend        AS monetary
            FROM fct_customer_churn_features
            WHERE count_lifetime_orders IS NOT NULL
        ),
        scored AS (
            SELECT *,
                   ntile(5) OVER (ORDER BY recency_days DESC) AS r,
                   ntile(5) OVER (ORDER BY frequency ASC)     AS f,
                   ntile(5) OVER (ORDER BY monetary ASC)      AS m
            FROM rfm_raw
        )
        SELECT *,
               CASE
                   WHEN r >= 4 AND f >= 4           THEN 'Champions'
                   WHEN r >= 3 AND f >= 3           THEN 'Loyal'
                   WHEN r >= 4 AND f < 3            THEN 'Recent'
                   WHEN r BETWEEN 2 AND 3 AND f >=3 THEN 'At Risk'
                   WHEN r < 2 AND f >= 3            THEN 'Cannot Lose'
                   WHEN r < 2 AND f < 2             THEN 'Lost'
                   ELSE 'Potential'
               END AS segment
        FROM scored
        """)
        seg_counts = rfm["segment"].value_counts().reset_index()
        seg_counts.columns = ["Segment", "Customers"]
        fig1 = px.pie(seg_counts, values="Customers", names="Segment",
                      color_discrete_sequence=px.colors.qualitative.Set2,
                      title="RFM Segments")
        fig1.update_traces(textinfo="label+percent")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("K-Means Clustering")
        st.caption("Data-driven: groups customers by behavioral similarity")
        df_km, _, sil = run_kmeans(4)
        km_counts = df_km["cluster"].value_counts().reset_index()
        km_counts.columns = ["Cluster", "Customers"]
        fig2 = px.pie(km_counts, values="Customers", names="Cluster",
                      color_discrete_sequence=px.colors.qualitative.Pastel,
                      title="K-Means Clusters (k=4)")
        fig2.update_traces(textinfo="label+percent")
        st.plotly_chart(fig2, use_container_width=True)
        st.metric("Silhouette Score", sil,
                  help="0–1 scale. Higher = more distinct clusters. Above 0.3 = reasonable.")

    st.info("""
    **Why both?**
    - **RFM** is transparent and easy to explain to marketing or sales — "here are your Champions."
    - **K-Means** finds patterns the rules might miss (e.g., high-frequency low-spenders vs. rare big-spenders).
    - In practice, RFM drives campaigns; K-Means validates or discovers unexpected segments.
    """)

# ── TAB 2: ELBOW METHOD ───────────────────────────────────────────
with tab2:
    st.subheader("Finding the Optimal Number of Clusters")

    elbow = elbow_data()
    col1, col2 = st.columns(2)
    with col1:
        fig3 = px.line(elbow, x="k", y="inertia", markers=True,
                       title="Elbow Method — Inertia vs. k",
                       labels={"inertia": "Inertia (within-cluster variance)", "k": "Number of clusters"},
                       color_discrete_sequence=["#4C78A8"])
        fig3.add_vline(x=4, line_dash="dash", line_color="#E45756",
                       annotation_text="Optimal k=4")
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        fig4 = px.line(elbow, x="k", y="silhouette", markers=True,
                       title="Silhouette Score vs. k",
                       labels={"silhouette": "Silhouette Score", "k": "Number of clusters"},
                       color_discrete_sequence=["#54A24B"])
        fig4.add_vline(x=4, line_dash="dash", line_color="#E45756",
                       annotation_text="Optimal k=4")
        st.plotly_chart(fig4, use_container_width=True)

    n_clusters = st.slider("Explore k =", min_value=2, max_value=8, value=4)
    df_explore, inertia, sil_score = run_kmeans(n_clusters)

    fig5 = px.scatter(
        df_explore,
        x="recency", y="frequency",
        color="cluster", size="monetary",
        opacity=0.6,
        labels={"recency": "Days since last order", "frequency": "Lifetime orders",
                "cluster": "Cluster"},
        title=f"K-Means (k={n_clusters}) — Recency vs. Frequency (size = Spend)",
        color_discrete_sequence=px.colors.qualitative.Set1,
    )
    fig5.update_layout(height=450)
    st.plotly_chart(fig5, use_container_width=True)

# ── TAB 3: CLUSTER PROFILES ───────────────────────────────────────
with tab3:
    df_km4, _, _ = run_kmeans(4)

    profile = df_km4.groupby("cluster").agg(
        customers=("customer_id", "count"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_spend=("monetary", "mean"),
        avg_food_pct=("food_item_pct", "mean"),
    ).reset_index()
    profile = profile.round(1)

    st.subheader("Cluster Profiles (k=4)")
    st.dataframe(profile, use_container_width=True, hide_index=True)

    # Radar per cluster
    dims = ["avg_recency", "avg_frequency", "avg_spend", "avg_food_pct"]
    radar = profile[["cluster"] + dims].copy()
    # Normalize
    for col in dims:
        cmax, cmin = radar[col].max(), radar[col].min()
        if cmax > cmin:
            radar[col] = (radar[col] - cmin) / (cmax - cmin)
        # Invert recency: lower = better
    radar["avg_recency"] = 1 - radar["avg_recency"]

    labels = ["Recency\n(lower=better)", "Frequency", "Avg Spend", "Food %"]
    colors_list = px.colors.qualitative.Set1[:4]

    fig6 = go.Figure()
    for i, row in radar.iterrows():
        vals = [row[d] for d in dims]
        vals += [vals[0]]
        fig6.add_trace(go.Scatterpolar(
            r=vals, theta=labels + [labels[0]],
            fill="toself", name=row["cluster"],
            line=dict(color=colors_list[i % 4]),
        ))
    fig6.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="Cluster Profile Radar (normalized)",
        height=480,
    )
    st.plotly_chart(fig6, use_container_width=True)
