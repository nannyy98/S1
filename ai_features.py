"""
AI функции для телеграм-бота
"""

import re
from datetime import datetime
from collections import Counter

class AIRecommendationEngine:
    def __init__(self, db):
        self.db = db
    
    def get_personalized_recommendations(self, user_id, limit=5):
        """Персональные рекомендации на основе AI"""
        # Анализируем историю покупок пользователя
        user_purchases = self.db.execute_query('''
            SELECT p.category_id, p.price, oi.quantity
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.user_id = ? AND o.status != 'cancelled'
        ''', (user_id,))
        
        if not user_purchases:
            # Для новых пользователей - популярные товары
            return self.get_trending_products(limit)
        
        # Анализируем предпочтения
        category_preferences = Counter()
        price_preferences = []
        
        for category_id, price, quantity in user_purchases:
            category_preferences[category_id] += quantity
            price_preferences.extend([price] * quantity)
        
        # Определяем любимые категории
        top_categories = [cat_id for cat_id, _ in category_preferences.most_common(3)]
        
        # Определяем ценовой диапазон
        if price_preferences:
            avg_price = sum(price_preferences) / len(price_preferences)
            price_tolerance = avg_price * 0.3  # ±30% от средней цены
            min_price = max(0, avg_price - price_tolerance)
            max_price = avg_price + price_tolerance
        else:
            min_price, max_price = 0, 1000
        
        # Находим рекомендации
        placeholders = ','.join('?' * len(top_categories))
        recommendations = self.db.execute_query(f'''
            SELECT p.*, c.name as category_name,
                   (p.views * 0.3 + p.sales_count * 0.7) as popularity_score
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.is_active = 1
            AND p.category_id IN ({placeholders})
            AND p.price BETWEEN ? AND ?
            AND p.id NOT IN (
                SELECT DISTINCT oi.product_id
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE o.user_id = ?
            )
            ORDER BY popularity_score DESC, p.views DESC
            LIMIT ?
        ''', (*top_categories, min_price, max_price, user_id, limit))
        
        return recommendations
    
    def get_trending_products(self, limit=5):
        """Трендовые товары"""
        return self.db.execute_query('''
            SELECT p.*, c.name as category_name,
                   (p.views * 0.4 + p.sales_count * 0.6) as trend_score
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.is_active = 1
            ORDER BY trend_score DESC, p.created_at DESC
            LIMIT ?
        ''', (limit,))
    
    def get_collaborative_recommendations(self, user_id, limit=5):
        """Коллаборативная фильтрация - "Покупатели также покупали" """
        # Находим похожих пользователей
        similar_users = self.db.execute_query('''
            SELECT DISTINCT o2.user_id, COUNT(*) as common_products
            FROM order_items oi1
            JOIN orders o1 ON oi1.order_id = o1.id
            JOIN order_items oi2 ON oi1.product_id = oi2.product_id
            JOIN orders o2 ON oi2.order_id = o2.id
            WHERE o1.user_id = ? AND o2.user_id != ? 
            AND o1.status != 'cancelled' AND o2.status != 'cancelled'
            GROUP BY o2.user_id
            HAVING common_products >= 2
            ORDER BY common_products DESC
            LIMIT 10
        ''', (user_id, user_id))
        
        if not similar_users:
            return self.get_trending_products(limit)
        
        # Получаем товары, которые покупали похожие пользователи
        similar_user_ids = [user[0] for user in similar_users]
        placeholders = ','.join('?' * len(similar_user_ids))
        
        recommendations = self.db.execute_query(f'''
            SELECT p.*, c.name as category_name,
                   COUNT(*) as recommendation_score
            FROM products p
            JOIN categories c ON p.category_id = c.id
            JOIN order_items oi ON p.id = oi.product_id
            JOIN orders o ON oi.order_id = o.id
            WHERE p.is_active = 1
            AND o.user_id IN ({placeholders})
            AND o.status != 'cancelled'
            AND p.id NOT IN (
                SELECT DISTINCT oi2.product_id
                FROM order_items oi2
                JOIN orders o2 ON oi2.order_id = o2.id
                WHERE o2.user_id = ?
            )
            GROUP BY p.id
            ORDER BY recommendation_score DESC, p.views DESC
            LIMIT ?
        ''', (*similar_user_ids, user_id, limit))
        
        return recommendations
    
    def analyze_search_intent(self, search_query):
        """Анализ намерений поиска"""
        query_lower = search_query.lower()
        
        # Определяем категорию по ключевым словам
        category_keywords = {
            1: ['телефон', 'смартфон', 'iphone', 'samsung', 'ноутбук', 'компьютер', 'наушники'],
            2: ['футболка', 'джинсы', 'куртка', 'одежда', 'рубашка', 'платье'],
            3: ['кофеварка', 'посуда', 'дом', 'кухня', 'мебель'],
            4: ['кроссовки', 'спорт', 'фитнес', 'тренировка', 'мяч'],
            5: ['крем', 'косметика', 'парфюм', 'красота', 'уход'],
            6: ['книга', 'учебник', 'литература', 'роман']
        }
        
        detected_categories = []
        for cat_id, keywords in category_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_categories.append(cat_id)
        
        # Определяем ценовой диапазон
        price_keywords = {
            'дешевый': (0, 50),
            'недорогой': (0, 100),
            'средний': (50, 200),
            'дорогой': (200, 500),
            'премиум': (500, 10000),
            'люкс': (1000, 10000)
        }
        
        price_range = None
        for keyword, price_range_tuple in price_keywords.items():
            if keyword in query_lower:
                price_range = price_range_tuple
                break
        
        return {
            'categories': detected_categories,
            'price_range': price_range,
            'intent': self.classify_search_intent(query_lower)
        }
    
    def classify_search_intent(self, query):
        """Классификация намерения поиска"""
        if any(word in query for word in ['купить', 'заказать', 'нужен', 'хочу']):
            return 'purchase'
        elif any(word in query for word in ['сравнить', 'отличие', 'лучше']):
            return 'compare'
        elif any(word in query for word in ['отзыв', 'мнение', 'качество']):
            return 'research'
        else:
            return 'browse'
    
    def auto_categorize_product(self, product_name, product_description=""):
        """Автоматическая категоризация товара"""
        text = f"{product_name} {product_description}".lower()
        
        category_scores = {}
        
        # Ключевые слова для каждой категории
        category_keywords = {
            1: ['телефон', 'смартфон', 'iphone', 'android', 'ноутбук', 'компьютер', 'планшет', 'наушники', 'зарядка', 'кабель'],
            2: ['футболка', 'джинсы', 'куртка', 'рубашка', 'платье', 'юбка', 'брюки', 'свитер', 'кроссовки', 'ботинки'],
            3: ['кофеварка', 'чайник', 'посуда', 'кастрюля', 'сковорода', 'тарелка', 'стакан', 'нож', 'вилка', 'ложка'],
            4: ['кроссовки', 'мяч', 'гантели', 'тренажер', 'спорт', 'фитнес', 'велосипед', 'ракетка', 'форма'],
            5: ['крем', 'шампунь', 'мыло', 'парфюм', 'косметика', 'помада', 'тушь', 'пудра', 'лосьон'],
            6: ['книга', 'учебник', 'роман', 'детектив', 'фантастика', 'поэзия', 'справочник', 'словарь']
        }
        
        # Подсчитываем совпадения
        for cat_id, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                category_scores[cat_id] = score
        
        # Возвращаем категорию с наибольшим скором
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            confidence = category_scores[best_category] / len(category_keywords[best_category])
            return best_category, confidence
        
        return None, 0

