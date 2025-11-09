"""
Система резервного копирования базы данных
"""

import os
import shutil
import sqlite3
import gzip
import threading
import time
from datetime import datetime, timedelta
from config import DATABASE_CONFIG
from logger import logger

class DatabaseBackup:
    def __init__(self, db_path):
        self.db_path = db_path
        self.backup_dir = 'backups'
        os.makedirs(self.backup_dir, exist_ok=True)
        self.start_backup_scheduler()
    
    def start_backup_scheduler(self):
        """Запуск планировщика резервного копирования"""
        def backup_worker():
            while True:
                try:
                    self.create_backup()
                    self.cleanup_old_backups()
                    time.sleep(DATABASE_CONFIG['backup_interval'])
                except Exception as e:
                    logger.error(f"Ошибка резервного копирования: {e}", exc_info=True)
                    time.sleep(3600)  # Повтор через час при ошибке
        
        backup_thread = threading.Thread(target=backup_worker, daemon=True)
        backup_thread.start()
        logger.info("Планировщик резервного копирования запущен")
    
    def create_backup(self):
        """Создание резервной копии"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"shop_bot_backup_{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            # Создаем резервную копию с блокировкой
            source_conn = sqlite3.connect(self.db_path)
            source_conn.execute('BEGIN IMMEDIATE;')
            
            # Копируем базу данных
            shutil.copy2(self.db_path, backup_path)
            
            source_conn.rollback()
            source_conn.close()
            
            # Сжимаем резервную копию
            compressed_path = f"{backup_path}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Удаляем несжатую копию
            os.remove(backup_path)
            
            # Проверяем целостность
            if self.verify_backup(compressed_path):
                logger.info(f"Резервная копия создана: {compressed_path}")
                return compressed_path
            else:
                logger.error(f"Резервная копия повреждена: {compressed_path}")
                os.remove(compressed_path)
                return None
                
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}", exc_info=True)
            return None
    
    def verify_backup(self, backup_path):
        """Проверка целостности резервной копии"""
        try:
            # Распаковываем во временный файл
            temp_path = backup_path.replace('.gz', '.temp')
            
            with gzip.open(backup_path, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Проверяем базу данных
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            
            # Проверяем основные таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            required_tables = ['users', 'products', 'orders', 'categories']
            existing_tables = [table[0] for table in tables]
            
            for required_table in required_tables:
                if required_table not in existing_tables:
                    conn.close()
                    os.remove(temp_path)
                    return False
            
            # Проверяем количество записей
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            conn.close()
            os.remove(temp_path)
            
            return user_count >= 0  # Базовая проверка
            
        except Exception as e:
            logger.error(f"Ошибка проверки резервной копии: {e}")
            return False
    
    def cleanup_old_backups(self, keep_days=7):
        """Очистка старых резервных копий"""
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('shop_bot_backup_') and filename.endswith('.db.gz'):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        logger.info(f"Удалена старая резервная копия: {filename}")
                        
        except Exception as e:
            logger.error(f"Ошибка очистки старых копий: {e}")
    
    def restore_backup(self, backup_path):
        """Восстановление из резервной копии"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Резервная копия не найдена: {backup_path}")
                return False
            
            # Создаем резервную копию текущей базы
            current_backup = f"{self.db_path}.before_restore"
            shutil.copy2(self.db_path, current_backup)
            
            # Распаковываем резервную копию
            if backup_path.endswith('.gz'):
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(self.db_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(backup_path, self.db_path)
            
            # Проверяем восстановленную базу
            if self.verify_backup(self.db_path):
                logger.info(f"База данных восстановлена из: {backup_path}")
                return True
            else:
                # Откатываем изменения
                shutil.copy2(current_backup, self.db_path)
                logger.error("Ошибка восстановления, откат изменений")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка восстановления: {e}", exc_info=True)
            return False
    
    def list_backups(self):
        """Список доступных резервных копий"""
        backups = []
        
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('shop_bot_backup_') and filename.endswith('.db.gz'):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_size = os.path.getsize(file_path)
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    backups.append({
                        'filename': filename,
                        'path': file_path,
                        'size_mb': file_size / 1024 / 1024,
                        'created': file_time.isoformat()
                    })
            
            return sorted(backups, key=lambda x: x['created'], reverse=True)
            
        except Exception as e:
            logger.error(f"Ошибка получения списка копий: {e}")
            return []