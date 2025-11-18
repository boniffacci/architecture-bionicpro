# airflow_etl_dag.py
# ETL-процесс для BionicPRO, обновляющий витрины в ClickHouse
# Запускается ежедневно в 02:00 UTC

from datetime import datetime, timedelta
from typing import Dict, List
from decimal import Decimal

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

# Конфигурация соединений
CRM_DATABASE_URL = Variable.get("CRM_DATABASE_URL", 
                               "postgresql://postgres:password@localhost/crm_db")
TELEMETRY_DATABASE_URL = Variable.get("TELEMETRY_DATABASE_URL",
                                      "postgresql://postgres:password@localhost/telemetry_db")
CLICKHOUSE_DATABASE_URL = Variable.get("CLICKHOUSE_DATABASE_URL",
                                       "clickhouse://default:@localhost/reports_db")

# DAG параметры
DAG_ID = "bionicpro_etl_daily"
default_args = {
    "owner": "data_engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2024, 1, 1),
}

# ============================================================================
# ETL ФУНКЦИИ
# ============================================================================

def extract_crm_data(**context):
    """
    Extract: Извлекаем данные из CRM
    
    Достаём:
    - История платежей за вчерашний день
    - Активные подписки
    - Информацию о пользователях
    """
    execution_date = context["execution_date"]
    yesterday = (execution_date - timedelta(days=1)).date()
    
    crm_engine = create_engine(CRM_DATABASE_URL)
    
    with Session(crm_engine) as session:
        # SQL для извлечения данных CRM
        query = text("""
            SELECT 
                u.user_id,
                u.user_uuid,
                p.subscription_id,
                p.subscription_type,
                p.monthly_cost,
                pay.payment_date,
                pay.amount,
                pay.status
            FROM crm_users u
            LEFT JOIN crm_subscriptions p ON u.user_id = p.user_id
            LEFT JOIN crm_payments pay ON p.subscription_id = pay.subscription_id
            WHERE DATE(pay.payment_date) = :target_date
               OR (p.is_active = true AND pay.payment_date IS NULL)
            ORDER BY u.user_id
        """)
        
        result = session.execute(query, {"target_date": yesterday})
        crm_data = [dict(row) for row in result]
    
    context["task_instance"].xcom_push(key="crm_data", value=crm_data)
    print(f"✓ Извлечено {len(crm_data)} записей из CRM")
    return len(crm_data)


def extract_telemetry_data(**context):
    """
    Extract: Извлекаем данные телеметрии
    
    Достаём:
    - События с протезов (power_on/off, errors, etc.)
    - Метрики батареи
    """
    execution_date = context["execution_date"]
    yesterday = (execution_date - timedelta(days=1)).date()
    
    telemetry_engine = create_engine(TELEMETRY_DATABASE_URL)
    
    with Session(telemetry_engine) as session:
        # События телеметрии
        events_query = text("""
            SELECT 
                te.prosthetic_id,
                COUNT(CASE WHEN te.event_type = 'power_on' THEN 1 END) as power_on_count,
                COUNT(CASE WHEN te.event_type = 'power_off' THEN 1 END) as power_off_count,
                COUNT(CASE WHEN te.severity = 'warning' THEN 1 END) as warning_count,
                COUNT(CASE WHEN te.severity = 'error' THEN 1 END) as error_count,
                COUNT(CASE WHEN te.severity = 'critical' THEN 1 END) as critical_error_count
            FROM telemetry_events te
            WHERE DATE(te.event_timestamp) = :target_date
            GROUP BY te.prosthetic_id
        """)
        
        events_result = session.execute(events_query, {"target_date": yesterday})
        telemetry_events = [dict(row) for row in events_result]
        
        # Метрики батареи
        battery_query = text("""
            SELECT 
                bm.prosthetic_id,
                AVG(CASE WHEN bm.current_ma < 0 THEN ABS(bm.current_ma) ELSE NULL END) as avg_discharge_active,
                AVG(CASE WHEN bm.is_charging THEN bm.current_ma ELSE NULL END) as avg_charge_rate,
                COUNT(DISTINCT CASE WHEN bm.charge_level > 95 AND bm.is_charging THEN DATE(bm.metric_timestamp) END) as charge_cycles
            FROM battery_metrics bm
            WHERE DATE(bm.metric_timestamp) = :target_date
            GROUP BY bm.prosthetic_id
        """)
        
        battery_result = session.execute(battery_query, {"target_date": yesterday})
        telemetry_battery = [dict(row) for row in battery_result]
    
    context["task_instance"].xcom_push(key="telemetry_events", value=telemetry_events)
    context["task_instance"].xcom_push(key="telemetry_battery", value=telemetry_battery)
    
    print(f"✓ Извлечено {len(telemetry_events)} событий и {len(telemetry_battery)} метрик батареи")
    return len(telemetry_events) + len(telemetry_battery)


