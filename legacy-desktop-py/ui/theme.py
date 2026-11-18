# -*- coding: utf-8 -*-
"""
موتور تم‌های پویا و زنده:
- چند تم پیش‌فرض زیبا + شخصی‌سازی کامل توسط کاربر:
  رنگ تاکیدی، رنگ پس‌زمینه، رنگ متن، فونت، اندازه فونت، رنگ پس‌زمینه گزارش‌ها، عکس پس‌زمینه
- ذخیره تنظیمات تم در دیتابیس و اعمال QSS به کل برنامه
"""
import os
from PySide6.QtGui import QFont, QPixmap, QBrush, QPalette, QColor
from PySide6.QtWidgets import QApplication

PRESET_THEMES = {
    'آبی اقیانوس':  {'accent': '#2563eb', 'accent2': '#0ea5e9', 'bg': '#f1f5f9', 'panel': '#ffffff', 'text': '#0f172a', 'sidebar': '#0f2557'},
    'سبز زمرد':     {'accent': '#059669', 'accent2': '#10b981', 'bg': '#f0fdf4', 'panel': '#ffffff', 'text': '#052e16', 'sidebar': '#064e3b'},
    'بنفش مدرن':    {'accent': '#7c3aed', 'accent2': '#a855f7', 'bg': '#faf5ff', 'panel': '#ffffff', 'text': '#2e1065', 'sidebar': '#3b0764'},
    'نارنجی غروب':  {'accent': '#ea580c', 'accent2': '#f59e0b', 'bg': '#fff7ed', 'panel': '#ffffff', 'text': '#431407', 'sidebar': '#7c2d12'},
    'شب کربنی':     {'accent': '#38bdf8', 'accent2': '#818cf8', 'bg': '#0b1220', 'panel': '#111a2e', 'text': '#e2e8f0', 'sidebar': '#060b16'},
    'طلایی سلطنتی': {'accent': '#b45309', 'accent2': '#d97706', 'bg': '#fffbeb', 'panel': '#fffdf5', 'text': '#292524', 'sidebar': '#451a03'},
}

PERSIAN_FONTS = ['Vazirmatn', 'IRANSans', 'B Nazanin', 'Tahoma', 'Segoe UI', 'Noto Sans Arabic']


