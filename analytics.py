
"""Аналитика: сводные метрики, топы, временные ряды."""
from datetime import datetime

def get_sales_report(db, start_date, end_date):
    """Сводные метрики за период: кол-во заказов, выручка, средний чек, уникальные клиенты, топ-товары и топ-клиенты."""
    sales = db.execute_query('''
        SELECT 
            COUNT(*) as orders_count,
            IFNULL(SUM(total_amount), 0) as revenue,
            IFNULL(AVG(total_amount), 0) as avg_order_value,
            COUNT(DISTINCT user_id) as unique_customers
        FROM orders
        WHERE DATE(created_at) BETWEEN ? AND ?
          AND status != 'cancelled'
    ''', (start_date, end_date)) or [(0,0,0,0)]
    sales_row = sales[0]

    top_products = db.execute_query('''
        SELECT p.id, p.name,
               IFNULL(SUM(oi.quantity), 0) as qty,
               IFNULL(SUM(oi.quantity * COALESCE(oi.price,0)), 0) as revenue
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        JOIN orders o ON o.id = oi.order_id
        WHERE DATE(o.created_at) BETWEEN ? AND ?
          AND o.status != 'cancelled'
        GROUP BY p.id, p.name
        ORDER BY revenue DESC
        LIMIT 10
    ''', (start_date, end_date)) or []

    top_users = db.execute_query('''
        SELECT u.id, u.name,
               IFNULL(SUM(o.total_amount), 0) as spent,
               COUNT(o.id) as orders
        FROM users u
        JOIN orders o ON o.user_id = u.id
        WHERE DATE(o.created_at) BETWEEN ? AND ?
          AND o.status != 'cancelled'
        GROUP BY u.id, u.name
        ORDER BY spent DESC
        LIMIT 10
    ''', (start_date, end_date)) or []

    return type('SalesReport', (), {'sales_data':[sales_row], 'top_products': top_products, 'top_users': top_users})

def get_timeseries(db, start_date, end_date, group='daily'):
    """Временной ряд по заказам и выручке для графиков. group: daily|weekly|monthly"""
    if group == 'weekly':
        fmt = '%Y-%W'
    elif group == 'monthly':
        fmt = '%Y-%m'
    else:
        fmt = '%Y-%m-%d'
    rows = db.execute_query(f'''
        SELECT strftime('{fmt}', created_at) as bucket,
               COUNT(*) as orders,
               IFNULL(SUM(total_amount), 0) as revenue,
               COUNT(DISTINCT user_id) as customers
        FROM orders
        WHERE DATE(created_at) BETWEEN ? AND ?
          AND status != 'cancelled'
        GROUP BY bucket
        ORDER BY bucket
    ''', (start_date, end_date)) or []
    return rows