def transform_user_monthly_metrics(**context):
    """
    Transform: Трансформируем данные для витрины user_monthly_metrics
    
    Витрина содержит:
    - Total payments (все платежи за месяц)
    - Successful payments
    - Failed payments count
    - Active subscriptions count
    - Total subscription cost
    """
    execution_date = context["execution_date"]
    report_date = datetime(execution_date.year, execution_date.month, 1).date()
    
    crm_engine = create_engine(CRM_DATABASE_URL)
    
    with Session(crm_engine) as session:
        query = text("""
            SELECT 
                u.user_id,
                u.user_uuid,
                COALESCE(SUM(CASE WHEN pay.status = 'success' THEN pay.amount ELSE 0 END), 0) as successful_payments,
                COALESCE(SUM(CASE WHEN pay.status = 'failed' THEN pay.amount ELSE 0 END), 0) as failed_payments_amount,
                COUNT(CASE WHEN pay.status = 'failed' THEN 1 END) as failed_payments_count,
                COUNT(DISTINCT CASE WHEN s.is_active = true THEN s.subscription_id END) as active_subscriptions_count,
                COALESCE(SUM(s.monthly_cost), 0) as subscription_cost_total
            FROM crm_users u
            LEFT JOIN crm_subscriptions s ON u.user_id = s.user_id
            LEFT JOIN crm_payments pay ON s.subscription_id = pay.subscription_id
                AND DATE_TRUNC('month', pay.payment_date)::date = :report_date
            GROUP BY u.user_id, u.user_uuid
        """)
        
        result = session.execute(query, {"report_date": report_date})
        metrics = [dict(row) for row in result]
    
    context["task_instance"].xcom_push(key="user_monthly_metrics", value=metrics)
    print(f"✓ Трансформировано {len(metrics)} метрик пользователей")
    return metrics


