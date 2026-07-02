"""Phase G — Iceberg taste track tests."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from pyiceberg.catalog.sql import SqlCatalog

_ICEBERG_DIR = Path(__file__).parent.parent / "data" / "iceberg"
_CATALOG_URI = f"sqlite:///{_ICEBERG_DIR / 'catalog.db'}"
_WAREHOUSE = str(_ICEBERG_DIR / "warehouse")

_EXPECTED_ORDERS = 2000
_EXPECTED_ITEMS = 5050


def _catalog() -> SqlCatalog:
    return SqlCatalog("meridian", **{"uri": _CATALOG_URI, "warehouse": _WAREHOUSE})


@pytest.fixture(scope="module", autouse=True)
def run_iceberg_pipeline() -> None:
    """Ensure the Iceberg pipeline has produced >= 2 snapshots before tests.

    Each run appends a new snapshot, so a fresh catalog is seeded with two runs
    to exercise the time-travel assertion in test_multiple_snapshots_exist.
    """
    if not (_ICEBERG_DIR / "catalog.db").exists():
        import subprocess

        for _ in range(2):
            result = subprocess.run(
                ["uv", "run", "python", "-m", "ingestion.iceberg_pipeline"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
            )
            assert result.returncode == 0, f"iceberg_pipeline failed: {result.stderr}"


def test_iceberg_catalog_exists() -> None:
    assert (_ICEBERG_DIR / "catalog.db").exists(), (
        "SQLite catalog missing — run make ingest-iceberg"
    )


def test_orders_row_count() -> None:
    """Total rows in orders Iceberg table must match a single run's output."""
    cat = _catalog()
    table = cat.load_table(("meridian", "orders"))
    # scan returns all appended rows (may be multiple of _EXPECTED_ORDERS after re-runs)
    df = table.scan().to_arrow()
    assert len(df) >= _EXPECTED_ORDERS, (
        f"Expected at least {_EXPECTED_ORDERS} order rows, got {len(df)}"
    )


def test_order_items_row_count() -> None:
    """Total rows in order_items Iceberg table must be at least one run's worth."""
    cat = _catalog()
    table = cat.load_table(("meridian", "order_items"))
    df = table.scan().to_arrow()
    assert len(df) >= _EXPECTED_ITEMS, (
        f"Expected at least {_EXPECTED_ITEMS} item rows, got {len(df)}"
    )


def test_multiple_snapshots_exist() -> None:
    """Two pipeline runs must have produced at least 2 snapshots (time-travel proof)."""
    cat = _catalog()
    table = cat.load_table(("meridian", "orders"))
    snapshots = list(table.snapshots())
    assert len(snapshots) >= 2, (
        f"Expected >= 2 snapshots for time-travel, got {len(snapshots)}. "
        "Run 'make ingest-iceberg' twice."
    )


def test_schema_evolution_adds_column() -> None:
    """Schema evolution demo must add a 'priority' column to the orders table."""
    from ingestion.iceberg_demo import demo_schema_evolution

    demo_schema_evolution()

    cat = _catalog()
    table = cat.load_table(("meridian", "orders"))
    col_names = [f.name for f in table.schema().fields]
    assert "priority" in col_names, (
        f"'priority' column not found after evolution. Cols: {col_names}"
    )


def test_duckdb_iceberg_scan() -> None:
    """DuckDB must be able to query the Iceberg metadata file directly."""
    cat = _catalog()
    table = cat.load_table(("meridian", "orders"))
    metadata_location = table.metadata_location

    con = duckdb.connect()
    con.execute("INSTALL iceberg; LOAD iceberg;")
    count = con.execute(f"SELECT count(*) FROM iceberg_scan('{metadata_location}')").fetchone()[0]
    con.close()

    assert count >= _EXPECTED_ORDERS, (
        f"DuckDB iceberg_scan returned {count} rows, expected >= {_EXPECTED_ORDERS}"
    )
