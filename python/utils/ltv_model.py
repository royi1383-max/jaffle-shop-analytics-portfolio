"""
Shared LTV model — BG/NBD (purchase frequency) + Gamma-Gamma (spend per
order) via the `lifetimes` package, fit on the full order history.

Unlike the churn model, this uses ALL orders (no holdout) since it's a
forward-looking forecast from "now" (the true end of the dataset), not a
backtest against known future behavior.

Imported by both python/05_ltv_forecast.py (terminal report) and
dashboard/pages/6_Predictions.py.
"""
import pandas as pd
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import summary_data_from_transaction_data

from utils.db_connector import query


def build_rfm_summary() -> pd.DataFrame:
    tx = query("select customer_id, ordered_at, order_total from orders")
    tx["ordered_at"] = pd.to_datetime(tx["ordered_at"])
    obs_end = tx["ordered_at"].max()
    return summary_data_from_transaction_data(
        tx, "customer_id", "ordered_at", monetary_value_col="order_total",
        observation_period_end=obs_end, freq="D",
    )


def fit_and_forecast(forecast_days: int = 90, discount_rate: float = 0.01) -> dict:
    summary = build_rfm_summary()

    bgf = BetaGeoFitter(penalizer_coef=0.001)
    bgf.fit(summary["frequency"], summary["recency"], summary["T"])

    repeat = summary[summary["frequency"] > 0].copy()
    # Gamma-Gamma assumes frequency and monetary value are independent —
    # in this dataset they're mildly correlated (~-0.36). Not zero, so
    # treat resulting CLV as directional/estimate rather than exact.
    freq_monetary_corr = repeat[["frequency", "monetary_value"]].corr().iloc[0, 1]

    ggf = GammaGammaFitter(penalizer_coef=0.001)
    ggf.fit(repeat["frequency"], repeat["monetary_value"])

    repeat["predicted_avg_order_value"] = ggf.conditional_expected_average_profit(
        repeat["frequency"], repeat["monetary_value"]
    )
    repeat[f"expected_purchases_{forecast_days}d"] = bgf.conditional_expected_number_of_purchases_up_to_time(
        forecast_days, repeat["frequency"], repeat["recency"], repeat["T"]
    )
    repeat["clv_forecast"] = ggf.customer_lifetime_value(
        bgf, repeat["frequency"], repeat["recency"], repeat["T"], repeat["monetary_value"],
        time=forecast_days / 30, freq="D", discount_rate=discount_rate,
    )

    non_repeat_count = len(summary) - len(repeat)

    return {
        "summary": summary,
        "repeat_customers": repeat,
        "freq_monetary_corr": freq_monetary_corr,
        "non_repeat_count": non_repeat_count,
        "forecast_days": forecast_days,
    }
