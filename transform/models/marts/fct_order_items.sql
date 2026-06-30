with order_items as (
    select * from {{ ref('stg_meridian__order_items') }}
),

orders as (
    select order_id, customer_id, order_date, order_status, order_channel
    from {{ ref('stg_meridian__orders') }}
),

products as (
    select product_id, product_title, product_category
    from {{ ref('stg_meridian__products') }}
),

final as (
    select
        oi.order_item_id,
        oi.order_id,
        oi.product_id,
        o.customer_id,
        o.order_date,
        o.order_status,
        o.order_channel,
        p.product_title,
        p.product_category,
        oi.quantity,
        oi.unit_price,
        oi.line_total
    from order_items oi
    inner join orders o using (order_id)
    inner join products p using (product_id)
)

select * from final
