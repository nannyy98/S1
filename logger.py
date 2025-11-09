"""
Система логирования для продакшена
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from config import LOGGING_CONFIG

class ProductionLogger:
    def __init__(self):
        self.setup_logging()
    
    def setup_logging(self):
        """Настройка системы логирования"""
        # Создаем директорию для логов
        log_dir = os.path.dirname(LOGGING_CONFIG['file']) or 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        # Основной логгер
        self.logger = logging.getLogger('shop_bot')
        self.logger.setLevel(getattr(logging, LOGGING_CONFIG['level']))
        
        # Очищаем существующие обработчики
        self.logger.handlers.clear()
        
        # Форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        
        # Консольный вывод
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Файловый вывод с ротацией
        file_handler = logging.handlers.RotatingFileHandler(
            LOGGING_CONFIG['file'],
            maxBytes=LOGGING_CONFIG['max_size'],
            backupCount=LOGGING_CONFIG['backup_count'],
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Отдельный файл для ошибок
        error_handler = logging.handlers.RotatingFileHandler(
            LOGGING_CONFIG['file'].replace('.log', '_errors.log'),
            maxBytes=LOGGING_CONFIG['max_size'],
            backupCount=LOGGING_CONFIG['backup_count'],
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
        
        # Логгер для безопасности
        self.security_logger = logging.getLogger('shop_bot.security')
        security_handler = logging.handlers.RotatingFileHandler(
            'logs/security.log',
            maxBytes=LOGGING_CONFIG['max_size'],
            backupCount=LOGGING_CONFIG['backup_count'],
            encoding='utf-8'
        )
        security_handler.setFormatter(formatter)
        self.security_logger.addHandler(security_handler)
        self.security_logger.setLevel(logging.INFO)
    
    def info(self, message, extra=None):
        """Информационное сообщение"""
        self.logger.info(message, extra=extra)
    
    def warning(self, message, extra=None):
        """Предупреждение"""
        self.logger.warning(message, extra=extra)
    
    def error(self, message, exc_info=None, extra=None):
        """Ошибка"""
        self.logger.error(message, exc_info=exc_info, extra=extra)
    
    def critical(self, message, exc_info=None, extra=None):
        """Критическая ошибка"""
        self.logger.critical(message, exc_info=exc_info, extra=extra)
    
    def security(self, message, user_id=None, action=None):
        """Лог безопасности"""
        extra_info = {
            'user_id': user_id,
            'action': action,
            'timestamp': datetime.now().isoformat()
        }
        self.security_logger.info(f"SECURITY: {message}", extra=extra_info)
    
    def performance(self, operation, duration, details=None):
        """Лог производительности"""
        perf_message = f"PERFORMANCE: {operation} took {duration:.3f}s"
        if details:
            perf_message += f" - {details}"
        self.logger.info(perf_message)

# Глобальный экземпляр логгера
logger = ProductionLogger()