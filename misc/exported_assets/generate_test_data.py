# generate_test_data.py
# Генератор тестовых данных для BionicPRO за 2-3 года
# Используется для 10-15 пользователей

import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from sqlalchemy.orm import Session
from database_schemas import (
    CRMUser, CRMProsthetic, CRMSubscription, CRMPayment, CRMSupportTicket,
    TelemetryEvent, BatteryMetric, create_crm_engine, create_telemetry_engine
)

# ============================================================================
# КОНФИГУРАЦИЯ ГЕНЕРАТОРА
# ============================================================================

NUM_USERS = 12  # 10-15 пользователей
NUM_PROSTHETICS_PER_USER = (1, 2)  # 1-2 протеза на пользователя
START_DATE = datetime.now() - timedelta(days=365*2.5)  # 2.5 года назад
END_DATE = datetime.now()

SUBSCRIPTION_TYPES = ["basic", "premium", "enterprise"]
SUBSCRIPTION_COSTS = {
    "basic": Decimal("2999.00"),
    "premium": Decimal("5999.00"),
    "enterprise": Decimal("9999.00")
}

DEVICE_TYPES = ["left_arm", "right_arm", "left_leg", "right_leg"]
MODELS = ["BionicPRO X1", "BionicPRO X2", "BionicPRO X3 Pro"]

SUPPORT_TICKET_STATUSES = ["open", "in_progress", "resolved", "closed"]
PAYMENT_METHODS = ["card", "bank_transfer", "paypal"]

# ============================================================================
# КЛАСС ГЕНЕРАТОРА
# ============================================================================

