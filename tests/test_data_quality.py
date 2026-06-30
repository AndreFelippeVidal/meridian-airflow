"""Phase F — Elementary data quality gate."""

from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb
import pytest

DB_PATH = Path(__file__).parent.parent / "data" / "meridian.duckdb"
TRANSFORM_DIR = Path(__file__).parent.parent / "transform"
REPORT_PATH = TRANSFORM_DIR / "edr_target" / "elementary_report.html"


@pytest.mark.skipif(not DB_PATH.exists(), reason="Run 'make ingest && make transform' first")
def test_edr_report_generates() -> None:
    """edr report must exit 0 and produce a non-empty HTML file."""
    result = subprocess.run(
        [
            "uv", "run", "edr", "report",
            "--profiles-dir", ".",
            "--profile-target", "duckdb",
            "--project-dir", ".",
            "--file-path", str(REPORT_PATH),
        ],
        cwd=TRANSFORM_DIR,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "DUCKDB_PATH": str(DB_PATH.resolve())},
    )
    assert result.returncode == 0, f"edr report failed:\n{result.stderr[-2000:]}"
    assert REPORT_PATH.exists(), f"Report file not found at {REPORT_PATH}"
    assert REPORT_PATH.stat().st_size > 10_000, "Report HTML appears empty"


@pytest.mark.skipif(not DB_PATH.exists(), reason="Run 'make ingest && make transform' first")
def test_dbt_catches_negative_gmv() -> None:
    """Inject a bad row into the daily mart, confirm dbt test fails, clean up."""
    # columns: order_date, orders_placed, unique_customers, gmv, units_sold,
    #          delivered_gmv, aov, revenue_collected, revenue_failed, revenue_refunded
    sentinel = "('9999-12-31'::DATE, 0, 0, -999.99, 0, 0.0, 0.0, 0.0, 0.0, 0.0)"

    con = duckdb.connect(str(DB_PATH))
    try:
        row = con.execute(
            "SELECT * FROM main_marts.mart_marketplace_daily LIMIT 1"
        ).fetchone()
        assert row is not None, "mart_marketplace_daily is empty — run make transform first"
        con.execute(
            f"INSERT INTO main_marts.mart_marketplace_daily VALUES {sentinel}"
        )
    finally:
        con.close()

    # dbt test should report a failure on assert_daily_gmv_non_negative
    result = subprocess.run(
        ["uv", "run", "dbt", "test", "--profiles-dir", ".",
         "--select", "assert_daily_gmv_non_negative"],
        cwd=TRANSFORM_DIR,
        capture_output=True,
        text=True,
    )

    # Clean up BEFORE asserting so we never leave the DB dirty
    con = duckdb.connect(str(DB_PATH))
    try:
        con.execute(
            "DELETE FROM main_marts.mart_marketplace_daily WHERE order_date = '9999-12-31'"
        )
    finally:
        con.close()

    assert result.returncode != 0, (
        "dbt test should have caught the negative-GMV row but passed — "
        "check assert_daily_gmv_non_negative.sql"
    )
