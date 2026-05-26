with purchases as (

    select * from {{ ref('int_purchases') }}

)

select
    user_id,

    min(event_time)::date                           as first_purchase_date,
    max(event_time)::date                           as last_purchase_date,

    count(*)                                        as total_purchases,
    sum(price)                                      as total_spend,

    date_trunc('month', min(event_time))::date      as cohort_month

from purchases
group by user_id
