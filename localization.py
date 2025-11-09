"""
Модуль локализации для поддержки русского и узбекского языков
"""

class Localization:
    def __init__(self):
        self.translations = {
            'ru': {
                # Основные сообщения
                'welcome_new': """
🛍 <b>Добро пожаловать в наш интернет-магазин!</b>

Здесь вы можете:
• 📱 Просматривать каталог товаров
• 🛒 Добавлять товары в корзину  
• 📦 Оформлять заказы
• 📋 Отслеживать статус доставки

Для начала работы пройдите быструю регистрацию.
                """,
                
                'welcome_back': """
👋 <b>С возвращением!</b>

Рады видеть вас снова в нашем магазине.
Выберите действие из меню ниже:
                """,
                
                # Кнопки меню
                'btn_catalog': '🛍 Каталог',
                'btn_cart': '🛒 Корзина',
                'btn_orders': '📋 Мои заказы',
                'btn_profile': '👤 Профиль',
                'btn_search': '🔍 Поиск',
                'btn_help': 'ℹ️ Помощь',

                # Помощь
                'help': """
ℹ️ <b>Помощь по использованию бота</b>

<b>🛍 Каталог</b>
Просмотр всех доступных товаров по категориям.

<b>🛒 Корзина</b>
Просмотр и управление выбранными товарами.

<b>📋 Мои заказы</b>
Просмотр истории заказов и их статусов.

<b>👤 Профиль</b>
Управление личными данными и настройками.

<b>🔍 Поиск</b>
Быстрый поиск товаров по названию.

<b>📞 Контакты</b>
По всем вопросам обращайтесь к администратору.
                """,
                'btn_back': '🔙 Назад',
                'btn_main': '🏠 Главная',
                'btn_cancel': '❌ Отмена',
                'btn_yes': '✅ Да',
                'btn_no': '❌ Нет',
                
                # Статусы заказов
                'status_pending': '⏳ В обработке',
                'status_confirmed': '✅ Подтвержден',
                'status_shipped': '🚚 Отправлен',
                'status_delivered': '📦 Доставлен',
                'status_cancelled': '❌ Отменен',
                
                # Уведомления
                'order_status_update': 'Обновление заказа',
                'payment_success_title': 'Оплата прошла успешно!',
                'payment_confirmed': 'Платеж подтвержден',
                'loyalty_points_earned': 'Начислено баллов',
                'contact_soon': 'Мы свяжемся с вами в ближайшее время',
                
                # Регистрация
                'registration_complete': """
✅ <b>Регистрация завершена!</b>

Добро пожаловать в наш магазин! 🎉

Теперь вы можете:
• Просматривать каталог товаров
• Добавлять товары в корзину
• Оформлять заказы

Приятных покупок! 🛍
                """,
                
                # Корзина
                'empty_cart': """
🛒 <b>Ваша корзина пуста</b>

Перейдите в каталог, чтобы добавить товары!
                """,

                # Дополнительные переводы
                'language_changed': '✅ Язык успешно изменен!'
            },
            
            'uz': {
                # Основные сообщения
                'welcome_new': """
🛍 <b>Internet-do'konimizga xush kelibsiz!</b>

Bu yerda siz:
• 📱 Mahsulotlar katalogini ko'rishingiz
• 🛒 Mahsulotlarni savatchaga qo'shishingiz  
• 📦 Buyurtma berishingiz
• 📋 Yetkazib berish holatini kuzatishingiz mumkin

Ishni boshlash uchun tezkor ro'yxatdan o'ting.
                """,
                
                'welcome_back': """
👋 <b>Qaytganingiz bilan!</b>

Sizni do'konimizda yana ko'rishdan xursandmiz.
Quyidagi menyudan amalni tanlang:
                """,
                
                # Кнопки меню
                'btn_catalog': '🛍 Katalog',
                'btn_cart': '🛒 Savat',
                'btn_orders': '📋 Mening buyurtmalarim',
                'btn_profile': '👤 Profil',
                'btn_search': '🔍 Qidiruv',
                'btn_help': 'ℹ️ Yordam',

                # Помощь
                'help': """
ℹ️ <b>Botdan foydalanish bo'yicha yordam</b>

<b>🛍 Katalog</b>
Barcha mavjud mahsulotlarni toifalar bo'yicha ko'rish.

<b>🛒 Savat</b>
Tanlangan mahsulotlarni ko'rish va boshqarish.

<b>📋 Mening buyurtmalarim</b>
Buyurtmalar tarixi va ularning holatini ko'rish.

<b>👤 Profil</b>
Shaxsiy ma'lumotlar va sozlamalarni boshqarish.

<b>🔍 Qidiruv</b>
Mahsulotlarni nom bo'yicha tez qidirish.

<b>📞 Kontaktlar</b>
Barcha savollar bo'yicha administratorga murojaat qiling.
                """,
                'btn_back': '🔙 Orqaga',
                'btn_main': '🏠 Bosh sahifa',
                'btn_cancel': '❌ Bekor qilish',
                'btn_yes': '✅ Ha',
                'btn_no': '❌ Yo\'q',
                
                # Статусы заказов
                'status_pending': '⏳ Qayta ishlanmoqda',
                'status_confirmed': '✅ Tasdiqlangan',
                'status_shipped': '🚚 Jo\'natilgan',
                'status_delivered': '📦 Yetkazilgan',
                'status_cancelled': '❌ Bekor qilingan',
                
                # Уведомления
                'order_status_update': 'Buyurtma yangilanishi',
                'payment_success_title': 'To\'lov muvaffaqiyatli o\'tdi!',
                'payment_confirmed': 'To\'lov tasdiqlandi',
                'loyalty_points_earned': 'Ball qo\'shildi',
                'contact_soon': 'Tez orada siz bilan bog\'lanamiz',
                
                # Регистрация
                'registration_complete': """
✅ <b>Ro'yxatdan o'tish yakunlandi!</b>

Do'konimizga xush kelibsiz! 🎉

Endi siz:
• Mahsulotlar katalogini ko'rishingiz
• Mahsulotlarni savatchaga qo'shishingiz
• Buyurtma berishingiz mumkin

Xaridlaringiz baxtiyor bo'lsin! 🛍
                """,
                
                # Корзина
                'empty_cart': """
🛒 <b>Savatingiz bo'sh</b>

Mahsulot qo'shish uchun katalogga o'ting!
                """,

                # Дополнительные переводы
                'language_changed': '✅ Til muvaffaqiyatli o\'zgartirildi!'
            }
        }
    
    def get_text(self, key, language='ru'):
        """Получение переведенного текста"""
        return self.translations.get(language, self.translations['ru']).get(key, key)

# Глобальный экземпляр локализации
localization = Localization()

def get_user_language(db, telegram_id):
    """Получение языка пользователя"""
    try:
        user_data = db.get_user_by_telegram_id(telegram_id)
        if user_data:
            return user_data[0][5]  # language поле
    except Exception:
        pass
    return 'ru'  # По умолчанию русский

def t(key, telegram_id=None, db=None, language=None):
    """Быстрая функция для получения переведенного текста"""
    if language is None and telegram_id and db:
        language = get_user_language(db, telegram_id)
    elif language is None:
        language = 'ru'
    
    return localization.get_text(key, language)