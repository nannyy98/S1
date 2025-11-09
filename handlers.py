"""
Обработчики сообщений для телеграм-бота
"""

import logging
from utils import validate_phone, validate_email
from datetime import datetime
from keyboards import (
    create_main_keyboard, create_categories_keyboard, create_subcategories_keyboard,
    create_products_keyboard, create_product_inline_keyboard, create_cart_keyboard,
    create_registration_keyboard, create_order_keyboard, create_back_keyboard,
    create_confirmation_keyboard, create_search_filters_keyboard,
    create_price_filter_keyboard, create_rating_keyboard,
    create_order_details_keyboard, create_language_keyboard,
    create_payment_methods_keyboard, create_cart_item_keyboard
)
from keyboards import create_product_inline_keyboard_with_qty
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

    def _extract_label_name(self, text: str) -> str:
        """Возвращает часть после первого пробела: '🍎 Фрукты' -> 'Фрукты'"""
        if not text:
            return ''
        parts = text.split(' ', 1)
        return parts[1].strip() if len(parts) > 1 else text.strip()

    def _is_category_label(self, text: str) -> bool:
        name = self._extract_label_name(text)
        if not name:
            return False
        rows = self.db.execute_query('SELECT id FROM categories WHERE name = ? AND is_active = 1', (name,))
        return bool(rows)

    def _is_subcategory_label(self, text: str) -> bool:
        name = self._extract_label_name(text)
        if not name:
            return False
        rows = self.db.execute_query('SELECT id FROM subcategories WHERE name = ? AND is_active = 1', (name,))
        return bool(rows)

    
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
            elif text in ['📞 Связаться с нами', '📞 Biz bilan bog\'lanish']:
                self.handle_contact_request(message, user_language)
            elif text == '🔙 Главная' or text == '🏠 Главная' or text == '🏠 Bosh sahifa':
                self.show_main_menu(message)
            elif text == '🌍 Сменить язык':
                self.start_language_change(message)
            
            # Обрабатываем выбор категории
            elif self._is_category_label(text):
                self.handle_category_selection(message)
            
            # Обрабатываем выбор подкатегории/бренда
            elif self._is_subcategory_label(text):
                self.handle_subcategory_selection(message)
            
            # Обрабатываем выбор товара
            elif text.startswith('🛍 '):
                self.handle_product_selection(message)
            
            # Обрабатываем поиск
            elif telegram_id in self.user_states and self.user_states[telegram_id] == 'searching':
                self.handle_search_query(message)
            
            # Обрабатываем оформление заказа
            elif text == '📦 Оформить заказ':
                self.start_order_process(message)
            elif text in ['💳 Оплата картой', '💳 Kartadan toʻlov', '💵 Наличными при получении', '💵 Qabul qilishda naqd']:
                self.handle_payment_method_selection(message)
            
            # Обрабатываем управление корзиной
            elif text == '🗑 Очистить корзину':
                self.clear_user_cart(message)
            elif text == '➕ Добавить товары' or text == '🛍 Перейти в каталог':
                self.show_catalog(message)
            
            # Неизвестная команда
            else:
                self.handle_unknown_command(message, user_language)
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
            self.bot.send_message(message['chat']['id'], "❌ Произошла ошибка. Попробуйте еще раз.")
    
    def handle_start_command(self, message):
        """Обработка команды /start"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        # Проверяем регистрацию
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        
        if user_data:
            # Пользователь уже зарегистрирован
            user_language = user_data[0][5] or 'ru'
            welcome_text = t('welcome_back', language=user_language)
            self.bot.send_message(chat_id, welcome_text, create_main_keyboard(user_language))
        else:
            # Новый пользователь - начинаем регистрацию
            self.start_registration(message)
    
    def start_registration(self, message):
        """Начало процесса регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        # Получаем имя из Telegram
        suggested_name = message['from'].get('first_name', '')
        if message['from'].get('last_name'):
            suggested_name += f" {message['from']['last_name']}"
        
        welcome_text = t('welcome_new')
        self.bot.send_message(chat_id, welcome_text)
        
        # Запрашиваем имя
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
        elif state == 'order_phone':
            self.handle_order_phone(message)
        elif state == 'order_address':
            self.handle_order_address(message)
        elif state == 'changing_language':
            self.handle_language_change(message)
        elif state.startswith('rating_product_'):
            self.handle_product_rating(message)
        elif state and isinstance(state, str) and state.startswith('confirm_clear_cart_'):
            user_id_str = state.split('confirm_clear_cart_', 1)[1]
            try:
                user_id = int(user_id_str)
            except Exception:
                user_id = None
            text = message.get('text', '')
            if text == '✅ Да' and user_id:
                try:
                    self.db.clear_cart(user_id)
                except Exception:
                    pass
                # сбрасываем состояние
                self.user_states.pop(telegram_id, None)
                # показываем пустую корзину
                empty_text = "🧹 Корзина очищена."
                try:
                    lang = self.db.get_user_by_telegram_id(telegram_id)[0][5]
                except Exception:
                    lang = 'ru'
                self.bot.send_message(message['chat']['id'], empty_text, create_main_keyboard(lang))
                return
            elif text == '❌ Нет':
                self.user_states.pop(telegram_id, None)
                self.show_cart(message)
                return
            else:
                self.bot.send_message(message['chat']['id'], 'Нажмите «✅ Да» или «❌ Нет».')
                return
    
    def handle_order_phone(self, message):
        """Приём номера телефона (контактом или текстом) в процессе оформления заказа"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        # Контакт от Telegram
        if 'contact' in message and isinstance(message['contact'], dict):
            phone = message['contact'].get('phone_number')
        else:
            phone = message.get('text', '').strip()
        if not phone or len(phone) < 5:
            self.bot.send_message(chat_id, '❗ Введите корректный номер телефона или нажмите кнопку для отправки контакта')
            return
        try:
            self.db.update_user_phone_by_telegram_id(telegram_id, phone)
        except Exception as e:
            logger.info(f'[order_phone] save phone warn: {e}')
        # После сохранения номера — запрашиваем адрес
        from keyboards import create_address_location_keyboard
        self.user_states[telegram_id] = 'order_address'
        self.bot.send_message(chat_id, '📍 Укажите адрес доставки (улица, дом, ориентир)', create_address_location_keyboard())

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
        
        # Сохраняем имя и переходим к телефону
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
        """Обработка выбора языка"""
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
        
        # Завершаем регистрацию
        reg_data = self.registration_data.get(telegram_id, {})
        
        user_id = self.db.add_user(
            telegram_id,
            reg_data.get('name', 'Пользователь'),
            reg_data.get('phone'),
            reg_data.get('email'),
            language
        )
        
        if user_id:
            # Создаем запись баллов лояльности
            self.db.execute_query(
                'INSERT OR IGNORE INTO loyalty_points (user_id) VALUES (?)',
                (user_id,)
            )
            
            # Приветственное сообщение
            welcome_complete = t('registration_complete', language=language)
            self.bot.send_message(chat_id, welcome_complete, create_main_keyboard(language))
            
            # Создаем приветственную серию если есть автоматизация
            if hasattr(self.bot, 'marketing_automation') and self.bot.marketing_automation:
                self.bot.marketing_automation.create_welcome_series(user_id)
        else:
            self.bot.send_message(chat_id, "❌ Ошибка регистрации. Попробуйте позже.")
        
        # Очищаем состояние
        del self.user_states[telegram_id]
        if hasattr(self, 'registration_data') and telegram_id in self.registration_data:
            del self.registration_data[telegram_id]
    
    def send_registration_prompt(self, chat_id):
        """Приглашение к регистрации"""
        prompt_text = "👋 Добро пожаловать!\n\nДля использования бота необходимо пройти регистрацию.\n\nНажмите /start для начала."
        self.bot.send_message(chat_id, prompt_text)
    
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
                    {'text': '📱 Позвонить', 'url': f'tel:{CONTACT_INFO["call_center_phone"]}'},
                    {'text': '💬 Telegram', 'url': f'https://t.me/{CONTACT_INFO["support_telegram"].replace("@", "")}'}
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
    
    def handle_category_selection(self, message):
        """Обработка выбора категории"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        
        # Извлекаем название категории
        category_name = text.split(' ', 1)[-1].strip()  # Убираем эмодзи
        
        # Находим категорию в базе
        category = self.db.execute_query(
            'SELECT id FROM categories WHERE name = ? AND is_active = 1',
            (category_name,)
        )
        
        if category:
            category_id = category[0][0]
            
            # Получаем подкатегории/бренды
            subcategories = self.db.get_products_by_category(category_id)
            
            if subcategories:
                subcategory_text = f"📂 <b>{category_name}</b>\n\nВыберите бренд или подкатегорию:"
                self.bot.send_message(chat_id, subcategory_text, create_subcategories_keyboard(subcategories))
            else:
                # Если подкатегорий с товарами нет — показываем товары прямо из категории
                products = self.db.execute_query(
                    'SELECT * FROM products WHERE category_id = ? AND is_active = 1 ORDER BY name LIMIT 30',
                    (category_id,)
                )
                if products:
                    products_text = f"🛍 <b>{category_name}</b>\n\nВыберите товар:"
                    self.bot.send_message(chat_id, products_text, create_products_keyboard(products, show_back=True))
                else:
                    self.bot.send_message(chat_id, f"❌ В категории '{category_name}' пока нет товаров")
        else:
            self.bot.send_message(chat_id, "❌ Категория не найдена")
    
    def handle_subcategory_selection(self, message):
        """Обработка выбора подкатегории"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        
        # Извлекаем название подкатегории
        subcategory_name = text.split(' ', 1)[-1].strip()  # Убираем эмодзи
        
        # Находим подкатегорию
        subcategory = self.db.execute_query(
            'SELECT id FROM subcategories WHERE name = ? AND is_active = 1',
            (subcategory_name,)
        )
        
        if subcategory:
            subcategory_id = subcategory[0][0]
            
            # Получаем товары подкатегории
            products = self.db.get_products_by_subcategory(subcategory_id)
            
            if products:
                products_text = f"🛍 <b>{subcategory_name}</b>\n\nВыберите товар:"
                self.bot.send_message(chat_id, products_text, create_products_keyboard(products))
            else:
                self.bot.send_message(chat_id, f"❌ В подкатегории '{subcategory_name}' пока нет товаров")
        else:
            self.bot.send_message(chat_id, "❌ Подкатегория не найдена")
    
    def handle_product_selection(self, message):
        """Обработка выбора товара"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        
        # Извлекаем название товара и цену
        product_info = text.split(' ', 1)[-1].strip()  # Убираем "🛍 "
        
        # Разделяем название и цену
        if ' - $' in product_info:
            product_name = product_info.split(' - $')[0]
        else:
            product_name = product_info
        
        # Находим товар
        product = self.db.execute_query(
            'SELECT * FROM products WHERE name = ? AND is_active = 1',
            (product_name,)
        )
        
        if product:
            self.show_product_details(chat_id, product[0])
        else:
            self.bot.send_message(chat_id, "❌ Товар не найден")
    
    def show_product_details(self, chat_id, product):
        logger.info(f"[show_product_details] product_id={product[0]}, image_url={product[7]!r}, cat={product[4]}, subcat={product[5]}")
        """Показ деталей товара"""
        try:
            # Увеличиваем счетчик просмотров
            self.db.increment_product_views(product[0])

            # Получаем отзывы и среднюю оценку
            reviews = self.db.get_product_reviews(product[0])
            avg_rating = sum(r[0] for r in reviews) / len(reviews) if reviews else 0

            # Формируем карточку товара
            product_card = create_product_card(product)
            if avg_rating > 0:
                stars = create_stars_display(avg_rating)
                product_card += f"⭐ Рейтинг: {stars} ({avg_rating:.1f}/5, {len(reviews)} отзывов)\n"

            # Клавиатура
            kb = create_product_inline_keyboard_with_qty(product[0], qty=1, category_id=product[4], subcategory_id=product[5])

            # Отправляем карточку + фото (если есть)
            if product[7]:  # image_url
                try:
                    res = self.bot.send_photo(chat_id, product[7], product_card, kb)
                    if not res or (isinstance(res, dict) and not res.get('ok', True)):
                        # Фоллбэк: фото без подписи, затем текст с клавиатурой
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
            # Фоллбэк: если есть фото, попробуем отправить без подписи, затем сообщение об ошибке
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
        cart_items = self.db.get_cart_items(user_id)

        if not cart_items:
            empty_cart_text = t('empty_cart', language=user_data[0][5])
            self.bot.send_message(chat_id, empty_cart_text, create_cart_keyboard(False))
            return

        # Формируем текст корзины
        cart_text = "🛒 <b>Ваша корзина:</b>\n\n"
        total_amount = 0

        for item in cart_items:
            item_total = item[2] * item[3]  # price * quantity
            total_amount += item_total
            cart_text += f"🛍 <b>{item[1]}</b>\n"
            cart_text += f"💰 {format_price(item[2])} × {item[3]} = {format_price(item_total)}\n\n"

        cart_text += f"💳 <b>Итого: {format_price(total_amount)}</b>"
        self.bot.send_message(chat_id, cart_text, create_cart_keyboard(True))

    def show_user_orders(self, message):
        """Показ заказов пользователя"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return
        
        user_id = user_data[0][0]
        orders = self.db.get_user_orders(user_id)
        
        if not orders:
            self.bot.send_message(chat_id, "📋 У вас пока нет заказов")
            return
        
        orders_text = "📋 <b>Ваши заказы:</b>\n\n"
        
        for order in orders[:10]:  # Показываем последние 10
            status_emoji = get_order_status_emoji(order[3])
            status_text = get_order_status_text(order[3])
            
            orders_text += f"{status_emoji} <b>Заказ #{order[0]}</b>\n"
            orders_text += f"💰 {format_price(order[2])}\n"
            orders_text += f"📅 {format_date(order[7])}\n"
            orders_text += f"📊 {status_text}\n\n"
        
        orders_text += "👆 Используйте /order_ID для деталей заказа"
        
        self.bot.send_message(chat_id, orders_text, create_back_keyboard())
    
    def show_user_profile(self, message):
        """Показ профиля пользователя"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return
        
        user = user_data[0]
        user_id = user[0]
        
        # Получаем статистику заказов
        order_stats = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_orders,
                COALESCE(SUM(total_amount), 0) as total_spent,
                MAX(created_at) as last_order
            FROM orders 
            WHERE user_id = ? AND status != 'cancelled'
        ''', (user_id,))[0]
        
        # Получаем баллы лояльности
        loyalty_data = self.db.get_user_loyalty_points(user_id)
        
        profile_text = f"👤 <b>Ваш профиль</b>\n\n"
        profile_text += f"📝 Имя: {user[2]}\n"
        
        if user[3]:
            profile_text += f"📱 Телефон: {user[3]}\n"
        if user[4]:
            profile_text += f"📧 Email: {user[4]}\n"
        
        lang = "🇷🇺 Русский" if user[5] == "ru" else "🇺🇿 O'zbekcha"
        profile_text += f"🌍 Язык: {lang}\n"
        profile_text += f"📅 Регистрация: {format_date(user[7])}\n\n"
        
        profile_text += f"📊 <b>Статистика:</b>\n"
        profile_text += f"📦 Заказов: {order_stats[0]}\n"
        profile_text += f"💰 Потрачено: {format_price(order_stats[1])}\n"
        
        if order_stats[2]:
            profile_text += f"📅 Последний заказ: {format_date(order_stats[2])}\n"
        
        profile_text += f"\n⭐ <b>Программа лояльности:</b>\n"
        profile_text += f"💎 Уровень: {loyalty_data[3]}\n"
        profile_text += f"🏆 Баллов: {loyalty_data[1]}\n\n"
        profile_text += f"🌍 Для смены языка: /language"
        
        # Создаем клавиатуру профиля
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
        
        search_text = "🔍 <b>Поиск товаров</b>\n\nВведите название товара для поиска:"
        self.bot.send_message(chat_id, search_text, create_back_keyboard())
        
        self.user_states[telegram_id] = 'searching'
    
    def handle_search_query(self, message):
        """Обработка поискового запроса"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        if text in ['🔙 Назад', '🏠 Главная']:
            del self.user_states[telegram_id]
            self.show_main_menu(message)
            return
        
        # Выполняем поиск
        products = self.db.search_products(text)
        
        if products:
            search_results = f"🔍 <b>Результаты поиска:</b> '{text}'\n\n"
            
            for product in products[:10]:  # Показываем первые 10
                search_results += f"🛍 <b>{product[1]}</b>\n"
                search_results += f"💰 {format_price(product[3])}\n"
                search_results += f"📦 В наличии: {product[6]} шт.\n\n"
            
            if len(products) > 10:
                search_results += f"... и еще {len(products) - 10} товаров\n\n"
            
            search_results += "💡 Нажмите на название товара для подробностей"
            
            self.bot.send_message(chat_id, search_results, create_products_keyboard(products[:10], False))
        else:
            no_results = f"❌ По запросу '{text}' ничего не найдено\n\n"
            no_results += "💡 Попробуйте:\n"
            no_results += "• Изменить запрос\n"
            no_results += "• Использовать другие ключевые слова\n"
            no_results += "• Просмотреть каталог"
            
            self.bot.send_message(chat_id, no_results, create_back_keyboard())
        
        # Сбрасываем состояние поиска
        if telegram_id in self.user_states:
            del self.user_states[telegram_id]
    
    def start_order_process(self, message):
        """Начало оформления заказа"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return
        
        user_id = user_data[0][0]
        cart_items = self.db.get_cart_items(user_id)
        
        if not cart_items:
            empty_cart_text = t('empty_cart', language=user_data[0][5])
            self.bot.send_message(chat_id, empty_cart_text)
            return
        # Проверяем наличие телефона. Если нет — просим отправить номер
        phone = None
        try:
            phone = user_data[0][3] if user_data and len(user_data[0])>3 else None
        except Exception:
            phone = None
        if not phone:
            from keyboards import create_contact_request_keyboard
            self.user_states[telegram_id] = 'order_phone'
            lang = user_data[0][5] if user_data else 'ru'
            prompt = '📞 Отправьте номер телефона кнопкой ниже' if lang!='uz' else '📞 Raqamni quyidagi tugma orqali yuboring'
            self.bot.send_message(chat_id, prompt, create_contact_request_keyboard(lang))
            # Также сообщим и зафиксируем Telegram ID
            self.bot.send_message(chat_id, f'🆔 Ваш Telegram ID: <b>{telegram_id}</b>')
            return

        
        # Показываем сводку заказа
        total_amount = calculate_cart_total(cart_items)
        
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
        

        # Поддержка геолокации и кнопок
        location = message.get('location')
        if location and isinstance(location, dict) and 'latitude' in location and 'longitude' in location:
            # Сохраняем координаты и двигаемся к выбору оплаты
            if not hasattr(self, 'order_data'):
                self.order_data = {}
            self.order_data[telegram_id] = self.order_data.get(telegram_id, {})
            self.order_data[telegram_id]['lat'] = float(location.get('latitude'))
            self.order_data[telegram_id]['lon'] = float(location.get('longitude'))
            # Если адрес текстом не задан — ставим пометку
            self.order_data[telegram_id].setdefault('address', 'Геолокация отправлена')

            user_data = self.db.get_user_by_telegram_id(telegram_id)
            language = user_data[0][5] if user_data else 'ru'
            payment_text = "💳 Выберите способ оплаты:"
            self.bot.send_message(chat_id, payment_text, create_payment_methods_keyboard(language))
            del self.user_states[telegram_id]
            return

        # Пользователь нажал кнопку "✍️ Ввести адрес" — просто попросим ввести текст
        if text == '✍️ Ввести адрес':
            self.bot.send_message(chat_id, "✍️ Введите адрес доставки текстом:")
            return

        if text in ['🔙 Назад', '🏠 Главная']:
            del self.user_states[telegram_id]
            self.show_main_menu(message)
            return
        
        if len(text) < 10:
            self.bot.send_message(chat_id, "❌ Адрес слишком короткий. Введите полный адрес:")
            return
        
        # Сохраняем адрес и показываем способы оплаты
        if not hasattr(self, 'order_data'):
            self.order_data = {}
        
        self.order_data[telegram_id] = {'address': text}
        
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        language = user_data[0][5] if user_data else 'ru'
        
        payment_text = "💳 Выберите способ оплаты:"
        self.bot.send_message(chat_id, payment_text, create_payment_methods_keyboard(language))
        
        del self.user_states[telegram_id]
    
    def handle_payment_method_selection(self, message):
        """Обработка выбора способа оплаты"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return
        
        user_id = user_data[0][0]
        # Определяем язык пользователя (RU по умолчанию)
        try:
            user_language = get_user_language(telegram_id)
        except Exception:
            try:
                user_language = user_data[0][5] if user_data and len(user_data[0]) > 5 and user_data[0][5] else 'ru'
            except Exception:
                user_language = 'ru'

        cart_items = self.db.get_cart_items(user_id)
        
        if not cart_items:
            self.bot.send_message(chat_id, "❌ Корзина пуста")
            return
        
        # Определяем способ оплаты (только наличные или карта)
        if text in ['💵 Наличными при получении', '💵 Qabul qilishda naqd']:
            payment_method = 'cash'
        elif text in ['💳 Оплата картой', '💳 Kartadan toʻlov']:
            payment_method = 'card'
        else:
            self.bot.send_message(chat_id, "❌ Выберите способ оплаты из предложенных")
            return
        
        # Создаем заказ
        total_amount = calculate_cart_total(cart_items)
        order_data = getattr(self, 'order_data', {}).get(telegram_id, {})
        delivery_address = order_data.get('address', 'Не указан')
        
        order_id = self.db.create_order(user_id, total_amount, delivery_address, payment_method, order_data.get('lat'), order_data.get('lon'))
        
        if order_id:
            # Добавляем товары в заказ
            self.db.add_order_items(order_id, cart_items)
            
            # Очищаем корзину
            self.db.clear_cart(user_id)
            
            # Начисляем баллы лояльности
            points_earned = int(total_amount * 0.05)  # 5% от суммы
            self.db.update_loyalty_points(user_id, points_earned)
            
            # Уведомляем клиента
            success_text = f"✅ <b>Заказ #{order_id} оформлен!</b>\n\n"
            success_text += f"💰 Сумма: {format_price(total_amount)}\n"
            success_text += f"📍 Адрес: {delivery_address}\n"
            success_text += f"💳 Оплата: {payment_method}\n"
            success_text += f"⭐ Начислено баллов: {points_earned}\n\n"
            
            if payment_method == 'card':
                if user_language == 'uz':
                    success_text += "📞 Karta bilan toʻlovni tasdiqlash uchun 10 daqiqa ichida bogʻlanamiz"
                else:
                    success_text += "📞 Мы свяжемся с вами в течение 10 минут для подтверждения оплаты картой"
            else:
                if user_language == 'uz':
                    success_text += "📞 10 daqiqa ichida siz bilan bogʻlanamiz"
                else:
                    success_text += "📞 Мы свяжемся с вами в течение 10 минут"
            self.bot.send_message(chat_id, success_text, create_main_keyboard(user_language))
            
            # Уведомляем админов
            if self.notification_manager:
                self.notification_manager.send_order_notification_to_admins(order_id)
            
            # Очищаем данные заказа
            if hasattr(self, 'order_data') and telegram_id in self.order_data:
                del self.order_data[telegram_id]
        else:
            self.bot.send_message(chat_id, "❌ Ошибка создания заказа")
    
    
    def clear_user_cart(self, message):
            """Мгновенная очистка корзины пользователя (без подтверждения)."""
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            user_id = user_data[0][0]
            # чистим корзину
            try:
                self.db.clear_cart(user_id)
            except Exception:
                pass
            # сообщаем пользователю
            try:
                lang = self.db.get_user_by_telegram_id(telegram_id)[0][5]
            except Exception:
                lang = 'ru'
            self.bot.send_message(chat_id, '🧹 Корзина очищена.', create_main_keyboard(lang))
            # сбрасываем возможные состояния подтверждения
            self.user_states.pop(telegram_id, None)



    def show_loyalty_program(self, message):
            """Показ программы лояльности"""
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']

            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return

            user_id = user_data[0][0]
            loyalty_data = self.db.get_user_loyalty_points(user_id)

            loyalty_text = f"⭐ <b>Программа лояльности</b>\n\n"
            loyalty_text += f"💎 Ваш уровень: <b>{loyalty_data[3]}</b>\n"
            loyalty_text += f"🏆 Текущие баллы: {loyalty_data[1]}\n"
            loyalty_text += f"📊 Всего заработано: {loyalty_data[2]}\n\n"

            # Показываем уровни
            loyalty_text += f"🏅 <b>Уровни лояльности:</b>\n"
            loyalty_text += f"🥉 Bronze (0+ баллов) - 0% скидка\n"
            loyalty_text += f"🥈 Silver (100+ баллов) - 5% скидка\n"
            loyalty_text += f"🥇 Gold (500+ баллов) - 10% скидка\n"
            loyalty_text += f"💎 Platinum (1500+ баллов) - 15% скидка\n"
            loyalty_text += f"💍 Diamond (5000+ баллов) - 20% скидка\n\n"

            loyalty_text += f"💡 Зарабатывайте 5% с каждой покупки!"

            self.bot.send_message(chat_id, loyalty_text, create_back_keyboard())

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
                    promos_text = f"🎁 <b>Доступные промокоды:</b>\n\n"

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
                    promos_text = f"🎁 <b>Промокоды</b>\n\n"
                    promos_text += f"❌ Нет доступных промокодов\n\n"
                    promos_text += f"💡 Следите за акциями в нашем канале!"

                self.bot.send_message(chat_id, promos_text, create_back_keyboard())

            except Exception as e:
                logger.error(f"Ошибка показа промокодов: {e}")
                self.bot.send_message(chat_id, "❌ Ошибка получения промокодов")

    def start_language_change(self, message):
            """Начало смены языка"""
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']

            language_text = "🌍 Выберите язык / Tilni tanlang:"
            self.bot.send_message(chat_id, language_text, create_language_keyboard())

            self.user_states[telegram_id] = 'changing_language'

    def handle_language_change(self, message):
            """Обработка смены языка"""
            text = message.get('text', '')
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']

            if text == '❌ Отмена':
                del self.user_states[telegram_id]
                self.show_main_menu(message)
                return

            if text == '🇷🇺 Русский':
                new_language = 'ru'
            elif text == "🇺🇿 O'zbekcha":
                new_language = 'uz'
            else:
                self.bot.send_message(chat_id, "❌ Выберите язык из предложенных")
                return

            # Обновляем язык в базе
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if user_data:
                user_id = user_data[0][0]
                self.db.update_user_language(user_id, new_language)

                success_text = t('language_changed', language=new_language)
                self.bot.send_message(chat_id, success_text, create_main_keyboard(new_language))

            del self.user_states[telegram_id]

    def handle_order_command(self, message):
            """Обработка команды просмотра заказа"""
            text = message.get('text', '')
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']

            try:
                order_id = int(text.split('_')[1])

                # Проверяем принадлежность заказа пользователю
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

            details_text += f"🛍 <b>Товары:</b>\n"
            for item in items:
                details_text += f"• {item[2]} × {item[0]} = {format_price(item[1] * item[0])}\n"

            if order[6] > 0:  # promo_discount
                details_text += f"\n🎁 Скидка: -{format_price(order[6])}"

            self.bot.send_message(chat_id, details_text, create_order_details_keyboard(order[0]))

    def handle_track_command(self, message):
            """Обработка команды отслеживания"""
            text = message.get('text', '')
            chat_id = message['chat']['id']

            try:
                tracking_number = text.split('_')[1]

                # Получаем информацию о доставке
                if hasattr(self.bot, 'logistics_manager'):
                    tracking_info = self.bot.logistics_manager.track_shipment(tracking_number)

                    if tracking_info:
                        track_text = f"📦 <b>Отслеживание посылки</b>\n\n"
                        track_text += f"🏷 Трек-номер: {tracking_number}\n"
                        track_text += f"📊 Статус: {tracking_info['current_status']}\n"
                        track_text += f"📅 Ожидаемая доставка: {format_date(tracking_info['estimated_delivery'])}\n\n"

                        track_text += f"📋 <b>История:</b>\n"
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

                # Проверяем промокод
                from promotions import PromotionManager
                promo_manager = PromotionManager(self.db)
                validation = promo_manager.validate_promo_code(promo_code, user_id, cart_total)

                if validation['valid']:
                    promo_text = f"🎁 <b>Промокод применен!</b>\n\n"
                    promo_text += f"🏷 Код: {promo_code}\n"
                    promo_text += f"💰 Скидка: {format_price(validation['discount_amount'])}\n"
                    promo_text += f"📊 Новая сумма: {format_price(cart_total - validation['discount_amount'])}\n\n"
                    promo_text += f"🛒 Оформите заказ чтобы зафиксировать скидку"

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

                restore_text = f"💾 <b>Восстановление заказа</b>\n\n"
                restore_text += f"🔍 ID для восстановления: {restore_id}\n\n"
                restore_text += f"💡 Функция восстановления будет добавлена в следующей версии"

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

            # Показываем все уведомления
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

                # Отмечаем как прочитанное
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
                        # Показ подкатегорий
                        cat_row = self.db.execute_query('SELECT name FROM categories WHERE id=?', (cid,))
                        name = cat_row[0][0] if cat_row else ''
                        subs = self.db.get_products_by_category(cid)
                        if subs:
                            self.bot.send_message(chat_id, f"📂 <b>{name}</b>\n\nВыберите бренд или подкатегорию:", create_subcategories_keyboard(subs))
                        else:
                            self.bot.send_message(chat_id, f"❌ В категории '{name}' пока нет товаров")
                    else:
                        msg = {'chat': {'id': chat_id}}
                        self.show_catalog(msg)
                elif data == 'go_to_cart':
                    # Переход в корзину
                    msg = {'chat': {'id': chat_id}, 'from': {'id': telegram_id}}
                    self.show_cart(msg)
                elif data.startswith('back_to_subcategory_'):
                    try:
                        sid = int(data.split('_')[-1])
                    except Exception:
                        sid = None
                    if sid:
                        # Показ товаров в подкатегории
                        sub_row = self.db.execute_query('SELECT name FROM subcategories WHERE id=?', (sid,))
                        subname = sub_row[0][0] if sub_row else 'Подкатегория'
                        products = self.db.get_products_by_subcategory(sid)
                        if products:
                            self.bot.send_message(chat_id, f"🛍 <b>{subname}</b>\n\nВыберите товар:", create_products_keyboard(products))
                        else:
                            self.bot.send_message(chat_id, f"❌ В подкатегории '{subname}' пока нет товаров")
                    else:
                        msg = {'chat': {'id': chat_id}}
                        self.show_catalog(msg)
                elif data.startswith('qty_inc_') or data.startswith('qty_dec_'):
                    parts = data.split('_')
                    try:
                        pid = int(parts[2]); qty = int(parts[3])
                    except (ValueError, IndexError):
                        return
                    new_qty = qty + 1 if data.startswith('qty_inc_') else max(1, qty - 1)
                    kb = create_product_inline_keyboard_with_qty(pid, new_qty)
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

            except Exception as e:
                logger.error(f"Ошибка обработки callback: {e}")

    def handle_add_to_cart(self, callback_query):
            """Добавление товара в корзину"""
            data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']

            try:
                product_id = int(data.split('_')[3])

                user_data = self.db.get_user_by_telegram_id(telegram_id)
                if not user_data:
                    return

                user_id = user_data[0][0]

                # Добавляем в корзину
                result = self.db.add_to_cart(user_id, product_id, 1)

                if result:
                    product = self.db.get_product_by_id(product_id)
                    success_text = f"✅ <b>{product[1]}</b> добавлен в корзину!"

                    # Показываем кнопку перехода в корзину
                    cart_keyboard = {
                        'inline_keyboard': [
                            [
                                {'text': '🛒 Перейти в корзину', 'callback_data': 'go_to_cart'},
                                {'text': '🛍 Продолжить покупки', 'callback_data': 'back_to_categories'}
                            ]
                        ]
                    }

                    self.bot.send_message(chat_id, success_text, cart_keyboard)
                else:
                    self.bot.send_message(chat_id, "❌ Товар недоступен или закончился")

            except (ValueError, IndexError) as e:
                logger.error(f"Ошибка добавления в корзину: {e}")
                self.bot.send_message(chat_id, "❌ Ошибка добавления товара")

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

                # Добавляем в избранное
                result = self.db.add_to_favorites(user_id, product_id)

                if result:
                    product = self.db.get_product_by_id(product_id)
                    self.bot.send_message(chat_id, f"❤️ {product[1]} добавлен в избранное!")
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

                if reviews:
                    reviews_text = f"⭐ <b>Отзывы о товаре:</b>\n{product[1]}\n\n"

                    for review in reviews[:5]:  # Показываем первые 5
                        stars = create_stars_display(review[0])
                        reviews_text += f"{stars} <b>{review[3]}</b>\n"

                        if review[1]:
                            reviews_text += f"💭 {review[1]}\n"

                        reviews_text += f"📅 {format_date(review[2])}\n\n"

                    if len(reviews) > 5:
                        reviews_text += f"... и еще {len(reviews) - 5} отзывов"
                else:
                    reviews_text = f"⭐ <b>Отзывы о товаре:</b>\n{product[1]}\n\n"
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

                # Проверяем, покупал ли пользователь этот товар
                purchased = self.db.execute_query('''
                    SELECT COUNT(*) FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE o.user_id = ? AND oi.product_id = ? AND o.status != 'cancelled'
                ''', (user_id, product_id))[0][0]

                if purchased == 0:
                    self.bot.send_message(chat_id, "❌ Вы можете оценивать только купленные товары")
                    return

                # Сохраняем оценку
                self.db.add_review(user_id, product_id, rating, "")

                stars = '⭐' * rating
                self.bot.send_message(chat_id, f"✅ Спасибо за оценку! {stars}")

            except (ValueError, IndexError) as e:
                logger.error(f"Ошибка оценки товара: {e}")

    def handle_cart_action(self, callback_query):
            """Обработка действий с корзиной"""
            data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']

            try:
                action = data.split('_')[1]
                cart_item_id = int(data.split('_')[2])

                if action == 'increase':
                    # Увеличиваем количество
                    current_quantity = self.get_cart_item_quantity(cart_item_id)
                    self.db.update_cart_quantity(cart_item_id, current_quantity + 1)
                    self.update_cart_message(callback_query, cart_item_id)

                elif action == 'decrease':
                    # Уменьшаем количество
                    current_quantity = self.get_cart_item_quantity(cart_item_id)
                    if current_quantity > 1:
                        self.db.update_cart_quantity(cart_item_id, current_quantity - 1)
                        self.update_cart_message(callback_query, cart_item_id)
                    else:
                        self.bot.send_message(chat_id, "❌ Минимальное количество: 1")

                elif action == 'remove':
                    # Удаляем товар
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
            """Обработка выбора способа оплаты"""
            data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']

            try:
                parts = data.split('_')
                provider = parts[1]
                order_id = int(parts[2])

                if provider == 'cash':
                    # Наличная оплата
                    self.bot.send_message(
                        chat_id,
                        f"💵 <b>Оплата наличными</b>\n\nЗаказ #{order_id} будет оплачен при получении.\n\n📞 Мы свяжемся с вами для подтверждения."
                    )
                else:
                    # Онлайн оплата
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

            # Проверяем, может быть это поисковый запрос
            if len(text) > 2 and not text.startswith('/'):
                # Выполняем поиск
                products = self.db.search_products(text, 5)

                if products:
                    search_text = f"🔍 Найдено по запросу '{text}':\n\n"

                    for product in products:
                        search_text += f"🛍 {product[1]} - {format_price(product[3])}\n"

                    search_text += f"\n💡 Используйте 🔍 Поиск для расширенного поиска"

                    self.bot.send_message(chat_id, search_text, create_main_keyboard())
                    return

            # Если ничего не найдено
            telegram_id = message['from']['id']
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            lang = user_data[0][5] if user_data else 'ru'

            unknown_text = "❓ Команда не распознана\n\n"
            unknown_text += "💡 Используйте кнопки меню или команды:\n"
            unknown_text += "• /help - справка\n"
            unknown_text += "• /start - главное меню\n"
            unknown_text += "• 🛍 Каталог - просмотр товаров"

            self.bot.send_message(chat_id, unknown_text, create_main_keyboard(lang))
def show_contacts(self, message):
    """Показать контакты: телефон, чат и информация"""
    chat_id = message['chat']['id']
    info = CONTACT_INFO if 'CONTACT_INFO' in globals() else {}
    phone = info.get('support_phone') or info.get('call_center_phone')
    tg_username = info.get('support_telegram')
    working_hours = info.get('working_hours', 'ежедневно')
    about = info.get('about', 'Мы на связи и быстро отвечаем.')

    # Текст
    text_lines = [
        "📞 <b>Связаться с нами</b>",
    ]
    if phone:
        text_lines.append(f"• Телефон: <b>{phone}</b>")
    if tg_username:
        text_lines.append(f"• Telegram: <b>{tg_username}</b>")
    if working_hours:
        text_lines.append(f"• Время работы: {working_hours}")
    if about:
        text_lines.append(f"\n{about}")
    text = "\n".join(text_lines)

    # Кнопки
    from keyboards import create_contact_inline_keyboard
    kb = create_contact_inline_keyboard(phone=phone, tg_username=tg_username, chat_url=info.get('chat_url'))

    # Отправляем
    self.bot.send_message(chat_id, text, kb)


# === Переопределённый обработчик контактов: только чат + телефон ===
def handle_contact_request(self, message, language='ru'):
    from config import CONTACT_INFO
    chat_id = message['chat']['id']
    if language == 'uz':
        text = (
            "📞 <b>Biz bilan bog'lanish</b>\n\n"
            f"• Chat: {CONTACT_INFO['support_telegram']}\n"
            f"• Telefon: {CONTACT_INFO['support_phone']}"
        )
    else:
        text = (
            "📞 <b>Связаться с нами</b>\n\n"
            f"• Чат: {CONTACT_INFO['support_telegram']}\n"
            f"• Телефон: {CONTACT_INFO['support_phone']}"
        )
    self.bot.send_message(chat_id, text, create_main_keyboard(language))

# === Диалог «Стать продавцом» ===
def start_seller_application(self, message):
    chat_id = message['chat']['id']
    telegram_id = message['from']['id']
    user_data = self.db.get_user_by_telegram_id(telegram_id)
    language = (user_data[0][5] if user_data else 'ru') or 'ru'
    if not hasattr(self, 'seller_data'):
        self.seller_data = {}
    self.seller_data[telegram_id] = {}
    prompt = "👤 Как вас зовут?" if language == 'ru' else "👤 Ismingiz nima?"
    self.bot.send_message(chat_id, prompt, create_back_keyboard())
    self.user_states[telegram_id] = 'seller_name'

def handle_seller_name(self, message):
    text = message.get('text', '').strip()
    chat_id = message['chat']['id']
    telegram_id = message['from']['id']
    if text in ['❌ Отмена', '🔙 Назад']:
        self.user_states.pop(telegram_id, None)
        if hasattr(self, 'seller_data'): self.seller_data.pop(telegram_id, None)
        self.bot.send_message(chat_id, "Отменено.", create_main_keyboard('ru'))
        return
    if not text or len(text) < 2:
        self.bot.send_message(chat_id, "❌ Имя слишком короткое. Попробуйте ещё раз:")
        return
    if not hasattr(self, 'seller_data'):
        self.seller_data = {}
    self.seller_data.setdefault(telegram_id, {})['name'] = text
    self.bot.send_message(chat_id, "📱 Укажите ваш номер телефона (например, +998 90 123 45 67):")
    self.user_states[telegram_id] = 'seller_phone'

def handle_seller_phone(self, message):
    text = message.get('text', '').strip()
    chat_id = message['chat']['id']
    telegram_id = message['from']['id']
    phone = validate_phone(text)
    if not phone:
        self.bot.send_message(chat_id, "❌ Неверный формат телефона. Попробуйте ещё раз:")
        return
    self.seller_data.setdefault(telegram_id, {})['phone'] = phone
    self.bot.send_message(chat_id, "🏷️ Название вашего бренда или компании:")
    self.user_states[telegram_id] = 'seller_brand'

def handle_seller_brand(self, message):
    text = message.get('text', '').strip()
    chat_id = message['chat']['id']
    telegram_id = message['from']['id']
    if len(text) < 2:
        self.bot.send_message(chat_id, "❌ Слишком коротко. Введите название бренда/компании:")
        return
    self.seller_data.setdefault(telegram_id, {})['brand'] = text
    self.bot.send_message(chat_id, "🛍 Что вы продаёте? Кратко опишите товары/категории:")
    self.user_states[telegram_id] = 'seller_products'

def handle_seller_products(self, message):
    text = message.get('text', '').strip()
    chat_id = message['chat']['id']
    telegram_id = message['from']['id']
    if len(text) < 2:
        self.bot.send_message(chat_id, "❌ Слишком коротко. Опишите, что вы продаёте:")
        return
    data = self.seller_data.get(telegram_id, {})
    data['products'] = text
    try:
        admins = self.db.execute_query('SELECT telegram_id FROM users WHERE is_admin = 1')
        if not admins:
            from config import BOT_CONFIG
            admin_id = int(BOT_CONFIG.get('admin_telegram_id', '0') or 0)
            if admin_id:
                admins = [(admin_id,)]
        msg = (
            "🧑‍💼 <b>Новая заявка продавца</b>\n\n"
            f"• Имя: {data.get('name','')}\n"
            f"• Телефон: {data.get('phone','')}\n"
            f"• Бренд/Компания: {data.get('brand','')}\n"
            f"• Что продаёт: {data.get('products','')}"
        )
        for adm in admins or []:
            try:
                self.bot.send_message(adm[0], msg)
            except Exception as e:
                logging.error(f"Ошибка отправки заявки админу {adm}: {e}")
    except Exception as e:
        logging.error(f"Ошибка подготовки уведомления админа: {e}")
    self.bot.send_message(chat_id, "✅ Спасибо! Ваша заявка отправлена. Мы свяжемся с вами в ближайшее время.", create_main_keyboard('ru'))
    self.user_states.pop(telegram_id, None)
    if hasattr(self, 'seller_data'):
        self.seller_data.pop(telegram_id, None)

# === Привязка новых методов к классу MessageHandler ===
MessageHandler.start_seller_application = start_seller_application
MessageHandler.handle_seller_name = handle_seller_name
MessageHandler.handle_seller_phone = handle_seller_phone
MessageHandler.handle_seller_brand = handle_seller_brand
MessageHandler.handle_seller_products = handle_seller_products
MessageHandler.handle_contact_request = handle_contact_request