"""
Модуль безопасности для телеграм-бота
"""
import logging

import time
import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict

class SecurityManager:
    def __init__(self, db):
        self.db = db
        self.rate_limits = defaultdict(list)
        self.blocked_users = set()
        self.suspicious_activity = defaultdict(int)
        
        # Настройки лимитов
        self.limits = {
            'messages_per_minute': 20,
            'orders_per_hour': 5,
            'search_per_minute': 10,
            'cart_actions_per_minute': 30,
            'callback_per_minute': 50
        }
        
        # Настройки блокировки
        self.block_thresholds = {
            'spam_messages': 50,
            'failed_payments': 10,
            'suspicious_searches': 100
        }
    
    def check_rate_limit(self, user_id, action_type):
        """Проверка лимитов частоты запросов"""
        now = time.time()
        user_key = f"{user_id}_{action_type}"
        
        # Очищаем старые записи
        self.rate_limits[user_key] = [
            timestamp for timestamp in self.rate_limits[user_key]
            if now - timestamp < 60  # Последняя минута
        ]
        
        # Проверяем лимит
        limit_key = f"{action_type}_per_minute"
        if limit_key in self.limits:
            if len(self.rate_limits[user_key]) >= self.limits[limit_key]:
                self.log_suspicious_activity(user_id, f"rate_limit_exceeded_{action_type}")
                return False
        
        # Добавляем текущий запрос
        self.rate_limits[user_key].append(now)
        return True
    
    def is_user_blocked(self, user_id):
        """Проверка блокировки пользователя"""
        return user_id in self.blocked_users
    
    def block_user(self, user_id, reason, duration_hours=24):
        """Блокировка пользователя"""
        self.blocked_users.add(user_id)
        
        # Сохраняем в базу
        try:
            self.db.execute_query('''
                INSERT INTO security_blocks (user_id, reason, blocked_until, created_at)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                reason,
                (datetime.now() + timedelta(hours=duration_hours)).strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        except Exception as e:
            logging.info(f"Ошибка записи блокировки: {e}")
        
        self.log_security_event(user_id, 'user_blocked', {'reason': reason, 'duration': duration_hours})
    
    def log_suspicious_activity(self, user_id, activity_type, details=""):
        """Логирование подозрительной активности"""
        self.suspicious_activity[f"{user_id}_{activity_type}"] += 1
        
        # Сохраняем в базу
        try:
            self.db.execute_query('''
                INSERT INTO security_logs (user_id, activity_type, details, severity, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                activity_type,
                details,
                self.get_activity_severity(activity_type),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        except Exception as e:
            logging.info(f"Ошибка записи лога безопасности: {e}")
    
    def get_activity_severity(self, activity_type):
        """Определение серьезности активности"""
        high_severity = ['sql_injection_attempt', 'multiple_failed_payments', 'bot_behavior']
        medium_severity = ['rate_limit_exceeded', 'suspicious_search_patterns']
        
        if activity_type in high_severity:
            return 'high'
        elif activity_type in medium_severity:
            return 'medium'
        else:
            return 'low'
    
    def log_security_event(self, user_id, event_type, details=None):
        """Логирование событий безопасности"""
        details_json = json.dumps(details) if details else None
        
        try:
            self.db.execute_query('''
                INSERT INTO security_logs (user_id, activity_type, details, severity, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                event_type,
                details_json,
                'info',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        except Exception as e:
            logging.info(f"Ошибка записи события безопасности: {e}")
    
    def verify_webhook_signature(self, payload, signature, secret_key):
        """Проверка подписи webhook'а"""
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)

class AntiSpamFilter:
    def __init__(self, db):
        self.db = db
        self.spam_patterns = [
            r'(https?://[^\s]+)',  # URL
            r'(@\w+)',  # Упоминания
            r'(\b\d{4,}\b)',  # Длинные числа
            r'(СКИДКА|АКЦИЯ|БЕСПЛАТНО|FREE)',  # Спам слова
        ]
        self.blacklist = set()
    
    def is_spam(self, message):
        """Проверка сообщения на спам"""
        if not message:
            return False
        
        message_upper = message.upper()
        
        # Проверяем спам-паттерны
        spam_score = 0
        for pattern in self.spam_patterns:
            if re.search(pattern, message_upper):
                spam_score += 1
        
        # Проверяем повторяющиеся символы
        if re.search(r'(.)\1{5,}', message):
            spam_score += 2
        
        # Проверяем капс
        if len(message) > 10 and message.isupper():
            spam_score += 1
        
        return spam_score >= 3
    
    def add_to_blacklist(self, user_id):
        """Добавление в черный список"""
        self.blacklist.add(user_id)

class InputSanitizer:
    @staticmethod
    def sanitize_text(text):
        """Очистка текста от опасных символов"""
        if not text:
            return text
        
        # Удаляем потенциально опасные символы
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        # Ограничиваем длину
        return text[:1000]
    
    @staticmethod
    def validate_email(email):
        """Проверка email"""
        if not email:
            return True
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone):
        """Проверка телефона"""
        if not phone:
            return True
        
        # Убираем все кроме цифр и +
        clean_phone = re.sub(r'[^\d+]', '', phone)
        return len(clean_phone) >= 10

class ActivityLogger:
    def __init__(self, db):
        self.db = db
    
    def log_action(self, user_id, action, details=""):
        """Логирование действий пользователя"""
        try:
            self.db.execute_query('''
                INSERT INTO user_activity_logs (user_id, action, search_query, created_at)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                action,
                details[:100] if details else None,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        except Exception as e:
            logging.info(f"Ошибка логирования активности: {e}")