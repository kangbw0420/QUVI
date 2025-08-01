

with  __dbt__cte__stg_aicfo_get_all_trsc as (


Select
    *

FROM "webcash"."public"."aicfo_get_all_trsc"
), base as (
  select
    *,
    md5(cast(coalesce(cast(com_nm as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(bank_nm as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(acct_no as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(curr_cd as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(view_dv as TEXT), '_dbt_utils_surrogate_key_null_') as TEXT)) as acct_id
  from __dbt__cte__stg_aicfo_get_all_trsc
)

select * from base