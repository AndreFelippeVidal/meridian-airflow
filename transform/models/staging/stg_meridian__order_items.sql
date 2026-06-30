with source as (
    select * from {{ source('meridian', 'order_items') }}
),

renamed as (
    select
        order_item_id,
        order_id,
        product_id,
        cast(qty as integer)              as quantity,
        cast(unit_price as decimal(10,2)) as unit_price,
        cast(qty * unit_price as decimal(12,2)) as line_total
    from source
)

select * from renamed
