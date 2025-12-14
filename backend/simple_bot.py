# -*- coding: utf-8 -*-
"""
ПРОСТОЙ ТОРГОВЫЙ БОТ - ТЕСТОВАЯ ВЕРСИЯ
"""
import os
import sys
import time
from datetime import datetime

print("=" * 60)
print("SIMPLE TRADING BOT - ТЕСТ ЗАПУСКА")
print("=" * 60)

# 1. Сначала проверяем Python и базовые модули
print("\nPython работает!")
print(f"Версия Python: {sys.version}")
print(f"Текущая папка: {os.getcwd()}")

# 2. Пробуем загрузить .env файл
print("\nПоиск файла .env...")
env_path = '../.env'

if os.path.exists(env_path):
    print(f"Файл .env найден: {env_path}")
else:
    print(f"Файл .env НЕ НАЙДЕН!")
    print(f"Создайте его командой: cd .. && echo 'MT5_LOGIN=ваш_логин' > .env")

# 3. Пробуем импортировать MetaTrader5
print("\nПроверка установки MetaTrader5...")
try:
    import MetaTrader5 as mt5
    print("MetaTrader5 установлен")
    
    if mt5.initialize():
        print("MT5 подключен")
        mt5.shutdown()
    else:
        print(f"Ошибка MT5: {mt5.last_error()}")
        
except ImportError:
    print("MetaTrader5 НЕ установлен")
    print("Установите: pip install MetaTrader5")

print("\nГотово!")
input("Нажмите Enter для выхода...")
