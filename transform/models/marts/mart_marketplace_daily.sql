-- Grain: one row per calendar day.
-- GMV = gross merchandise value (sum of order subtotals for all orders placed that day).
with daily_orders as (
    select
        order_date,
        count(distinct order_id)                                    as orders_placed,
        count(distinct customer_id)                                 as unique_customers,
        sum(order_subtotal)                                         as gmv,
        sum(total_items)                                            as units_sold,
        sum(case when order_status = 'delivered' then order_subtotal else 0 end) as delivered_gmv
    from {{ ref('fct_orders') }}
    group by order_date
),

daily_payments as (
    select
        order_date,
        sum(collected_amount) as revenue_collected,
        sum(failed_amount)    as revenue_failed,
        sum(refunded_amount)  as revenue_refunded
    from {{ ref('fct_payments') }}
    group by order_date
),

final as (
    select
        o.order_date,
        o.orders_placed,
        o.unique_customers,
        o.gmv,
        o.units_sold,
        o.delivered_gmv,
        case
            when o.orders_placed > 0
            then round(o.gmv / o.orders_placed, 2)
        end                             as aov,
        coalesce(p.revenue_collected, 0) as revenue_collected,
        coalesce(p.revenue_failed, 0)    as revenue_failed,
        coalesce(p.revenue_refunded, 0)  as revenue_refunded
    from daily_orders o
    left join daily_payments p using (order_date)
)

select * from final
