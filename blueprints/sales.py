# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from core.db import query, execute, get_db
from core.auth import login_required, permission_required, log_action
from core.accounting import (create_journal_entry, get_account_id, next_number,
                              ACC_CASH, ACC_BANK, ACC_AR, ACC_INVENTORY, ACC_SALES, ACC_COGS, ACC_TAX_PAYABLE)
from core.inventory import move_stock, get_stock, get_item_cost

bp = Blueprint('sales', __name__, url_prefix='/sales')


# ==================== فواتير البيع ====================
@bp.route('/invoices')
@login_required
@permission_required('sales')
def invoices():
    items = query('''SELECT s.*, c.name as customer_name FROM sales_invoices s
                      LEFT JOIN customers c ON c.id = s.customer_id ORDER BY s.id DESC''')
    return render_template('sales/invoices.html', items=items)


@bp.route('/invoices/new', methods=['GET', 'POST'])
@login_required
@permission_required('sales', 'can_add')
def new_invoice():
    if request.method == 'POST':
        try:
            customer_id = request.form.get('customer_id') or None
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
                return redirect(url_for('sales.new_invoice'))

            subtotal = 0
            cost_total = 0
            line_items = []
            for iid, qty, price in zip(item_ids, quantities, prices):
                iid = int(iid); qty = float(qty); price = float(price)
                if get_stock(iid, warehouse_id) < qty:
                    item_row = query('SELECT name FROM items WHERE id=?', (iid,), one=True)
                    flash(f"الكمية غير متوفرة للصنف: {item_row['name']}", 'danger')
                    return redirect(url_for('sales.new_invoice'))
                cost = get_item_cost(iid)
                subtotal += qty * price
                cost_total += qty * cost
                line_items.append((iid, qty, price, cost))

            tax_total = round((subtotal - discount) * tax_rate / 100, 2)
            total = round(subtotal - discount + tax_total, 2)

            number = next_number('SI', 'sales_invoices')
            invoice_id = execute('''INSERT INTO sales_invoices
                (number, date, customer_id, warehouse_id, payment_type, subtotal, discount, tax_total, total, cost_total, paid_amount, status, created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (number, date, customer_id, warehouse_id, payment_type, subtotal, discount, tax_total, total,
                 cost_total, total if payment_type == 'cash' else 0, 'posted', session['user_id']))

            for iid, qty, price, cost in line_items:
                execute('''INSERT INTO sales_invoice_items (invoice_id, item_id, quantity, price, cost_price, total)
                           VALUES (?,?,?,?,?,?)''', (invoice_id, iid, qty, price, cost, qty * price))
                move_stock(iid, warehouse_id, 'out', qty, ref_type='sales_invoice', ref_id=invoice_id,
                          notes=f'فاتورة بيع {number}')

            # ---- القيد المحاسبي ----
            lines = []
            if payment_type == 'cash':
                lines.append({'account_id': get_account_id(ACC_CASH), 'debit': total, 'credit': 0})
            else:
                lines.append({'account_id': get_account_id(ACC_AR), 'debit': total, 'credit': 0})
                execute('UPDATE customers SET opening_balance = opening_balance + ? WHERE id=?', (total, customer_id))
            lines.append({'account_id': get_account_id(ACC_SALES), 'debit': 0, 'credit': round(subtotal - discount, 2)})
            if tax_total:
                lines.append({'account_id': get_account_id(ACC_TAX_PAYABLE), 'debit': 0, 'credit': tax_total})
            if cost_total:
                lines.append({'account_id': get_account_id(ACC_COGS), 'debit': cost_total, 'credit': 0})
                lines.append({'account_id': get_account_id(ACC_INVENTORY), 'debit': 0, 'credit': cost_total})

            create_journal_entry(date, f'فاتورة بيع رقم {number}', lines, 'sales_invoice', invoice_id, session['user_id'])
            log_action('add', 'sales_invoices', invoice_id, f'فاتورة بيع {number} بقيمة {total}')

            flash(f'تم إنشاء فاتورة البيع {number} بنجاح', 'success')
            return redirect(url_for('sales.view_invoice', id=invoice_id))
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('sales.new_invoice'))

    customers = query('SELECT * FROM customers WHERE is_active=1')
    warehouses = query('SELECT * FROM warehouses WHERE is_active=1')
    items = query('SELECT * FROM items WHERE is_active=1')
    from datetime import date as dt
    return render_template('sales/invoice_form.html', customers=customers, warehouses=warehouses,
                           items=items, today=dt.today().isoformat())


@bp.route('/invoices/<int:id>')
@login_required
@permission_required('sales')
def view_invoice(id):
    invoice = query('''SELECT s.*, c.name as customer_name, w.name as warehouse_name
                        FROM sales_invoices s LEFT JOIN customers c ON c.id=s.customer_id
                        LEFT JOIN warehouses w ON w.id = s.warehouse_id WHERE s.id=?''', (id,), one=True)
    items = query('''SELECT si.*, i.name as item_name, i.code FROM sales_invoice_items si
                      JOIN items i ON i.id = si.item_id WHERE si.invoice_id=?''', (id,))
    return render_template('sales/invoice_view.html', invoice=invoice, items=items)


# ==================== مرتجع المبيعات ====================
@bp.route('/returns')
@login_required
@permission_required('sales')
def returns():
    items = query('''SELECT r.*, c.name as customer_name FROM sales_returns r
                      LEFT JOIN customers c ON c.id = r.customer_id ORDER BY r.id DESC''')
    return render_template('sales/returns.html', items=items)


@bp.route('/returns/new', methods=['GET', 'POST'])
@login_required
@permission_required('sales', 'can_add')
def new_return():
    if request.method == 'POST':
        invoice_id = int(request.form['invoice_id'])
        invoice = query('SELECT * FROM sales_invoices WHERE id=?', (invoice_id,), one=True)
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        date = request.form['date']

        total = 0
        cost_total = 0
        number = next_number('SRET', 'sales_returns')
        return_id = execute('''INSERT INTO sales_returns (number, date, invoice_id, customer_id, warehouse_id, total)
                               VALUES (?,?,?,?,?,0)''',
                            (number, date, invoice_id, invoice['customer_id'], invoice['warehouse_id']))

        for iid, qty in zip(item_ids, quantities):
            iid = int(iid); qty = float(qty)
            if qty <= 0:
                continue
            line = query('SELECT price, cost_price FROM sales_invoice_items WHERE invoice_id=? AND item_id=?',
                         (invoice_id, iid), one=True)
            price = line['price']; cost = line['cost_price']
            line_total = qty * price
            total += line_total
            cost_total += qty * cost
            execute('''INSERT INTO sales_return_items (return_id, item_id, quantity, price, cost_price, total)
                       VALUES (?,?,?,?,?,?)''', (return_id, iid, qty, price, cost, line_total))
            move_stock(iid, invoice['warehouse_id'], 'in', qty, unit_cost=cost, ref_type='sales_return',
                      ref_id=return_id, notes=f'مرتجع بيع {number}')

        execute('UPDATE sales_returns SET total=? WHERE id=?', (total, return_id))

        lines = [{'account_id': get_account_id(ACC_SALES), 'debit': total, 'credit': 0}]
        if invoice['payment_type'] == 'cash':
            lines.append({'account_id': get_account_id(ACC_CASH), 'debit': 0, 'credit': total})
        else:
            lines.append({'account_id': get_account_id(ACC_AR), 'debit': 0, 'credit': total})
            execute('UPDATE customers SET opening_balance = opening_balance - ? WHERE id=?',
                   (total, invoice['customer_id']))
        if cost_total:
            lines.append({'account_id': get_account_id(ACC_INVENTORY), 'debit': cost_total, 'credit': 0})
            lines.append({'account_id': get_account_id(ACC_COGS), 'debit': 0, 'credit': cost_total})

        create_journal_entry(date, f'مرتجع بيع رقم {number}', lines, 'sales_return', return_id, session['user_id'])
        flash(f'تم تسجيل مرتجع البيع {number}', 'success')
        return redirect(url_for('sales.returns'))

    invoices = query("SELECT id, number FROM sales_invoices WHERE status='posted' ORDER BY id DESC")
    from datetime import date as dt
    return render_template('sales/return_form.html', invoices=invoices, today=dt.today().isoformat())


@bp.route('/api/invoice-items/<int:invoice_id>')
@login_required
def api_invoice_items(invoice_id):
    from flask import jsonify
    items = query('''SELECT si.item_id, i.name, si.quantity, si.price FROM sales_invoice_items si
                      JOIN items i ON i.id = si.item_id WHERE si.invoice_id=?''', (invoice_id,))
    return jsonify([dict(r) for r in items])
