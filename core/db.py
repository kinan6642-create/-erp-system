import sqlite3
import os
import sys
from flask import g, current_app


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


if getattr(sys, 'frozen', False):
    # عند التشغيل كملف exe: قاعدة البيانات تُحفظ بجانب البرنامج التنفيذي (لتبقى بعد إعادة التشغيل)
    # بينما ملف المخطط schema.sql يُقرأ من داخل الحزمة المؤقتة (_MEIPASS)
    DB_PATH = os.path.join(os.path.dirname(sys.executable), 'erp.db')
    SCHEMA_PATH = os.path.join(sys._MEIPASS, 'database', 'schema.sql')
else:
    DB_PATH = os.path.join(_project_root(), 'erp.db')
    SCHEMA_PATH = os.path.join(_project_root(), 'database', 'schema.sql')


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def init_db():
    """ينشئ قاعدة البيانات من الصفر إن لم تكن موجودة"""
    fresh = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    return fresh


def query(sql, args=(), one=False):
    db = get_db()
    cur = db.execute(sql, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid
