with source as (
    select * from {{ source('meridian', 'customers') }}
),

renamed as (
    select
        customer_id,
        name            as customer_name,
        email           as customer_email,
        country         as customer_country,
        cast(signup_date as date) as signup_date,
        segment         as customer_segment
    from source
)

select * from renamed
