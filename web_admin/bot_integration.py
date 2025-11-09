"""
Интеграция веб-админ панели с Telegram ботом
"""
import logging

import sys
import os
import json
import urllib.request
import urllib.parse
import time

# Добавляем путь к модулям бота
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BOT_TOKEN, POST_CHANNEL_ID

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TelegramBotIntegration:
    def __init__(self):
        self.token = BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.channel_id = POST_CHANNEL_ID
    
    def trigger_bot_data_reload(self):
        """Сигнал боту о необходимости перезагрузки данных"""
        try:
            # Создаем файл-флаг для бота
            update_flag_file = os.path.join(BASE_DIR, 'data_update_flag.txt')
            with open(update_flag_file, 'w') as f:
                f.write(str(time.time()))
            return True
        except Exception as e:
            logging.info(f"Ошибка создания флага обновления: {e}")
            return False
    
    def send_message(self, chat_id, text, reply_markup=None):
        """Отправка сообщения через Telegram API"""
        url = f"{self.base_url}/sendMessage"
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
                return result
        except Exception as e:
            logging.info(f"Ошибка отправки сообщения: {e}")
            return None
    
    def send_to_channel(self, message):
        """Отправка сообщения в канал"""
        return self.send_message(self.channel_id, message, None)
    
    def send_photo_to_channel(self, photo_url, caption="", reply_markup=None):
        """Отправка фото в канал"""
        return self.send_photo(self.channel_id, photo_url, caption, reply_markup)
    
    def send_photo(self, chat_id, photo_url, caption="", reply_markup=None):
        """Отправка фото"""
        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
        data = {
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        try:
            data_encoded = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_encoded, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result
        except Exception as e:
            logging.info(f"Ошибка отправки фото: {e}")
            return None
    
    def send_broadcast(self, message, user_list):
        """Массовая рассылка"""
        success_count = 0
        error_count = 0
        
        for user in user_list:
            telegram_id = user[0] if isinstance(user, (list, tuple)) else user.get('telegram_id')
            try:
                result = self.send_message(telegram_id, message)
                if result and result.get('ok'):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                logging.info(f"Ошибка отправки пользователю {telegram_id}: {e}")
        
        return success_count, error_count
    
    def notify_admins(self, message):
        """Уведомление всех админов"""
        try:
            from database import DatabaseManager
            db = DatabaseManager()
            
            admins = db.execute_query(
                'SELECT telegram_id FROM users WHERE is_admin = 1'
            )
            
            for admin in admins:
                self.send_message(admin[0], message)
                
        except Exception as e:
            logging.info(f"Ошибка уведомления админов: {e}")
    
    def test_connection(self):
        """Тестирование соединения с Telegram"""
        try:
            url = f"{self.base_url}/getMe"
            with urllib.request.urlopen(url) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('ok', False)
        except Exception as e:
            logging.info(f"Ошибка тестирования соединения: {e}")
            return False

# Глобальный экземпляр для использования в Flask
telegram_bot = TelegramBotIntegration()