def transform_prosthetic_monthly_metrics(**context):
    """
    Transform: Трансформируем данные для витрины prosthetic_monthly_metrics
    
    Витрина содержит:
    - Количество включений/выключений
    - Время активного использования
    - Средняя скорость разрядки
    - Количество ошибок
    - Время простоя
    """
    execution_date = context["execution_date"]
    yesterday = (execution_date - timedelta(days=1)).date()
    
    crm_engine = create_engine(CRM_DATABASE_URL)
    telemetry_engine = create_engine(TELEMETRY_DATABASE_URL)
    
    prosthetic_metrics = []
    
    with Session(crm_engine) as crm_session, Session(telemetry_engine) as telemetry_session:
        # Берём все активные протезы
        prosthetics = crm_session.query("prosthetic_id", "user_id", "user_uuid", "prosthetic_uuid", "device_type").all()
        
        for p in prosthetics:
            # Считаем события для протеза
            events_query = text("""
                SELECT 
                    COUNT(CASE WHEN event_type = 'power_on' THEN 1 END) as power_on_count,
                    COUNT(CASE WHEN event_type = 'power_off' THEN 1 END) as power_off_count,
                    COUNT(CASE WHEN severity = 'warning' THEN 1 END) as warning_count,
                    COUNT(CASE WHEN severity = 'error' THEN 1 END) as error_count,
                    COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_error_count
                FROM telemetry_events
                WHERE prosthetic_id = :prosthetic_id
                  AND DATE(event_timestamp) = :target_date
            """)
            
            telemetry_result = telemetry_session.execute(
                events_query,
                {"prosthetic_id": p.prosthetic_id, "target_date": yesterday}
            ).fetchone()
            
            # Считаем метрики батареи
            battery_query = text("""
                SELECT 
                    AVG(CASE WHEN current_ma < 0 THEN ABS(current_ma) ELSE NULL END) as avg_discharge_active,
                    AVG(CASE WHEN is_charging THEN current_ma ELSE NULL END) as avg_charge_rate,
                    COUNT(DISTINCT CASE WHEN charge_level > 95 AND is_charging THEN DATE(metric_timestamp) END) as charge_cycles
                FROM battery_metrics
                WHERE prosthetic_id = :prosthetic_id
                  AND DATE(metric_timestamp) = :target_date
            """)
            
            battery_result = telemetry_session.execute(
                battery_query,
                {"prosthetic_id": p.prosthetic_id, "target_date": yesterday}
            ).fetchone()
            
            prosthetic_metrics.append({
                "prosthetic_id": p.prosthetic_id,
                "user_id": p.user_id,
                "user_uuid": p.user_uuid,
                "prosthetic_uuid": p.prosthetic_uuid,
                "device_type": p.device_type,
                "power_on_count": telemetry_result[0] or 0,
                "power_off_count": telemetry_result[1] or 0,
                "warning_count": telemetry_result[3] or 0,
                "error_count": telemetry_result[4] or 0,
                "critical_error_count": telemetry_result[5] or 0,
                "avg_discharge_active": battery_result[0] or 0.0,
                "avg_charge_rate": battery_result[1] or 0.0,
                "charge_cycles": battery_result[2] or 0,
            })
    
    context["task_instance"].xcom_push(key="prosthetic_monthly_metrics", value=prosthetic_metrics)
    print(f"✓ Трансформировано {len(prosthetic_metrics)} метрик протезов")
    return prosthetic_metrics


