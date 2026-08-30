# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request
from core.db import query
from core.auth import login_required, permission_required
from core.inventory import total_inventory_value

bp = Blueprint('reports', __name__, url_prefix='/reports')


@bp.route('/')
@login_required
@permission_required('reports')
def index():
    return render_template('reports/index.html')


# ==================== ميزان المراجعة ====================
@bp.route('/trial-balance')
@login_required
@permission_required('reports')
def trial_balance():
    accounts = query('''SELECT * FROM accounts WHERE is_control=0 ORDER BY code''')
    rows = []
    total_debit = total_credit = 0
    for a in accounts:
        bal = a['balance'] or 0
        if a['type'] in ('asset', 'expense'):
            debit = bal if bal >= 0 else 0
            credit = -bal if bal < 0 else 0
        else:
            credit = bal if bal >= 0 else 0
            debit = -bal if bal < 0 else 0
        if debit or credit:
            rows.append({'code': a['code'], 'name': a['name'], 'debit': debit, 'credit': credit})
            total_debit += debit
            total_credit += credit
    return render_template('reports/trial_balance.html', rows=rows, total_debit=round(total_debit, 2),
                           total_credit=round(total_credit, 2))


# ==================== قائمة الدخل (الأرباح والخسائر) ====================
@bp.route('/income-statement')
@login_required
@permission_required('reports')
def income_statement():
    date_from = request.args.get('from', '2000-01-01')
    date_to = request.args.get('to', '2100-01-01')

    revenue_rows = query('''
        SELECT a.name, COALESCE(SUM(l.credit - l.debit),0) as amount
        FROM accounts a JOIN journal_entry_lines l ON l.account_id = a.id
        JOIN journal_entries j ON j.id = l.entry_id
        WHERE a.type='revenue' AND a.is_control=0 AND j.date BETWEEN ? AND ?
        GROUP BY a.id HAVING amount != 0''', (date_from, date_to))

    expense_rows = query('''
        SELECT a.name, COALESCE(SUM(l.debit - l.credit),0) as amount
        FROM accounts a JOIN journal_entry_lines l ON l.account_id = a.id
        JOIN journal_entries j ON j.id = l.entry_id
        WHERE a.type='expense' AND a.is_control=0 AND j.date BETWEEN ? AND ?
        GROUP BY a.id HAVING amount != 0''', (date_from, date_to))

    total_revenue = sum(r['amount'] for r in revenue_rows)
    total_expense = sum(r['amount'] for r in expense_rows)
    net_profit = round(total_revenue - total_expense, 2)

    return render_template('reports/income_statement.html', revenue_rows=revenue_rows, expense_rows=expense_rows,
                           total_revenue=total_revenue, total_expense=total_expense, net_profit=net_profit,
                           date_from=date_from, date_to=date_to)


# ==================== الميزانية العمومية ====================
@bp.route('/balance-sheet')
@login_required
@permission_required('reports')
def balance_sheet():
    assets = query("SELECT * FROM accounts WHERE type='asset' AND is_control=0 ORDER BY code")
    liabilities = query("SELECT * FROM accounts WHERE type='liability' AND is_control=0 ORDER BY code")
    equity = query("SELECT * FROM accounts WHERE type='equity' AND is_control=0 ORDER BY code")

    total_assets = sum(a['balance'] or 0 for a in assets)
    total_liabilities = sum(a['balance'] or 0 for a in liabilities)
    total_equity_base = sum(a['balance'] or 0 for a in equity)

    # صافي الربح المتراكم يُضاف لحقوق الملكية لإتمام التوازن
    revenue_total = query("SELECT COALESCE(SUM(balance),0) t FROM accounts WHERE type='revenue' AND is_control=0", one=True)['t']
    expense_total = query("SELECT COALESCE(SUM(balance),0) t FROM accounts WHERE type='expense' AND is_control=0", one=True)['t']
    net_profit = revenue_total - expense_total
    total_equity = total_equity_base + net_profit

    return render_template('reports/balance_sheet.html', assets=assets, liabilities=liabilities, equity=equity,
                           total_assets=round(total_assets, 2), total_liabilities=round(total_liabilities, 2),
                           total_equity=round(total_equity, 2), net_profit=round(net_profit, 2))


