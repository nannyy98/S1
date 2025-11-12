"""
Клавиатуры для телеграм-бота
"""

def create_main_keyboard(language='ru'):
    """Главная клавиатура"""
    if language == 'uz':
        return {
            'keyboard': [
                ['🛍 Katalog', '🛒 Savat'],
                ['📋 Mening buyurtmalarim', '👤 Profil'],
                ['🔍 Qidiruv', 'ℹ️ Yordam'],
                ['📞 Biz bilan bog\'lanish'],
                ['🧑‍💼 Sotuvchi bo\'lish']
            ],
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
    else:
        return {
            'keyboard': [
                ['🛍 Каталог', '🛒 Корзина'],
                ['📋 Мои заказы', '👤 Профиль'],
                ['🔍 Поиск', 'ℹ️ Помощь'],
                ['📞 Связаться с нами'],
                ['🧑‍💼 Стать продавцом']
            ],
            'resize_keyboard': True,
            'one_time_keyboard': False
        }

def create_categories_keyboard(categories):
    """Клавиатура с категориями"""
    keyboard = []
    
    for i in range(0, len(categories), 2):
        row = [f"{categories[i][3]} {categories[i][1]}"]
        if i + 1 < len(categories):
            row.append(f"{categories[i + 1][3]} {categories[i + 1][1]}")
        keyboard.append(row)
    
    keyboard.append(['🔙 Главная'])
    
    return {
        'keyboard': keyboard,
        'resize_keyboard': True,
        'one_time_keyboard': False
    }

def create_subcategories_keyboard(subcategories):
    """Клавиатура с подкатегориями/брендами"""
    keyboard = []
    
    for i in range(0, len(subcategories), 2):
        row = [f"{subcategories[i][2]} {subcategories[i][1]}"]
        if i + 1 < len(subcategories):
            row.append(f"{subcategories[i + 1][2]} {subcategories[i + 1][1]}")
        keyboard.append(row)
    
    keyboard.append(['🔙 К категориям', '🏠 Главная'])
    
    return {
        'keyboard': keyboard,
        'resize_keyboard': True,
        'one_time_keyboard': False
    }
def create_products_keyboard(products, show_back=True):
    """Клавиатура с товарами"""
    keyboard = []
    
    for product in products:
        keyboard.append([f"🛍 {product[1]} - ${product[3]:.2f}"])
    
    if show_back:
        keyboard.append(['🔙 К категориям', '🏠 Главная'])
    else:
        keyboard.append(['🏠 Главная'])
    
    return {
        'keyboard': keyboard,
        'resize_keyboard': True,
        'one_time_keyboard': False
    }

def format_price(price):
    """Форматирование цены для клавиатур"""
    return f"${price:.2f}"

def create_product_inline_keyboard(product_id):
    """Inline клавиатура для товара"""
    return {
        'inline_keyboard': [
            [
                {'text': '🛒 Добавить в корзину', 'callback_data': f'add_to_cart_{product_id}'},
                {'text': '❤️ В избранное', 'callback_data': f'add_to_favorites_{product_id}'}
            ],
            [
                {'text': '📊 Отзывы', 'callback_data': f'reviews_{product_id}'},
                {'text': '⭐ Оценить', 'callback_data': f'rate_product_{product_id}'}
            ]
        ]
    }

def create_cart_keyboard(has_items=False):
    """Клавиатура для корзины"""
    keyboard = []
    
    if has_items:
        keyboard.extend([
            ['📦 Оформить заказ'],
            ['🗑 Очистить корзину', '➕ Добавить товары']
        ])
    else:
        keyboard.append(['🛍 Перейти в каталог'])
    
    keyboard.append(['🏠 Главная'])
    
    return {
        'keyboard': keyboard,
        'resize_keyboard': True,
        'one_time_keyboard': False
    }

def create_registration_keyboard(step, suggested_value=None):
    """Клавиатура для регистрации"""
    keyboard = []
    
    if step == 'name' and suggested_value:
        keyboard.append([suggested_value])
    elif step == 'phone':
        keyboard.append([{'text': '📱 Поделиться номером', 'request_contact': True}])
        keyboard.append(['⏭ Пропустить'])
    elif step == 'email':
        keyboard.append(['⏭ Пропустить'])
    elif step == 'language':
        keyboard.append(['🇷🇺 Русский', '🇺🇿 O\'zbekcha'])
    
    if step != 'language':  # Не показываем отмену на последнем шаге
        keyboard.append(['❌ Отмена'])
    
    return {
        'keyboard': keyboard,
        'resize_keyboard': True,
        'one_time_keyboard': True
    }

def create_order_keyboard():
    """Клавиатура для оформления заказа"""
    return {
        'keyboard': [
            ['💳 Онлайн оплата', '💵 Наличными при получении'],
            ['❌ Отмена заказа']
        ],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }

def create_admin_keyboard():
    """Клавиатура для администратора"""
    return {
        'keyboard': [
            ['📊 Статистика', '📦 Заказы'],
            ['🛠 Товары', '👥 Пользователи'],
            ['📈 Аналитика', '🛡 Безопасность'],
            ['💰 Финансы', '📦 Склад'],
            ['🤖 AI', '🎯 Автоматизация'],
            ['👥 CRM', '📢 Рассылка'],
            ['🔙 Пользовательский режим']
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }

def create_back_keyboard():
    """Простая клавиатура "Назад"""
    return {
        'keyboard': [
            ['🔙 Назад', '🏠 Главная']
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }

def create_confirmation_keyboard():
    """Клавиатура подтверждения"""
    return {
        'keyboard': [
            ['✅ Да', '❌ Нет']
        ],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }

def create_search_filters_keyboard():
    """Клавиатура для фильтров поиска"""
    return {
        'inline_keyboard': [
            [
                {'text': '💰 По цене ↑', 'callback_data': 'sort_price_low'},
                {'text': '💰 По цене ↓', 'callback_data': 'sort_price_high'}
            ],
            [
                {'text': '🔥 Популярные', 'callback_data': 'sort_popular'},
                {'text': '🆕 Новинки', 'callback_data': 'sort_newest'}
            ],
            [
                {'text': '📊 Продаваемые', 'callback_data': 'sort_sales'},
                {'text': '🔍 Сбросить фильтры', 'callback_data': 'reset_filters'}
            ]
        ]
    }

def create_price_filter_keyboard():
    """Клавиатура для фильтра по цене"""
    return {
        'inline_keyboard': [
            [
                {'text': '💵 До $50', 'callback_data': 'price_0_50'},
                {'text': '💰 $50-100', 'callback_data': 'price_50_100'}
            ],
            [
                {'text': '💎 $100-500', 'callback_data': 'price_100_500'},
                {'text': '👑 $500+', 'callback_data': 'price_500_plus'}
            ],
            [
                {'text': '🔙 Назад', 'callback_data': 'back_to_search'}
            ]
        ]
    }

def create_rating_keyboard(product_id):
    """Клавиатура для оценки товара"""
    return {
        'inline_keyboard': [
            [
                {'text': '⭐', 'callback_data': f'rate_{product_id}_1'},
                {'text': '⭐⭐', 'callback_data': f'rate_{product_id}_2'},
                {'text': '⭐⭐⭐', 'callback_data': f'rate_{product_id}_3'}
            ],
            [
                {'text': '⭐⭐⭐⭐', 'callback_data': f'rate_{product_id}_4'},
                {'text': '⭐⭐⭐⭐⭐', 'callback_data': f'rate_{product_id}_5'}
            ],
            [
                {'text': '❌ Отмена', 'callback_data': 'cancel_rating'}
            ]
        ]
    }

def create_order_details_keyboard(order_id):
    """Клавиатура для детального просмотра заказа"""
    return {
        'inline_keyboard': [
            [
                {'text': '📋 Детали заказа', 'callback_data': f'order_details_{order_id}'},
                {'text': '📞 Связаться', 'callback_data': f'contact_about_{order_id}'}
            ],
            [
                {'text': '❌ Отменить заказ', 'callback_data': f'cancel_order_{order_id}'}
            ]
        ]
    }

def create_language_keyboard():
    """Клавиатура выбора языка"""
    return {
        'keyboard': [
            ['🇷🇺 Русский', '🇺🇿 O\'zbekcha'],
            ['❌ Отмена']
        ],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }

def create_payment_methods_keyboard(language='ru'):
    """Клавиатура способов оплаты (только наличные и оплата картой)"""
    if language == 'uz':
        return {
            'keyboard': [
                ['💵 Qabul qilishda naqd', '💳 Kartadan toʻlov'],
                ['❌ Bekor qilish']
            ],
            'resize_keyboard': True
        }
    else:
        return {
            'keyboard': [
                ['💵 Наличными при получении', '💳 Оплата картой'],
                ['❌ Отмена']
            ],
            'resize_keyboard': True
        }
def create_cart_item_keyboard(cart_item_id, current_quantity):
    """Клавиатура для управления товаром в корзине"""
    return {
        'inline_keyboard': [
            [
                {'text': '➖', 'callback_data': f'cart_decrease_{cart_item_id}'},
                {'text': f'📦 {current_quantity} шт.', 'callback_data': f'cart_quantity_{cart_item_id}'},
                {'text': '➕', 'callback_data': f'cart_increase_{cart_item_id}'}
            ],
            [
                {'text': '🗑 Удалить', 'callback_data': f'cart_remove_{cart_item_id}'}
            ]
        ]
    }

def create_admin_products_keyboard(products):
    """Клавиатура для управления товарами админом"""
    keyboard = []
    
    for product in products:
        status_emoji = "✅" if product[7] else "❌"
        keyboard.append([
            {'text': f'{status_emoji} {product[1]}', 'callback_data': f'admin_view_product_{product[0]}'}
        ])
    
    keyboard.append([
        {'text': '➕ Добавить товар', 'callback_data': 'admin_add_product'},
        {'text': '🔙 Назад', 'callback_data': 'admin_back_main'}
    ])
    
    return {'inline_keyboard': keyboard}

def create_notifications_keyboard():
    """Клавиатура для управления уведомлениями"""
    return {
        'inline_keyboard': [
            [
                {'text': '📢 Рассылка всем', 'callback_data': 'broadcast_all'},
                {'text': '🎯 Активным клиентам', 'callback_data': 'broadcast_active'}
            ],
            [
                {'text': '😴 Неактивным', 'callback_data': 'broadcast_inactive'},
                {'text': '🆕 Новым пользователям', 'callback_data': 'broadcast_new'}
            ],
            [
                {'text': '📊 Статистика рассылок', 'callback_data': 'broadcast_stats'},
                {'text': '🔙 Назад', 'callback_data': 'admin_back_main'}
            ]
        ]
    }

def create_analytics_keyboard():
    """Клавиатура для аналитики"""
    return {
        'inline_keyboard': [
            [
                {'text': '📊 Продажи за период', 'callback_data': 'analytics_sales'},
                {'text': '👥 Поведение клиентов', 'callback_data': 'analytics_behavior'}
            ],
            [
                {'text': '📈 ABC-анализ', 'callback_data': 'analytics_abc'},
                {'text': '🎯 Воронка конверсии', 'callback_data': 'analytics_funnel'}
            ],
            [
                {'text': '💰 Прогноз выручки', 'callback_data': 'analytics_forecast'},
                {'text': '📦 Эффективность товаров', 'callback_data': 'analytics_products'}
            ],
            [
                {'text': '🔙 Назад', 'callback_data': 'admin_back_main'}
            ]
        ]
    }

def create_period_selection_keyboard():
    """Клавиатура выбора периода для отчетов"""
    return {
        'inline_keyboard': [
            [
                {'text': '📅 Сегодня', 'callback_data': 'period_today'},
                {'text': '📅 Вчера', 'callback_data': 'period_yesterday'}
            ],
            [
                {'text': '📅 Неделя', 'callback_data': 'period_week'},
                {'text': '📅 Месяц', 'callback_data': 'period_month'}
            ],
            [
                {'text': '📅 Квартал', 'callback_data': 'period_quarter'},
                {'text': '📅 Год', 'callback_data': 'period_year'}
            ],
            [
                {'text': '🔙 Назад', 'callback_data': 'admin_analytics'}
            ]
        ]
    }


def create_address_location_keyboard():
    """Клавиатура для ввода адреса или отправки локации"""
    return {
        'keyboard': [
            [ {'text': '📍 Отправить локацию', 'request_location': True} ],
            ['✍️ Ввести адрес'],
            ['🔙 Назад', '🏠 Главная']
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }

def create_product_inline_keyboard_with_qty(product_id, qty=1, category_id=None, subcategory_id=None):
    """Inline клавиатура товара с выбором количества"""
    if qty < 1: qty = 1
    if qty > 20: qty = 20
    return {
        'inline_keyboard': [
            [
                {'text': '➖', 'callback_data': f'qty_dec_{product_id}_{qty}'},
                {'text': f'{qty} шт.', 'callback_data': 'noop'},
                {'text': '➕', 'callback_data': f'qty_inc_{product_id}_{qty}'}
            ],
            [
                {'text': '🛒 Добавить', 'callback_data': f'add_to_cart_{product_id}_{qty}'},
                {'text': '🔙 Назад', 'callback_data': ('back_to_subcategory_' + str(subcategory_id)) if subcategory_id else (('back_to_category_' + str(category_id)) if category_id else 'back_to_categories')}
            ]
        ]
    }


def create_contact_inline_keyboard(phone=None, tg_username=None, chat_url=None, extra=None):
    """Inline-клавиатура с кнопками для связи (чат/звонок)"""
    rows = []
    btn_row = []
    url = None
    if chat_url:
        url = chat_url.strip()
    elif tg_username:
        uname = tg_username.strip()
        if uname.startswith('@'):
            uname = uname[1:]
        url = f"https://t.me/{uname}"
    if url:
        btn_row.append({'text': '💬 Написать в чате', 'url': url})
    if phone:
        tel = str(phone).replace(' ', '')
        btn_row.append({'text': f'📞 Позвонить {phone}', 'url': f'tel:{tel}'})
    if btn_row:
        rows.append(btn_row)
    if extra and isinstance(extra, list) and extra:
        rows.append(extra)
    return {'inline_keyboard': rows} if rows else None

def create_contact_request_keyboard(lang=None):
    """Клавиатура с кнопкой запроса контакта (номер телефона).
    lang: строка языка ('ru'/'uz'), сейчас влияет только на подписи при необходимости.
    """
    # Подписи можно локализовать в будущем при необходимости
    share_text = '📱 Поделиться номером'
    cancel_text = '❌ Отмена'
    keyboard = [
        [ {'text': share_text, 'request_contact': True} ],
        [ cancel_text ]
    ]
    return {
        'keyboard': keyboard,
        'resize_keyboard': True,
        'one_time_keyboard': True
    }
