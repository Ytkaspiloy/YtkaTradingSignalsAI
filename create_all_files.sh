#!/bin/bash

echo "Создание структуры проекта..."

# Создание папок
mkdir -p trading-bot-platform/{backend/app/{bot,api,models},backend/tests,frontend/{public,src/{components,stores,utils}},infrastructure/{nginx,certbot},scripts,docs,.github/workflows}

# Переход в папку проекта
cd trading-bot-platform

# Копирование всех файлов (создайте их сначала простыми версиями)

# Бэкенд файлы
echo "Создание бэкенд файлов..."

# requirements.txt
echo "Flask==2.3.3
Flask-CORS==4.0.0
Flask-SQLAlchemy==3.0.5
MetaTrader5==5.0.41
pandas==2.1.0
numpy==1.24.3
pyTelegramBotAPI==4.14.0" > backend/requirements.txt

# config.py
echo "import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///bot.db')" > backend/config.py

# Dockerfile
echo "FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD [\"python\", \"app/main.py\"]" > backend/Dockerfile

# .env.example
echo "MT5_LOGIN=12345678
MT5_PASSWORD=your_password
TELEGRAM_BOT_TOKEN=your_token
DATABASE_URL=sqlite:///bot.db" > backend/.env.example

# Фронтенд файлы
echo "Создание фронтенд файлов..."

# package.json
echo '{
  "name": "trading-bot-frontend",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "vue": "^3.3.4",
    "axios": "^1.5.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.4.0",
    "vite": "^4.4.9"
  }
}' > frontend/package.json

# vite.config.js
echo "import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000
  }
})" > frontend/vite.config.js

# index.html
echo '<!DOCTYPE html>
<html>
<head>
    <title>Trading Bot</title>
</head>
<body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
</body>
</html>' > frontend/public/index.html

# Главные файлы
echo "Создание основных файлов..."

# docker-compose.yml
echo "version: '3.8'
services:
  api:
    build: ./backend
    ports:
      - \"5000:5000\"
  frontend:
    build: ./frontend
    ports:
      - \"3000:3000\"" > docker-compose.yml

# README.md
echo "# Trading Bot Platform
## Быстрый старт:
1. Запустите: docker-compose up --build
2. Откройте: http://localhost:3000" > README.md

# .gitignore
echo ".env
__pycache__
node_modules
*.db
.DS_Store" > .gitignore

echo "✅ Структура проекта создана!"
echo "Следующие шаги:"
echo "1. cd trading-bot-platform"
echo "2. cp backend/.env.example .env"
echo "3. Отредактируйте .env файл"
echo "4. docker-compose up --build"
