INSERT INTO
    sample_facade (id, buyer_id, telemetry_count, sales_amount)
select
    ROW_NUMBER() OVER (
        order by
            sample_sales.buyer_id
    ),
    sample_sales.buyer_id,
    count(sample_telemetry.value),
    sample_sales.total
from
    sample_sales
    inner join sample_telemetry on sample_sales.buyer_id = sample_telemetry.buyer_id
group by
    sample_sales.id,
    sample_sales.buyer_id