{{ config(materialized='table') }}

-- retention matrix: grain = (cohort_month, period_number)
-- cohort_month  — місяць першої покупки user (з dim_users)
-- period_number — 0 = місяць першої покупки, 1 = наступний, і т.д.
-- retention_rate = retained_users / cohort_size * 100

with cohorts as (

    -- один рядок на user: cohort_month = місяць першої покупки
    select
        user_id,
        cohort_month
    from {{ ref('dim_users') }}

),

cohort_sizes as (

    -- скільки унікальних users у кожному когорті
    select
        cohort_month,
        count(distinct user_id) as cohort_size
    from cohorts
    group by cohort_month

),

user_periods as (

    -- для кожної покупки визначаємо period_number відносно cohort_month user-а
    select
        c.cohort_month,
        p.user_id,
        datediff('month', c.cohort_month, p.event_date) as period_number

    from {{ ref('fct_purchases') }} p
    inner join cohorts c on p.user_id = c.user_id

),

retention as (

    -- скільки унікальних users активні в кожному period
    select
        cohort_month,
        period_number,
        count(distinct user_id) as retained_users

    from user_periods
    group by cohort_month, period_number

)

select
    r.cohort_month,
    r.period_number,
    cs.cohort_size,
    r.retained_users,
    round(r.retained_users * 100.0 / cs.cohort_size, 2) as retention_rate

from retention r
inner join cohort_sizes cs on r.cohort_month = cs.cohort_month

order by r.cohort_month, r.period_number
