

with  __dbt__cte__stg_aicfo_get_all_trsc as (


Select
    *

FROM "webcash"."public"."aicfo_get_all_trsc"
),  __dbt__cte__stg_aicfo_get_all_amt as (


Select
    *

FROM "webcash"."public"."aicfo_get_all_amt"
),  __dbt__cte__stg_aicfo_get_all_trsc_fore as (


Select
    *

FROM "webcash"."public"."aicfo_get_all_trsc_fore"
),  __dbt__cte__stg_aicfo_get_all_amt_fore as (


Select
    *

FROM "webcash"."public"."aicfo_get_all_amt_fore"
), trsc_accts as (
  select distinct
    com_nm,
    bank_nm,
    acct_no,
    curr_cd,
    view_dv
  from __dbt__cte__stg_aicfo_get_all_trsc
),

amt_accts as (
  select distinct
    com_nm,
    bank_nm,
    acct_no,
    curr_cd,
    view_dv
  from __dbt__cte__stg_aicfo_get_all_amt
),

trsc_accts_fore as (
  select distinct
    com_nm,
    bank_nm,
    acct_no,
    curr_cd,
    view_dv
  from __dbt__cte__stg_aicfo_get_all_trsc_fore
),

amt_accts_fore as (
  select distinct
    com_nm,
    bank_nm,
    acct_no,
    curr_cd,
    view_dv
  from __dbt__cte__stg_aicfo_get_all_amt_fore
),

unioned as (
  select * from trsc_accts
  union
  select * from amt_accts
  union
  select * from trsc_accts_fore
  union
  select * from amt_accts_fore
)

select
  md5(cast(coalesce(cast(com_nm as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(bank_nm as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(acct_no as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(curr_cd as TEXT), '_dbt_utils_surrogate_key_null_') || '-' || coalesce(cast(view_dv as TEXT), '_dbt_utils_surrogate_key_null_') as TEXT)) as acct_id,
  com_nm,
  bank_nm,
  acct_no,
  curr_cd,
  view_dv
from unioned