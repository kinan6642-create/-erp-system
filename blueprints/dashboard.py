# -*- coding: utf-8 -*-
from flask import Blueprint, render_template
from core.db import query
from core.auth import login_required
from core.inventory import total_inventory_value, low_stock_items
from datetime import date

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@bp.route('/')
@login_required
def index():
    today = date.today().isoformat()
    month_start = today[:7] + '-01'

    sales_today = query("SELECT COALESCE(SUM(total),0) t FROM sales_invoices WHERE date=? AND status='posted'",
                         (today,), one=True)['t']
    sales_month = query("SELECT COALESCE(SUM(total),0) t FROM sales_invoices WHERE date>=? AND status='posted'",
                         (month_start,), one=True)['t']
    purchases_month = query("SELECT COALESCE(SUM(total),0) t FROM purchase_invoices WHERE date>=? AND status='posted'",
                             (month_start,), one=True)['t']
    cogs_month = query("SELECT COALESCE(SUM(cost_total),0) t FROM sales_invoices WHERE date>=? AND status='posted'",
                        (month_start,), one=True)['t']
    profit_month = round(sales_month - cogs_month, 2)

    cash_balance = query("SELECT balance FROM accounts WHERE code='1101'", one=True)
    bank_balance = query("SELECT balance FROM accounts WHERE code='1102'", one=True)

    customers_debt = query("SELECT COALESCE(SUM(opening_balance),0) t FROM customers", one=True)['t']
    suppliers_debt = query("SELECT COALESCE(SUM(opening_balance),0) t FROM suppliers", one=True)['t']

    inventory_value = total_inventory_value()
    low_stock = low_stock_items()

    recent_sales = query('''
        SELECT s.id, s.number, s.date, s.total, c.name as customer_name
        FROM sales_invoices s LEFT JOIN customers c ON c.id = s.customer_id
        ORDER BY s.id DESC LIMIT 5
    ''')

    top_customers = query('''
        SELECT c.name, COALESCE(SUM(s.total),0) as total
        FROM customers c JOIN sales_invoices s ON s.customer_id = c.id
        GROUP BY c.id ORDER BY total DESC LIMIT 5
    ''')

    return render_template('dashboard.html',
                           sales_today=sales_today, sales_month=sales_month,
                           purchases_month=purchases_month, profit_month=profit_month,
                           cash_balance=cash_balance['balance'] if cash_balance else 0,
                           bank_balance=bank_balance['balance'] if bank_balance else 0,
                           customers_debt=customers_debt, suppliers_debt=suppliers_debt,
                           inventory_value=inventory_value, low_stock=low_stock,
                           recent_sales=recent_sales, top_customers=top_customers)
