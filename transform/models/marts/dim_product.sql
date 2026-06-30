with products as (
    select * from {{ ref('stg_meridian__products') }}
),

sales as (
    select
        product_id,
        sum(quantity)   as total_units_sold,
        sum(line_total) as total_revenue
    from {{ ref('stg_meridian__order_items') }}
    group by product_id
),

final as (
    select
        p.product_id,
        p.product_title,
        p.product_category,
        p.price,
        p.cost,
        p.price - p.cost                        as gross_margin,
        round((p.price - p.cost) / p.price, 4) as margin_pct,
        p.supplier_id,
        coalesce(s.total_units_sold, 0)         as total_units_sold,
        coalesce(s.total_revenue, 0)            as total_revenue
    from products p
    left join sales s using (product_id)
)

select * from final
