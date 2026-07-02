"""End-to-end test: dlt ingest → dbt build runs cleanly via Dagster materialize."""

from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb
import pytest

DB_PATH = Path(__file__).parent.parent / "data" / "meridian.duckdb"
TRANSFORM_DIR = Path(__file__).parent.parent / "transform"

MART_TABLES = [
    "dim_customer",
    "dim_product",
    "fct_orders",
    "fct_order_items",
    "fct_payments",
    "mart_marketplace_daily",
]


@pytest.mark.skipif(not DB_PATH.exists(), reason="Run 'make ingest' first")
def test_full_pipeline_dbt_build() -> None:
    """dbt build must exit 0 after ingest has run (staging + marts + all tests)."""
    result = subprocess.run(
        ["uv", "run", "dbt", "build", "--profiles-dir", "."],
        cwd=TRANSFORM_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"dbt build failed:\n{result.stdout[-3000:]}"


@pytest.mark.skipif(not DB_PATH.exists(), reason="Run 'make ingest' first")
def test_all_mart_tables_populated() -> None:
    """Every mart table must have rows — proves lineage raw → staging → mart ran."""
    con = duckdb.connect(str(DB_PATH), read_only=True)
    for table in MART_TABLES:
        count = con.execute(f"SELECT count(*) FROM main_marts.{table}").fetchone()[0]
        assert count > 0, f"mart {table!r} is empty — pipeline may not have run"
    con.close()


@pytest.mark.skipif(not DB_PATH.exists(), reason="Run 'make ingest' first")
def test_asset_checks_pass() -> None:
    """Key business invariants: daily mart non-empty, GMV non-negative."""
    con = duckdb.connect(str(DB_PATH), read_only=True)

    daily_count = con.execute("SELECT count(*) FROM main_marts.mart_marketplace_daily").fetchone()[
        0
    ]
    assert daily_count > 0, "mart_marketplace_daily is empty"

    neg_gmv = con.execute(
        "SELECT count(*) FROM main_marts.mart_marketplace_daily WHERE gmv < 0"
    ).fetchone()[0]
    assert neg_gmv == 0, f"{neg_gmv} days have negative GMV"

    order_count = con.execute("SELECT count(*) FROM main_marts.fct_orders").fetchone()[0]
    assert order_count > 0, "fct_orders is empty"

    con.close()
