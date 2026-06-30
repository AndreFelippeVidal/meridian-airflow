"""Verify meridian-core v0.2.0 generators work correctly from this repo's perspective."""

from meridian.synthetic import (
    generate_customers,
    generate_order_items,
    generate_orders,
    generate_payments,
    generate_products,
)


def test_all_generators_importable() -> None:
    customers = generate_customers(10)
    products = generate_products(5)
    orders = generate_orders(customers, 20)
    items = generate_order_items(orders, products)
    payments = generate_payments(orders)

    assert customers.height == 10
    assert products.height == 5
    assert orders.height == 20
    assert items.height > 0
    assert payments.height == 20


def test_referential_integrity() -> None:
    customers = generate_customers(50)
    products = generate_products(20)
    orders = generate_orders(customers, 100)
    items = generate_order_items(orders, products)
    payments = generate_payments(orders)

    customer_ids = set(customers["customer_id"].to_list())
    order_ids = set(orders["order_id"].to_list())
    product_ids = set(products["product_id"].to_list())

    assert set(orders["customer_id"].to_list()).issubset(customer_ids)
    assert set(items["order_id"].to_list()).issubset(order_ids)
    assert set(items["product_id"].to_list()).issubset(product_ids)
    assert set(payments["order_id"].to_list()).issubset(order_ids)


def test_non_negative_invariants() -> None:
    customers = generate_customers(20)
    products = generate_products(10)
    orders = generate_orders(customers, 50)
    items = generate_order_items(orders, products)
    payments = generate_payments(orders)

    assert (items["qty"] >= 1).all()
    assert (items["unit_price"] >= 0).all()
    assert (payments["amount"] >= 0).all()


def test_determinism_across_all_generators() -> None:
    customers_a = generate_customers(10)
    customers_b = generate_customers(10)
    assert customers_a.equals(customers_b)

    products_a = generate_products(5)
    products_b = generate_products(5)
    assert products_a.equals(products_b)

    orders_a = generate_orders(customers_a, 20)
    orders_b = generate_orders(customers_a, 20)
    assert orders_a.equals(orders_b)

    items_a = generate_order_items(orders_a, products_a)
    items_b = generate_order_items(orders_a, products_a)
    assert items_a.equals(items_b)

    payments_a = generate_payments(orders_a)
    payments_b = generate_payments(orders_a)
    assert payments_a.equals(payments_b)
