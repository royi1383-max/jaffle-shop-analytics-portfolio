import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parents[2] / "jaffle_shop.duckdb"


def get_connection(read_only: bool = True):
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def query(sql: str):
    with get_connection() as con:
        return con.execute(sql).fetchdf()
