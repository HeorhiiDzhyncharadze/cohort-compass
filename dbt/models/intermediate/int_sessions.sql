with lagged as (

    select
        *,
        lag(event_time) over (
            partition by user_id
            order by event_time
        ) as prev_event_time

    from {{ ref('stg_events') }}

),

session_flags as (

    select
        *,
        -- кожного разу коли gap > 30 хвилин (або це перша подія юзера) — нова сесія
        sum(
            case
                when prev_event_time is null then 0  -- перша подія: починаємо з 0
                when event_time - prev_event_time > interval 30 minute then 1
                else 0
            end
        ) over (
            partition by user_id
            order by event_time
            rows between unbounded preceding and current row
        ) as session_id_raw

    from lagged

),

sessions as (

    select
        user_id,
        session_id_raw,
        -- унікальний ключ сесії
        user_id::varchar || '-' || session_id_raw::varchar as session_id,

        min(event_time)                                     as session_start,
        max(event_time)                                     as session_end,
        count(*)                                            as event_count,

        -- конвертація: хоча б одна purchase в сесії
        bool_or(event_type = 'purchase')                    as converted,

        -- додаткові корисні атрибути сесії
        max(user_session)                                   as user_session,
        count(*) filter (where event_type = 'purchase')     as purchase_count,
        max(price) filter (where event_type = 'purchase')   as max_purchase_price

    from session_flags
    group by user_id, session_id_raw

)

select * from sessions
