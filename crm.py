"""
CRM модуль для управления клиентами
"""

from datetime import datetime
from utils import format_price, format_date

class CRMManager:
    def __init__(self, db):
        self.db = db
    
    def segment_customers(self):
        """Сегментация клиентов по RFM анализу"""
        customers = self.db.execute_query('''
            SELECT 
                u.id,
                u.name,
                u.telegram_id,
                u.created_at,
                COUNT(o.id) as total_orders,
                SUM(o.total_amount) as total_spent,
                AVG(o.total_amount) as avg_order_value,
                MAX(o.created_at) as last_order_date,
                julianday('now') - julianday(MAX(o.created_at)) as days_since_last_order
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
            WHERE u.is_admin = 0
            GROUP BY u.id, u.name, u.telegram_id, u.created_at
        ''')
        
        segments = {
            'champions': [],      # Лучшие клиенты
            'loyal': [],          # Лояльные клиенты
            'potential': [],      # Потенциально лояльные
            'new': [],           # Новые клиенты
            'promising': [],     # Перспективные
            'need_attention': [], # Требуют внимания
            'at_risk': [],       # В зоне риска
            'hibernating': [],   # Спящие
            'lost': []           # Потерянные
        }
        
        for customer in customers:
            user_id, name, telegram_id, reg_date, orders, spent, avg_order, last_order, days_since = customer
            
            # RFM скоринг
            if orders == 0:
                segments['new'].append(customer)
                continue
            
            # Recency (дни с последнего заказа)
            if days_since is None:
                recency_score = 5
            elif days_since <= 30:
                recency_score = 5
            elif days_since <= 60:
                recency_score = 4
            elif days_since <= 90:
                recency_score = 3
            elif days_since <= 180:
                recency_score = 2
            else:
                recency_score = 1
            
            # Frequency (количество заказов)
            if orders >= 10:
                frequency_score = 5
            elif orders >= 5:
                frequency_score = 4
            elif orders >= 3:
                frequency_score = 3
            elif orders >= 2:
                frequency_score = 2
            else:
                frequency_score = 1
            
            # Monetary (общая сумма покупок)
            if spent >= 1000:
                monetary_score = 5
            elif spent >= 500:
                monetary_score = 4
            elif spent >= 200:
                monetary_score = 3
            elif spent >= 50:
                monetary_score = 2
            else:
                monetary_score = 1
            
            # Определяем сегмент
            avg_score = (recency_score + frequency_score + monetary_score) / 3
            
            if avg_score >= 4.5:
                segments['champions'].append(customer)
            elif avg_score >= 4:
                segments['loyal'].append(customer)
            elif avg_score >= 3.5:
                segments['potential'].append(customer)
            elif avg_score >= 3:
                if orders == 1:
                    segments['new'].append(customer)
                else:
                    segments['promising'].append(customer)
            elif avg_score >= 2.5:
                segments['need_attention'].append(customer)
            elif avg_score >= 2:
                segments['at_risk'].append(customer)
            elif days_since and days_since > 180:
                segments['hibernating'].append(customer)
            else:
                segments['lost'].append(customer)
        
        return segments
    
    def get_customer_profile(self, user_id):
        """Получение полного профиля клиента"""
        # Основная информация
        user_info = self.db.execute_query(
            'SELECT * FROM users WHERE id = ?',
            (user_id,)
        )[0]
        
        # Статистика заказов
        order_stats = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_spent,
                AVG(total_amount) as avg_order_value,
                MIN(created_at) as first_order,
                MAX(created_at) as last_order
            FROM orders 
            WHERE user_id = ? AND status != 'cancelled'
        ''', (user_id,))[0]
        
        # Любимые категории
        favorite_categories = self.db.execute_query('''
            SELECT 
                c.name,
                c.emoji,
                COUNT(*) as orders_count,
                SUM(oi.quantity * oi.price) as spent_amount
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.user_id = ? AND o.status != 'cancelled'
            GROUP BY c.id, c.name, c.emoji
            ORDER BY spent_amount DESC
            LIMIT 3
        ''', (user_id,))
        
        # Любимые товары
        favorite_products = self.db.execute_query('''
            SELECT 
                p.name,
                SUM(oi.quantity) as total_bought,
                SUM(oi.quantity * oi.price) as total_spent
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.user_id = ? AND o.status != 'cancelled'
            GROUP BY p.id, p.name
            ORDER BY total_bought DESC
            LIMIT 5
        ''', (user_id,))
        
        # Баллы лояльности
        loyalty_data = self.db.get_user_loyalty_points(user_id)
        
        return {
            'user_info': user_info,
            'order_stats': order_stats,
            'favorite_categories': favorite_categories,
            'favorite_products': favorite_products,
            'loyalty_data': loyalty_data
        }
    
    def create_personalized_offer(self, user_id):
        """Создание персонального предложения"""
        profile = self.get_customer_profile(user_id)
        
        # Анализируем профиль клиента
        total_spent = profile['order_stats'][1] or 0
        total_orders = profile['order_stats'][0]
        favorite_categories = profile['favorite_categories']
        
        # Определяем тип предложения
        if total_orders == 0:
            # Новый клиент - скидка на первый заказ
            offer = {
                'type': 'first_order_discount',
                'title': 'Скидка 10% на первый заказ!',
                'description': 'Добро пожаловать! Получите скидку 10% на первую покупку',
                'discount_percentage': 10,
                'min_amount': 20
            }
        elif total_spent >= 500:
            # VIP клиент - эксклюзивная скидка
            offer = {
                'type': 'vip_discount',
                'title': 'Эксклюзивная скидка 20% для VIP!',
                'description': 'Спасибо за лояльность! Специальная скидка только для вас',
                'discount_percentage': 20,
                'min_amount': 100
            }
        elif favorite_categories:
            # Предложение по любимой категории
            top_category = favorite_categories[0]
            offer = {
                'type': 'category_discount',
                'title': f'Скидка 15% на {top_category[0]}!',
                'description': f'Специальное предложение на товары категории {top_category[1]} {top_category[0]}',
                'discount_percentage': 15,
                'category_id': top_category[0],
                'min_amount': 50
            }
        else:
            # Общее предложение
            offer = {
                'type': 'general_discount',
                'title': 'Скидка 12% на все товары!',
                'description': 'Ограниченное предложение - скидка на весь каталог',
                'discount_percentage': 12,
                'min_amount': 30
            }
        
        return offer
    
    def track_customer_journey(self, user_id):
        """Отслеживание пути клиента"""
        # Основные события
        events = []
        
        # Регистрация
        user = self.db.execute_query('SELECT created_at FROM users WHERE id = ?', (user_id,))[0]
        events.append({
            'type': 'registration',
            'date': user[0],
            'description': 'Регистрация в боте'
        })
        
        # Первый просмотр товара
        first_view = self.db.execute_query('''
            SELECT MIN(created_at) FROM cart WHERE user_id = ?
        ''', (user_id,))[0]
        
        if first_view[0]:
            events.append({
                'type': 'first_product_view',
                'date': first_view[0],
                'description': 'Первый просмотр товара'
            })
        
        # Первое добавление в корзину
        first_cart = self.db.execute_query('''
            SELECT MIN(created_at) FROM cart WHERE user_id = ?
        ''', (user_id,))[0]
        
        if first_cart[0]:
            events.append({
                'type': 'first_add_to_cart',
                'date': first_cart[0],
                'description': 'Первое добавление в корзину'
            })
        
        # Заказы
        orders = self.db.execute_query('''
            SELECT created_at, total_amount, status FROM orders 
            WHERE user_id = ? 
            ORDER BY created_at
        ''', (user_id,))
        
        for order in orders:
            events.append({
                'type': 'order',
                'date': order[0],
                'description': f'Заказ на {format_price(order[1])} - {order[2]}'
            })
        
        # Сортируем по дате
        events.sort(key=lambda x: x['date'])
        
        return events
    
    def get_churn_risk_customers(self):
        """Получение клиентов с риском оттока"""
        at_risk_customers = self.db.execute_query('''
            SELECT 
                u.id,
                u.name,
                u.telegram_id,
                MAX(o.created_at) as last_order,
                julianday('now') - julianday(MAX(o.created_at)) as days_since_last_order,
                COUNT(o.id) as total_orders,
                SUM(o.total_amount) as total_spent
            FROM users u
            JOIN orders o ON u.id = o.user_id
            WHERE u.is_admin = 0 AND o.status != 'cancelled'
            GROUP BY u.id, u.name, u.telegram_id
            HAVING days_since_last_order > 60 AND total_orders >= 2
            ORDER BY total_spent DESC
        ''')
        
        return at_risk_customers
    
    def create_win_back_campaign(self, customer_ids):
        """Создание кампании возврата клиентов"""
        campaign_results = []
        
        for customer_id in customer_ids:
            # Создаем персональный промокод
            from promotions import PromotionManager
            promo_manager = PromotionManager(self.db)
            
            personal_promo = promo_manager.generate_personal_promo(customer_id, 'return')
            
            # Получаем данные клиента
            customer = self.db.execute_query(
                'SELECT telegram_id, name, language FROM users WHERE id = ?',
                (customer_id,)
            )[0]
            
            # Создаем персональное сообщение
            from localization import t
            language = customer[2]
            
            message = f"💔 <b>{t('miss_you_title', language=language)}</b>\n\n"
            message += f"👋 {customer[1]}, {t('miss_you_message', language=language)}\n\n"
            message += f"🎁 <b>{t('special_offer', language=language)}:</b>\n"
            message += f"💰 {personal_promo['discount']}% {t('discount', language=language)}\n"
            message += f"🏷 {t('promo_code', language=language)}: <code>{personal_promo['code']}</code>\n"
            message += f"⏰ {t('valid_until', language=language)}: {format_date(personal_promo['expires_at'])}\n\n"
            message += f"🛍 {t('come_back_cta', language=language)}"
            
            campaign_results.append({
                'customer_id': customer_id,
                'telegram_id': customer[0],
                'promo_code': personal_promo['code'],
                'message': message
            })
        
        return campaign_results
    
    def analyze_customer_behavior(self, user_id):
        """Анализ поведения конкретного клиента"""
        # Паттерны покупок
        purchase_patterns = self.db.execute_query('''
            SELECT 
                strftime('%w', created_at) as day_of_week,
                strftime('%H', created_at) as hour_of_day,
                COUNT(*) as orders_count
            FROM orders
            WHERE user_id = ? AND status != 'cancelled'
            GROUP BY day_of_week, hour_of_day
            ORDER BY orders_count DESC
        ''', (user_id,))
        
        # Сезонность покупок
        seasonal_patterns = self.db.execute_query('''
            SELECT 
                strftime('%m', created_at) as month,
                COUNT(*) as orders_count,
                SUM(total_amount) as total_spent
            FROM orders
            WHERE user_id = ? AND status != 'cancelled'
            GROUP BY month
            ORDER BY month
        ''', (user_id,))
        
        # Средний интервал между покупками
        purchase_intervals = self.db.execute_query('''
            SELECT 
                julianday(created_at) - julianday(LAG(created_at) OVER (ORDER BY created_at)) as days_between
            FROM orders
            WHERE user_id = ? AND status != 'cancelled'
            ORDER BY created_at
        ''', (user_id,))
        
        avg_interval = None
        if purchase_intervals:
            intervals = [interval[0] for interval in purchase_intervals if interval[0] is not None]
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
        
        # Предпочтения по ценовым сегментам
        price_preferences = self.db.execute_query('''
            SELECT 
                CASE 
                    WHEN oi.price < 25 THEN 'Бюджетные'
                    WHEN oi.price < 100 THEN 'Средние'
                    WHEN oi.price < 500 THEN 'Премиум'
                    ELSE 'Люкс'
                END as price_segment,
                COUNT(*) as items_bought,
                SUM(oi.quantity * oi.price) as total_spent
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.user_id = ? AND o.status != 'cancelled'
            GROUP BY price_segment
            ORDER BY total_spent DESC
        ''', (user_id,))
        
        return {
            'purchase_patterns': purchase_patterns,
            'seasonal_patterns': seasonal_patterns,
            'avg_purchase_interval': avg_interval,
            'price_preferences': price_preferences
        }
    
    def get_customer_recommendations(self, user_id):
        """Получение рекомендаций для клиента"""
        # Анализируем историю покупок
        purchase_history = self.db.execute_query('''
            SELECT DISTINCT p.category_id
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.user_id = ? AND o.status != 'cancelled'
        ''', (user_id,))
        
        if not purchase_history:
            # Для новых клиентов - популярные товары
            recommendations = self.db.execute_query('''
                SELECT p.*, c.name as category_name
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.is_active = 1
                ORDER BY p.views DESC, p.sales_count DESC
                LIMIT 5
            ''')
        else:
            # Рекомендации на основе категорий покупок
            category_ids = [cat[0] for cat in purchase_history]
            placeholders = ','.join('?' * len(category_ids))
            
            recommendations = self.db.execute_query(f'''
                SELECT p.*, c.name as category_name
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.is_active = 1 
                AND p.category_id IN ({placeholders})
                AND p.id NOT IN (
                    SELECT DISTINCT oi.product_id
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE o.user_id = ?
                )
                ORDER BY p.views DESC, p.sales_count DESC
                LIMIT 5
            ''', (*category_ids, user_id))
        
        return recommendations
    
    def create_customer_communication_plan(self, segment):
        """Создание плана коммуникации для сегмента"""
        plans = {
            'champions': {
                'frequency': 'weekly',
                'content_type': 'exclusive_offers',
                'discount_range': (15, 25),
                'message_tone': 'premium'
            },
            'loyal': {
                'frequency': 'bi_weekly',
                'content_type': 'loyalty_rewards',
                'discount_range': (10, 20),
                'message_tone': 'appreciative'
            },
            'potential': {
                'frequency': 'weekly',
                'content_type': 'engagement_boost',
                'discount_range': (12, 18),
                'message_tone': 'encouraging'
            },
            'new': {
                'frequency': 'every_3_days',
                'content_type': 'onboarding',
                'discount_range': (10, 15),
                'message_tone': 'welcoming'
            },
            'need_attention': {
                'frequency': 'weekly',
                'content_type': 'reactivation',
                'discount_range': (15, 25),
                'message_tone': 'urgent'
            },
            'at_risk': {
                'frequency': 'immediate',
                'content_type': 'win_back',
                'discount_range': (20, 30),
                'message_tone': 'apologetic'
            }
        }
        
        return plans.get(segment, plans['new'])
    
    def get_customer_lifetime_value_prediction(self, user_id):
        """Прогноз жизненной ценности клиента"""
        # Получаем историю покупок
        orders = self.db.execute_query('''
            SELECT total_amount, created_at
            FROM orders
            WHERE user_id = ? AND status != 'cancelled'
            ORDER BY created_at
        ''', (user_id,))
        
        if len(orders) < 2:
            return None
        
        # Вычисляем средний интервал между покупками
        intervals = []
        for i in range(1, len(orders)):
            prev_date = datetime.strptime(orders[i-1][1], '%Y-%m-%d %H:%M:%S')
            curr_date = datetime.strptime(orders[i][1], '%Y-%m-%d %H:%M:%S')
            interval = (curr_date - prev_date).days
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals)
        avg_order_value = sum(order[0] for order in orders) / len(orders)
        
        # Простой прогноз на год
        orders_per_year = 365 / avg_interval if avg_interval > 0 else 0
        predicted_clv = orders_per_year * avg_order_value
        
        return {
            'avg_interval_days': avg_interval,
            'avg_order_value': avg_order_value,
            'predicted_orders_per_year': orders_per_year,
            'predicted_clv': predicted_clv,
            'confidence': 'High' if len(orders) >= 5 else 'Medium' if len(orders) >= 3 else 'Low'
        }
    
    def create_targeted_campaign(self, segment, campaign_type):
        """Создание таргетированной кампании"""
        segments = self.segment_customers()
        target_customers = segments.get(segment, [])
        
        if not target_customers:
            return {'success': False, 'message': 'Нет клиентов в выбранном сегменте'}
        
        campaign_messages = {
            'reactivation': {
                'title': 'Мы скучаем по вам!',
                'template': 'Вернитесь и получите скидку {discount}% на следующий заказ!'
            },
            'upsell': {
                'title': 'Специальное предложение!',
                'template': 'Попробуйте товары премиум-класса со скидкой {discount}%!'
            },
            'cross_sell': {
                'title': 'Дополните свою покупку!',
                'template': 'Товары, которые отлично дополнят ваши предыдущие покупки'
            },
            'loyalty_boost': {
                'title': 'Бонусы за лояльность!',
                'template': 'Получите {discount}% скидку как наш постоянный клиент!'
            }
        }
        
        message_data = campaign_messages.get(campaign_type, campaign_messages['reactivation'])
        
        # Создаем кампанию
        campaign_id = self.db.execute_query('''
            INSERT INTO marketing_campaigns (
                name, segment, campaign_type, target_count, created_at
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            f"{campaign_type.title()} для {segment}",
            segment,
            campaign_type,
            len(target_customers),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        return {
            'success': True,
            'campaign_id': campaign_id,
            'target_count': len(target_customers),
            'customers': target_customers[:10]  # Первые 10 для предпросмотра
        }
    
    def get_customer_interaction_history(self, user_id):
        """История взаимодействий с клиентом"""
        # Заказы
        orders = self.db.execute_query('''
            SELECT 'order' as type, created_at, 
                   'Заказ #' || id || ' на ' || total_amount || '$' as description
            FROM orders
            WHERE user_id = ?
        ''', (user_id,))
        
        # Уведомления
        notifications = self.db.execute_query('''
            SELECT 'notification' as type, created_at, 
                   title || ': ' || message as description
            FROM notifications
            WHERE user_id = ?
        ''', (user_id,))
        
        # Отзывы
        reviews = self.db.execute_query('''
            SELECT 'review' as type, r.created_at,
                   'Отзыв на ' || p.name || ' (' || r.rating || '/5)' as description
            FROM reviews r
            JOIN products p ON r.product_id = p.id
            WHERE r.user_id = ?
        ''', (user_id,))
        
        # Объединяем и сортируем
        all_interactions = list(orders) + list(notifications) + list(reviews)
        all_interactions.sort(key=lambda x: x[1], reverse=True)
        
        return all_interactions[:20]  # Последние 20 взаимодействий
    
    def calculate_customer_satisfaction_score(self, user_id):
        """Расчет индекса удовлетворенности клиента"""
        # Средняя оценка в отзывах
        avg_rating = self.db.execute_query(
            'SELECT AVG(rating) FROM reviews WHERE user_id = ?',
            (user_id,)
        )[0][0]
        
        # Процент завершенных заказов
        order_completion = self.db.execute_query('''
            SELECT 
                COUNT(CASE WHEN status = 'delivered' THEN 1 END) * 100.0 / COUNT(*) as completion_rate
            FROM orders
            WHERE user_id = ? AND status != 'cancelled'
        ''', (user_id,))[0][0]
        
        # Частота повторных покупок
        repeat_purchase_rate = self.db.execute_query('''
            SELECT COUNT(*) FROM orders WHERE user_id = ? AND status != 'cancelled'
        ''', (user_id,))[0][0]
        
        # Рассчитываем общий индекс (0-100)
        satisfaction_score = 0
        
        if avg_rating:
            satisfaction_score += (avg_rating / 5) * 40  # 40% веса
        
        if order_completion:
            satisfaction_score += (order_completion / 100) * 30  # 30% веса
        
        if repeat_purchase_rate:
            repeat_score = min(repeat_purchase_rate / 5, 1) * 30  # 30% веса
            satisfaction_score += repeat_score
        
        return {
            'overall_score': round(satisfaction_score, 1),
            'avg_rating': avg_rating or 0,
            'order_completion_rate': order_completion or 0,
            'repeat_purchases': repeat_purchase_rate,
            'satisfaction_level': self.get_satisfaction_level(satisfaction_score)
        }
    
    def get_satisfaction_level(self, score):
        """Определение уровня удовлетворенности"""
        if score >= 80:
            return 'Очень доволен'
        elif score >= 60:
            return 'Доволен'
        elif score >= 40:
            return 'Нейтрален'
        elif score >= 20:
            return 'Недоволен'
        else:
            return 'Очень недоволен'
    
    def get_cross_sell_opportunities(self, user_id):
        """Поиск возможностей для кросс-продаж"""
        # Анализируем что покупал клиент
        purchased_categories = self.db.execute_query('''
            SELECT DISTINCT p.category_id, c.name
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.user_id = ? AND o.status != 'cancelled'
        ''', (user_id,))
        
        # Находим дополняющие категории
        cross_sell_rules = {
            1: [3, 5],  # Электроника → Дом и сад, Красота
            2: [5, 4],  # Одежда → Красота, Спорт
            3: [1, 6],  # Дом и сад → Электроника, Книги
            4: [2, 5],  # Спорт → Одежда, Красота
            5: [2, 3],  # Красота → Одежда, Дом и сад
            6: [1, 3]   # Книги → Электроника, Дом и сад
        }
        
        recommended_categories = set()
        for purchased_cat in purchased_categories:
            cat_id = purchased_cat[0]
            if cat_id in cross_sell_rules:
                recommended_categories.update(cross_sell_rules[cat_id])
        
        # Исключаем уже купленные категории
        purchased_cat_ids = {cat[0] for cat in purchased_categories}
        recommended_categories -= purchased_cat_ids
        
        # Получаем товары из рекомендуемых категорий
        if recommended_categories:
            placeholders = ','.join('?' * len(recommended_categories))
            cross_sell_products = self.db.execute_query(f'''
                SELECT p.*, c.name as category_name
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.category_id IN ({placeholders})
                AND p.is_active = 1
                ORDER BY p.sales_count DESC, p.views DESC
                LIMIT 5
            ''', list(recommended_categories))
            
            return cross_sell_products
        
        return []
    
    def create_loyalty_tier_upgrade_notification(self, user_id, new_tier):
        """Создание уведомления о повышении уровня лояльности"""
        user = self.db.execute_query(
            'SELECT telegram_id, name, language FROM users WHERE id = ?',
            (user_id,)
        )[0]
        
        tier_benefits = {
            'Silver': ['5% скидка на все товары', 'Приоритетная поддержка'],
            'Gold': ['10% скидка на все товары', 'Бесплатная доставка', 'Ранний доступ к акциям'],
            'Platinum': ['15% скидка на все товары', 'Персональный менеджер', 'Эксклюзивные товары'],
            'Diamond': ['20% скидка на все товары', 'VIP поддержка 24/7', 'Подарки на день рождения']
        }
        
        from localization import t
        language = user[2]
        
        notification_text = f"🎉 <b>{t('tier_upgrade_title', language=language)}</b>\n\n"
        notification_text += f"👑 {user[1]}, {t('congratulations', language=language)}!\n"
        notification_text += f"🆙 {t('new_tier', language=language)}: <b>{new_tier}</b>\n\n"
        notification_text += f"🎁 <b>{t('your_benefits', language=language)}:</b>\n"
        
        benefits = tier_benefits.get(new_tier, [])
        for benefit in benefits:
            notification_text += f"✅ {benefit}\n"
        
        notification_text += f"\n🛍 {t('enjoy_benefits', language=language)}"
        
        return {
            'telegram_id': user[0],
            'message': notification_text,
            'tier': new_tier
        }
    
    def analyze_cart_abandonment_patterns(self):
        """Анализ паттернов брошенных корзин"""
        abandonment_data = self.db.execute_query('''
            SELECT 
                u.id,
                u.name,
                COUNT(c.id) as items_in_cart,
                SUM(p.price * c.quantity) as cart_value,
                MAX(c.created_at) as last_activity,
                julianday('now') - julianday(MAX(c.created_at)) as hours_since_activity
            FROM users u
            JOIN cart c ON u.id = c.user_id
            JOIN products p ON c.product_id = p.id
            WHERE u.is_admin = 0
            GROUP BY u.id, u.name
            HAVING hours_since_activity > 1  # Более часа назад
            ORDER BY cart_value DESC
        ''')
        
        # Сегментируем по времени
        segments = {
            'recent': [],      # 1-24 часа
            'stale': [],       # 1-7 дней
            'abandoned': []    # 7+ дней
        }
        
        for cart in abandonment_data:
            hours = cart[5]
            if hours <= 24:
                segments['recent'].append(cart)
            elif hours <= 168:  # 7 дней
                segments['stale'].append(cart)
            else:
                segments['abandoned'].append(cart)
        
        return segments
    
    def create_abandonment_recovery_campaign(self, segment_type):
        """Создание кампании возврата брошенных корзин"""
        patterns = self.analyze_cart_abandonment_patterns()
        target_carts = patterns.get(segment_type, [])
        
        if not target_carts:
            return {'success': False, 'message': 'Нет подходящих корзин'}
        
        # Создаем сообщения в зависимости от сегмента
        if segment_type == 'recent':
            message_template = "🛒 Не забудьте завершить покупку!\n\nВ вашей корзине {items_count} товар(ов) на сумму {cart_value}"
            discount = 5
        elif segment_type == 'stale':
            message_template = "⏰ Товары в корзине ждут вас!\n\nСпециальная скидка 10% на вашу корзину: {cart_value}"
            discount = 10
        else:  # abandoned
            message_template = "💔 Мы скучаем по вам!\n\nВернитесь и получите 15% скидку на товары в корзине: {cart_value}"
            discount = 15
        
        campaign_results = []
        for cart in target_carts:
            user_id, name, items_count, cart_value, last_activity, hours = cart
            
            # Получаем telegram_id
            user = self.db.execute_query(
                'SELECT telegram_id, language FROM users WHERE id = ?',
                (user_id,)
            )[0]
            
            message = message_template.format(
                items_count=items_count,
                cart_value=format_price(cart_value)
            )
            
            campaign_results.append({
                'user_id': user_id,
                'telegram_id': user[0],
                'message': message,
                'discount': discount,
                'cart_value': cart_value
            })
        
        return {
            'success': True,
            'campaign_type': f'cart_abandonment_{segment_type}',
            'target_count': len(campaign_results),
            'results': campaign_results
        }