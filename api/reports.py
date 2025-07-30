from typing import Dict, List, Any
import json
import random
from datetime import datetime, timedelta
from pydantic import BaseModel

class UsageReport(BaseModel):
    """Модель отчета об использовании протеза"""
    user_id: str
    username: str
    report_period: str
    generated_at: str
    prosthetic_id: str
    total_usage_hours: float
    daily_usage: List[Dict[str, Any]]
    battery_stats: Dict[str, Any]
    movement_patterns: Dict[str, Any]
    calibration_history: List[Dict[str, Any]]

def generate_mock_report(user_info: dict) -> UsageReport:
    """Генерировать мок-данные для отчета пользователя"""
    
    # Simulate different prosthetic devices for different users
    prosthetic_id = f"BIONIC-{user_info['username'].upper()}-{random.randint(1000, 9999)}"
    
    # Generate daily usage data for the last 30 days
    daily_usage = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(30):
        current_date = base_date + timedelta(days=i)
        daily_usage.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "usage_hours": round(random.uniform(6, 12), 2),
            "movements_count": random.randint(800, 1500),
            "grip_strength_avg": round(random.uniform(15, 25), 1),
            "response_time_ms": round(random.uniform(45, 95), 1)
        })
    
    # Battery statistics
    battery_stats = {
        "average_daily_consumption": f"{random.randint(15, 25)}%",
        "longest_usage_session": f"{random.uniform(3, 6):.1f} hours",
        "charging_cycles_this_month": random.randint(25, 35),
        "battery_health": f"{random.randint(85, 98)}%"
    }
    
    # Movement patterns analysis
    movement_patterns = {
        "most_used_gesture": random.choice(["grip", "pinch", "point", "wave"]),
        "gesture_accuracy": f"{random.randint(88, 97)}%",
        "adaptation_score": f"{random.randint(85, 95)}%",
        "muscle_signal_quality": random.choice(["Excellent", "Good", "Fair"]),
        "common_usage_times": [
            {"time_range": "08:00-12:00", "percentage": random.randint(25, 35)},
            {"time_range": "12:00-18:00", "percentage": random.randint(35, 45)},
            {"time_range": "18:00-22:00", "percentage": random.randint(20, 30)}
        ]
    }
    
    # Calibration history
    calibration_history = []
    for i in range(random.randint(3, 7)):
        cal_date = datetime.now() - timedelta(days=random.randint(1, 30))
        calibration_history.append({
            "date": cal_date.strftime("%Y-%m-%d %H:%M"),
            "type": random.choice(["automatic", "manual", "scheduled"]),
            "improvement": f"{random.uniform(2, 8):.1f}%",
            "duration_minutes": random.randint(5, 15)
        })
    
    # Sort calibration history by date
    calibration_history.sort(key=lambda x: x["date"], reverse=True)
    
    return UsageReport(
        user_id=user_info["sub"],
        username=user_info["username"],
        report_period=f"{(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}",
        generated_at=datetime.now().isoformat(),
        prosthetic_id=prosthetic_id,
        total_usage_hours=sum(day["usage_hours"] for day in daily_usage),
        daily_usage=daily_usage,
        battery_stats=battery_stats,
        movement_patterns=movement_patterns,
        calibration_history=calibration_history
    )

def get_report_summary(user_info: dict) -> Dict[str, Any]:
    """Получить краткую сводку отчета"""
    report = generate_mock_report(user_info)
    
    return {
        "username": report.username,
        "prosthetic_id": report.prosthetic_id,
        "report_period": report.report_period,
        "total_usage_hours": report.total_usage_hours,
        "avg_daily_usage": round(report.total_usage_hours / 30, 1),
        "battery_health": report.battery_stats["battery_health"],
        "movement_accuracy": report.movement_patterns["gesture_accuracy"],
        "last_calibration": report.calibration_history[0]["date"] if report.calibration_history else "N/A"
    }