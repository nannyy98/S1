"""
Админ-панель для телеграм-бота
"""

import logging
from datetime import datetime, timedelta
from keyboards import (
    create_admin_keyboard,
    create_notifications_keyboard,
    create_analytics_keyboard,
    create_period_selection_keyboard
)
from utils import format_price, format_date
from localization import t

logger = logging.getLogger(__name__)

class AdminHandler:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.admin_states = {}
        self.notification_manager = None
    
    def is_admin(self, telegram_id):
        """Проверка прав администратора"""
        try:
            user = self.db.get_user_by_telegram_id(telegram_id)
            return user and user[0][6] == 1  # is_admin поле
        except Exception as e:
            logger.error(f"Ошибка проверки прав админа: {e}")
            return False
    
    def handle_admin_command(self, message):
        """Обработка админ команд"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        if not self.is_admin(telegram_id):
            self.bot.send_message(chat_id, "❌ У вас нет прав администратора")
            return
        
        if text == '/admin' or text == '📊 Статистика':
            self.show_admin_panel(chat_id)
        elif text == '📦 Заказы':
            self.show_orders_management(chat_id)
        elif text == '🛠 Товары':
            self.show_products_management(chat_id)
        elif text == '👥 Пользователи':
            self.show_users_management(chat_id)
        elif text == '📈 Аналитика':
            self.show_analytics_menu(chat_id)
        elif text == '🛡 Безопасность':
            self.show_security_panel(chat_id)
        elif text == '💰 Финансы':
            self.show_financial_reports(chat_id)
        elif text == '📦 Склад':
            self.show_inventory_management(chat_id)
        elif text == '🤖 AI':
            self.show_ai_features(chat_id)
        elif text == '🎯 Автоматизация':
            self.show_automation_panel(chat_id)
        elif text == '👥 CRM':
            self.show_crm_panel(chat_id)
        elif text == '📢 Рассылка':
            self.show_broadcast_panel(chat_id)
        elif text == '🔙 Пользовательский режим':
            self.exit_admin_mode(chat_id)
    
    def show_admin_panel(self, chat_id):
        """Показ главной админ-панели"""
        try:
            # Получаем статистику
            today = datetime.now().strftime('%Y-%m-%d')
            stats = self.db.execute_query('''
                SELECT 
                    COUNT(*) as orders_today,
                    COALESCE(SUM(total_amount), 0) as revenue_today,
                    COUNT(DISTINCT user_id) as customers_today
                FROM orders 
                WHERE DATE(created_at) = ?
            ''', (today,))
            
            if stats:
                orders_today, revenue_today, customers_today = stats[0]
            else:
                orders_today, revenue_today, customers_today = 0, 0, 0
            
            admin_text = f"🛠 <b>Админ-панель</b>\n\n"
            admin_text += f"📊 <b>Статистика за сегодня:</b>\n"
            admin_text += f"📦 Заказов: {orders_today}\n"
            admin_text += f"💰 Выручка: {format_price(revenue_today)}\n"
            admin_text += f"👥 Клиентов: {customers_today}\n\n"
            admin_text += f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}"
            
            self.bot.send_message(chat_id, admin_text, create_admin_keyboard())
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка получения статистики")
    
    def show_orders_management(self, chat_id):
        """Управление заказами"""
        try:
            # Получаем последние заказы
            recent_orders = self.db.execute_query('''
                SELECT o.id, o.total_amount, o.status, o.created_at, u.name
                FROM orders o
                JOIN users u ON o.user_id = u.id
                ORDER BY o.created_at DESC
                LIMIT 10
            ''')
            
            if not recent_orders:
                self.bot.send_message(chat_id, "📦 Заказов пока нет")
                return
            
            orders_text = "📦 <b>Последние заказы:</b>\n\n"
            
            for order in recent_orders:
                status_emoji = self.get_status_emoji(order[2])
                orders_text += f"{status_emoji} #{order[0]} - {format_price(order[1])}\n"
                orders_text += f"👤 {order[4]}\n"
                orders_text += f"📅 {format_date(order[3])}\n\n"
            
            orders_text += "👆 Используйте /admin_order_ID для управления заказом"
            
            self.bot.send_message(chat_id, orders_text, create_admin_keyboard())
            
        except Exception as e:
            logger.error(f"Ошибка получения заказов: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка получения заказов")
    
    def show_products_management(self, chat_id):
        """Управление товарами"""
        try:
            products_count = self.db.execute_query('SELECT COUNT(*) FROM products WHERE is_active = 1')[0][0]
            low_stock = self.db.execute_query('SELECT COUNT(*) FROM products WHERE stock <= 5 AND is_active = 1')[0][0]
            
            products_text = f"🛠 <b>Управление товарами</b>\n\n"
            products_text += f"📦 Активных товаров: {products_count}\n"
            products_text += f"⚠️ Заканчивается: {low_stock}\n\n"
            products_text += f"Команды:\n"
            products_text += f"• /edit_product_ID - редактировать\n"
            products_text += f"• /delete_product_ID - удалить\n\n"
            products_text += f"💡 Добавляйте товары через веб-панель"
            
            self.bot.send_message(chat_id, products_text, create_admin_keyboard())
            
        except Exception as e:
            logger.error(f"Ошибка управления товарами: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка управления товарами")
    
    def show_users_management(self, chat_id):
        """Управление пользователями"""
        try:
            users_stats = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN created_at >= date('now', '-7 days') THEN 1 END) as new_users,
                    COUNT(CASE WHEN id IN (
                        SELECT DISTINCT user_id FROM orders 
                        WHERE created_at >= date('now', '-30 days')
                    ) THEN 1 END) as active_users
                FROM users 
                WHERE is_admin = 0
            ''')[0]
            
            users_text = f"👥 <b>Управление пользователями</b>\n\n"
            users_text += f"👤 Всего пользователей: {users_stats[0]}\n"
            users_text += f"🆕 Новых за неделю: {users_stats[1]}\n"
            users_text += f"🔥 Активных за месяц: {users_stats[2]}\n\n"
            users_text += f"📊 Подробная статистика доступна в веб-панели"
            
            self.bot.send_message(chat_id, users_text, create_admin_keyboard())
            
        except Exception as e:
            logger.error(f"Ошибка статистики пользователей: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка получения статистики пользователей")
    
    def show_analytics_menu(self, chat_id):
        """Меню аналитики"""
        analytics_text = "📈 <b>Аналитика и отчеты</b>\n\n"
        analytics_text += "Выберите тип отчета:"
        
        self.bot.send_message(chat_id, analytics_text, create_analytics_keyboard())
    
    def show_security_panel(self, chat_id):
        """Панель безопасности"""
        try:
            # Получаем статистику безопасности
            security_stats = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_logs,
                    COUNT(CASE WHEN severity = 'high' THEN 1 END) as high_severity,
                    COUNT(CASE WHEN created_at >= date('now', '-1 day') THEN 1 END) as today_events
                FROM security_logs
            ''')
            
            if security_stats:
                total_logs, high_severity, today_events = security_stats[0]
            else:
                total_logs, high_severity, today_events = 0, 0, 0
            
            security_text = f"🛡 <b>Панель безопасности</b>\n\n"
            security_text += f"📋 Всего событий: {total_logs}\n"
            security_text += f"🔴 Высокая важность: {high_severity}\n"
            security_text += f"📅 События сегодня: {today_events}\n\n"
            security_text += f"🔒 Система работает в штатном режиме"
            
            self.bot.send_message(chat_id, security_text, create_admin_keyboard())
            
        except Exception as e:
            logger.error(f"Ошибка панели безопасности: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка получения данных безопасности")
    
    def show_financial_reports(self, chat_id):
        """Финансовые отчеты"""
        try:
            # Получаем финансовую статистику за месяц
            month_revenue = self.db.execute_query('''
                SELECT 
                    COUNT(*) as orders_count,
                    SUM(total_amount) as total_revenue,
                    AVG(total_amount) as avg_order
                FROM orders 
                WHERE created_at >= date('now', '-30 days')
                AND status != 'cancelled'
            ''')[0]
            
            financial_text = f"💰 <b>Финансовые отчеты</b>\n\n"
            financial_text += f"📊 <b>За последние 30 дней:</b>\n"
            financial_text += f"📦 Заказов: {month_revenue[0]}\n"
            financial_text += f"💰 Выручка: {format_price(month_revenue[1] or 0)}\n"
            financial_text += f"💳 Средний чек: {format_price(month_revenue[2] or 0)}\n\n"
            financial_text += f"📋 Подробные отчеты в веб-панели"
            
            self.bot.send_message(chat_id, financial_text, create_admin_keyboard())
            
        except Exception as e:
            logger.error(f"Ошибка финансовых отчетов: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка получения финансовых данных")
    
    def show_inventory_management(self, chat_id):
        """Управление складом"""
        try:
            # Получаем статистику склада
            inventory_stats = self.db.execute_query('''
                SELECT 
                    COUNT(*) as total_products,
                    SUM(stock) as total_units,
                    COUNT(CASE WHEN stock = 0 THEN 1 END) as out_of_stock,
                    COUNT(CASE WHEN stock <= 5 THEN 1 END) as low_stock
                FROM products
                WHERE is_active = 1
            ''')[0]
            
            inventory_text = f"📦 <b>Управление складом</b>\n\n"
            inventory_text += f"🛍 Товаров: {inventory_stats[0]}\n"
            inventory_text += f"📊 Единиц на складе: {inventory_stats[1]}\n"
            inventory_text += f"🔴 Нет в наличии: {inventory_stats[2]}\n"
            inventory_text += f"🟡 Заканчивается: {inventory_stats[3]}\n\n"
            
            if inventory_stats[3] > 0:
                inventory_text += f"⚠️ Требуется пополнение склада!"
            else:
                inventory_text += f"✅ Склад в порядке"
            
            self.bot.send_message(chat_id, inventory_text, create_admin_keyboard())
            
        except Exception as e:
            logger.error(f"Ошибка управления складом: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка получения данных склада")
    
    def show_ai_features(self, chat_id):
        """AI функции"""
        ai_text = f"🤖 <b>AI функции</b>\n\n"
        ai_text += f"🎯 Персональные рекомендации\n"
        ai_text += f"💬 Умная поддержка клиентов\n"
        ai_text += f"📊 Анализ поведения пользователей\n"
        ai_text += f"🔍 Исправление опечаток в поиске\n\n"
        ai_text += f"🚀 AI функции работают автоматически"
        
        self.bot.send_message(chat_id, ai_text, create_admin_keyboard())
    
    def show_automation_panel(self, chat_id):
        """Панель автоматизации"""
        automation_text = f"🎯 <b>Автоматизация маркетинга</b>\n\n"
        automation_text += f"📧 Автоматические рассылки\n"
        automation_text += f"🛒 Напоминания о корзине\n"
        automation_text += f"🎁 Персональные предложения\n"
        automation_text += f"📊 Сегментация клиентов\n\n"
        automation_text += f"⚙️ Правила работают в фоновом режиме"
        
        self.bot.send_message(chat_id, automation_text, create_admin_keyboard())
    
    def show_crm_panel(self, chat_id):
        """CRM панель"""
        try:
            # Получаем сегментацию клиентов
            from crm import CRMManager
            crm = CRMManager(self.db)
            segments = crm.segment_customers()
            
            crm_text = f"👥 <b>CRM - Управление клиентами</b>\n\n"
            crm_text += f"🏆 Чемпионы: {len(segments.get('champions', []))}\n"
            crm_text += f"💎 Лояльные: {len(segments.get('loyal', []))}\n"
            crm_text += f"🌟 Потенциальные: {len(segments.get('potential', []))}\n"
            crm_text += f"🆕 Новые: {len(segments.get('new', []))}\n"
            crm_text += f"⚠️ Требуют внимания: {len(segments.get('need_attention', []))}\n"
            crm_text += f"🚨 В зоне риска: {len(segments.get('at_risk', []))}\n\n"
            crm_text += f"📊 Подробная аналитика в веб-панели"
            
            self.bot.send_message(chat_id, crm_text, create_admin_keyboard())
            
        except Exception as e:
            logger.error(f"Ошибка CRM панели: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка получения CRM данных")
    
    def show_broadcast_panel(self, chat_id):
        """Панель рассылок"""
        broadcast_text = f"📢 <b>Управление рассылками</b>\n\n"
        broadcast_text += f"📊 Доступные аудитории:\n"
        broadcast_text += f"• 👥 Все клиенты\n"
        broadcast_text += f"• 🔥 Активные клиенты\n"
        broadcast_text += f"• 💎 VIP клиенты\n"
        broadcast_text += f"• 🆕 Новые клиенты\n\n"
        broadcast_text += f"💡 Создавайте рассылки через веб-панель"
        
        self.bot.send_message(chat_id, broadcast_text, create_notifications_keyboard())
    
    def exit_admin_mode(self, chat_id):
        """Выход из админ-режима"""
        from keyboards import create_main_keyboard
        
        self.bot.send_message(
            chat_id,
            "👤 Переключение в пользовательский режим",
            create_main_keyboard()
        )
    
    def get_status_emoji(self, status):
        """Получение эмодзи для статуса"""
        emojis = {
            'pending': '⏳',
            'confirmed': '✅',
            'shipped': '🚚',
            'delivered': '📦',
            'cancelled': '❌'
        }
        return emojis.get(status, '❓')
    
    def handle_callback_query(self, callback_query):
        """Обработка callback запросов"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        telegram_id = callback_query['from']['id']
        
        if not self.is_admin(telegram_id):
            return
        
        if data.startswith('admin_'):
            self.handle_admin_callback(callback_query)
        elif data.startswith('change_status_'):
            self.handle_status_change(callback_query)
        elif data.startswith('order_details_'):
            self.handle_order_details(callback_query)
    
    def handle_admin_callback(self, callback_query):
        """Обработка админ callback'ов"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        
        if data == 'admin_back_main':
            self.show_admin_panel(chat_id)
    
    def handle_analytics_callback(self, callback_query):
        """Обработка callback'ов аналитики"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        
        if data == 'analytics_sales':
            self.show_sales_analytics(chat_id)
        elif data == 'period_today':
            self.show_period_analytics(chat_id, 'today')
        elif data == 'period_week':
            self.show_period_analytics(chat_id, 'week')
        elif data == 'period_month':
            self.show_period_analytics(chat_id, 'month')
    
    def show_sales_analytics(self, chat_id):
        """Показ аналитики продаж"""
        period_text = "📊 <b>Выберите период для анализа:</b>"
        self.bot.send_message(chat_id, period_text, create_period_selection_keyboard())
    
    def show_period_analytics(self, chat_id, period):
        """Показ аналитики за период"""
        try:
            if period == 'today':
                date_filter = datetime.now().strftime('%Y-%m-%d')
                period_name = "сегодня"
            elif period == 'week':
                date_filter = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                period_name = "за неделю"
            elif period == 'month':
                date_filter = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                period_name = "за месяц"
            else:
                return
            
            stats = self.db.execute_query('''
                SELECT 
                    COUNT(*) as orders,
                    SUM(total_amount) as revenue,
                    AVG(total_amount) as avg_order,
                    COUNT(DISTINCT user_id) as customers
                FROM orders 
                WHERE created_at >= ? AND status != 'cancelled'
            ''', (date_filter,))[0]
            
            analytics_text = f"📊 <b>Аналитика {period_name}</b>\n\n"
            analytics_text += f"📦 Заказов: {stats[0]}\n"
            analytics_text += f"💰 Выручка: {format_price(stats[1] or 0)}\n"
            analytics_text += f"💳 Средний чек: {format_price(stats[2] or 0)}\n"
            analytics_text += f"👥 Клиентов: {stats[3]}\n\n"
            analytics_text += f"📈 Подробная аналитика в веб-панели"
            
            self.bot.send_message(chat_id, analytics_text, create_admin_keyboard())
            
        except Exception as e:
            logger.error(f"Ошибка аналитики за период: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка получения аналитики")
    
    def handle_order_management(self, message):
        """Управление конкретным заказом"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        
        if text.startswith('/admin_order_'):
            try:
                order_id = int(text.split('_')[2])
                self.show_order_details(chat_id, order_id)
            except (ValueError, IndexError):
                self.bot.send_message(chat_id, "❌ Неверный формат команды")
    
    def show_order_details(self, chat_id, order_id):
        """Показ деталей заказа"""
        try:
            order_details = self.db.get_order_details(order_id)
            
            if not order_details:
                self.bot.send_message(chat_id, f"❌ Заказ #{order_id} не найден")
                return
            
            order = order_details['order']
            items = order_details['items']
            
            # Получаем информацию о клиенте
            user = self.db.execute_query(
                'SELECT name, phone, email FROM users WHERE id = ?',
                (order[1],)
            )[0]
            
            details_text = f"📋 <b>Заказ #{order[0]}</b>\n\n"
            details_text += f"👤 Клиент: {user[0]}\n"
            
            if user[1]:
                details_text += f"📱 Телефон: {user[1]}\n"
            if user[2]:
                details_text += f"📧 Email: {user[2]}\n"
            
            details_text += f"\n💰 Сумма: {format_price(order[2])}\n"
            details_text += f"📅 Дата: {format_date(order[7])}\n"
            details_text += f"📍 Адрес: {order[4] or 'Не указан'}\n"
            details_text += f"💳 Оплата: {order[5]}\n"
            
            status_emoji = self.get_status_emoji(order[3])
            details_text += f"📊 Статус: {status_emoji} {order[3]}\n"
            
            details_text += f"\n🛍 <b>Товары ({len(items)}):</b>\n"
            for item in items:
                details_text += f"• {item[2]} × {item[0]} = {format_price(item[1] * item[0])}\n"
            
            # Создаем inline клавиатуру для управления
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '✅ Подтвердить', 'callback_data': f'change_status_{order_id}_confirmed'},
                        {'text': '🚚 Отправить', 'callback_data': f'change_status_{order_id}_shipped'}
                    ],
                    [
                        {'text': '📦 Доставлен', 'callback_data': f'change_status_{order_id}_delivered'},
                        {'text': '❌ Отменить', 'callback_data': f'change_status_{order_id}_cancelled'}
                    ]
                ]
            }
            
            self.bot.send_message(chat_id, details_text, keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка показа деталей заказа: {e}")
            self.bot.send_message(chat_id, f"❌ Ошибка получения заказа #{order_id}")
    
    def handle_status_change(self, callback_query):
        """Обработка изменения статуса заказа"""
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        
        try:
            parts = data.split('_')
            order_id = int(parts[2])
            new_status = parts[3]
            
            # Обновляем статус
            result = self.db.update_order_status(order_id, new_status)
            
            if result is not None:
                # Уведомляем клиента
                if self.notification_manager:
                    self.notification_manager.send_order_status_notification(order_id, new_status)
                
                status_names = {
                    'confirmed': 'подтвержден',
                    'shipped': 'отправлен',
                    'delivered': 'доставлен',
                    'cancelled': 'отменен'
                }
                
                status_text = status_names.get(new_status, new_status)
                self.bot.send_message(chat_id, f"✅ Заказ #{order_id} {status_text}")
            else:
                self.bot.send_message(chat_id, "❌ Ошибка изменения статуса")
                
        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка изменения статуса: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка обработки команды")
    
    def handle_product_commands(self, message):
        """Обработка команд управления товарами"""
        text = message.get('text', '')
        chat_id = message['chat']['id']
        
        if text.startswith('/edit_product_'):
            try:
                product_id = int(text.split('_')[2])
                self.show_product_edit_options(chat_id, product_id)
            except (ValueError, IndexError):
                self.bot.send_message(chat_id, "❌ Неверный формат команды")
        
        elif text.startswith('/delete_product_'):
            try:
                product_id = int(text.split('_')[2])
                self.confirm_product_deletion(chat_id, product_id)
            except (ValueError, IndexError):
                self.bot.send_message(chat_id, "❌ Неверный формат команды")
    
    def show_product_edit_options(self, chat_id, product_id):
        """Показ опций редактирования товара"""
        try:
            product = self.db.get_product_by_id(product_id)
            
            if not product:
                self.bot.send_message(chat_id, f"❌ Товар #{product_id} не найден")
                return
            
            edit_text = f"✏️ <b>Редактирование товара</b>\n\n"
            edit_text += f"🛍 <b>{product[1]}</b>\n"
            edit_text += f"💰 Цена: {format_price(product[3])}\n"
            edit_text += f"📦 Остаток: {product[6]} шт.\n\n"
            edit_text += f"💡 Используйте веб-панель для полного редактирования"
            
            self.bot.send_message(chat_id, edit_text)
            
        except Exception as e:
            logger.error(f"Ошибка редактирования товара: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка получения товара")
    
    def confirm_product_deletion(self, chat_id, product_id):
        """Подтверждение удаления товара"""
        try:
            product = self.db.get_product_by_id(product_id)
            
            if not product:
                self.bot.send_message(chat_id, f"❌ Товар #{product_id} не найден")
                return
            
            confirm_text = f"⚠️ <b>Подтверждение удаления</b>\n\n"
            confirm_text += f"🛍 Товар: {product[1]}\n"
            confirm_text += f"💰 Цена: {format_price(product[3])}\n\n"
            confirm_text += f"❗ Это действие нельзя отменить!"
            
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '✅ Да, удалить', 'callback_data': f'confirm_delete_{product_id}'},
                        {'text': '❌ Отмена', 'callback_data': 'cancel_delete'}
                    ]
                ]
            }
            
            self.bot.send_message(chat_id, confirm_text, keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка подтверждения удаления: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка обработки команды")