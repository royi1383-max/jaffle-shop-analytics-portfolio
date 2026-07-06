import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / "python"))

import streamlit as st
import plotly.express as px

from utils.text_to_sql import ANTHROPIC_API_KEY, QUERYABLE_TABLES, ask

st.set_page_config(page_title="Ask the Data", page_icon="💬", layout="wide")

st.title("💬 Ask the Data")
st.caption("Ask a question in plain English — Claude writes the SQL, DuckDB runs it.")

if not ANTHROPIC_API_KEY:
    st.warning("Set ANTHROPIC_API_KEY in a `.env` file at the project root to use this page.")
    st.stop()

with st.expander("What tables can this query?"):
    st.write(", ".join(QUERYABLE_TABLES))
    st.caption(
        "Scoped to the marts/analytics layer only — staging tables (raw, uncleaned) "
        "and dbt-internal tables are excluded."
    )

st.info(
    "The query runs on a **read-only** database connection, and generated SQL is "
    "rejected up front if it isn't a single SELECT statement — so nothing here can "
    "modify the data even if the model tried to."
)

examples = [
    "What were the top 5 products by revenue last month?",
    "Which location has the highest average order value?",
    "How many customers have churned?",
    "What's the monthly revenue trend for the last 6 months?",
]
st.markdown("**Examples:**")
cols = st.columns(len(examples))
for col, ex in zip(cols, examples):
    if col.button(ex, use_container_width=True):
        st.session_state["ask_question"] = ex

question = st.text_input(
    "Your question",
    value=st.session_state.get("ask_question", ""),
    placeholder="e.g. Which products have the best margin?",
    label_visibility="collapsed",
)

if st.button("Ask", type="primary", disabled=not question.strip()):
    with st.spinner("Writing SQL and running it..."):
        result = ask(question)

    st.subheader("Generated SQL")
    st.code(result["sql"] or "(no SQL generated)", language="sql")

    if result["error"]:
        st.error(result["error"])
    else:
        df = result["result"]
        st.subheader(f"Result ({len(df)} rows)")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Quick auto-chart when the shape looks chartable: one categorical/date
        # column plus one numeric column.
        if 1 < len(df.columns) <= 3 and len(df) > 1:
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            other_cols = [c for c in df.columns if c not in numeric_cols]
            if numeric_cols and other_cols:
                fig = px.bar(df, x=other_cols[0], y=numeric_cols[0])
                st.plotly_chart(fig, use_container_width=True)
