# -*- coding: utf-8 -*-
"""
Клавиатуры для телеграм-бота (RU/UZ)
"""

# Минимальный локализатор для RU→UZ
def _t(lang: str, ru: str) -> str:
    if (lang or 'ru') != 'uz':
        return ru
    m = {
        # Главная
        '🛍 Каталог': '🛍 Katalog',
        '🛒 Корзина': '🛒 Savat',
        '📋 Мои заказы': '📋 Mening buyurtmalarim',
        '👤 Профиль': '👤 Profil',
        '🔍 Поиск': '🔍 Qidiruv',
        'ℹ️ Помощь': 'ℹ️ Yordam',
        '📞 Связаться с нами': "📞 Biz bilan bog'lanish",
        '🧑‍💼 Стать продавцом': "🧑‍💼 Sotuvchi bo'lish",
        '🔙 Назад': '🔙 Orqaga',
        '🏠 Главная': '🏠 Bosh sahifa',
        '🔙 Главная': '🔙 Bosh sahifa',
        '🔙 К категориям': '🔙 Kategoriyalarga',
        '🔙 К подкатегориям': '🔙 Subkategoriyalarga',
        '🔙 Пользовательский режим': '🔙 Foydalanuvchi rejimi',
        '🛍 Перейти в каталог': '🛍 Katalogga o‘tish',
        '➕ Добавить товары': '➕ Tovarlar qo‘shish',

        # Товар/карточки
        '🛒 Добавить в корзину': "🛒 Savatchaga qo'shish",
        '❤️ В избранное': '❤️ Sevimlilarga',
        '📊 Отзывы': '📊 Fikrlar',
        '⭐ Оценить': '⭐ Baholash',
        '🗑 Удалить': "🗑 O'chirish",
        'шт.': 'dona',
        '📦 Оформить заказ': '📦 Buyurtma berish',
        '🗑 Очистить корзину': '🗑 Savatni tozalash',

        # Регистрация/общие действия
        '📱 Поделиться номером': '📱 Raqamni ulashish',
        '⏭ Пропустить': "⏭ O'tkazib yuborish",
        '❌ Отмена': '❌ Bekor qilish',
        '❌ Отмена заказа': '❌ Buyurtmani bekor qilish',
        '✅ Да': '✅ Ha',
        '❌ Нет': "❌ Yo'q",

        # Оплата
        '💳 Онлайн оплата': '💳 Onlayn to‘lov',
        '💵 Наличными при получении': '💵 Qabul qilishda naqd',
        '💳 Оплата картой': '💳 Kartadan to‘lov',

        # Поиск/фильтры/сортировка
        '💰 По цене ↑': '💰 Narx bo‘yicha ↑',
        '💰 По цене ↓': '💰 Narx bo‘yicha ↓',
        '🔥 Популярные': '🔥 Ommabop',
        '🆕 Новинки': '🆕 Yangi',
        '📊 Продаваемые': '📊 Sotiladiganlar',
        '🔍 Сбросить фильтры': '🔍 Filtrlarni tiklash',

        # Диапазоны цен
        '💵 До $50': '💵 $50 gacha',
        '💰 $50-100': '💰 $50-100',
        '💎 $100-500': '💎 $100-500',
        '👑 $500+': '👑 $500+',

        # Рейтинг/оценки
        '❌ Отмена': '❌ Bekor qilish',

        # Заказы/детали
        '📋 Детали заказа': '📋 Buyurtma tafsilotlari',
        '📞 Связаться': '📞 Bog‘lanish',
        '❌ Отменить заказ': '❌ Buyurtmani bekor qilish',

        # Выбор языка
        '🇷🇺 Русский': '🇷🇺 Русский',
        "🇺🇿 O'zbekcha": "🇺🇿 O'zbekcha",

        # Админ-панель
        '📊 Статистика': '📊 Statistika',
        '📦 Заказы': '📦 Buyurtmalar',
        '🛠 Товары': '🛠 Tovarlar',
        '👥 Пользователи': '👥 Foydalanuvchilar',
        '📈 Аналитика': '📈 Analitika',
        '🛡 Безопасность': '🛡 Xavfsizlik',
        '💰 Финансы': '💰 Moliya',
        '📦 Склад': '📦 Ombor',
        '🤖 AI': '🤖 AI',
        '🎯 Автоматизация': '🎯 Avtomatlashtirish',
        '👥 CRM': '👥 CRM',
        '📢 Рассылка': '📢 Xabarnoma',
        '➕ Добавить товар': "➕ Tovar qo'shish",

        # Аналитика/периоды
        '📊 Продажи за период': '📊 Davr bo‘yicha savdo',
        '👥 Поведение клиентов': '👥 Mijozlar xulqi',
        '📈 ABC-анализ': '📈 ABC-tahlil',
        '🎯 Воронка конверсии': '🎯 Konversiya voronkasi',
        '💰 Прогноз выручки': '💰 Daromad prognozi',
        '📦 Эффективность товаров': '📦 Tovarlar samaradorligi',
        '📅 Сегодня': '📅 Bugun',
        '📅 Вчера': '📅 Kecha',
        '📅 Неделя': '📅 Hafta',
        '📅 Месяц': '📅 Oy',
        '📅 Квартал': '📅 Chorak',
        '📅 Год': '📅 Yil',

        # Контакты
        '💬 Написать в чате': '💬 Chatda yozish',
        '📞 Позвонить': '📞 Qo‘ng‘iroq qilish',
    }
    return m.get(ru, ru)

