# -*- coding: utf-8 -*-
from functools import wraps
from flask import session, redirect, url_for, flash, request
from core.db import query, execute
import hashlib


def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password, hashed):
    return hash_password(password) == hashed


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return wrapper


def permission_required(module, action='can_view'):
    """action: can_view / can_add / can_edit / can_delete"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login', next=request.path))
            if session.get('role_name') == 'مدير النظام':
                return f(*args, **kwargs)
            row = query(
                f'SELECT {action} as allowed FROM permissions WHERE role_id=? AND module=?',
                (session.get('role_id'), module), one=True
            )
            if not row or not row['allowed']:
                flash('ليست لديك صلاحية للوصول إلى هذه الشاشة', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


def log_action(action, table_name, record_id, details=''):
    execute(
        'INSERT INTO audit_log (user_id, username, action, table_name, record_id, details) VALUES (?,?,?,?,?,?)',
        (session.get('user_id'), session.get('username'), action, table_name, record_id, details)
    )
