# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from core.db import query, execute
from core.auth import login_required, permission_required, log_action, hash_password

bp = Blueprint('settings', __name__, url_prefix='/settings')


# ==================== الشركة ====================
@bp.route('/company', methods=['GET', 'POST'])
@login_required
@permission_required('settings')
def company():
    if request.method == 'POST':
        row = query('SELECT id FROM companies LIMIT 1', one=True)
        if row:
            execute('UPDATE companies SET name=?, address=?, phone=?, tax_number=? WHERE id=?',
                    (request.form['name'], request.form.get('address'), request.form.get('phone'),
                     request.form.get('tax_number'), row['id']))
        else:
            execute('INSERT INTO companies (name, address, phone, tax_number) VALUES (?,?,?,?)',
                    (request.form['name'], request.form.get('address'), request.form.get('phone'),
                     request.form.get('tax_number')))
        flash('تم حفظ بيانات الشركة', 'success')
        return redirect(url_for('settings.company'))
    company = query('SELECT * FROM companies LIMIT 1', one=True)
    return render_template('settings/company.html', company=company)


# ==================== الفروع ====================
@bp.route('/branches', methods=['GET', 'POST'])
@login_required
@permission_required('settings')
def branches():
    if request.method == 'POST':
        company = query('SELECT id FROM companies LIMIT 1', one=True)
        execute('INSERT INTO branches (company_id, name, address) VALUES (?,?,?)',
                (company['id'] if company else None, request.form['name'], request.form.get('address')))
        flash('تمت إضافة الفرع', 'success')
        return redirect(url_for('settings.branches'))
    items = query('SELECT * FROM branches ORDER BY id DESC')
    return render_template('settings/branches.html', items=items)


@bp.route('/branches/delete/<int:id>')
@login_required
@permission_required('settings', 'can_delete')
def delete_branch(id):
    execute('DELETE FROM branches WHERE id=?', (id,))
    flash('تم الحذف', 'success')
    return redirect(url_for('settings.branches'))


# ==================== المستودعات ====================
@bp.route('/warehouses', methods=['GET', 'POST'])
@login_required
@permission_required('settings')
def warehouses():
    if request.method == 'POST':
        execute('INSERT INTO warehouses (branch_id, name, location) VALUES (?,?,?)',
                (request.form.get('branch_id') or None, request.form['name'], request.form.get('location')))
        flash('تمت إضافة المستودع', 'success')
        return redirect(url_for('settings.warehouses'))
    items = query('''SELECT w.*, b.name as branch_name FROM warehouses w
                      LEFT JOIN branches b ON b.id = w.branch_id ORDER BY w.id DESC''')
    branches = query('SELECT * FROM branches')
    return render_template('settings/warehouses.html', items=items, branches=branches)


@bp.route('/warehouses/delete/<int:id>')
@login_required
@permission_required('settings', 'can_delete')
def delete_warehouse(id):
    execute('DELETE FROM warehouses WHERE id=?', (id,))
    flash('تم الحذف', 'success')
    return redirect(url_for('settings.warehouses'))


# ==================== المستخدمون ====================
@bp.route('/users', methods=['GET', 'POST'])
@login_required
@permission_required('users')
def users():
    if request.method == 'POST':
        execute('INSERT INTO users (username, password_hash, full_name, role_id, is_active) VALUES (?,?,?,?,1)',
                (request.form['username'], hash_password(request.form['password']),
                 request.form.get('full_name'), request.form.get('role_id')))
        log_action('add', 'users', None, f"إضافة مستخدم {request.form['username']}")
        flash('تمت إضافة المستخدم', 'success')
        return redirect(url_for('settings.users'))
    items = query('''SELECT u.*, r.name as role_name FROM users u
                      LEFT JOIN roles r ON r.id = u.role_id ORDER BY u.id DESC''')
    roles = query('SELECT * FROM roles')
    return render_template('settings/users.html', items=items, roles=roles)


@bp.route('/users/toggle/<int:id>')
@login_required
@permission_required('users', 'can_edit')
def toggle_user(id):
    u = query('SELECT is_active FROM users WHERE id=?', (id,), one=True)
    execute('UPDATE users SET is_active=? WHERE id=?', (0 if u['is_active'] else 1, id))
    flash('تم تحديث حالة المستخدم', 'success')
    return redirect(url_for('settings.users'))


