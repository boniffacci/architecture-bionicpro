CREATE TABLE IF NOT EXISTS raw_crm_users (
    user_id String,
    username String,
    email String,
    contract_number String,
    prosthetic_model String,
    region LowCardinality(String),
    created_at DateTime,
    loaded_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(created_at)
ORDER BY (user_id, created_at);

CREATE TABLE IF NOT EXISTS raw_telemetry (
    event_id String,
    user_id String,
    event_type LowCardinality(String),
    metric_name LowCardinality(String),
    metric_value Float64,
    event_timestamp DateTime,
    region LowCardinality(String),
    loaded_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_timestamp)
ORDER BY (user_id, event_timestamp, event_id);

CREATE TABLE IF NOT EXISTS mart_report_user_daily (
    user_id String,
    report_date Date,
    
    metrics Nested(
        name String,
        events_count UInt64,
        value_sum Float64,
        value_avg Float64,
        value_min Float64,
        value_max Float64
    ),
    
    region LowCardinality(String),
    prosthetic_model LowCardinality(String),
    generated_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (user_id, report_date)
SETTINGS index_granularity = 8192;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_report_last_30days
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (user_id, report_date)
AS
SELECT
    user_id,
    report_date,
    metrics,
    region,
    prosthetic_model,
    generated_at
FROM mart_report_user_daily
WHERE report_date >= today() - INTERVAL 30 DAY;

ALTER TABLE mart_report_user_daily 
ADD INDEX idx_user_id user_id TYPE bloom_filter GRANULARITY 1;

ALTER TABLE mart_report_user_daily 
ADD INDEX idx_region region TYPE set(100) GRANULARITY 4;



