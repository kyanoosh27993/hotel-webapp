# -*- coding: utf-8 -*-
"""نقطه ورود برنامه — سیستم جامع حضور و غیاب و حقوق و دستمزد، نسخه ۰.۱.۰"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from core.db import Database
from core.security import AuthService
from core.jalali import CalendarService
from core.context import AppContext
from ui.theme import ThemeManager
from ui.main_window import MainWindow, LoginDialog


def _load_bundled_fonts(app):
    """بارگذاری فونت وزیرمتن همراه برنامه"""
    from PySide6.QtGui import QFontDatabase
    fdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'fonts')
    if os.path.isdir(fdir):
        for f in os.listdir(fdir):
            if f.lower().endswith('.ttf'):
                QFontDatabase.addApplicationFont(os.path.join(fdir, f))


def main():
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    _load_bundled_fonts(app)
    db = Database()
    db.init_schema()
    auth = AuthService(db)
    auth.ensure_admin_exists()
    cal = CalendarService(db)
    cal.seed_defaults()
    theme_mgr = ThemeManager(db)
    theme_mgr.apply(app)
    login = LoginDialog(auth)
    if not login.exec():
        return 0
    ctx = AppContext(db, auth, theme_mgr, cal)
    win = MainWindow(ctx)
    win.load_companies()
    # انتخاب اولین شرکت به‌صورت خودکار
    if ctx.company_id is None:
        comps = ctx.load_companies()
        if comps:
            ctx.set_company(comps[0]['id'])
        else:
            QMessageBox.information(win, 'شروع کار',
                                    'اول از بخش «مدیریت سیستم ← شرکت‌ها»، شرکت خود را ثبت و سال مالی بسازید.')
    win.reapply_theme()
    win.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
