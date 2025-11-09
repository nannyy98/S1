"""
Модуль автоматических постов для телеграм-бота
"""
import logging

import threading
import html
import time
from logger import logger

# Простой планировщик без внешних зависимостей
class SimpleScheduler:
    def __init__(self):
        self.jobs = []
    
    def every(self):
        return ScheduleJob(self)
    
    def run_pending(self):
        import time
        now = time.time()
        current_time = time.strftime('%H:%M', time.localtime(now))
        current_date = time.strftime('%Y-%m-%d', time.localtime(now))
        
        for job in self.jobs:
            if job.should_run(current_time, current_date):
                try:
                    job.run()
                except Exception as e:
                    logging.info(f"Ошибка выполнения задачи: {e}")
    
    def clear(self):
        self.jobs.clear()

class ScheduleJob:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.job_func = None
        self.job_args = ()
        self.time = None
        self.last_run = None
    
    @property
    def day(self):
        return self
    
    def at(self, time_str):
        self.time = time_str
        return self
    
    def do(self, job_func, *args):
        self.job_func = job_func
        self.job_args = args
        self.scheduler.jobs.append(self)
        return self
    
    def should_run(self, current_time, current_date):
        if not self.time:
            return False
        
        # Проверяем, нужно ли запускать
        if current_time == self.time:
            if not self.last_run or self.last_run != current_date:
                return True
        
        return False
    
    def run(self):
        if self.job_func:
            self.last_run = time.strftime('%Y-%m-%d', time.localtime())
            self.job_func(*self.job_args)

# Используем простой планировщик
schedule = SimpleScheduler()

