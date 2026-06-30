"""Verify the dlt→DuckDB ingestion pipeline: row counts, idempotency, no failures."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from ingestion.meridian_source import (
    _N_CUSTOMERS,
    _N_ORDERS,
    _N_PRODUCTS,
    _order_items_df,
    meridian_source,
)


@pytest.fixture()
def tmp_db(tmp_path: Path) -> str:
    """Return a path to a fresh temporary DuckDB file."""
    return str(tmp_path / "test_meridian.duckdb")


def _run_pipeline(db_path: str) -> object:
    import dlt

    pipeline = dlt.pipeline(
        pipeline_name="test_meridian",
        destination=dlt.destinations.duckdb(db_path),
        dataset_name="raw",
    )
    pipeline.run(meridian_source())
    return pipeline


def test_row_counts_match_generators(tmp_db: str) -> None:
    _run_pipeline(tmp_db)

    con = duckdb.connect(tmp_db, read_only=True)
    assert con.execute("SELECT count(*) FROM raw.customers").fetchone()[0] == _N_CUSTOMERS
    assert con.execute("SELECT count(*) FROM raw.products").fetchone()[0] == _N_PRODUCTS
    assert con.execute("SELECT count(*) FROM raw.orders").fetchone()[0] == _N_ORDERS
    n_items = _order_items_df.height
    assert con.execute("SELECT count(*) FROM raw.order_items").fetchone()[0] == n_items
    assert con.execute("SELECT count(*) FROM raw.payments").fetchone()[0] == _N_ORDERS
    con.close()


def test_second_run_adds_no_duplicates(tmp_db: str) -> None:
    """Running the pipeline twice must not double the row counts (idempotency)."""
    _run_pipeline(tmp_db)
    counts_after_first: dict[str, int] = {}
    con = duckdb.connect(tmp_db, read_only=True)
    for tbl in ("customers", "products", "orders", "order_items", "payments"):
        counts_after_first[tbl] = con.execute(f"SELECT count(*) FROM raw.{tbl}").fetchone()[0]
    con.close()

    _run_pipeline(tmp_db)
    con = duckdb.connect(tmp_db, read_only=True)
    for tbl, expected in counts_after_first.items():
        actual = con.execute(f"SELECT count(*) FROM raw.{tbl}").fetchone()[0]
        assert actual == expected, f"{tbl}: expected {expected} after 2nd run, got {actual}"
    con.close()


def test_no_failed_jobs(tmp_db: str) -> None:
    import dlt

    pipeline = dlt.pipeline(
        pipeline_name="test_meridian_trace",
        destination=dlt.destinations.duckdb(tmp_db),
        dataset_name="raw",
    )
    pipeline.run(meridian_source())
    assert pipeline.last_trace is not None
    for step in pipeline.last_trace.steps:
        if hasattr(step, "exception") and step.exception is not None:
            pytest.fail(f"Pipeline step failed: {step.exception}")
