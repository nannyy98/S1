"""
Система мониторинга здоровья бота
"""

import time
import threading
import psutil
from datetime import datetime
from config import MONITORING_CONFIG
from logger import logger

class HealthMonitor:
    def __init__(self, db, bot):
        self.db = db
        self.bot = bot
        self.metrics = {
            'start_time': time.time(),
            'messages_processed': 0,
            'errors_count': 0,
            'last_error': None,
            'database_status': 'unknown',
            'memory_usage': 0,
            'cpu_usage': 0
        }
        self.start_monitoring()
    
    def start_monitoring(self):
        """Запуск мониторинга"""
        def monitor_worker():
            while True:
                try:
                    self.update_metrics()
                    self.check_health()
                    time.sleep(MONITORING_CONFIG['health_check_interval'])
                except Exception as e:
                    logger.error(f"Ошибка мониторинга: {e}", exc_info=True)
                    time.sleep(60)
        
        monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
        monitor_thread.start()
        logger.info("Система мониторинга запущена")
    
    def update_metrics(self):
        """Обновление метрик"""
        # Системные метрики
        process = psutil.Process()
        self.metrics['memory_usage'] = process.memory_info().rss / 1024 / 1024  # MB
        self.metrics['cpu_usage'] = process.cpu_percent()
        
        # Проверка базы данных
        try:
            self.db.execute_query('SELECT 1')
            self.metrics['database_status'] = 'healthy'
        except Exception as e:
            self.metrics['database_status'] = 'error'
            logger.error(f"Ошибка базы данных: {e}")
        
        # Время работы
        uptime = time.time() - self.metrics['start_time']
        self.metrics['uptime_hours'] = uptime / 3600
    
    def check_health(self):
        """Проверка здоровья системы"""
        issues = []
        
        # Проверка памяти
        if self.metrics['memory_usage'] > 500:  # 500MB
            issues.append(f"Высокое потребление памяти: {self.metrics['memory_usage']:.1f}MB")
        
        # Проверка CPU
        if self.metrics['cpu_usage'] > 80:
            issues.append(f"Высокая загрузка CPU: {self.metrics['cpu_usage']:.1f}%")
        
        # Проверка базы данных
        if self.metrics['database_status'] != 'healthy':
            issues.append("Проблемы с базой данных")
        
        # Проверка ошибок
        if self.metrics['errors_count'] > 100:
            issues.append(f"Много ошибок: {self.metrics['errors_count']}")
        
        if issues:
            logger.warning(f"Проблемы со здоровьем системы: {'; '.join(issues)}")
            self.send_alert_to_admins(issues)
    
    def send_alert_to_admins(self, issues):
        """Отправка алертов админам"""
        try:
            admins = self.db.execute_query('SELECT telegram_id FROM users WHERE is_admin = 1')
            
            alert_message = "🚨 <b>СИСТЕМНОЕ ПРЕДУПРЕЖДЕНИЕ</b>\n\n"
            alert_message += "Обнаружены проблемы:\n"
            for issue in issues:
                alert_message += f"• {issue}\n"
            
            alert_message += f"\n📊 Метрики:\n"
            alert_message += f"💾 Память: {self.metrics['memory_usage']:.1f}MB\n"
            alert_message += f"⚡ CPU: {self.metrics['cpu_usage']:.1f}%\n"
            alert_message += f"🕐 Время работы: {self.metrics['uptime_hours']:.1f}ч\n"
            alert_message += f"📨 Сообщений: {self.metrics['messages_processed']}\n"
            
            for admin in admins:
                self.bot.send_message(admin[0], alert_message)
                
        except Exception as e:
            logger.error(f"Ошибка отправки алерта: {e}")
    
    def increment_messages(self):
        """Увеличить счетчик сообщений"""
        self.metrics['messages_processed'] += 1
    
    def increment_errors(self, error_message=None):
        """Увеличить счетчик ошибок"""
        self.metrics['errors_count'] += 1
        if error_message:
            self.metrics['last_error'] = {
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_health_status(self):
        """Получить статус здоровья"""
        return {
            'status': 'healthy' if self.metrics['database_status'] == 'healthy' else 'unhealthy',
            'uptime': self.metrics['uptime_hours'],
            'memory_mb': self.metrics['memory_usage'],
            'cpu_percent': self.metrics['cpu_usage'],
            'messages_processed': self.metrics['messages_processed'],
            'errors_count': self.metrics['errors_count'],
            'database_status': self.metrics['database_status']
        }
    
    def create_health_endpoint(self):
        """Создание HTTP endpoint для проверки здоровья"""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json
        
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/health':
                    health_status = self.server.health_monitor.get_health_status()
                    
                    self.send_response(200 if health_status['status'] == 'healthy' else 503)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    
                    response = json.dumps(health_status, indent=2)
                    self.wfile.write(response.encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Отключаем логи HTTP сервера
        
        def start_health_server():
            try:
                server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
                server.health_monitor = self
                logger.info("Health check сервер запущен на порту 8080")
                server.serve_forever()
            except Exception as e:
                logger.error(f"Ошибка запуска health check сервера: {e}")
        
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()