# ==================== التدفقات النقدية (مبسطة) ====================
@bp.route('/cash-flow')
@login_required
@permission_required('reports')
def cash_flow():
    cash_id = query("SELECT id FROM accounts WHERE code='1101'", one=True)['id']
    bank_id = query("SELECT id FROM accounts WHERE code='1102'", one=True)['id']
    rows = query('''
        SELECT j.date, j.description, l.debit, l.credit, a.name as account_name
        FROM journal_entry_lines l JOIN journal_entries j ON j.id = l.entry_id
        JOIN accounts a ON a.id = l.account_id
        WHERE l.account_id IN (?, ?) ORDER BY j.date, j.id''', (cash_id, bank_id))
    inflow = sum(r['debit'] for r in rows)
    outflow = sum(r['credit'] for r in rows)
    return render_template('reports/cash_flow.html', rows=rows, inflow=round(inflow, 2), outflow=round(outflow, 2),
                           net=round(inflow - outflow, 2))


# ==================== تقارير تشغيلية ====================
@bp.route('/sales')
@login_required
@permission_required('reports')
def sales_report():
    rows = query('''SELECT s.number, s.date, c.name as customer_name, s.total, s.cost_total,
                     (s.total - s.cost_total) as profit, s.payment_type
                     FROM sales_invoices s LEFT JOIN customers c ON c.id = s.customer_id
                     ORDER BY s.date DESC''')
    total_sales = sum(r['total'] for r in rows)
    total_profit = sum(r['profit'] for r in rows)
    return render_template('reports/sales_report.html', rows=rows, total_sales=round(total_sales, 2),
                           total_profit=round(total_profit, 2))


@bp.route('/purchases')
@login_required
@permission_required('reports')
def purchases_report():
    rows = query('''SELECT p.number, p.date, s.name as supplier_name, p.total, p.payment_type
                     FROM purchase_invoices p LEFT JOIN suppliers s ON s.id = p.supplier_id
                     ORDER BY p.date DESC''')
    total = sum(r['total'] for r in rows)
    return render_template('reports/purchases_report.html', rows=rows, total=round(total, 2))


@bp.route('/inventory-valuation')
@login_required
@permission_required('reports')
def inventory_valuation():
    rows = query('''SELECT i.code, i.name, w.name as warehouse_name, s.quantity, i.cost_price,
                     (s.quantity * i.cost_price) as value
                     FROM inventory_stock s JOIN items i ON i.id = s.item_id
                     JOIN warehouses w ON w.id = s.warehouse_id
                     WHERE s.quantity > 0 ORDER BY value DESC''')
    total = total_inventory_value()
    return render_template('reports/inventory_valuation.html', rows=rows, total=total)


@bp.route('/customers-debts')
@login_required
@permission_required('reports')
def customers_debts():
    rows = query("SELECT * FROM customers WHERE opening_balance != 0 ORDER BY opening_balance DESC")
    total = sum(r['opening_balance'] for r in rows)
    return render_template('reports/customers_debts.html', rows=rows, total=round(total, 2))


@bp.route('/suppliers-debts')
@login_required
@permission_required('reports')
def suppliers_debts():
    rows = query("SELECT * FROM suppliers WHERE opening_balance != 0 ORDER BY opening_balance DESC")
    total = sum(r['opening_balance'] for r in rows)
    return render_template('reports/suppliers_debts.html', rows=rows, total=round(total, 2))


@bp.route('/audit-log')
@login_required
@permission_required('reports')
def audit_log():
    rows = query('SELECT * FROM audit_log ORDER BY id DESC LIMIT 300')
    return render_template('reports/audit_log.html', rows=rows)
