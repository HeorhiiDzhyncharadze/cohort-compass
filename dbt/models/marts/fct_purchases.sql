{{
    config(
        materialized='incremental',
        unique_key="event_time::varchar || user_id::varchar || product_id::varchar"
    )
}}

with purchases as (

    select * from {{ ref('int_purchases') }}

    {% if is_incremental() %}
        where event_time > (select max(event_time) from {{ this }})
    {% endif %}

)

select
    user_id,
    event_time,
    product_id,
    category_id,
    category_code,
    brand,
    price,
    user_session,
    -- обраховуємо локально щоб уникнути TIMESTAMPTZ->DATE при матеріалізації
    date_trunc('month', event_time::timestamp)::date as event_date,
    purchase_rank,
    days_since_prev_purchase,
    is_first_purchase

from purchases
