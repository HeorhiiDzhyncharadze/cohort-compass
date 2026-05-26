{{ config(materialized='table') }}

with users as (

    select * from {{ ref('int_users') }}

)

select
    user_id,
    first_purchase_date,
    last_purchase_date,
    total_purchases,
    total_spend,
    cohort_month,

    case
        when total_purchases = 1 then 'NEW'
        else 'REPEAT'
    end as user_segment

from users