def create_main_keyboard(language='ru'):
    """Главная клавиатура"""
    if language == 'uz':
        return {
            'keyboard': [
                ['🛍 Katalog', '🛒 Savat'],
                ['📋 Mening buyurtmalarim', '👤 Profil'],
                ['🔍 Qidiruv', 'ℹ️ Yordam'],
                ["📞 Biz bilan bog'lanish"],
                ["🧑‍💼 Sotuvchi bo'lish"]
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

def create_categories_keyboard(categories, language='ru'):
    """Клавиатура с категориями"""
    keyboard = []
    for i in range(0, len(categories), 2):
        row = [f"{categories[i][3]} {categories[i][1]}"]
        if i + 1 < len(categories):
            row.append(f"{categories[i + 1][3]} {categories[i + 1][1]}")
        keyboard.append(row)
    keyboard.append([_t(language, '🔙 К категориям'), _t(language, '🏠 Главная')])
    return {'keyboard': keyboard, 'resize_keyboard': True, 'one_time_keyboard': False}

def create_subcategories_keyboard(subcategories, language='ru'):
    """Клавиатура с подкатегориями/брендами"""
    keyboard = []
    for i in range(0, len(subcategories), 2):
        row = [f"{subcategories[i][2]} {subcategories[i][1]}"]
        if i + 1 < len(subcategories):
            row.append(f"{subcategories[i + 1][2]} {subcategories[i + 1][1]}")
        keyboard.append(row)
    keyboard.append([_t(language, '🔙 К категориям'), _t(language, '🏠 Главная')])
    return {'keyboard': keyboard, 'resize_keyboard': True, 'one_time_keyboard': False}

def create_products_keyboard(products, show_back=True, language='ru'):
    """Клавиатура с товарами"""
    keyboard = []
    for product in products:
        keyboard.append([f"🛍 {product[1]} - ${product[3]:.2f}"])
    if show_back:
        keyboard.append([_t(language, '🔙 К категориям'), _t(language, '🏠 Главная')])
    else:
        keyboard.append([_t(language, '🏠 Главная')])
    return {'keyboard': keyboard, 'resize_keyboard': True, 'one_time_keyboard': False}

def format_price(price):
    """Форматирование цены для клавиатур"""
    return f"${price:.2f}"

def create_product_inline_keyboard(product_id, language='ru'):
    """Inline клавиатура для товара"""
    return {
        'inline_keyboard': [
            [
                {'text': _t(language, '🛒 Добавить в корзину'), 'callback_data': f'add_to_cart_{product_id}'},
                {'text': _t(language, '❤️ В избранное'), 'callback_data': f'add_to_favorites_{product_id}'}
            ],
            [
                {'text': _t(language, '📊 Отзывы'), 'callback_data': f'reviews_{product_id}'},
                {'text': _t(language, '⭐ Оценить'), 'callback_data': f'rate_product_{product_id}'}
            ]
        ]
    }

def create_cart_keyboard(has_items=False, language='ru'):
    """Клавиатура для корзины"""
    keyboard = []
    if has_items:
        keyboard.extend([
            [_t(language, '📦 Оформить заказ')],
            [_t(language, '🗑 Очистить корзину'), _t(language, '➕ Добавить товары')]
        ])
    else:
        keyboard.append([_t(language, '🛍 Перейти в каталог')])
    keyboard.append([_t(language, '🏠 Главная')])
    return {'keyboard': keyboard, 'resize_keyboard': True, 'one_time_keyboard': False}

def create_registration_keyboard(step, suggested_value=None, language='ru'):
    """Клавиатура для регистрации"""
    keyboard = []
    if step == 'name' and suggested_value:
        keyboard.append([suggested_value])
    elif step == 'phone':
        keyboard.append([{ 'text': _t(language, '📱 Поделиться номером'), 'request_contact': True }])
        keyboard.append([_t(language, '⏭ Пропустить')])
    elif step == 'email':
        keyboard.append([_t(language, '⏭ Пропустить')])
    elif step == 'language':
        keyboard.append(['🇷🇺 Русский', "🇺🇿 O'zbekcha"])
    if step != 'language':  # не показываем отмену на последнем шаге
        keyboard.append([_t(language, '❌ Отмена')])
    return {'keyboard': keyboard, 'resize_keyboard': True, 'one_time_keyboard': True}

def create_order_keyboard(language='ru'):
    """Клавиатура для оформления заказа"""
    return {
        'keyboard': [
            [_t(language, '💳 Онлайн оплата'), _t(language, '💵 Наличными при получении')],
            [_t(language, '❌ Отмена заказа')]
        ],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }

def create_admin_keyboard(language='ru'):
    """Клавиатура для администратора"""
    return {
        'keyboard': [
            [_t(language, '📊 Статистика'), _t(language, '📦 Заказы')],
            [_t(language, '🛠 Товары'), _t(language, '👥 Пользователи')],
            [_t(language, '📈 Аналитика'), _t(language, '🛡 Безопасность')],
            [_t(language, '💰 Финансы'), _t(language, '📦 Склад')],
            [_t(language, '🤖 AI'), _t(language, '🎯 Автоматизация')],
            [_t(language, '👥 CRM'), _t(language, '📢 Рассылка')],
            [_t(language, '🔙 Пользовательский режим')]
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }

def create_back_keyboard(language='ru'):
    """Простая клавиатура 'Назад'"""
    return {
        'keyboard': [[_t(language, '🔙 Назад'), _t(language, '🏠 Главная')]],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }

def create_confirmation_keyboard(language='ru'):
    """Клавиатура подтверждения"""
    return {
        'keyboard': [[_t(language, '✅ Да'), _t(language, '❌ Нет')]],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }

def create_search_filters_keyboard(language='ru'):
    """Клавиатура для фильтров поиска"""
    return {
        'inline_keyboard': [
            [
                {'text': _t(language, '💰 По цене ↑'), 'callback_data': 'sort_price_low'},
                {'text': _t(language, '💰 По цене ↓'), 'callback_data': 'sort_price_high'}
            ],
            [
                {'text': _t(language, '🔥 Популярные'), 'callback_data': 'sort_popular'},
                {'text': _t(language, '🆕 Новинки'), 'callback_data': 'sort_newest'}
            ],
            [
                {'text': _t(language, '📊 Продаваемые'), 'callback_data': 'sort_sales'},
                {'text': _t(language, '🔍 Сбросить фильтры'), 'callback_data': 'reset_filters'}
            ]
        ]
    }

def create_price_filter_keyboard(language='ru'):
    """Клавиатура для фильтра по цене"""
    return {
        'inline_keyboard': [
            [
                {'text': _t(language, '💵 До $50'), 'callback_data': 'price_0_50'},
                {'text': _t(language, '💰 $50-100'), 'callback_data': 'price_50_100'}
            ],
            [
                {'text': _t(language, '💎 $100-500'), 'callback_data': 'price_100_500'}
            ],
            [
                {'text': _t(language, '👑 $500+'), 'callback_data': 'price_500_plus'}
            ],
            [
                {'text': _t(language, '🔙 Назад'), 'callback_data': 'back_to_search'}
            ]
        ]
    }

def create_rating_keyboard(product_id, language='ru'):
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
                {'text': _t(language, '❌ Отмена'), 'callback_data': 'cancel_rating'}
            ]
        ]
    }

