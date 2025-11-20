INSERT INTO raw_crm_users (user_id, username, email, contract_number, prosthetic_model, region, created_at)
VALUES
    ('user-001', 'ivan_ivanov', 'ivan@example.com', 'CTR-001', 'ProHand-X1', 'Москва', now() - INTERVAL 30 DAY),
    ('user-002', 'maria_petrova', 'maria@example.com', 'CTR-002', 'ProLeg-Z2', 'Санкт-Петербург', now() - INTERVAL 60 DAY);

INSERT INTO raw_telemetry (event_id, user_id, event_type, metric_name, metric_value, event_timestamp, region)
VALUES
    ('evt-001', 'user-001', 'step', 'steps_count', 1500, today() - 1, 'Москва'),
    ('evt-002', 'user-001', 'step', 'steps_count', 2000, today(), 'Москва'),
    ('evt-003', 'user-001', 'battery', 'battery_level', 85, today() - 1, 'Москва'),
    ('evt-004', 'user-001', 'battery', 'battery_level', 80, today(), 'Москва'),
    ('evt-005', 'user-002', 'step', 'steps_count', 3000, today() - 1, 'Санкт-Петербург'),
    ('evt-006', 'user-002', 'step', 'steps_count', 3500, today(), 'Санкт-Петербург');

INSERT INTO mart_report_user_daily (
    user_id, report_date, 
    metrics.name, metrics.events_count, metrics.value_sum, metrics.value_avg, metrics.value_min, metrics.value_max,
    region, prosthetic_model
)
VALUES
    ('user-001', today() - 1, ['steps_count', 'battery_level'], [1, 1], [1500, 85], [1500, 85], [1500, 85], [1500, 85], 'Москва', 'ProHand-X1'),
    ('user-001', today(), ['steps_count', 'battery_level'], [1, 1], [2000, 80], [2000, 80], [2000, 80], [2000, 80], 'Москва', 'ProHand-X1'),
    ('user-002', today() - 1, ['steps_count', 'battery_level'], [1, 1], [3000, 90], [3000, 90], [3000, 90], [3000, 90], 'Санкт-Петербург', 'ProLeg-Z2'),
    ('user-002', today(), ['steps_count', 'battery_level'], [1, 1], [3500, 88], [3500, 88], [3500, 88], [3500, 88], 'Санкт-Петербург', 'ProLeg-Z2');

