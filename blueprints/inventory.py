# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from core.db import query, execute
from core.auth import login_required, permission_required, log_action
from core.accounting import create_journal_entry, get_account_id, next_number, ACC_INVENTORY, ACC_OTHER_REVENUE, ACC_EXPENSE
from core.inventory import move_stock, get_stock, get_item_cost, total_inventory_value, low_stock_items

bp = Blueprint('inventory', __name__, url_prefix='/inventory')


@bp.route('/stock')
@login_required
@permission_required('inventory')
def stock():
    rows = query('''SELECT i.code, i.name, w.name as warehouse_name, s.quantity, i.cost_price,
                     (s.quantity * i.cost_price) as value
                     FROM inventory_stock s JOIN items i ON i.id = s.item_id
                     JOIN warehouses w ON w.id = s.warehouse_id
                     ORDER BY i.name''')
    total_value = total_inventory_value()
    return render_template('inventory/stock.html', rows=rows, total_value=total_value)


@bp.route('/moves')
@login_required
@permission_required('inventory')
def moves():
    rows = query('''SELECT m.*, i.name as item_name, w.name as warehouse_name
                     FROM inventory_moves m JOIN items i ON i.id = m.item_id
                     JOIN warehouses w ON w.id = m.warehouse_id
                     ORDER BY m.id DESC LIMIT 200''')
    return render_template('inventory/moves.html', rows=rows)


@bp.route('/low-stock')
@login_required
@permission_required('inventory')
def low_stock():
    items = low_stock_items()
    return render_template('inventory/low_stock.html', items=items)


# ==================== الجرد والتسوية ====================
@bp.route('/adjustments', methods=['GET', 'POST'])
@login_required
@permission_required('inventory', 'can_add')
def adjustments():
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        warehouse_id = int(request.form['warehouse_id'])
        actual_qty = float(request.form['actual_qty'])
        reason = request.form.get('reason', '')
        date = request.form['date']

        before = get_stock(item_id, warehouse_id)
        diff = actual_qty - before
        number = next_number('ADJ', 'stock_adjustments')

        adj_id = execute('''INSERT INTO stock_adjustments
            (number, date, item_id, warehouse_id, qty_before, qty_after, difference, reason, created_by)
            VALUES (?,?,?,?,?,?,?,?,?)''',
            (number, date, item_id, warehouse_id, before, actual_qty, diff, reason, session['user_id']))

        cost = get_item_cost(item_id)
        if diff != 0:
            move_stock(item_id, warehouse_id, 'in' if diff > 0 else 'out', abs(diff), unit_cost=cost,
                      ref_type='stock_adjustment', ref_id=adj_id, notes=f'تسوية جرد {number}')
            value = abs(diff) * cost
            if value > 0:
                if diff > 0:
                    lines = [{'account_id': get_account_id(ACC_INVENTORY), 'debit': value, 'credit': 0},
                             {'account_id': get_account_id(ACC_OTHER_REVENUE), 'debit': 0, 'credit': value}]
                else:
                    lines = [{'account_id': get_account_id(ACC_EXPENSE), 'debit': value, 'credit': 0},
                             {'account_id': get_account_id(ACC_INVENTORY), 'debit': 0, 'credit': value}]
                create_journal_entry(date, f'تسوية جرد رقم {number}', lines, 'stock_adjustment', adj_id, session['user_id'])

        flash(f'تم تسجيل التسوية {number}', 'success')
        return redirect(url_for('inventory.adjustments'))

    items = query('SELECT * FROM items WHERE is_active=1')
    warehouses = query('SELECT * FROM warehouses WHERE is_active=1')
    history = query('''SELECT a.*, i.name as item_name, w.name as warehouse_name FROM stock_adjustments a
                        JOIN items i ON i.id=a.item_id JOIN warehouses w ON w.id=a.warehouse_id
                        ORDER BY a.id DESC LIMIT 50''')
    from datetime import date as dt
    return render_template('inventory/adjustments.html', items=items, warehouses=warehouses,
                           history=history, today=dt.today().isoformat())


# ==================== التحويلات بين المستودعات ====================
@bp.route('/transfers', methods=['GET', 'POST'])
@login_required
@permission_required('inventory', 'can_add')
def transfers():
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        from_wh = int(request.form['from_warehouse'])
        to_wh = int(request.form['to_warehouse'])
        qty = float(request.form['quantity'])
        date = request.form['date']

        if from_wh == to_wh:
            flash('لا يمكن التحويل لنفس المستودع', 'danger')
            return redirect(url_for('inventory.transfers'))

        number = next_number('TRF', 'stock_transfers')
        transfer_id = execute('''INSERT INTO stock_transfers
            (number, date, item_id, from_warehouse, to_warehouse, quantity, created_by)
            VALUES (?,?,?,?,?,?,?)''', (number, date, item_id, from_wh, to_wh, qty, session['user_id']))

        cost = get_item_cost(item_id)
        move_stock(item_id, from_wh, 'out', qty, ref_type='stock_transfer', ref_id=transfer_id, notes=f'تحويل {number}')
        move_stock(item_id, to_wh, 'in', qty, unit_cost=cost, ref_type='stock_transfer', ref_id=transfer_id, notes=f'تحويل {number}')

        flash(f'تم تحويل المخزون {number}', 'success')
        return redirect(url_for('inventory.transfers'))

    items = query('SELECT * FROM items WHERE is_active=1')
    warehouses = query('SELECT * FROM warehouses WHERE is_active=1')
    history = query('''SELECT t.*, i.name as item_name, w1.name as from_name, w2.name as to_name
                        FROM stock_transfers t JOIN items i ON i.id=t.item_id
                        JOIN warehouses w1 ON w1.id=t.from_warehouse JOIN warehouses w2 ON w2.id=t.to_warehouse
                        ORDER BY t.id DESC LIMIT 50''')
    from datetime import date as dt
    return render_template('inventory/transfers.html', items=items, warehouses=warehouses,
                           history=history, today=dt.today().isoformat())
