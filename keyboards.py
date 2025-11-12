import logging

logger = logging.getLogger(__name__)


def create_main_keyboard(language='ru'):
    """Главное меню"""
    if language == 'uz':
        keyboard = {
            'keyboard': [
                ['🛍 Katalog', '🛒 Savat'],
                ['📋 Mening buyurtmalarim', '👤 Profil'],
                ['🔍 Qidiruv', "🧑‍💼 Sotuvchi bo'lish"],
                ['ℹ️ Yordam', "📞 Biz bilan bog'lanish"]
            ],
            'resize_keyboard': True
        }
    else:
        keyboard = {
            'keyboard': [
                ['🛍 Каталог', '🛒 Корзина'],
                ['📋 Мои заказы', '👤 Профиль'],
                ['🔍 Поиск', '🧑‍💼 Стать продавцом'],
                ['ℹ️ Помощь', '📞 Связаться с нами']
            ],
            'resize_keyboard': True
        }
    return keyboard


def create_categories_keyboard(categories):
    """Клавиатура категорий"""
    keyboard = {'keyboard': [], 'resize_keyboard': True}
    row = []
    for cat in categories:
        btn_text = f"{cat[2]} {cat[1]}" if cat[2] else cat[1]
        row.append(btn_text)
        if len(row) == 2:
            keyboard['keyboard'].append(row)
            row = []
    if row:
        keyboard['keyboard'].append(row)
    keyboard['keyboard'].append(['🔙 Главная'])
    return keyboard


def create_subcategories_keyboard(subcategories, category_id=None):
    """Клавиатура подкатегорий/брендов"""
    keyboard = {'keyboard': [], 'resize_keyboard': True}
    row = []
    for sub in subcategories:
        btn_text = f"{sub[3]} {sub[2]}" if sub[3] else sub[2]
        row.append(btn_text)
        if len(row) == 2:
            keyboard['keyboard'].append(row)
            row = []
    if row:
        keyboard['keyboard'].append(row)
    keyboard['keyboard'].append(['🔙 К категориям'])
    return keyboard


def create_products_keyboard(products, show_back=True, language='ru'):
    """Клавиатура списка товаров"""
    keyboard = {'keyboard': [], 'resize_keyboard': True}
    for product in products:
        name = product[1]
        price = product[3]
        btn_text = f"🛍 {name} - {price} so'm" if language == 'uz' else f"🛍 {name} - {price} ₽"
        keyboard['keyboard'].append([btn_text])

    if show_back:
        if language == 'uz':
            keyboard['keyboard'].append(['🔙 Kategoriyalarga qaytish'])
        else:
            keyboard['keyboard'].append(['🔙 К категориям'])
    return keyboard


def create_product_inline_keyboard(product_id, category_id=None, subcategory_id=None, qty: int = 1):
    """Инлайн-клавиатура товара"""
    inline_keyboard = [
        [
            {'text': f'➕ Добавить в корзину (×{qty})', 'callback_data': f'add_to_cart_{product_id}_{qty}'}
        ],
        [
            {'text': '❤️ В избранное', 'callback_data': f'add_to_favorites_product_{product_id}'}
        ],
        [
            {'text': '📝 Отзывы', 'callback_data': f'reviews_{product_id}'}
        ]
    ]
    if category_id:
        inline_keyboard.append(
            [{'text': '🔙 К подкатегориям', 'callback_data': f'back_to_category_{category_id}'}]
        )
    if subcategory_id:
        inline_keyboard.append(
            [{'text': '🔙 К товарам', 'callback_data': f'back_to_subcategory_{subcategory_id}'}]
        )
    return {'inline_keyboard': inline_keyboard}


def create_cart_keyboard(has_items: bool, language='ru'):
    """Клавиатура корзины"""
    buttons = []

    if has_items:
        if language == 'uz':
            buttons.append(['📦 Buyurtma berish'])
            buttons.append(['🗑 Savatni tozalash', '🛍 Katalogga qaytish'])
        else:
            buttons.append(['📦 Оформить заказ'])
            buttons.append(['🗑 Очистить корзину', '🛍 Перейти в каталог'])
    else:
        if language == 'uz':
            buttons.append(['🛍 Katalogga o‘tish'])
        else:
            buttons.append(['🛍 Перейти в каталог'])

    buttons.append(['🔙 Главная'] if language == 'ru' else ['🏠 Bosh sahifa'])

    return {
        'keyboard': buttons,
        'resize_keyboard': True
    }


def create_registration_keyboard(step, suggested_name=None):
    """Клавиатура регистрации"""
    keyboard = {'keyboard': [], 'resize_keyboard': True}

    if step == 'name':
        if suggested_name:
            keyboard['keyboard'].append([suggested_name])
        keyboard['keyboard'].append(['❌ Отмена'])
    elif step == 'phone':
        keyboard['keyboard'].append(['⏭ Пропустить'])
        keyboard['keyboard'].append(['❌ Отмена'])
    elif step == 'email':
        keyboard['keyboard'].append(['⏭ Пропустить'])
        keyboard['keyboard'].append(['❌ Отмена'])
    elif step == 'language':
        keyboard['keyboard'].append(['🇷🇺 Русский', "🇺🇿 O'zbekcha"])
        keyboard['keyboard'].append(['❌ Отмена'])

    return keyboard


