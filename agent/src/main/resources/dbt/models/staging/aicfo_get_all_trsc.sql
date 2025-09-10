{{ config(
    materialized = 'view',
) 
}}

Select
    *

FROM {{ source('aicfo', 'aicfo_get_all_trsc') }}
