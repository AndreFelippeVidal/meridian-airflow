"""Verify dbt build succeeds and key marts exist in DuckDB."""

from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb
import pytest

TRANSFORM_DIR = Path(__file__).parent.parent / "transform"
DB_PATH = Path(__file__).parent.parent / "data" / "meridian.duckdb"

EXPECTED_MARTS = [
    "dim_customer",
    "dim_product",
    "fct_orders",
    "fct_order_items",
    "fct_payments",
    "mart_marketplace_daily",
]


@pytest.mark.skipif(not DB_PATH.exists(), reason="Run 'make ingest' first")
def test_dbt_build_exits_zero() -> None:
    result = subprocess.run(
        ["uv", "run", "dbt", "build", "--profiles-dir", "."],
        cwd=TRANSFORM_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"dbt build failed:\n{result.stdout}\n{result.stderr}"


@pytest.mark.skipif(not DB_PATH.exists(), reason="Run 'make ingest' first")
def test_mart_tables_exist() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    tables = {
        r[0]
        for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main_marts'"
        ).fetchall()
    }
    con.close()
    for mart in EXPECTED_MARTS:
        assert mart in tables, f"Missing mart: {mart}"


@pytest.mark.skipif(not DB_PATH.exists(), reason="Run 'make ingest' first")
def test_mart_marketplace_daily_has_rows() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    count = con.execute("SELECT count(*) FROM main_marts.mart_marketplace_daily").fetchone()[0]
    con.close()
    assert count > 0


@pytest.mark.skipif(not DB_PATH.exists(), reason="Run 'make ingest' first")
def test_singular_test_gmv_non_negative() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    bad_rows = con.execute(
        "SELECT count(*) FROM main_marts.mart_marketplace_daily WHERE gmv < 0"
    ).fetchone()[0]
    con.close()
    assert bad_rows == 0, f"{bad_rows} days have negative GMV"
