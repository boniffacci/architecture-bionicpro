from clickhouse_driver import Client
from datetime import datetime
from models_report import UserReport
import traceback

class ClickHouseClient:
    def __init__(self, host, port, database, username, password):
        try:
            print(f"Connecting to ClickHouse: {host}:{port}, db={database}, user={username}")
            self.client = Client(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                settings={'connect_timeout': 10, 'send_receive_timeout': 30}
            )
            # Проверяем подключение
            version = self.client.execute('SELECT version()')
            print(f"ClickHouse connected! Version: {version[0][0]}")
        except Exception as e:
            print(f"ClickHouse connection error: {str(e)}")
            print(traceback.format_exc())
            raise
    
    def get_user_report(self, user_id):
        try:
            print(f"Getting report for user_id: {user_id}")
            
            # 1. Получаем данные пользователя
            # ВАЖНО: Без параметров, вставляем значение напрямую
            user_query = f"SELECT name, email FROM dim_customers WHERE id = {user_id}"
            print(f"Executing user query: {user_query}")
            
            user_result = self.client.execute(user_query)
            print(f"User query result: {user_result}")
            
            username, email = "", ""
            if user_result:
                username, email = user_result[0]
                print(f"Found user: name={username}, email={email}")
            else:
                print(f"User not found for id: {user_id}")
            
            # 2. Получаем отчет
            # ВАЖНО: Без параметров, вставляем значение напрямую
            report_query = f"""
                SELECT 
                    user_id,
                    session_count as total_sessions,
                    total_signals,
                    avg_duration * session_count as total_usage_time,
                    avg_duration as average_session_time,
                    muscle_groups,
                    avg_accuracy,
                    report_date as last_activity
                FROM bionicpro.user_reports_realtime 
                WHERE user_id = {user_id}
                ORDER BY report_date DESC
                LIMIT 1
            """
            
            print(f"Executing report query")
            result = self.client.execute(report_query)
            print(f"Report query result: {result}")
            
            if not result:
                print(f"No report data found for user_id: {user_id}")
                return UserReport(
                    user_id=user_id,
                    username=username,
                    email=email,
                    total_sessions=0,
                    total_signals=0,
                    total_usage_time=0.0,
                    average_session_time=0.0,
                    muscle_groups="",
                    average_accuracy=0.0,
                    last_activity=datetime.now(),
                    report_generated_at=datetime.now(),
                    has_data=False,
                    message="Данные отчёта пока отсутствуют"
                )
            
            row = result[0]
            print(f"Report data found: {row}")
            
            return UserReport(
                user_id=row[0],
                username=username,
                email=email,
                total_sessions=row[1],
                total_signals=row[2],
                total_usage_time=float(row[3]),
                average_session_time=float(row[4]),
                muscle_groups=row[5],
                average_accuracy=float(row[6]),
                last_activity=row[7],
                report_generated_at=datetime.now(),
                has_data=True
            )
            
        except Exception as e:
            print(f"Error in get_user_report: {str(e)}")
            print(traceback.format_exc())
            raise