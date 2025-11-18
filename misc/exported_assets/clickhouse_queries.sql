# clickhouse_queries.sql
# Примеры SQL-запросов для ClickHouse - Витрины отчётов BionicPRO

# ==============================================================================
# ВИТРИНА 1: Финансовые отчёты пользователей (Monthly)
# ==============================================================================

-- Запрос 1: Все платежи пользователя за месяц
SELECT 
    user_id,
    user_uuid,
    report_date,
    total_payments,
    successful_payments,
    failed_payments_count,
    active_subscriptions_count,
    subscription_cost_total,
    (successful_payments / total_payments * 100) AS success_rate_pct
FROM reports_db.report_user_monthly_metrics
WHERE user_id = 1
ORDER BY report_date DESC
LIMIT 12;  -- Последние 12 месяцев


-- Запрос 2: Статистика платежей за год (агрегирование витрины)
SELECT 
    toYear(report_date) AS year,
    toMonth(report_date) AS month,
    COUNT(DISTINCT user_id) AS active_users,
    SUM(total_payments) AS total_revenue,
    AVG(successful_payments) AS avg_payment_per_user,
    SUM(failed_payments_count) AS total_failed_payments
FROM reports_db.report_user_monthly_metrics
WHERE report_date >= '2023-01-01'
GROUP BY year, month
ORDER BY year DESC, month DESC;


-- Запрос 3: Топ-10 пользователей по расходам (за последний месяц)
SELECT 
    user_id,
    user_uuid,
    successful_payments,
    subscription_cost_total,
    active_subscriptions_count
FROM reports_db.report_user_monthly_metrics
WHERE report_date = '2024-01-01'
ORDER BY successful_payments DESC
LIMIT 10;


-- Запрос 4: Пользователи с проблемами платежей
SELECT 
    user_id,
    report_date,
    total_payments,
    failed_payments_count,
    CASE 
        WHEN failed_payments_count >= 2 THEN 'HIGH_RISK'
        WHEN failed_payments_count = 1 THEN 'MEDIUM_RISK'
        ELSE 'OK'
    END AS payment_status
FROM reports_db.report_user_monthly_metrics
WHERE report_date >= '2023-11-01'
    AND failed_payments_count > 0
ORDER BY failed_payments_count DESC, user_id;


# ==============================================================================
# ВИТРИНА 2: Технические метрики протезов (Monthly)
# ==============================================================================

-- Запрос 5: Все метрики протеза за месяц
SELECT 
    prosthetic_id,
    user_id,
    device_type,
    report_date,
    power_on_count,
    power_off_count,
    total_active_hours,
    avg_discharge_rate_active,
    avg_charge_rate,
    charge_cycles,
    warning_count,
    error_count,
    critical_error_count,
    downtime_minutes
FROM reports_db.report_prosthetic_monthly_metrics
WHERE user_id = 1 AND prosthetic_id = 1
ORDER BY report_date DESC;


-- Запрос 6: Анализ надёжности протеза ( 6 месяцев)
SELECT 
    report_date,
    prosthetic_id,
    device_type,
    power_on_count,
    error_count + critical_error_count AS total_errors,
    ROUND(100 - (error_count + critical_error_count) / NULLIF(power_on_count, 0) * 100, 2) AS reliability_pct,
    downtime_minutes,
    CASE 
        WHEN error_count + critical_error_count = 0 THEN '✓ Здоров'
        WHEN error_count + critical_error_count <= 2 THEN '⚠ Внимание'
        ELSE '✗ Требует ремонта'
    END AS status
FROM reports_db.report_prosthetic_monthly_metrics
WHERE prosthetic_id = 1 AND report_date >= '2023-07-01'
ORDER BY report_date DESC;


-- Запрос 7: Анализ батареи протеза (тренд разрядки)
SELECT 
    report_date,
    prosthetic_id,
    avg_discharge_rate_active,
    avg_discharge_rate_idle,
    avg_charge_rate,
    charge_cycles,
    -- Рассчитываем время работы на полной батарее
    ROUND(100 / NULLIF(avg_discharge_rate_active, 0), 1) AS work_hours_per_charge,
    -- Рассчитываем время зарядки с 0 до 100%
    ROUND(100 / NULLIF(avg_charge_rate, 0), 1) AS charge_hours
FROM reports_db.report_prosthetic_monthly_metrics
WHERE prosthetic_id = 1 AND report_date >= '2023-10-01'
ORDER BY report_date DESC;


-- Запрос 8: Протезы с максимальной нагрузкой (использованием)
SELECT 
    prosthetic_id,
    device_type,
    report_date,
    power_on_count,
    total_active_hours,
    ROUND(total_active_hours / (power_on_count / 24), 2) AS avg_session_hours,
    avg_discharge_rate_active,
    charge_cycles
FROM reports_db.report_prosthetic_monthly_metrics
WHERE report_date = '2024-01-01'
    AND total_active_hours > 0
ORDER BY total_active_hours DESC
LIMIT 20;


# ==============================================================================
# КРОСС-ВИТРИНЫ ЗАПРОСЫ (Объединение данных)
# ==============================================================================

