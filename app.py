# -*- coding: utf-8 -*-
import os
import sys
from flask import Flask, session, redirect, url_for
from core import db as core_db


def resource_path(relative_path):
    """يحل المسار الصحيح للموارد سواء كان التشغيل من المصدر أو من حزمة PyInstaller"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def create_app():
    app = Flask(
        __name__,
        template_folder=resource_path('templates'),
        static_folder=resource_path('static'),
    )
    app.secret_key = 'change-this-secret-key-in-production'
    app.config['JSON_AS_ASCII'] = False

    core_db.init_app(app)

    # تهيئة قاعدة البيانات إن لم تكن موجودة
    with app.app_context():
        from database.seed import seed
        seed()

    # تسجيل البلوبرنتس (الوحدات)
    from blueprints.auth import bp as auth_bp
    from blueprints.dashboard import bp as dashboard_bp
    from blueprints.settings import bp as settings_bp
    from blueprints.masterdata import bp as masterdata_bp
    from blueprints.sales import bp as sales_bp
    from blueprints.purchases import bp as purchases_bp
    from blueprints.inventory import bp as inventory_bp
    from blueprints.finance import bp as finance_bp
    from blueprints.production import bp as production_bp
    from blueprints.reports import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(masterdata_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(production_bp)
    app.register_blueprint(reports_bp)

    @app.route('/')
    def home():
        if 'user_id' in session:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))

    @app.context_processor
    def inject_globals():
        return dict(session=session)

    return app


app = create_app()

if __name__ == '__main__':
    print('=' * 60)
    print('  نظام إدارة الأعمال المتكامل ERP')
    print('  الرابط: http://127.0.0.1:5000')
    print('  المستخدم: admin  |  كلمة المرور: admin123')
    print('=' * 60)
    app.run(debug=True, host='127.0.0.1', port=5000)
