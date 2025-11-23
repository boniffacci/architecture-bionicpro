#!/bin/bash

# Скрипт для запуска Vite dev server
# Запускает фронтенд на порту 5173

set -e  # Прервать выполнение при ошибке

# Цветной вывод
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Запуск Vite dev server ===${NC}"

# Проверяем, что node_modules установлены
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚠ node_modules не найдены. Устанавливаем зависимости...${NC}"
    npm install
fi

# Проверяем, что порт 5173 свободен
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${RED}✗ Порт 5173 уже занят${NC}"
    echo -e "${YELLOW}Попытка остановить процесс на порту 5173...${NC}"
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Запускаем Vite dev server
echo -e "${GREEN}✓ Запускаем Vite dev server на http://localhost:5173${NC}"
echo -e "${YELLOW}Примечание: Для доступа к приложению используйте http://localhost:3000 (через auth-proxy)${NC}"
npm run dev
