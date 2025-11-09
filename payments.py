"""
Модуль для работы с платежными системами
"""
import logging

import json
import urllib.request
import urllib.parse

class PaymentProcessor:
    def __init__(self):
        self.providers = {
            'payme': PaymeProvider(),
            'click': ClickProvider(),
            'stripe': StripeProvider(),
            'paypal': PayPalProvider(),
            'zoodpay': ZoodPayProvider()
        }
    
    def create_payment(self, provider, amount, order_id, user_data):
        """Создание платежа через выбранного провайдера"""
        if provider not in self.providers:
            raise ValueError(f"Неподдерживаемый провайдер: {provider}")
        
        return self.providers[provider].create_payment(amount, order_id, user_data)
    
    def verify_payment(self, provider, payment_data):
        """Проверка статуса платежа"""
        if provider not in self.providers:
            return False
        
        return self.providers[provider].verify_payment(payment_data)

class PaymeProvider:
    def __init__(self):
        self.merchant_id = "PAYME_MERCHANT_ID"  # Заменить на реальный
        self.secret_key = "PAYME_SECRET_KEY"   # Заменить на реальный
        self.base_url = "https://checkout.paycom.uz"
    
    def create_payment(self, amount, order_id, user_data):
        """Создание платежа через Payme"""
        # Конвертируем в тийины (1 сум = 100 тийин)
        amount_tiyin = int(amount * 100 * 100)  # USD -> UZS -> tiyin
        
        params = {
            'm': self.merchant_id,
            'ac.order_id': str(order_id),
            'a': str(amount_tiyin),
            'c': f"https://t.me/your_bot?start=payment_{order_id}",
            'l': 'ru'  # Язык интерфейса
        }
        
        # Создаем URL для оплаты
        query_string = urllib.parse.urlencode(params)
        payment_url = f"{self.base_url}?{query_string}"
        
        return {
            'url': payment_url,
            'provider': 'payme',
            'amount': amount,
            'order_id': order_id
        }
    
    def verify_payment(self, payment_data):
        """Проверка платежа Payme через webhook"""
        # Здесь должна быть логика проверки подписи и статуса
        return payment_data.get('state') == 2  # 2 = успешно оплачено

class ClickProvider:
    def __init__(self):
        self.merchant_id = "CLICK_MERCHANT_ID"
        self.service_id = "CLICK_SERVICE_ID"
        self.secret_key = "CLICK_SECRET_KEY"
        self.base_url = "https://my.click.uz/services/pay"
    
    def create_payment(self, amount, order_id, user_data):
        """Создание платежа через Click"""
        # Конвертируем в сумы
        amount_uzs = int(amount * 12000)  # Примерный курс USD -> UZS
        
        params = {
            'service_id': self.service_id,
            'merchant_id': self.merchant_id,
            'amount': str(amount_uzs),
            'transaction_param': str(order_id),
            'return_url': f"https://t.me/your_bot?start=payment_{order_id}",
            'merchant_user_id': str(user_data.get('telegram_id', ''))
        }
        
        query_string = urllib.parse.urlencode(params)
        payment_url = f"{self.base_url}?{query_string}"
        
        return {
            'url': payment_url,
            'provider': 'click',
            'amount': amount,
            'order_id': order_id
        }
    
    def verify_payment(self, payment_data):
        """Проверка платежа Click"""
        return payment_data.get('error') == '0'

