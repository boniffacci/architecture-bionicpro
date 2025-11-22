# Dockerfile для кастомного образа Debezium Connect
# Наследуемся от официального образа Debezium Connect версии 2.7.3
FROM debezium/connect:2.7.3.Final

# Переключаемся на root для установки пакетов и копирования файлов
USER root

# Устанавливаем jq для обработки JSON в скрипте
RUN microdnf install -y jq && microdnf clean all

# Копируем скрипт инициализации коннекторов
COPY init_debezium_connectors.sh /usr/local/bin/init_debezium_connectors.sh

# Делаем скрипт исполняемым
RUN chmod +x /usr/local/bin/init_debezium_connectors.sh

# Создаём wrapper-скрипт, который запускает Kafka Connect и затем инициализирует коннекторы
RUN echo '#!/bin/bash' > /usr/local/bin/start-and-init.sh && \
    echo 'set -e' >> /usr/local/bin/start-and-init.sh && \
    echo '' >> /usr/local/bin/start-and-init.sh && \
    echo '# Запускаем Kafka Connect в фоне' >> /usr/local/bin/start-and-init.sh && \
    echo '/docker-entrypoint.sh start &' >> /usr/local/bin/start-and-init.sh && \
    echo 'CONNECT_PID=$!' >> /usr/local/bin/start-and-init.sh && \
    echo '' >> /usr/local/bin/start-and-init.sh && \
    echo '# Запускаем скрипт инициализации коннекторов' >> /usr/local/bin/start-and-init.sh && \
    echo '/usr/local/bin/init_debezium_connectors.sh' >> /usr/local/bin/start-and-init.sh && \
    echo '' >> /usr/local/bin/start-and-init.sh && \
    echo '# Ждём завершения процесса Kafka Connect' >> /usr/local/bin/start-and-init.sh && \
    echo 'wait $CONNECT_PID' >> /usr/local/bin/start-and-init.sh && \
    chmod +x /usr/local/bin/start-and-init.sh

# Используем wrapper-скрипт как entrypoint
CMD ["/usr/local/bin/start-and-init.sh"]