class ScheduledPostsManager:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.scheduler_running = False
        from os import getenv
        # Конфигурируемый канал: POST_CHANNEL_ID (env) или BOT_CONFIG['post_channel_id']
        try:
            from config import BOT_CONFIG
        except Exception:
            BOT_CONFIG = {}
        cfg_channel = getenv('POST_CHANNEL_ID') or BOT_CONFIG.get('post_channel_id')
        self.channel_id = str(cfg_channel or '-1002566537425')  # можно задать @username или -100...
        self.start_scheduler()
    
    def start_scheduler(self):
        """Запуск планировщика постов"""
        if self.scheduler_running:
            return
        
        def scheduler_worker():
            while True:
                try:
                    schedule.run_pending()
                    time.sleep(30)  # Проверяем каждую минуту
                except Exception as e:
                    logger.error(f"Ошибка планировщика постов: {e}")
                    time.sleep(300)  # При ошибке ждем 5 минут
        
        # Загружаем расписание из базы
        self.load_schedule_from_database()
        
        scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
        scheduler_thread.start()
        self.scheduler_running = True
        logger.info("Планировщик автоматических постов запущен")
    
    def load_schedule_from_database(self):
        """Загрузка расписания из базы данных"""
        try:
            # Очищаем текущее расписание
            schedule.clear()
            
            # Загружаем активные посты
            scheduled_posts = self.db.execute_query('''
                SELECT id, title, content, time_morning, time_afternoon, time_evening, 
                       target_audience, is_active
                FROM scheduled_posts 
                WHERE is_active = 1
            ''')
            
            for post in scheduled_posts:
                post_id, title, content, morning, afternoon, evening, audience, active = post
                
                # Планируем утренний пост
                if morning:
                    schedule.every().day.at(morning).do(
                        self.send_scheduled_post, post_id, 'morning'
                    )
                
                # Планируем дневной пост
                if afternoon:
                    schedule.every().day.at(afternoon).do(
                        self.send_scheduled_post, post_id, 'afternoon'
                    )
                
                # Планируем вечерний пост
                if evening:
                    schedule.every().day.at(evening).do(
                        self.send_scheduled_post, post_id, 'evening'
                    )
            
            logger.info(f"Загружено {len(scheduled_posts)} автоматических постов")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки расписания: {e}")
    
    def send_scheduled_post(self, post_id, time_period):
        """Отправка запланированного поста"""
        try:
            logging.info(f"🔄 Отправка поста {post_id} ({time_period})...")
            
            # Получаем данные поста
            post_data = self.db.execute_query(
                'SELECT title, content, target_audience, image_url FROM scheduled_posts WHERE id = ?',
                (post_id,)
            )
            
            if not post_data:
                logging.info(f"❌ Пост {post_id} не найден")
                return
            
            title, content, target_audience, image_url = post_data[0]
            logging.info(f"📝 Пост: {title}, Аудитория: {target_audience}")
            
            # Получаем список получателей
            recipients = self.get_target_audience(target_audience)
            
            if not recipients:
                logging.info(f"⚠️ Нет получателей для поста {post_id}")
                return
            
            logging.info(f"👥 Получателей: {len(recipients)}")
            
            # Форматируем сообщение
            message_text = self.format_post_message(title, content, time_period)
            logging.info(f"📄 Сообщение готово: {len(message_text)} символов")
            
            # Создаем кнопки для товаров
            keyboard = self.create_post_keyboard()
            
            # Отправляем ТОЛЬКО ОДИН пост
            success_count = 0
            error_count = 0
            
            if target_audience == 'channel':
                # Отправляем в канал ТОЛЬКО ОДИН РАЗ
                logging.info(f"📺 Отправка в канал {self.channel_id}")
                try:
                    if image_url and len(message_text) <= 1024:
                        result = self.bot.send_photo(self.channel_id, image_url, message_text, keyboard)
                    elif image_url and len(message_text) > 1024:
                        _r1 = self.bot.send_photo(self.channel_id, image_url, '', None)
                        result = self.bot.send_message(self.channel_id, message_text, keyboard)
                    else:
                        result = self.bot.send_message(self.channel_id, message_text, keyboard)
                    
                    if result and result.get('ok'):
                        success_count = 1
                        logging.info(f"✅ Пост отправлен в канал")
                        
                        
                        
                        # НЕ отправляем товары автоматически - только по запросу
                        # self.send_product_reviews_to_channel()
                    else:
                        error_count = error_count + 1 if 'error_count' in locals() else 1
                        logging.info('❌ Не удалось отправить в канал. Проверьте, что бот админ в канале, и POST_CHANNEL_ID верный.')
                        logging.info(f"❌ Ошибка отправки в канал: {result}")
                except Exception as e:
                    error_count = 1
                    logging.info(f"❌ Ошибка отправки в канал: {e}")
            else:
                # Отправляем пользователям
                for recipient in recipients:
                    try:
                        telegram_id = recipient[0] if isinstance(recipient, (list, tuple)) else recipient.get('telegram_id')
                        if image_url and len(message_text) <= 1024:
                            result = self.bot.send_photo(telegram_id, image_url, message_text, keyboard)
                        elif image_url and len(message_text) > 1024:
                            _ = self.bot.send_photo(telegram_id, image_url, '', None)
                            result = self.bot.send_message(telegram_id, message_text, keyboard)
                        else:
                            result = self.bot.send_message(telegram_id, message_text, keyboard)
                        
                        if result and result.get('ok'):
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        error_count += 1
                        logging.info(f"❌ Ошибка отправки пользователю: {e}")
            
            # Записываем статистику
            current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            self.db.execute_query('''
                INSERT INTO post_statistics (
                    post_id, time_period, sent_count, error_count, sent_at
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                post_id, time_period, success_count, error_count, current_time
            ))
            
            logging.info(f"📊 Пост {post_id} ({time_period}): отправлен {success_count}, ошибок {error_count}")
            
        except Exception as e:
            logging.info(f"❌ Ошибка отправки запланированного поста {post_id}: {e}")
    
    def get_target_audience(self, audience_type):
        """Получение целевой аудитории"""
        if audience_type == 'channel':
            # Отправка в канал
            return [(self.channel_id, 'Канал', 'ru')]
        elif audience_type == 'all':
            return self.db.execute_query(
                'SELECT telegram_id, name, language FROM users WHERE is_admin = 0'
            )
        elif audience_type == 'active':
            return self.db.execute_query('''
                SELECT DISTINCT u.telegram_id, u.name, u.language
                FROM users u
                JOIN orders o ON u.id = o.user_id
                WHERE u.is_admin = 0 AND o.created_at >= datetime('now', '-30 days')
            ''')
        elif audience_type == 'vip':
            return self.db.execute_query('''
                SELECT DISTINCT u.telegram_id, u.name, u.language
                FROM users u
                JOIN orders o ON u.id = o.user_id
                WHERE u.is_admin = 0
                GROUP BY u.id
                HAVING SUM(o.total_amount) >= 500
            ''')
        elif audience_type == 'new':
            return self.db.execute_query('''
                SELECT telegram_id, name, language
                FROM users
                WHERE is_admin = 0 AND created_at >= datetime('now', '-7 days')
            ''')
        else:
            return []
    
    def format_post_message(self, title, content, time_period):
        """Форматирование сообщения поста"""
        time_emojis = {
            'morning': '🌅',
            'afternoon': '☀️',
            'evening': '🌆'
        }
        
        time_greetings = {
            'morning': 'Доброе утро',
            'afternoon': 'Добрый день', 
            'evening': 'Добрый вечер'
        }
        
        emoji = time_emojis.get(time_period, '📢')
        greeting = time_greetings.get(time_period, 'Привет')
        
        message = f"{emoji} <b>{greeting}!</b>\n\n"
        
        if title:
            message += f"📢 <b>{title}</b>\n\n"
        
        message += html.escape(content)
        
        # Добавляем призыв к действию
        message += f"\n\n🛍 Перейти в каталог: /start"
        
        return message
    
    def create_post_keyboard(self):
        """Создание клавиатуры для постов"""
        return {
            'inline_keyboard': [
                [
                    {'text': '🛒 Заказать товары', 'url': 'https://t.me/Safar_call_bot'},
                    {'text': '🌐 Перейти на сайт', 'url': 'https://your-website.com'}
                ],
              
            ]
        }
    
    def send_product_reviews_to_channel(self):
        """Отправка отзывов о товарах в канал (ТОЛЬКО ПО ЗАПРОСУ)"""
        try:
            # Получаем популярные товары с отзывами
            popular_products_with_reviews = self.db.execute_query('''
                SELECT 
                    p.id, p.name, p.price, p.image_url,
                    AVG(r.rating) as avg_rating,
                    COUNT(r.id) as reviews_count
                FROM products p
                JOIN reviews r ON p.id = r.product_id
                WHERE p.is_active = 1
                GROUP BY p.id, p.name, p.price, p.image_url
                HAVING reviews_count >= 3
                ORDER BY avg_rating DESC, reviews_count DESC
                LIMIT 3
            ''')
            
            if not popular_products_with_reviews:
                # Если нет отзывов, отправляем просто популярные товары
                popular_products = self.db.execute_query('''
                    SELECT id, name, price, image_url, views, sales_count
                    FROM products
                    WHERE is_active = 1
                    ORDER BY views DESC, sales_count DESC
                    LIMIT 3
                ''')
                
                for product in popular_products:
                    self.send_product_with_buttons(product, has_reviews=False)
                return
            
            # Отправляем каждый товар с отзывами
            for product in popular_products_with_reviews:
                self.send_product_with_buttons(product, has_reviews=True)
                
        except Exception as e:
            logging.info(f"Ошибка отправки отзывов в канал: {e}")
    
    def send_product_with_buttons(self, product, has_reviews=False):
        """Отправка товара с кнопками и отзывами"""
        try:
            if has_reviews:
                product_id, name, price, image_url, avg_rating, reviews_count = product
                
                # Получаем последние отзывы
                recent_reviews = self.db.execute_query('''
                    SELECT r.rating, r.comment, r.created_at, u.name
                    FROM reviews r
                    JOIN users u ON r.user_id = u.id
                    WHERE r.product_id = ? AND r.comment IS NOT NULL AND r.comment != ''
                    ORDER BY r.created_at DESC
                    LIMIT 3
                ''', (product_id,))
                
                # Форматируем сообщение о товаре
                product_message = f"🛍 <b>{name}</b>\n\n"
                product_message += f"💰 Цена: <b>${price:.2f}</b>\n"
                product_message += f"⭐ Рейтинг: {avg_rating:.1f}/5 ({reviews_count} отзывов)\n\n"
                
                # Добавляем отзывы
                if recent_reviews:
                    product_message += f"💬 <b>Отзывы покупателей:</b>\n\n"
                    for review in recent_reviews:
                        stars = '⭐' * review[0]
                        product_message += f"{stars} <b>{review[3]}</b>\n"
                        if review[1]:
                            product_message += f"💭 <i>\"{review[1][:100]}{'...' if len(review[1]) > 100 else ''}\"</i>\n"
                        product_message += f"📅 {review[2][:10]}\n\n"
            else:
                product_id, name, price, image_url, views, sales_count = product
                
                product_message = f"🛍 <b>{name}</b>\n\n"
                product_message += f"💰 Цена: <b>${price:.2f}</b>\n"
                product_message += f"👁 Просмотров: {views}\n"
                product_message += f"🛒 Продано: {sales_count} шт.\n\n"
                product_message += f"🔥 Популярный товар в нашем каталоге!"
            
            # Создаем кнопки для товара
            product_keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '🛒 Заказать товар', 'url': f'https://t.me/Safar_call_bot?start=product_{product_id}'},
                        {'text': '🌐 Перейти на сайт', 'url': f'https://your-website.com/product/{product_id}'}
                    ],
                    [
                        {'text': '⭐ Все отзывы', 'url': f'https://t.me/Safar_call_bot?start=reviews_{product_id}'},
                        {'text': '💬 Задать вопрос', 'url': 'https://t.me/your_support_username'}
                    ]
                ]
            }
            
            # Отправляем товар с кнопками
            if image_url and len(product_message) <= 1024:
                self.bot.send_photo(self.channel_id, image_url, product_message, product_keyboard)
            elif image_url and len(product_message) > 1024:
                _ = self.bot.send_photo(self.channel_id, image_url, '', None)
                self.bot.send_message(self.channel_id, product_message, product_keyboard)
            else:
                self.bot.send_message(self.channel_id, product_message, product_keyboard)
            
            # Небольшая пауза между товарами
            time.sleep(2)
            
        except Exception as e:
            logging.info(f"Ошибка отправки товара с кнопками: {e}")
    
    def create_scheduled_post(self, title, content, morning_time=None, afternoon_time=None, evening_time=None, target_audience='all'):
        """Создание нового запланированного поста"""
        current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        return self.db.execute_query('''
            INSERT INTO scheduled_posts (
                title, content, time_morning, time_afternoon, time_evening,
                target_audience, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        ''', (
            title, content, morning_time, afternoon_time, evening_time,
            target_audience, current_time
        ))
