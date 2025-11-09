"""
Модуль webhook'ов для интеграции с платежными системами
"""
import logging

import json
from datetime import datetime

class WebhookManager:
    def __init__(self, bot, db, security_manager):
        self.bot = bot
        self.db = db
        self.security = security_manager
        
        # Секретные ключи для проверки подписей
        self.webhook_secrets = {
            'payme': 'PAYME_WEBHOOK_SECRET',
            'click': 'CLICK_WEBHOOK_SECRET',
            'stripe': 'STRIPE_WEBHOOK_SECRET',
            'paypal': 'PAYPAL_WEBHOOK_SECRET',
            'zoodpay': 'ZOODPAY_WEBHOOK_SECRET'
        }
    
    def handle_payment_webhook(self, provider, payload, signature=None):
        """Обработка webhook'а от платежной системы"""
        try:
            # Проверяем подпись
            if signature and not self.verify_webhook_signature(provider, payload, signature):
                self.log_webhook_error(provider, "Invalid signature", payload[:100])
                return {'status': 'error', 'message': 'Invalid signature'}
            
            # Парсим данные
            if provider == 'stripe':
                return self.handle_stripe_webhook(payload)
            elif provider == 'paypal':
                return self.handle_paypal_webhook(payload)
            else:
                return {'status': 'error', 'message': 'Unknown provider'}
                
        except Exception as e:
            self.log_webhook_error(provider, str(e), payload[:100])
            return {'status': 'error', 'message': 'Processing error'}
    
    def handle_stripe_webhook(self, payload):
        """Обработка Stripe webhook"""
        try:
            data = json.loads(payload)
            
            if data['type'] == 'payment_intent.succeeded':
                payment_intent = data['data']['object']
                order_id = payment_intent['metadata'].get('order_id')
                
                if order_id:
                    self.confirm_payment(order_id, 'stripe')
                    return {'status': 'success'}
            
            return {'status': 'success'}
        except Exception as e:
            logging.info(f"Ошибка обработки Stripe webhook: {e}")
            return {'status': 'error'}
    
    def handle_paypal_webhook(self, payload):
        """Обработка PayPal webhook"""
        try:
            data = json.loads(payload)
            
            if data.get('event_type') == 'PAYMENT.CAPTURE.COMPLETED':
                purchase_units = data['resource']['purchase_units']
                if purchase_units:
                    order_id = purchase_units[0]['reference_id']
                    self.confirm_payment(order_id, 'paypal')
            
            return {'status': 'success'}
        except Exception as e:
            logging.info(f"Ошибка обработки PayPal webhook: {e}")
            return {'status': 'error'}
    
    def confirm_payment(self, order_id, provider):
        """Подтверждение успешной оплаты"""
        try:
            # Обновляем статус заказа
            self.db.execute_query(
                'UPDATE orders SET payment_status = "paid", status = "confirmed" WHERE id = ?',
                (order_id,)
            )
            
            # Получаем данные заказа
            order = self.db.execute_query(
                'SELECT user_id FROM orders WHERE id = ?',
                (order_id,)
            )
            
            if order:
                user_id = order[0][0]
                
                # Очищаем корзину
                self.db.clear_cart(user_id)
                
                # Уведомляем клиента
                user = self.db.execute_query(
                    'SELECT telegram_id, name FROM users WHERE id = ?',
                    (user_id,)
                )
                
                if user:
                    success_text = f"✅ <b>Оплата прошла успешно!</b>\n\n"
                    success_text += f"💳 Платеж подтвержден\n"
                    success_text += f"📦 Заказ #{order_id}\n\n"
                    success_text += f"📞 Мы свяжемся с вами в ближайшее время"
                    
                    self.bot.send_message(user[0][0], success_text)
            
            self.log_webhook_success(provider, order_id, user_id if order else None)
            
        except Exception as e:
            logging.info(f"Ошибка подтверждения платежа: {e}")
    
    def verify_webhook_signature(self, provider, payload, signature):
        """Проверка подписи webhook'а"""
        secret = self.webhook_secrets.get(provider)
        if not secret:
            return False
        
        return self.security.verify_webhook_signature(payload, signature, secret)
    
    def log_webhook_success(self, provider, order_id, user_id):
        """Логирование успешного webhook'а"""
        try:
            self.db.execute_query('''
                INSERT INTO webhook_logs (provider, order_id, user_id, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                provider,
                order_id,
                user_id,
                'success',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        except Exception as e:
            logging.info(f"Ошибка записи лога webhook: {e}")
    
    def log_webhook_error(self, provider, error_message, payload_preview):
        """Логирование ошибки webhook'а"""
        try:
            self.db.execute_query('''
                INSERT INTO webhook_logs (provider, status, error_message, payload_preview, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                provider,
                'error',
                error_message,
                payload_preview,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        except Exception as e:
            logging.info(f"Ошибка записи лога ошибки webhook: {e}")