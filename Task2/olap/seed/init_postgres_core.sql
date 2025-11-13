-- PostgreSQL Core DB - Sample Telemetry Data
-- Создание таблиц и тестовых данных телеметрии

-- Таблица событий телеметрии
CREATE TABLE IF NOT EXISTS telemetry_events (
    event_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    device_id VARCHAR(100),
    region VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_telemetry_user_id ON telemetry_events(user_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_events(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_telemetry_metric ON telemetry_events(metric_name);

-- Вставка тестовых данных телеметрии
INSERT INTO telemetry_events (event_id, user_id, event_type, metric_name, metric_value, event_timestamp, region) VALUES
-- User 001 - сегодня
('pg-evt-001-001', 'user-001', 'step_count', 'steps', 5420.0, NOW() - INTERVAL '2 hours', 'RU'),
('pg-evt-001-002', 'user-001', 'battery', 'battery_level', 87.5, NOW() - INTERVAL '1 hour', 'RU'),
('pg-evt-001-003', 'user-001', 'motion', 'motion_quality', 92.3, NOW() - INTERVAL '30 minutes', 'RU'),

-- User 001 - вчера
('pg-evt-001-004', 'user-001', 'step_count', 'steps', 8320.0, NOW() - INTERVAL '1 day' - INTERVAL '5 hours', 'RU'),
('pg-evt-001-005', 'user-001', 'battery', 'battery_level', 65.2, NOW() - INTERVAL '1 day' - INTERVAL '3 hours', 'RU'),
('pg-evt-001-006', 'user-001', 'motion', 'motion_quality', 88.7, NOW() - INTERVAL '1 day' - INTERVAL '1 hour', 'RU'),

-- User 002 - сегодня
('pg-evt-002-001', 'user-002', 'step_count', 'steps', 6890.0, NOW() - INTERVAL '3 hours', 'EU'),
('pg-evt-002-002', 'user-002', 'battery', 'battery_level', 92.1, NOW() - INTERVAL '2 hours', 'EU'),
('pg-evt-002-003', 'user-002', 'motion', 'motion_quality', 95.4, NOW() - INTERVAL '1 hour', 'EU'),
('pg-evt-002-004', 'user-002', 'pressure', 'pressure_sensor', 120.5, NOW() - INTERVAL '30 minutes', 'EU'),

-- User 003 - сегодня
('pg-evt-003-001', 'user-003', 'step_count', 'steps', 4210.0, NOW() - INTERVAL '4 hours', 'US'),
('pg-evt-003-002', 'user-003', 'battery', 'battery_level', 78.3, NOW() - INTERVAL '2 hours', 'US'),
('pg-evt-003-003', 'user-003', 'motion', 'motion_quality', 85.6, NOW() - INTERVAL '1 hour', 'US'),

-- User 001 - неделю назад
('pg-evt-001-007', 'user-001', 'step_count', 'steps', 7200.0, NOW() - INTERVAL '7 days', 'RU'),
('pg-evt-001-008', 'user-001', 'battery', 'battery_level', 92.0, NOW() - INTERVAL '7 days', 'RU'),

-- User 002 - неделю назад
('pg-evt-002-005', 'user-002', 'step_count', 'steps', 9100.0, NOW() - INTERVAL '7 days', 'EU'),
('pg-evt-002-006', 'user-002', 'battery', 'battery_level', 88.5, NOW() - INTERVAL '7 days', 'EU');

-- Таблица пользователей (для join с телеметрией)
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(200),
    region VARCHAR(50),
    prosthetic_model VARCHAR(100),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Вставка тестовых пользователей
INSERT INTO users (user_id, username, email, region, prosthetic_model) VALUES
('user-001', 'prothetic1', 'prothetic1@example.com', 'RU', 'BionicPRO-X1'),
('user-002', 'prothetic2', 'prothetic2@example.com', 'EU', 'BionicPRO-X2'),
('user-003', 'prothetic3', 'prothetic3@example.com', 'US', 'BionicPRO-X1'),
('user-004', 'admin1', 'admin1@example.com', 'RU', 'BionicPRO-Admin');

-- Представление для удобного доступа к агрегированным данным
CREATE OR REPLACE VIEW v_daily_telemetry AS
SELECT
    user_id,
    DATE(event_timestamp) as report_date,
    metric_name,
    COUNT(*) as events_count,
    SUM(metric_value) as value_sum,
    AVG(metric_value) as value_avg,
    MIN(metric_value) as value_min,
    MAX(metric_value) as value_max,
    region
FROM telemetry_events
GROUP BY user_id, DATE(event_timestamp), metric_name, region
ORDER BY report_date DESC, user_id;

-- Комментарии к таблицам
COMMENT ON TABLE telemetry_events IS 'События телеметрии протезов BionicPRO';
COMMENT ON TABLE users IS 'Пользователи протезов BionicPRO';
COMMENT ON VIEW v_daily_telemetry IS 'Агрегированная дневная телеметрия по пользователям';



