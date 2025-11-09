#!/usr/bin/env python3
"""
Запуск веб-панели администратора
"""

import os
import sys

# Добавляем путь к модулям бота
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

if __name__ == '__main__':
    # Настройки для разработки
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )