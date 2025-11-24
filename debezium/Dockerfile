# Dockerfile для кастомного образа Debezium Connect
# Наследуемся от официального образа Debezium Connect версии 2.7.3
FROM debezium/connect:2.7.3.Final

# Переключаемся на root для установки пакетов и копирования файлов
USER root

# Устанавливаем jq для обработки JSON в скрипте (может пригодиться для отладки)
RUN microdnf install -y jq && microdnf clean all

# Копируем скрипт инициализации коннекторов (для совместимости, но не используется автоматически)
COPY init_debezium_connectors.sh /usr/local/bin/init_debezium_connectors.sh

# Делаем скрипт исполняемым
RUN chmod +x /usr/local/bin/init_debezium_connectors.sh

# ВАЖНО: Коннекторы теперь создаются через reports_api при старте,
# а не автоматически при старте debezium.
# Это позволяет создавать коннекторы ПОСЛЕ того, как данные будут загружены в PostgreSQL.

# Используем стандартный entrypoint Debezium Connect (без автоматической инициализации коннекторов)
# CMD определена в базовом образе debezium/connect
