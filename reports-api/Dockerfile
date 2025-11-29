FROM node:16-alpine

WORKDIR /app

# Копирование файлов конфигурации
COPY package.json package-lock.json* ./

# Установка зависимостей
RUN npm install

# Копирование исходного кода
COPY . .

# Компиляция TypeScript
RUN npm run build

# Команда запуска
CMD ["npm", "start"]