def create_order_details_keyboard(order_id, language='ru'):
    """Клавиатура для детального просмотра заказа"""
    return {
        'inline_keyboard': [
            [
                {'text': _t(language, '📋 Детали заказа'), 'callback_data': f'order_details_{order_id}'},
                {'text': _t(language, '📞 Связаться'), 'callback_data': f'contact_about_{order_id}'}
            ],
            [
                {'text': _t(language, '❌ Отменить заказ'), 'callback_data': f'cancel_order_{order_id}'}
            ]
        ]
    }

def create_language_keyboard(language='ru'):
    """Клавиатура выбора языка"""
    return {
        'keyboard': [
            ['🇷🇺 Русский', "🇺🇿 O'zbekcha"],
            [_t(language, '❌ Отмена')]
        ],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }

def create_payment_methods_keyboard(language='ru'):
    """Клавиатура способов оплаты (наличные/карта)"""
    return {
        'keyboard': [
            [_t(language, '💵 Наличными при получении'), _t(language, '💳 Оплата картой')],
            [_t(language, '❌ Отмена')]
        ],
        'resize_keyboard': True
    }

def create_cart_item_keyboard(cart_item_id, current_quantity, language='ru'):
    """Клавиатура для управления товаром в корзине"""
    qty_text = f'📦 {current_quantity} ' + (_t(language, 'шт.'))
    return {
        'inline_keyboard': [
            [
                {'text': '➖', 'callback_data': f'cart_decrease_{cart_item_id}'},
                {'text': qty_text, 'callback_data': f'cart_quantity_{cart_item_id}'},
                {'text': '➕', 'callback_data': f'cart_increase_{cart_item_id}'}
            ],
            [
                {'text': _t(language, '🗑 Удалить'), 'callback_data': f'cart_remove_{cart_item_id}'}
            ]
        ]
    }