def create_order_keyboard(language='ru'):
    """Клавиатура оформления заказа"""
    if language == 'uz':
        keyboard = {
            'keyboard': [
                ['💳 Kartadan toʻlov'],
                ['💵 Qabul qilishda naqd'],
                ['🔙 Bosh menyu']
            ],
            'resize_keyboard': True
        }
    else:
        keyboard = {
            'keyboard': [
                ['💳 Оплата картой'],
                ['💵 Наличными при получении'],
                ['🔙 Главная']
            ],
            'resize_keyboard': True
        }
    return keyboard


def create_back_keyboard(language='ru'):
    """Клавиатура с кнопкой Назад/Главная"""
    if language == 'uz':
        keyboard = {
            'keyboard': [
                ['🏠 Bosh sahifa']
            ],
            'resize_keyboard': True
        }
    else:
        keyboard = {
            'keyboard': [
                ['🏠 Главная']
            ],
            'resize_keyboard': True
        }
    return keyboard


def create_confirmation_keyboard():
    """Клавиатура подтверждения"""
    keyboard = {
        'keyboard': [
            ['✅ Да', '❌ Нет']
        ],
        'resize_keyboard': True
    }
    return keyboard


def create_search_filters_keyboard():
    """Клавиатура фильтров поиска (пока заглушка)"""
    keyboard = {
        'inline_keyboard': [
            [{'text': '💰 По цене', 'callback_data': 'filter_price'}],
            [{'text': '⭐ По рейтингу', 'callback_data': 'filter_rating'}],
            [{'text': '🔙 Назад', 'callback_data': 'back_to_search'}]
        ]
    }
    return keyboard


def create_price_filter_keyboard():
    """Клавиатура фильтра цены (заглушка)"""
    keyboard = {
        'inline_keyboard': [
            [{'text': '⬆ Дешевле', 'callback_data': 'price_asc'}],
            [{'text': '⬇ Дороже', 'callback_data': 'price_desc'}],
            [{'text': '🔙 Назад', 'callback_data': 'back_to_filters'}]
        ]
    }
    return keyboard


def create_rating_keyboard():
    """Клавиатура выбора рейтинга"""
    keyboard = {
        'inline_keyboard': [
            [{'text': '⭐', 'callback_data': 'rate_1'},
             {'text': '⭐⭐', 'callback_data': 'rate_2'},
             {'text': '⭐⭐⭐', 'callback_data': 'rate_3'},
             {'text': '⭐⭐⭐⭐', 'callback_data': 'rate_4'},
             {'text': '⭐⭐⭐⭐⭐', 'callback_data': 'rate_5'}]
        ]
    }
    return keyboard


def create_order_details_keyboard(order_id):
    """Клавиатура деталей заказа"""
    keyboard = {
        'inline_keyboard': [
            [{'text': '📦 Повторить заказ', 'callback_data': f'repeat_order_{order_id}'}],
            [{'text': '❌ Отменить заказ', 'callback_data': f'cancel_order_{order_id}'}]
        ]
    }
    return keyboard


def create_language_keyboard():
    """Клавиатура выбора языка"""
    keyboard = {
        'keyboard': [
            ['🇷🇺 Русский', "🇺🇿 O'zbekcha"],
            ['❌ Отмена']
        ],
        'resize_keyboard': True
    }
    return keyboard


def create_payment_methods_keyboard(language='ru'):
    """Клавиатура способов оплаты"""
    if language == 'uz':
        keyboard = {
            'keyboard': [
                ['💳 Kartadan toʻlov'],
                ['💵 Qabul qilishda naqd'],
                ['🔙 Bosh sahifa']
            ],
            'resize_keyboard': True
        }
    else:
        keyboard = {
            'keyboard': [
                ['💳 Оплата картой'],
                ['💵 Наличными при получении'],
                ['🔙 Главная']
            ],
            'resize_keyboard': True
        }
    return keyboard


def create_cart_item_keyboard(cart_item_id, quantity):
    """Инлайн-клавиатура одного товара в корзине"""
    keyboard = {
        'inline_keyboard': [
            [
                {'text': '➖', 'callback_data': f'cart_decrease_{cart_item_id}'},
                {'text': str(quantity), 'callback_data': 'noop'},
                {'text': '➕', 'callback_data': f'cart_increase_{cart_item_id}'}
            ],
            [
                {'text': '🗑 Удалить', 'callback_data': f'cart_remove_{cart_item_id}'}
            ]
        ]
    }
    return keyboard

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

