# -*- coding: utf-8 -*-
"""
المحرك المحاسبي المركزي
========================
كل عملية في النظام (فاتورة بيع، فاتورة شراء، سند قبض، سند صرف، مصروف...)
تمر من هنا لإنشاء قيد محاسبي مزدوج (مدين = دائن) وتحديث أرصدة الحسابات
وأرصدة العملاء/الموردين تلقائياً.
"""
from core.db import get_db, execute, query
from datetime import datetime

# ---------- أكواد الحسابات الثابتة (يتم إنشاؤها في seed.py) ----------
ACC_CASH = '1101'          # الصندوق
ACC_BANK = '1102'          # البنك
ACC_AR = '1201'            # العملاء (ذمم مدينة)
ACC_INVENTORY = '1301'     # المخزون
ACC_AP = '2101'            # الموردون (ذمم دائنة)
ACC_TAX_PAYABLE = '2102'   # ضريبة مستحقة
ACC_SALES = '4101'         # إيرادات المبيعات
ACC_OTHER_REVENUE = '4201'  # إيرادات أخرى
ACC_COGS = '5101'          # تكلفة البضاعة المباعة
ACC_EXPENSE = '5201'       # مصاريف تشغيلية عامة


def get_account_id(code):
    row = query('SELECT id FROM accounts WHERE code=?', (code,), one=True)
    if not row:
        raise ValueError(f'الحساب بالكود {code} غير موجود في الدليل المحاسبي')
    return row['id']


def next_number(prefix, table):
    """يولد رقم مستند تسلسلي مثل INV-000001"""
    row = query(f'SELECT COUNT(*) c FROM {table}', one=True)
    seq = (row['c'] or 0) + 1
    return f"{prefix}-{seq:06d}"


def create_journal_entry(date, description, lines, ref_type=None, ref_id=None, created_by=None):
    """
    lines: قائمة من dict {account_id, debit, credit, cost_center_id(اختياري)}
    يتحقق أن إجمالي المدين = إجمالي الدائن قبل الترحيل، ثم يحدّث أرصدة الحسابات.
    """
    total_debit = round(sum(l.get('debit', 0) or 0 for l in lines), 2)
    total_credit = round(sum(l.get('credit', 0) or 0 for l in lines), 2)
    if total_debit != total_credit:
        raise ValueError(f'القيد غير متوازن: مدين {total_debit} != دائن {total_credit}')
    if total_debit == 0:
        raise ValueError('لا يمكن ترحيل قيد بقيمة صفر')

    number = next_number('JE', 'journal_entries')
    entry_id = execute(
        'INSERT INTO journal_entries (number, date, description, ref_type, ref_id, created_by) VALUES (?,?,?,?,?,?)',
        (number, date, description, ref_type, ref_id, created_by)
    )
    db = get_db()
    for l in lines:
        db.execute(
            'INSERT INTO journal_entry_lines (entry_id, account_id, debit, credit, cost_center_id) VALUES (?,?,?,?,?)',
            (entry_id, l['account_id'], l.get('debit', 0) or 0, l.get('credit', 0) or 0, l.get('cost_center_id'))
        )
        # تحديث رصيد الحساب: نعتبر (مدين - دائن) هو التغير على حساب من نوع أصل/مصروف
        acc = query('SELECT type FROM accounts WHERE id=?', (l['account_id'],), one=True)
        delta = (l.get('debit', 0) or 0) - (l.get('credit', 0) or 0)
        if acc['type'] in ('asset', 'expense'):
            db.execute('UPDATE accounts SET balance = balance + ? WHERE id=?', (delta, l['account_id']))
        else:  # liability, equity, revenue تزيد بالدائن
            db.execute('UPDATE accounts SET balance = balance - ? WHERE id=?', (delta, l['account_id']))
    db.commit()
    return entry_id


def cash_or_bank_account(method):
    return get_account_id(ACC_CASH if method == 'cash' else ACC_BANK)


# ------------------------------------------------------------------
# دوال مساعدة لتحديث أرصدة العملاء والموردين
# ------------------------------------------------------------------
def adjust_customer_balance(customer_id, delta):
    execute('UPDATE customers SET opening_balance = opening_balance + ? WHERE id=?', (delta, customer_id))


def adjust_supplier_balance(supplier_id, delta):
    execute('UPDATE suppliers SET opening_balance = opening_balance + ? WHERE id=?', (delta, supplier_id))


def get_customer_balance(customer_id):
    row = query('SELECT opening_balance FROM customers WHERE id=?', (customer_id,), one=True)
    return row['opening_balance'] if row else 0


def get_supplier_balance(supplier_id):
    row = query('SELECT opening_balance FROM suppliers WHERE id=?', (supplier_id,), one=True)
    return row['opening_balance'] if row else 0
