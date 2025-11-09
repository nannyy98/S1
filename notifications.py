"""
Система уведомлений для телеграм-бота
"""
import logging

from datetime import datetime, timedelta
from utils import format_date, format_price
import threading
import time

class NotificationManager:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.push_queue = []
        self.start_push_service()
    
    def start_push_service(self):
        """Запуск службы push-уведомлений"""
        def push_worker():
            while True:
                try:
                    if self.push_queue:
                        notification = self.push_queue.pop(0)
                        self.send_push_notification(notification)
                    time.sleep(1)
                except Exception as e:
                    logging.info(f"Ошибка push-службы: {e}")
        
        push_thread = threading.Thread(target=push_worker, daemon=True)
        push_thread.start()
    
    def queue_push_notification(self, user_id, title, message, notification_type='info', delay_seconds=0):
        """Добавление push-уведомления в очередь"""
        notification = {
            'user_id': user_id,
            'title': title,
            'message': message,
            'type': notification_type,
            'scheduled_time': datetime.now() + timedelta(seconds=delay_seconds),
            'attempts': 0,
            'max_attempts': 3
        }
        self.push_queue.append(notification)
    
    def send_push_notification(self, notification):
        """Отправка push-уведомления"""
        if datetime.now() < notification['scheduled_time']:
            # Возвращаем в очередь если время еще не пришло
            self.push_queue.append(notification)
            return
        
        try:
            # Получаем telegram_id пользователя
            user = self.db.execute_query(
                'SELECT telegram_id, language FROM users WHERE id = ?',
                (notification['user_id'],)
            )
            
            if user:
                telegram_id, language = user[0]
                
                # Локализуем сообщение
                from localization import t
                localized_title = t(notification['title'], language=language) if notification['title'].startswith('push_') else notification['title']
                localized_message = t(notification['message'], language=language) if notification['message'].startswith('push_') else notification['message']
                
                # Добавляем эмодзи в зависимости от типа
                type_emojis = {
                    'order': '📦',
                    'payment': '💳',
                    'delivery': '🚚',
                    'promotion': '🎁',
                    'reminder': '⏰',
                    'warning': '⚠️',
                    'success': '✅',
                    'info': 'ℹ️'
                }
                
                emoji = type_emojis.get(notification['type'], '📱')
                push_text = f"{emoji} <b>{localized_title}</b>\n\n{localized_message}"
                
                # Отправляем уведомление
                result = self.bot.send_message(telegram_id, push_text)
                
                if result and result.get('ok'):
                    # Сохраняем в базу как доставленное
                    self.db.add_notification(
                        notification['user_id'],
                        localized_title,
                        localized_message,
                        notification['type']
                    )
                    logging.info(f"✅ Push отправлен пользователю {telegram_id}")
                else:
                    raise Exception("Не удалось отправить сообщение")
                    
        except Exception as e:
            notification['attempts'] += 1
            logging.info(f"❌ Ошибка отправки push пользователю {notification['user_id']}: {e}")
            
            # Повторная попытка если не превышен лимит
            if notification['attempts'] < notification['max_attempts']:
                notification['scheduled_time'] = datetime.now() + timedelta(minutes=5)
                self.push_queue.append(notification)
    
    def send_instant_push(self, user_id, title, message, notification_type='info'):
        """Мгновенная отправка push-уведомления"""
        self.queue_push_notification(user_id, title, message, notification_type, 0)
    
    def send_delayed_push(self, user_id, title, message, delay_minutes=0, notification_type='reminder'):
        """Отложенное push-уведомление"""
        self.queue_push_notification(user_id, title, message, notification_type, delay_minutes * 60)
    
    def send_order_notification_to_admins(self, order_id):
        """Уведомление админам о новом заказе"""
        order_details = self.db.get_order_details(order_id)
        if not order_details:
            return
        
        order = order_details['order']
        items = order_details['items']
        
        # Получаем информацию о пользователе
        user = self.db.execute_query(
            'SELECT name, phone, email FROM users WHERE id = ?',
            (order[1],)
        )[0]
        
        notification_text = f"🔔 <b>НОВЫЙ ЗАКАЗ #{order[0]}</b>\n\n"
        notification_text += f"👤 Клиент: {user[0]}\n"
        
        if user[1]:
            notification_text += f"📱 Телефон: {user[1]}\n"
        if user[2]:
            notification_text += f"📧 Email: {user[2]}\n"
        
        notification_text += f"\n💰 Сумма: {format_price(order[2])}\n"
        notification_text += f"📅 Время: {format_date(order[7])}\n"
        
        if order[4]:
            notification_text += f"📍 Адрес: {order[4]}\n"
        
        notification_text += f"💳 Оплата: {order[5]}\n"
        
        notification_text += f"\n🛍 <b>Товары ({len(items)}):</b>\n"
        for item in items:
            notification_text += f"• {item[2]} × {item[0]} = {format_price(item[1] * item[0])}\n"
        
        notification_text += f"\n👆 /admin_order_{order[0]} - управление заказом"
        
        # Отправляем всем админам
        admins = self.db.execute_query(
            'SELECT telegram_id FROM users WHERE is_admin = 1'
        )
        
        for admin in admins:
            try:
                self.bot.send_message(admin[0], notification_text)
                
                # Получаем ID админа в базе
                admin_user = self.db.execute_query(
                    'SELECT id FROM users WHERE telegram_id = ?',
                    (admin[0],)
                )
                if admin_user:
                    # Отправляем push-уведомление
                    self.send_instant_push(
                        admin_user[0][0],
                        f"Новый заказ #{order[0]}",
                        f"Заказ на сумму {format_price(order[2])} от {user[0]}",
                        'order'
                    )
            except Exception as e:
                logging.info(f"Ошибка отправки уведомления админу {admin[0]}: {e}")
    
    def send_order_status_notification(self, order_id, new_status):
        """Уведомление клиенту об изменении статуса заказа"""
        order_details = self.db.get_order_details(order_id)
        if not order_details:
            return
        
        order = order_details['order']
        
        # Получаем пользователя
        user = self.db.execute_query(
            'SELECT telegram_id, name, language FROM users WHERE id = ?',
            (order[1],)
        )[0]
        
        from localization import t
        language = user[2]
        
        status_emoji = self.get_status_emoji(new_status)
        status_text = t(f'status_{new_status}', language=language)
        
        notification_text = f"📦 <b>{t('order_status_update', language=language)} #{order[0]}</b>\n\n"
        notification_text += f"{t('status_changed_to', language=language)}: {status_emoji} <b>{status_text}</b>\n\n"
        
        # Персонализированные сообщения по статусам
        if new_status == 'confirmed':
            notification_text += t('status_confirmed_message', language=language)
        elif new_status == 'shipped':
            notification_text += t('status_shipped_message', language=language)
        elif new_status == 'delivered':
            notification_text += t('status_delivered_message', language=language)
        elif new_status == 'cancelled':
            notification_text += t('status_cancelled_message', language=language)
        
        try:
            self.bot.send_message(user[0], notification_text)
            
            # Отправляем push-уведомление
            user_db_id = self.db.execute_query(
                'SELECT id FROM users WHERE telegram_id = ?',
                (user[0],)
            )[0][0]
            
            self.send_instant_push(
                user_db_id,
                f"push_order_status_update",
                notification_text,
                'order'
            )
            
        except Exception as e:
            logging.info(f"Ошибка отправки уведомления пользователю {user[0]}: {e}")
    
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
    
    def send_low_stock_alert(self):
        """Уведомление админам о товарах с низким остатком"""
        low_stock_products = self.db.execute_query(
            'SELECT name, stock FROM products WHERE stock <= 5 AND is_active = 1'
        )
        
        if not low_stock_products:
            return
        
        alert_text = "⚠️ <b>ВНИМАНИЕ: Заканчиваются товары!</b>\n\n"
        alert_text += "📦 <b>Товары с низким остатком:</b>\n\n"
        
        for product_name, stock in low_stock_products:
            if stock == 0:
                alert_text += f"🔴 <b>{product_name}</b> - НЕТ В НАЛИЧИИ\n"
            else:
                alert_text += f"🟡 <b>{product_name}</b> - осталось {stock} шт.\n"
        
        alert_text += "\n📋 Рекомендуется пополнить склад!"
        
        # Отправляем всем админам
        admins = self.db.execute_query(
            'SELECT telegram_id FROM users WHERE is_admin = 1'
        )
        
        for admin in admins:
            try:
                self.bot.send_message(admin[0], alert_text)
            except Exception as e:
                logging.info(f"Ошибка отправки уведомления о складе админу {admin[0]}: {e}")
    
    def send_daily_summary(self):
        """Ежедневная сводка для админов"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Статистика за день
        daily_stats = self.db.execute_query('''
            SELECT 
                COUNT(*) as orders_count,
                SUM(total_amount) as revenue,
                COUNT(DISTINCT user_id) as unique_customers
            FROM orders 
            WHERE DATE(created_at) = ?
        ''', (today,))
        
        if not daily_stats or daily_stats[0][0] == 0:
            return  # Нет заказов за день
        
        stats = daily_stats[0]
        
        summary_text = f"📊 <b>Сводка за {today}</b>\n\n"
        summary_text += f"📦 Заказов: {stats[0]}\n"
        summary_text += f"💰 Выручка: {format_price(stats[1] or 0)}\n"
        summary_text += f"👥 Уникальных клиентов: {stats[2]}\n\n"
        
        # Топ товары за день
        top_products = self.db.execute_query('''
            SELECT p.name, SUM(oi.quantity) as sold
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE DATE(o.created_at) = ?
            GROUP BY p.id, p.name
            ORDER BY sold DESC
            LIMIT 3
        ''', (today,))
        
        if top_products:
            summary_text += "🏆 <b>Топ товары дня:</b>\n"
            for i, (name, sold) in enumerate(top_products, 1):
                summary_text += f"{i}. {name} - {sold} шт.\n"
        
        # Отправляем админам
        admins = self.db.execute_query(
            'SELECT telegram_id FROM users WHERE is_admin = 1'
        )
        
        for admin in admins:
            try:
                self.bot.send_message(admin[0], summary_text)
            except Exception as e:
                logging.info(f"Ошибка отправки сводки админу {admin[0]}: {e}")
    
    def send_promotional_broadcast(self, message_text, target_group='all'):
        """Рассылка промо-сообщений"""
        if target_group == 'all':
            users = self.db.execute_query(
                'SELECT telegram_id, name, language FROM users WHERE is_admin = 0'
            )
        elif target_group == 'active':
            # Пользователи, делавшие заказы за последние 30 дней
            users = self.db.execute_query('''
                SELECT DISTINCT u.telegram_id, u.name, u.language
                FROM users u
                JOIN orders o ON u.id = o.user_id
                WHERE u.is_admin = 0 AND o.created_at >= datetime('now', '-30 days')
            ''')
        elif target_group == 'inactive':
            # Пользователи без заказов за последние 30 дней
            users = self.db.execute_query('''
                SELECT u.telegram_id, u.name, u.language
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id AND o.created_at >= datetime('now', '-30 days')
                WHERE u.is_admin = 0 AND o.id IS NULL
            ''')
        else:
            return 0, 0
        
        success_count = 0
        error_count = 0
        
        for user in users:
            try:
                # Можно добавить локализацию сообщения по языку пользователя
                localized_message = self.localize_broadcast_message(message_text, user[2])
                self.bot.send_message(user[0], localized_message)
                success_count += 1
            except Exception as e:
                error_count += 1
                logging.info(f"Ошибка рассылки пользователю {user[0]}: {e}")
        
        return success_count, error_count
    
    def localize_broadcast_message(self, message, language):
        """Локализация рассылочного сообщения"""
        if language == 'uz':
            # Простая замена ключевых слов для узбекского
            message = message.replace('Скидка', 'Chegirma')
            message = message.replace('Акция', 'Aksiya')
            message = message.replace('Новинка', 'Yangilik')
            message = message.replace('Товар', 'Mahsulot')
        
        return message
    
    def check_and_send_birthday_notifications(self):
        """Проверка и отправка поздравлений с днем рождения"""
        # Если в будущем добавим поле birthday в таблицу users
        today = datetime.now().strftime('%m-%d')
        
        # Пример запроса (требует добавления поля birthday)
        # birthday_users = self.db.execute_query(
        #     'SELECT telegram_id, name FROM users WHERE strftime("%m-%d", birthday) = ?',
        #     (today,)
        # )
        
        # Пока что заглушка
        birthday_users = []
        
        for user in birthday_users:
            birthday_text = f"🎉 <b>С Днем Рождения, {user[1]}!</b>\n\n"
            birthday_text += "🎁 Специально для вас скидка 15% на все товары!\n"
            birthday_text += "Промокод: BIRTHDAY15\n\n"
            birthday_text += "🛍 Приятных покупок!"
            
            try:
                self.bot.send_message(user[0], birthday_text)
            except Exception as e:
                logging.info(f"Ошибка отправки поздравления {user[0]}: {e}")
    
    def send_cart_abandonment_reminder(self):
        """Напоминание о забытых товарах в корзине"""
        # Пользователи с товарами в корзине старше 24 часов
        abandoned_carts = self.db.execute_query('''
            SELECT DISTINCT u.telegram_id, u.name, u.language,
                   COUNT(c.id) as items_count,
                   SUM(p.price * c.quantity) as total_amount
            FROM users u
            JOIN cart c ON u.id = c.user_id
            JOIN products p ON c.product_id = p.id
            WHERE c.created_at <= datetime('now', '-1 day')
            GROUP BY u.id
        ''')
        
        for user in abandoned_carts:
            from localization import t
            language = user[2]
            
            reminder_text = f"🛒 <b>{t('cart_reminder_title', language=language)}</b>\n\n"
            reminder_text += f"{t('cart_reminder_message', language=language)}\n\n"
            reminder_text += f"📦 {t('items_in_cart', language=language)}: {user[3]}\n"
            reminder_text += f"💰 {t('total_amount', language=language)}: {format_price(user[4])}\n\n"
            reminder_text += f"🎯 {t('cart_reminder_cta', language=language)}"
            
            try:
                self.bot.send_message(user[0], reminder_text)
            except Exception as e:
                logging.info(f"Ошибка отправки напоминания {user[0]}: {e}")
    
    def send_restock_notification(self, product_id):
        """Уведомление о поступлении товара"""
        product = self.db.get_product_by_id(product_id)
        if not product:
            return
        
        # Находим пользователей, которые добавляли этот товар в избранное
        interested_users = self.db.execute_query('''
            SELECT u.telegram_id, u.name, u.language
            FROM users u
            JOIN favorites f ON u.id = f.user_id
            WHERE f.product_id = ?
        ''', (product_id,))
        
        for user in interested_users:
            from localization import t
            language = user[2]
            
            restock_text = f"📦 <b>{t('restock_notification', language=language)}</b>\n\n"
            restock_text += f"🛍 <b>{product[1]}</b>\n"
            restock_text += f"💰 {format_price(product[3])}\n\n"
            restock_text += f"✅ {t('back_in_stock', language=language)}\n"
            restock_text += f"🏃‍♂️ {t('order_now', language=language)}"
            
            try:
                self.bot.send_message(user[0], restock_text)
            except Exception as e:
                logging.info(f"Ошибка уведомления о поступлении {user[0]}: {e}")
    
    def send_weekly_recommendations(self):
        """Еженедельные персональные рекомендации"""
        # Получаем активных пользователей
        active_users = self.db.execute_query('''
            SELECT DISTINCT u.telegram_id, u.name, u.language, u.id
            FROM users u
            JOIN orders o ON u.id = o.user_id
            WHERE u.is_admin = 0 AND o.created_at >= datetime('now', '-30 days')
        ''')
        
        for user in active_users:
            # Получаем рекомендации на основе истории покупок
            recommendations = self.db.execute_query('''
                SELECT DISTINCT p.id, p.name, p.price, p.image_url
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.is_active = 1 
                AND p.id NOT IN (
                    SELECT DISTINCT oi.product_id
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE o.user_id = ?
                )
                AND c.id IN (
                    SELECT DISTINCT p2.category_id
                    FROM products p2
                    JOIN order_items oi2 ON p2.id = oi2.product_id
                    JOIN orders o2 ON oi2.order_id = o2.id
                    WHERE o2.user_id = ?
                )
                ORDER BY p.views DESC, p.sales_count DESC
                LIMIT 3
            ''', (user[3], user[3]))
            
            if recommendations:
                from localization import t
                language = user[2]
                
                rec_text = f"💡 <b>{t('weekly_recommendations', language=language)}</b>\n\n"
                rec_text += f"👋 {user[1]}, {t('recommendations_intro', language=language)}\n\n"
                
                for product in recommendations:
                    rec_text += f"🛍 <b>{product[1]}</b>\n"
                    rec_text += f"💰 {format_price(product[2])}\n\n"
                
                rec_text += f"🎯 {t('check_catalog', language=language)}"
                
                try:
                    self.bot.send_message(user[0], rec_text)
                except Exception as e:
                    logging.info(f"Ошибка отправки рекомендаций {user[0]}: {e}")
    
    def send_promotional_campaign(self, campaign_data):
        """Отправка промо-кампании"""
        target_users = []
        
        # Определяем целевую аудиторию
        if campaign_data['target'] == 'new_users':
            # Новые пользователи (зарегистрированы за последние 7 дней)
            target_users = self.db.execute_query('''
                SELECT telegram_id, name, language
                FROM users
                WHERE is_admin = 0 AND created_at >= datetime('now', '-7 days')
            ''')
        elif campaign_data['target'] == 'big_spenders':
            # Пользователи с заказами на сумму больше $100
            target_users = self.db.execute_query('''
                SELECT DISTINCT u.telegram_id, u.name, u.language
                FROM users u
                JOIN orders o ON u.id = o.user_id
                WHERE u.is_admin = 0 AND o.total_amount >= 100
            ''')
        elif campaign_data['target'] == 'category_buyers':
            # Покупатели определенной категории
            target_users = self.db.execute_query('''
                SELECT DISTINCT u.telegram_id, u.name, u.language
                FROM users u
                JOIN orders o ON u.id = o.user_id
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                WHERE u.is_admin = 0 AND p.category_id = ?
            ''', (campaign_data.get('category_id'),))
        
        success_count = 0
        for user in target_users:
            try:
                # Локализуем сообщение
                localized_message = self.localize_broadcast_message(
                    campaign_data['message'], 
                    user[2]
                )
                
                self.bot.send_message(user[0], localized_message)
                success_count += 1
            except Exception as e:
                logging.info(f"Ошибка рассылки кампании {user[0]}: {e}")
        
        return success_count