class ChatbotSupport:
    def __init__(self, db):
        self.db = db
        self.faq_data = self.load_faq()
        self.context_memory = {}
    
    def load_faq(self):
        """Загрузка базы знаний FAQ"""
        return {
            'доставка': {
                'keywords': ['доставка', 'доставить', 'курьер', 'получить', 'адрес'],
                'answer': '''
🚚 <b>Информация о доставке:</b>

📦 <b>Варианты доставки:</b>
• Стандартная (3-5 дней) - $5
• Экспресс (1-2 дня) - $15
• В день заказа (до 18:00) - $25
• Самовывоз - бесплатно

📍 <b>Зоны доставки:</b>
• Ташкент и область
• Другие регионы Узбекистана

⏰ <b>Время доставки:</b>
• 09:00-12:00 (утром)
• 12:00-15:00 (днем)
• 15:00-18:00 (вечером)
• 18:00-21:00 (поздно вечером)
                '''
            },
            'оплата': {
                'keywords': ['оплата', 'платить', 'карта', 'наличные', 'payme', 'click'],
                'answer': '''
💳 <b>Способы оплаты:</b>

💳 <b>Онлайн:</b>
• Payme - популярная в Узбекистане
• Click - узбекская система
• Stripe - международная
• PayPal - глобальная
• ZoodPay - рассрочка

💵 <b>Наличными:</b>
• При получении заказа
• Без комиссии

🔒 <b>Безопасность:</b>
Все платежи защищены SSL-шифрованием
                '''
            },
            'возврат': {
                'keywords': ['возврат', 'вернуть', 'обмен', 'не подошло', 'брак'],
                'answer': '''
🔄 <b>Возврат и обмен:</b>

✅ <b>Условия возврата:</b>
• В течение 14 дней
• Товар в оригинальной упаковке
• Сохранен товарный вид

📋 <b>Процедура:</b>
1. Свяжитесь с поддержкой
2. Опишите причину возврата
3. Получите инструкции

💰 <b>Возврат средств:</b>
• На карту - 3-5 рабочих дней
• Наличными - при возврате товара
                '''
            },
            'размеры': {
                'keywords': ['размер', 'размеры', 'таблица размеров', 'подойдет'],
                'answer': '''
📏 <b>Размеры и подбор:</b>

👕 <b>Одежда:</b>
• S (44-46) - обхват груди 88-92 см
• M (48-50) - обхват груди 96-100 см  
• L (52-54) - обхват груди 104-108 см
• XL (56-58) - обхват груди 112-116 см

👟 <b>Обувь:</b>
• Размеры указаны в европейской системе
• При сомнениях выбирайте больший размер

📞 <b>Консультация:</b>
Свяжитесь с нами для индивидуального подбора
                '''
            },
            'гарантия': {
                'keywords': ['гарантия', 'сломался', 'не работает', 'ремонт'],
                'answer': '''
🛡 <b>Гарантия и сервис:</b>

⏰ <b>Сроки гарантии:</b>
• Электроника - 12 месяцев
• Одежда - 6 месяцев
• Остальные товары - 3 месяца

🔧 <b>Гарантийный ремонт:</b>
• Бесплатно при заводском браке
• Сроки ремонта: 7-14 дней

📞 <b>Обращение:</b>
Свяжитесь с поддержкой с номером заказа
                '''
            }
        }
    
    def find_best_answer(self, user_question):
        """Поиск лучшего ответа на вопрос"""
        question_lower = user_question.lower()
        
        best_match = None
        best_score = 0
        
        for topic, data in self.faq_data.items():
            score = 0
            for keyword in data['keywords']:
                if keyword in question_lower:
                    score += 1
            
            # Бонус за точное совпадение
            if topic in question_lower:
                score += 2
            
            if score > best_score:
                best_score = score
                best_match = data['answer']
        
        if best_score >= 1:
            return best_match
        
        return self.generate_fallback_response(user_question)
    
    def generate_fallback_response(self, question):
        """Ответ по умолчанию когда не найден точный ответ"""
        return '''
🤖 <b>Не нашел точный ответ на ваш вопрос</b>

Но я могу помочь с:
• 🚚 Информацией о доставке
• 💳 Способами оплаты  
• 🔄 Возвратом и обменом
• 📏 Размерами товаров
• 🛡 Гарантией

📞 <b>Или свяжитесь с поддержкой:</b>
• Telegram: @shop_support
• Телефон: +998 71 123-45-67
• Email: support@shop.uz

❓ Попробуйте переформулировать вопрос или используйте ключевые слова.
        '''
    
    def get_smart_search_suggestions(self, query):
        """Умные предложения для поиска"""
        suggestions = []
        
        # Исправление опечаток (простая реализация)
        common_typos = {
            'телефн': 'телефон',
            'айфон': 'iphone',
            'ноутбк': 'ноутбук',
            'кросовки': 'кроссовки',
            'футбока': 'футболка'
        }
        
        corrected_query = query.lower()
        for typo, correction in common_typos.items():
            corrected_query = corrected_query.replace(typo, correction)
        
        if corrected_query != query.lower():
            suggestions.append(f"Возможно, вы имели в виду: <b>{corrected_query}</b>")
        
        # Похожие запросы
        similar_products = self.db.execute_query('''
            SELECT name FROM products 
            WHERE name LIKE ? AND is_active = 1
            ORDER BY views DESC
            LIMIT 3
        ''', (f'%{query[:5]}%',))
        
        if similar_products:
            suggestions.append("Похожие товары:")
            for product in similar_products:
                suggestions.append(f"• {product[0]}")
        
        return suggestions
    
    def analyze_user_preferences(self, user_id):
        """Анализ предпочтений пользователя"""
        # История покупок
        purchase_history = self.db.execute_query('''
            SELECT p.category_id, p.price, p.name, oi.quantity
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.user_id = ? AND o.status != 'cancelled'
            ORDER BY o.created_at DESC
        ''', (user_id,))
        
        # История поиска (если есть)
        search_history = self.db.execute_query('''
            SELECT search_query, created_at
            FROM user_activity_logs
            WHERE user_id = ? AND action = 'search'
            ORDER BY created_at DESC
            LIMIT 20
        ''', (user_id,))
        
        # Анализируем предпочтения
        preferences = {
            'favorite_categories': [],
            'price_range': {'min': 0, 'max': 1000},
            'brands': [],
            'search_patterns': []
        }
        
        if purchase_history:
            # Любимые категории
            category_counts = Counter(item[0] for item in purchase_history)
            preferences['favorite_categories'] = [cat for cat, _ in category_counts.most_common(3)]
            
            # Ценовой диапазон
            prices = [item[1] for item in purchase_history]
            preferences['price_range'] = {
                'min': min(prices) * 0.7,
                'max': max(prices) * 1.3
            }
            
            # Анализ брендов (простая реализация)
            brand_keywords = ['apple', 'samsung', 'nike', 'adidas', 'sony']
            found_brands = []
            for item in purchase_history:
                product_name = item[2].lower()
                for brand in brand_keywords:
                    if brand in product_name:
                        found_brands.append(brand)
            
            preferences['brands'] = list(set(found_brands))
        
        if search_history:
            # Паттерны поиска
            search_queries = [item[0] for item in search_history]
            preferences['search_patterns'] = self.extract_search_patterns(search_queries)
        
        return preferences
    
    def extract_search_patterns(self, search_queries):
        """Извлечение паттернов из истории поиска"""
        all_words = []
        for query in search_queries:
            words = re.findall(r'\b\w+\b', query.lower())
            all_words.extend(words)
        
        # Находим часто используемые слова
        word_counts = Counter(all_words)
        common_words = [word for word, count in word_counts.most_common(10) if count > 1]
        
        return common_words
    
    def get_seasonal_recommendations(self, user_id=None):
        """Сезонные рекомендации"""
        current_month = datetime.now().month
        
        # Определяем сезон
        if current_month in [12, 1, 2]:
            season = 'winter'
            seasonal_keywords = ['зимний', 'теплый', 'куртка', 'сапоги', 'шарф']
        elif current_month in [3, 4, 5]:
            season = 'spring'
            seasonal_keywords = ['весенний', 'легкий', 'кроссовки', 'ветровка']
        elif current_month in [6, 7, 8]:
            season = 'summer'
            seasonal_keywords = ['летний', 'футболка', 'шорты', 'сандалии', 'купальник']
        else:
            season = 'autumn'
            seasonal_keywords = ['осенний', 'джинсы', 'свитер', 'ботинки']
        
        # Ищем сезонные товары
        seasonal_products = []
        for keyword in seasonal_keywords:
            products = self.db.execute_query('''
                SELECT * FROM products 
                WHERE (name LIKE ? OR description LIKE ?) 
                AND is_active = 1
                ORDER BY views DESC
                LIMIT 2
            ''', (f'%{keyword}%', f'%{keyword}%'))
            
            seasonal_products.extend(products)
        
        # Убираем дубликаты
        seen_ids = set()
        unique_products = []
        for product in seasonal_products:
            if product[0] not in seen_ids:
                unique_products.append(product)
                seen_ids.add(product[0])
        
        return unique_products[:5]