def create_admin_products_keyboard(products, language='ru'):
    """Клавиатура для управления товарами админом"""
    keyboard = []
    for product in products:
        status_emoji = "✅" if product[7] else "❌"
        keyboard.append([
            {'text': f'{status_emoji} {product[1]}', 'callback_data': f'admin_view_product_{product[0]}'}
        ])
    keyboard.append([
        {'text': _t(language, '➕ Добавить товар'), 'callback_data': 'admin_add_product'},
        {'text': _t(language, '🔙 Назад'), 'callback_data': 'admin_back_main'}
    ])
    return {'inline_keyboard': keyboard}

def create_notifications_keyboard(language='ru'):
    """Клавиатура для управления уведомлениями"""
    return {
        'inline_keyboard': [
            [
                {'text': _t(language, '📢 Рассылка всем'), 'callback_data': 'broadcast_all'},
                {'text': _t(language, '🎯 Автоматизация'), 'callback_data': 'broadcast_active'}  # при желании замените текст
            ],
            [
                {'text': '😴 ' + ('Неактивным' if language != 'uz' else 'Nofaollarga'),
                 'callback_data': 'broadcast_inactive'},
                {'text': '🆕 ' + ('Новым пользователям' if language != 'uz' else 'Yangi foydalanuvchilarga'),
                 'callback_data': 'broadcast_new'}
            ],
            [
                {'text': _t(language, '📊 Статистика рассылок') if language != 'uz' else '📊 Xabarnoma statistikasi',
                 'callback_data': 'broadcast_stats'},
                {'text': _t(language, '🔙 Назад'), 'callback_data': 'admin_back_main'}
            ]
        ]
    }

