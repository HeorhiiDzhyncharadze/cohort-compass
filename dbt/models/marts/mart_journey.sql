{{ config(materialized='view') }}

with transitions as (

    select
        user_session,
        event_type                                                           as to_event,
        lag(event_type) over (partition by user_session order by event_time) as from_event

    from {{ ref('stg_events') }}

)

select
    from_event,
    to_event,
    count(*) as transition_count

from transitions
where from_event is not null

group by from_event, to_event
order by transition_count desc
