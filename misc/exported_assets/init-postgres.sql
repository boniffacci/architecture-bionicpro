# init-postgres.sql
# Инициализация PostgreSQL для BionicPRO
# Этот файл автоматически запускается при первом старте контейнера

-- Создаём БД для Airflow (если ещё не создана)
CREATE DATABASE IF NOT EXISTS airflow;

-- Создаём БД для CRM
CREATE DATABASE IF NOT EXISTS crm_db;

-- Создаём БД для Telemetry
CREATE DATABASE IF NOT EXISTS telemetry_db;

-- Выдаём права пользователю postgres на все БД
ALTER DATABASE airflow OWNER TO postgres;
ALTER DATABASE crm_db OWNER TO postgres;
ALTER DATABASE telemetry_db OWNER TO postgres;

-- Создаём расширения, которые могут понадобиться
\connect airflow
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

\connect crm_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\connect telemetry_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Возвращаемся в postgres БД
\connect postgres

-- Выводим информацию о созданных БД
SELECT datname FROM pg_database 
WHERE datname IN ('airflow', 'crm_db', 'telemetry_db') 
ORDER BY datname;