class StripeProvider:
    def __init__(self):
        self.secret_key = "STRIPE_SECRET_KEY"
        self.publishable_key = "STRIPE_PUBLISHABLE_KEY"
        self.base_url = "https://api.stripe.com/v1"
    
    def create_payment(self, amount, order_id, user_data):
        """Создание платежа через Stripe"""
        # Stripe работает в центах
        amount_cents = int(amount * 100)
        
        # Создаем Payment Intent через API
        data = {
            'amount': str(amount_cents),
            'currency': 'usd',
            'metadata[order_id]': str(order_id),
            'automatic_payment_methods[enabled]': 'true'
        }
        
        headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            data_encoded = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(
                f"{self.base_url}/payment_intents",
                data=data_encoded,
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                return {
                    'url': f"https://checkout.stripe.com/pay/{result['client_secret']}",
                    'provider': 'stripe',
                    'amount': amount,
                    'order_id': order_id,
                    'payment_intent_id': result['id']
                }
        except Exception as e:
            logging.info(f"Ошибка создания Stripe платежа: {e}")
            return None
    
    def verify_payment(self, payment_data):
        """Проверка платежа Stripe"""
        return payment_data.get('status') == 'succeeded'

class PayPalProvider:
    def __init__(self):
        self.client_id = "PAYPAL_CLIENT_ID"
        self.client_secret = "PAYPAL_CLIENT_SECRET"
        self.base_url = "https://api.paypal.com"  # Для продакшена
        # self.base_url = "https://api.sandbox.paypal.com"  # Для тестов
    
    def create_payment(self, amount, order_id, user_data):
        """Создание платежа через PayPal"""
        payment_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": str(order_id),
                "amount": {
                    "currency_code": "USD",
                    "value": f"{amount:.2f}"
                }
            }],
            "application_context": {
                "return_url": f"https://t.me/your_bot?start=payment_success_{order_id}",
                "cancel_url": f"https://t.me/your_bot?start=payment_cancel_{order_id}"
            }
        }
        
        # Здесь должна быть реальная интеграция с PayPal API
        return {
            'url': f"https://www.paypal.com/checkoutnow?token=EXAMPLE_TOKEN",
            'provider': 'paypal',
            'amount': amount,
            'order_id': order_id
        }
    
    def verify_payment(self, payment_data):
        """Проверка платежа PayPal"""
        return payment_data.get('status') == 'COMPLETED'

class ZoodPayProvider:
    def __init__(self):
        self.merchant_id = "ZOODPAY_MERCHANT_ID"
        self.secret_key = "ZOODPAY_SECRET_KEY"
        self.base_url = "https://api.zoodpay.com"
    
    def create_payment(self, amount, order_id, user_data):
        """Создание платежа через ZoodPay"""
        payment_data = {
            'merchant_reference': str(order_id),
            'amount': f"{amount:.2f}",
            'currency': 'USD',
            'customer': {
                'first_name': user_data.get('name', ''),
                'phone': user_data.get('phone', ''),
                'email': user_data.get('email', '')
            },
            'success_url': f"https://t.me/your_bot?start=payment_success_{order_id}",
            'error_url': f"https://t.me/your_bot?start=payment_error_{order_id}"
        }
        
        return {
            'url': f"https://checkout.zoodpay.com/pay?data={json.dumps(payment_data)}",
            'provider': 'zoodpay',
            'amount': amount,
            'order_id': order_id
        }
    
    def verify_payment(self, payment_data):
        """Проверка платежа ZoodPay"""
        return payment_data.get('status') == 'paid'

def create_payment_keyboard(order_id, amount):
    """Создание клавиатуры для выбора способа оплаты"""
    return {
        'inline_keyboard': [
            [
                {'text': '💳 Payme', 'callback_data': f'pay_payme_{order_id}_{amount}'},
                {'text': '🔵 Click', 'callback_data': f'pay_click_{order_id}_{amount}'}
            ],
            [
                {'text': '💎 Stripe', 'callback_data': f'pay_stripe_{order_id}_{amount}'},
                {'text': '🟡 PayPal', 'callback_data': f'pay_paypal_{order_id}_{amount}'}
            ],
            [
                {'text': '🦓 ZoodPay', 'callback_data': f'pay_zoodpay_{order_id}_{amount}'},
                {'text': '💵 Наличными', 'callback_data': f'pay_cash_{order_id}'}
            ],
            [
                {'text': '❌ Отмена', 'callback_data': 'cancel_payment'}
            ]
        ]
    }

def format_payment_info(payment_result):
    """Форматирование информации о платеже"""
    if not payment_result:
        return "❌ Ошибка создания платежа"
    
    provider_names = {
        'payme': 'Payme',
        'click': 'Click',
        'stripe': 'Stripe',
        'paypal': 'PayPal',
        'zoodpay': 'ZoodPay'
    }
    
    provider_name = provider_names.get(payment_result['provider'], payment_result['provider'])
    
    info = f"💳 <b>Оплата через {provider_name}</b>\n\n"
    info += f"💰 Сумма: ${payment_result['amount']:.2f}\n"
    info += f"📦 Заказ: #{payment_result['order_id']}\n\n"
    info += f"👆 <a href='{payment_result['url']}'>Перейти к оплате</a>"
    
    return info