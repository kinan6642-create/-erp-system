# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from core.db import query, execute
from core.auth import login_required, permission_required, log_action
from core.accounting import (create_journal_entry, get_account_id, next_number, cash_or_bank_account,
                              ACC_CASH, ACC_BANK, ACC_AR, ACC_AP, ACC_OTHER_REVENUE, ACC_EXPENSE)

bp = Blueprint('finance', __name__, url_prefix='/finance')


# ==================== سند قبض ====================
@bp.route('/receipts', methods=['GET', 'POST'])
@login_required
@permission_required('finance', 'can_add')
def receipts():
    if request.method == 'POST':
        customer_id = int(request.form['customer_id'])
        amount = float(request.form['amount'])
        method = request.form['method']
        date = request.form['date']
        notes = request.form.get('notes', '')

        number = next_number('REC', 'receipt_vouchers')
        rid = execute('''INSERT INTO receipt_vouchers (number, date, customer_id, amount, method, notes, created_by)
                         VALUES (?,?,?,?,?,?,?)''', (number, date, customer_id, amount, method, notes, session['user_id']))

        execute('UPDATE customers SET opening_balance = opening_balance - ? WHERE id=?', (amount, customer_id))

        lines = [
            {'account_id': cash_or_bank_account(method), 'debit': amount, 'credit': 0},
            {'account_id': get_account_id(ACC_AR), 'debit': 0, 'credit': amount},
        ]
        create_journal_entry(date, f'سند قبض رقم {number}', lines, 'receipt_voucher', rid, session['user_id'])
        flash(f'تم تسجيل سند القبض {number}', 'success')
        return redirect(url_for('finance.receipts'))

    customers = query('SELECT * FROM customers WHERE is_active=1')
    history = query('''SELECT r.*, c.name as customer_name FROM receipt_vouchers r
                        JOIN customers c ON c.id = r.customer_id ORDER BY r.id DESC LIMIT 100''')
    from datetime import date as dt
    return render_template('finance/receipts.html', customers=customers, history=history, today=dt.today().isoformat())


# ==================== سند صرف ====================
@bp.route('/payments', methods=['GET', 'POST'])
@login_required
@permission_required('finance', 'can_add')
def payments():
    if request.method == 'POST':
        supplier_id = int(request.form['supplier_id'])
        amount = float(request.form['amount'])
        method = request.form['method']
        date = request.form['date']
        notes = request.form.get('notes', '')

        number = next_number('PAY', 'payment_vouchers')
        pid = execute('''INSERT INTO payment_vouchers (number, date, supplier_id, amount, method, notes, created_by)
                         VALUES (?,?,?,?,?,?,?)''', (number, date, supplier_id, amount, method, notes, session['user_id']))

        execute('UPDATE suppliers SET opening_balance = opening_balance - ? WHERE id=?', (amount, supplier_id))

        lines = [
            {'account_id': get_account_id(ACC_AP), 'debit': amount, 'credit': 0},
            {'account_id': cash_or_bank_account(method), 'debit': 0, 'credit': amount},
        ]
        create_journal_entry(date, f'سند صرف رقم {number}', lines, 'payment_voucher', pid, session['user_id'])
        flash(f'تم تسجيل سند الصرف {number}', 'success')
        return redirect(url_for('finance.payments'))

    suppliers = query('SELECT * FROM suppliers WHERE is_active=1')
    history = query('''SELECT p.*, s.name as supplier_name FROM payment_vouchers p
                        JOIN suppliers s ON s.id = p.supplier_id ORDER BY p.id DESC LIMIT 100''')
    from datetime import date as dt
    return render_template('finance/payments.html', suppliers=suppliers, history=history, today=dt.today().isoformat())


# ==================== المصاريف ====================
@bp.route('/expenses', methods=['GET', 'POST'])
@login_required
@permission_required('finance', 'can_add')
def expenses():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        method = request.form['method']
        date = request.form['date']
        category = request.form.get('category', '')
        description = request.form.get('description', '')

        number = next_number('EXP', 'expenses')
        eid = execute('''INSERT INTO expenses (number, date, category, amount, method, description, created_by)
                         VALUES (?,?,?,?,?,?,?)''', (number, date, category, amount, method, description, session['user_id']))

        lines = [
            {'account_id': get_account_id(ACC_EXPENSE), 'debit': amount, 'credit': 0},
            {'account_id': cash_or_bank_account(method), 'debit': 0, 'credit': amount},
        ]
        create_journal_entry(date, f'مصروف رقم {number}: {category}', lines, 'expense', eid, session['user_id'])
        flash(f'تم تسجيل المصروف {number}', 'success')
        return redirect(url_for('finance.expenses'))

    history = query('SELECT * FROM expenses ORDER BY id DESC LIMIT 100')
    from datetime import date as dt
    return render_template('finance/expenses.html', history=history, today=dt.today().isoformat())


