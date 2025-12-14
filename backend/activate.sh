#!/bin/bash
echo "Активация виртуального окружения..."

# Проверяем, существует ли venv
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python -m venv venv
fi

# Активируем
source venv/Scripts/activate

# Проверяем
if [ "$VIRTUAL_ENV" != "" ]; then
    echo "✅ Виртуальное окружение активировано!"
    echo "Python: $(which python)"
else
    echo "❌ Не удалось активировать виртуальное окружение"
    echo "Попробуйте вручную: source venv/Scripts/activate"
fi