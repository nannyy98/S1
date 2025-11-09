import logging
#!/usr/bin/env python3
"""
Скрипт для исправления проблем с базой данных
"""

import sqlite3
import os

def fix_database_issues():
    """Исправление проблем с базой данных"""
    logging.info("🔧 Исправление базы данных...")
    
    if not os.path.exists('shop_bot.db'):
        logging.info("❌ База данных не найдена")
        return False
    
    try:
        conn = sqlite3.connect('shop_bot.db')
        cursor = conn.cursor()
        
        logging.info("1. Проверка и исправление категорий...")
        
        # Проверяем категории
        cursor.execute('SELECT COUNT(*) FROM categories')
        categories_count = cursor.fetchone()[0]
        
        if categories_count == 0:
            logging.info("   Создаем категории...")
            categories = [
                ('Электроника', 'Смартфоны, ноутбуки, гаджеты', '📱'),
                ('Одежда', 'Мужская и женская одежда', '👕'),
                ('Дом и сад', 'Товары для дома и дачи', '🏠'),
                ('Спорт', 'Спортивные товары и инвентарь', '⚽'),
                ('Красота', 'Косметика и парфюмерия', '💄'),
                ('Книги', 'Художественная и техническая литература', '📚')
            ]
            
            cursor.executemany(
                'INSERT INTO categories (name, description, emoji) VALUES (?, ?, ?)',
                categories
            )
            logging.info(f"   ✅ Создано {len(categories)} категорий")
        
        logging.info("2. Проверка и исправление товаров...")
        
        # Проверяем товары
        cursor.execute('SELECT COUNT(*) FROM products')
        products_count = cursor.fetchone()[0]
        
        if products_count == 0:
            logging.info("   Создаем товары...")
            products = [
                ('iPhone 14', 'Смартфон Apple iPhone 14 128GB', 799.99, 1, 'https://images.pexels.com/photos/788946/pexels-photo-788946.jpeg', 50, 0, 0, 1, 600.00),
                ('Samsung Galaxy S23', 'Флагманский смартфон Samsung', 699.99, 1, 'https://images.pexels.com/photos/1092644/pexels-photo-1092644.jpeg', 30, 0, 0, 1, 500.00),
                ('MacBook Air M2', 'Ноутбук Apple MacBook Air с чипом M2', 1199.99, 1, 'https://images.pexels.com/photos/18105/pexels-photo.jpg', 20, 0, 0, 1, 900.00),
                ('Футболка Nike', 'Спортивная футболка Nike Dri-FIT', 29.99, 2, 'https://images.pexels.com/photos/8532616/pexels-photo-8532616.jpeg', 100, 0, 0, 1, 15.00),
                ('Джинсы Levi\'s', 'Классические джинсы Levi\'s 501', 79.99, 2, 'https://images.pexels.com/photos/1598507/pexels-photo-1598507.jpeg', 75, 0, 0, 1, 40.00),
                ('Кофеварка Delonghi', 'Автоматическая кофеварка', 299.99, 3, 'https://images.pexels.com/photos/324028/pexels-photo-324028.jpeg', 25, 0, 0, 1, 180.00),
                ('Набор посуды', 'Набор кастрюль из нержавеющей стали', 149.99, 3, 'https://images.pexels.com/photos/4226796/pexels-photo-4226796.jpeg', 40, 0, 0, 1, 80.00),
                ('Кроссовки Adidas', 'Беговые кроссовки Adidas Ultraboost', 159.99, 4, 'https://images.pexels.com/photos/2529148/pexels-photo-2529148.jpeg', 60, 0, 0, 1, 90.00),
                ('Гантели 10кг', 'Набор гантелей для домашних тренировок', 89.99, 4, 'https://images.pexels.com/photos/416717/pexels-photo-416717.jpeg', 35, 0, 0, 1, 50.00),
                ('Крем для лица', 'Увлажняющий крем с гиалуроновой кислотой', 49.99, 5, 'https://images.pexels.com/photos/3685530/pexels-photo-3685530.jpeg', 80, 0, 0, 1, 25.00),
                ('Парфюм Chanel', 'Туалетная вода Chanel No.5', 129.99, 5, 'https://images.pexels.com/photos/965989/pexels-photo-965989.jpeg', 45, 0, 0, 1, 70.00),
                ('Книга "Python для начинающих"', 'Учебник по программированию на Python', 39.99, 6, 'https://images.pexels.com/photos/159711/books-bookstore-book-reading-159711.jpeg', 90, 0, 0, 1, 20.00),
                ('Роман "1984"', 'Классический роман Джорджа Оруэлла', 19.99, 6, 'https://images.pexels.com/photos/46274/pexels-photo-46274.jpeg', 120, 0, 0, 1, 10.00),
                ('Беспроводные наушники', 'AirPods Pro с шумоподавлением', 249.99, 1, 'https://images.pexels.com/photos/3394650/pexels-photo-3394650.jpeg', 70, 0, 0, 1, 150.00)
            ]
            
            cursor.executemany('''
                INSERT INTO products (name, description, price, category_id, image_url, stock, views, sales_count, is_active, cost_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', products)
            logging.info(f"   ✅ Создано {len(products)} товаров")
        
        logging.info("3. Исправление проблем...")
        
        # Активируем все товары
        cursor.execute('UPDATE products SET is_active = 1 WHERE is_active = 0')
        activated = cursor.rowcount
        if activated > 0:
            logging.info(f"   ✅ Активировано {activated} товаров")
        
        # Устанавливаем остатки
        cursor.execute('UPDATE products SET stock = 50 WHERE stock <= 0')
        restocked = cursor.rowcount
        if restocked > 0:
            logging.info(f"   ✅ Восстановлены остатки для {restocked} товаров")
        
        # Проверяем админа из .env
        admin_telegram_id = os.getenv('ADMIN_TELEGRAM_ID', '5720497431')
        admin_name = os.getenv('ADMIN_NAME', 'Admin')
        
        if admin_telegram_id:
            try:
                admin_telegram_id = int(admin_telegram_id)
                
                cursor.execute('SELECT id, is_admin FROM users WHERE telegram_id = ?', (admin_telegram_id,))
                existing_admin = cursor.fetchone()
                
                if existing_admin:
                    if existing_admin[1] != 1:
                        cursor.execute('UPDATE users SET is_admin = 1 WHERE telegram_id = ?', (admin_telegram_id,))
                        logging.info(f"   ✅ Права админа обновлены для {admin_name}")
                    else:
                        logging.info(f"   ✅ Админ уже существует: {admin_name}")
                else:
                    cursor.execute('''
                        INSERT INTO users (telegram_id, name, is_admin, language, created_at)
                        VALUES (?, ?, 1, 'ru', CURRENT_TIMESTAMP)
                    ''', (admin_telegram_id, admin_name))
                    logging.info(f"   ✅ Создан новый админ: {admin_name} (ID: {admin_telegram_id})")
                    
            except ValueError:
                logging.info(f"   ❌ Неверный ADMIN_TELEGRAM_ID: {admin_telegram_id}")
        else:
            logging.info("   ⚠️ ADMIN_TELEGRAM_ID не найден, создаю с ID по умолчанию")
            cursor.execute('''
                INSERT OR IGNORE INTO users (telegram_id, name, is_admin, language, created_at)
                VALUES (5720497431, 'Admin', 1, 'ru', CURRENT_TIMESTAMP)
            ''')
            logging.info("   ✅ Создан админ по умолчанию: Admin (ID: 5720497431)")
        
        conn.commit()
        conn.close()
        
        logging.info("\n🎉 База данных исправлена!")
        return True
        
    except Exception as e:
        logging.info(f"❌ Ошибка исправления базы: {e}")
        return False

def show_debug_info():
    """Показ отладочной информации"""
    logging.info("\n🔍 Отладочная информация:")
    
    try:
        conn = sqlite3.connect('shop_bot.db')
        cursor = conn.cursor()
        
        # Показываем структуру таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logging.info(f"📋 Таблицы в базе: {[table[0] for table in tables]}")
        
        # Показываем примеры данных
        cursor.execute('SELECT id, name, emoji FROM categories LIMIT 3')
        sample_categories = cursor.fetchall()
        logging.info(f"📂 Примеры категорий: {sample_categories}")
        
        cursor.execute('SELECT id, name, category_id, is_active, stock FROM products LIMIT 3')
        sample_products = cursor.fetchall()
        logging.info(f"🛍 Примеры товаров: {sample_products}")
        
        conn.close()
        
    except Exception as e:
        logging.info(f"❌ Ошибка получения отладочной информации: {e}")

if __name__ == "__main__":
    # Загружаем .env если есть
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    logging.info("🧪 Диагностика и исправление бота")
    logging.info("=" * 40)
    
    if fix_database_issues():
        show_debug_info()
        logging.info("\n🚀 Теперь можно запускать бота: python main.py")
    else:
        logging.info("\n❌ Исправьте ошибки перед запуском")