with source as (
    select * from {{ source('meridian', 'payments') }}
),

renamed as (
    select
        payment_id,
        order_id,
        cast(amount as decimal(12,2)) as amount,
        method  as payment_method,
        status  as payment_status,
        cast(ts as timestamp) as paid_at
    from source
)

select * from renamed