# ==================== الإيرادات الأخرى ====================
@bp.route('/revenues', methods=['GET', 'POST'])
@login_required
@permission_required('finance', 'can_add')
def revenues():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        method = request.form['method']
        date = request.form['date']
        category = request.form.get('category', '')
        description = request.form.get('description', '')

        number = next_number('REV', 'revenues')
        rid = execute('''INSERT INTO revenues (number, date, category, amount, method, description, created_by)
                         VALUES (?,?,?,?,?,?,?)''', (number, date, category, amount, method, description, session['user_id']))

        lines = [
            {'account_id': cash_or_bank_account(method), 'debit': amount, 'credit': 0},
            {'account_id': get_account_id(ACC_OTHER_REVENUE), 'debit': 0, 'credit': amount},
        ]
        create_journal_entry(date, f'إيراد رقم {number}: {category}', lines, 'revenue', rid, session['user_id'])
        flash(f'تم تسجيل الإيراد {number}', 'success')
        return redirect(url_for('finance.revenues'))

    history = query('SELECT * FROM revenues ORDER BY id DESC LIMIT 100')
    from datetime import date as dt
    return render_template('finance/revenues.html', history=history, today=dt.today().isoformat())


# ==================== تحويل بين الصندوق والبنك ====================
@bp.route('/bank-transfers', methods=['GET', 'POST'])
@login_required
@permission_required('finance', 'can_add')
def bank_transfers():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        direction = request.form['direction']
        date = request.form['date']
        notes = request.form.get('notes', '')

        number = next_number('BTR', 'bank_transfers')
        tid = execute('''INSERT INTO bank_transfers (number, date, direction, amount, notes, created_by)
                         VALUES (?,?,?,?,?,?)''', (number, date, direction, amount, notes, session['user_id']))

        if direction == 'cash_to_bank':
            lines = [{'account_id': get_account_id(ACC_BANK), 'debit': amount, 'credit': 0},
                     {'account_id': get_account_id(ACC_CASH), 'debit': 0, 'credit': amount}]
        else:
            lines = [{'account_id': get_account_id(ACC_CASH), 'debit': amount, 'credit': 0},
                     {'account_id': get_account_id(ACC_BANK), 'debit': 0, 'credit': amount}]
        create_journal_entry(date, f'تحويل بنكي رقم {number}', lines, 'bank_transfer', tid, session['user_id'])
        flash(f'تم تسجيل التحويل {number}', 'success')
        return redirect(url_for('finance.bank_transfers'))

    history = query('SELECT * FROM bank_transfers ORDER BY id DESC LIMIT 100')
    cash_balance = query("SELECT balance FROM accounts WHERE code='1101'", one=True)['balance']
    bank_balance = query("SELECT balance FROM accounts WHERE code='1102'", one=True)['balance']
    from datetime import date as dt
    return render_template('finance/bank_transfers.html', history=history, today=dt.today().isoformat(),
                           cash_balance=cash_balance, bank_balance=bank_balance)


# ==================== القيود اليومية / دفتر الأستاذ ====================
@bp.route('/journal')
@login_required
@permission_required('finance')
def journal():
    entries = query('SELECT * FROM journal_entries ORDER BY id DESC LIMIT 100')
    return render_template('finance/journal.html', entries=entries)


@bp.route('/journal/<int:id>')
@login_required
@permission_required('finance')
def journal_view(id):
    entry = query('SELECT * FROM journal_entries WHERE id=?', (id,), one=True)
    lines = query('''SELECT l.*, a.code, a.name FROM journal_entry_lines l
                      JOIN accounts a ON a.id = l.account_id WHERE l.entry_id=?''', (id,))
    return render_template('finance/journal_view.html', entry=entry, lines=lines)


@bp.route('/ledger/<int:account_id>')
@login_required
@permission_required('finance')
def ledger(account_id):
    account = query('SELECT * FROM accounts WHERE id=?', (account_id,), one=True)
    lines = query('''SELECT l.*, j.date, j.number, j.description FROM journal_entry_lines l
                      JOIN journal_entries j ON j.id = l.entry_id
                      WHERE l.account_id=? ORDER BY j.date, j.id''', (account_id,))
    return render_template('finance/ledger.html', account=account, lines=lines)
