"""
Конфигурация для Telegram бота интернет-магазина
"""
import os

# === Telegram credentials (hardcoded with optional env override) ===
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8292684103:AAH0TKL-lCOaKVeppjtAdmsx0gdeMrGtjdQ')
POST_CHANNEL_ID = os.getenv('POST_CHANNEL_ID', '-1002566537425')


# Конфигурация окружения
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG = ENVIRONMENT == 'development'

# Настройки базы данных
DATABASE_CONFIG = {
    'path': os.getenv('DATABASE_PATH', 'shop_bot.db'),
    'backup_interval': 3600,  # Резервное копирование каждый час
    'max_connections': 10
}

# Настройки безопасности
SECURITY_CONFIG = {
    'rate_limit_per_minute': int(os.getenv('RATE_LIMIT', '20')),
    'max_failed_attempts': 5,
    'block_duration_hours': 24,
    'jwt_secret': os.getenv('JWT_SECRET', 'your-secret-key-change-in-production'),
    'encryption_key': os.getenv('ENCRYPTION_KEY', 'your-encryption-key')
}

# Настройки логирования
LOGGING_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'file': os.getenv('LOG_FILE', 'bot.log'),
    'max_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5
}

# Настройки Redis (для кэширования)
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', '6379')),
    'db': int(os.getenv('REDIS_DB', '0')),
    'password': os.getenv('REDIS_PASSWORD'),
    'enabled': os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
}

# Настройки мониторинга
MONITORING_CONFIG = {
    'health_check_interval': 60,
    'metrics_enabled': True,
    'sentry_dsn': os.getenv('SENTRY_DSN'),
    'prometheus_port': int(os.getenv('PROMETHEUS_PORT', '8000'))
}

# Настройки бота
BOT_CONFIG = {
    'name': os.getenv('BOT_NAME', 'Shop Bot'),
    'version': '1.0',
    'description': 'Телеграм-бот для интернет-магазина',
    'bot_username': 'Safar_call_bot',
    'currency': os.getenv('CURRENCY', 'USD'),
    'currency_symbol': os.getenv('CURRENCY_SYMBOL', '$'),
    'webhook_url': os.getenv('WEBHOOK_URL'),
    'webhook_secret': os.getenv('WEBHOOK_SECRET'),
    'max_message_length': 4096,
    'request_timeout': 30,
    'admin_telegram_id': os.getenv('ADMIN_TELEGRAM_ID', '5720497431'),
    'admin_name': 'Safar',
    'post_channel_id': '-1002566537425'
}

# Контактная информация
CONTACT_INFO = {
    'support_phone': os.getenv('SUPPORT_PHONE', '+998901234567'),
    'support_telegram': os.getenv('SUPPORT_TELEGRAM', '@Safar_call_bot'),
    'call_center_phone': os.getenv('CALL_CENTER_PHONE', '+998901234567'),
    'working_hours': os.getenv('WORKING_HOURS', '9:00 - 18:00 (Пн-Пт)')
}

# Сообщения бота
MESSAGES = {
    'welcome_new': """
🛍 <b>Добро пожаловать в наш интернет-магазин!</b>

Здесь вы можете:
• 📱 Просматривать каталог товаров
• 🛒 Добавлять товары в корзину  
• 📦 Оформлять заказы
• 📋 Отслеживать статус доставки

Для начала работы пройдите быструю регистрацию.
    """,
    
    'welcome_back': """
👋 <b>С возвращением!</b>

Рады видеть вас снова в нашем магазине.
Выберите действие из меню ниже:
    """,
    
    'help': """
ℹ️ <b>Справка по использованию бота:</b>

🛍 <b>Каталог</b> - просмотр товаров по категориям
🛒 <b>Корзина</b> - ваши выбранные товары
📋 <b>Мои заказы</b> - история ваших покупок
👤 <b>Профиль</b> - управление вашими данными

<b>Как сделать заказ:</b>
1️⃣ Выберите товары в каталоге
2️⃣ Добавьте их в корзину
3️⃣ Перейдите в корзину и оформите заказ
4️⃣ Укажите адрес и способ оплаты

❓ По вопросам обращайтесь к администратору.
    """,
    
    'registration_complete': """
✅ <b>Регистрация завершена!</b>

Добро пожаловать в наш магазин! 🎉

Теперь вы можете:
• Просматривать каталог товаров
• Добавлять товары в корзину
• Оформлять заказы

Приятных покупок! 🛍
    """,
    
    'empty_cart': """
🛒 <b>Ваша корзина пуста</b>

Перейдите в каталог, чтобы добавить товары!
    """,
    
    'order_success': """
✅ <b>Заказ успешно оформлен!</b>

📞 Мы свяжемся с вами в ближайшее время для подтверждения.

Спасибо за покупку! 🎉
    """
}

# Статусы заказов
ORDER_STATUSES = {
    'pending': '⏳ В обработке',
    'confirmed': '✅ Подтвержден',
    'shipped': '🚚 Отправлен',
    'delivered': '📦 Доставлен',
    'cancelled': '❌ Отменен'
}

# Способы оплаты
PAYMENT_METHODS = {
    'online': '💳 Онлайн оплата',
    'cash': '💵 Наличными при получении'
}

# Эмодзи для категорий
CATEGORY_EMOJIS = {
    'Электроника': '📱',
    'Одежда': '👕',
    'Дом и сад': '🏠',
    'Спорт': '⚽',
    'Книги': '📚',
    'Красота': '💄'
}

# Настройки пагинации
PAGINATION = {
    'products_per_page': 5,
    'orders_per_page': 10
}
# Marketing automation toggle
ENABLE_MARKETING = False
