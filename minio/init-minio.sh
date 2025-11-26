#!/bin/bash

# Скрипт инициализации MinIO с автоматической настройкой OIDC и политик

echo "Запуск MinIO сервера..."

# Запускаем MinIO в фоне (используем статический ключ)
minio server --console-address ":9001" /data &
MINIO_PID=$!

# Ждём запуска MinIO
echo "Ожидание запуска MinIO..."
sleep 30

# Ждём полной инициализации MinIO
echo "Ожидание полной инициализации MinIO..."
for i in {1..30}; do
  if mc admin info local > /dev/null 2>&1; then
    echo "✓ MinIO полностью инициализирован (попытка $i)"
    break
  fi
  echo "Ожидание инициализации MinIO... (попытка $i/30)"
  sleep 2
done

# Настраиваем mc (MinIO Client)
echo "Настройка MinIO Client..."
mc alias set local http://localhost:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}

# Создаём бакет reports если его нет
echo "Создание бакета reports..."
mc mb local/reports --ignore-existing

# Создаём политику для prosthetic_users (доступ только к своим файлам)
echo "Создание политики prosthetic-user-policy..."
cat > /tmp/prosthetic-user-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::reports/default/${jwt:sub}/*",
        "arn:aws:s3:::reports/debezium/${jwt:sub}/*"
      ]
    }
  ]
}
EOF

mc admin policy create local prosthetic-user-policy /tmp/prosthetic-user-policy.json

# Создаём политику для administrators (доступ ко всем файлам)
echo "Создание политики admin-policy..."
cat > /tmp/admin-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::reports",
        "arn:aws:s3:::reports/*"
      ]
    }
  ]
}
EOF

mc admin policy create local admin-policy /tmp/admin-policy.json

# Настраиваем OIDC конфигурацию
echo "Настройка OIDC конфигурации..."
mc admin config set local identity_openid config_url="http://keycloak:8080/realms/reports-realm/.well-known/openid_configuration"
mc admin config set local identity_openid client_id="reports-frontend"
mc admin config set local identity_openid claim_name="policy"
mc admin config set local identity_openid scopes="openid,profile,email"

# Перезапускаем MinIO для применения OIDC настроек
echo "Перезапуск MinIO для применения OIDC настроек..."
mc admin service restart local

echo "MinIO инициализация завершена"

# Ждём завершения процесса MinIO
wait $MINIO_PID
