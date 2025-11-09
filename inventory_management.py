"""
Модуль управления складом и инвентаризацией
"""
import logging

from datetime import datetime, timedelta
from utils import format_price, format_date

class InventoryManager:
    def __init__(self, db):
        self.db = db
        self.reorder_rules = {}
        self.suppliers = {}
        self.load_reorder_rules()
    
    def load_reorder_rules(self):
        """Загрузка правил автопополнения"""
        rules = self.db.execute_query('''
            SELECT product_id, reorder_point, reorder_quantity, supplier_id
            FROM inventory_rules
            WHERE is_active = 1
        ''')
        
        for rule in rules:
            self.reorder_rules[rule[0]] = {
                'reorder_point': rule[1],
                'reorder_quantity': rule[2],
                'supplier_id': rule[3]
            }
    
    def check_stock_levels(self):
        """Проверка уровней остатков"""
        low_stock_products = self.db.execute_query('''
            SELECT id, name, stock, category_id
            FROM products
            WHERE stock <= 5 AND is_active = 1
            ORDER BY stock ASC
        ''')
        
        critical_stock = []
        low_stock = []
        
        for product in low_stock_products:
            if product[2] == 0:
                critical_stock.append(product)
            else:
                low_stock.append(product)
        
        return {
            'critical': critical_stock,
            'low': low_stock,
            'total_affected': len(low_stock_products)
        }
    
    def update_stock(self, product_id, new_quantity, movement_type='manual', reason=""):
        """Обновление остатков товара"""
        # Получаем текущий остаток
        current_stock = self.db.execute_query(
            'SELECT stock FROM products WHERE id = ?',
            (product_id,)
        )
        
        if not current_stock:
            return False
        
        old_quantity = current_stock[0][0]
        quantity_change = new_quantity - old_quantity
        
        # Обновляем остаток
        self.db.execute_query(
            'UPDATE products SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (new_quantity, product_id)
        )
        
        # Записываем движение
        self.db.execute_query('''
            INSERT INTO inventory_movements (
                product_id, movement_type, quantity_change, 
                old_quantity, new_quantity, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_id, movement_type, quantity_change,
            old_quantity, new_quantity, reason,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        # Проверяем правила автопополнения
        if new_quantity <= self.reorder_rules.get(product_id, {}).get('reorder_point', 0):
            self.trigger_automatic_reorder(product_id)
        
        return True
    
    def add_stock(self, product_id, quantity, supplier_id=None, cost_per_unit=None, reason="Поступление"):
        """Добавление товара на склад"""
        current_stock = self.db.execute_query(
            'SELECT stock FROM products WHERE id = ?',
            (product_id,)
        )[0][0]
        
        new_stock = current_stock + quantity
        
        # Обновляем остаток
        self.db.execute_query(
            'UPDATE products SET stock = ? WHERE id = ?',
            (new_stock, product_id)
        )
        
        # Записываем поступление
        self.db.execute_query('''
            INSERT INTO inventory_movements (
                product_id, movement_type, quantity_change,
                old_quantity, new_quantity, supplier_id, cost_per_unit, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_id, 'inbound', quantity,
            current_stock, new_stock, supplier_id, cost_per_unit, reason,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        # Уведомляем о поступлении
        self.notify_restock(product_id)
        
        return new_stock
    
    def reserve_stock(self, product_id, quantity, order_id):
        """Резервирование товара для заказа"""
        current_stock = self.db.execute_query(
            'SELECT stock FROM products WHERE id = ?',
            (product_id,)
        )[0][0]
        
        if current_stock < quantity:
            return False, "Недостаточно товара на складе"
        
        # Создаем резерв
        self.db.execute_query('''
            INSERT INTO stock_reservations (
                product_id, order_id, quantity, expires_at, created_at
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            product_id, order_id, quantity,
            (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S'),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        # Уменьшаем доступный остаток
        self.db.execute_query(
            'UPDATE products SET stock = stock - ? WHERE id = ?',
            (quantity, product_id)
        )
        
        return True, "Товар зарезервирован"
    
    def release_reservation(self, order_id):
        """Освобождение резерва при отмене заказа"""
        reservations = self.db.execute_query(
            'SELECT product_id, quantity FROM stock_reservations WHERE order_id = ?',
            (order_id,)
        )
        
        for reservation in reservations:
            product_id, quantity = reservation
            
            # Возвращаем товар на склад
            self.db.execute_query(
                'UPDATE products SET stock = stock + ? WHERE id = ?',
                (quantity, product_id)
            )
        
        # Удаляем резервы
        self.db.execute_query(
            'DELETE FROM stock_reservations WHERE order_id = ?',
            (order_id,)
        )
    
    def trigger_automatic_reorder(self, product_id):
        """Автоматическое пополнение товара"""
        if product_id not in self.reorder_rules:
            return False
        
        rule = self.reorder_rules[product_id]
        
        # Проверяем, не было ли недавнего заказа
        recent_order = self.db.execute_query('''
            SELECT id FROM purchase_orders
            WHERE product_id = ? AND created_at >= datetime('now', '-7 days')
        ''', (product_id,))
        
        if recent_order:
            return False  # Уже заказывали недавно
        
        # Создаем заказ поставщику
        purchase_order_id = self.create_purchase_order(
            product_id,
            rule['reorder_quantity'],
            rule['supplier_id']
        )
        
        # Уведомляем админов
        self.notify_automatic_reorder(product_id, rule['reorder_quantity'], purchase_order_id)
        
        return purchase_order_id
    
    def create_purchase_order(self, product_id, quantity, supplier_id):
        """Создание заказа поставщику"""
        product = self.db.get_product_by_id(product_id)
        if not product:
            return None
        
        # Получаем данные поставщика
        supplier = self.db.execute_query(
            'SELECT name, contact_email, cost_per_unit FROM suppliers WHERE id = ?',
            (supplier_id,)
        )
        
        if not supplier:
            return None
        
        supplier_data = supplier[0]
        total_cost = quantity * supplier_data[2]
        
        # Создаем заказ
        purchase_order_id = self.db.execute_query('''
            INSERT INTO purchase_orders (
                product_id, supplier_id, quantity, cost_per_unit,
                total_amount, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_id, supplier_id, quantity, supplier_data[2],
            total_cost, 'pending',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        return purchase_order_id
    
    def notify_automatic_reorder(self, product_id, quantity, purchase_order_id):
        """Уведомление об автоматическом заказе"""
        product = self.db.get_product_by_id(product_id)
        
        notification_text = f"🔄 <b>Автоматический заказ поставщику</b>\n\n"
        notification_text += f"📦 Товар: {product[1]}\n"
        notification_text += f"📊 Количество: {quantity} шт.\n"
        notification_text += f"📋 Заказ: #{purchase_order_id}\n"
        notification_text += f"⏰ Время: {format_date(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}\n\n"
        notification_text += f"✅ Заказ отправлен поставщику автоматически"
        
        # Отправляем всем админам
        admins = self.db.execute_query('SELECT telegram_id FROM users WHERE is_admin = 1')
        for admin in admins:
            try:
                # Используем метод бота для отправки
                if hasattr(self, 'bot'):
                    self.bot.send_message(admin[0], notification_text)
            except Exception as e:
                logging.info(f"Ошибка уведомления админа {admin[0]}: {e}")
    
    def notify_restock(self, product_id):
        """Уведомление о поступлении товара"""
        # Находим пользователей, которые добавляли товар в избранное
        interested_users = self.db.execute_query('''
            SELECT u.telegram_id, u.name, u.language
            FROM users u
            JOIN favorites f ON u.id = f.user_id
            WHERE f.product_id = ?
        ''', (product_id,))
        
        product = self.db.get_product_by_id(product_id)
        
        for user in interested_users:
            from localization import t
            language = user[2]
            
            restock_text = f"📦 <b>{t('restock_notification', language=language)}</b>\n\n"
            restock_text += f"🛍 <b>{product[1]}</b>\n"
            restock_text += f"💰 {format_price(product[3])}\n\n"
            restock_text += f"✅ {t('back_in_stock', language=language)}\n"
            restock_text += f"🏃‍♂️ {t('order_now', language=language)}"
            
            try:
                if hasattr(self, 'bot'):
                    self.bot.send_message(user[0], restock_text)
            except Exception as e:
                logging.info(f"Ошибка уведомления о поступлении {user[0]}: {e}")
    
    def get_inventory_report(self, report_type='summary'):
        """Получение отчета по складу"""
        if report_type == 'summary':
            return self.get_inventory_summary()
        elif report_type == 'movements':
            return self.get_movements_report()
        elif report_type == 'abc_analysis':
            return self.get_abc_inventory_analysis()
        elif report_type == 'turnover':
            return self.get_turnover_analysis()
        
        return None
    
    def get_inventory_summary(self):
        """Сводка по складу"""
        summary = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_products,
                SUM(stock) as total_units,
                SUM(stock * price) as total_value,
                COUNT(CASE WHEN stock = 0 THEN 1 END) as out_of_stock,
                COUNT(CASE WHEN stock <= 5 THEN 1 END) as low_stock
            FROM products
            WHERE is_active = 1
        ''')[0]
        
        # Топ товары по стоимости запасов
        top_value_products = self.db.execute_query('''
            SELECT name, stock, price, (stock * price) as inventory_value
            FROM products
            WHERE is_active = 1 AND stock > 0
            ORDER BY inventory_value DESC
            LIMIT 10
        ''')
        
        return {
            'total_products': summary[0],
            'total_units': summary[1],
            'total_value': summary[2],
            'out_of_stock': summary[3],
            'low_stock': summary[4],
            'top_value_products': top_value_products
        }
    
    def get_movements_report(self, days=30):
        """Отчет по движениям товаров"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        movements = self.db.execute_query('''
            SELECT 
                im.created_at,
                p.name,
                im.movement_type,
                im.quantity_change,
                im.reason,
                s.name as supplier_name
            FROM inventory_movements im
            JOIN products p ON im.product_id = p.id
            LEFT JOIN suppliers s ON im.supplier_id = s.id
            WHERE DATE(im.created_at) >= ?
            ORDER BY im.created_at DESC
        ''', (start_date,))
        
        # Статистика движений
        movement_stats = self.db.execute_query('''
            SELECT 
                movement_type,
                COUNT(*) as count,
                SUM(ABS(quantity_change)) as total_quantity
            FROM inventory_movements
            WHERE DATE(created_at) >= ?
            GROUP BY movement_type
        ''', (start_date,))
        
        return {
            'movements': movements,
            'stats': movement_stats,
            'period_days': days
        }
    
    def get_abc_inventory_analysis(self):
        """ABC анализ товаров по стоимости запасов"""
        inventory_data = self.db.execute_query('''
            SELECT 
                id, name, stock, price, (stock * price) as inventory_value
            FROM products
            WHERE is_active = 1 AND stock > 0
            ORDER BY inventory_value DESC
        ''')
        
        if not inventory_data:
            return {'categories': {}, 'total_value': 0}
        
        total_value = sum(item[4] for item in inventory_data)
        
        # Классификация ABC
        abc_products = {'A': [], 'B': [], 'C': []}
        cumulative_value = 0
        
        for product in inventory_data:
            cumulative_value += product[4]
            cumulative_percentage = (cumulative_value / total_value) * 100
            
            if cumulative_percentage <= 80:
                category = 'A'
            elif cumulative_percentage <= 95:
                category = 'B'
            else:
                category = 'C'
            
            abc_products[category].append({
                'id': product[0],
                'name': product[1],
                'stock': product[2],
                'price': product[3],
                'inventory_value': product[4],
                'value_percentage': (product[4] / total_value) * 100
            })
        
        return {
            'categories': abc_products,
            'total_value': total_value
        }
    
    def get_turnover_analysis(self, days=90):
        """Анализ оборачиваемости товаров"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        turnover_data = self.db.execute_query('''
            SELECT 
                p.id,
                p.name,
                p.stock,
                COALESCE(SUM(oi.quantity), 0) as sold_quantity,
                p.price,
                CASE 
                    WHEN p.stock > 0 THEN COALESCE(SUM(oi.quantity), 0) * 1.0 / p.stock
                    ELSE 0 
                END as turnover_ratio,
                CASE
                    WHEN COALESCE(SUM(oi.quantity), 0) = 0 THEN 'Не продается'
                    WHEN p.stock <= 5 THEN 'Критический остаток'
                    WHEN p.stock <= 10 THEN 'Низкий остаток'
                    WHEN p.stock >= 50 THEN 'Избыток'
                    ELSE 'Нормальный'
                END as stock_status
            FROM products p
            LEFT JOIN order_items oi ON p.id = oi.product_id
            LEFT JOIN orders o ON oi.order_id = o.id AND o.status != 'cancelled'
                AND DATE(o.created_at) >= ?
            WHERE p.is_active = 1
            GROUP BY p.id, p.name, p.stock, p.price
            ORDER BY turnover_ratio DESC
        ''', (start_date,))
        
        # Категоризация по оборачиваемости
        fast_moving = []
        slow_moving = []
        dead_stock = []
        
        for item in turnover_data:
            if item[5] >= 2:  # Оборачиваемость >= 2
                fast_moving.append(item)
            elif item[5] > 0:
                slow_moving.append(item)
            else:
                dead_stock.append(item)
        
        return {
            'fast_moving': fast_moving,
            'slow_moving': slow_moving,
            'dead_stock': dead_stock,
            'analysis_period': days
        }
    
    def forecast_demand(self, product_id, days_ahead=30):
        """Прогнозирование спроса на товар"""
        # Анализируем продажи за последние 90 дней
        sales_history = self.db.execute_query('''
            SELECT 
                DATE(o.created_at) as sale_date,
                SUM(oi.quantity) as daily_sales
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE oi.product_id = ?
            AND o.created_at >= datetime('now', '-90 days')
            AND o.status != 'cancelled'
            GROUP BY DATE(o.created_at)
            ORDER BY sale_date
        ''', (product_id,))
        
        if len(sales_history) < 7:
            return None
        
        # Простое скользящее среднее
        daily_sales = [sale[1] for sale in sales_history]
        avg_daily_sales = sum(daily_sales) / len(daily_sales)
        
        # Учитываем тренд (последние 30 дней vs предыдущие 30)
        if len(daily_sales) >= 60:
            recent_avg = sum(daily_sales[-30:]) / 30
            previous_avg = sum(daily_sales[-60:-30]) / 30
            trend_factor = recent_avg / previous_avg if previous_avg > 0 else 1
        else:
            trend_factor = 1
        
        # Прогноз
        forecasted_daily = avg_daily_sales * trend_factor
        forecasted_total = forecasted_daily * days_ahead
        
        # Рекомендуемый заказ с запасом
        safety_stock = forecasted_total * 0.2  # 20% запас
        recommended_order = forecasted_total + safety_stock
        
        return {
            'avg_daily_sales': avg_daily_sales,
            'trend_factor': trend_factor,
            'forecasted_daily': forecasted_daily,
            'forecasted_total': forecasted_total,
            'recommended_order': recommended_order,
            'confidence': 'High' if len(daily_sales) >= 30 else 'Medium'
        }
    
    def create_reorder_rule(self, product_id, reorder_point, reorder_quantity, supplier_id):
        """Создание правила автопополнения"""
        return self.db.execute_query('''
            INSERT INTO inventory_rules (
                product_id, reorder_point, reorder_quantity, supplier_id, is_active, created_at
            ) VALUES (?, ?, ?, ?, 1, ?)
        ''', (
            product_id, reorder_point, reorder_quantity, supplier_id,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    def add_supplier(self, name, contact_email, phone, address, payment_terms):
        """Добавление поставщика"""
        return self.db.execute_query('''
            INSERT INTO suppliers (
                name, contact_email, phone, address, payment_terms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            name, contact_email, phone, address, payment_terms,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    def process_incoming_shipment(self, purchase_order_id, received_quantity, condition='good'):
        """Обработка входящей поставки"""
        # Получаем данные заказа
        purchase_order = self.db.execute_query(
            'SELECT product_id, quantity, cost_per_unit FROM purchase_orders WHERE id = ?',
            (purchase_order_id,)
        )
        
        if not purchase_order:
            return False
        
        product_id, ordered_quantity, cost_per_unit = purchase_order[0]
        
        # Добавляем товар на склад
        self.add_stock(
            product_id, received_quantity, 
            cost_per_unit=cost_per_unit,
            reason=f"Поставка по заказу #{purchase_order_id}"
        )
        
        # Обновляем статус заказа
        if received_quantity >= ordered_quantity:
            new_status = 'completed'
        else:
            new_status = 'partially_received'
        
        self.db.execute_query(
            'UPDATE purchase_orders SET status = ?, received_quantity = ? WHERE id = ?',
            (new_status, received_quantity, purchase_order_id)
        )
        
        return True
    
    def check_reorder_alerts(self):
        """Проверка товаров требующих пополнения"""
        alerts = []
        
        for product_id, rule in self.reorder_rules.items():
            current_stock = self.db.execute_query(
                'SELECT stock, name FROM products WHERE id = ?',
                (product_id,)
            )
            
            if current_stock and current_stock[0][0] <= rule['reorder_point']:
                alerts.append({
                    'product_id': product_id,
                    'product_name': current_stock[0][1],
                    'current_stock': current_stock[0][0],
                    'reorder_point': rule['reorder_point'],
                    'recommended_quantity': rule['reorder_quantity']
                })
        
        return alerts
    
    def process_automatic_reorders(self):
        """Обработка автоматических заказов"""
        alerts = self.check_reorder_alerts()
        
        for alert in alerts:
            # Проверяем, не заказывали ли уже
            recent_order = self.db.execute_query('''
                SELECT id FROM purchase_orders
                WHERE product_id = ? AND created_at >= datetime('now', '-7 days')
                AND status IN ('pending', 'sent')
            ''', (alert['product_id'],))
            
            if not recent_order:
                # Создаем автоматический заказ
                rule = self.reorder_rules[alert['product_id']]
                purchase_order_id = self.create_purchase_order(
                    alert['product_id'],
                    rule['reorder_quantity'],
                    rule['supplier_id']
                )
                
                if purchase_order_id:
                    self.notify_automatic_reorder(
                        alert['product_id'],
                        rule['reorder_quantity'],
                        purchase_order_id
                    )
    
    def get_supplier_performance(self, supplier_id=None, days=90):
        """Анализ эффективности поставщиков"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        if supplier_id:
            suppliers_data = self.db.execute_query('''
                SELECT 
                    s.id, s.name,
                    COUNT(po.id) as total_orders,
                    SUM(po.total_amount) as total_spent,
                    AVG(julianday(po.delivered_at) - julianday(po.created_at)) as avg_delivery_days,
                    COUNT(CASE WHEN po.status = 'completed' THEN 1 END) * 100.0 / COUNT(po.id) as completion_rate
                FROM suppliers s
                LEFT JOIN purchase_orders po ON s.id = po.supplier_id
                    AND DATE(po.created_at) >= ?
                WHERE s.id = ?
                GROUP BY s.id, s.name
            ''', (start_date, supplier_id))
        else:
            suppliers_data = self.db.execute_query('''
                SELECT 
                    s.id, s.name,
                    COUNT(po.id) as total_orders,
                    SUM(po.total_amount) as total_spent,
                    AVG(julianday(po.delivered_at) - julianday(po.created_at)) as avg_delivery_days,
                    COUNT(CASE WHEN po.status = 'completed' THEN 1 END) * 100.0 / COUNT(po.id) as completion_rate
                FROM suppliers s
                LEFT JOIN purchase_orders po ON s.id = po.supplier_id
                    AND DATE(po.created_at) >= ?
                GROUP BY s.id, s.name
                ORDER BY total_spent DESC
            ''', (start_date,))
        
        return suppliers_data
    
    def optimize_inventory_levels(self):
        """Оптимизация уровней запасов"""
        recommendations = []
        
        # Анализируем каждый товар
        products = self.db.execute_query('''
            SELECT id, name, stock, price
            FROM products
            WHERE is_active = 1
        ''')
        
        for product in products:
            product_id, name, current_stock, price = product
            
            # Получаем прогноз спроса
            demand_forecast = self.forecast_demand(product_id, 30)
            
            if demand_forecast:
                recommended_stock = demand_forecast['recommended_order']
                
                if current_stock < recommended_stock * 0.5:
                    recommendations.append({
                        'product_id': product_id,
                        'product_name': name,
                        'current_stock': current_stock,
                        'recommended_stock': recommended_stock,
                        'action': 'increase',
                        'priority': 'high' if current_stock == 0 else 'medium'
                    })
                elif current_stock > recommended_stock * 2:
                    recommendations.append({
                        'product_id': product_id,
                        'product_name': name,
                        'current_stock': current_stock,
                        'recommended_stock': recommended_stock,
                        'action': 'decrease',
                        'priority': 'low'
                    })
        
        return recommendations
    
    def create_stocktaking_session(self, location="Основной склад"):
        """Создание сессии инвентаризации"""
        session_id = self.db.execute_query('''
            INSERT INTO stocktaking_sessions (
                location, status, started_at, created_by
            ) VALUES (?, 'active', ?, 1)
        ''', (location, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        # Создаем записи для всех товаров
        products = self.db.execute_query(
            'SELECT id, stock FROM products WHERE is_active = 1'
        )
        
        for product in products:
            self.db.execute_query('''
                INSERT INTO stocktaking_items (
                    session_id, product_id, system_quantity, counted_quantity
                ) VALUES (?, ?, ?, NULL)
            ''', (session_id, product[0], product[1]))
        
        return session_id
    
    def update_stocktaking_count(self, session_id, product_id, counted_quantity):
        """Обновление подсчета при инвентаризации"""
        return self.db.execute_query('''
            UPDATE stocktaking_items 
            SET counted_quantity = ?, counted_at = ?
            WHERE session_id = ? AND product_id = ?
        ''', (
            counted_quantity, 
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            session_id, product_id
        ))
    
    def complete_stocktaking(self, session_id):
        """Завершение инвентаризации"""
        # Получаем расхождения
        discrepancies = self.db.execute_query('''
            SELECT 
                si.product_id, p.name, si.system_quantity, si.counted_quantity,
                (si.counted_quantity - si.system_quantity) as difference
            FROM stocktaking_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.session_id = ? AND si.counted_quantity IS NOT NULL
            AND si.counted_quantity != si.system_quantity
        ''', (session_id,))
        
        # Применяем корректировки
        for discrepancy in discrepancies:
            product_id, name, system_qty, counted_qty, difference = discrepancy
            
            # Обновляем остаток
            self.db.execute_query(
                'UPDATE products SET stock = ? WHERE id = ?',
                (counted_qty, product_id)
            )
            
            # Записываем движение
            self.db.execute_query('''
                INSERT INTO inventory_movements (
                    product_id, movement_type, quantity_change,
                    old_quantity, new_quantity, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                product_id, 'adjustment', difference,
                system_qty, counted_qty, f'Инвентаризация #{session_id}',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        # Закрываем сессию
        self.db.execute_query('''
            UPDATE stocktaking_sessions 
            SET status = 'completed', completed_at = ?
            WHERE id = ?
        ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session_id))
        
        return {
            'discrepancies_count': len(discrepancies),
            'discrepancies': discrepancies
        }
    
    def get_inventory_valuation(self, method='fifo'):
        """Оценка стоимости запасов"""
        if method == 'fifo':
            # FIFO - первый пришел, первый ушел
            valuation = self.db.execute_query('''
                SELECT 
                    p.id, p.name, p.stock,
                    AVG(im.cost_per_unit) as avg_cost,
                    p.stock * AVG(im.cost_per_unit) as inventory_value
                FROM products p
                LEFT JOIN inventory_movements im ON p.id = im.product_id
                    AND im.movement_type = 'inbound'
                    AND im.cost_per_unit IS NOT NULL
                WHERE p.is_active = 1 AND p.stock > 0
                GROUP BY p.id, p.name, p.stock
                ORDER BY inventory_value DESC
            ''')
        else:
            # Текущая цена
            valuation = self.db.execute_query('''
                SELECT 
                    id, name, stock, price as avg_cost,
                    stock * price as inventory_value
                FROM products
                WHERE is_active = 1 AND stock > 0
                ORDER BY inventory_value DESC
            ''')
        
        total_value = sum(item[4] for item in valuation if item[4])
        
        return {
            'method': method,
            'total_value': total_value,
            'products': valuation
        }
    
    def generate_purchase_order_document(self, purchase_order_id):
        """Генерация документа заказа поставщику"""
        order_data = self.db.execute_query('''
            SELECT 
                po.id, po.quantity, po.cost_per_unit, po.total_amount,
                po.created_at, po.status,
                p.name as product_name, p.description,
                s.name as supplier_name, s.contact_email, s.phone, s.address
            FROM purchase_orders po
            JOIN products p ON po.product_id = p.id
            JOIN suppliers s ON po.supplier_id = s.id
            WHERE po.id = ?
        ''', (purchase_order_id,))
        
        if not order_data:
            return None
        
        order = order_data[0]
        
        document = f"""
📋 ЗАКАЗ ПОСТАВЩИКУ #{order[0]}

📅 Дата: {format_date(order[4])}
📊 Статус: {order[5]}

🏢 ПОСТАВЩИК:
Название: {order[7]}
Email: {order[8]}
Телефон: {order[9]}
Адрес: {order[10]}

📦 ТОВАР:
Название: {order[6]}
Описание: {order[7] or 'Не указано'}
Количество: {order[1]} шт.
Цена за единицу: {format_price(order[2])}

💰 ИТОГО: {format_price(order[3])}

---
Документ сгенерирован автоматически
        """
        
        return document
    
    def format_inventory_report(self, report_type, data):
        """Форматирование отчета по складу"""
        if report_type == 'summary':
            text = f"📦 <b>Сводка по складу</b>\n\n"
            text += f"📊 <b>Общие показатели:</b>\n"
            text += f"🛍 Товаров: {data['total_products']}\n"
            text += f"📦 Единиц: {data['total_units']}\n"
            text += f"💰 Стоимость: {format_price(data['total_value'])}\n"
            text += f"🔴 Нет в наличии: {data['out_of_stock']}\n"
            text += f"🟡 Мало на складе: {data['low_stock']}\n\n"
            
            if data['top_value_products']:
                text += f"💎 <b>Топ по стоимости запасов:</b>\n"
                for product in data['top_value_products'][:5]:
                    text += f"• {product[0]} - {format_price(product[3])}\n"
            
            return text
        
        elif report_type == 'abc_analysis':
            text = f"📊 <b>ABC анализ склада</b>\n\n"
            text += f"💰 Общая стоимость: {format_price(data['total_value'])}\n\n"
            
            for category, products in data['categories'].items():
                if products:
                    category_value = sum(p['inventory_value'] for p in products)
                    text += f"🏷 <b>Категория {category}:</b>\n"
                    text += f"📦 Товаров: {len(products)}\n"
                    text += f"💰 Стоимость: {format_price(category_value)}\n"
                    text += f"📊 Доля: {(category_value/data['total_value']*100):.1f}%\n\n"
            
            return text
        
        elif report_type == 'turnover':
            text = f"🔄 <b>Анализ оборачиваемости</b>\n"
            text += f"📅 Период: {data['analysis_period']} дней\n\n"
            
            text += f"🔥 <b>Быстрооборачиваемые ({len(data['fast_moving'])}):</b>\n"
            for item in data['fast_moving'][:5]:
                text += f"• {item[1]} - оборот: {item[5]:.1f}\n"
            
            text += f"\n🐌 <b>Медленнооборачиваемые ({len(data['slow_moving'])}):</b>\n"
            for item in data['slow_moving'][:5]:
                text += f"• {item[1]} - оборот: {item[5]:.1f}\n"
            
            if data['dead_stock']:
                text += f"\n💀 <b>Неликвиды ({len(data['dead_stock'])}):</b>\n"
                for item in data['dead_stock'][:3]:
                    text += f"• {item[1]} - {item[2]} шт.\n"
            
            return text
        
        return "❌ Неизвестный тип отчета"
    
    def export_inventory_csv(self, report_type):
        """Экспорт данных склада в CSV"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if report_type == 'stock_levels':
            products = self.db.execute_query('''
                SELECT 
                    p.id, p.name, p.stock, p.price,
                    (p.stock * p.price) as inventory_value,
                    c.name as category
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.is_active = 1
                ORDER BY inventory_value DESC
            ''')
            
            writer.writerow(['ID', 'Название', 'Остаток', 'Цена', 'Стоимость запасов', 'Категория'])
            for product in products:
                writer.writerow([
                    product[0], product[1], product[2], f"${product[3]:.2f}",
                    f"${product[4]:.2f}", product[5]
                ])
        
        elif report_type == 'movements':
            movements = self.db.execute_query('''
                SELECT 
                    im.created_at, p.name, im.movement_type,
                    im.quantity_change, im.reason, s.name
                FROM inventory_movements im
                JOIN products p ON im.product_id = p.id
                LEFT JOIN suppliers s ON im.supplier_id = s.id
                WHERE DATE(im.created_at) >= date('now', '-30 days')
                ORDER BY im.created_at DESC
            ''')
            
            writer.writerow(['Дата', 'Товар', 'Тип', 'Изменение', 'Причина', 'Поставщик'])
            for movement in movements:
                writer.writerow([
                    movement[0], movement[1], movement[2],
                    movement[3], movement[4], movement[5] or ''
                ])
        
        return output.getvalue()