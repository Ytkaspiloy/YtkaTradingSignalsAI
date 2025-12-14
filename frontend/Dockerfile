# Этап 1: Сборка приложения
FROM node:18-alpine AS builder

# Установка рабочей директории
WORKDIR /app

# Копирование package.json
COPY package*.json ./

# Установка зависимостей
RUN npm ci --silent

# Копирование исходного кода
COPY . .

# Сборка приложения
RUN npm run build

# Этап 2: Production сервер
FROM nginx:alpine

# Копирование собранного приложения
COPY --from=builder /app/dist /usr/share/nginx/html

# Копирование конфигурации Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Открытие порта 80
EXPOSE 80

# Запуск Nginx
CMD ["nginx", "-g", "daemon off;"]