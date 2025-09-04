{{ 
    config(
        materialized = 'table',
    )
}}

with

base_dates as (
    {{
        dbt.date_spine(
            'day',
            "'2000-01-01'",
            "'2030-01-01'"
        )
    }}
),

final as (
    select
        FORMAT(date_day, 'yyyyMMdd') as date_ymd
    from base_dates
)

select *
from final
where 
    CAST(date_ymd AS INT) > CAST(FORMAT(DATEADD(DAY, -365*5, GETDATE()), 'yyyyMMdd') AS INT)
  and CAST(date_ymd AS INT) < CAST(FORMAT(DATEADD(DAY, 30, GETDATE()), 'yyyyMMdd') AS INT)
