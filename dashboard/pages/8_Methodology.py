import streamlit as st

st.set_page_config(page_title="Methodology", page_icon="📖", layout="wide")

st.title("📖 Methodology & Metrics Glossary")
st.caption(
    "What every metric on this dashboard actually means, how it's calculated, "
    "and the assumptions/limitations behind each method — organized by the page it appears on."
)

# ── Revenue ────────────────────────────────────────────────────────────────
with st.expander("📈 Revenue page", expanded=True):
    st.markdown("""
**4-week moving average** — the mean of the current week's revenue and the 3 weeks
before it. Smooths out week-to-week noise so the underlying trend is easier to see
than in the raw weekly line.

**WoW / MoM Growth %** — percentage change vs. the immediately preceding
week/month: `(current − previous) / previous × 100`. The very first period has
no prior value to compare against, so it's dropped rather than shown as 0% or blank.

**Age-normalized revenue (Revenue / Month Open)** — total revenue divided by how
many months a location has been open. Without this, an older location will
always look bigger than a newer one purely because it's had more time to
accumulate revenue — normalizing by age lets you compare a 9-year-old store to
a newer one fairly.

**Revenue Change Decomposition (Volume vs. Price effect)** — splits the change in
revenue between two consecutive months into two pieces:
- **Volume effect** = (change in order count) × (previous month's AOV)
- **Price effect** = (change in AOV) × (previous month's order count)

This is a standard variance-decomposition technique: it answers "did revenue move
because we sold more, or because each order was worth more?" — two very
different business situations that a single revenue number can't distinguish.
""")

# ── Customers ──────────────────────────────────────────────────────────────
with st.expander("👥 Customers page"):
    st.markdown("""
**Cohort retention** — customers are grouped into a "cohort" by the month of
their *first* order. For each cohort, retention at month N = the % of that
cohort's original customers who placed at least one order in month N (whether
or not they ordered in between). This is the standard way to answer "do
customers stick around?" independent of when they joined.

**Pareto curve (80/20 rule)** — customers are ranked by lifetime spend, then
the chart plots cumulative % of customers (x) against cumulative % of revenue
they represent (y). A dead-diagonal line would mean every customer contributes
equally; a curve that bows sharply toward the top-left means revenue is
concentrated in a small number of high-value customers. The vertical marker at
20% shows exactly how much revenue your top-fifth of customers accounts for.

**RFM scoring** — every customer is scored 1–5 on three dimensions using
quintiles (`ntile(5)`, so each score bucket has roughly the same number of
customers):
- **Recency (R)** — days since last order (lower = more recent = better, so this is scored in reverse)
- **Frequency (F)** — total lifetime orders
- **Monetary (M)** — total lifetime spend

Segments (Champions, At Risk, Cannot Lose Them, etc.) are then assigned from
simple rules on the R and F scores. RFM is deliberately simple and rule-based —
anyone in marketing can look at a customer's score and immediately understand
why they're in a given segment, which is its main advantage over a black-box
clustering model.
""")

# ── Products ───────────────────────────────────────────────────────────────
with st.expander("🥪 Products page"):
    st.markdown("""
**BCG Matrix (Boston Consulting Group growth-share matrix)** — a classic
portfolio-strategy technique, adapted here to revenue vs. margin instead of its
original market-growth vs. market-share axes. Each product is split into a
quadrant based on whether it's above or below the *median* revenue and *median*
margin across all products:
- **⭐ Star** — high revenue, high margin → invest and protect
- **🐄 Cash Cow** — high revenue, lower margin → sells well, but check if supply costs can be trimmed
- **❓ Question Mark** — low revenue, high margin → a bundling/promotion candidate
- **🐕 Dog** — low revenue, low margin → first place to look for pricing/menu changes

**Gross margin %** — `(revenue − cost) / revenue × 100`, per product.

**Perishable cost %** — the share of a product's supply cost that comes from
perishable ingredients. Higher = more exposure to waste if demand is
overestimated, since unsold perishable stock can't be carried over.
""")

# ── Locations ──────────────────────────────────────────────────────────────
with st.expander("📍 Locations page"):
    st.markdown("""
**Age-normalized comparison** — see "Revenue / Month Open" above (Revenue
page). Used throughout this page so that a location open for 107 months isn't
unfairly compared to one open for 101 months as if they'd had identical time
to grow.

**Radar / spider chart normalization** — each metric (revenue, orders, AOV,
etc.) is rescaled to a 0–1 range using min-max normalization across the
locations being compared:  `(value − min) / (max − min)`. This is necessary
because the raw metrics live on wildly different scales (revenue in the
hundreds of thousands, AOV in single-digit dollars) — without normalizing,
the chart would be dominated entirely by whichever metric has the largest
raw numbers.
""")

