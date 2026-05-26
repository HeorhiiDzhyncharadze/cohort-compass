{{ config(materialized='view') }}

-- fct_events = матеріалізована копія stg_events (scan + write, без window функцій)
-- session_id живе в fct_sessions як окремий mart
select
    user_id,
    event_time,
    event_type,
    product_id,
    category_id,
    category_code,
    brand,
    price,
    user_session,
    event_date

from {{ ref('stg_events') }}
