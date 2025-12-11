from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import sys
from middleware_auth import AuthMiddleware
from storage_clickhouse import ClickHouseClient
from storage_s3 import S3Client
from services_report import ReportService
from handlers_report import ReportHandler
from config import load_config

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Загрузка конфигурации
config = load_config()
logger.info(f"Config loaded: ClickHouse={config.clickhouse.host}:{config.clickhouse.port}")

# Инициализация клиентов
try:
    logger.info("Initializing ClickHouse client...")
    clickhouse_client = ClickHouseClient(
        host=config.clickhouse.host,
        port=config.clickhouse.port,
        database=config.clickhouse.database,
        username=config.clickhouse.username,
        password=config.clickhouse.password
    )
    logger.info("ClickHouse client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize ClickHouse client: {e}")
    raise

try:
    logger.info("Initializing S3 client...")
    s3_client = S3Client(
        endpoint=config.s3.endpoint,
        access_key_id=config.s3.access_key_id,
        secret_access_key=config.s3.secret_access_key,
        bucket_name=config.s3.bucket_name,
        region=config.s3.region,
        use_ssl=config.s3.use_ssl
    )
    logger.info("S3 client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {e}")
    raise

# Инициализация сервисов
report_service = ReportService(clickhouse_client, s3_client, config)
report_handler = ReportHandler(report_service)

# Инициализация middleware
auth_middleware = AuthMiddleware()

# Middleware для логирования всех запросов
@app.before_request
def log_request_info():
    logger.debug(f"Request: {request.method} {request.path}")
    logger.debug(f"Headers: {dict(request.headers)}")
    if request.method in ['POST', 'PUT']:
        logger.debug(f"Body: {request.get_data()}")

@app.after_request
def log_response_info(response):
    logger.debug(f"Response: {response.status_code}")
    return response

# Health check с проверкой подключений
@app.route('/health', methods=['GET'])
def health():
    try:
        # Проверяем ClickHouse
        clickhouse_test = clickhouse_client.client.execute('SELECT 1')
        clickhouse_ok = bool(clickhouse_test)
        
        return jsonify({
            "status": "ok",
            "clickhouse": "connected" if clickhouse_ok else "disconnected",
            "timestamp": "2025-12-10T18:04:00Z"
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# Debug endpoint для проверки ClickHouse
@app.route('/api/v1/debug/clickhouse', methods=['GET'])
def debug_clickhouse():
    try:
        # Простой запрос
        test_result = clickhouse_client.client.execute('SELECT 1 as test')
        
        # Проверяем таблицы
        tables = clickhouse_client.client.execute('SHOW TABLES')
        
        # Проверяем конкретную таблицу
        try:
            dim_customers = clickhouse_client.client.execute('SELECT COUNT(*) FROM dim_customers')
        except Exception as e:
            dim_customers = f"Error: {e}"
            
        try:
            user_reports = clickhouse_client.client.execute('SELECT COUNT(*) FROM bionicpro.user_reports_realtime')
        except Exception as e:
            user_reports = f"Error: {e}"
        
        return jsonify({
            "status": "connected",
            "test_result": test_result[0][0] if test_result else None,
            "tables": [table[0] for table in tables] if tables else [],
            "dim_customers_count": dim_customers,
            "user_reports_count": user_reports,
            "config": {
                "host": config.clickhouse.host,
                "port": config.clickhouse.port,
                "database": config.clickhouse.database,
                "username": config.clickhouse.username
            }
        }), 200
    except Exception as e:
        import traceback
        logger.error(f"Debug endpoint error: {e}\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

# API routes
@app.route('/api/v1/reports', methods=['GET'])
@auth_middleware.require_auth
def get_reports():
    logger.info("GET /api/v1/reports called")
    return report_handler.get_reports()

@app.route('/api/v1/reports/generate', methods=['POST'])
@auth_middleware.require_auth
def generate_reports():
    logger.info("POST /api/v1/reports/generate called")
    return report_handler.generate_reports()

# CORS headers
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-User-ID')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

@app.route('/api/v1/reports', methods=['OPTIONS'])
@app.route('/api/v1/reports/generate', methods=['OPTIONS'])
def options_handler():
    return '', 204

if __name__ == '__main__':
    logger.info("Starting reports service on port 5003")
    app.run(host='0.0.0.0', port=5003, debug=True)