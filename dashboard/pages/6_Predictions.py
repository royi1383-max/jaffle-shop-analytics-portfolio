import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / "python"))

import streamlit as st
import pandas as pd
import plotly.express as px

from utils.churn_model import train_and_evaluate
from utils.ltv_model import fit_and_forecast
from utils.plotting_theme import COLORS

st.set_page_config(page_title="Predictions", page_icon="🔮", layout="wide")


@st.cache_resource(show_spinner="Training churn model...")
def get_churn_results():
    return train_and_evaluate()


@st.cache_resource(show_spinner="Fitting BG/NBD + Gamma-Gamma...")
def get_ltv_results():
    return fit_and_forecast(forecast_days=90)


st.title("🔮 Predictions")
st.caption("Churn risk (Random Forest + SHAP) and 90-day LTV forecast (BG/NBD + Gamma-Gamma)")

tab_churn, tab_ltv = st.tabs(["⚠️ Churn Risk", "💰 LTV Forecast"])

# ── TAB 1: CHURN RISK ────────────────────────────────────────────────────
with tab_churn:
    results = get_churn_results()

    st.info(
        "The churn label uses a 30-day holdout window (see README) rather than the "
        "dataset's own end date, and the model deliberately excludes recency-window "
        "features that turned out to be near-tautological restatements of the label "
        "(orders_last_30_days, days_since_last_order, etc.) — see `python/04_churn_model.py` "
        "for the full writeup of both issues."
    )

    m1, m2, m3, m4 = st.columns(4)
    rf = results["rf_metrics"]
    m1.metric("Precision", f"{rf['precision']:.2f}")
    m2.metric("Recall", f"{rf['recall']:.2f}")
    m3.metric("F1", f"{rf['f1']:.2f}")
    m4.metric("ROC-AUC", f"{rf['roc_auc']:.3f}")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("What drives the prediction")
        shap_df = results["mean_abs_shap"].reset_index()
        shap_df.columns = ["feature", "mean_abs_shap"]
        fig = px.bar(
            shap_df.sort_values("mean_abs_shap"),
            x="mean_abs_shap", y="feature", orientation="h",
            color_discrete_sequence=[COLORS["danger"]],
            title="Mean |SHAP value| per feature",
        )
        fig.update_layout(height=380, yaxis_title="", xaxis_title="Impact on churn prediction")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Product mix and average order value dominate: customers who skew more "
            "food-heavy (vs. drink-habit) and spend less per order are the higher-risk group."
        )

    with col2:
        st.subheader("At-risk customers")
        threshold = st.slider("Churn probability threshold", 0.0, 1.0, 0.5, 0.05)
        preds = results["predictions_df"]
        at_risk = preds[preds["churn_probability"] >= threshold].sort_values(
            "churn_probability", ascending=False
        )
        st.metric("Customers above threshold", len(at_risk))
        st.dataframe(
            at_risk[["customer_name", "churn_probability", "is_churned"]]
            .rename(columns={"customer_name": "Customer", "churn_probability": "Churn probability",
                              "is_churned": "Actually churned"})
            .style.format({"Churn probability": "{:.1%}"}),
            use_container_width=True, hide_index=True, height=320,
        )

# ── TAB 2: LTV FORECAST ──────────────────────────────────────────────────
with tab_ltv:
    ltv = get_ltv_results()
    repeat = ltv["repeat_customers"]
    forecast_col = f"expected_purchases_{ltv['forecast_days']}d"

    st.info(
        f"Frequency/monetary correlation is {ltv['freq_monetary_corr']:.2f} — Gamma-Gamma "
        "assumes ~0, so treat these CLV figures as directional estimates, not exact forecasts. "
        f"{ltv['non_repeat_count']} one-time customers are excluded (Gamma-Gamma needs repeat purchases)."
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Repeat customers modeled", len(repeat))
    m2.metric(f"Total forecasted value ({ltv['forecast_days']}d)", f"${repeat['clv_forecast'].sum():,.0f}")
    m3.metric("Median forecasted CLV", f"${repeat['clv_forecast'].median():,.0f}")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Forecasted purchases vs. spend")
        fig2 = px.scatter(
            repeat, x=forecast_col, y="monetary_value", size="clv_forecast",
            color="clv_forecast", color_continuous_scale="Blues",
            labels={forecast_col: f"Expected purchases (next {ltv['forecast_days']}d)",
                    "monetary_value": "Avg order value ($)", "clv_forecast": "Forecasted CLV"},
            title="Each point is a customer",
        )
        fig2.update_layout(height=420)
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.subheader("Top forecasted-value customers")
        top = repeat.sort_values("clv_forecast", ascending=False).head(15).reset_index()
        st.dataframe(
            top[["customer_id", "frequency", "monetary_value", forecast_col, "clv_forecast"]]
            .rename(columns={"customer_id": "Customer ID", "frequency": "Lifetime orders",
                              "monetary_value": "Avg order value",
                              forecast_col: f"Expected purchases ({ltv['forecast_days']}d)",
                              "clv_forecast": "Forecasted CLV"})
            .style.format({"Avg order value": "${:.2f}", "Forecasted CLV": "${:.0f}",
                            f"Expected purchases ({ltv['forecast_days']}d)": "{:.1f}"}),
            use_container_width=True, hide_index=True, height=460,
        )
