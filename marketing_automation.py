"""
Модуль маркетинговой автоматизации
"""
import logging

from datetime import datetime, timedelta
from utils import format_price, format_date
import json
import threading
import time

class MarketingAutomationManager:
    def __init__(self, db, notification_manager):
        self.db = db
        self.notification_manager = notification_manager
        self.automation_rules = {}
        self.start_automation_engine()
    
    def start_automation_engine(self):
        # Cleanup: deactivate duplicate rules with same name+trigger, keep smallest id
        try:
            dups = self.db.execute_query('''
                SELECT MIN(id) AS keep_id, name, trigger_type
                FROM automation_rules WHERE is_active = 1
                GROUP BY name, trigger_type
                HAVING COUNT(*) > 1
            ''')
            for keep_id, name, trig in dups:
                self.db.execute_query('UPDATE automation_rules SET is_active = 0 WHERE name = ? AND trigger_type = ? AND id <> ?', (name, trig, keep_id))
        except Exception as e:
            logging.info(f"deduplicate rules warn: {e}")
        """Запуск движка автоматизации"""
        def automation_worker():
            while True:
                try:
                    self.process_automation_rules()
                    time.sleep(300)  # Проверяем каждые 5 минут
                except Exception as e:
                    logging.info(f"Ошибка автоматизации: {e}")
                    time.sleep(60)
        
        automation_thread = threading.Thread(target=automation_worker, daemon=True)
        automation_thread.start()
    
    def create_automation_rule(self, rule_name, trigger_type, conditions, actions):
        """Создание правила автоматизации"""
                # Avoid duplicates: reuse existing active rule with same name+trigger
        existing = self.db.execute_query(
            'SELECT id FROM automation_rules WHERE name = ? AND trigger_type = ? AND is_active = 1 LIMIT 1',
            (rule_name, trigger_type)
        )
        if existing:
            rule_id = existing[0][0]
        else:
            rule_id = self.db.execute_query('''
            INSERT INTO automation_rules (
                name, trigger_type, conditions, actions, is_active, created_at
            ) VALUES (?, ?, ?, ?, 1, ?)
        ''', (
            rule_name, trigger_type, 
            json.dumps(conditions), json.dumps(actions),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        self.automation_rules[rule_id] = {
            'name': rule_name,
            'trigger': trigger_type,
            'conditions': conditions,
            'actions': actions,
            'active': True
        }
        
        return rule_id
    
    def process_automation_rules(self):
        """Обработка правил автоматизации"""
        # Загружаем активные правила
        active_rules = self.db.execute_query('''
            SELECT id, name, trigger_type, conditions, actions
            FROM automation_rules
            WHERE is_active = 1
        ''')
        
        for rule in active_rules:
            rule_id, name, trigger_type, conditions_json, actions_json = rule
            
            try:
                conditions = json.loads(conditions_json)
                actions = json.loads(actions_json)
                
                # Проверяем условия срабатывания
                if self.check_trigger_conditions(trigger_type, conditions):
                    self.execute_automation_actions(rule_id, actions)
                    
            except Exception as e:
                logging.info(f"Ошибка обработки правила {name}: {e}")
    
    def check_trigger_conditions(self, trigger_type, conditions):
        """Проверка условий срабатывания"""
        if trigger_type == 'cart_abandonment':
            # Проверяем брошенные корзины
            hours_threshold = conditions.get('hours_since_last_activity', 24)
            min_cart_value = conditions.get('min_cart_value', 0)
            
            abandoned_carts = self.db.execute_query('''
                SELECT DISTINCT c.user_id
                FROM cart c
                JOIN products p ON c.product_id = p.id
                WHERE c.created_at <= datetime('now', '-{} hours')
                AND c.user_id NOT IN (
                    SELECT DISTINCT user_id FROM orders 
                    WHERE created_at >= datetime('now', '-{} hours')
                )
                GROUP BY c.user_id
                HAVING SUM(p.price * c.quantity) >= ?
            '''.format(hours_threshold, hours_threshold), (min_cart_value,))
            
            return len(abandoned_carts) > 0
        
        elif trigger_type == 'customer_milestone':
            # Проверяем достижения клиентов
            milestone_type = conditions.get('milestone_type')
            
            if milestone_type == 'first_order':
                # Клиенты, сделавшие первый заказ за последний час
                first_orders = self.db.execute_query('''
                    SELECT user_id FROM orders
                    WHERE created_at >= datetime('now', '-1 hour')
                    AND user_id NOT IN (
                        SELECT DISTINCT user_id FROM orders
                        WHERE created_at < datetime('now', '-1 hour')
                    )
                ''')
                return len(first_orders) > 0
            
            elif milestone_type == 'spending_threshold':
                threshold = conditions.get('spending_amount', 500)
                # Клиенты, достигшие порога трат
                milestone_customers = self.db.execute_query('''
                    SELECT user_id, SUM(total_amount) as total_spent
                    FROM orders
                    WHERE status != 'cancelled'
                    GROUP BY user_id
                    HAVING total_spent >= ?
                    AND user_id NOT IN (
                        SELECT user_id FROM automation_executions
                        WHERE rule_type = 'spending_milestone'
                        AND created_at >= datetime('now', '-30 days')
                    )
                ''', (threshold,))
                return len(milestone_customers) > 0
        
        elif trigger_type == 'product_restock':
            # Проверяем поступления товаров
            restocked_products = self.db.execute_query('''
                SELECT product_id FROM inventory_movements
                WHERE movement_type = 'inbound'
                AND created_at >= datetime('now', '-1 hour')
            ''')
            return len(restocked_products) > 0
        
        elif trigger_type == 'seasonal':
            # Сезонные триггеры
            season = conditions.get('season')
            current_month = datetime.now().month
            
            seasonal_months = {
                'winter': [12, 1, 2],
                'spring': [3, 4, 5],
                'summer': [6, 7, 8],
                'autumn': [9, 10, 11]
            }
            
            return current_month in seasonal_months.get(season, [])
        
        return False
    
    def execute_automation_actions(self, rule_id, actions):
        """Выполнение действий автоматизации"""
        for action in actions:
            action_type = action.get('type')
            
            if action_type == 'send_notification':
                self.execute_notification_action(rule_id, action)
            elif action_type == 'create_promo_code':
                self.execute_promo_creation_action(rule_id, action)
            elif action_type == 'update_product_price':
                self.execute_price_update_action(rule_id, action)
            elif action_type == 'send_personalized_offer':
                self.execute_personalized_offer_action(rule_id, action)
        
        # Записываем выполнение
        self.db.execute_query('''
            INSERT INTO automation_executions (rule_id, executed_at)
            VALUES (?, ?)
        ''', (rule_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    def execute_notification_action(self, rule_id, action):
        """Выполнение действия отправки уведомления"""
        target_audience = action.get('target_audience', 'all')
        message_template = action.get('message_template', '')
        notification_type = action.get('notification_type', 'promotion')
        
        # Определяем целевую аудиторию
        if target_audience == 'abandoned_cart':
            target_users = self.db.execute_query('''
                SELECT DISTINCT c.user_id
                FROM cart c
                WHERE c.created_at <= datetime('now', '-24 hours')
                AND c.user_id NOT IN (
                    SELECT DISTINCT user_id FROM orders 
                    WHERE created_at >= datetime('now', '-24 hours')
                )
                AND c.user_id NOT IN (
                    SELECT user_id FROM automation_executions WHERE rule_type = 'abandoned_cart_once'
                )
            ''')
        elif target_audience == 'first_time_buyers':
            target_users = self.db.execute_query('''
                SELECT user_id FROM orders
                WHERE created_at >= datetime('now', '-1 hour')
                AND user_id NOT IN (
                    SELECT DISTINCT user_id FROM orders
                    WHERE created_at < datetime('now', '-1 hour')
                )
            ''')
        elif target_audience == 'vip_customers':
            target_users = self.db.execute_query('''
                SELECT user_id FROM (
                    SELECT user_id, SUM(total_amount) as total_spent
                    FROM orders
                    WHERE status != 'cancelled'
                    GROUP BY user_id
                    HAVING total_spent >= 500
                )
            ''')
        else:
            target_users = self.db.execute_query(
                'SELECT id FROM users WHERE is_admin = 0'
            )
        
        # Отправляем уведомления
        for user in target_users:
            user_id = user[0]
            personalized_message = self.personalize_message(user_id, message_template)
            
            self.notification_manager.send_instant_push(
                user_id, 'Автоматическое уведомление', 
                personalized_message, notification_type
            )
            try:
                self.db.execute_query('''
                    INSERT INTO automation_executions (user_id, rule_type, executed_at)
                    VALUES (?, 'abandoned_cart_once', datetime('now'))
                ''', (user_id,))
            except Exception as _e:
                logging.info(f"warn: cannot log abandoned_cart_once for user {user_id}: {_e}")
    
    def execute_promo_creation_action(self, rule_id, action):
        """Создание промокода через автоматизацию"""
        from promotions import PromotionManager
        promo_manager = PromotionManager(self.db)
        
        promo_config = action.get('promo_config', {})
        
        # Генерируем код
        import random
        import string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        promo_manager.create_promo_code(
            code,
            promo_config.get('discount_type', 'percentage'),
            promo_config.get('discount_value', 10),
            promo_config.get('min_order_amount', 0),
            promo_config.get('max_uses', 100),
            (datetime.now() + timedelta(days=promo_config.get('valid_days', 7))).strftime('%Y-%m-%d %H:%M:%S'),
            f"Автоматически созданный промокод (правило {rule_id})"
        )
        
        # Уведомляем админов о создании
        admin_message = f"🎁 Автоматически создан промокод: <code>{code}</code>\n"
        admin_message += f"💰 Скидка: {promo_config.get('discount_value', 10)}%\n"
        admin_message += f"🎯 Правило: {rule_id}"
        
        admins = self.db.execute_query('SELECT telegram_id FROM users WHERE is_admin = 1')
        for admin in admins:
            try:
                self.notification_manager.bot.send_message(admin[0], admin_message)
            except Exception as e:
                logging.info(f"Ошибка уведомления админа о промокоде: {e}")
    
    def execute_price_update_action(self, rule_id, action):
        """Автоматическое обновление цен"""
        price_config = action.get('price_config', {})
        update_type = price_config.get('update_type', 'percentage')
        
        if update_type == 'seasonal_discount':
            # Сезонные скидки
            category_id = price_config.get('category_id')
            discount_percentage = price_config.get('discount_percentage', 10)
            
            if category_id:
                self.db.execute_query('''
                    UPDATE products 
                    SET price = price * (1 - ? / 100.0),
                        original_price = CASE WHEN original_price IS NULL THEN price ELSE original_price END
                    WHERE category_id = ? AND is_active = 1
                ''', (discount_percentage, category_id))
        
        elif update_type == 'dynamic_pricing':
            # Динамическое ценообразование на основе спроса
            high_demand_products = self.db.execute_query('''
                SELECT p.id, p.price
                FROM products p
                JOIN order_items oi ON p.id = oi.product_id
                JOIN orders o ON oi.order_id = o.id
                WHERE o.created_at >= datetime('now', '-7 days')
                AND o.status != 'cancelled'
                GROUP BY p.id, p.price
                HAVING SUM(oi.quantity) >= 10
            ''')
            
            for product in high_demand_products:
                product_id, current_price = product
                new_price = current_price * 1.05  # Увеличиваем на 5%
                
                self.db.execute_query(
                    'UPDATE products SET price = ? WHERE id = ?',
                    (new_price, product_id)
                )
    
    def execute_personalized_offer_action(self, rule_id, action):
        """Создание персональных предложений"""
        from crm import CRMManager
        crm = CRMManager(self.db)
        
        # Получаем клиентов для персональных предложений
        segments = crm.segment_customers()
        target_segment = action.get('target_segment', 'need_attention')
        
        if target_segment in segments:
            customers = segments[target_segment]
            
            for customer in customers[:10]:  # Ограничиваем 10 клиентами за раз
                user_id = customer[0]
                
                # Создаем персональное предложение
                offer = crm.create_personalized_offer(user_id)
                
                # Генерируем персональный промокод
                from promotions import PromotionManager
                promo_manager = PromotionManager(self.db)
                personal_promo = promo_manager.generate_personal_promo(user_id, 'automation')
                
                # Отправляем предложение
                offer_message = f"🎯 <b>Персональное предложение!</b>\n\n"
                offer_message += f"{offer['description']}\n\n"
                offer_message += f"🎁 Ваш промокод: <code>{personal_promo['code']}</code>\n"
                offer_message += f"💰 Скидка: {personal_promo['discount']}%\n"
                offer_message += f"⏰ Действует до: {format_date(personal_promo['expires_at'])}"
                
                self.notification_manager.send_instant_push(
                    user_id, 'Персональное предложение', offer_message, 'promotion'
                )
    
    def personalize_message(self, user_id, message_template):
        """Персонализация сообщения"""
        user = self.db.execute_query(
            'SELECT name, language FROM users WHERE id = ?',
            (user_id,)
        )[0]
        
        # Заменяем плейсхолдеры
        personalized = message_template.replace('{name}', user[0])
        
        # Добавляем персональные данные
        from crm import CRMManager
        crm = CRMManager(self.db)
        profile = crm.get_customer_profile(user_id)
        
        if profile['order_stats'][1]:  # total_spent
            personalized = personalized.replace(
                '{total_spent}', 
                format_price(profile['order_stats'][1])
            )
        
        if profile['favorite_categories']:
            cat_name = profile['favorite_categories'][0][0]
            personalized = personalized.replace('{favorite_category}', cat_name)
        
        return personalized
    
    def create_welcome_series(self, user_id):
        """Создание серии приветственных сообщений"""
        welcome_messages = [
            {
                'delay_hours': 1,
                'title': 'Добро пожаловать!',
                'message': 'Спасибо за регистрацию! Получите 10% скидку на первый заказ: WELCOME10',
                'type': 'welcome'
            },
            {
                'delay_hours': 2164,
                'title': 'Популярные товары',
                'message': 'Посмотрите наши хиты продаж! Специально для новых клиентов.',
                'type': 'engagement'
            },
            {
                'delay_hours': 216,
                'title': 'Нужна помощь?',
                'message': 'Если у вас есть вопросы, наша поддержка всегда готова помочь!',
                'type': 'support'
            }
        ]
        
        for message in welcome_messages:
            self.notification_manager.send_delayed_push(
                user_id,
                message['title'],
                message['message'],
                message['delay_hours'] * 60,  # Конвертируем в минуты
                message['type']
            )
    
    def create_win_back_campaign(self, days_inactive=60):
        """Кампания возврата неактивных клиентов"""
        inactive_customers = self.db.execute_query('''
            SELECT 
                u.id, u.name, u.telegram_id,
                MAX(o.created_at) as last_order,
                SUM(o.total_amount) as total_spent
            FROM users u
            JOIN orders o ON u.id = o.user_id
            WHERE u.is_admin = 0
            AND o.status != 'cancelled'
            GROUP BY u.id, u.name, u.telegram_id
            HAVING julianday('now') - julianday(MAX(o.created_at)) >= ?
            AND total_spent >= 50
            ORDER BY total_spent DESC
        ''', (days_inactive,))
        
        campaign_results = []
        
        for customer in inactive_customers:
            user_id, name, telegram_id, last_order, total_spent = customer
            
            # Создаем персональный промокод
            from promotions import PromotionManager
            promo_manager = PromotionManager(self.db)
            win_back_promo = promo_manager.generate_personal_promo(user_id, 'return')
            
            # Персонализированное сообщение
            win_back_message = f"💔 <b>Мы скучаем по вам, {name}!</b>\n\n"
            win_back_message += f"Вы не делали заказы уже {days_inactive}+ дней.\n"
            win_back_message += f"Как наш ценный клиент (потратили {format_price(total_spent)}), "
            win_back_message += f"вы получаете специальную скидку!\n\n"
            win_back_message += f"🎁 Ваш промокод: <code>{win_back_promo['code']}</code>\n"
            win_back_message += f"💰 Скидка: {win_back_promo['discount']}%\n"
            win_back_message += f"⏰ Действует до: {format_date(win_back_promo['expires_at'])}\n\n"
            win_back_message += f"🛍 Вернитесь и воспользуйтесь скидкой!"
            
            # Отправляем через NotificationManager
            self.notification_manager.send_instant_push(
                user_id, 'Мы скучаем по вам!', win_back_message, 'promotion'
            )
            
            campaign_results.append({
                'user_id': user_id,
                'promo_code': win_back_promo['code'],
                'discount': win_back_promo['discount']
            })
        
        return campaign_results
    
    def create_upsell_campaign(self, target_segment='loyal'):
        """Кампания допродаж"""
        from crm import CRMManager
        crm = CRMManager(self.db)
        
        segments = crm.segment_customers()
        target_customers = segments.get(target_segment, [])
        
        upsell_results = []
        
        for customer in target_customers:
            user_id = customer[0]
            
            # Анализируем историю покупок
            purchase_history = self.db.execute_query('''
                SELECT p.category_id, AVG(p.price) as avg_price
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                WHERE o.user_id = ? AND o.status != 'cancelled'
                GROUP BY p.category_id
                ORDER BY COUNT(*) DESC
                LIMIT 1
            ''', (user_id,))
            
            if purchase_history:
                category_id, avg_price = purchase_history[0]
                
                # Находим товары дороже обычных покупок
                upsell_products = self.db.execute_query('''
                    SELECT id, name, price
                    FROM products
                    WHERE category_id = ? 
                    AND price > ? * 1.5
                    AND is_active = 1
                    ORDER BY views DESC, sales_count DESC
                    LIMIT 3
                ''', (category_id, avg_price))
                
                if upsell_products:
                    user_data = self.db.execute_query(
                        'SELECT name FROM users WHERE id = ?',
                        (user_id,)
                    )[0]
                    
                    upsell_message = f"⬆️ <b>Специально для вас, {user_data[0]}!</b>\n\n"
                    upsell_message += f"Попробуйте товары премиум-класса:\n\n"
                    
                    for product in upsell_products:
                        upsell_message += f"💎 <b>{product[1]}</b> - {format_price(product[2])}\n"
                    
                    upsell_message += f"\n🎁 Скидка 15% на премиум товары: PREMIUM15"
                    
                    self.notification_manager.send_instant_push(
                        user_id, 'Премиум предложение', upsell_message, 'promotion'
                    )
                    
                    upsell_results.append({
                        'user_id': user_id,
                        'products_count': len(upsell_products)
                    })
        
        return upsell_results
    
    def create_cross_sell_campaign(self):
        """Кампания кросс-продаж"""
        # Находим клиентов с недавними заказами
        recent_buyers = self.db.execute_query('''
            SELECT DISTINCT o.user_id, u.name
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.created_at >= datetime('now', '-7 days')
            AND o.status IN ('confirmed', 'shipped')
        ''')
        
        cross_sell_results = []
        
        for buyer in recent_buyers:
            user_id, name = buyer
            
            # Получаем рекомендации для кросс-продаж
            from crm import CRMManager
            crm = CRMManager(self.db)
            cross_sell_products = crm.get_cross_sell_opportunities(user_id)
            
            if cross_sell_products:
                cross_sell_message = f"🛍 <b>Дополните свою покупку, {name}!</b>\n\n"
                cross_sell_message += f"Товары, которые отлично дополнят ваш заказ:\n\n"
                
                for product in cross_sell_products[:3]:
                    cross_sell_message += f"• <b>{product[1]}</b> - {format_price(product[3])}\n"
                
                cross_sell_message += f"\n🎯 Скидка 10% на дополнительные товары: ADDON10"
                
                self.notification_manager.send_instant_push(
                    user_id, 'Дополните покупку', cross_sell_message, 'promotion'
                )
                
                cross_sell_results.append({
                    'user_id': user_id,
                    'recommendations_count': len(cross_sell_products)
                })
        
        return cross_sell_results
    
    def schedule_seasonal_campaigns(self):
        """Планирование сезонных кампаний"""
        current_month = datetime.now().month
        
        seasonal_campaigns = {
            1: {'name': 'Новогодние скидки', 'discount': 20, 'categories': [1, 2]},
            3: {'name': 'Весенняя распродажа', 'discount': 15, 'categories': [2, 5]},
            6: {'name': 'Летние предложения', 'discount': 12, 'categories': [2, 4]},
            9: {'name': 'Осенняя коллекция', 'discount': 18, 'categories': [2, 3]},
            11: {'name': 'Черная пятница', 'discount': 30, 'categories': [1, 2, 3, 4, 5, 6]},
            12: {'name': 'Предновогодняя распродажа', 'discount': 25, 'categories': [1, 2, 3]}
        }
        
        if current_month in seasonal_campaigns:
            campaign = seasonal_campaigns[current_month]
            
            # Создаем флеш-распродажу
            from promotions import PromotionManager
            promo_manager = PromotionManager(self.db)
            
            # Получаем товары из целевых категорий
            category_products = []
            for cat_id in campaign['categories']:
                products = self.db.execute_query(
                    'SELECT id FROM products WHERE category_id = ? AND is_active = 1',
                    (cat_id,)
                )
                category_products.extend([p[0] for p in products])
            
            if category_products:
                flash_sale = promo_manager.create_flash_sale(
                    category_products,
                    campaign['discount'],
                    72  # 3 дня
                )
                
                # Уведомляем всех пользователей
                campaign_message = f"🔥 <b>{campaign['name']}!</b>\n\n"
                campaign_message += f"💰 Скидка {campaign['discount']}% на популярные категории!\n"
                campaign_message += f"🏷 Промокод: <code>{flash_sale['code']}</code>\n"
                campaign_message += f"⏰ Только 3 дня!\n\n"
                campaign_message += f"🛍 Не упустите возможность!"
                
                success_count, error_count = self.notification_manager.send_promotional_broadcast(
                    campaign_message, 'all'
                )
                
                return {
                    'campaign_name': campaign['name'],
                    'promo_code': flash_sale['code'],
                    'products_count': len(category_products),
                    'notifications_sent': success_count
                }
        
        return None
    
    def create_abandoned_cart_sequence(self):
        """Последовательность для брошенных корзин"""
        # 3-этапная последовательность
        sequences = [
            {
                'delay_hours': 216,
                'title': 'Не забудьте о корзине!',
                'message': 'У вас есть товары в корзине. Завершите покупку!',
                'discount': 0
            },
            {
                'delay_hours': 2164,
                'title': 'Специальная скидка!',
                'message': 'Получите 10% скидку на товары в корзине: CART10',
                'discount': 10
            },
            {
                'delay_hours': 216,
                'title': 'Последний шанс!',
                'message': 'Товары могут закончиться! Скидка 15%: LASTCHANCE15',
                'discount': 15
            }
        ]
        
        # Находим брошенные корзины
        abandoned_carts = self.db.execute_query('''
            SELECT 
                c.user_id,
                MAX(c.created_at) as last_activity,
                SUM(p.price * c.quantity) as cart_value
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id NOT IN (
                SELECT DISTINCT user_id FROM orders 
                WHERE created_at >= datetime('now', '-1 hour')
            )
            GROUP BY c.user_id
            HAVING julianday('now') - julianday(MAX(c.created_at)) >= 0.1  # 2.4 часа
        ''')
        
        for cart in abandoned_carts:
            user_id, last_activity, cart_value = cart
            hours_since = (datetime.now() - datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600
            
            # Определяем какое сообщение отправить
            for sequence in sequences:
                if hours_since >= sequence['delay_hours']:
                    # Проверяем, не отправляли ли уже это сообщение
                    already_sent = self.db.execute_query('''
                        SELECT COUNT(*) FROM automation_executions
                        WHERE user_id = ? AND rule_type = ?
                        AND created_at >= datetime('now', '-{} hours')
                    '''.format(sequence['delay_hours'] + 12), (user_id, f"cart_abandonment_{sequence['delay_hours']}"))
                    
                    if already_sent[0][0] == 0:
                        # Персонализируем сообщение
                        user_data = self.db.execute_query(
                            'SELECT name FROM users WHERE id = ?',
                            (user_id,)
                        )[0]
                        
                        personalized_message = f"{user_data[0]}, {sequence['message']}\n\n"
                        personalized_message += f"💰 Сумма корзины: {format_price(cart_value)}"
                        
                        self.notification_manager.send_instant_push(
                            user_id, sequence['title'], personalized_message, 'reminder'
                        )
                        
                        # Записываем выполнение
                        self.db.execute_query('''
                            INSERT INTO automation_executions (
                                user_id, rule_type, executed_at
                            ) VALUES (?, ?, ?)
                        ''', (
                            user_id, f"cart_abandonment_{sequence['delay_hours']}",
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ))
                        
                        break
    
    def create_loyalty_upgrade_automation(self):
        """Автоматизация повышения уровня лояльности"""
        # Проверяем пользователей, готовых к повышению
        upgrade_candidates = self.db.execute_query('''
            SELECT 
                u.id, u.name, u.telegram_id,
                lp.current_points, lp.current_tier,
                SUM(o.total_amount) as total_spent
            FROM users u
            JOIN loyalty_points lp ON u.id = lp.user_id
            LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
            WHERE u.is_admin = 0
            GROUP BY u.id, u.name, u.telegram_id, lp.current_points, lp.current_tier
        ''')
        
        tier_thresholds = {
            'Bronze': 0,
            'Silver': 100,
            'Gold': 500,
            'Platinum': 1500,
            'Diamond': 5000
        }
        
        tier_order = ['Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond']
        
        for candidate in upgrade_candidates:
            user_id, name, telegram_id, points, current_tier, total_spent = candidate
            
            # Определяем новый уровень
            new_tier = current_tier
            for tier in tier_order:
                if points >= tier_thresholds[tier]:
                    new_tier = tier
            
            # Если уровень изменился
            if new_tier != current_tier:
                # Обновляем в базе
                self.db.execute_query(
                    'UPDATE loyalty_points SET current_tier = ? WHERE user_id = ?',
                    (new_tier, user_id)
                )
                
                # Создаем уведомление
                from crm import CRMManager
                crm = CRMManager(self.db)
                upgrade_notification = crm.create_loyalty_tier_upgrade_notification(user_id, new_tier)
                
                # Отправляем уведомление
                self.notification_manager.send_instant_push(
                    user_id, 'Повышение уровня!', 
                    upgrade_notification['message'], 'success'
                )
    
    def analyze_campaign_effectiveness(self, campaign_id):
        """Анализ эффективности кампании"""
        campaign_data = self.db.execute_query('''
            SELECT 
                name, created_at, target_count,
                (SELECT COUNT(*) FROM automation_executions WHERE rule_id = ?) as executions
            FROM marketing_campaigns
            WHERE id = ?
        ''', (campaign_id, campaign_id))
        
        if not campaign_data:
            return None
        
        campaign = campaign_data[0]
        
        # Анализируем результаты
        campaign_results = self.db.execute_query('''
            SELECT 
                COUNT(DISTINCT o.user_id) as converted_users,
                SUM(o.total_amount) as generated_revenue,
                AVG(o.total_amount) as avg_order_value
            FROM orders o
            JOIN automation_executions ae ON o.user_id = ae.user_id
            WHERE ae.rule_id = ?
            AND o.created_at >= ae.executed_at
            AND o.created_at <= datetime(ae.executed_at, '+7 days')
            AND o.status != 'cancelled'
        ''', (campaign_id,))
        
        results = campaign_results[0] if campaign_results else (0, 0, 0)
        
        conversion_rate = (results[0] / campaign[2] * 100) if campaign[2] > 0 else 0
        
        return {
            'campaign_name': campaign[0],
            'target_count': campaign[2],
            'executions': campaign[3],
            'converted_users': results[0],
            'generated_revenue': results[1] or 0,
            'avg_order_value': results[2] or 0,
            'conversion_rate': conversion_rate,
            'roi': ((results[1] or 0) / 100) if results[1] else 0  # Примерная стоимость кампании $100
        }
    
    def get_automation_statistics(self):
        """Статистика автоматизации"""
        # Статистика выполнений за последние 30 дней
        executions_stats = self.db.execute_query('''
            SELECT 
                rule_type,
                COUNT(*) as executions_count,
                DATE(executed_at) as date
            FROM automation_executions
            WHERE executed_at >= datetime('now', '-30 days')
            GROUP BY rule_type, DATE(executed_at)
            ORDER BY date DESC, executions_count DESC
        ''')
        
        # Эффективность правил
        rules_effectiveness = self.db.execute_query('''
            SELECT 
                ar.name,
                COUNT(ae.id) as total_executions,
                COUNT(DISTINCT ae.user_id) as unique_users_reached
            FROM automation_rules ar
            LEFT JOIN automation_executions ae ON ar.id = ae.rule_id
            WHERE ar.is_active = 1
            GROUP BY ar.id, ar.name
            ORDER BY total_executions DESC
        ''')
        
        return {
            'executions_stats': executions_stats,
            'rules_effectiveness': rules_effectiveness
        }