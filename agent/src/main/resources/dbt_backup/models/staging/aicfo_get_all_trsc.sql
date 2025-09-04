{{ config(
    materialized = 'view',
) 
}}

Select
    *

FROM {{ source('public', 'aicfo_get_all_trsc') }}
