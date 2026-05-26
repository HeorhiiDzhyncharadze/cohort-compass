with source as (

    select * from {{ source('raw', 'raw_events') }}

),

cast_and_clean as (

    select
        -- identifiers
        cast(user_id      as bigint)         as user_id,
        cast(product_id   as bigint)         as product_id,
        cast(category_id  as bigint)         as category_id,

        -- event metadata
        cast(event_time   as timestamptz)    as event_time,
        event_type,
        user_session,

        -- product attributes
        category_code,
        brand,
        cast(price        as decimal(10, 2)) as price,

        -- month-level partition key for downstream cohort models
        -- cast через timestamp (без tz) бо DuckDB не підтримує TIMESTAMPTZ::DATE
        date_trunc('month', cast(event_time as timestamp))::date as event_date

    from source
    where price > 0 or price is null

),

deduped as (

    select *
    from cast_and_clean
    qualify
        row_number() over (
            partition by user_id, event_time, event_type, product_id
            order by 1
        ) = 1

)

select * from deduped