def create_analytics_keyboard(language='ru'):
    """Клавиатура для аналитики"""
    return {
        'inline_keyboard': [
            [
                {'text': _t(language, '📊 Продажи за период'), 'callback_data': 'analytics_sales'},
                {'text': _t(language, '👥 Поведение клиентов'), 'callback_data': 'analytics_behavior'}
            ],
            [
                {'text': _t(language, '📈 ABC-анализ'), 'callback_data': 'analytics_abc'},
                {'text': _t(language, '🎯 Воронка конверсии'), 'callback_data': 'analytics_funnel'}
            ],
            [
                {'text': _t(language, '💰 Прогноз выручки'), 'callback_data': 'analytics_forecast'},
                {'text': _t(language, '📦 Эффективность товаров'), 'callback_data': 'analytics_products'}
            ],
            [
                {'text': _t(language, '🔙 Назад'), 'callback_data': 'admin_back_main'}
            ]
        ]
    }

def create_period_selection_keyboard(language='ru'):
    """Клавиатура выбора периода для отчетов"""
    return {
        'inline_keyboard': [
            [
                {'text': _t(language, '📅 Сегодня'), 'callback_data': 'period_today'},
                {'text': _t(language, '📅 Вчера'), 'callback_data': 'period_yesterday'}
            ],
            [
                {'text': _t(language, '📅 Неделя'), 'callback_data': 'period_week'},
                {'text': _t(language, '📅 Месяц'), 'callback_data': 'period_month'}
            ],
            [
                {'text': _t(language, '📅 Квартал'), 'callback_data': 'period_quarter'},
                {'text': _t(language, '📅 Год'), 'callback_data': 'period_year'}
            ],
            [
                {'text': _t(language, '🔙 Назад'), 'callback_data': 'admin_analytics'}
            ]
        ]
    }

def create_address_location_keyboard(language='ru'):
    """Клавиатура для ввода адреса или отправки локации"""
    return {
        'keyboard': [
            [{ 'text': _t(language, '📍 Отправить локацию'), 'request_location': True }],
            ['✍️ ' + ('Ввести адрес' if language != 'uz' else 'Manzil kiritish')],
            [_t(language, '🔙 Назад'), _t(language, '🏠 Главная')]
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }

def create_product_inline_keyboard_with_qty(product_id, qty=1, category_id=None, subcategory_id=None, language='ru'):
    """Inline клавиатура товара с выбором количества"""
    qty = max(1, min(int(qty or 1), 20))
    qty_label = f'{qty} ' + (_t(language, 'шт.'))
    back_cb = ('back_to_subcategory_' + str(subcategory_id)) if subcategory_id else (('back_to_category_' + str(category_id)) if category_id else 'back_to_categories')
    return {
        'inline_keyboard': [
            [
                {'text': '➖', 'callback_data': f'qty_dec_{product_id}_{qty}'},
                {'text': qty_label, 'callback_data': 'noop'},
                {'text': '➕', 'callback_data': f'qty_inc_{product_id}_{qty}'}
            ],
            [
                {'text': _t(language, '🛒 Добавить в корзину').replace(' в корзину', ''), 'callback_data': f'add_to_cart_{product_id}_{qty}'},
                {'text': _t(language, '🔙 Назад'), 'callback_data': back_cb}
            ]
        ]
    }

def create_contact_inline_keyboard(phone=None, tg_username=None, chat_url=None, extra=None, language='ru'):
    """Inline-клавиатура с кнопками для связи (чат/звонок)"""
    rows = []
    btn_row = []
    url = chat_url.strip() if chat_url else None
    if not url and tg_username:
        uname = tg_username.strip()
        if uname.startswith('@'):
            uname = uname[1:]
        url = f"https://t.me/{uname}"
    if url:
        btn_row.append({'text': _t(language, '💬 Написать в чате'), 'url': url})
    if phone:
        tel = str(phone).replace(' ', '')
        btn_row.append({'text': f"{_t(language, '📞 Позвонить')} {phone}", 'url': f'tel:{tel}'})
    if btn_row:
        rows.append(btn_row)
    if extra and isinstance(extra, list) and extra:
        rows.append(extra)
    return {'inline_keyboard': rows} if rows else None

def create_contact_request_keyboard(lang=None):
    """Клавиатура: запрос контакта (номер телефона)"""
    language = (lang or 'ru')
    share_text = _t(language, '📱 Поделиться номером')
    cancel_text = _t(language, '❌ Отмена')
    keyboard = [
        [ {'text': share_text, 'request_contact': True} ],
        [ cancel_text ]
    ]
    return {'keyboard': keyboard, 'resize_keyboard': True, 'one_time_keyboard': True}
