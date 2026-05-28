{{ config(materialized='table') }}

select
    u.user_id,
    u.cohort_month,
    u.total_purchases,
    u.total_spend,

    -- recency: днів від останньої покупки до кінця датасету
    datediff('day', u.last_purchase_date, date '2020-04-30')            as days_since_last_purchase,

    -- avg gap між покупками (null для single-purchase users)
    l.avg_days_between_purchases,

    -- label: не купував в останні 60 днів перед кінцем датасету
    (datediff('day', u.last_purchase_date, date '2020-04-30') > 60)     as is_churned,

    r.r_score,
    r.f_score,
    r.m_score,
    r.rfm_segment

from {{ ref('dim_users') }} u
left join {{ ref('mart_ltv') }} l on u.user_id = l.user_id
left join {{ ref('mart_rfm') }} r on u.user_id = r.user_id
