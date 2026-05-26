with purchases as (

    select *
    from {{ ref('stg_events') }}
    where event_type = 'purchase'

),

ranked as (

    select
        user_id,
        event_time,
        product_id,
        category_id,
        category_code,
        brand,
        price,
        user_session,
        event_date,

        row_number() over (
            partition by user_id
            order by event_time
        ) as purchase_rank,

        datediff(
            'day',
            lag(event_time) over (partition by user_id order by event_time),
            event_time
        ) as days_since_prev_purchase

    from purchases

)

select
    *,
    purchase_rank = 1 as is_first_purchase
from ranked
