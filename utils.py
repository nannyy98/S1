"""
Вспомогательные функции для телеграм-бота
"""
import logging

from datetime import datetime
import re

def format_price(price):
    """Форматирование цены"""
    return f"${price:.2f}"

def format_date(date_string):
    """Форматирование даты"""
    try:
        if isinstance(date_string, str):
            if 'T' in date_string:
                date_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            else:
                date_obj = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
        else:
            date_obj = date_string
        return date_obj.strftime('%d.%m.%Y %H:%M')
    except Exception as e:
        logging.info(f"Ошибка форматирования даты {date_string}: {e}")
        return date_string

def validate_email(email):
    """Проверка корректности email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Проверка корректности номера телефона"""
    # Убираем все символы кроме цифр и +
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Проверяем длину и формат
    if len(clean_phone) >= 10 and (clean_phone.startswith('+') or clean_phone.isdigit()):
        return clean_phone
    return None

def truncate_text(text, max_length=100):
    """Обрезка текста до указанной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def create_pagination_keyboard(current_page, total_pages, callback_prefix):
    """Создание клавиатуры для пагинации"""
    keyboard = []
    
    if total_pages > 1:
        row = []
        
        if current_page > 1:
            row.append({
                'text': '⬅️ Назад',
                'callback_data': f'{callback_prefix}_{current_page - 1}'
            })
        
        row.append({
            'text': f'{current_page}/{total_pages}',
            'callback_data': 'current_page'
        })
        
        if current_page < total_pages:
            row.append({
                'text': 'Вперед ➡️',
                'callback_data': f'{callback_prefix}_{current_page + 1}'
            })
        
        keyboard.append(row)
    
    return keyboard

def escape_html(text):
    """Экранирование HTML символов"""
    if not text:
        return ""
    
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))

def calculate_cart_total(cart_items):
    """Подсчет общей суммы корзины"""
    return sum(item[2] * item[3] for item in cart_items)

def format_cart_summary(cart_items):
    """Форматирование краткой информации о корзине"""
    if not cart_items:
        return "Корзина пуста"
    
    total_items = sum(item[3] for item in cart_items)
    total_price = calculate_cart_total(cart_items)
    
    return f"🛒 {total_items} товар(ов) на сумму {format_price(total_price)}"

def get_order_status_emoji(status):
    """Получение эмодзи для статуса заказа"""
    status_emojis = {
        'pending': '⏳',
        'confirmed': '✅',
        'shipped': '🚚',
        'delivered': '📦',
        'cancelled': '❌'
    }
    return status_emojis.get(status, '❓')

def get_order_status_text(status):
    """Получение текста для статуса заказа"""
    status_texts = {
        'pending': 'В обработке',
        'confirmed': 'Подтвержден',
        'shipped': 'Отправлен',
        'delivered': 'Доставлен',
        'cancelled': 'Отменен'
    }
    return status_texts.get(status, 'Неизвестно')

def create_product_card(product):
    """Создание карточки товара"""
    # 0:id,1:name,2:description,3:price,7:image_url,8:stock,9:views
    name = product[1]
    description = product[2] if len(product) > 2 else ''
    price = product[3] if len(product) > 3 else 0
    stock = product[8] if len(product) > 8 else 0
    views = product[9] if len(product) > 9 else 0

    nl = chr(10)
    card = "<b>" + escape_html(name) + "</b>" + nl + nl
    if description:
        card += escape_html(truncate_text(description, 150)) + nl + nl
    card += "💰 Цена: <b>" + format_price(price) + "</b>" + nl
    card += "📦 В наличии: " + str(stock) + " шт." + nl
    card += "👁 Просмотров: " + str(views) + nl
    return card

def log_user_action(telegram_id, action, details=""):
    """Логирование действий пользователя"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{timestamp}] User {telegram_id}: {action} {details}")

