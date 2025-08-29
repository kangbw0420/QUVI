{{ config(
    materialized = 'view',
) 
}}

with trsc_accts as (
  select distinct
    com_nm,
    bank_nm,
    acct_no,
    curr_cd,
    view_dv
  from {{ ref('stg_aicfo_get_all_trsc') }}
),

amt_accts as (
  select distinct
    com_nm,
    bank_nm,
    acct_no,
    curr_cd,
    view_dv
  from {{ ref('stg_aicfo_get_all_amt') }}
),

trsc_accts_fore as (
  select distinct
    com_nm,
    bank_nm,
    acct_no,
    curr_cd,
    view_dv
  from {{ ref('stg_aicfo_get_all_trsc_fore') }}
),

amt_accts_fore as (
  select distinct
    com_nm,
    bank_nm,
    acct_no,
    curr_cd,
    view_dv
  from {{ ref('stg_aicfo_get_all_amt_fore') }}
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
  {{ dbt_utils.generate_surrogate_key([
    'com_nm',
    'bank_nm',
    'acct_no',
    'curr_cd',
    'view_dv'
  ]) }} as acct_id,
  com_nm,
  bank_nm,
  acct_no,
  curr_cd,
  view_dv
from unioned
