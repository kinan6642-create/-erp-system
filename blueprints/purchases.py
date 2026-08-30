# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from core.db import query, execute
from core.auth import login_required, permission_required, log_action
from core.accounting import (create_journal_entry, get_account_id, next_number,
                              ACC_CASH, ACC_BANK, ACC_AP, ACC_INVENTORY)
from core.inventory import move_stock

bp = Blueprint('purchases', __name__, url_prefix='/purchases')


@bp.route('/invoices')
@login_required
@permission_required('purchases')
def invoices():
    items = query('''SELECT p.*, s.name as supplier_name FROM purchase_invoices p
                      LEFT JOIN suppliers s ON s.id = p.supplier_id ORDER BY p.id DESC''')
    return render_template('purchases/invoices.html', items=items)


@bp.route('/invoices/new', methods=['GET', 'POST'])
@login_required
@permission_required('purchases', 'can_add')
def new_invoice():
    if request.method == 'POST':
        supplier_id = request.form.get('supplier_id') or None
        warehouse_id = int(request.form['warehouse_id'])
        payment_type = request.form['payment_type']
        date = request.form['date']
        discount = float(request.form.get('discount') or 0)
        tax_rate = float(request.form.get('tax_rate') or 0)

        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        prices = request.form.getlist('price[]')

        if not item_ids:
            flash('يجب إضافة صنف واحد على الأقل', 'danger')
            return redirect(url_for('purchases.new_invoice'))

        subtotal = sum(float(q) * float(p) for q, p in zip(quantities, prices))
        tax_total = round((subtotal - discount) * tax_rate / 100, 2)
        total = round(subtotal - discount + tax_total, 2)

        number = next_number('PI', 'purchase_invoices')
        invoice_id = execute('''INSERT INTO purchase_invoices
            (number, date, supplier_id, warehouse_id, payment_type, subtotal, discount, tax_total, total, paid_amount, status, created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (number, date, supplier_id, warehouse_id, payment_type, subtotal, discount, tax_total, total,
             total if payment_type == 'cash' else 0, 'posted', session['user_id']))

        # توزيع نسبي للخصم/الضريبة على كل صنف لتحديث تكلفته
        for iid, qty, price in zip(item_ids, quantities, prices):
            iid = int(iid); qty = float(qty); price = float(price)
            line_total = qty * price
            execute('''INSERT INTO purchase_invoice_items (invoice_id, item_id, quantity, price, total)
                       VALUES (?,?,?,?,?)''', (invoice_id, iid, qty, price, line_total))
            unit_cost_incl = price if subtotal == 0 else price * (total / subtotal)
            move_stock(iid, warehouse_id, 'in', qty, unit_cost=round(unit_cost_incl, 4),
                      ref_type='purchase_invoice', ref_id=invoice_id, notes=f'فاتورة شراء {number}')

        lines = [{'account_id': get_account_id(ACC_INVENTORY), 'debit': total, 'credit': 0}]
        if payment_type == 'cash':
            lines.append({'account_id': get_account_id(ACC_CASH), 'debit': 0, 'credit': total})
        else:
            lines.append({'account_id': get_account_id(ACC_AP), 'debit': 0, 'credit': total})
            execute('UPDATE suppliers SET opening_balance = opening_balance + ? WHERE id=?', (total, supplier_id))

        create_journal_entry(date, f'فاتورة شراء رقم {number}', lines, 'purchase_invoice', invoice_id, session['user_id'])
        log_action('add', 'purchase_invoices', invoice_id, f'فاتورة شراء {number} بقيمة {total}')

        flash(f'تم إنشاء فاتورة الشراء {number} بنجاح', 'success')
        return redirect(url_for('purchases.view_invoice', id=invoice_id))

    suppliers = query('SELECT * FROM suppliers WHERE is_active=1')
    warehouses = query('SELECT * FROM warehouses WHERE is_active=1')
    items = query('SELECT * FROM items WHERE is_active=1')
    from datetime import date as dt
    return render_template('purchases/invoice_form.html', suppliers=suppliers, warehouses=warehouses,
                           items=items, today=dt.today().isoformat())


@bp.route('/invoices/<int:id>')
@login_required
@permission_required('purchases')
def view_invoice(id):
    invoice = query('''SELECT p.*, s.name as supplier_name, w.name as warehouse_name
                        FROM purchase_invoices p LEFT JOIN suppliers s ON s.id=p.supplier_id
                        LEFT JOIN warehouses w ON w.id = p.warehouse_id WHERE p.id=?''', (id,), one=True)
    items = query('''SELECT pi.*, i.name as item_name, i.code FROM purchase_invoice_items pi
                      JOIN items i ON i.id = pi.item_id WHERE pi.invoice_id=?''', (id,))
    return render_template('purchases/invoice_view.html', invoice=invoice, items=items)


# ==================== مرتجع المشتريات ====================
@bp.route('/returns')
@login_required
@permission_required('purchases')
def returns():
    items = query('''SELECT r.*, s.name as supplier_name FROM purchase_returns r
                      LEFT JOIN suppliers s ON s.id = r.supplier_id ORDER BY r.id DESC''')
    return render_template('purchases/returns.html', items=items)


@bp.route('/returns/new', methods=['GET', 'POST'])
@login_required
@permission_required('purchases', 'can_add')
def new_return():
    if request.method == 'POST':
        invoice_id = int(request.form['invoice_id'])
        invoice = query('SELECT * FROM purchase_invoices WHERE id=?', (invoice_id,), one=True)
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        date = request.form['date']

        total = 0
        number = next_number('PRET', 'purchase_returns')
        return_id = execute('''INSERT INTO purchase_returns (number, date, invoice_id, supplier_id, warehouse_id, total)
                               VALUES (?,?,?,?,?,0)''',
                            (number, date, invoice_id, invoice['supplier_id'], invoice['warehouse_id']))

        for iid, qty in zip(item_ids, quantities):
            iid = int(iid); qty = float(qty)
            if qty <= 0:
                continue
            line = query('SELECT price FROM purchase_invoice_items WHERE invoice_id=? AND item_id=?',
                         (invoice_id, iid), one=True)
            price = line['price']
            line_total = qty * price
            total += line_total
            execute('''INSERT INTO purchase_return_items (return_id, item_id, quantity, price, total)
                       VALUES (?,?,?,?,?)''', (return_id, iid, qty, price, line_total))
            move_stock(iid, invoice['warehouse_id'], 'out', qty, ref_type='purchase_return',
                      ref_id=return_id, notes=f'مرتجع شراء {number}')

        execute('UPDATE purchase_returns SET total=? WHERE id=?', (total, return_id))

        lines = [{'account_id': get_account_id(ACC_INVENTORY), 'debit': 0, 'credit': total}]
        if invoice['payment_type'] == 'cash':
            lines.append({'account_id': get_account_id(ACC_CASH), 'debit': total, 'credit': 0})
        else:
            lines.append({'account_id': get_account_id(ACC_AP), 'debit': total, 'credit': 0})
            execute('UPDATE suppliers SET opening_balance = opening_balance - ? WHERE id=?',
                   (total, invoice['supplier_id']))

        create_journal_entry(date, f'مرتجع شراء رقم {number}', lines, 'purchase_return', return_id, session['user_id'])
        flash(f'تم تسجيل مرتجع الشراء {number}', 'success')
        return redirect(url_for('purchases.returns'))

    invoices = query("SELECT id, number FROM purchase_invoices WHERE status='posted' ORDER BY id DESC")
    from datetime import date as dt
    return render_template('purchases/return_form.html', invoices=invoices, today=dt.today().isoformat())


@bp.route('/api/invoice-items/<int:invoice_id>')
@login_required
def api_invoice_items(invoice_id):
    items = query('''SELECT pi.item_id, i.name, pi.quantity, pi.price FROM purchase_invoice_items pi
                      JOIN items i ON i.id = pi.item_id WHERE pi.invoice_id=?''', (invoice_id,))
    return jsonify([dict(r) for r in items])
