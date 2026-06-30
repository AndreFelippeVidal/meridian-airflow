"""Iceberg taste — schema evolution + time-travel demo.

Run after at least two executions of iceberg_pipeline.py so there are
multiple snapshots to travel between.

Output is captured in the README as proof-of-concept.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
from pyiceberg.catalog.sql import SqlCatalog

_ICEBERG_DIR = Path(__file__).parent.parent / "data" / "iceberg"
_CATALOG_URI = f"sqlite:///{_ICEBERG_DIR / 'catalog.db'}"
_WAREHOUSE = str(_ICEBERG_DIR / "warehouse")


def _catalog() -> SqlCatalog:
    return SqlCatalog("meridian", **{"uri": _CATALOG_URI, "warehouse": _WAREHOUSE})


def demo_time_travel() -> None:
    """Show row counts across snapshots for the orders table."""
    cat = _catalog()
    table = cat.load_table(("meridian", "orders"))
    snapshots = list(table.snapshots())

    print(f"\n{'='*55}")
    print("  TIME TRAVEL — meridian.orders")
    print(f"{'='*55}")
    print(f"  Total snapshots: {len(snapshots)}")
    for snap in snapshots:
        summary = snap.summary or {}
        added = summary.get("added-records", "?")
        total = summary.get("total-records", "?")
        ts_ms = snap.timestamp_ms
        print(f"  snapshot {snap.snapshot_id}  added={added}  total={total}  ts_ms={ts_ms}")

    if len(snapshots) >= 2:
        first_snap = snapshots[0]
        first_total = int(first_snap.summary.get("total-records", 0))
        latest_total = int(snapshots[-1].summary.get("total-records", 0))
        print(f"\n  First snapshot total rows : {first_total}")
        print(f"  Latest snapshot total rows: {latest_total}")
        print(f"  Rows added across runs    : {latest_total - first_total}")


def demo_schema_evolution() -> None:
    """Add a 'priority' column to orders and confirm DuckDB sees it."""
    cat = _catalog()
    table = cat.load_table(("meridian", "orders"))

    col_names = [f.name for f in table.schema().fields]
    if "priority" not in col_names:
        with table.update_schema() as update:
            from pyiceberg.types import StringType
            update.add_column("priority", StringType())
        print(f"\n{'='*55}")
        print("  SCHEMA EVOLUTION — added 'priority' column")
        print(f"{'='*55}")
    else:
        print(f"\n{'='*55}")
        print("  SCHEMA EVOLUTION — 'priority' column already present")
        print(f"{'='*55}")

    updated = cat.load_table(("meridian", "orders"))
    print("  Updated schema columns:", [f.name for f in updated.schema().fields])


def demo_duckdb_scan() -> None:
    """Query the Iceberg table directly from DuckDB using the metadata file."""
    cat = _catalog()
    table = cat.load_table(("meridian", "orders"))

    # DuckDB can read Iceberg via the metadata.json path
    metadata_location = table.metadata_location
    con = duckdb.connect()
    con.execute("INSTALL iceberg; LOAD iceberg;")

    count = con.execute(
        f"SELECT count(*) FROM iceberg_scan('{metadata_location}')"
    ).fetchone()[0]

    sample = con.execute(
        f"SELECT order_id, status, channel FROM iceberg_scan('{metadata_location}') LIMIT 3"
    ).fetchall()

    print(f"\n{'='*55}")
    print("  DUCKDB ICEBERG SCAN")
    print(f"{'='*55}")
    print(f"  Row count from DuckDB iceberg_scan: {count}")
    print("  Sample rows:")
    for row in sample:
        print(f"    {row}")
    con.close()


if __name__ == "__main__":
    demo_time_travel()
    demo_schema_evolution()
    demo_duckdb_scan()
    print("\nDone.")
