-- Canonical mart shape. Staging is simpler (renames/casts only).
with orders as (
    select * from {{ ref("stg_meridian__orders") }}
),

customers as (
    select * from {{ ref("stg_meridian__customers") }}
),

final as (
    select
        o.order_id,
        o.customer_id,
        c.country,
        o.order_total,
        o.ordered_at
    from orders as o
    inner join customers as c on o.customer_id = c.customer_id
)

select * from final