# ── Segmentation ───────────────────────────────────────────────────────────
with st.expander("🎯 Segmentation page"):
    st.markdown("""
**K-Means clustering** — an unsupervised algorithm that groups customers into
*k* clusters by minimizing the distance between each customer and their
cluster's center, based on standardized (z-scored) recency, frequency,
monetary, and food-% features. Unlike RFM's fixed rules, K-Means finds
whatever groupings the data actually supports — including patterns a
human-written rule might miss.

**Elbow method** — run K-Means for a range of *k* values and plot "inertia"
(within-cluster variance — how tightly packed each cluster is). Inertia always
decreases as *k* increases, but the rate of improvement drops off sharply at
some point — that "elbow" in the curve is a reasonable balance between
simplicity (fewer clusters) and explanatory power (tighter clusters).

**Silhouette score** — measures how well-separated clusters are, from -1 to 1.
A customer with a high score sits comfortably inside its own cluster and far
from neighboring clusters; a score near 0 means it's ambiguous which cluster
it belongs to. Above ~0.3 is generally considered a reasonable clustering for
real-world behavioral data (perfect separation, near 1.0, is rare outside of
synthetic data).
""")

# ── Predictions ────────────────────────────────────────────────────────────
with st.expander("🔮 Predictions page"):
    st.markdown("""
**Churn label (30-day holdout window)** — a customer is "churned" if they
placed at least one order before a cutoff date (30 days before the end of the
dataset) but placed *zero* orders in the 30 days after that cutoff. All
features are computed using only data available as of the cutoff, so nothing
about the "future" leaks into the prediction — this is the same discipline a
real production churn model needs, just applied to historical data with a
simulated cutoff instead of "today."

*Why not just "no order in 90 days," measured from today?* Because this
dataset is a fixed historical snapshot that ends while the business is still
fully active — nobody has had the chance to go quiet near the very end of the
data by construction. See `python/04_churn_model.py` for the full writeup,
including a second issue (a near-tautological feature) caught the same way.

**Precision / Recall / F1 / ROC-AUC** — precision = of the customers the model
flagged as churned, how many actually were; recall = of the customers who
actually churned, how many did the model catch; F1 is their harmonic mean.
ROC-AUC measures how well the model ranks churners above non-churners across
every possible probability threshold (0.5 = random guessing, 1.0 = perfect
separation). These are used instead of plain accuracy because the churn rate
here is 18% — a model that always predicts "not churned" would already be 82%
"accurate" while being completely useless.

**SHAP values** — for each feature, SHAP (SHapley Additive exPlanations)
measures its average contribution to pushing a prediction toward or away from
"churned," based on game-theoretic principles (the same idea as fairly
splitting credit among players who contributed differently to a team's win).
Unlike a simple feature-importance ranking, SHAP values are additive and
signed, so they explain *why* a specific prediction was made, not just which
features matter *on average*.

**BG/NBD model** (Beta-Geometric/Negative Binomial Distribution) — a
probabilistic model of *how often* a customer purchases and *whether they're
still an active customer at all*, fit only on each customer's purchase
frequency, recency, and how long they've been observed (`T`). It doesn't need
a hard "churned/not churned" label — it estimates a continuous probability
that a customer is still "alive."

**Gamma-Gamma model** — estimates a customer's *average transaction value*,
independent of how often they buy. Combined with BG/NBD's purchase-frequency
estimate, this produces a full Customer Lifetime Value forecast: expected
future purchases × expected value per purchase. It technically assumes
frequency and monetary value are uncorrelated — in this dataset they're
mildly correlated (~-0.36), so treat the resulting CLV numbers as directional
estimates, not exact forecasts.

**STL decomposition** (Seasonal-Trend decomposition using LOESS) — splits a
time series into three parts: trend (the slow-moving underlying direction),
seasonality (a repeating pattern — here, a 7-day weekly cycle), and residual
(whatever's left over after removing both). Days where the residual is
unusually large (measured in standard deviations, or "z-score") are flagged as
anomalies — they're not explained by the normal trend or weekly pattern, and
are worth investigating individually (promotions, holidays, data issues, etc.).
""")

# ── Ask the Data ───────────────────────────────────────────────────────────
with st.expander("💬 Ask the Data page"):
    st.markdown("""
**Text-to-SQL** — a natural-language question is sent to Claude along with the
database schema (table and column names/types) and the dataset's actual date
range. Claude returns a single SQL query, which is then validated (must be a
single read-only `SELECT`/`WITH` statement, no DDL/DML keywords) and executed
against a **read-only** database connection — so even if the model somehow
produced a write statement, the database itself would reject it, independent
of the keyword filter.
""")

st.divider()
st.caption(
    "This page is a reference, not an analysis — go back to any other page to see "
    "these methods applied to the actual data."
)
