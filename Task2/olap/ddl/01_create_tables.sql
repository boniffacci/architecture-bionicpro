-- ClickHouse DDL для BionicPRO Reports Service
-- Создание таблиц для хранения сырых данных и витрин

-- ====================================
-- RAW DATA TABLES (Staging)
-- ====================================

-- Сырые данные из CRM
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

-- Сырые данные телеметрии из Core DB
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

-- ====================================
-- DATA MART (Витрина для отчётов)
-- ====================================

-- Агрегированные данные по пользователям (дневная детализация)
CREATE TABLE IF NOT EXISTS mart_report_user_daily (
    user_id String,
    report_date Date,
    
    -- Вложенные метрики
    metrics Nested(
        name String,             -- Название метрики (steps, battery_level, motion_quality, etc.)
        events_count UInt64,     -- Количество событий
        value_sum Float64,       -- Сумма значений
        value_avg Float64,       -- Среднее значение
        value_min Float64,       -- Минимальное значение
        value_max Float64        -- Максимальное значение
    ),
    
    -- Метаданные
    region LowCardinality(String),
    prosthetic_model LowCardinality(String),
    generated_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (user_id, report_date)
SETTINGS index_granularity = 8192;

-- ====================================
-- MATERIALIZED VIEWS (Опционально)
-- ====================================

-- Представление для быстрого доступа к метрикам последних 30 дней
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

-- ====================================
-- INDEXES (для улучшения производительности)
-- ====================================

-- Skip index для быстрого поиска по user_id
ALTER TABLE mart_report_user_daily 
ADD INDEX idx_user_id user_id TYPE bloom_filter GRANULARITY 1;

-- Skip index для region
ALTER TABLE mart_report_user_daily 
ADD INDEX idx_region region TYPE set(100) GRANULARITY 4;

-- ====================================
-- COMMENTS
-- ====================================

COMMENT ON TABLE raw_crm_users IS 'Сырые данные пользователей из CRM (Bitrix24/Oracle)';
COMMENT ON TABLE raw_telemetry IS 'Сырые данные телеметрии протезов из Core Database';
COMMENT ON TABLE mart_report_user_daily IS 'Витрина ежедневных отчётов пользователей с агрегированными метриками';



