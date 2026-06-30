"""dlt source for the Meridian fictional marketplace.

Each resource is backed by a deterministic generator from meridian-core.
orders and payments use merge write-disposition with a cursor so repeated
runs stay idempotent (no duplicates).
"""

from __future__ import annotations

from collections.abc import Iterator

import dlt
from meridian.synthetic import (
    generate_customers,
    generate_order_items,
    generate_orders,
    generate_payments,
    generate_products,
)

_N_CUSTOMERS = 500
_N_PRODUCTS = 200
_N_ORDERS = 2_000
_SEED = 42

# Pre-generate dataframes once; resources pull from them.
_customers_df = generate_customers(_N_CUSTOMERS, seed=_SEED)
_products_df = generate_products(_N_PRODUCTS, seed=_SEED)
_orders_df = generate_orders(_customers_df, _N_ORDERS, seed=_SEED)
_order_items_df = generate_order_items(_orders_df, _products_df, seed=_SEED)
_payments_df = generate_payments(_orders_df, seed=_SEED)


@dlt.source(name="meridian")
def meridian_source() -> list[dlt.resource]:  # type: ignore[type-arg]
    """All five Meridian domain resources."""
    return [
        customers(),
        products(),
        orders(),
        order_items(),
        payments(),
    ]


@dlt.resource(
    name="customers",
    write_disposition="replace",
    primary_key="customer_id",
)
def customers() -> Iterator[dict[str, object]]:  # type: ignore[type-arg]
    yield from _customers_df.to_dicts()


@dlt.resource(
    name="products",
    write_disposition="replace",
    primary_key="product_id",
)
def products() -> Iterator[dict[str, object]]:  # type: ignore[type-arg]
    yield from _products_df.to_dicts()


@dlt.resource(
    name="orders",
    write_disposition="merge",
    primary_key="order_id",
    merge_key="ordered_at",
)
def orders() -> Iterator[dict[str, object]]:  # type: ignore[type-arg]
    yield from _orders_df.to_dicts()


@dlt.resource(
    name="order_items",
    write_disposition="replace",
    primary_key="order_item_id",
)
def order_items() -> Iterator[dict[str, object]]:  # type: ignore[type-arg]
    yield from _order_items_df.to_dicts()


@dlt.resource(
    name="payments",
    write_disposition="merge",
    primary_key="payment_id",
    merge_key="ts",
)
def payments() -> Iterator[dict[str, object]]:  # type: ignore[type-arg]
    yield from _payments_df.to_dicts()
