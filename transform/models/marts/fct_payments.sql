with payments as (
    select * from {{ ref('stg_meridian__payments') }}
),

orders as (
    select order_id, customer_id, order_date, order_channel
    from {{ ref('stg_meridian__orders') }}
),

final as (
    select
        p.payment_id,
        p.order_id,
        o.customer_id,
        o.order_date,
        o.order_channel,
        p.amount,
        p.payment_method,
        p.payment_status,
        p.paid_at,
        case when p.payment_status = 'completed' then p.amount else 0 end as collected_amount,
        case when p.payment_status = 'failed'    then p.amount else 0 end as failed_amount,
        case when p.payment_status = 'refunded'  then p.amount else 0 end as refunded_amount
    from payments p
    inner join orders o using (order_id)
)

select * from final