class ThemeManager:
    def __init__(self, db):
        self.db = db
        self.app = None

    def _get(self, key, default=''):
        cur = self.db.conn.execute("SELECT value FROM fy_settings WHERE key=? AND fiscal_year_id=0", (key,))
        row = cur.fetchone()
        return row['value'] if row else default

    def _set(self, key, value):
        self.db.conn.execute(
            "INSERT OR REPLACE INTO fy_settings(fiscal_year_id,key,value) VALUES(0,?,?)", (key, str(value)))
        self.db.conn.commit()

    def current(self):
        name = self._get('theme_name', 'آبی اقیانوس')
        theme = dict(PRESET_THEMES.get(name, PRESET_THEMES['آبی اقیانوس']))
        # شخصی‌سازی‌های کاربر
        for k, dflt in [('theme_accent', theme['accent']), ('theme_bg', theme['bg']),
                        ('theme_text', theme['text']), ('theme_panel', theme['panel']),
                        ('theme_sidebar', theme['sidebar']), ('theme_font', 'Vazirmatn'),
                        ('theme_font_size', '10'), ('theme_report_bg', '#ffffff'),
                        ('theme_bg_image', ''), ('theme_bg_opacity', '12')]:
            v = self._get(k, '')
            if v:
                key = k.replace('theme_', '')
                theme[key if key != 'font' else 'font'] = v
                if key == 'font_size':
                    theme['font_size'] = v
                if key == 'report_bg':
                    theme['report_bg'] = v
                if key == 'bg_image':
                    theme['bg_image'] = v
                if key == 'bg_opacity':
                    theme['bg_opacity'] = v
        return theme

    def set_preset(self, name):
        self._set('theme_name', name)
        t = PRESET_THEMES[name]
        for k, v in [('theme_accent', t['accent']), ('theme_bg', t['bg']),
                     ('theme_text', t['text']), ('theme_panel', t['panel']),
                     ('theme_sidebar', t['sidebar'])]:
            self._set(k, v)

    def set_custom(self, **kwargs):
        for k, v in kwargs.items():
            self._set('theme_' + k, v)

    # ---------------- ساخت QSS ----------------
    def build_qss(self, theme):
        accent, accent2 = theme['accent'], theme['accent2']
        bg, panel, text = theme['bg'], theme['panel'], theme['text']
        sidebar = theme['sidebar']
        fs = theme.get('font_size', '10')
        fam = theme.get('font', 'Vazirmatn')
        return f"""
* {{ font-family: '{fam}', 'Tahoma'; font-size: {fs}pt; color: {text}; }}
QMainWindow, QDialog {{ background: {bg}; }}
QStackedWidget {{ background: {bg}; }}

/* سایدبار */
#Sidebar {{ background: {sidebar}; border: none; }}
#Sidebar QLabel {{ color: #ffffff; }}
#AppTitle {{ color: #ffffff; font-size: 13pt; font-weight: bold; }}
#NavButton {{
    background: transparent; color: #cbd5e1; text-align: right; padding: 9px 14px;
    border: none; border-radius: 8px; margin: 2px 8px; font-size: {fs}pt;
}}
#NavButton:hover {{ background: rgba(255,255,255,0.12); color: white; }}
#NavButton:checked {{ background: {accent}; color: white; font-weight: bold; }}
#VersionLabel {{ color: #64748b; font-size: 8pt; }}

/* کارت‌ها و پنل‌ها */
#Card, #Panel {{ background: {panel}; border: 1px solid rgba(100,116,139,0.25);
                  border-radius: 12px; padding: 12px; }}
#CardTitle {{ font-size: 12pt; font-weight: bold; color: {accent}; }}
#StatValue {{ font-size: 16pt; font-weight: bold; color: {accent}; }}
#PageTitle {{ font-size: 15pt; font-weight: bold; }}

/* دکمه‌ها */
QPushButton {{
    background: {panel}; border: 1px solid rgba(100,116,139,0.35); border-radius: 8px;
    padding: 7px 16px; color: {text};
}}
QPushButton:hover {{ border-color: {accent}; color: {accent}; }}
QPushButton:pressed {{ background: {bg}; }}
#PrimaryBtn {{ background: {accent}; color: white; border: none; font-weight: bold; }}
#PrimaryBtn:hover {{ background: {accent2}; color: white; }}
#DangerBtn {{ background: #dc2626; color: white; border: none; }}
#DangerBtn:hover {{ background: #ef4444; }}
#GhostBtn {{ background: transparent; border: 1px solid {accent}; color: {accent}; }}
QPushButton:disabled {{ color: #94a3b8; border-color: rgba(100,116,139,0.2); }}

/* ورودی‌ها */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit, QPlainTextEdit {{
    background: {panel}; border: 1.5px solid rgba(100,116,139,0.4); border-radius: 8px;
    padding: 6px 10px; selection-background-color: {accent};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
    border-color: {accent};
}}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent;
    border-right: 5px solid transparent; border-top: 6px solid {accent}; margin-right: 8px; }}
QComboBox QAbstractItemView {{ background: {panel}; border: 1px solid {accent};
    selection-background-color: {accent}; selection-color: white; }}

/* جدول‌ها */
QTableWidget, QTableView {{
    background: {panel}; alternate-background-color: rgba(100,116,139,0.04);
    border: 1px solid rgba(100,116,139,0.3); border-radius: 10px; gridline-color: rgba(100,116,139,0.2);
    selection-background-color: {accent}; selection-color: white;
}}
QHeaderView::section {{
    background: {sidebar}; color: white; padding: 7px 6px; border: none;
    border-left: 1px solid rgba(255,255,255,0.08); font-weight: bold;
}}
QTableCornerButton::section {{ background: {sidebar}; border: none; }}

/* نوارهای اسکرول */
QScrollBar:vertical {{ background: {bg}; width: 10px; border-radius: 5px; }}
QScrollBar::handle:vertical {{ background: rgba(100,116,139,0.5); border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {accent}; }}
QScrollBar:horizontal {{ background: {bg}; height: 10px; border-radius: 5px; }}
QScrollBar::handle:horizontal {{ background: rgba(100,116,139,0.5); border-radius: 5px; min-width: 30px; }}

/* تب‌ها */
QTabWidget::pane {{ border: 1px solid rgba(100,116,139,0.3); border-radius: 10px; background: {panel}; }}
QTabBar::tab {{ background: {bg}; padding: 8px 18px; border-top-right-radius: 8px;
    border-top-left-radius: 8px; margin-left: 3px; }}
QTabBar::tab:selected {{ background: {accent}; color: white; font-weight: bold; }}

/* منو، تقویم پاپ‌آپ، چک باکس */
QMenu {{ background: {panel}; border: 1px solid {accent}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 6px 24px; border-radius: 6px; }}
QMenu::item:selected {{ background: {accent}; color: white; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; }}
QGroupBox {{ border: 1px solid rgba(100,116,139,0.35); border-radius: 10px;
    margin-top: 12px; padding-top: 6px; background: {panel}; }}
QGroupBox::title {{ color: {accent}; font-weight: bold; subcontrol-origin: margin; right: 12px; }}
QProgressBar {{ border: none; background: rgba(100,116,139,0.2); border-radius: 6px; height: 12px; }}
QProgressBar::chunk {{ background: {accent}; border-radius: 6px; }}
QStatusBar {{ background: {panel}; color: {text}; }}
        """

    def apply(self, app, bg_image_path=None):
        self.app = app
        theme = self.current()
        app.setStyleSheet(self.build_qss(theme))
        if bg_image_path and os.path.exists(bg_image_path):
            palette = QPalette()
            pix = QPixmap(bg_image_path)
            if not pix.isNull():
                palette.setBrush(QPalette.ColorRole.Window, QBrush(pix))
                app.setPalette(palette)
        else:
            app.setPalette(QPalette())
            app.setPalette(QPalette(QColor(theme['bg'])))
        # فونت
        fam = theme.get('font', 'Vazirmatn')
        size = float(theme.get('font_size', 10) or 10)
        font = QFont(fam, int(size))
        font.setStyleHint(QFont.StyleHint.SansSerif)
        app.setFont(font)
