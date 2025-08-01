{{ config(
    materialized = 'ephemeral',
) 
}}

Select
    *

FROM {{ source('public', 'aicfo_get_all_stock') }}