class SmartNotificationAI:
    def __init__(self, db):
        self.db = db
    
    def determine_best_notification_time(self, user_id):
        """Определение лучшего времени для уведомлений"""
        # Анализируем активность пользователя
        activity_hours = self.db.execute_query('''
            SELECT strftime('%H', created_at) as hour, COUNT(*) as activity_count
            FROM user_activity_logs
            WHERE user_id = ?
            GROUP BY hour
            ORDER BY activity_count DESC
            LIMIT 3
        ''', (user_id,))
        
        if activity_hours:
            # Возвращаем час с наибольшей активностью
            return int(activity_hours[0][0])
        
        # По умолчанию - 10:00
        return 10
    
    def generate_personalized_message(self, user_id, message_type, context=None):
        """Генерация персонализированного сообщения"""
        user = self.db.execute_query(
            'SELECT name, language FROM users WHERE id = ?',
            (user_id,)
        )[0]
        
        name = user[0]
        language = user[1]
        
        # Анализируем предпочтения пользователя
        ai_engine = AIRecommendationEngine(self.db)
        preferences = ai_engine.analyze_user_preferences(user_id)
        
        if message_type == 'cart_abandonment':
            if preferences['favorite_categories']:
                cat_name = self.get_category_name(preferences['favorite_categories'][0])
                message = f"🛒 {name}, в вашей корзине есть отличные товары из категории {cat_name}!"
            else:
                message = f"🛒 {name}, не забудьте о товарах в корзине!"
        
        elif message_type == 'recommendation':
            if preferences['brands']:
                brand = preferences['brands'][0].title()
                message = f"💡 {name}, новинки от {brand} уже в каталоге!"
            else:
                message = f"💡 {name}, специально для вас подобрали интересные товары!"
        
        elif message_type == 'promotion':
            if preferences['price_range']['max'] > 200:
                message = f"🎁 {name}, эксклюзивная скидка для VIP-клиентов!"
            else:
                message = f"🎁 {name}, специальная скидка только для вас!"
        
        else:
            message = f"👋 {name}, у нас есть новости для вас!"
        
        return message
    
    def get_category_name(self, category_id):
        """Получение названия категории"""
        category = self.db.execute_query(
            'SELECT name FROM categories WHERE id = ?',
            (category_id,)
        )
        return category[0][0] if category else "товары"
    
    def predict_user_churn_risk(self, user_id):
        """Прогноз риска ухода клиента"""
        # Анализируем активность пользователя
        user_stats = self.db.execute_query('''
            SELECT 
                COUNT(o.id) as total_orders,
                MAX(o.created_at) as last_order,
                AVG(o.total_amount) as avg_order_value,
                julianday('now') - julianday(MAX(o.created_at)) as days_since_last_order
            FROM orders o
            WHERE o.user_id = ? AND o.status != 'cancelled'
        ''', (user_id,))[0]
        
        if not user_stats[0]:  # Нет заказов
            return {'risk': 'low', 'score': 0, 'reason': 'Новый пользователь'}
        
        total_orders = user_stats[0]
        days_since_last = user_stats[3] or 0
        
        # Рассчитываем риск
        risk_score = 0
        
        # Фактор времени с последнего заказа
        if days_since_last > 90:
            risk_score += 40
        elif days_since_last > 60:
            risk_score += 25
        elif days_since_last > 30:
            risk_score += 10
        
        # Фактор количества заказов
        if total_orders == 1:
            risk_score += 20
        elif total_orders < 3:
            risk_score += 10
        
        # Фактор средней суммы заказа
        avg_order = user_stats[2] or 0
        if avg_order < 25:
            risk_score += 15
        
        # Определяем уровень риска
        if risk_score >= 60:
            risk_level = 'high'
            reason = 'Долго нет заказов, низкая активность'
        elif risk_score >= 30:
            risk_level = 'medium'
            reason = 'Снижение активности'
        else:
            risk_level = 'low'
            reason = 'Активный клиент'
        
        return {
            'risk': risk_level,
            'score': risk_score,
            'reason': reason,
            'days_since_last_order': days_since_last
        }
    
    def generate_win_back_offer(self, user_id):
        """Генерация предложения для возврата клиента"""
        churn_risk = self.predict_user_churn_risk(user_id)
        preferences = AIRecommendationEngine(self.db).analyze_user_preferences(user_id)
        
        # Определяем размер скидки
        if churn_risk['risk'] == 'high':
            discount = 25
        elif churn_risk['risk'] == 'medium':
            discount = 15
        else:
            discount = 10
        
        # Персонализируем предложение
        if preferences['favorite_categories']:
            cat_id = preferences['favorite_categories'][0]
            category_name = self.get_category_name(cat_id)
            offer_text = f"Скидка {discount}% на товары категории {category_name}"
        else:
            offer_text = f"Скидка {discount}% на весь каталог"
        
        return {
            'discount_percentage': discount,
            'offer_text': offer_text,
            'urgency': churn_risk['risk']
        }