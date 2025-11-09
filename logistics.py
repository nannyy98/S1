"""
Модуль логистики и доставки
"""

from datetime import datetime, timedelta

class LogisticsManager:
    def __init__(self, db):
        self.db = db
        self.delivery_providers = {
            'dhl': DHLProvider(),
            'fedex': FedExProvider(),
            'ups': UPSProvider(),
            'local_courier': LocalCourierProvider(),
            'post': PostProvider()
        }
    
    def get_delivery_options(self, address, total_weight=1.0):
        """Получение вариантов доставки"""
        options = []
        
        # Стандартная доставка
        options.append({
            'id': 'standard',
            'name': 'Стандартная доставка',
            'price': 5.00,
            'delivery_time': '3-5 рабочих дней',
            'description': 'Обычная доставка курьерской службой'
        })
        
        # Экспресс доставка
        options.append({
            'id': 'express',
            'name': 'Экспресс доставка',
            'price': 15.00,
            'delivery_time': '1-2 рабочих дня',
            'description': 'Быстрая доставка в приоритетном порядке'
        })
        
        # Доставка в день заказа
        options.append({
            'id': 'same_day',
            'name': 'Доставка в день заказа',
            'price': 25.00,
            'delivery_time': 'В течение дня',
            'description': 'Доставка в тот же день (до 18:00)'
        })
        
        # Самовывоз
        options.append({
            'id': 'pickup',
            'name': 'Самовывоз',
            'price': 0.00,
            'delivery_time': 'В любое время',
            'description': 'Забрать в пункте выдачи'
        })
        
        return options
    
    def get_delivery_time_slots(self, delivery_date):
        """Получение временных слотов для доставки"""
        slots = [
            {'id': 'morning', 'time': '09:00-12:00', 'name': 'Утром'},
            {'id': 'afternoon', 'time': '12:00-15:00', 'name': 'Днем'},
            {'id': 'evening', 'time': '15:00-18:00', 'name': 'Вечером'},
            {'id': 'night', 'time': '18:00-21:00', 'name': 'Поздно вечером'},
            {'id': 'anytime', 'time': '09:00-21:00', 'name': 'В любое время'}
        ]
        
        return slots
    
    def create_shipment(self, order_id, delivery_option, time_slot=None):
        """Создание отправления"""
        order_details = self.db.get_order_details(order_id)
        if not order_details:
            return None
        
        order = order_details['order']
        
        # Генерируем трек-номер
        tracking_number = self.generate_tracking_number(order_id)
        
        # Сохраняем информацию о доставке
        shipment_id = self.db.execute_query('''
            INSERT INTO shipments (
                order_id, tracking_number, delivery_provider, 
                delivery_option, time_slot, status, estimated_delivery
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_id,
            tracking_number,
            delivery_option.get('provider', 'local'),
            delivery_option['id'],
            time_slot,
            'created',
            self.calculate_estimated_delivery(delivery_option)
        ))
        
        # Обновляем статус заказа
        self.db.update_order_status(order_id, 'shipped')
        
        return {
            'shipment_id': shipment_id,
            'tracking_number': tracking_number,
            'estimated_delivery': self.calculate_estimated_delivery(delivery_option)
        }
    
    def generate_tracking_number(self, order_id):
        """Генерация трек-номера"""
        import random
        import string
        
        prefix = "SB"  # Shop Bot
        order_part = f"{order_id:06d}"
        random_part = ''.join(random.choices(string.digits, k=4))
        
        return f"{prefix}{order_part}{random_part}"
    
    def calculate_estimated_delivery(self, delivery_option):
        """Расчет предполагаемой даты доставки"""
        now = datetime.now()
        
        delivery_days = {
            'same_day': 0,
            'express': 2,
            'standard': 4,
            'pickup': 1
        }
        
        days = delivery_days.get(delivery_option['id'], 3)
        estimated_date = now + timedelta(days=days)
        
        return estimated_date.strftime('%Y-%m-%d %H:%M:%S')
    
    def track_shipment(self, tracking_number):
        """Отслеживание посылки"""
        shipment = self.db.execute_query(
            'SELECT * FROM shipments WHERE tracking_number = ?',
            (tracking_number,)
        )
        
        if not shipment:
            return None
        
        shipment_data = shipment[0]
        
        # Симуляция статусов доставки
        status_history = [
            {
                'status': 'created',
                'description': 'Заказ создан',
                'timestamp': shipment_data[7],  # created_at
                'location': 'Склад'
            },
            {
                'status': 'picked_up',
                'description': 'Заказ забран курьером',
                'timestamp': self.add_hours_to_date(shipment_data[7], 2),
                'location': 'Сортировочный центр'
            },
            {
                'status': 'in_transit',
                'description': 'В пути',
                'timestamp': self.add_hours_to_date(shipment_data[7], 24),
                'location': 'Транспортный узел'
            }
        ]
        
        # Добавляем доставку если время пришло
        estimated_delivery = datetime.strptime(shipment_data[6], '%Y-%m-%d %H:%M:%S')
        if datetime.now() >= estimated_delivery:
            status_history.append({
                'status': 'delivered',
                'description': 'Доставлено',
                'timestamp': shipment_data[6],
                'location': 'Адрес получателя'
            })
        
        return {
            'tracking_number': tracking_number,
            'current_status': shipment_data[5],
            'estimated_delivery': shipment_data[6],
            'history': status_history
        }
    
    def add_hours_to_date(self, date_string, hours):
        """Добавление часов к дате"""
        date_obj = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
        new_date = date_obj + timedelta(hours=hours)
        return new_date.strftime('%Y-%m-%d %H:%M:%S')
    
    def get_pickup_points(self, city='Ташкент'):
        """Получение пунктов самовывоза"""
        pickup_points = [
            {
                'id': 1,
                'name': 'ТРЦ Mega Planet',
                'address': 'ул. Катартал, 60А',
                'working_hours': '10:00-22:00',
                'phone': '+998 71 123-45-67'
            },
            {
                'id': 2,
                'name': 'Офис на Амире Темуре',
                'address': 'пр. Амира Темура, 15',
                'working_hours': '09:00-18:00',
                'phone': '+998 71 234-56-78'
            },
            {
                'id': 3,
                'name': 'Пункт в Чиланзаре',
                'address': 'Чиланзар, 12 квартал',
                'working_hours': '08:00-20:00',
                'phone': '+998 71 345-67-89'
            }
        ]
        
        return pickup_points
    
    def schedule_delivery(self, order_id, delivery_date, time_slot):
        """Планирование доставки"""
        return self.db.execute_query('''
            UPDATE shipments 
            SET scheduled_date = ?, time_slot = ?, status = 'scheduled'
            WHERE order_id = ?
        ''', (delivery_date, time_slot, order_id))
    
    def notify_delivery_update(self, tracking_number, new_status):
        """Уведомление об обновлении доставки"""
        shipment = self.db.execute_query('''
            SELECT s.order_id, u.telegram_id, u.name, u.language
            FROM shipments s
            JOIN orders o ON s.order_id = o.id
            JOIN users u ON o.user_id = u.id
            WHERE s.tracking_number = ?
        ''', (tracking_number,))
        
        if shipment:
            order_id, telegram_id, user_name, language = shipment[0]
            
            from localization import t
            
            status_messages = {
                'picked_up': 'delivery_picked_up',
                'in_transit': 'delivery_in_transit',
                'out_for_delivery': 'delivery_out_for_delivery',
                'delivered': 'delivery_delivered'
            }
            
            message_key = status_messages.get(new_status, 'delivery_update')
            
            notification_text = f"🚚 <b>{t('delivery_update', language=language)}</b>\n\n"
            notification_text += f"📦 {t('order', language=language)} #{order_id}\n"
            notification_text += f"📍 {t('tracking_number', language=language)}: {tracking_number}\n\n"
            notification_text += f"📋 {t(message_key, language=language)}"
            
            # Отправляем через NotificationManager
            if hasattr(self, 'notification_manager'):
                self.notification_manager.send_instant_push(
                    shipment[0][0],  # user_id из orders
                    'push_delivery_update',
                    notification_text,
                    'delivery'
                )

class DHLProvider:
    def __init__(self):
        self.api_key = "DHL_API_KEY"
        self.base_url = "https://api.dhl.com"
    
    def create_shipment(self, order_data):
        """Создание отправления через DHL"""
        # Здесь должна быть реальная интеграция с DHL API
        return {
            'tracking_number': f"DHL{order_data['order_id']:08d}",
            'estimated_delivery': '2024-01-15',
            'cost': 25.00
        }

class FedExProvider:
    def __init__(self):
        self.api_key = "FEDEX_API_KEY"
        self.base_url = "https://api.fedex.com"
    
    def create_shipment(self, order_data):
        """Создание отправления через FedEx"""
        return {
            'tracking_number': f"FX{order_data['order_id']:08d}",
            'estimated_delivery': '2024-01-16',
            'cost': 30.00
        }

class UPSProvider:
    def __init__(self):
        self.api_key = "UPS_API_KEY"
        self.base_url = "https://api.ups.com"
    
    def create_shipment(self, order_data):
        """Создание отправления через UPS"""
        return {
            'tracking_number': f"UPS{order_data['order_id']:08d}",
            'estimated_delivery': '2024-01-17',
            'cost': 28.00
        }

class LocalCourierProvider:
    def __init__(self):
        self.name = "Местная курьерская служба"
    
    def create_shipment(self, order_data):
        """Создание отправления через местного курьера"""
        return {
            'tracking_number': f"LC{order_data['order_id']:08d}",
            'estimated_delivery': '2024-01-14',
            'cost': 8.00
        }

class PostProvider:
    def __init__(self):
        self.name = "Почта Узбекистана"
    
    def create_shipment(self, order_data):
        """Создание отправления через почту"""
        return {
            'tracking_number': f"UZ{order_data['order_id']:08d}",
            'estimated_delivery': '2024-01-20',
            'cost': 3.00
        }