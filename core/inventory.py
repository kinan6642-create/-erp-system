# -*- coding: utf-8 -*-
"""محرك المخزون: يدير الكميات في كل مستودع ويسجل حركة كل صنف"""
from core.db import get_db, execute, query


def get_stock(item_id, warehouse_id):
    row = query('SELECT quantity FROM inventory_stock WHERE item_id=? AND warehouse_id=?',
                (item_id, warehouse_id), one=True)
    return row['quantity'] if row else 0


def get_item_cost(item_id):
    row = query('SELECT cost_price FROM items WHERE id=?', (item_id,), one=True)
    return row['cost_price'] if row else 0


def move_stock(item_id, warehouse_id, move_type, quantity, unit_cost=0, ref_type=None, ref_id=None, notes=None):
    """move_type: 'in' يزيد الكمية، 'out' ينقصها. يسجل الحركة في inventory_moves."""
    db = get_db()
    current = get_stock(item_id, warehouse_id)
    delta = quantity if move_type == 'in' else -quantity
    new_qty = current + delta

    if move_type == 'out' and new_qty < 0:
        raise ValueError('الكمية المطلوبة غير متوفرة في المخزون لهذا المستودع')

    exists = query('SELECT id FROM inventory_stock WHERE item_id=? AND warehouse_id=?',
                    (item_id, warehouse_id), one=True)
    if exists:
        db.execute('UPDATE inventory_stock SET quantity=? WHERE id=?', (new_qty, exists['id']))
    else:
        db.execute('INSERT INTO inventory_stock (item_id, warehouse_id, quantity) VALUES (?,?,?)',
                   (item_id, warehouse_id, new_qty))

    db.execute(
        'INSERT INTO inventory_moves (item_id, warehouse_id, move_type, quantity, unit_cost, ref_type, ref_id, notes) '
        'VALUES (?,?,?,?,?,?,?,?)',
        (item_id, warehouse_id, move_type, quantity, unit_cost, ref_type, ref_id, notes)
    )
    db.commit()

    # عند الشراء (in) نحدّث متوسط تكلفة الصنف بطريقة المتوسط المرجح
    if move_type == 'in' and unit_cost:
        _update_weighted_avg_cost(item_id, current, unit_cost, quantity)
    return new_qty


def _update_weighted_avg_cost(item_id, old_qty, new_unit_cost, new_qty):
    old_cost = get_item_cost(item_id)
    total_qty = old_qty + new_qty
    if total_qty <= 0:
        avg = new_unit_cost
    else:
        avg = ((old_qty * old_cost) + (new_qty * new_unit_cost)) / total_qty
    execute('UPDATE items SET cost_price=? WHERE id=?', (round(avg, 4), item_id))


def total_inventory_value():
    rows = query('''
        SELECT s.quantity, i.cost_price
        FROM inventory_stock s JOIN items i ON i.id = s.item_id
    ''')
    return round(sum((r['quantity'] or 0) * (r['cost_price'] or 0) for r in rows), 2)


def low_stock_items():
    return query('''
        SELECT i.id, i.code, i.name, i.reorder_level, COALESCE(SUM(s.quantity),0) as total_qty
        FROM items i LEFT JOIN inventory_stock s ON s.item_id = i.id
        GROUP BY i.id
        HAVING total_qty <= i.reorder_level
    ''')
