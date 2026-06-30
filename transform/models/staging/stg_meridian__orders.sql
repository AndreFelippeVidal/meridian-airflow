with source as (
    select * from {{ source('meridian', 'orders') }}
),

renamed as (
    select
        order_id,
        customer_id,
        cast(ordered_at as timestamp) as ordered_at,
        cast(ordered_at as date)      as order_date,
        status                        as order_status,
        channel                       as order_channel
    from source
)

select * from renamed
