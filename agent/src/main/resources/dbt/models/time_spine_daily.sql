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
            "DATE('2000-01-01')",
            "DATE('2030-01-01')"
        )
    }}
),

final as (
    select
        to_char(date_day, 'YYYYMMDD') as date_ymd
    from base_dates
)

select *
from final
where date_ymd::int > to_char(current_date - interval '5 years', 'YYYYMMDD')::int
  and date_ymd::int < to_char(current_date + interval '30 days', 'YYYYMMDD')::int