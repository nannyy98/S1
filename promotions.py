"""
Модуль промокодов и скидок
"""

from datetime import datetime, timedelta
import random

class PromotionManager:
    def __init__(self, db):
        self.db = db
    
    def create_promo_code(self, code, discount_type, discount_value, min_order_amount=0, max_uses=None, expires_at=None, description=""):
        """Создание промокода"""
        return self.db.execute_query('''
            INSERT INTO promo_codes (
                code, discount_type, discount_value, min_order_amount,
                max_uses, expires_at, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (code, discount_type, discount_value, min_order_amount, max_uses, expires_at, description))
    
    def validate_promo_code(self, code, user_id, order_amount):
        """Проверка промокода"""
        promo = self.db.execute_query(
            'SELECT * FROM promo_codes WHERE code = ? AND is_active = 1',
            (code.upper(),)
        )
        
        if not promo:
            return {'valid': False, 'error': 'Промокод не найден'}
        
        promo_data = promo[0]
        
        # Проверка срока действия
        if promo_data[6] and datetime.now() > datetime.strptime(promo_data[6], '%Y-%m-%d %H:%M:%S'):
            return {'valid': False, 'error': 'Промокод истек'}
        
        # Проверка минимальной суммы заказа
        if order_amount < promo_data[4]:
            return {'valid': False, 'error': f'Минимальная сумма заказа: {format_price(promo_data[4])}'}
        
        # Проверка лимита использований
        if promo_data[5]:
            uses_count = self.db.execute_query(
                'SELECT COUNT(*) FROM promo_uses WHERE promo_code_id = ?',
                (promo_data[0],)
            )[0][0]
            
            if uses_count >= promo_data[5]:
                return {'valid': False, 'error': 'Промокод исчерпан'}
        
        # Проверка использования пользователем
        user_uses = self.db.execute_query(
            'SELECT COUNT(*) FROM promo_uses WHERE promo_code_id = ? AND user_id = ?',
            (promo_data[0], user_id)
        )[0][0]
        
        if user_uses > 0:
            return {'valid': False, 'error': 'Промокод уже использован'}
        
        # Рассчитываем скидку
        discount_amount = self.calculate_discount(promo_data, order_amount)
        
        return {
            'valid': True,
            'promo_id': promo_data[0],
            'discount_amount': discount_amount,
            'description': promo_data[7]
        }
    
    def calculate_discount(self, promo_data, order_amount):
        """Расчет размера скидки"""
        discount_type = promo_data[2]
        discount_value = promo_data[3]
        
        if discount_type == 'percentage':
            return min(order_amount * (discount_value / 100), order_amount)
        elif discount_type == 'fixed':
            return min(discount_value, order_amount)
        
        return 0
    
    def apply_promo_code(self, promo_id, user_id, order_id, discount_amount):
        """Применение промокода к заказу"""
        # Записываем использование
        self.db.execute_query(
            'INSERT INTO promo_uses (promo_code_id, user_id, order_id, discount_amount) VALUES (?, ?, ?, ?)',
            (promo_id, user_id, order_id, discount_amount)
        )
        
        # Обновляем сумму заказа
        self.db.execute_query(
            'UPDATE orders SET total_amount = total_amount - ?, promo_discount = ? WHERE id = ?',
            (discount_amount, discount_amount, order_id)
        )
        
        return True
    
    def generate_personal_promo(self, user_id, occasion='birthday'):
        """Генерация персонального промокода"""
        user = self.db.execute_query('SELECT name FROM users WHERE id = ?', (user_id,))[0]
        user_name = user[0].replace(' ', '').upper()[:6]
        
        if occasion == 'birthday':
            code = f"BIRTHDAY{user_name}{random.randint(10, 99)}"
            discount_value = 15
            description = "Скидка в честь дня рождения"
        elif occasion == 'first_order':
            code = f"WELCOME{user_name}{random.randint(10, 99)}"
            discount_value = 10
            description = "Скидка на первый заказ"
        elif occasion == 'return':
            code = f"RETURN{user_name}{random.randint(10, 99)}"
            discount_value = 20
            description = "Скидка для возвращения"
        else:
            code = f"SPECIAL{user_name}{random.randint(10, 99)}"
            discount_value = 12
            description = "Специальная скидка"
        
        expires_at = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        
        promo_id = self.create_promo_code(
            code, 'percentage', discount_value, 0, 1, expires_at, description
        )
        
        return {
            'code': code,
            'discount': discount_value,
            'expires_at': expires_at,
            'description': description
        }
    
    def get_active_promotions(self):
        """Получение активных акций"""
        return self.db.execute_query('''
            SELECT * FROM promo_codes 
            WHERE is_active = 1 
            AND (expires_at IS NULL OR expires_at > datetime('now'))
            AND (max_uses IS NULL OR (
                SELECT COUNT(*) FROM promo_uses WHERE promo_code_id = promo_codes.id
            ) < max_uses)
            ORDER BY created_at DESC
        ''')
    
    def create_flash_sale(self, product_ids, discount_percentage, duration_hours=24):
        """Создание флеш-распродажи"""
        expires_at = (datetime.now() + timedelta(hours=duration_hours)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Создаем промокод для флеш-распродажи
        flash_code = f"FLASH{random.randint(1000, 9999)}"
        
        promo_id = self.create_promo_code(
            flash_code,
            'percentage',
            discount_percentage,
            0,
            None,  # Без ограничения использований
            expires_at,
            f"Флеш-распродажа {discount_percentage}% на {duration_hours} часов"
        )
        
        # Сохраняем товары участвующие в акции
        for product_id in product_ids:
            self.db.execute_query(
                'INSERT INTO flash_sale_products (promo_code_id, product_id) VALUES (?, ?)',
                (promo_id, product_id)
            )
        
        return {
            'code': flash_code,
            'discount': discount_percentage,
            'duration': duration_hours,
            'products_count': len(product_ids)
        }
    
    def get_user_available_promos(self, user_id):
        """Получение доступных промокодов для пользователя"""
        return self.db.execute_query('''
            SELECT pc.* FROM promo_codes pc
            WHERE pc.is_active = 1
            AND (pc.expires_at IS NULL OR pc.expires_at > datetime('now'))
            AND (pc.max_uses IS NULL OR (
                SELECT COUNT(*) FROM promo_uses pu WHERE pu.promo_code_id = pc.id
            ) < pc.max_uses)
            AND pc.id NOT IN (
                SELECT promo_code_id FROM promo_uses WHERE user_id = ?
            )
            ORDER BY pc.discount_value DESC
        ''', (user_id,))