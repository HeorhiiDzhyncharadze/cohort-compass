{{ config(materialized='table') }}

with daily_stats as (

    select
        event_time::date                                                          as event_day,
        approx_count_distinct(case when event_type = 'view'     then user_id end) as viewers,
        approx_count_distinct(case when event_type = 'purchase' then user_id end) as buyers,
        round(
            approx_count_distinct(case when event_type = 'purchase' then user_id end) * 1.0
            / nullif(approx_count_distinct(case when event_type = 'view' then user_id end), 0),
            6
        )                                                                         as cvr

    from {{ ref('stg_events') }}
    group by event_time::date

),

rolling as (

    select
        *,
        avg(cvr) over (
            order by event_day
            rows between 29 preceding and current row
        ) as rolling_avg_cvr,

        stddev(cvr) over (
            order by event_day
            rows between 29 preceding and current row
        ) as rolling_stddev_cvr

    from daily_stats

)

select
    event_day,
    viewers,
    buyers,
    cvr,
    round(rolling_avg_cvr,    6) as rolling_avg_cvr,
    round(rolling_stddev_cvr, 6) as rolling_stddev_cvr,

    round(
        (cvr - rolling_avg_cvr) / nullif(rolling_stddev_cvr, 0),
        4
    )                            as z_score,

    abs(
        (cvr - rolling_avg_cvr) / nullif(rolling_stddev_cvr, 0)
    ) > 2                        as is_anomaly

from rolling
order by event_day
