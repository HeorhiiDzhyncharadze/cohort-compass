{{ config(materialized='table') }}

with scores as (

    select
        user_id,
        cohort_month,
        last_purchase_date,
        total_purchases,
        total_spend,
        user_segment,

        ntile(5) over (order by last_purchase_date desc) as r_score,
        ntile(5) over (order by total_purchases)         as f_score,
        ntile(5) over (order by total_spend)             as m_score

    from {{ ref('dim_users') }}

)

select
    user_id,
    cohort_month,
    last_purchase_date,
    total_purchases,
    total_spend,
    user_segment,
    r_score,
    f_score,
    m_score,
    r_score + f_score + m_score as rfm_score,

    case
        when r_score + f_score >= 8  then 'Champions'
        when r_score + f_score >= 6  then 'Loyal'
        when r_score + f_score >= 4  then 'At Risk'
        when r_score + f_score >= 2  then 'Hibernating'
        else                              'Lost'
    end as rfm_segment

from scores
