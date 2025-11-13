-- Sample Data для тестирования BionicPRO Reports Service

-- Вставка тестовых пользователей из CRM
INSERT INTO raw_crm_users (user_id, username, email, contract_number, prosthetic_model, region, created_at) VALUES
('user-001', 'prothetic1', 'prothetic1@example.com', 'CNT-2024-001', 'BionicPRO-X1', 'RU', '2024-01-15 10:00:00'),
('user-002', 'prothetic2', 'prothetic2@example.com', 'CNT-2024-002', 'BionicPRO-X2', 'EU', '2024-02-20 11:30:00'),
('user-003', 'prothetic3', 'prothetic3@example.com', 'CNT-2024-003', 'BionicPRO-X1', 'US', '2024-03-10 14:20:00'),
('user-004', 'admin1', 'admin1@example.com', 'CNT-2024-004', 'BionicPRO-Admin', 'RU', '2024-01-01 09:00:00');

-- Вставка тестовых данных телеметрии
INSERT INTO raw_telemetry (event_id, user_id, event_type, metric_name, metric_value, event_timestamp, region) VALUES
-- User 001 - текущий день
('evt-001-001', 'user-001', 'step_count', 'steps', 5420.0, now() - INTERVAL 2 HOUR, 'RU'),
('evt-001-002', 'user-001', 'battery', 'battery_level', 87.5, now() - INTERVAL 1 HOUR, 'RU'),
('evt-001-003', 'user-001', 'motion', 'motion_quality', 92.3, now() - INTERVAL 30 MINUTE, 'RU'),

-- User 001 - вчера
('evt-001-004', 'user-001', 'step_count', 'steps', 8320.0, now() - INTERVAL 1 DAY - INTERVAL 5 HOUR, 'RU'),
('evt-001-005', 'user-001', 'battery', 'battery_level', 65.2, now() - INTERVAL 1 DAY - INTERVAL 3 HOUR, 'RU'),
('evt-001-006', 'user-001', 'motion', 'motion_quality', 88.7, now() - INTERVAL 1 DAY - INTERVAL 1 HOUR, 'RU'),

-- User 002 - текущий день
('evt-002-001', 'user-002', 'step_count', 'steps', 6890.0, now() - INTERVAL 3 HOUR, 'EU'),
('evt-002-002', 'user-002', 'battery', 'battery_level', 92.1, now() - INTERVAL 2 HOUR, 'EU'),
('evt-002-003', 'user-002', 'motion', 'motion_quality', 95.4, now() - INTERVAL 1 HOUR, 'EU'),

-- User 003 - текущий день
('evt-003-001', 'user-003', 'step_count', 'steps', 4210.0, now() - INTERVAL 4 HOUR, 'US'),
('evt-003-002', 'user-003', 'battery', 'battery_level', 78.3, now() - INTERVAL 2 HOUR, 'US'),
('evt-003-003', 'user-003', 'motion', 'motion_quality', 85.6, now() - INTERVAL 1 HOUR, 'US');

-- Создание тестовой витрины (обычно заполняется ETL)
INSERT INTO mart_report_user_daily (
    user_id, 
    report_date, 
    metrics.name, 
    metrics.events_count, 
    metrics.value_sum, 
    metrics.value_avg, 
    metrics.value_min, 
    metrics.value_max,
    region,
    prosthetic_model
) VALUES
-- User 001 - сегодня
(
    'user-001',
    today(),
    ['steps', 'battery_level', 'motion_quality'],
    [1, 1, 1],
    [5420.0, 87.5, 92.3],
    [5420.0, 87.5, 92.3],
    [5420.0, 87.5, 92.3],
    [5420.0, 87.5, 92.3],
    'RU',
    'BionicPRO-X1'
),
-- User 001 - вчера
(
    'user-001',
    today() - INTERVAL 1 DAY,
    ['steps', 'battery_level', 'motion_quality'],
    [1, 1, 1],
    [8320.0, 65.2, 88.7],
    [8320.0, 65.2, 88.7],
    [8320.0, 65.2, 88.7],
    [8320.0, 65.2, 88.7],
    'RU',
    'BionicPRO-X1'
),
-- User 002 - сегодня
(
    'user-002',
    today(),
    ['steps', 'battery_level', 'motion_quality'],
    [1, 1, 1],
    [6890.0, 92.1, 95.4],
    [6890.0, 92.1, 95.4],
    [6890.0, 92.1, 95.4],
    [6890.0, 92.1, 95.4],
    'EU',
    'BionicPRO-X2'
),
-- User 003 - сегодня
(
    'user-003',
    today(),
    ['steps', 'battery_level', 'motion_quality'],
    [1, 1, 1],
    [4210.0, 78.3, 85.6],
    [4210.0, 78.3, 85.6],
    [4210.0, 78.3, 85.6],
    [4210.0, 78.3, 85.6],
    'US',
    'BionicPRO-X1'
);