class TestDataGenerator:
    """Генератор тестовых данных для BionicPRO"""
    
    def __init__(self, crm_session: Session, telemetry_session: Session):
        self.crm_session = crm_session
        self.telemetry_session = telemetry_session
        self.users: List[CRMUser] = []
        self.prosthetics: List[CRMProsthetic] = []
        
    def generate_random_date_in_range(self, start: datetime, end: datetime) -> datetime:
        """Генерирует случайную дату в диапазоне"""
        time_between = (end - start).total_seconds()
        random_seconds = random.randint(0, int(time_between))
        return start + timedelta(seconds=random_seconds)
    
    # ========================================================================
    # CRM: ПОЛЬЗОВАТЕЛИ
    # ========================================================================
    
    def generate_crm_users(self) -> None:
        """Генерирует пользователей CRM"""
        print("Генерирую пользователей CRM...")
        
        first_names = ["Александр", "Мария", "Иван", "Ольга", "Петр", 
                       "Анна", "Сергей", "Елена", "Дмитрий", "Виктория",
                       "Алексей", "Татьяна"]
        last_names = ["Иванов", "Петров", "Сидоров", "Федоров", "Сергеев",
                      "Смирнов", "Волков", "Новиков", "Морозов", "Павлов"]
        
        for i in range(NUM_USERS):
            user = CRMUser(
                user_uuid=str(uuid.uuid4()),
                first_name=random.choice(first_names),
                last_name=random.choice(last_names),
                email=f"user{i+1}@bionicpro.ru",
                phone=f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}",
                created_at=self.generate_random_date_in_range(START_DATE, END_DATE - timedelta(days=30))
            )
            self.crm_session.add(user)
            self.users.append(user)
        
        self.crm_session.commit()
        print(f"✓ Создано {len(self.users)} пользователей")
    
    # ========================================================================
    # CRM: ПРОТЕЗЫ
    # ========================================================================
    
    def generate_crm_prosthetics(self) -> None:
        """Генерирует протезы для пользователей"""
        print("Генерирую протезы CRM...")
        
        for user in self.users:
            num_prosthetics = random.randint(*NUM_PROSTHETICS_PER_USER)
            for _ in range(num_prosthetics):
                purchase_date = self.generate_random_date_in_range(
                    START_DATE, END_DATE - timedelta(days=7)
                ).date()
                
                prosthetic = CRMProsthetic(
                    user_id=user.user_id,
                    prosthetic_uuid=str(uuid.uuid4()),
                    device_type=random.choice(DEVICE_TYPES),
                    serial_number=f"SN-{random.randint(100000, 999999)}",
                    model=random.choice(MODELS),
                    purchase_date=purchase_date,
                    warranty_end_date=purchase_date + timedelta(days=365),
                    is_active=random.random() > 0.1  # 90% активны
                )
                self.crm_session.add(prosthetic)
                self.prosthetics.append(prosthetic)
        
        self.crm_session.commit()
        print(f"✓ Создано {len(self.prosthetics)} протезов")
    
    # ========================================================================
    # CRM: ПОДПИСКИ
    # ========================================================================
    
    def generate_crm_subscriptions(self) -> None:
        """Генерирует подписки на сопровождение"""
        print("Генерирую подписки CRM...")
        
        subscription_count = 0
        for user in self.users:
            # 70% вероятность, что у пользователя есть подписка
            if random.random() < 0.7:
                start_date = self.generate_random_date_in_range(
                    START_DATE, END_DATE - timedelta(days=30)
                ).date()
                
                # 80% активных подписок
                is_active = random.random() < 0.8
                end_date = None if is_active else (start_date + timedelta(days=random.randint(30, 365)))
                
                subscription = CRMSubscription(
                    user_id=user.user_id,
                    subscription_type=random.choice(SUBSCRIPTION_TYPES),
                    start_date=start_date,
                    end_date=end_date,
                    is_active=is_active,
                    monthly_cost=SUBSCRIPTION_COSTS[subscription.subscription_type]
                )
                self.crm_session.add(subscription)
                subscription_count += 1
        
        self.crm_session.commit()
        print(f"✓ Создано {subscription_count} подписок")
    
    # ========================================================================
    # CRM: ПЛАТЕЖИ
    # ========================================================================
    
    def generate_crm_payments(self) -> None:
        """Генерирует историю платежей"""
        print("Генерирую платежи CRM...")
        
        payment_count = 0
        for user in self.users:
            subscriptions = self.crm_session.query(CRMSubscription).filter_by(user_id=user.user_id).all()
            
            for subscription in subscriptions:
                # Генерируем платежи за весь период подписки
                current_date = subscription.start_date
                end_date = subscription.end_date or END_DATE.date()
                
                while current_date <= end_date:
                    # 85% вероятность успешного платежа
                    is_success = random.random() < 0.85
                    
                    payment = CRMPayment(
                        user_id=user.user_id,
                        subscription_id=subscription.subscription_id,
                        payment_date=datetime.combine(current_date, datetime.min.time()) + timedelta(hours=random.randint(0, 23)),
                        amount=subscription.monthly_cost,
                        payment_method=random.choice(PAYMENT_METHODS),
                        status="success" if is_success else "failed",
                        description="Платёж за подписку" if is_success else "Платёж отклонён (недостаточно средств)"
                    )
                    self.crm_session.add(payment)
                    payment_count += 1
                    
                    # Следующий платёж через месяц
                    current_date += timedelta(days=30)
        
        self.crm_session.commit()
        print(f"✓ Создано {payment_count} платежей")
    
    # ========================================================================
    # CRM: ОБРАЩЕНИЯ В ПОДДЕРЖКУ
    # ========================================================================
    
    def generate_crm_support_tickets(self) -> None:
        """Генерирует обращения в поддержку"""
        print("Генерирую обращения в поддержку CRM...")
        
        issues = [
            ("Протез не включается", "Протез не реагирует на команды, не включается"),
            ("Проблемы с батареей", "Батарея быстро разряжается"),
            ("Дёргается движение", "При выполнении движений протез дёргается"),
            ("Боль при использовании", "Возникает боль в культе при использовании"),
            ("Нужна калибровка", "Требуется переобучение и переналадка протеза"),
            ("Вопрос по использованию", "Как правильно одевать и снимать протез?"),
            ("Доставка протеза", "Когда приезжает мой протез?"),
        ]
        
        ticket_count = 0
        for user in self.users:
            user_prosthetics = [p for p in self.prosthetics if p.user_id == user.user_id]
            
            # В среднем 2-3 обращения на пользователя
            num_tickets = random.randint(1, 4)
            
            for _ in range(num_tickets):
                title, description = random.choice(issues)
                ticket_date = self.generate_random_date_in_range(START_DATE, END_DATE)
                
                # 70% обращений имеют привязку к протезу
                prosthetic_id = None
                if user_prosthetics and random.random() < 0.7:
                    prosthetic_id = random.choice(user_prosthetics).prosthetic_id
                
                ticket = CRMSupportTicket(
                    user_id=user.user_id,
                    prosthetic_id=prosthetic_id,
                    title=title,
                    description=description,
                    status=random.choice(SUPPORT_TICKET_STATUSES),
                    created_at=ticket_date,
                    resolved_at=ticket_date + timedelta(hours=random.randint(1, 48)) if random.random() < 0.8 else None
                )
                self.crm_session.add(ticket)
                ticket_count += 1
        
        self.crm_session.commit()
        print(f"✓ Создано {ticket_count} обращений в поддержку")
    
    # ========================================================================
    # TELEMETRY: События
    # ========================================================================
    
    def generate_telemetry_events(self) -> None:
        """Генерирует события телеметрии с протезов"""
        print("Генерирую события телеметрии...")
        
        event_types_weights = {
            "power_on": 0.25,
            "power_off": 0.25,
            "battery_low": 0.10,
            "charging_started": 0.10,
            "charging_completed": 0.10,
            "calibration": 0.05,
            "warning": 0.10,
            "error": 0.04,
            "critical_error": 0.01
        }
        
        event_types = list(event_types_weights.keys())
        weights = list(event_types_weights.values())
        
        severity_map = {
            "power_on": "info",
            "power_off": "info",
            "battery_low": "warning",
            "charging_started": "info",
            "charging_completed": "info",
            "calibration": "info",
            "warning": "warning",
            "error": "error",
            "critical_error": "critical"
        }
        
        event_count = 0
        for prosthetic in self.prosthetics:
            # Примерно 50 событий в день * 2.5 года = 45,000 событий на протез
            current_date = START_DATE
            
            while current_date < END_DATE:
                # 3-8 событий в день на протез
                num_events_today = random.randint(3, 8)
                
                for _ in range(num_events_today):
                    event_type = random.choices(event_types, weights=weights)[0]
                    
                    event = TelemetryEvent(
                        prosthetic_id=prosthetic.prosthetic_id,
                        event_type=event_type,
                        event_timestamp=current_date + timedelta(minutes=random.randint(0, 1440)),
                        event_value=random.choice([None, "battery_80%", "temperature_35C", "ok"]),
                        severity=severity_map[event_type]
                    )
                    self.telemetry_session.add(event)
                    event_count += 1
                
                current_date += timedelta(days=1)
        
        self.telemetry_session.commit()
        print(f"✓ Создано {event_count} событий телеметрии")
    
    # ========================================================================
    # TELEMETRY: Метрики батареи
    # ========================================================================
    
    def generate_battery_metrics(self) -> None:
        """Генерирует метрики батареи"""
        print("Генерирую метрики батареи...")
        
        metric_count = 0
        for prosthetic in self.prosthetics:
            # По 2-4 замера в день
            current_date = START_DATE
            
            while current_date < END_DATE:
                num_metrics_today = random.randint(2, 4)
                
                for _ in range(num_metrics_today):
                    # Батарея: 20-100% при работе, 50-100% в режиме ожидания
                    is_charging = random.random() < 0.2
                    charge_level = random.uniform(20 if not is_charging else 0, 100)
                    
                    # Ток: +150 to 300 mA при зарядке, -50 to -150 mA при разрядке
                    if is_charging:
                        current_ma = random.uniform(150, 300)
                    else:
                        current_ma = random.uniform(-150, -50)
                    
                    metric = BatteryMetric(
                        prosthetic_id=prosthetic.prosthetic_id,
                        metric_timestamp=current_date + timedelta(minutes=random.randint(0, 1440)),
                        charge_level=charge_level,
                        current_ma=current_ma,
                        is_charging=is_charging
                    )
                    self.telemetry_session.add(metric)
                    metric_count += 1
                
                current_date += timedelta(days=1)
        
        self.telemetry_session.commit()
        print(f"✓ Создано {metric_count} метрик батареи")
    
    # ========================================================================
    # ГЛАВНАЯ ФУНКЦИЯ ГЕНЕРАЦИИ
    # ========================================================================
    
    def generate_all(self) -> None:
        """Генерирует все тестовые данные"""
        print("=" * 70)
        print("Генератор тестовых данных BionicPRO")
        print("=" * 70)
        
        self.generate_crm_users()
        self.generate_crm_prosthetics()
        self.generate_crm_subscriptions()
        self.generate_crm_payments()
        self.generate_crm_support_tickets()
        
        self.generate_telemetry_events()
        self.generate_battery_metrics()
        
        print("=" * 70)
        print("✓ ВСЕ ДАННЫЕ СГЕНЕРИРОВАНЫ УСПЕШНО!")
        print("=" * 70)


# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

if __name__ == "__main__":
    # Конфигурация БД
    CRM_DATABASE_URL = "postgresql://postgres:password@localhost:5432/crm_db"
    TELEMETRY_DATABASE_URL = "postgresql://postgres:password@localhost:5432/telemetry_db"
    
    # Создаём engines
    crm_engine = create_crm_engine(CRM_DATABASE_URL)
    telemetry_engine = create_telemetry_engine(TELEMETRY_DATABASE_URL)
    
    # Создаём сессии
    with Session(crm_engine) as crm_session, Session(telemetry_engine) as telemetry_session:
        generator = TestDataGenerator(crm_session, telemetry_session)
        generator.generate_all()
