# Dockerfile для кастомного образа Debezium Connect
# Наследуемся от официального образа Debezium Connect версии 2.7.3
FROM debezium/connect:2.7.3.Final

# Переключаемся на root для установки пакетов и копирования файлов
USER root

# Устанавливаем jq для обработки JSON в скрипте (может пригодиться для отладки)
RUN microdnf install -y jq && microdnf clean all

# Копируем скрипт инициализации коннекторов
COPY init_debezium_connectors.sh /usr/local/bin/init_debezium_connectors.sh

# Копируем wrapper-скрипт для автоматического запуска
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Делаем скрипты исполняемыми
RUN chmod +x /usr/local/bin/init_debezium_connectors.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

# Возвращаемся к пользователю kafka (из базового образа)
USER kafka

# Используем кастомный entrypoint для автоматической инициализации коннекторов
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
