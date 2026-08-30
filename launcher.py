"""
مشغّل النظام كتطبيق سطح مكتب:
يشغّل خادم Flask في الخلفية ثم يفتح المتصفح الافتراضي تلقائياً.
هذا هو الملف الذي يُحوَّل إلى exe عبر PyInstaller.
"""
import os
import sys
import threading
import time
import webbrowser

# دعم تشغيل الملف سواء من المصدر أو من داخل حزمة PyInstaller (exe)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    RUNTIME_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RUNTIME_DIR = BASE_DIR

sys.path.insert(0, BASE_DIR)
os.chdir(RUNTIME_DIR)  # قاعدة البيانات erp.db تُنشأ بجانب البرنامج التنفيذي

from app import app

HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}"


def open_browser():
    time.sleep(1.5)
    webbrowser.open(URL)


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    print(f"نظام إدارة الأعمال يعمل الآن على {URL}")
    print("لا تغلق هذه النافذة أثناء استخدام النظام.")
    try:
        from waitress import serve
        serve(app, host=HOST, port=PORT)
    except ImportError:
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
