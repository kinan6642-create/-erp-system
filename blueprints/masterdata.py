# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, flash
from core.db import query, execute
from core.auth import login_required, permission_required, log_action
from core.accounting import get_account_id, ACC_AR, ACC_AP

bp = Blueprint('masterdata', __name__, url_prefix='/masterdata')


# ==================== العملاء ====================
@bp.route('/customers', methods=['GET', 'POST'])
@login_required
@permission_required('masterdata')
def customers():
    if request.method == 'POST':
        code = request.form.get('code') or f"CUS-{query('SELECT COUNT(*) c FROM customers', one=True)['c']+1:04d}"
        execute('''INSERT INTO customers (code, name, phone, address, account_id, opening_balance, credit_limit)
                   VALUES (?,?,?,?,?,?,?)''',
                (code, request.form['name'], request.form.get('phone'), request.form.get('address'),
                 get_account_id(ACC_AR), float(request.form.get('opening_balance') or 0),
                 float(request.form.get('credit_limit') or 0)))
        log_action('add', 'customers', None, f"إضافة عميل {request.form['name']}")
        flash('تمت إضافة العميل', 'success')
        return redirect(url_for('masterdata.customers'))
    items = query('SELECT * FROM customers ORDER BY id DESC')
    return render_template('masterdata/customers.html', items=items)


