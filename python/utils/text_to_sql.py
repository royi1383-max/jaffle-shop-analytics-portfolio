"""
Text-to-SQL — turns a natural-language question into a SQL query against
this DuckDB database, using Claude, then runs it and returns the result.

Safety:
- The DB connection used to run generated SQL is opened read-only
  (utils.db_connector.get_connection default), so DuckDB itself rejects
  any INSERT/UPDATE/DELETE/DROP/CREATE/ALTER regardless of what the model
  produces.
- As a second layer, generated SQL is rejected up front if it contains
  any non-SELECT statement keyword, or more than one statement.
"""
import os
import re

import anthropic
from dotenv import load_dotenv

from utils.db_connector import get_connection

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"

# Only the marts/analytics layer — staging tables are raw/uncleaned and the
# time-spine table is a dbt internal, neither is meant to be queried directly.
QUERYABLE_TABLES = [
    "customers", "orders", "order_items", "products", "locations", "supplies",
    "fct_daily_revenue", "fct_cohorts", "fct_customer_churn_features",
    "fct_product_performance", "fct_location_performance", "fct_supply_cogs",
]

_BLOCKED_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|copy|pragma|"
    r"install|load|call|export|import)\b",
    re.IGNORECASE,
)


def _client() -> anthropic.Anthropic | None:
    if not ANTHROPIC_API_KEY:
        return None
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def get_schema_summary() -> str:
    with get_connection() as con:
        df = con.execute(
            """
            select table_name, column_name, data_type
            from information_schema.columns
            where table_schema = 'main'
            order by table_name, ordinal_position
            """
        ).fetchdf()

    df = df[df["table_name"].isin(QUERYABLE_TABLES)]
    lines = []
    for table in QUERYABLE_TABLES:
        cols = df[df["table_name"] == table]
        if cols.empty:
            continue
        col_list = ", ".join(f"{r.column_name} ({r.data_type})" for r in cols.itertuples())
        lines.append(f"- {table}: {col_list}")
    return "\n".join(lines)


def _extract_sql(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw.rstrip(";").strip()


def generate_sql(question: str, schema: str) -> str:
    client = _client()
    if client is None:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    prompt = f"""You are a DuckDB SQL expert. Given this schema (DuckDB dialect):

{schema}

Write ONE read-only SELECT query that answers this question:
"{question}"

Rules:
- Only query the tables listed above.
- SELECT only — no INSERT/UPDATE/DELETE/DDL of any kind.
- Use DuckDB SQL syntax (e.g. date_trunc, datediff).
- Return ONLY the SQL query, no explanation, no markdown fences."""

    msg = client.messages.create(
        model=MODEL, max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_sql(msg.content[0].text)


def is_safe_select(sql: str) -> bool:
    if ";" in sql.strip().rstrip(";"):
        return False  # multiple statements
    if not sql.strip().lower().startswith(("select", "with")):
        return False
    if _BLOCKED_KEYWORDS.search(sql):
        return False
    return True


def ask(question: str) -> dict:
    schema = get_schema_summary()
    try:
        sql = generate_sql(question, schema)
    except Exception as e:
        return {"sql": "", "result": None, "error": str(e)}

    if not is_safe_select(sql):
        return {"sql": sql, "result": None, "error": "Generated query failed the read-only safety check."}

    try:
        with get_connection() as con:
            result = con.execute(sql).fetchdf()
        return {"sql": sql, "result": result, "error": None}
    except Exception as e:
        return {"sql": sql, "result": None, "error": str(e)}
