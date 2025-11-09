"""
Модуль финансовой отчетности
"""

from datetime import datetime, timedelta
from utils import format_price

class FinancialReportsManager:
    def __init__(self, db):
        self.db = db
        self.tax_rate = 0.12  # НДС 12% для Узбекистана
        self.currency_rates = {
            'USD': 1.0,
            'UZS': 12000.0,  # Примерный курс
            'EUR': 0.85,
            'RUB': 75.0
        }
    
    def generate_profit_loss_report(self, start_date, end_date):
        """Отчет о прибылях и убытках"""
        # Доходы
        revenue_data = self.db.execute_query('''
            SELECT 
                SUM(total_amount) as gross_revenue,
                SUM(promo_discount) as total_discounts,
                COUNT(*) as orders_count,
                SUM(delivery_cost) as delivery_revenue
            FROM orders 
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status IN ('confirmed', 'shipped', 'delivered')
        ''', (start_date, end_date))
        
        # Себестоимость товаров
        cogs_data = self.db.execute_query('''
            SELECT SUM(oi.quantity * p.cost_price) as total_cogs
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE DATE(o.created_at) BETWEEN ? AND ?
            AND o.status IN ('confirmed', 'shipped', 'delivered')
        ''', (start_date, end_date))
        
        # Операционные расходы
        expenses_data = self.db.execute_query('''
            SELECT 
                expense_type,
                SUM(amount) as total_amount
            FROM business_expenses
            WHERE DATE(expense_date) BETWEEN ? AND ?
            GROUP BY expense_type
        ''', (start_date, end_date))
        
        # Расчеты
        gross_revenue = revenue_data[0][0] or 0
        total_discounts = revenue_data[0][1] or 0
        delivery_revenue = revenue_data[0][3] or 0
        net_revenue = gross_revenue - total_discounts
        
        total_cogs = cogs_data[0][0] or 0
        gross_profit = net_revenue - total_cogs
        gross_margin = (gross_profit / net_revenue * 100) if net_revenue > 0 else 0
        
        # Операционные расходы
        operating_expenses = sum(expense[1] for expense in expenses_data)
        operating_profit = gross_profit - operating_expenses
        
        # Налоги
        tax_amount = operating_profit * self.tax_rate if operating_profit > 0 else 0
        net_profit = operating_profit - tax_amount
        
        return {
            'period': f"{start_date} - {end_date}",
            'gross_revenue': gross_revenue,
            'discounts': total_discounts,
            'net_revenue': net_revenue,
            'cogs': total_cogs,
            'gross_profit': gross_profit,
            'gross_margin': gross_margin,
            'operating_expenses': operating_expenses,
            'operating_profit': operating_profit,
            'tax_amount': tax_amount,
            'net_profit': net_profit,
            'orders_count': revenue_data[0][2],
            'expenses_breakdown': expenses_data
        }
    
    def generate_cash_flow_report(self, start_date, end_date):
        """Отчет о движении денежных средств"""
        # Поступления
        cash_inflows = self.db.execute_query('''
            SELECT 
                DATE(created_at) as date,
                SUM(total_amount - COALESCE(promo_discount, 0)) as daily_revenue
            FROM orders
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND payment_status = 'paid'
            GROUP BY DATE(created_at)
            ORDER BY date
        ''', (start_date, end_date))
        
        # Расходы
        cash_outflows = self.db.execute_query('''
            SELECT 
                DATE(expense_date) as date,
                SUM(amount) as daily_expenses
            FROM business_expenses
            WHERE DATE(expense_date) BETWEEN ? AND ?
            GROUP BY DATE(expense_date)
            ORDER BY date
        ''', (start_date, end_date))
        
        # Закупки товаров
        inventory_purchases = self.db.execute_query('''
            SELECT 
                DATE(created_at) as date,
                SUM(total_amount) as daily_purchases
            FROM purchase_orders
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status = 'paid'
            GROUP BY DATE(created_at)
            ORDER BY date
        ''', (start_date, end_date))
        
        # Объединяем данные по дням
        daily_cash_flow = {}
        
        for inflow in cash_inflows:
            date = inflow[0]
            daily_cash_flow[date] = daily_cash_flow.get(date, {'inflow': 0, 'outflow': 0})
            daily_cash_flow[date]['inflow'] += inflow[1]
        
        for outflow in cash_outflows:
            date = outflow[0]
            daily_cash_flow[date] = daily_cash_flow.get(date, {'inflow': 0, 'outflow': 0})
            daily_cash_flow[date]['outflow'] += outflow[1]
        
        for purchase in inventory_purchases:
            date = purchase[0]
            daily_cash_flow[date] = daily_cash_flow.get(date, {'inflow': 0, 'outflow': 0})
            daily_cash_flow[date]['outflow'] += purchase[1]
        
        # Рассчитываем накопительный баланс
        cumulative_balance = 0
        cash_flow_data = []
        
        for date in sorted(daily_cash_flow.keys()):
            daily_data = daily_cash_flow[date]
            net_flow = daily_data['inflow'] - daily_data['outflow']
            cumulative_balance += net_flow
            
            cash_flow_data.append({
                'date': date,
                'inflow': daily_data['inflow'],
                'outflow': daily_data['outflow'],
                'net_flow': net_flow,
                'cumulative_balance': cumulative_balance
            })
        
        return {
            'period': f"{start_date} - {end_date}",
            'daily_data': cash_flow_data,
            'total_inflow': sum(d['inflow'] for d in cash_flow_data),
            'total_outflow': sum(d['outflow'] for d in cash_flow_data),
            'net_cash_flow': sum(d['net_flow'] for d in cash_flow_data)
        }
    
    def generate_tax_report(self, start_date, end_date):
        """Налоговый отчет"""
        # Налогооблагаемые доходы
        taxable_income = self.db.execute_query('''
            SELECT 
                SUM(total_amount - COALESCE(promo_discount, 0)) as net_revenue,
                SUM(total_amount - COALESCE(promo_discount, 0)) * ? as vat_amount
            FROM orders
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status IN ('confirmed', 'shipped', 'delivered')
        ''', (self.tax_rate, start_date, end_date))
        
        # Расходы, уменьшающие налогооблагаемую базу
        deductible_expenses = self.db.execute_query('''
            SELECT 
                expense_type,
                SUM(amount) as total_amount
            FROM business_expenses
            WHERE DATE(expense_date) BETWEEN ? AND ?
            AND is_tax_deductible = 1
            GROUP BY expense_type
        ''', (start_date, end_date))
        
        net_revenue = taxable_income[0][0] or 0
        vat_amount = taxable_income[0][1] or 0
        total_deductions = sum(expense[1] for expense in deductible_expenses)
        
        taxable_base = max(0, net_revenue - total_deductions)
        income_tax = taxable_base * 0.12  # Подоходный налог 12%
        
        return {
            'period': f"{start_date} - {end_date}",
            'gross_revenue': net_revenue,
            'deductible_expenses': total_deductions,
            'taxable_base': taxable_base,
            'vat_amount': vat_amount,
            'income_tax': income_tax,
            'total_tax_liability': vat_amount + income_tax,
            'expenses_breakdown': deductible_expenses
        }
    
    def generate_roi_analysis(self):
        """Анализ рентабельности инвестиций"""
        # ROI по каналам привлечения
        channel_roi = self.db.execute_query('''
            SELECT 
                acquisition_channel,
                COUNT(DISTINCT u.id) as users_acquired,
                SUM(o.total_amount) as revenue_generated,
                AVG(o.total_amount) as avg_order_value
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'cancelled'
            WHERE u.acquisition_channel IS NOT NULL
            GROUP BY acquisition_channel
        ''')
        
        # ROI по товарам
        product_roi = self.db.execute_query('''
            SELECT 
                p.name,
                SUM(oi.quantity * oi.price) as revenue,
                SUM(oi.quantity * p.cost_price) as cost,
                SUM(oi.quantity * oi.price) - SUM(oi.quantity * p.cost_price) as profit,
                (SUM(oi.quantity * oi.price) - SUM(oi.quantity * p.cost_price)) / 
                NULLIF(SUM(oi.quantity * p.cost_price), 0) * 100 as roi_percentage
            FROM products p
            JOIN order_items oi ON p.id = oi.product_id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status != 'cancelled'
            GROUP BY p.id, p.name
            ORDER BY roi_percentage DESC
            LIMIT 20
        ''')
        
        # ROI по категориям
        category_roi = self.db.execute_query('''
            SELECT 
                c.name,
                c.emoji,
                SUM(oi.quantity * oi.price) as revenue,
                SUM(oi.quantity * p.cost_price) as cost,
                (SUM(oi.quantity * oi.price) - SUM(oi.quantity * p.cost_price)) / 
                NULLIF(SUM(oi.quantity * p.cost_price), 0) * 100 as roi_percentage
            FROM categories c
            JOIN products p ON c.id = p.category_id
            JOIN order_items oi ON p.id = oi.product_id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status != 'cancelled'
            GROUP BY c.id, c.name, c.emoji
            ORDER BY roi_percentage DESC
        ''')
        
        return {
            'channel_roi': channel_roi,
            'product_roi': product_roi,
            'category_roi': category_roi
        }
    
    def format_financial_report(self, report_type, data):
        """Форматирование финансового отчета"""
        if report_type == 'profit_loss':
            text = f"💰 <b>Отчет о прибылях и убытках</b>\n"
            text += f"📅 Период: {data['period']}\n\n"
            
            text += f"📈 <b>ДОХОДЫ:</b>\n"
            text += f"💵 Валовая выручка: {format_price(data['gross_revenue'])}\n"
            text += f"🎁 Скидки: -{format_price(data['discounts'])}\n"
            text += f"💰 Чистая выручка: {format_price(data['net_revenue'])}\n\n"
            
            text += f"📉 <b>РАСХОДЫ:</b>\n"
            text += f"📦 Себестоимость: {format_price(data['cogs'])}\n"
            text += f"⚙️ Операционные: {format_price(data['operating_expenses'])}\n"
            text += f"🏛 Налоги: {format_price(data['tax_amount'])}\n\n"
            
            text += f"📊 <b>ПРИБЫЛЬ:</b>\n"
            text += f"💎 Валовая: {format_price(data['gross_profit'])} ({data['gross_margin']:.1f}%)\n"
            text += f"⚙️ Операционная: {format_price(data['operating_profit'])}\n"
            text += f"✅ Чистая: {format_price(data['net_profit'])}\n\n"
            
            text += f"📋 <b>ПОКАЗАТЕЛИ:</b>\n"
            text += f"📦 Заказов: {data['orders_count']}\n"
            text += f"💳 Средний чек: {format_price(data['net_revenue'] / data['orders_count'] if data['orders_count'] > 0 else 0)}"
            
            return text
        
        elif report_type == 'cash_flow':
            text = f"💸 <b>Отчет о движении денежных средств</b>\n"
            text += f"📅 Период: {data['period']}\n\n"
            
            text += f"📈 <b>ИТОГИ:</b>\n"
            text += f"💰 Поступления: {format_price(data['total_inflow'])}\n"
            text += f"💸 Расходы: {format_price(data['total_outflow'])}\n"
            text += f"📊 Чистый поток: {format_price(data['net_cash_flow'])}\n\n"
            
            if data['daily_data']:
                text += f"📅 <b>ПОСЛЕДНИЕ ДНИ:</b>\n"
                for day_data in data['daily_data'][-7:]:
                    net_flow = day_data['net_flow']
                    flow_emoji = "📈" if net_flow > 0 else "📉" if net_flow < 0 else "➖"
                    text += f"{flow_emoji} {day_data['date']}: {format_price(net_flow)}\n"
            
            return text
        
        elif report_type == 'tax':
            text = f"🏛 <b>Налоговый отчет</b>\n"
            text += f"📅 Период: {data['period']}\n\n"
            
            text += f"💰 <b>ДОХОДЫ:</b>\n"
            text += f"📊 Валовая выручка: {format_price(data['gross_revenue'])}\n"
            text += f"📉 Вычеты: {format_price(data['deductible_expenses'])}\n"
            text += f"🎯 Налогооблагаемая база: {format_price(data['taxable_base'])}\n\n"
            
            text += f"🏛 <b>НАЛОГИ:</b>\n"
            text += f"📊 НДС (12%): {format_price(data['vat_amount'])}\n"
            text += f"💼 Подоходный (12%): {format_price(data['income_tax'])}\n"
            text += f"💰 Всего к доплате: {format_price(data['total_tax_liability'])}\n\n"
            
            if data['expenses_breakdown']:
                text += f"📋 <b>ВЫЧИТАЕМЫЕ РАСХОДЫ:</b>\n"
                for expense in data['expenses_breakdown']:
                    text += f"• {expense[0]}: {format_price(expense[1])}\n"
            
            return text
        
        return "❌ Неизвестный тип отчета"
    
    def export_financial_data_csv(self, report_type, start_date, end_date):
        """Экспорт финансовых данных в CSV"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if report_type == 'transactions':
            # Экспорт всех транзакций
            transactions = self.db.execute_query('''
                SELECT 
                    o.id,
                    o.created_at,
                    u.name,
                    o.total_amount,
                    o.promo_discount,
                    o.payment_method,
                    o.status
                FROM orders o
                JOIN users u ON o.user_id = u.id
                WHERE DATE(o.created_at) BETWEEN ? AND ?
                ORDER BY o.created_at DESC
            ''', (start_date, end_date))
            
            writer.writerow(['Order ID', 'Date', 'Customer', 'Amount', 'Discount', 'Payment Method', 'Status'])
            for transaction in transactions:
                writer.writerow([
                    transaction[0], transaction[1], transaction[2],
                    f"${transaction[3]:.2f}", f"${transaction[4] or 0:.2f}",
                    transaction[5], transaction[6]
                ])
        
        elif report_type == 'products_performance':
            # Экспорт эффективности товаров
            products = self.db.execute_query('''
                SELECT 
                    p.name,
                    SUM(oi.quantity) as units_sold,
                    SUM(oi.quantity * oi.price) as revenue,
                    SUM(oi.quantity * p.cost_price) as cost,
                    SUM(oi.quantity * oi.price) - SUM(oi.quantity * p.cost_price) as profit,
                    p.stock,
                    p.views
                FROM products p
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id 
                    AND DATE(o.created_at) BETWEEN ? AND ?
                    AND o.status != 'cancelled'
                GROUP BY p.id, p.name, p.stock, p.views
                ORDER BY profit DESC
            ''', (start_date, end_date))
            
            writer.writerow(['Product', 'Units Sold', 'Revenue', 'Cost', 'Profit', 'Stock', 'Views'])
            for product in products:
                writer.writerow([
                    product[0], product[1] or 0, f"${product[2] or 0:.2f}",
                    f"${product[3] or 0:.2f}", f"${product[4] or 0:.2f}",
                    product[5], product[6]
                ])
        
        return output.getvalue()
    
    def calculate_business_metrics(self):
        """Расчет ключевых бизнес-метрик"""
        # Метрики за последние 30 дней
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Customer Acquisition Cost (CAC)
        marketing_spend = self.db.execute_query('''
            SELECT SUM(amount) FROM business_expenses
            WHERE expense_type = 'marketing'
            AND DATE(expense_date) >= ?
        ''', (start_date.strftime('%Y-%m-%d'),))[0][0] or 0
        
        new_customers = self.db.execute_query('''
            SELECT COUNT(*) FROM users
            WHERE DATE(created_at) >= ?
            AND is_admin = 0
        ''', (start_date.strftime('%Y-%m-%d'),))[0][0]
        
        cac = marketing_spend / new_customers if new_customers > 0 else 0
        
        # Customer Lifetime Value (CLV)
        clv_data = self.db.execute_query('''
            SELECT 
                AVG(total_spent) as avg_ltv,
                AVG(orders_count) as avg_orders,
                AVG(total_spent / orders_count) as avg_order_value
            FROM (
                SELECT 
                    u.id,
                    SUM(o.total_amount) as total_spent,
                    COUNT(o.id) as orders_count
                FROM users u
                JOIN orders o ON u.id = o.user_id
                WHERE o.status != 'cancelled'
                GROUP BY u.id
                HAVING orders_count > 0
            ) customer_stats
        ''')[0]
        
        avg_clv = clv_data[0] or 0
        avg_orders = clv_data[1] or 0
        avg_order_value = clv_data[2] or 0
        
        # Churn Rate (отток клиентов)
        active_customers_30_days_ago = self.db.execute_query('''
            SELECT COUNT(DISTINCT user_id) FROM orders
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND status != 'cancelled'
        ''', (
            (start_date - timedelta(days=30)).strftime('%Y-%m-%d'),
            start_date.strftime('%Y-%m-%d')
        ))[0][0]
        
        active_customers_now = self.db.execute_query('''
            SELECT COUNT(DISTINCT user_id) FROM orders
            WHERE DATE(created_at) >= ?
            AND status != 'cancelled'
        ''', (start_date.strftime('%Y-%m-%d'),))[0][0]
        
        churn_rate = ((active_customers_30_days_ago - active_customers_now) / 
                     active_customers_30_days_ago * 100) if active_customers_30_days_ago > 0 else 0
        
        # Monthly Recurring Revenue (MRR) - для подписочных товаров
        mrr = self.db.execute_query('''
            SELECT SUM(total_amount) / 30 as daily_revenue
            FROM orders
            WHERE DATE(created_at) >= ?
            AND status != 'cancelled'
        ''', (start_date.strftime('%Y-%m-%d'),))[0][0] or 0
        
        return {
            'cac': cac,
            'clv': avg_clv,
            'clv_cac_ratio': avg_clv / cac if cac > 0 else 0,
            'avg_order_value': avg_order_value,
            'churn_rate': max(0, churn_rate),
            'mrr': mrr * 30,  # Месячная выручка
            'new_customers_30d': new_customers
        }