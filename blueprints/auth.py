# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from core.db import query
from core.auth import verify_password, log_action

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = query('SELECT u.*, r.name as role_name FROM users u LEFT JOIN roles r ON r.id=u.role_id WHERE username=?',
                      (username,), one=True)
        if user and user['is_active'] and verify_password(password, user['password_hash']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role_id'] = user['role_id']
            session['role_name'] = user['role_name']
            log_action('login', 'users', user['id'], 'تسجيل دخول')
            return redirect(url_for('dashboard.index'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    return render_template('login.html')


@bp.route('/logout')
def logout():
    if 'user_id' in session:
        log_action('logout', 'users', session['user_id'], 'تسجيل خروج')
    session.clear()
    return redirect(url_for('auth.login'))