-- Запрос 9: Полный отчёт пользователя на месяц (финансы + техника)
SELECT 
    u.user_id,
    u.user_uuid,
    u.report_date,
    u.total_payments AS financial_total_payments,
    u.successful_payments AS financial_successful,
    u.failed_payments_count,
    u.subscription_cost_total,
    p.prosthetic_id,
    p.device_type,
    p.power_on_count,
    p.total_active_hours,
    p.error_count,
    p.critical_error_count,
    CASE 
        WHEN u.failed_payments_count > 0 THEN 'PAYMENT_ISSUE'
        WHEN p.critical_error_count > 0 THEN 'DEVICE_ISSUE'
        WHEN p.error_count > 1 THEN 'WARNINGS'
        ELSE 'OK'
    END AS overall_status
FROM reports_db.report_user_monthly_metrics u
LEFT JOIN reports_db.report_prosthetic_monthly_metrics p 
    ON u.user_id = p.user_id AND u.report_date = p.report_date
WHERE u.user_id = 1 AND u.report_date = '2024-01-01';


-- Запрос 10: Статистика по устройствам (для ML-команды)
SELECT 
    device_type,
    report_date,
    COUNT(DISTINCT prosthetic_id) AS num_devices,
    AVG(total_active_hours) AS avg_daily_usage_hours,
    AVG(avg_discharge_rate_active) AS avg_battery_drain_mah_h,
    SUM(CASE WHEN error_count > 0 THEN 1 ELSE 0 END) AS devices_with_errors,
    SUM(critical_error_count) AS total_critical_errors,
    ROUND(100 - (SUM(error_count + critical_error_count) / NULLIF(SUM(power_on_count), 0) * 100), 2) AS reliability_pct
FROM reports_db.report_prosthetic_monthly_metrics
WHERE report_date >= '2023-10-01'
GROUP BY device_type, report_date
ORDER BY device_type, report_date DESC;


# ==============================================================================
# ПРОИЗВОДИТЕЛЬНОСТЬ И ОТЛАДКА
# ==============================================================================

-- Запрос 11: Информация о партициях (размер, количество строк)
SELECT 
    table,
    partition,
    COUNT(*) AS num_rows,
    formatReadableSize(sum(bytes_on_disk)) AS disk_size
FROM system.parts
WHERE database = 'reports_db'
GROUP BY table, partition
ORDER BY table, partition DESC;


-- Запрос 12: Проверка целостности витрин (нет дублей)
SELECT 
    user_id,
    report_date,
    COUNT(*) AS count
FROM reports_db.report_user_monthly_metrics
GROUP BY user_id, report_date
HAVING COUNT(*) > 1
LIMIT 10;


-- Запрос 13: Время последнего обновления витрин
SELECT 
    'report_user_monthly_metrics' AS table_name,
    MAX(last_updated) AS last_update_time,
    MAX(created_at) AS creation_time
FROM reports_db.report_user_monthly_metrics
UNION ALL
SELECT 
    'report_prosthetic_monthly_metrics',
    MAX(last_updated),
    MAX(created_at)
FROM reports_db.report_prosthetic_monthly_metrics;


-- Запрос 14: Покрытие данных (какие месяцы есть в витринах)
SELECT 
    toYYYYMM(report_date) AS year_month,
    COUNT(DISTINCT user_id) AS num_users,
    COUNT(DISTINCT prosthetic_id) AS num_prosthetics
FROM reports_db.report_prosthetic_monthly_metrics
GROUP BY year_month
ORDER BY year_month DESC;


# ==============================================================================
# ПРИМЕРЫ ДЛЯ API ОТЧЁТОВ
# ==============================================================================

-- Query 15: Для API endpoint GET /reports/user/{user_id}?month=2024-01
-- Это будет основной query для отчёта пользователя

PREPARE user_report AS
SELECT 
    u.user_id,
    u.user_uuid,
    u.report_date,
    -- Финансовая часть
    u.total_payments,
    u.successful_payments,
    u.failed_payments_count,
    u.subscription_cost_total,
    -- Техническая часть (агрегируем все протезы)
    arrayJoin(
        arrayMap(
            (pid, ptype, poh, pof, tah, errs, cerrs) -> 
            (pid, ptype, poh, pof, tah, errs, cerrs),
            [p.prosthetic_id],
            [p.device_type],
            [p.power_on_count],
            [p.power_off_count],
            [p.total_active_hours],
            [p.error_count],
            [p.critical_error_count]
        )
    ) AS prosthetic_data
FROM reports_db.report_user_monthly_metrics u
LEFT ARRAY JOIN (
    SELECT 
        prosthetic_id,
        device_type,
        power_on_count,
        power_off_count,
        total_active_hours,
        error_count,
        critical_error_count
    FROM reports_db.report_prosthetic_monthly_metrics
    WHERE user_id = u.user_id AND report_date = u.report_date
) p ON 1=1
WHERE u.user_id = ? AND u.report_date = ?;


-- Query 16: Для отправки в API как JSON
SELECT 
    user_id,
    user_uuid,
    report_date,
    multiIf(
        failed_payments_count > 0, 'PAYMENT_ISSUE',
        total_payments = 0, 'NO_ACTIVITY',
        'OK'
    ) AS status
FROM reports_db.report_user_monthly_metrics
WHERE user_id = ?
FORMAT JSON;