# ==================== الأدوار والصلاحيات ====================
@bp.route('/roles', methods=['GET', 'POST'])
@login_required
@permission_required('users')
def roles():
    if request.method == 'POST':
        execute('INSERT INTO roles (name) VALUES (?)', (request.form['name'],))
        flash('تمت إضافة الدور', 'success')
        return redirect(url_for('settings.roles'))
    items = query('SELECT * FROM roles')
    return render_template('settings/roles.html', items=items)


MODULES = [
    ('dashboard', 'لوحة التحكم'), ('settings', 'الإعدادات'), ('masterdata', 'البيانات الأساسية'),
    ('sales', 'المبيعات'), ('purchases', 'المشتريات'), ('inventory', 'المخزون'),
    ('finance', 'المالية'), ('production', 'الإنتاج'), ('reports', 'التقارير'), ('users', 'المستخدمون'),
]


@bp.route('/roles/<int:role_id>/permissions', methods=['GET', 'POST'])
@login_required
@permission_required('users')
def role_permissions(role_id):
    role = query('SELECT * FROM roles WHERE id=?', (role_id,), one=True)
    if request.method == 'POST':
        for code, label in MODULES:
            can_view = 1 if request.form.get(f'{code}_view') else 0
            can_add = 1 if request.form.get(f'{code}_add') else 0
            can_edit = 1 if request.form.get(f'{code}_edit') else 0
            can_delete = 1 if request.form.get(f'{code}_delete') else 0
            existing = query('SELECT id FROM permissions WHERE role_id=? AND module=?', (role_id, code), one=True)
            if existing:
                execute('UPDATE permissions SET can_view=?, can_add=?, can_edit=?, can_delete=? WHERE id=?',
                        (can_view, can_add, can_edit, can_delete, existing['id']))
            else:
                execute('INSERT INTO permissions (role_id, module, can_view, can_add, can_edit, can_delete) VALUES (?,?,?,?,?,?)',
                        (role_id, code, can_view, can_add, can_edit, can_delete))
        flash('تم حفظ الصلاحيات', 'success')
        return redirect(url_for('settings.role_permissions', role_id=role_id))
    perms = {p['module']: p for p in query('SELECT * FROM permissions WHERE role_id=?', (role_id,))}
    return render_template('settings/permissions.html', role=role, perms=perms, modules=MODULES)


# ==================== السنوات المالية ====================
@bp.route('/fiscal-years', methods=['GET', 'POST'])
@login_required
@permission_required('settings')
def fiscal_years():
    if request.method == 'POST':
        execute('INSERT INTO fiscal_years (name, start_date, end_date, is_closed) VALUES (?,?,?,0)',
                (request.form['name'], request.form['start_date'], request.form['end_date']))
        flash('تمت الإضافة', 'success')
        return redirect(url_for('settings.fiscal_years'))
    items = query('SELECT * FROM fiscal_years ORDER BY id DESC')
    return render_template('settings/fiscal_years.html', items=items)


@bp.route('/fiscal-years/close/<int:id>')
@login_required
@permission_required('settings', 'can_edit')
def close_fiscal_year(id):
    execute('UPDATE fiscal_years SET is_closed=1 WHERE id=?', (id,))
    flash('تم إقفال السنة المالية', 'success')
    return redirect(url_for('settings.fiscal_years'))


# ==================== العملات ====================
@bp.route('/currencies', methods=['GET', 'POST'])
@login_required
@permission_required('settings')
def currencies():
    if request.method == 'POST':
        execute('INSERT INTO currencies (code, name, rate, is_base) VALUES (?,?,?,0)',
                (request.form['code'], request.form['name'], request.form['rate']))
        flash('تمت الإضافة', 'success')
        return redirect(url_for('settings.currencies'))
    items = query('SELECT * FROM currencies')
    return render_template('settings/currencies.html', items=items)


# ==================== الضرائب ====================
@bp.route('/taxes', methods=['GET', 'POST'])
@login_required
@permission_required('settings')
def taxes():
    if request.method == 'POST':
        execute('INSERT INTO taxes (name, rate) VALUES (?,?)',
                (request.form['name'], request.form['rate']))
        flash('تمت الإضافة', 'success')
        return redirect(url_for('settings.taxes'))
    items = query('SELECT * FROM taxes')
    return render_template('settings/taxes.html', items=items)
