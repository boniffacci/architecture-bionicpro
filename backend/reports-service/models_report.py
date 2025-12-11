# models_report.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import dateutil.parser
import re

def safe_iso_format(dt):
    """Безопасное преобразование datetime в ISO строку БЕЗ Z"""
    if dt is None:
        return None
    
    if isinstance(dt, str):
        # Если уже строка, возвращаем как есть
        return dt
    
    # Если это datetime объект
    if hasattr(dt, 'isoformat'):
        iso_str = dt.isoformat()
        # Убираем Z если есть - оставляем просто ISO без часового пояса
        if iso_str.endswith('Z'):
            iso_str = iso_str[:-1]  # Убираем Z
        
        # Убираем лишние микросекунды (оставляем максимум 6 знаков)
        # Для совместимости с fromisoformat
        if '.' in iso_str:
            parts = iso_str.split('.')
            if len(parts) == 2:
                seconds_part = parts[1]
                # Оставляем только первые 6 цифр
                cleaned_seconds = re.sub(r'(\d{6})\d*', r'\1', seconds_part)
                iso_str = f"{parts[0]}.{cleaned_seconds}"
        
        return iso_str
    
    # Иначе преобразуем в строку
    return str(dt)

def parse_datetime_safe(dt_str):
    """Безопасный парсинг datetime строки с наносекундами"""
    if not dt_str:
        return datetime.now()
    
    # Убираем Z если есть
    if dt_str.endswith('Z'):
        dt_str = dt_str[:-1]
    
    try:
        # Пробуем стандартный fromisoformat
        return datetime.fromisoformat(dt_str)
    except ValueError:
        try:
            # Пробуем dateutil.parser который более гибкий
            return dateutil.parser.isoparse(dt_str + 'Z' if not dt_str.endswith('Z') else dt_str)
        except:
            try:
                # Убираем наносекунды и пробуем снова
                # Находим и удаляем лишние цифры после точки
                if '.' in dt_str:
                    parts = dt_str.split('.')
                    if len(parts) == 2:
                        seconds_part = parts[1]
                        # Оставляем только первые 6 цифр или меньше
                        match = re.match(r'(\d{1,6})', seconds_part)
                        if match:
                            cleaned_seconds = match.group(1)
                            # Дополняем до 6 цифр если нужно для микросекунд
                            cleaned_seconds = cleaned_seconds.ljust(6, '0')
                            dt_str = f"{parts[0]}.{cleaned_seconds}"
                
                return datetime.fromisoformat(dt_str)
            except:
                # В крайнем случае возвращаем текущее время
                print(f"Warning: Could not parse datetime string: {dt_str}")
                return datetime.now()

@dataclass
class UserReport:
    user_id: int
    username: str
    email: str
    total_sessions: int
    total_signals: int
    total_usage_time: float
    average_session_time: float
    muscle_groups: str
    average_accuracy: float
    last_activity: datetime
    report_generated_at: datetime
    has_data: bool
    message: Optional[str] = None
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "total_sessions": self.total_sessions,
            "total_signals": self.total_signals,
            "total_usage_time": self.total_usage_time,
            "average_session_time": self.average_session_time,
            "muscle_groups": self.muscle_groups,
            "average_accuracy": self.average_accuracy,
            "last_activity": safe_iso_format(self.last_activity),
            "report_generated_at": safe_iso_format(self.report_generated_at),
            "has_data": self.has_data,
            "message": self.message
        }
    
    @classmethod
    def from_dict(cls, data):
        last_activity = parse_datetime_safe(data.get('last_activity'))
        report_generated_at = parse_datetime_safe(data.get('report_generated_at'))
        
        return cls(
            user_id=data.get('user_id', 0),
            username=data.get('username', ''),
            email=data.get('email', ''),
            total_sessions=data.get('total_sessions', 0),
            total_signals=data.get('total_signals', 0),
            total_usage_time=data.get('total_usage_time', 0.0),
            average_session_time=data.get('average_session_time', 0.0),
            muscle_groups=data.get('muscle_groups', ''),
            average_accuracy=data.get('average_accuracy', 0.0),
            last_activity=last_activity,
            report_generated_at=report_generated_at,
            has_data=data.get('has_data', False),
            message=data.get('message')
        )