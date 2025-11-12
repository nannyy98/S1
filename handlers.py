"""
Обработчики сообщений для телеграм-бота
"""

import logging
from datetime import datetime

from keyboards import (
    create_main_keyboard, create_categories_keyboard, create_subcategories_keyboard,
    create_products_keyboard, create_product_inline_keyboard, create_cart_keyboard,
    create_registration_keyboard, create_order_keyboard, create_back_keyboard,
    create_confirmation_keyboard, create_search_filters_keyboard,
    create_price_filter_keyboard, create_rating_keyboard, create_order_details_keyboard,
    create_language_keyboard, create_payment_methods_keyboard, create_cart_item_keyboard
)
from utils import (
    format_price, format_date, validate_email, validate_phone,
    truncate_text, create_pagination_keyboard, escape_html,
    calculate_cart_total, format_cart_summary, get_order_status_emoji,
    get_order_status_text, create_product_card, create_stars_display
)
from localization import t, get_user_language
from payments import PaymentProcessor, create_payment_keyboard, format_payment_info

logger = logging.getLogger(__name__)


class MessageHandler:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.user_states = {}
        self.notification_manager = None
        self.payment_processor = PaymentProcessor()

    def handle_message(self, message):
        """Главный обработчик сообщений"""
        try:
            text = message.get('text', '')
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']

            # Проверяем регистрацию пользователя
            user_data = self.db.get_user_by_telegram_id(telegram_id)

            if not user_data and text != '/start' and telegram_id not in self.user_states:
                self.send_registration_prompt(chat_id)
                return

            # Получаем язык пользователя
            user_language = 'ru'
            if user_data:
                user_language = user_data[0][5] or 'ru'

            # Обрабатываем команды
            if text == '/start':
                self.handle_start_command(message)
            elif text == '/help':
                self.handle_help_command(message, user_language)
            elif text.startswith('/order_'):
                self.handle_order_command(message)
            elif text.startswith('/track_'):
                self.handle_track_command(message)
            elif text.startswith('/promo_'):
                self.handle_promo_command(message)
            elif text.startswith('/restore_'):
                self.handle_restore_command(message)
            elif text == '/notifications':
                self.show_user_notifications(message)

            # Обрабатываем состояния пользователя
            elif telegram_id in self.user_states:
                self.handle_user_state(message)

            # Обрабатываем кнопки меню
            elif text in ['🛍 Каталог', '🛍 Katalog', '🛍 Перейти в каталог']:
                self.show_catalog(message)
            elif text == '🔙 К категориям':
                self.show_catalog(message)
            elif text.startswith('🛍 '):
                self.handle_product_selection(message)
            elif text in ['🛒 Корзина', '🛒 Savat']:
                self.show_cart(message)
            elif text in ['📋 Мои заказы', '📋 Mening buyurtmalarim']:
                self.show_user_orders(message)
            elif text in ['👤 Профиль', '👤 Profil']:
                self.show_user_profile(message)
            elif text in ['🔍 Поиск', '🔍 Qidiruv']:
                self.start_product_search(message)
            elif text in ['🧑‍💼 Стать продавцом', "🧑‍💼 Sotuvchi bo'lish"]:
                self.start_seller_application(message)
            elif text in ['ℹ️ Помощь', 'ℹ️ Yordam']:
                self.handle_help_command(message, user_language)
            elif text in ['📞 Связаться с нами', "📞 Biz bilan bog'lanish"]:
                self.handle_contact_request(message, user_language)
            elif text == '🔙 Главная' or text == '🏠 Главная' or text == '🏠 Bosh sahifa':
                self.show_main_menu(message)
            elif text == '🌍 Сменить язык':
                self.start_language_change(message)

            # Обработка кнопок категорий и подкатегорий
            elif self.is_category_button(text):
                self.handle_category_selection(message)
            elif self.is_subcategory_button(text):
                self.handle_subcategory_selection(message)

            # Обработка поиска из неизвестной команды
            elif len(text) > 2 and not text.startswith('/'):
                self.handle_unknown_command(message, user_language)

            # Обработка оформления заказа
            elif text == '📦 Оформить заказ':
                self.start_order_process(message)
            elif text in ['💳 Оплата картой', '💳 Kartadan toʻlov']:
                self.handle_payment_method_selection(message)
            elif text in ['💵 Наличными при получении', '💵 Qabul qilishda naqd']:
                self.handle_payment_method_selection(message)

            # Управление корзиной
            elif text == '🗑 Очистить корзину':
                self.clear_cart(message)
            elif text == '➕ Добавить товары' or text == '🛍 Перейти в каталог':
                self.show_catalog(message)

            else:
                self.handle_unknown_command(message, user_language)

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
            self.bot.send_message(message['chat']['id'], "❌ Произошла ошибка. Попробуйте еще раз.")

    def send_registration_prompt(self, chat_id):
        """Приглашение к регистрации"""
        prompt_text = (
            "👋 Добро пожаловать!\n\n"
            "Для использования бота необходимо пройти регистрацию.\n\n"
            "Нажмите /start для начала."
        )
        self.bot.send_message(chat_id, prompt_text)

    def handle_start_command(self, message):
        """Обработка команды /start"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)

        if user_data:
            user_language = user_data[0][5] or 'ru'
            welcome_text = t('welcome_back', language=user_language)
            self.bot.send_message(chat_id, welcome_text, create_main_keyboard(user_language))
        else:
            self.start_registration(message)

    def start_registration(self, message):
        """Начало процесса регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        suggested_name = message['from'].get('first_name', '')
        if message['from'].get('last_name'):
            suggested_name += f" {message['from']['last_name']}"

        welcome_text = t('welcome_new')
        self.bot.send_message(chat_id, welcome_text)

        name_text = "👤 Как вас зовут?"
        self.bot.send_message(
            chat_id,
            name_text,
            create_registration_keyboard('name', suggested_name)
        )

        self.user_states[telegram_id] = 'registration_name'

    def handle_user_state(self, message):
        """Обработка состояний пользователя"""
        telegram_id = message['from']['id']
        state = self.user_states.get(telegram_id)

        if state == 'registration_name':
            self.handle_registration_name(message)
        elif state == 'registration_phone':
            self.handle_registration_phone(message)
        elif state == 'registration_email':
            self.handle_registration_email(message)
        elif state == 'registration_language':
            self.handle_registration_language(message)
        elif state == 'seller_name':
            self.handle_seller_name(message)
        elif state == 'seller_phone':
            self.handle_seller_phone(message)
        elif state == 'seller_brand':
            self.handle_seller_brand(message)
        elif state == 'seller_products':
            self.handle_seller_products(message)
        elif state == 'searching':
            self.handle_search_query(message)
        elif state == 'order_address':
            self.handle_order_address(message)
        elif state == 'changing_language':
            self.handle_language_change(message)
        elif state and isinstance(state, str) and state.startswith('confirm_clear_cart_'):
            self.handle_clear_cart_confirmation(message, state)
        else:
            # Сброс неизвестного состояния
            self.user_states.pop(telegram_id, None)

    def handle_registration_name(self, message):
        """Обработка ввода имени при регистрации"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        if text == '❌ Отмена':
            del self.user_states[telegram_id]
            self.bot.send_message(chat_id, "❌ Регистрация отменена")
            return

        if len(text) < 2:
            self.bot.send_message(chat_id, "❌ Имя слишком короткое. Попробуйте еще раз:")
            return

        if not hasattr(self, 'registration_data'):
            self.registration_data = {}
        self.registration_data[telegram_id] = {'name': text}

        phone_text = "📱 Поделитесь номером телефона или пропустите этот шаг:"
        self.bot.send_message(chat_id, phone_text, create_registration_keyboard('phone'))

        self.user_states[telegram_id] = 'registration_phone'

    def handle_registration_phone(self, message):
        """Обработка ввода телефона"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        phone = None

        if text == '⏭ Пропустить':
            phone = None
        elif text == '❌ Отмена':
            del self.user_states[telegram_id]
            if hasattr(self, 'registration_data') and telegram_id in self.registration_data:
                del self.registration_data[telegram_id]
            self.bot.send_message(chat_id, "❌ Регистрация отменена")
            return
        elif 'contact' in message:
            phone = message['contact']['phone_number']
        else:
            phone = validate_phone(text)
            if not phone:
                self.bot.send_message(chat_id, "❌ Неверный формат телефона. Попробуйте еще раз:")
                return

        self.registration_data[telegram_id]['phone'] = phone

        email_text = "📧 Введите email или пропустите:"
        self.bot.send_message(chat_id, email_text, create_registration_keyboard('email'))

        self.user_states[telegram_id] = 'registration_email'

    def handle_registration_email(self, message):
        """Обработка ввода email"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        email = None

        if text == '⏭ Пропустить':
            email = None
        elif text == '❌ Отмена':
            del self.user_states[telegram_id]
            if hasattr(self, 'registration_data') and telegram_id in self.registration_data:
                del self.registration_data[telegram_id]
            self.bot.send_message(chat_id, "❌ Регистрация отменена")
            return
        else:
            if not validate_email(text):
                self.bot.send_message(chat_id, "❌ Неверный формат email. Попробуйте еще раз:")
                return
            email = text

        self.registration_data[telegram_id]['email'] = email

        language_text = "🌍 Выберите язык / Tilni tanlang:"
        self.bot.send_message(chat_id, language_text, create_registration_keyboard('language'))

        self.user_states[telegram_id] = 'registration_language'

    def handle_registration_language(self, message):
        """Обработка выбора языка при регистрации"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        if text == '🇷🇺 Русский':
            language = 'ru'
        elif text == "🇺🇿 O'zbekcha":
            language = 'uz'
        else:
            self.bot.send_message(chat_id, "❌ Выберите язык из предложенных вариантов:")
            return

        reg_data = self.registration_data.get(telegram_id, {})

        user_id = self.db.add_user(
            telegram_id,
            reg_data.get('name', 'Пользователь'),
            reg_data.get('phone'),
            reg_data.get('email'),
            language
        )

        if user_id:
            self.db.execute_query(
                'INSERT OR IGNORE INTO loyalty_points (user_id) VALUES (?)',
                (user_id,)
            )

            welcome_complete = t('registration_complete', language=language)
            self.bot.send_message(chat_id, welcome_complete, create_main_keyboard(language))

            if hasattr(self.bot, 'marketing_automation') and self.bot.marketing_automation:
                self.bot.marketing_automation.create_welcome_series(user_id)
        else:
            self.bot.send_message(chat_id, "❌ Ошибка регистрации. Попробуйте позже.")

        del self.user_states[telegram_id]
        if hasattr(self, 'registration_data') and telegram_id in self.registration_data:
            del self.registration_data[telegram_id]

    def handle_help_command(self, message, language='ru'):
        """Обработка команды помощи"""
        chat_id = message['chat']['id']
        help_text = t('help', language=language)
        self.bot.send_message(chat_id, help_text, create_main_keyboard(language))

    def handle_contact_request(self, message, language='ru'):
        """Обработка запроса на связь"""
        from config import CONTACT_INFO
        chat_id = message['chat']['id']

        if language == 'uz':
            contact_text = f"""
📞 <b>Biz bilan bog'lanish</b>

🏢 <b>Call-центр:</b>
📱 {CONTACT_INFO['call_center_phone']}

💬 <b>Telegram yordam:</b>
👤 {CONTACT_INFO['support_telegram']}

🕐 <b>Ish vaqti:</b>
{CONTACT_INFO['working_hours']}

📧 Savollaringiz bo'lsa, biz bilan bog'laning!
Biz doimo yordam berishga tayyormiz! 🤝
"""
        else:
            contact_text = f"""
📞 <b>Связаться с нами</b>

🏢 <b>Call-центр:</b>
📱 {CONTACT_INFO['call_center_phone']}

💬 <b>Telegram поддержка:</b>
👤 {CONTACT_INFO['support_telegram']}

🕐 <b>Время работы:</b>
{CONTACT_INFO['working_hours']}

📧 Если у вас есть вопросы, свяжитесь с нами!
Мы всегда рады помочь! 🤝
"""

        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '📱 Позвонить', 'url': f"tel:{CONTACT_INFO['call_center_phone']}"},
                    {'text': '💬 Telegram', 'url': f"https://t.me/{CONTACT_INFO['support_telegram'].replace('@', '')}"}
                ],
                [
                    {'text': '🔙 Назад' if language == 'ru' else '🔙 Orqaga', 'callback_data': 'back_to_main'}
                ]
            ]
        }

        self.bot.send_message(chat_id, contact_text, keyboard)

    def show_main_menu(self, message):
        """Показ главного меню"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if user_data:
            language = user_data[0][5] or 'ru'
            welcome_text = t('welcome_back', language=language)
        else:
            language = 'ru'
            welcome_text = "👋 Добро пожаловать!"

        self.bot.send_message(chat_id, welcome_text, create_main_keyboard(language))

    def show_catalog(self, message):
        """Показ каталога товаров"""
        chat_id = message['chat']['id']

        categories = self.db.get_categories()

        if categories:
            catalog_text = "🛍 <b>Каталог товаров</b>\n\nВыберите категорию:"
            self.bot.send_message(chat_id, catalog_text, create_categories_keyboard(categories))
        else:
            self.bot.send_message(chat_id, "❌ Каталог временно недоступен")

    def is_category_button(self, text: str) -> bool:
        """Определение, является ли текст кнопкой категории (по БД)"""
        if not text:
            return False
        name = text.split(' ', 1)[-1]
        rows = self.db.execute_query(
            'SELECT id FROM categories WHERE name = ? AND is_active = 1',
            (name,)
        )
        return bool(rows)

    def is_subcategory_button(self, text: str) -> bool:
        """Определение, является ли текст кнопкой подкатегории"""
        if not text:
            return False
        name = text.split(' ', 1)[-1]
        rows = self.db.execute_query(
            'SELECT id FROM subcategories WHERE name = ? AND is_active = 1',
            (name,)
        )
        return bool(rows)

    def handle_category_selection(self, message):
        """Обработка выбора категории"""
        text = message.get('text', '')
        chat_id = message['chat']['id']

        category_name = text.split(' ', 1)[-1].strip()

        category = self.db.execute_query(
            'SELECT id FROM categories WHERE name = ? AND is_active = 1',
            (category_name,)
        )

        if category:
            category_id = category[0][0]

            subcategories = self.db.get_subcategories_by_category(category_id)

            if subcategories:
                subcat_text = f"📂 <b>{category_name}</b>\n\nВыберите бренд или подкатегорию:"
                self.bot.send_message(
                    chat_id,
                    subcat_text,
                    create_subcategories_keyboard(subcategories, category_id)
                )
            else:
                products = self.db.execute_query(
                    'SELECT * FROM products WHERE category_id = ? AND is_active = 1 ORDER BY name LIMIT 30',
                    (category_id,)
                )
                if products:
                    products_text = f"🛍 <b>{category_name}</b>\n\nВыберите товар:"
                    self.bot.send_message(
                        chat_id,
                        products_text,
                        create_products_keyboard(products, show_back=True)
                    )
                else:
                    self.bot.send_message(chat_id, f"❌ В категории '{category_name}' пока нет товаров")
        else:
            self.bot.send_message(chat_id, "❌ Категория не найдена")

    def handle_subcategory_selection(self, message):
        """Обработка выбора подкатегории"""
        text = message.get('text', '')
        chat_id = message['chat']['id']

        subcategory_name = text.split(' ', 1)[-1].strip()

        subcategory = self.db.execute_query(
            'SELECT id, category_id FROM subcategories WHERE name = ? AND is_active = 1',
            (subcategory_name,)
        )

        if subcategory:
            subcategory_id = subcategory[0][0]
            category_id = subcategory[0][1]

            products = self.db.get_products_by_subcategory(subcategory_id)

            if products:
                products_text = f"🛍 <b>{subcategory_name}</b>\n\nВыберите товар:"
                self.bot.send_message(
                    chat_id,
                    products_text,
                    create_products_keyboard(products, language='ru')
                )
            else:
                self.bot.send_message(chat_id, f"❌ В подкатегории '{subcategory_name}' пока нет товаров")
        else:
            self.bot.send_message(chat_id, "❌ Подкатегория не найдена")

    def handle_product_selection(self, message):
        """Обработка выбора товара"""
        text = message.get('text', '')
        chat_id = message['chat']['id']

        product_info = text.split(' ', 1)[-1].strip()

        if ' - ' in product_info:
            product_name = product_info.split(' - ')[0]
        else:
            product_name = product_info

        product = self.db.execute_query(
            'SELECT * FROM products WHERE name = ? AND is_active = 1',
            (product_name,)
        )

        if product:
            self.show_product_details(chat_id, product[0])
        else:
            self.bot.send_message(chat_id, "❌ Товар не найден")

    def show_product_details(self, chat_id, product):
        """Показ деталей товара"""
        try:
            self.db.increment_product_views(product[0])

            reviews = self.db.get_product_reviews(product[0])
            avg_rating = sum(r[0] for r in reviews) / len(reviews) if reviews else 0

            product_card = create_product_card(product)
            if avg_rating > 0:
                stars = create_stars_display(avg_rating)
                product_card += f"⭐ Рейтинг: {stars} ({avg_rating:.1f}/5, {len(reviews)} отзывов)\n"

            kb = create_product_inline_keyboard(product[0], product[4], product[5])

            if product[7]:
                try:
                    res = self.bot.send_photo(chat_id, product[7], product_card, kb)
                    if not res or (isinstance(res, dict) and not res.get('ok', True)):
                        try:
                            self.bot.send_photo(chat_id, product[7])
                        except Exception as _err_photo_plain:
                            logger.error(f"Ошибка отправки фото без подписи: {_err_photo_plain}")
                        self.bot.send_message(chat_id, product_card, kb)
                except Exception as _err_send_photo:
                    logger.error(f"Ошибка отправки фото товара: {_err_send_photo}")
                    try:
                        self.bot.send_photo(chat_id, product[7])
                    except Exception as _err2:
                        logger.error(f"Ошибка повторной отправки фото без подписи: {_err2}")
                    self.bot.send_message(chat_id, product_card, kb)
            else:
                self.bot.send_message(chat_id, product_card, kb)

        except Exception as e:
            logger.error(f"Ошибка показа товара: {e}")
            try:
                if product[7]:
                    self.bot.send_photo(chat_id, product[7])
            except Exception as _err3:
                logger.error(f"Ошибка фолбэка фото без подписи: {_err3}")
            self.bot.send_message(chat_id, "❌ Ошибка загрузки товара")

    def show_cart(self, message):
        """Показ корзины"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return

        user_id = user_data[0][0]
        language = user_data[0][5] or 'ru'

        cart_items = self.db.get_cart_items(user_id)

        if not cart_items:
            empty_cart_text = t('empty_cart', language=language)
            self.bot.send_message(chat_id, empty_cart_text, create_cart_keyboard(False, language=language))
            return

        cart_text = "🛒 <b>Ваша корзина:</b>\n\n"
        total_amount = 0

        for item in cart_items:
            item_total = item[2] * item[3]
            total_amount += item_total
            cart_text += f"🛍 <b>{item[1]}</b>\n"
            cart_text += f"💰 {format_price(item[2])} × {item[3]} = {format_price(item_total)}\n\n"

        cart_text += f"💳 <b>Итого: {format_price(total_amount)}</b>"
        self.bot.send_message(chat_id, cart_text, create_cart_keyboard(True, language=language))

    def show_user_orders(self, message):
        """Показ заказов пользователя"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return

        user_id = user_data[0][0]
        language = user_data[0][5] or 'ru'

        orders = self.db.get_user_orders(user_id)

        if not orders:
            if language == 'uz':
                self.bot.send_message(chat_id, "📋 Hali buyurtmalar yo‘q")
            else:
                self.bot.send_message(chat_id, "📋 У вас пока нет заказов")
            return

        if language == 'uz':
            orders_text = "📋 <b>Buyurtmalaringiz:</b>\n\n"
        else:
            orders_text = "📋 <b>Ваши заказы:</b>\n\n"

        for order in orders[:10]:
            status_emoji = get_order_status_emoji(order[3])
            status_text = get_order_status_text(order[3])
            orders_text += f"{status_emoji} <b>Заказ #{order[0]}</b>\n"
            orders_text += f"💰 {format_price(order[2])}\n"
            orders_text += f"📅 {format_date(order[7])}\n"
            orders_text += f"📊 {status_text}\n\n"

        if language == 'uz':
            orders_text += "👆 Tafsilotlar uchun /order_ID ishlating"
        else:
            orders_text += "👆 Используйте /order_ID для деталей заказа"

        self.bot.send_message(chat_id, orders_text, create_back_keyboard(language=language))

    def show_user_profile(self, message):
        """Показ профиля пользователя"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return

        user = user_data[0]
        user_id = user[0]
        language = user[5] or 'ru'

        order_stats = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_orders,
                COALESCE(SUM(total_amount), 0) as total_spent,
                MAX(created_at) as last_order
            FROM orders 
            WHERE user_id = ? AND status != 'cancelled'
        ''', (user_id,))[0]

        loyalty_data = self.db.get_user_loyalty_points(user_id)

        if language == 'uz':
            profile_text = "👤 <b>Profilingiz</b>\n\n"
            profile_text += f"📝 Ism: {user[2]}\n"
            if user[3]:
                profile_text += f"📱 Telefon: {user[3]}\n"
            if user[4]:
                profile_text += f"📧 Email: {user[4]}\n"
            lang_text = "🇷🇺 Русский" if user[5] == "ru" else "🇺🇿 O'zbekcha"
            profile_text += f"🌍 Til: {lang_text}\n"
            profile_text += f"📅 Roʻyxatdan o‘tgan sana: {format_date(user[7])}\n\n"

            profile_text += "📊 <b>Statistika:</b>\n"
            profile_text += f"📦 Buyurtmalar: {order_stats[0]}\n"
            profile_text += f"💰 Sarflangan: {format_price(order_stats[1])}\n"
            if order_stats[2]:
                profile_text += f"📅 Oxirgi buyurtma: {format_date(order_stats[2])}\n"

            profile_text += "\n⭐ <b>Sodiqlik dasturi:</b>\n"
            profile_text += f"💎 Daraja: {loyalty_data[3]}\n"
            profile_text += f"🏆 Ballar: {loyalty_data[1]}\n\n"
            profile_text += "🌍 Tilni almashtirish: /language"
        else:
            profile_text = "👤 <b>Ваш профиль</b>\n\n"
            profile_text += f"📝 Имя: {user[2]}\n"
            if user[3]:
                profile_text += f"📱 Телефон: {user[3]}\n"
            if user[4]:
                profile_text += f"📧 Email: {user[4]}\n"
            lang_text = "🇷🇺 Русский" if user[5] == "ru" else "🇺🇿 O'zbekcha"
            profile_text += f"🌍 Язык: {lang_text}\n"
            profile_text += f"📅 Регистрация: {format_date(user[7])}\n\n"

            profile_text += "📊 <b>Статистика:</b>\n"
            profile_text += f"📦 Заказов: {order_stats[0]}\n"
            profile_text += f"💰 Потрачено: {format_price(order_stats[1])}\n"
            if order_stats[2]:
                profile_text += f"📅 Последний заказ: {format_date(order_stats[2])}\n"

            profile_text += "\n⭐ <b>Программа лояльности:</b>\n"
            profile_text += f"💎 Уровень: {loyalty_data[3]}\n"
            profile_text += f"🏆 Баллов: {loyalty_data[1]}\n\n"
            profile_text += "🌍 Для смены языка: /language"

        profile_keyboard = {
            'keyboard': [
                ['🌍 Сменить язык', '⭐ Программа лояльности'],
                ['🔙 Главная']
            ],
            'resize_keyboard': True
        }

        self.bot.send_message(chat_id, profile_text, profile_keyboard)

    def start_product_search(self, message):
        """Начало поиска товаров"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        language = user_data[0][5] if user_data else 'ru'

        if language == 'uz':
            search_text = "🔍 <b>Tovar qidirish</b>\n\nQidiruv uchun nomni yozing:"
        else:
            search_text = "🔍 <b>Поиск товаров</b>\n\nВведите название товара для поиска:"

        self.bot.send_message(chat_id, search_text, create_back_keyboard(language=language))
        self.user_states[telegram_id] = 'searching'

    def handle_search_query(self, message):
        """Обработка поискового запроса"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        language = user_data[0][5] if user_data else 'ru'

        if text in ['🔙 Назад', '🏠 Главная', '🏠 Bosh sahifa']:
            self.user_states.pop(telegram_id, None)
            self.show_main_menu(message)
            return

        products = self.db.search_products(text)

        if products:
            if language == 'uz':
                search_results = f"🔍 <b>Qidiruv natijalari:</b> '{text}'\n\n"
            else:
                search_results = f"🔍 <b>Результаты поиска:</b> '{text}'\n\n"

            for product in products[:10]:
                search_results += f"🛍 <b>{product[1]}</b>\n"
                search_results += f"💰 {format_price(product[3])}\n"
                if language == 'uz':
                    search_results += f"📦 Omborda: {product[6]} dona\n\n"
                else:
                    search_results += f"📦 В наличии: {product[6]} шт.\n\n"

            if len(products) > 10:
                if language == 'uz':
                    search_results += f"... va yana {len(products) - 10} ta tovar\n\n"
                else:
                    search_results += f"... и еще {len(products) - 10} товаров\n\n"

            if language == 'uz':
                search_results += "💡 Batafsil uchun tovar nomini bosing"
            else:
                search_results += "💡 Нажмите на название товара для подробностей"

            self.bot.send_message(chat_id, search_results, create_products_keyboard(products[:10], False))
        else:
            if language == 'uz':
                no_results = f"❌ '{text}' bo‘yicha hech narsa topilmadi\n\n"
                no_results += "💡 Qiling:\n"
                no_results += "• So‘rovni o‘zgartiring\n"
                no_results += "• Boshqa kalit so‘zlarni sinab ko‘ring\n"
                no_results += "• Katalogni ko‘ring"
            else:
                no_results = f"❌ По запросу '{text}' ничего не найдено\n\n"
                no_results += "💡 Попробуйте:\n"
                no_results += "• Изменить запрос\n"
                no_results += "• Использовать другие ключевые слова\n"
                no_results += "• Просмотреть каталог"

            self.bot.send_message(chat_id, no_results, create_back_keyboard(language=language))

        self.user_states.pop(telegram_id, None)

    def start_order_process(self, message):
        """Начало оформления заказа"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return

        user_id = user_data[0][0]
        language = user_data[0][5] or 'ru'

        cart_items = self.db.get_cart_items(user_id)

        if not cart_items:
            empty_cart_text = t('empty_cart', language=language)
            self.bot.send_message(chat_id, empty_cart_text)
            return

        total_amount = calculate_cart_total(cart_items)

        if language == 'uz':
            order_summary = "📦 <b>Buyurtmani rasmiylashtirish</b>\n\n"
            order_summary += f"🛍 Tovarlar: {len(cart_items)}\n"
            order_summary += f"💰 Summa: {format_price(total_amount)}\n\n"
            order_summary += "📍 Yetkazib berish manzilini kiriting:"
        else:
            order_summary = "📦 <b>Оформление заказа</b>\n\n"
            order_summary += f"🛍 Товаров: {len(cart_items)}\n"
            order_summary += f"💰 Сумма: {format_price(total_amount)}\n\n"
            order_summary += "📍 Введите адрес доставки:"

        from keyboards import create_address_location_keyboard
        self.bot.send_message(chat_id, order_summary, create_address_location_keyboard())
        self.user_states[telegram_id] = 'order_address'

    def handle_order_address(self, message):
        """Обработка ввода адреса доставки"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        language = user_data[0][5] if user_data else 'ru'

        location = message.get('location')
        if location and isinstance(location, dict) and 'latitude' in location and 'longitude' in location:
            if not hasattr(self, 'order_data'):
                self.order_data = {}
            self.order_data[telegram_id] = self.order_data.get(telegram_id, {})
            self.order_data[telegram_id]['lat'] = float(location.get('latitude'))
            self.order_data[telegram_id]['lon'] = float(location.get('longitude'))
            self.order_data[telegram_id].setdefault('address', 'Геолокация отправлена')

            if language == 'uz':
                payment_text = "💳 To‘lov usulini tanlang:"
            else:
                payment_text = "💳 Выберите способ оплаты:"

            self.bot.send_message(chat_id, payment_text, create_payment_methods_keyboard(language))
            self.user_states.pop(telegram_id, None)
            return

        if text in ['🔙 Назад', '🏠 Главная', '🏠 Bosh sahifa']:
            self.user_states.pop(telegram_id, None)
            self.show_main_menu(message)
            return

        if len(text) < 10:
            if language == 'uz':
                self.bot.send_message(chat_id, "❌ Manzil juda qisqa. To‘liq manzilni yozing:")
            else:
                self.bot.send_message(chat_id, "❌ Адрес слишком короткий. Введите полный адрес:")
            return

        if not hasattr(self, 'order_data'):
            self.order_data = {}

        self.order_data[telegram_id] = {'address': text}

        if language == 'uz':
            payment_text = "💳 To‘lov usulini tanlang:"
        else:
            payment_text = "💳 Выберите способ оплаты:"

        self.bot.send_message(chat_id, payment_text, create_payment_methods_keyboard(language))
        self.user_states.pop(telegram_id, None)

    def handle_payment_method_selection(self, message):
        """Обработка выбора способа оплаты"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return

        user_id = user_data[0][0]
        language = user_data[0][5] or 'ru'

        cart_items = self.db.get_cart_items(user_id)

        if not cart_items:
            if language == 'uz':
                self.bot.send_message(chat_id, "❌ Savat bo‘sh")
            else:
                self.bot.send_message(chat_id, "❌ Корзина пуста")
            return

        if text in ['💵 Наличными при получении', '💵 Qabul qilishda naqd']:
            payment_method = 'cash'
        elif text in ['💳 Оплата картой', '💳 Kartadan toʻlov']:
            payment_method = 'card'
        else:
            if language == 'uz':
                self.bot.send_message(chat_id, "❌ Taklif qilingan to‘lov usulini tanlang")
            else:
                self.bot.send_message(chat_id, "❌ Выберите способ оплаты из предложенных")
            return

        total_amount = calculate_cart_total(cart_items)
        order_data = getattr(self, 'order_data', {}).get(telegram_id, {})
        delivery_address = order_data.get('address', 'Не указан')

        order_id = self.db.create_order(
            user_id,
            total_amount,
            delivery_address,
            payment_method,
            order_data.get('lat'),
            order_data.get('lon')
        )

        if order_id:
            self.db.add_order_items(order_id, cart_items)
            self.db.clear_cart(user_id)

            points_earned = int(total_amount * 0.05)
            self.db.update_loyalty_points(user_id, points_earned)

            if language == 'uz':
                success_text = f"✅ <b>Buyurtma #{order_id} rasmiylashtirildi!</b>\n\n"
                success_text += f"💰 Summa: {format_price(total_amount)}\n"
                success_text += f"📍 Manzil: {delivery_address}\n"
                success_text += f"💳 To‘lov: {payment_method}\n"
                success_text += f"⭐ Ballar qo‘shildi: {points_earned}\n\n"
                if payment_method == 'card':
                    success_text += "📞 Karta to‘lovi tasdig‘i uchun 10 daqiqada bog‘lanamiz"
                else:
                    success_text += "📞 10 daqiqa ichida siz bilan bogʻlanamiz"
            else:
                success_text = f"✅ <b>Заказ #{order_id} оформлен!</b>\n\n"
                success_text += f"💰 Сумма: {format_price(total_amount)}\n"
                success_text += f"📍 Адрес: {delivery_address}\n"
                success_text += f"💳 Оплата: {payment_method}\n"
                success_text += f"⭐ Начислено баллов: {points_earned}\n\n"
                if payment_method == 'card':
                    success_text += "📞 Мы свяжемся с вами в течение 10 минут для подтверждения оплаты картой"
                else:
                    success_text += "📞 Мы свяжемся с вами в течение 10 минут"

            self.bot.send_message(chat_id, success_text, create_main_keyboard(language))

            if self.notification_manager:
                self.notification_manager.send_order_notification_to_admins(order_id)

            if hasattr(self, 'order_data') and telegram_id in self.order_data:
                del self.order_data[telegram_id]
        else:
            self.bot.send_message(chat_id, "❌ Ошибка создания заказа")

    def clear_cart(self, message):
        """Очистка корзины пользователя"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return

        user_id = user_data[0][0]
        language = user_data[0][5] or 'ru'

        self.db.clear_cart(user_id)

        if language == 'uz':
            text = "🧹 Savat tozalandi."
        else:
            text = "🧹 Корзина очищена."

        self.bot.send_message(chat_id, text, create_main_keyboard(language))

    def handle_clear_cart_confirmation(self, message, state_value):
        """Обработка подтверждения очистки корзины"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        try:
            user_id_str = state_value.split('confirm_clear_cart_', 1)[1]
            user_id = int(user_id_str)
        except Exception:
            user_id = None

        text = message.get('text', '')
        if text == '✅ Да' and user_id:
            try:
                self.db.clear_cart(user_id)
            except Exception:
                pass
            self.user_states.pop(telegram_id, None)
            self.bot.send_message(chat_id, "🧹 Корзина очищена.")
        elif text == '❌ Нет':
            self.user_states.pop(telegram_id, None)
            self.show_cart(message)
        else:
            self.bot.send_message(chat_id, 'Нажмите «✅ Да» или «❌ Нет».')

    def show_loyalty_program(self, message):
        """Показ программы лояльности"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return

        user_id = user_data[0][0]
        loyalty_data = self.db.get_user_loyalty_points(user_id)

        loyalty_text = "⭐ <b>Программа лояльности</b>\n\n"
        loyalty_text += f"💎 Ваш уровень: <b>{loyalty_data[3]}</b>\n"
        loyalty_text += f"🏆 Текущие баллы: {loyalty_data[1]}\n"
        loyalty_text += f"📊 Всего заработано: {loyalty_data[2]}\n\n"
        loyalty_text += "🏅 <b>Уровни лояльности:</b>\n"
        loyalty_text += "🥉 Bronze (0+ баллов) - 0% скидка\n"
        loyalty_text += "🥈 Silver (100+ баллов) - 5% скидка\n"
        loyalty_text += "🥇 Gold (500+ баллов) - 10% скидка\n"
        loyalty_text += "💎 Platinum (1500+ баллов) - 15% скидка\n"
        loyalty_text += "💍 Diamond (5000+ баллов) - 20% скидка\n\n"
        loyalty_text += "💡 Зарабатывайте 5% с каждой покупки!"

        language = user_data[0][5] or 'ru'
        self.bot.send_message(chat_id, loyalty_text, create_back_keyboard(language=language))

    def show_available_promos(self, message):
        """Показ доступных промокодов"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return

        user_id = user_data[0][0]

        try:
            from promotions import PromotionManager
            promo_manager = PromotionManager(self.db)
            available_promos = promo_manager.get_user_available_promos(user_id)

            if available_promos:
                promos_text = "🎁 <b>Доступные промокоды:</b>\n\n"

                for promo in available_promos:
                    promos_text += f"🏷 <b>{promo[1]}</b>\n"

                    if promo[2] == 'percentage':
                        promos_text += f"💰 Скидка: {promo[3]}%\n"
                    else:
                        promos_text += f"💰 Скидка: {format_price(promo[3])}\n"

                    if promo[4] > 0:
                        promos_text += f"📊 Минимальная сумма: {format_price(promo[4])}\n"

                    if promo[6]:
                        promos_text += f"⏰ Действует до: {format_date(promo[6])}\n"

                    promos_text += f"📝 {promo[7]}\n\n"

                promos_text += "💡 Используйте промокод при оформлении заказа"
            else:
                promos_text = "🎁 <b>Промокоды</b>\n\n"
                promos_text += "❌ Нет доступных промокодов\n\n"
                promos_text += "💡 Следите за акциями в нашем канале!"

            language = user_data[0][5] or 'ru'
            self.bot.send_message(chat_id, promos_text, create_back_keyboard(language=language))

        except Exception as e:
            logger.error(f"Ошибка показа промокодов: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка получения промокодов")

    def start_language_change(self, message):
        """Начало смены языка"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        text = "🌍 Выберите язык / Tilni tanlang:"
        self.bot.send_message(chat_id, text, create_language_keyboard())

        self.user_states[telegram_id] = 'changing_language'

    def handle_language_change(self, message):
        """Обработка смены языка"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        if text == '❌ Отмена':
            self.user_states.pop(telegram_id, None)
            self.show_main_menu(message)
            return

        if text == '🇷🇺 Русский':
            new_language = 'ru'
        elif text == "🇺🇿 O'zbekcha":
            new_language = 'uz'
        else:
            self.bot.send_message(chat_id, "❌ Выберите язык из предложенных")
            return

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if user_data:
            user_id = user_data[0][0]
            self.db.update_user_language(user_id, new_language)

            success_text = t('language_changed', language=new_language)
            self.bot.send_message(chat_id, success_text, create_main_keyboard(new_language))

        self.user_states.pop(telegram_id, None)

    def handle_order_command(self, message):
        """Обработка команды просмотра заказа"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        try:
            order_id = int(text.split('_')[1])

            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return

            user_id = user_data[0][0]
            order = self.db.execute_query(
                'SELECT * FROM orders WHERE id = ? AND user_id = ?',
                (order_id, user_id)
            )

            if order:
                order_details = self.db.get_order_details(order_id)
                self.show_detailed_order(chat_id, order_details)
            else:
                self.bot.send_message(chat_id, f"❌ Заказ #{order_id} не найден")

        except (ValueError, IndexError):
            self.bot.send_message(chat_id, "❌ Неверный номер заказа")

    def show_detailed_order(self, chat_id, order_details):
        """Показ подробной информации о заказе"""
        order = order_details['order']
        items = order_details['items']

        status_emoji = get_order_status_emoji(order[3])
        status_text = get_order_status_text(order[3])

        details_text = f"📋 <b>Заказ #{order[0]}</b>\n\n"
        details_text += f"📊 Статус: {status_emoji} {status_text}\n"
        details_text += f"💰 Сумма: {format_price(order[2])}\n"
        details_text += f"📅 Дата: {format_date(order[7])}\n"
        details_text += f"📍 Адрес: {order[4]}\n"
        details_text += f"💳 Оплата: {order[5]}\n\n"

        details_text += "🛍 <b>Товары:</b>\n"
        for item in items:
            details_text += f"• {item[2]} × {item[0]} = {format_price(item[1] * item[0])}\n"

        if order[6] > 0:
            details_text += f"\n🎁 Скидка: -{format_price(order[6])}"

        self.bot.send_message(chat_id, details_text, create_order_details_keyboard(order[0]))

    def handle_track_command(self, message):
        """Обработка команды отслеживания"""
        text = message.get('text', '')
        chat_id = message['chat']['id']

        try:
            tracking_number = text.split('_')[1]

            if hasattr(self.bot, 'logistics_manager'):
                tracking_info = self.bot.logistics_manager.track_shipment(tracking_number)

                if tracking_info:
                    track_text = "📦 <b>Отслеживание посылки</b>\n\n"
                    track_text += f"🏷 Трек-номер: {tracking_number}\n"
                    track_text += f"📊 Статус: {tracking_info['current_status']}\n"
                    track_text += f"📅 Ожидаемая доставка: {format_date(tracking_info['estimated_delivery'])}\n\n"

                    track_text += "📋 <b>История:</b>\n"
                    for event in tracking_info['history']:
                        track_text += f"• {event['description']} ({event['location']})\n"
                        track_text += f"  📅 {format_date(event['timestamp'])}\n"

                    self.bot.send_message(chat_id, track_text)
                else:
                    self.bot.send_message(chat_id, f"❌ Посылка с номером {tracking_number} не найдена")
            else:
                self.bot.send_message(chat_id, "❌ Система отслеживания временно недоступна")

        except (ValueError, IndexError):
            self.bot.send_message(chat_id, "❌ Неверный формат трек-номера")

    def handle_promo_command(self, message):
        """Обработка команды промокода"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        try:
            promo_code = text.split('_')[1].upper()

            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return

            user_id = user_data[0][0]
            cart_items = self.db.get_cart_items(user_id)

            if not cart_items:
                self.bot.send_message(chat_id, "❌ Добавьте товары в корзину для применения промокода")
                return

            cart_total = calculate_cart_total(cart_items)

            from promotions import PromotionManager
            promo_manager = PromotionManager(self.db)
            validation = promo_manager.validate_promo_code(promo_code, user_id, cart_total)

            if validation['valid']:
                promo_text = "🎁 <b>Промокод применен!</b>\n\n"
                promo_text += f"🏷 Код: {promo_code}\n"
                promo_text += f"💰 Скидка: {format_price(validation['discount_amount'])}\n"
                promo_text += f"📊 Новая сумма: {format_price(cart_total - validation['discount_amount'])}\n\n"
                promo_text += "🛒 Оформите заказ чтобы зафиксировать скидку"

                self.bot.send_message(chat_id, promo_text)
            else:
                self.bot.send_message(chat_id, f"❌ {validation['error']}")

        except (ValueError, IndexError):
            self.bot.send_message(chat_id, "❌ Неверный формат промокода")
        except Exception as e:
            logger.error(f"Ошибка применения промокода: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка применения промокода")

    def handle_restore_command(self, message):
        """Обработка команды восстановления заказа"""
        text = message.get('text', '')
        chat_id = message['chat']['id']

        try:
            restore_id = text.split('_')[1]

            restore_text = "💾 <b>Восстановление заказа</b>\n\n"
            restore_text += f"🔍 ID для восстановления: {restore_id}\n\n"
            restore_text += "💡 Функция восстановления будет добавлена в следующей версии"

            self.bot.send_message(chat_id, restore_text)

        except (ValueError, IndexError):
            self.bot.send_message(chat_id, "❌ Неверный ID для восстановления")

    def show_user_notifications(self, message):
        """Показ уведомлений пользователя"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']

        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return

        user_id = user_data[0][0]
        notifications = self.db.get_unread_notifications(user_id)

        if not notifications:
            self.bot.send_message(chat_id, "🔔 У вас нет новых уведомлений")
            return

        for notif in notifications:
            type_emoji = {
                'order': '📦',
                'order_status': '📋',
                'promotion': '🎁',
                'system': '⚙️',
                'info': 'ℹ️'
            }.get(notif[4], 'ℹ️')

            notif_text = f"{type_emoji} <b>{notif[2]}</b>\n\n"
            notif_text += f"{notif[3]}\n\n"
            notif_text += f"📅 {format_date(notif[6])}"

            self.bot.send_message(chat_id, notif_text)
            self.db.mark_notification_read(notif[0])

    def handle_callback_query(self, callback_query):
        """Обработка callback запросов"""
        try:
            data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']

            if data == 'back_to_categories':
                msg = {'chat': {'id': chat_id}}
                self.show_catalog(msg)
            elif data.startswith('back_to_category_'):
                try:
                    cid = int(data.split('_')[-1])
                except Exception:
                    cid = None
                if cid:
                    cat_row = self.db.execute_query('SELECT name FROM categories WHERE id=?', (cid,))
                    name = cat_row[0][0] if cat_row else ''
                    subs = self.db.get_subcategories_by_category(cid)
                    if subs:
                        self.bot.send_message(
                            chat_id,
                            f"📂 <b>{name}</b>\n\nВыберите бренд или подкатегорию:",
                            create_subcategories_keyboard(subs, cid)
                        )
                    else:
                        self.bot.send_message(chat_id, f"❌ В категории '{name}' пока нет товаров")
                else:
                    msg = {'chat': {'id': chat_id}}
                    self.show_catalog(msg)
            elif data == 'go_to_cart':
                msg = {'chat': {'id': chat_id}, 'from': {'id': telegram_id}}
                self.show_cart(msg)
            elif data.startswith('back_to_subcategory_'):
                try:
                    sid = int(data.split('_')[-1])
                except Exception:
                    sid = None
                if sid:
                    sub_row = self.db.execute_query('SELECT name FROM subcategories WHERE id=?', (sid,))
                    subname = sub_row[0][0] if sub_row else 'Подкатегория'
                    products = self.db.get_products_by_subcategory(sid)
                    if products:
                        self.bot.send_message(
                            chat_id,
                            f"🛍 <b>{subname}</b>\n\nВыберите товар:",
                            create_products_keyboard(products, language='ru')
                        )
                    else:
                        self.bot.send_message(chat_id, f"❌ В подкатегории '{subname}' пока нет товаров")
                else:
                    msg = {'chat': {'id': chat_id}}
                    self.show_catalog(msg)
            elif data.startswith('qty_inc_') or data.startswith('qty_dec_'):
                parts = data.split('_')
                try:
                    pid = int(parts[2])
                    qty = int(parts[3])
                except (ValueError, IndexError):
                    return
                new_qty = qty + 1 if data.startswith('qty_inc_') else max(1, qty - 1)
                kb = create_product_inline_keyboard(pid, None, None, new_qty)
                message_id = callback_query['message']['message_id']
                self.bot.edit_message_reply_markup(chat_id, message_id, kb)
            elif data.startswith('add_to_cart_'):
                self.handle_add_to_cart(callback_query)
            elif data.startswith('add_to_favorites_'):
                self.handle_add_to_favorites(callback_query)
            elif data.startswith('reviews_'):
                self.handle_show_reviews(callback_query)
            elif data.startswith('rate_product_'):
                self.handle_rate_product(callback_query)
            elif data.startswith('cart_'):
                self.handle_cart_action(callback_query)
            elif data.startswith('pay_'):
                self.handle_payment_selection(callback_query)
            elif data == 'cancel_payment':
                self.bot.send_message(chat_id, "❌ Оплата отменена")
            elif data == 'back_to_main':
                msg = {'chat': {'id': chat_id}, 'from': {'id': telegram_id}}
                self.show_main_menu(msg)

        except Exception as e:
            logger.error(f"Ошибка обработки callback: {e}")

    def handle_add_to_cart(self, callback_query):
        """Добавление товара в корзину"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        telegram_id = callback_query['from']['id']

        try:
            parts = data.split('_')
            product_id = int(parts[2])
            quantity = int(parts[3]) if len(parts) > 3 else 1
        except (ValueError, IndexError):
            self.bot.send_message(chat_id, "❌ Ошибка добавления товара")
            return

        user = self.db.get_user_by_telegram_id(telegram_id)
        if not user:
            return
        user_id = user[0][0]

        success = self.db.add_to_cart(user_id, product_id, max(1, quantity))
        if success:
            product = self.db.get_product_by_id(product_id)
            title = product[1] if product else 'Товар'
            language = user[0][5] or 'ru'
            if language == 'uz':
                text = f"✅ <b>{title}</b> savatga qo‘shildi (×{max(1, quantity)})!"
                btn_cart = '🛒 Savatga o‘tish'
                btn_more = '🛍 Xaridni davom ettirish'
            else:
                text = f"✅ <b>{title}</b> добавлен в корзину (×{max(1, quantity)})!"
                btn_cart = '🛒 Перейти в корзину'
                btn_more = '🛍 Продолжить покупки'

            self.bot.send_message(
                chat_id,
                text,
                {
                    'inline_keyboard': [[
                        {'text': btn_cart, 'callback_data': 'go_to_cart'},
                        {'text': btn_more, 'callback_data': 'back_to_categories'}
                    ]]
                }
            )
        else:
            self.bot.send_message(chat_id, "❌ Товар недоступен или закончился")

    def handle_add_to_favorites(self, callback_query):
        """Добавление в избранное"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        telegram_id = callback_query['from']['id']

        try:
            product_id = int(data.split('_')[3])

            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return

            user_id = user_data[0][0]
            language = user_data[0][5] or 'ru'

            result = self.db.add_to_favorites(user_id, product_id)

            if result:
                product = self.db.get_product_by_id(product_id)
                if language == 'uz':
                    text = f"❤️ {product[1]} sevimlilarga qo‘shildi!"
                else:
                    text = f"❤️ {product[1]} добавлен в избранное!"
                self.bot.send_message(chat_id, text)
            else:
                if language == 'uz':
                    self.bot.send_message(chat_id, "❌ Sevimlilarga qo‘shishda xato")
                else:
                    self.bot.send_message(chat_id, "❌ Ошибка добавления в избранное")

        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка добавления в избранное: {e}")

    def handle_show_reviews(self, callback_query):
        """Показ отзывов о товаре"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']

        try:
            product_id = int(data.split('_')[1])

            reviews = self.db.get_product_reviews(product_id)
            product = self.db.get_product_by_id(product_id)

            reviews_text = f"⭐ <b>Отзывы о товаре:</b>\n{product[1]}\n\n"

            if reviews:
                for review in reviews[:5]:
                    stars = create_stars_display(review[0])
                    reviews_text += f"{stars} <b>{review[3]}</b>\n"
                    if review[1]:
                        reviews_text += f"💭 {review[1]}\n"
                    reviews_text += f"📅 {format_date(review[2])}\n\n"

                if len(reviews) > 5:
                    reviews_text += f"... и еще {len(reviews) - 5} отзывов"
            else:
                reviews_text += "❌ Пока нет отзывов\n\n"
                reviews_text += "💡 Станьте первым, кто оставит отзыв!"

            self.bot.send_message(chat_id, reviews_text)

        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка показа отзывов: {e}")

    def handle_rate_product(self, callback_query):
        """Обработка оценки товара"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        telegram_id = callback_query['from']['id']

        try:
            parts = data.split('_')
            product_id = int(parts[1])
            rating = int(parts[2])

            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return

            user_id = user_data[0][0]

            purchased = self.db.execute_query('''
                SELECT COUNT(*) FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE o.user_id = ? AND oi.product_id = ? AND o.status != 'cancelled'
            ''', (user_id, product_id))[0][0]

            if purchased == 0:
                self.bot.send_message(chat_id, "❌ Вы можете оценивать только купленные товары")
                return

            self.db.add_review(user_id, product_id, rating, "")

            stars = '⭐' * rating
            self.bot.send_message(chat_id, f"✅ Спасибо за оценку! {stars}")

        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка оценки товара: {e}")

    def handle_cart_action(self, callback_query):
        """Обработка действий с корзиной"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']

        try:
            action = data.split('_')[1]
            cart_item_id = int(data.split('_')[2])

            if action == 'increase':
                current_quantity = self.get_cart_item_quantity(cart_item_id)
                self.db.update_cart_quantity(cart_item_id, current_quantity + 1)
                self.update_cart_message(callback_query, cart_item_id)

            elif action == 'decrease':
                current_quantity = self.get_cart_item_quantity(cart_item_id)
                if current_quantity > 1:
                    self.db.update_cart_quantity(cart_item_id, current_quantity - 1)
                    self.update_cart_message(callback_query, cart_item_id)
                else:
                    self.bot.send_message(chat_id, "❌ Минимальное количество: 1")

            elif action == 'remove':
                self.db.remove_from_cart(cart_item_id)
                self.bot.send_message(chat_id, "🗑 Товар удален из корзины")

        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка действия с корзиной: {e}")

    def get_cart_item_quantity(self, cart_item_id):
        """Получение количества товара в корзине"""
        result = self.db.execute_query(
            'SELECT quantity FROM cart WHERE id = ?',
            (cart_item_id,)
        )
        return result[0][0] if result else 1

    def update_cart_message(self, callback_query, cart_item_id):
        """Обновление сообщения корзины"""
        try:
            new_quantity = self.get_cart_item_quantity(cart_item_id)
            new_keyboard = create_cart_item_keyboard(cart_item_id, new_quantity)

            self.bot.edit_message_reply_markup(
                callback_query['message']['chat']['id'],
                callback_query['message']['message_id'],
                new_keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка обновления сообщения корзины: {e}")

    def handle_payment_selection(self, callback_query):
        """Обработка выбора способа оплаты (inline)"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        telegram_id = callback_query['from']['id']

        try:
            parts = data.split('_')
            provider = parts[1]
            order_id = int(parts[2])

            if provider == 'cash':
                self.bot.send_message(
                    chat_id,
                    f"💵 <b>Оплата наличными</b>\n\nЗаказ #{order_id} будет оплачен при получении.\n\n📞 Мы свяжемся с вами для подтверждения."
                )
            else:
                amount = float(parts[3])

                user_data = self.db.get_user_by_telegram_id(telegram_id)
                payment_result = self.payment_processor.create_payment(
                    provider, amount, order_id, {
                        'telegram_id': telegram_id,
                        'name': user_data[0][2] if user_data else '',
                        'phone': user_data[0][3] if user_data else '',
                        'email': user_data[0][4] if user_data else ''
                    }
                )

                if payment_result:
                    payment_info = format_payment_info(payment_result)
                    self.bot.send_message(chat_id, payment_info)
                else:
                    self.bot.send_message(chat_id, "❌ Ошибка создания платежа")

        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка обработки платежа: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка обработки платежа")

    def handle_unknown_command(self, message, language='ru'):
        """Обработка неизвестной команды"""
        chat_id = message['chat']['id']
        text = message.get('text', '')

        if len(text) > 2 and not text.startswith('/'):
            products = self.db.search_products(text, 5)

            if products:
                if language == 'uz':
                    search_text = f"🔍 '{text}' bo‘yicha topildi:\n\n"
                else:
                    search_text = f"🔍 Найдено по запросу '{text}':\n\n"

                for product in products:
                    search_text += f"🛍 {product[1]} - {format_price(product[3])}\n"

                if language == 'uz':
                    search_text += "\n💡 Kengaytirilgan qidiruv uchun 🔍 Qidiruvdan foydalaning"
                else:
                    search_text += "\n💡 Используйте 🔍 Поиск для расширенного поиска"

                self.bot.send_message(chat_id, search_text, create_main_keyboard(language))
                return

        telegram_id = message['from']['id']
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        lang = user_data[0][5] if user_data else 'ru'

        if lang == 'uz':
            unknown_text = "❓ Buyruq tanilmadi\n\n"
            unknown_text += "💡 Menyu tugmalaridan yoki komandlardan foydalaning:\n"
            unknown_text += "• /help - yordam\n"
            unknown_text += "• /start - bosh menyu\n"
            unknown_text += "• 🛍 Katalog - tovarlarni ko‘rish"
        else:
            unknown_text = "❓ Команда не распознана\n\n"
            unknown_text += "💡 Используйте кнопки меню или команды:\n"
            unknown_text += "• /help - справка\n"
            unknown_text += "• /start - главное меню\n"
            unknown_text += "• 🛍 Каталог - просмотр товаров"

        self.bot.send_message(chat_id, unknown_text, create_main_keyboard(lang))


# Дополнительные обработчики продавца (если они есть в твоей БД):

def start_seller_application(self, message):
    """Начало заявки на продавца"""
    chat_id = message['chat']['id']
    telegram_id = message['from']['id']

    user_data = self.db.get_user_by_telegram_id(telegram_id)
    language = user_data[0][5] if user_data else 'ru'

    if language == 'uz':
        text = (
            "🧑‍💼 <b>Sotuvchi bo‘lish uchun ariza</b>\n\n"
            "Ismingizni kiriting:"
        )
    else:
        text = (
            "🧑‍💼 <b>Заявка на продавца</b>\n\n"
            "Введите ваше имя:"
        )

    self.bot.send_message(chat_id, text)
    self.user_states[telegram_id] = 'seller_name'


def handle_seller_name(self, message):
    """Обработка имени продавца"""
    chat_id = message['chat']['id']
    telegram_id = message['from']['id']
    text = message.get('text', '').strip()

    user_data = self.db.get_user_by_telegram_id(telegram_id)
    language = user_data[0][5] if user_data else 'ru'

    if len(text) < 2:
        if language == 'uz':
            self.bot.send_message(chat_id, "❌ Ism juda qisqa. Yana urinib ko‘ring:")
        else:
            self.bot.send_message(chat_id, "❌ Имя слишком короткое. Попробуйте еще раз:")
        return

    if not hasattr(self, 'seller_data'):
        self.seller_data = {}
    self.seller_data[telegram_id] = {'name': text}

    if language == 'uz':
        prompt = "📱 Telefon raqamingizni kiriting:"
    else:
        prompt = "📱 Введите ваш номер телефона:"

    self.bot.send_message(chat_id, prompt)
    self.user_states[telegram_id] = 'seller_phone'


def handle_seller_phone(self, message):
    """Обработка телефона продавца"""
    chat_id = message['chat']['id']
    telegram_id = message['from']['id']
    text = message.get('text', '').strip()

    user_data = self.db.get_user_by_telegram_id(telegram_id)
    language = user_data[0][5] if user_data else 'ru'

    phone = validate_phone(text)
    if not phone:
        if language == 'uz':
            self.bot.send_message(chat_id, "❌ Telefon formati noto‘g‘ri. Yana urinib ko‘ring:")
        else:
            self.bot.send_message(chat_id, "❌ Неверный формат телефона. Попробуйте еще раз:")
        return

    self.seller_data[telegram_id]['phone'] = phone

    if language == 'uz':
        prompt = "🏷 Brendingiz yoki do‘kon nomini kiriting:"
    else:
        prompt = "🏷 Введите название бренда или магазина:"

    self.bot.send_message(chat_id, prompt)
    self.user_states[telegram_id] = 'seller_brand'


def handle_seller_brand(self, message):
    """Обработка бренда продавца"""
    chat_id = message['chat']['id']
    telegram_id = message['from']['id']
    text = message.get('text', '').strip()

    user_data = self.db.get_user_by_telegram_id(telegram_id)
    language = user_data[0][5] if user_data else 'ru'

    if len(text) < 2:
        if language == 'uz':
            self.bot.send_message(chat_id, "❌ Nom juda qisqa. Yana urinib ko‘ring:")
        else:
            self.bot.send_message(chat_id, "❌ Название слишком короткое. Попробуйте еще раз:")
        return

    self.seller_data[telegram_id]['brand'] = text

    if language == 'uz':
        prompt = "📦 Qaysi tovarlarni sotmoqchisiz? Qisqacha yozing:"
    else:
        prompt = "📦 Какие товары вы хотите продавать? Опишите коротко:"

    self.bot.send_message(chat_id, prompt)
    self.user_states[telegram_id] = 'seller_products'


def handle_seller_products(self, message):
    """Завершение заявки продавца"""
    chat_id = message['chat']['id']
    telegram_id = message['from']['id']
    text = message.get('text', '').strip()

    user_data = self.db.get_user_by_telegram_id(telegram_id)
    language = user_data[0][5] if user_data else 'ru'

    self.seller_data[telegram_id]['products'] = text

    data = self.seller_data[telegram_id]

    self.db.save_seller_application(
        telegram_id,
        data['name'],
        data['phone'],
        data['brand'],
        data['products']
    )

    if language == 'uz':
        final_text = (
            "✅ <b>Arizangiz yuborildi!</b>\n\n"
            "Biz ma'lumotlaringizni ko‘rib chiqamiz va tez orada siz bilan bog‘lanamiz."
        )
    else:
        final_text = (
            "✅ <b>Ваша заявка отправлена!</b>\n\n"
            "Мы рассмотрим ваши данные и свяжемся с вами в ближайшее время."
        )

    self.bot.send_message(chat_id, final_text, create_main_keyboard(language))

    self.user_states.pop(telegram_id, None)
    del self.seller_data[telegram_id]


# Привязка функций к классу
MessageHandler.start_seller_application = start_seller_application
MessageHandler.handle_seller_name = handle_seller_name
MessageHandler.handle_seller_phone = handle_seller_phone
MessageHandler.handle_seller_brand = handle_seller_brand
MessageHandler.handle_seller_products = handle_seller_products