@bp.route('/customers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required('masterdata', 'can_edit')
def edit_customer(id):
    if request.method == 'POST':
        execute('''UPDATE customers SET name=?, phone=?, address=?, credit_limit=?, is_active=? WHERE id=?''',
                (request.form['name'], request.form.get('phone'), request.form.get('address'),
                 float(request.form.get('credit_limit') or 0), 1 if request.form.get('is_active') else 0, id))
        flash('تم التحديث', 'success')
        return redirect(url_for('masterdata.customers'))
    item = query('SELECT * FROM customers WHERE id=?', (id,), one=True)
    return render_template('masterdata/customer_form.html', item=item)


@bp.route('/customers/statement/<int:id>')
@login_required
@permission_required('masterdata')
def customer_statement(id):
    customer = query('SELECT * FROM customers WHERE id=?', (id,), one=True)
    invoices = query('SELECT * FROM sales_invoices WHERE customer_id=? ORDER BY date', (id,))
    receipts = query('SELECT * FROM receipt_vouchers WHERE customer_id=? ORDER BY date', (id,))
    returns = query('SELECT * FROM sales_returns WHERE customer_id=? ORDER BY date', (id,))
    return render_template('masterdata/customer_statement.html', customer=customer, invoices=invoices,
                           receipts=receipts, returns=returns)


# ==================== الموردون ====================
@bp.route('/suppliers', methods=['GET', 'POST'])
@login_required
@permission_required('masterdata')
def suppliers():
    if request.method == 'POST':
        code = request.form.get('code') or f"SUP-{query('SELECT COUNT(*) c FROM suppliers', one=True)['c']+1:04d}"
        execute('''INSERT INTO suppliers (code, name, phone, address, account_id, opening_balance)
                   VALUES (?,?,?,?,?,?)''',
                (code, request.form['name'], request.form.get('phone'), request.form.get('address'),
                 get_account_id(ACC_AP), float(request.form.get('opening_balance') or 0)))
        log_action('add', 'suppliers', None, f"إضافة مورد {request.form['name']}")
        flash('تمت إضافة المورد', 'success')
        return redirect(url_for('masterdata.suppliers'))
    items = query('SELECT * FROM suppliers ORDER BY id DESC')
    return render_template('masterdata/suppliers.html', items=items)


@bp.route('/suppliers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required('masterdata', 'can_edit')
def edit_supplier(id):
    if request.method == 'POST':
        execute('''UPDATE suppliers SET name=?, phone=?, address=?, is_active=? WHERE id=?''',
                (request.form['name'], request.form.get('phone'), request.form.get('address'),
                 1 if request.form.get('is_active') else 0, id))
        flash('تم التحديث', 'success')
        return redirect(url_for('masterdata.suppliers'))
    item = query('SELECT * FROM suppliers WHERE id=?', (id,), one=True)
    return render_template('masterdata/supplier_form.html', item=item)


@bp.route('/suppliers/statement/<int:id>')
@login_required
@permission_required('masterdata')
def supplier_statement(id):
    supplier = query('SELECT * FROM suppliers WHERE id=?', (id,), one=True)
    invoices = query('SELECT * FROM purchase_invoices WHERE supplier_id=? ORDER BY date', (id,))
    payments = query('SELECT * FROM payment_vouchers WHERE supplier_id=? ORDER BY date', (id,))
    returns = query('SELECT * FROM purchase_returns WHERE supplier_id=? ORDER BY date', (id,))
    return render_template('masterdata/supplier_statement.html', supplier=supplier, invoices=invoices,
                           payments=payments, returns=returns)


# ==================== الأصناف ====================
@bp.route('/items', methods=['GET', 'POST'])
@login_required
@permission_required('masterdata')
def items():
    if request.method == 'POST':
        code = request.form.get('code') or f"ITM-{query('SELECT COUNT(*) c FROM items', one=True)['c']+1:04d}"
        execute('''INSERT INTO items (code, name, category_id, unit_id, cost_price, sale_price, reorder_level, is_raw_material)
                   VALUES (?,?,?,?,?,?,?,?)''',
                (code, request.form['name'], request.form.get('category_id') or None,
                 request.form.get('unit_id') or None, float(request.form.get('cost_price') or 0),
                 float(request.form.get('sale_price') or 0), float(request.form.get('reorder_level') or 0),
                 1 if request.form.get('is_raw_material') else 0))
        flash('تمت إضافة الصنف', 'success')
        return redirect(url_for('masterdata.items'))
    items = query('''SELECT i.*, c.name as category_name, u.name as unit_name,
                      COALESCE((SELECT SUM(quantity) FROM inventory_stock WHERE item_id=i.id),0) as total_stock
                      FROM items i LEFT JOIN categories c ON c.id=i.category_id
                      LEFT JOIN units u ON u.id = i.unit_id ORDER BY i.id DESC''')
    categories = query('SELECT * FROM categories')
    units = query('SELECT * FROM units')
    return render_template('masterdata/items.html', items=items, categories=categories, units=units)


@bp.route('/items/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required('masterdata', 'can_edit')
def edit_item(id):
    if request.method == 'POST':
        execute('''UPDATE items SET name=?, category_id=?, unit_id=?, sale_price=?, reorder_level=?, is_active=? WHERE id=?''',
                (request.form['name'], request.form.get('category_id') or None, request.form.get('unit_id') or None,
                 float(request.form.get('sale_price') or 0), float(request.form.get('reorder_level') or 0),
                 1 if request.form.get('is_active') else 0, id))
        flash('تم التحديث', 'success')
        return redirect(url_for('masterdata.items'))
    item = query('SELECT * FROM items WHERE id=?', (id,), one=True)
    categories = query('SELECT * FROM categories')
    units = query('SELECT * FROM units')
    return render_template('masterdata/item_form.html', item=item, categories=categories, units=units)


# ==================== الخدمات ====================
@bp.route('/services', methods=['GET', 'POST'])
@login_required
@permission_required('masterdata')
def services():
    if request.method == 'POST':
        execute('INSERT INTO services (name, price) VALUES (?,?)',
                (request.form['name'], float(request.form.get('price') or 0)))
        flash('تمت الإضافة', 'success')
        return redirect(url_for('masterdata.services'))
    items = query('SELECT * FROM services ORDER BY id DESC')
    return render_template('masterdata/services.html', items=items)


# ==================== التصنيفات ====================
@bp.route('/categories', methods=['GET', 'POST'])
@login_required
@permission_required('masterdata')
def categories():
    if request.method == 'POST':
        execute('INSERT INTO categories (name) VALUES (?)', (request.form['name'],))
        flash('تمت الإضافة', 'success')
        return redirect(url_for('masterdata.categories'))
    items = query('SELECT * FROM categories ORDER BY id DESC')
    return render_template('masterdata/categories.html', items=items)


@bp.route('/categories/delete/<int:id>')
@login_required
@permission_required('masterdata', 'can_delete')
def delete_category(id):
    execute('DELETE FROM categories WHERE id=?', (id,))
    return redirect(url_for('masterdata.categories'))


# ==================== الوحدات ====================
@bp.route('/units', methods=['GET', 'POST'])
@login_required
@permission_required('masterdata')
def units():
    if request.method == 'POST':
        execute('INSERT INTO units (name) VALUES (?)', (request.form['name'],))
        flash('تمت الإضافة', 'success')
        return redirect(url_for('masterdata.units'))
    items = query('SELECT * FROM units ORDER BY id DESC')
    return render_template('masterdata/units.html', items=items)


@bp.route('/units/delete/<int:id>')
@login_required
@permission_required('masterdata', 'can_delete')
def delete_unit(id):
    execute('DELETE FROM units WHERE id=?', (id,))
    return redirect(url_for('masterdata.units'))


# ==================== مراكز التكلفة ====================
@bp.route('/cost-centers', methods=['GET', 'POST'])
@login_required
@permission_required('masterdata')
def cost_centers():
    if request.method == 'POST':
        execute('INSERT INTO cost_centers (name) VALUES (?)', (request.form['name'],))
        flash('تمت الإضافة', 'success')
        return redirect(url_for('masterdata.cost_centers'))
    items = query('SELECT * FROM cost_centers ORDER BY id DESC')
    return render_template('masterdata/cost_centers.html', items=items)


# ==================== الدليل المحاسبي ====================
@bp.route('/accounts', methods=['GET', 'POST'])
@login_required
@permission_required('masterdata')
def accounts():
    if request.method == 'POST':
        execute('INSERT INTO accounts (code, name, type, parent_id) VALUES (?,?,?,?)',
                (request.form['code'], request.form['name'], request.form['type'],
                 request.form.get('parent_id') or None))
        flash('تمت إضافة الحساب', 'success')
        return redirect(url_for('masterdata.accounts'))
    items = query('''SELECT a.*, p.name as parent_name FROM accounts a
                      LEFT JOIN accounts p ON p.id = a.parent_id ORDER BY a.code''')
    parents = query('SELECT * FROM accounts WHERE is_control=1')
    return render_template('masterdata/accounts.html', items=items, parents=parents)
