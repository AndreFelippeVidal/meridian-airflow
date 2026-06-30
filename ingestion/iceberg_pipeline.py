"""Write orders and order_items as Iceberg tables via PyIceberg + local Parquet files.

Keeps this fully self-contained (no cloud, no Hive) using a SQLite catalog.
Run twice to demonstrate time-travel (snapshot accumulation).
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
from meridian.synthetic import (
    generate_customers,
    generate_order_items,
    generate_orders,
    generate_products,
)
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

_PROJECT_ROOT = Path(__file__).parent.parent
_ICEBERG_DIR = _PROJECT_ROOT / "data" / "iceberg"
_CATALOG_URI = f"sqlite:///{_ICEBERG_DIR / 'catalog.db'}"
_WAREHOUSE = str(_ICEBERG_DIR / "warehouse")

_N_CUSTOMERS = 500
_N_PRODUCTS = 200
_N_ORDERS = 2000
_SEED = 42

# ── Iceberg schemas ───────────────────────────────────────────────────────────

ORDERS_SCHEMA = Schema(
    NestedField(1, "order_id", StringType(), required=False),
    NestedField(2, "customer_id", StringType(), required=False),
    NestedField(3, "ordered_at", TimestampType(), required=False),
    NestedField(4, "status", StringType(), required=False),
    NestedField(5, "channel", StringType(), required=False),
)

ORDER_ITEMS_SCHEMA = Schema(
    NestedField(1, "order_item_id", StringType(), required=False),
    NestedField(2, "order_id", StringType(), required=False),
    NestedField(3, "product_id", StringType(), required=False),
    NestedField(4, "qty", IntegerType(), required=False),
    NestedField(5, "unit_price", DoubleType(), required=False),
    NestedField(6, "line_total", DoubleType(), required=False),
)


def _get_catalog() -> SqlCatalog:
    _ICEBERG_DIR.mkdir(parents=True, exist_ok=True)
    return SqlCatalog(
        "meridian",
        **{"uri": _CATALOG_URI, "warehouse": _WAREHOUSE},
    )


def _ensure_namespace(catalog: SqlCatalog, ns: str) -> None:
    if (ns,) not in catalog.list_namespaces():
        catalog.create_namespace(ns)


def write_orders_iceberg(catalog: SqlCatalog) -> int:
    """Append orders to the Iceberg table; return row count written."""
    customers = generate_customers(_N_CUSTOMERS, seed=_SEED)
    orders = generate_orders(customers, _N_ORDERS, seed=_SEED)

    table_id = ("meridian", "orders")
    if not catalog.table_exists(table_id):
        catalog.create_table(table_id, schema=ORDERS_SCHEMA)
    table = catalog.load_table(table_id)

    arrow_table = pa.table(
        {
            "order_id": orders["order_id"].to_list(),
            "customer_id": orders["customer_id"].to_list(),
            "ordered_at": pa.array(
                orders["ordered_at"].to_list(), type=pa.timestamp("us")
            ),
            "status": orders["status"].to_list(),
            "channel": orders["channel"].to_list(),
        }
    )
    table.append(arrow_table)
    return len(arrow_table)


def write_order_items_iceberg(catalog: SqlCatalog) -> int:
    """Append order_items to the Iceberg table; return row count written."""
    customers = generate_customers(_N_CUSTOMERS, seed=_SEED)
    products = generate_products(_N_PRODUCTS, seed=_SEED)
    orders = generate_orders(customers, _N_ORDERS, seed=_SEED)
    items = generate_order_items(orders, products, seed=_SEED)

    table_id = ("meridian", "order_items")
    if not catalog.table_exists(table_id):
        catalog.create_table(table_id, schema=ORDER_ITEMS_SCHEMA)
    table = catalog.load_table(table_id)

    arrow_table = pa.table(
        {
            "order_item_id": items["order_item_id"].to_list(),
            "order_id": items["order_id"].to_list(),
            "product_id": items["product_id"].to_list(),
            "qty": pa.array(items["qty"].to_list(), type=pa.int32()),
            "unit_price": pa.array(items["unit_price"].to_list(), type=pa.float64()),
            "line_total": pa.array(
                (items["qty"] * items["unit_price"]).to_list(), type=pa.float64()
            ),
        }
    )
    table.append(arrow_table)
    return len(arrow_table)


def main() -> None:
    catalog = _get_catalog()
    _ensure_namespace(catalog, "meridian")

    orders_written = write_orders_iceberg(catalog)
    items_written = write_order_items_iceberg(catalog)

    orders_table = catalog.load_table(("meridian", "orders"))
    items_table = catalog.load_table(("meridian", "order_items"))
    n_order_snaps = len(list(orders_table.snapshots()))
    n_item_snaps = len(list(items_table.snapshots()))
    print(f"orders: {orders_written} rows written | snapshots: {n_order_snaps}")
    print(f"order_items: {items_written} rows written | snapshots: {n_item_snaps}")


if __name__ == "__main__":
    main()
