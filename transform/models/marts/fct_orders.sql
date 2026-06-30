with orders as (
    select * from {{ ref('stg_meridian__orders') }}
),

order_totals as (
    select
        order_id,
        sum(quantity)   as total_items,
        sum(line_total) as order_subtotal
    from {{ ref('stg_meridian__order_items') }}
    group by order_id
),

payments as (
    select
        order_id,
        amount          as payment_amount,
        payment_method,
        payment_status,
        paid_at
    from {{ ref('stg_meridian__payments') }}
),

final as (
    select
        o.order_id,
        o.customer_id,
        o.ordered_at,
        o.order_date,
        o.order_status,
        o.order_channel,
        coalesce(t.total_items, 0)      as total_items,
        coalesce(t.order_subtotal, 0)   as order_subtotal,
        p.payment_amount,
        p.payment_method,
        p.payment_status,
        p.paid_at
    from orders o
    left join order_totals t using (order_id)
    left join payments p using (order_id)
)

select * from final
