# init-clickhouse.sql
# Инициализация ClickHouse для BionicPRO
# Этот файл автоматически запускается при первом старте контейнера

-- ============================================================================
-- ВИТРИНА 1: Финансовые метрики пользователей (Monthly)
-- ============================================================================

CREATE TABLE IF NOT EXISTS reports_db.report_user_monthly_metrics (
    report_date Date COMMENT 'Первый день месяца',
    user_id Int32 COMMENT 'ID пользователя',
    user_uuid String COMMENT 'UUID пользователя',
    total_payments Decimal(10, 2) DEFAULT 0 COMMENT 'Все платежи (успешные + неудачные)',
    successful_payments Decimal(10, 2) DEFAULT 0 COMMENT 'Только успешные платежи',
    failed_payments_count Int32 DEFAULT 0 COMMENT 'Количество неудачных платежей',
    active_subscriptions_count Int32 DEFAULT 0 COMMENT 'Активные подписки',
    subscription_cost_total Decimal(10, 2) DEFAULT 0 COMMENT 'Сумма всех подписок',
    last_updated DateTime DEFAULT now() COMMENT 'Время последнего обновления',
    created_at DateTime DEFAULT now() COMMENT 'Время создания'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (user_id, report_date)
COMMENT 'Ежемесячные финансовые метрики пользователя';


-- ============================================================================
-- ВИТРИНА 2: Технические метрики протезов (Monthly)
-- ============================================================================

CREATE TABLE IF NOT EXISTS reports_db.report_prosthetic_monthly_metrics (
    report_date Date COMMENT 'Первый день месяца',
    prosthetic_id Int32 COMMENT 'ID протеза',
    user_id Int32 COMMENT 'ID пользователя',
    user_uuid String COMMENT 'UUID пользователя',
    prosthetic_uuid String COMMENT 'UUID протеза',
    device_type String COMMENT 'Тип устройства (left_arm, right_leg, etc.)',
    
    -- KPIs: Использование
    power_on_count Int32 DEFAULT 0 COMMENT 'Количество включений',
    power_off_count Int32 DEFAULT 0 COMMENT 'Количество выключений',
    total_active_hours Float32 DEFAULT 0 COMMENT 'Часы активного использования',
    
    -- KPIs: Батарея
    avg_discharge_rate_active Float32 DEFAULT 0 COMMENT 'Средняя разрядка при работе (mAh/h)',
    avg_discharge_rate_idle Float32 DEFAULT 0 COMMENT 'Средняя разрядка в режиме ожидания (mAh/h)',
    avg_charge_rate Float32 DEFAULT 0 COMMENT 'Средняя скорость зарядки (mAh/h)',
    charge_cycles Int32 DEFAULT 0 COMMENT 'Количество циклов зарядки',
    
    -- KPIs: Надёжность
    warning_count Int32 DEFAULT 0 COMMENT 'Предупреждения',
    error_count Int32 DEFAULT 0 COMMENT 'Ошибки (восстанавливаемые)',
    critical_error_count Int32 DEFAULT 0 COMMENT 'Критические сбои',
    downtime_minutes Int32 DEFAULT 0 COMMENT 'Минуты простоя',
    
    -- Метаданные
    last_updated DateTime DEFAULT now() COMMENT 'Время последнего обновления',
    created_at DateTime DEFAULT now() COMMENT 'Время создания'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (user_id, prosthetic_id, report_date)
COMMENT 'Ежемесячные технические метрики протеза';


-- ============================================================================
-- ПРИМЕРЫ ЗАПРОСОВ ДЛЯ ПРОВЕРКИ
-- ============================================================================

-- Проверяем структуру таблиц
-- DESCRIBE reports_db.report_user_monthly_metrics;
-- DESCRIBE reports_db.report_prosthetic_monthly_metrics;

-- Проверяем статус таблиц
-- SELECT table, rows, bytes_on_disk FROM system.tables 
-- WHERE database = 'reports_db';
