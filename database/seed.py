# -*- coding: utf-8 -*-
"""يهيئ البيانات الأولية: الدليل المحاسبي، الأدوار، المستخدم الأول، وحدات أساسية"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import init_db, execute, query, get_db, DB_PATH
from core.auth import hash_password
import sqlite3


ACCOUNTS = [
    # code, name, type, parent_code, is_control
    ('1000', 'الأصول', 'asset', None, 1),
    ('1100', 'النقدية والبنوك', 'asset', '1000', 1),
    ('1101', 'الصندوق', 'asset', '1100', 0),
    ('1102', 'البنك', 'asset', '1100', 0),
    ('1200', 'الذمم المدينة', 'asset', '1000', 1),
    ('1201', 'العملاء', 'asset', '1200', 0),
    ('1300', 'المخزون', 'asset', '1000', 1),
    ('1301', 'مخزون البضاعة', 'asset', '1300', 0),
    ('2000', 'الخصوم', 'liability', None, 1),
    ('2100', 'الذمم الدائنة', 'liability', '2000', 1),
    ('2101', 'الموردون', 'liability', '2100', 0),
    ('2102', 'ضريبة مستحقة على المبيعات', 'liability', '2100', 0),
    ('3000', 'حقوق الملكية', 'equity', None, 1),
    ('3100', 'رأس المال', 'equity', '3000', 0),
    ('3200', 'الأرباح المرحلة', 'equity', '3000', 0),
    ('4000', 'الإيرادات', 'revenue', None, 1),
    ('4100', 'إيرادات المبيعات', 'revenue', '4000', 1),
    ('4101', 'مبيعات البضاعة', 'revenue', '4100', 0),
    ('4200', 'إيرادات أخرى', 'revenue', '4000', 1),
    ('4201', 'إيرادات متنوعة', 'revenue', '4200', 0),
    ('5000', 'المصروفات', 'expense', None, 1),
    ('5100', 'تكلفة البضاعة المباعة', 'expense', '5000', 1),
    ('5101', 'تكلفة المبيعات', 'expense', '5100', 0),
    ('5200', 'المصاريف التشغيلية', 'expense', '5000', 1),
    ('5201', 'مصاريف عامة', 'expense', '5200', 0),
    ('5300', 'مصاريف أخرى', 'expense', '5000', 1),
]


def seed():
    fresh = init_db()
    db = get_db_direct()

    # ---------- الدليل المحاسبي ----------
    code_to_id = {}
    if not query_direct(db, 'SELECT COUNT(*) c FROM accounts')[0]['c']:
        for code, name, type_, parent_code, is_control in ACCOUNTS:
            parent_id = code_to_id.get(parent_code) if parent_code else None
            cur = db.execute(
                'INSERT INTO accounts (code, name, type, parent_id, is_control) VALUES (?,?,?,?,?)',
                (code, name, type_, parent_id, is_control)
            )
            code_to_id[code] = cur.lastrowid
        db.commit()

    # ---------- الأدوار ----------
    if not query_direct(db, 'SELECT COUNT(*) c FROM roles')[0]['c']:
        db.execute("INSERT INTO roles (name) VALUES ('مدير النظام')")
        db.execute("INSERT INTO roles (name) VALUES ('محاسب')")
        db.execute("INSERT INTO roles (name) VALUES ('موظف مبيعات')")
        db.execute("INSERT INTO roles (name) VALUES ('موظف مخزون')")
        db.commit()

    admin_role = query_direct(db, "SELECT id FROM roles WHERE name='مدير النظام'")[0]['id']

    # صلاحيات كاملة لكل الوحدات لكل الأدوار (مبسط، مدير النظام متجاوَز أصلاً بالكود)
    modules = ['dashboard', 'settings', 'masterdata', 'sales', 'purchases',
               'inventory', 'finance', 'production', 'reports', 'users']
    if not query_direct(db, 'SELECT COUNT(*) c FROM permissions')[0]['c']:
        roles = query_direct(db, 'SELECT id, name FROM roles')
        for r in roles:
            for m in modules:
                full = 1 if r['name'] == 'مدير النظام' else 0
                db.execute(
                    'INSERT INTO permissions (role_id, module, can_view, can_add, can_edit, can_delete) VALUES (?,?,?,?,?,?)',
                    (r['id'], m, full, full, full, full)
                )
        db.commit()

    # ---------- المستخدم الأول ----------
    if not query_direct(db, 'SELECT COUNT(*) c FROM users')[0]['c']:
        db.execute(
            'INSERT INTO users (username, password_hash, full_name, role_id, is_active) VALUES (?,?,?,?,1)',
            ('admin', hash_password('admin123'), 'مدير النظام', admin_role)
        )
        db.commit()

    # ---------- الشركة الافتراضية ----------
    if not query_direct(db, 'SELECT COUNT(*) c FROM companies')[0]['c']:
        cur = db.execute("INSERT INTO companies (name) VALUES ('شركتي')")
        company_id = cur.lastrowid
        cur = db.execute("INSERT INTO branches (company_id, name) VALUES (?, 'الفرع الرئيسي')", (company_id,))
        branch_id = cur.lastrowid
        db.execute("INSERT INTO warehouses (branch_id, name) VALUES (?, 'المستودع الرئيسي')", (branch_id,))
        db.commit()

    # ---------- العملة الأساسية ----------
    if not query_direct(db, 'SELECT COUNT(*) c FROM currencies')[0]['c']:
        db.execute("INSERT INTO currencies (code, name, rate, is_base) VALUES ('YER','ريال يمني',1,1)")
        db.commit()

    # ---------- وحدات أساسية ----------
    if not query_direct(db, 'SELECT COUNT(*) c FROM units')[0]['c']:
        for u in ['قطعة', 'كرتون', 'متر', 'كيلوجرام', 'لتر']:
            db.execute('INSERT INTO units (name) VALUES (?)', (u,))
        db.commit()

    # ---------- السنة المالية الحالية ----------
    if not query_direct(db, 'SELECT COUNT(*) c FROM fiscal_years')[0]['c']:
        db.execute("INSERT INTO fiscal_years (name, start_date, end_date, is_closed) VALUES ('2026','2026-01-01','2026-12-31',0)")
        db.commit()

    db.close()
    return fresh


def get_db_direct():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def query_direct(db, sql, args=()):
    return db.execute(sql, args).fetchall()


if __name__ == '__main__':
    seed()
    print('تمت تهيئة قاعدة البيانات بنجاح. المستخدم: admin | كلمة المرور: admin123')
