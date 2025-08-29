{{ config(
    materialized = 'view',
) 
}}

with base as (
  select
    *,
    {{ dbt_utils.generate_surrogate_key([
      'com_nm',
      'bank_nm',
      'acct_no',
      'curr_cd',
      'view_dv'
    ]) }} as acct_id
  from {{ ref('stg_aicfo_get_all_trsc_fore') }}
)

select * from base 