def format_order_summary(order, items):
    """Форматирование краткой информации о заказе"""
    status_emoji = get_order_status_emoji(order[3])
    
    summary = f"{status_emoji} Заказ #{order[0]} - {format_price(order[2])}\n"
    summary += f"📅 {format_date(order[7])}\n"
    summary += f"📦 {len(items)} товар(ов)"
    
    return summary

def create_stars_display(rating):
    """Создание отображения звезд для рейтинга"""
    full_stars = int(rating)
    half_star = 1 if rating - full_stars >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    
    stars = '⭐' * full_stars
    if half_star:
        stars += '✨'
    stars += '☆' * empty_stars
    
    return stars

def send_telegram_message(bot_token, chat_id, text, reply_markup=None):
    """Универсальная функция отправки сообщений"""
    import json
    import urllib.request
    import urllib.parse
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    
    try:
        data_encoded = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(url, data=data_encoded, method='POST')
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('ok', False)
    except Exception as e:
        logging.info(f"Ошибка отправки сообщения: {e}")
        return False

def schedule_notification(notification_manager, notification_type, delay_hours=0):
    """Планирование отправки уведомлений"""
    import time
    import threading
    
    def delayed_notification():
        if delay_hours > 0:
            time.sleep(delay_hours * 3600)  # Конвертируем часы в секунды
        
        if notification_type == 'low_stock':
            notification_manager.send_low_stock_alert()
        elif notification_type == 'daily_summary':
            notification_manager.send_daily_summary()
        elif notification_type == 'cart_abandonment':
            notification_manager.send_cart_abandonment_reminder()
        elif notification_type == 'weekly_recommendations':
            notification_manager.send_weekly_recommendations()
    
    # Запускаем в отдельном потоке
    thread = threading.Thread(target=delayed_notification)
    thread.daemon = True
    thread.start()

def format_notification_summary(notifications):
    """Форматирование сводки уведомлений"""
    if not notifications:
        return "🔔 Новых уведомлений нет"
    
    summary = f"🔔 <b>У вас {len(notifications)} новых уведомлений:</b>\n\n"
    
    for notif in notifications[:5]:  # Показываем первые 5
        type_emoji = {
            'order': '📦',
            'order_status': '📋',
            'promotion': '🎁',
            'system': '⚙️',
            'info': 'ℹ️'
        }.get(notif[4], 'ℹ️')
        
        summary += f"{type_emoji} <b>{notif[2]}</b>\n"
        summary += f"   {truncate_text(notif[3], 60)}\n"
        summary += f"   📅 {format_date(notif[6])}\n\n"
    
    if len(notifications) > 5:
        summary += f"... и еще {len(notifications) - 5} уведомлений\n\n"
    
    summary += "📋 Используйте команду /notifications для просмотра всех"
    
    return summary

def send_push_to_user(bot, user_id, title, message, notification_type='info'):
    """Отправка push-уведомления конкретному пользователю"""
    try:
        # Получаем telegram_id пользователя
        from database import DatabaseManager
        db = DatabaseManager()
        
        user = db.execute_query(
            'SELECT telegram_id, language FROM users WHERE id = ?',
            (user_id,)
        )
        
        if user:
            telegram_id, language = user[0]
            
            # Локализуем сообщение
            from localization import t
            localized_title = t(title, language=language) if title.startswith('push_') else title
            localized_message = t(message, language=language) if message.startswith('push_') else message
            
            # Добавляем эмодзи
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
            
            emoji = type_emojis.get(notification_type, '📱')
            push_text = f"{emoji} <b>{localized_title}</b>\n\n{localized_message}"
            
            # Отправляем
            result = bot.send_message(telegram_id, push_text)
            
            if result and result.get('ok'):
                # Сохраняем в базу
                db.add_notification(user_id, localized_title, localized_message, notification_type)
                return True
                
    except Exception as e:
        logging.info(f"Ошибка отправки push-уведомления: {e}")
    
    return False

def schedule_push_notification(notification_manager, user_id, title, message, delay_minutes=0, notification_type='reminder'):
    """Планирование отложенного push-уведомления"""
    notification_manager.send_delayed_push(
        user_id, title, message, delay_minutes, notification_type
    )