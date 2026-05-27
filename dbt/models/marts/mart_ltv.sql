{{ config(materialized='table') }}

with purchase_stats as (

    select
        user_id,
        avg(days_since_prev_purchase)   as avg_days_between_purchases

    from {{ ref('int_purchases') }}
    where days_since_prev_purchase is not null

    group by user_id

),

combined as (

    select
        u.user_id,
        u.cohort_month,
        u.first_purchase_date,
        u.last_purchase_date,
        u.total_purchases,
        u.total_spend,

        round(u.total_spend / nullif(u.total_purchases, 0), 2)  as avg_order_value,
        round(p.avg_days_between_purchases, 1)                  as avg_days_between_purchases,

        -- проста евристика; ML-модель замінить пізніше (mart_churn_features → ml/)
        round(
            (u.total_spend / nullif(u.total_purchases, 0)) * u.total_purchases * 2,
            2
        )                                                        as predicted_ltv

    from {{ ref('dim_users') }} u
    left join purchase_stats p on u.user_id = p.user_id

)

select * from combined
