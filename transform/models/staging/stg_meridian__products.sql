with source as (
    select * from {{ source('meridian', 'products') }}
),

renamed as (
    select
        product_id,
        title           as product_title,
        category        as product_category,
        cast(price as decimal(10, 2))  as price,
        cast(cost as decimal(10, 2))   as cost,
        supplier_id
    from source
)

select * from renamed