def load_to_clickhouse(**context):
    """
    Load: Загружаем трансформированные данные в ClickHouse
    
    Создаём/обновляем витрины:
    - report_user_monthly_metrics
    - report_prosthetic_monthly_metrics
    """
    execution_date = context["execution_date"]
    report_date = datetime(execution_date.year, execution_date.month, 1).date()
    
    user_metrics = context["task_instance"].xcom_pull(key="user_monthly_metrics")
    prosthetic_metrics = context["task_instance"].xcom_pull(key="prosthetic_monthly_metrics")
    
    clickhouse_engine = create_engine(CLICKHOUSE_DATABASE_URL)
    
    with Session(clickhouse_engine) as session:
        # Загружаем метрики пользователей
        for metric in user_metrics:
            # ClickHouse INSERT (используем raw SQL)
            insert_query = text("""
                INSERT INTO report_user_monthly_metrics (
                    report_date, user_id, user_uuid,
                    total_payments, successful_payments, failed_payments_count,
                    active_subscriptions_count, subscription_cost_total
                ) VALUES (
                    :report_date, :user_id, :user_uuid,
                    :total_payments, :successful_payments, :failed_payments_count,
                    :active_subscriptions_count, :subscription_cost_total
                )
            """)
            
            session.execute(insert_query, {
                "report_date": report_date,
                "user_id": metric["user_id"],
                "user_uuid": metric["user_uuid"],
                "total_payments": metric["successful_payments"] + metric["failed_payments_amount"],
                "successful_payments": metric["successful_payments"],
                "failed_payments_count": metric["failed_payments_count"],
                "active_subscriptions_count": metric["active_subscriptions_count"],
                "subscription_cost_total": metric["subscription_cost_total"],
            })
        
        # Загружаем метрики протезов
        for metric in prosthetic_metrics:
            insert_query = text("""
                INSERT INTO report_prosthetic_monthly_metrics (
                    report_date, prosthetic_id, user_id, user_uuid, prosthetic_uuid, device_type,
                    power_on_count, power_off_count, total_active_hours,
                    avg_discharge_rate_active, avg_discharge_rate_idle, avg_charge_rate,
                    charge_cycles, warning_count, error_count, critical_error_count, downtime_minutes
                ) VALUES (
                    :report_date, :prosthetic_id, :user_id, :user_uuid, :prosthetic_uuid, :device_type,
                    :power_on_count, :power_off_count, :total_active_hours,
                    :avg_discharge_rate_active, :avg_discharge_rate_idle, :avg_charge_rate,
                    :charge_cycles, :warning_count, :error_count, :critical_error_count, :downtime_minutes
                )
            """)
            
            session.execute(insert_query, {
                "report_date": report_date,
                "prosthetic_id": metric["prosthetic_id"],
                "user_id": metric["user_id"],
                "user_uuid": metric["user_uuid"],
                "prosthetic_uuid": metric["prosthetic_uuid"],
                "device_type": metric["device_type"],
                "power_on_count": metric["power_on_count"],
                "power_off_count": metric["power_off_count"],
                "total_active_hours": metric["power_on_count"] * 4.0,  # Примерная оценка
                "avg_discharge_rate_active": metric["avg_discharge_active"],
                "avg_discharge_rate_idle": metric["avg_discharge_active"] * 0.3,  # Примерная оценка
                "avg_charge_rate": metric["avg_charge_rate"],
                "charge_cycles": metric["charge_cycles"],
                "warning_count": metric["warning_count"],
                "error_count": metric["error_count"],
                "critical_error_count": metric["critical_error_count"],
                "downtime_minutes": metric["error_count"] * 15,  # Примерная оценка
            })
        
        session.commit()
    
    print(f"✓ Загружено {len(user_metrics)} метрик пользователей в ClickHouse")
    print(f"✓ Загружено {len(prosthetic_metrics)} метрик протезов в ClickHouse")
    return {"users": len(user_metrics), "prosthetics": len(prosthetic_metrics)}


# ============================================================================
# DAG ОПРЕДЕЛЕНИЕ
# ============================================================================

dag = DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description="Daily ETL for BionicPRO: CRM and Telemetry to ClickHouse",
    schedule_interval="0 2 * * *",  # Запускается каждый день в 02:00 UTC
    catchup=False,
    tags=["bionicpro", "etl", "analytics"],
)

# Задачи Extract
extract_crm = PythonOperator(
    task_id="extract_crm_data",
    python_callable=extract_crm_data,
    provide_context=True,
    dag=dag,
)

extract_telemetry = PythonOperator(
    task_id="extract_telemetry_data",
    python_callable=extract_telemetry_data,
    provide_context=True,
    dag=dag,
)

# Задачи Transform
transform_user = PythonOperator(
    task_id="transform_user_monthly_metrics",
    python_callable=transform_user_monthly_metrics,
    provide_context=True,
    dag=dag,
)

transform_prosthetic = PythonOperator(
    task_id="transform_prosthetic_monthly_metrics",
    python_callable=transform_prosthetic_monthly_metrics,
    provide_context=True,
    dag=dag,
)

# Задача Load
load = PythonOperator(
    task_id="load_to_clickhouse",
    python_callable=load_to_clickhouse,
    provide_context=True,
    dag=dag,
)

# Определяем зависимости
[extract_crm, extract_telemetry] >> [transform_user, transform_prosthetic] >> load
