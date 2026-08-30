# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from core.db import query, execute
from core.auth import login_required, permission_required, log_action
from core.accounting import next_number
from core.inventory import move_stock, get_stock, get_item_cost

bp = Blueprint('production', __name__, url_prefix='/production')


@bp.route('/orders')
@login_required
@permission_required('production')
def orders():
    items = query('''SELECT p.*, i.name as product_name, w.name as warehouse_name
                      FROM production_orders p JOIN items i ON i.id = p.product_item_id
                      JOIN warehouses w ON w.id = p.warehouse_id ORDER BY p.id DESC''')
    return render_template('production/orders.html', items=items)


@bp.route('/orders/new', methods=['GET', 'POST'])
@login_required
@permission_required('production', 'can_add')
def new_order():
    if request.method == 'POST':
        product_item_id = int(request.form['product_item_id'])
        warehouse_id = int(request.form['warehouse_id'])
        quantity = float(request.form['quantity'])
        date = request.form['date']
        notes = request.form.get('notes', '')

        material_ids = request.form.getlist('material_id[]')
        material_qtys = request.form.getlist('material_qty[]')

        # التحقق من توفر المواد الخام
        for mid, mqty in zip(material_ids, material_qtys):
            mid = int(mid); mqty = float(mqty)
            if get_stock(mid, warehouse_id) < mqty:
                item_row = query('SELECT name FROM items WHERE id=?', (mid,), one=True)
                flash(f"المادة الخام غير متوفرة بالكمية الكافية: {item_row['name']}", 'danger')
                return redirect(url_for('production.new_order'))

        number = next_number('PROD', 'production_orders')
        order_id = execute('''INSERT INTO production_orders
            (number, date, product_item_id, warehouse_id, quantity, notes, created_by)
            VALUES (?,?,?,?,?,?,?)''', (number, date, product_item_id, warehouse_id, quantity, notes, session['user_id']))

        total_material_cost = 0
        for mid, mqty in zip(material_ids, material_qtys):
            mid = int(mid); mqty = float(mqty)
            cost = get_item_cost(mid)
            execute('INSERT INTO production_materials (order_id, item_id, quantity, unit_cost) VALUES (?,?,?,?)',
                   (order_id, mid, mqty, cost))
            move_stock(mid, warehouse_id, 'out', mqty, ref_type='production_order', ref_id=order_id,
                      notes=f'أمر إنتاج {number} - استهلاك مواد خام')
            total_material_cost += mqty * cost

        unit_cost = round(total_material_cost / quantity, 4) if quantity else 0
        move_stock(product_item_id, warehouse_id, 'in', quantity, unit_cost=unit_cost,
                  ref_type='production_order', ref_id=order_id, notes=f'أمر إنتاج {number} - منتج جاهز')

        flash(f'تم إنشاء أمر الإنتاج {number} بتكلفة وحدة {unit_cost}', 'success')
        return redirect(url_for('production.orders'))

    products = query('SELECT * FROM items WHERE is_active=1 AND is_raw_material=0')
    materials = query('SELECT * FROM items WHERE is_active=1 AND is_raw_material=1')
    all_items = query('SELECT * FROM items WHERE is_active=1')
    warehouses = query('SELECT * FROM warehouses WHERE is_active=1')
    from datetime import date as dt
    return render_template('production/order_form.html', products=products, materials=materials,
                           all_items=all_items, warehouses=warehouses, today=dt.today().isoformat())


@bp.route('/orders/<int:id>')
@login_required
@permission_required('production')
def view_order(id):
    order = query('''SELECT p.*, i.name as product_name, w.name as warehouse_name
                      FROM production_orders p JOIN items i ON i.id = p.product_item_id
                      JOIN warehouses w ON w.id = p.warehouse_id WHERE p.id=?''', (id,), one=True)
    materials = query('''SELECT m.*, i.name as item_name FROM production_materials m
                          JOIN items i ON i.id = m.item_id WHERE m.order_id=?''', (id,))
    return render_template('production/order_view.html', order=order, materials=materials)
