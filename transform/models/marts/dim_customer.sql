with customers as (
    select * from {{ ref('stg_meridian__customers') }}
),

orders as (
    select
        customer_id,
        count(*)                             as lifetime_orders,
        min(order_date)                      as first_order_date,
        max(order_date)                      as last_order_date
    from {{ ref('stg_meridian__orders') }}
    group by customer_id
),

final as (
    select
        c.customer_id,
        c.customer_name,
        c.customer_email,
        c.customer_country,
        c.signup_date,
        c.customer_segment,
        coalesce(o.lifetime_orders, 0)  as lifetime_orders,
        o.first_order_date,
        o.last_order_date,
        case
            when o.customer_id is null then false
            else true
        end                             as has_ordered
    from customers c
    left join orders o using (customer_id)
)

select * from final
