
# === Telegram bot: переход на ПОДКАТЕГОРИИ (бренды убраны) ===
# Вставьте функции ниже в ваш handlers.py (или аналог) и подключите вызовы в обработчиках.
# Требуется объект `db` с методами execute_query(...) и ваш send/render API бота.

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def _kb_subcategories(category_id):
    rows = db.execute_query("""
        SELECT id, name
        FROM subcategories
        WHERE category_id = ? AND (is_active = 1 OR is_active IS NULL)
        ORDER BY name
    """, (category_id,)) or []
    if not rows:
        return None
    kb = [[InlineKeyboardButton(name, callback_data=f"subcat_{sid}")] for (sid, name) in rows]
    kb.append([InlineKeyboardButton("⬅ Назад", callback_data="back_categories")])
    return InlineKeyboardMarkup(kb)

def _render_products_list(bot, chat_id, products):
    if not products:
        bot.send_message(chat_id, "Товары не найдены 🤷")
        return
    lines = [f"• {name} — {price:g}" for (_id, name, price) in products]
    bot.send_message(chat_id, "Доступные товары:\n" + "\n".join(lines))

def _show_products_by_category(bot, chat_id, category_id):
    products = db.execute_query("""
        SELECT id, name, price
        FROM products
        WHERE category_id = ? AND is_active = 1 AND (stock IS NULL OR stock > 0)
        ORDER BY name
    """, (category_id,)) or []
    _render_products_list(bot, chat_id, products)

def _show_products_by_subcategory(bot, chat_id, subcategory_id):
    products = db.execute_query("""
        SELECT id, name, price
        FROM products
        WHERE subcategory_id = ? AND is_active = 1 AND (stock IS NULL OR stock > 0)
        ORDER BY name
    """, (subcategory_id,)) or []
    _render_products_list(bot, chat_id, products)

def handle_category_selection(bot, chat_id, category_id):
    kb = _kb_subcategories(category_id)
    if kb:
        bot.send_message(chat_id, "Выберите подкатегорию:", reply_markup=kb)
        return
    _show_products_by_category(bot, chat_id, category_id)

# В общем обработчике callback_query добавьте:
# if data.startswith("cat_"):
#     handle_category_selection(bot, chat_id, int(data.split("_",1)[1]))
#     return
# if data.startswith("subcat_"):
#     _show_products_by_subcategory(bot, chat_id, int(data.split("_",1)[1]))
#     return
