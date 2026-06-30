-- Fails (returns rows) if any day has negative GMV.
select order_date, gmv
from {{ ref('mart_marketplace_daily') }}
where gmv < 0
