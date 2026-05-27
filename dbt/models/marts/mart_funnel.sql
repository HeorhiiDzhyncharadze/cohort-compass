{{ config(materialized='table') }}

-- aliases з одного SELECT не можна референсувати в тому ж SELECT в DuckDB
-- тому рахуємо метрики в base CTE, конвертуємо rates зовні
with base as (

    select
        event_date,
        count(distinct case when event_type = 'view'     then user_id end) as viewers,
        count(distinct case when event_type = 'cart'     then user_id end) as carted,
        count(distinct case when event_type = 'purchase' then user_id end) as buyers

    from {{ ref('fct_events') }}
    group by event_date

)

select
    event_date,
    viewers,
    carted,
    buyers,
    round(buyers * 100.0 / nullif(viewers, 0), 2) as view_to_purchase_rate,
    round(buyers * 100.0 / nullif(carted,  0), 2) as cart_to_purchase_rate

from base
order by event_date
