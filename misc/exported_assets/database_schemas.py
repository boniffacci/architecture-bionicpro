# database_schemas.py
# Схемы данных для BionicPRO: CRM, Telemetry и Reports
# SQLAlchemy 2.0 Declarative ORM API

from datetime import datetime, timedelta
from typing import Optional, List
from decimal import Decimal
import uuid

from sqlalchemy import create_engine, String, Integer, DateTime, Float, Boolean, Text, Numeric, ForeignKey, Date
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.sql import func

# ============================================================================
# БАЗОВАЯ КОНФИГУРАЦИЯ
# ============================================================================

Base = declarative_base()

# Для локальной разработки:
# CRM_DATABASE_URL = "postgresql://user:password@localhost/crm_db"
# TELEMETRY_DATABASE_URL = "postgresql://user:password@localhost/telemetry_db"
# CLICKHOUSE_DATABASE_URL = "clickhouse://default:@localhost/reports_db"

# ============================================================================
# CRM БД - OLTP (PostgreSQL)
# ============================================================================
# Таблицы: Users, Prosthetics, Subscriptions, Payments, SupportTickets

class CRMUser(Base):
    """Пользователи BionicPRO"""
    __tablename__ = "crm_users"
    
    user_id = __table__.c.Integer(primary_key=True)
    user_uuid = String(36, nullable=False, unique=True)  # UUID v4
    first_name = String(100, nullable=False)
    last_name = String(100, nullable=False)
    email = String(255, nullable=False, unique=True)
    phone = String(20, nullable=True)
    created_at = DateTime(timezone=True, server_default=func.now())
    updated_at = DateTime(timezone=True, server_default=func.now(), onupdate=func.now())
    
    # Отношения
    prosthetics = relationship("CRMProsthetic", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("CRMSubscription", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("CRMPayment", back_populates="user", cascade="all, delete-orphan")
    support_tickets = relationship("CRMSupportTicket", back_populates="user", cascade="all, delete-orphan")


class CRMProsthetic(Base):
    """Протезы, принадлежащие пользователям"""
    __tablename__ = "crm_prosthetics"
    
    prosthetic_id = Integer(primary_key=True)
    user_id = Integer(ForeignKey("crm_users.user_id"), nullable=False)
    prosthetic_uuid = String(36, nullable=False, unique=True)  # UUID v4
    device_type = String(50, nullable=False)  # "left_arm", "right_leg", etc.
    serial_number = String(50, nullable=False, unique=True)
    model = String(100, nullable=False)
    purchase_date = Date(nullable=False)
    warranty_end_date = Date(nullable=True)
    is_active = Boolean(default=True)
    created_at = DateTime(timezone=True, server_default=func.now())
    updated_at = DateTime(timezone=True, server_default=func.now(), onupdate=func.now())
    
    # Отношения
    user = relationship("CRMUser", back_populates="prosthetics")
    telemetry_events = relationship("TelemetryEvent", back_populates="prosthetic")


class CRMSubscription(Base):
    """Подписки на сопровождение протезов"""
    __tablename__ = "crm_subscriptions"
    
    subscription_id = Integer(primary_key=True)
    user_id = Integer(ForeignKey("crm_users.user_id"), nullable=False)
    subscription_type = String(50, nullable=False)  # "basic", "premium", "enterprise"
    start_date = Date(nullable=False)
    end_date = Date(nullable=True)  # NULL если активна
    is_active = Boolean(default=True)
    monthly_cost = Numeric(10, 2, nullable=False)
    created_at = DateTime(timezone=True, server_default=func.now())
    updated_at = DateTime(timezone=True, server_default=func.now(), onupdate=func.now())
    
    # Отношения
    user = relationship("CRMUser", back_populates="subscriptions")


class CRMPayment(Base):
    """История платежей"""
    __tablename__ = "crm_payments"
    
    payment_id = Integer(primary_key=True)
    user_id = Integer(ForeignKey("crm_users.user_id"), nullable=False)
    subscription_id = Integer(ForeignKey("crm_subscriptions.subscription_id"), nullable=True)
    payment_date = DateTime(timezone=True, nullable=False)
    amount = Numeric(10, 2, nullable=False)
    payment_method = String(50, nullable=False)  # "card", "bank_transfer", etc.
    status = String(20, nullable=False)  # "success", "failed", "pending"
    description = Text(nullable=True)
    created_at = DateTime(timezone=True, server_default=func.now())
    
    # Отношения
    user = relationship("CRMUser", back_populates="payments")


class CRMSupportTicket(Base):
    """Обращения в поддержку"""
    __tablename__ = "crm_support_tickets"
    
    ticket_id = Integer(primary_key=True)
    user_id = Integer(ForeignKey("crm_users.user_id"), nullable=False)
    prosthetic_id = Integer(ForeignKey("crm_prosthetics.prosthetic_id"), nullable=True)
    title = String(255, nullable=False)
    description = Text(nullable=False)
    status = String(20, nullable=False)  # "open", "in_progress", "resolved", "closed"
    created_at = DateTime(timezone=True, server_default=func.now())
    updated_at = DateTime(timezone=True, server_default=func.now(), onupdate=func.now())
    resolved_at = DateTime(timezone=True, nullable=True)
    
    # Отношения
    user = relationship("CRMUser", back_populates="support_tickets")


# ============================================================================
# TELEMETRY БД - OLTP (PostgreSQL)
# ============================================================================
# Таблицы: Events, SystemDiagnostics, BatteryMetrics

class TelemetryEvent(Base):
    """События телеметрии с протезов"""
    __tablename__ = "telemetry_events"
    
    event_id = Integer(primary_key=True)
    prosthetic_id = Integer(ForeignKey("crm_prosthetics.prosthetic_id"), nullable=False)
    event_type = String(50, nullable=False)  # "power_on", "power_off", "error", "calibration", etc.
    event_timestamp = DateTime(timezone=True, nullable=False)
    event_value = String(255, nullable=True)  # Дополнительные данные события
    severity = String(20, nullable=False, default="info")  # "info", "warning", "error", "critical"
    created_at = DateTime(timezone=True, server_default=func.now())
    
    # Отношения
    prosthetic = relationship("CRMProsthetic", back_populates="telemetry_events")


class BatteryMetric(Base):
    """Метрики батареи"""
    __tablename__ = "battery_metrics"
    
    metric_id = Integer(primary_key=True)
    prosthetic_id = Integer(ForeignKey("crm_prosthetics.prosthetic_id"), nullable=False)
    metric_timestamp = DateTime(timezone=True, nullable=False)
    charge_level = Float(nullable=False)  # 0-100%
    current_ma = Float(nullable=False)  # Ток в миллиамперах (+ разрядка, - зарядка)
    is_charging = Boolean(nullable=False)
    created_at = DateTime(timezone=True, server_default=func.now())


# ============================================================================
# REPORTS БД - OLAP (ClickHouse) - на основе ClickHouse
# ============================================================================
# Витрины данных для отчётов пользователей

class ReportUserMonthlyMetrics(Base):
    """Витрина 1: Ежемесячные метрики пользователя"""
    __tablename__ = "report_user_monthly_metrics"
    
    # Ключевые поля
    report_date = Date(nullable=False)  # Первый день месяца
    user_id = Integer(nullable=False)
    user_uuid = String(36, nullable=False)
    
    # KPIs: Финансовые
    total_payments = Numeric(10, 2, nullable=False, default=0)
    successful_payments = Numeric(10, 2, nullable=False, default=0)
    failed_payments_count = Integer(nullable=False, default=0)
    
    # KPIs: Подписки
    active_subscriptions_count = Integer(nullable=False, default=0)
    subscription_cost_total = Numeric(10, 2, nullable=False, default=0)
    
    # Метаданные для сортировки (ORDER BY)
    last_updated = DateTime(timezone=True, server_default=func.now())
    created_at = DateTime(timezone=True, server_default=func.now())
    
    # ClickHouse специфика (если используется):
    # ENGINE = ReplicatedMergeTree(...) PARTITION BY toYYYYMM(report_date) ORDER BY (user_id, report_date)


class ReportProstheticMonthlyMetrics(Base):
    """Витрина 2: Ежемесячные метрики протеза"""
    __tablename__ = "report_prosthetic_monthly_metrics"
    
    # Ключевые поля
    report_date = Date(nullable=False)  # Первый день месяца
    prosthetic_id = Integer(nullable=False)
    user_id = Integer(nullable=False)
    user_uuid = String(36, nullable=False)
    prosthetic_uuid = String(36, nullable=False)
    device_type = String(50, nullable=False)
    
    # KPIs: Использование
    power_on_count = Integer(nullable=False, default=0)
    power_off_count = Integer(nullable=False, default=0)
    total_active_hours = Float(nullable=False, default=0)  # Часы активного использования
    
    # KPIs: Батарея
    avg_discharge_rate_active = Float(nullable=False, default=0)  # mAh/h при работе
    avg_discharge_rate_idle = Float(nullable=False, default=0)    # mAh/h в режиме ожидания
    avg_charge_rate = Float(nullable=False, default=0)            # mAh/h при зарядке
    charge_cycles = Integer(nullable=False, default=0)
    
    # KPIs: Проблемы
    warning_count = Integer(nullable=False, default=0)
    error_count = Integer(nullable=False, default=0)
    critical_error_count = Integer(nullable=False, default=0)
    downtime_minutes = Integer(nullable=False, default=0)
    
    # Метаданные
    last_updated = DateTime(timezone=True, server_default=func.now())
    created_at = DateTime(timezone=True, server_default=func.now())
    
    # ClickHouse специфика (если используется):
    # ENGINE = ReplicatedMergeTree(...) PARTITION BY toYYYYMM(report_date) ORDER BY (user_id, prosthetic_id, report_date)


# ============================================================================
# HELPER ФУНКЦИИ
# ============================================================================

def create_crm_engine(database_url: str):
    """Создаёт engine для CRM БД"""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def create_telemetry_engine(database_url: str):
    """Создаёт engine для Telemetry БД"""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def create_reports_engine(database_url: str):
    """Создаёт engine для Reports БД (ClickHouse)"""
    # Для ClickHouse может потребоваться специальный драйвер
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine
