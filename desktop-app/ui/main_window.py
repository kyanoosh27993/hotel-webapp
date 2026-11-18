# -*- coding: utf-8 -*-
"""پنجره اصلی: لاگین، سایدبار ماژول‌ها، داشبورد مدیریتی، انتخاب شرکت/سال مالی"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QStackedWidget, QComboBox, QMessageBox,
                               QDialog, QLineEdit, QFrame, QGridLayout, QApplication,
                               QDialogButtonBox, QToolButton, QSizePolicy, QTableWidget)
from core.numbers import to_persian_digits, format_money
from core import jalali as J
from core.db import APP_VERSION
from .theme import ThemeManager
from .widgets import setup_rtl_table, fill_table, JalaliMonthPicker
from .help import show_help, install_f1

APP_TITLE = 'سیستم جامع حضور و غیاب و حقوق و دستمزد'


class LoginDialog(QDialog):
    def __init__(self, auth):
        super().__init__()
        self.auth = auth
        self.user = None
        self.setWindowTitle('ورود به سیستم')
        self.setFixedSize(400, 280)
        v = QVBoxLayout(self)
        logo = QLabel('🔐')
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet('font-size:42pt;')
        v.addWidget(logo)
        t = QLabel(APP_TITLE)
        t.setObjectName('CardTitle')
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(t)
        v.addSpacing(10)
        self.un = QLineEdit()
        self.un.setPlaceholderText('نام کاربری')
        self.pw = QLineEdit()
        self.pw.setPlaceholderText('رمز عبور')
        self.pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw.returnPressed.connect(self.try_login)
        v.addWidget(self.un)
        v.addWidget(self.pw)
        btn = QPushButton('ورود')
        btn.setObjectName('PrimaryBtn')
        btn.clicked.connect(self.try_login)
        v.addWidget(btn)
        self.msg = QLabel('')
        self.msg.setStyleSheet('color:#dc2626;')
        self.msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.msg)

    def try_login(self):
        res = self.auth.login(self.un.text(), self.pw.text())
        if res and 'error' not in res:
            self.user = res
            self.accept()
        elif res and 'error' in res:
            self.msg.setText(res['error'])
        else:
            self.msg.setText('نام کاربری یا رمز عبور اشتباه است')


class StatCard(QFrame):
    def __init__(self, title, value=''):
        super().__init__()
        self.setObjectName('Card')
        v = QVBoxLayout(self)
        self.t = QLabel(title)
        self.t.setObjectName('CardTitle')
        self.v = QLabel(value)
        self.v.setObjectName('StatValue')
        v.addWidget(self.t)
        v.addWidget(self.v)

    def set(self, value):
        self.v.setText(value)


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(APP_TITLE)
        self.resize(1280, 780)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._build_sidebar()
        self._build_pages()
        self._build_dashboard()
        self._nav('داشبورد')

    # ---------------- سایدبار ----------------
    def _build_sidebar(self):
        central = QWidget()
        self.setCentralWidget(central)
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        side = QFrame()
        side.setObjectName('Sidebar')
        side.setFixedWidth(230)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(8, 16, 8, 12)
        title = QLabel('💼 ' + APP_TITLE.split(' ')[2])
        title.setObjectName('AppTitle')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sv.addWidget(title)
        sub = QLabel('حضور و غیاب • حقوق و دستمزد')
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet('color:#94a3b8; font-size:8pt;')
        sv.addWidget(sub)
        sv.addSpacing(14)
        self.navs = {}
        for key, label, icon in [
                ('داشبورد', 'داشبورد مدیریتی', '📊'),
                ('پرسنل', 'پرسنل و قراردادها', '👤'),
                ('احکام', 'احکام پرسنلی', '📜'),
                ('حضور', 'حضور و غیاب', '⏱'),
                ('حقوق', 'حقوق و دستمزد', '💰'),
                ('تقویم', 'تقویم و تعطیلات', '📅'),
                ('اطلاعات اصلی', 'اطلاعات اصلی برنامه', '⚙'),
                ('گزارش‌ساز', 'گزارش‌ساز حرفه‌ای', '📈'),
                ('مدیریت', 'مدیریت سیستم', '🛠')]:
            b = QPushButton(f'{icon}  {label}')
            b.setObjectName('NavButton')
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, k=key: self._nav(k))
            sv.addWidget(b)
            self.navs[key] = b
        sv.addStretch(1)
        # انتخاب شرکت و سال مالی
        sv.addWidget(QLabel('شرکت جاری:'))
        self.company_combo = QComboBox()
        self.company_combo.currentIndexChanged.connect(self._on_company)
        sv.addWidget(self.company_combo)
        sv.addWidget(QLabel('سال مالی:'))
        self.fy_combo = QComboBox()
        self.fy_combo.currentIndexChanged.connect(self._on_fy)
        sv.addWidget(self.fy_combo)
        ver = QLabel(f'نسخه {to_persian_digits(APP_VERSION)}')
        ver.setObjectName('VersionLabel')
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sv.addWidget(ver)
        b_help = QPushButton('❓ راهنمای کامل برنامه')
        b_help.setObjectName('GhostBtn')
        b_help.setCursor(Qt.CursorShape.PointingHandCursor)
        b_help.clicked.connect(self.show_full_help)
        sv.addWidget(b_help)
        h.addWidget(side)
        self.content = QStackedWidget()
        h.addWidget(self.content, 1)

    def _build_pages(self):
        from .pages_people import PersonnelPage, DecreesPage
        from .pages_attendance import AttendancePage
        from .pages_payroll import PayrollPage
        from .pages_settings import CoreSettingsPage
        from .pages_admin import AdminPage
        from .pages_calendar import CalendarPage
        from .pages_reports import ReportsPage
        from core.context import AppContext
        gate = self.ctx.auth  # کنترل دسترسی
        from core.security import RoleGate
        self.gate = RoleGate(self.ctx.auth)
        self.pages = {}
        self.dashboard = QWidget()
        self.content.addWidget(self.dashboard)
        self.pages['پرسنل'] = PersonnelPage(self.ctx, self.gate)
        self.pages['احکام'] = DecreesPage(self.ctx, self.gate)
        self.pages['حضور'] = AttendancePage(self.ctx, self.gate)
        self.pages['حقوق'] = PayrollPage(self.ctx, self.gate)
        self.pages['تقویم'] = CalendarPage(self.ctx, self.gate)
        self.pages['اطلاعات اصلی'] = CoreSettingsPage(self.ctx, self.gate)
        self.pages['گزارش‌ساز'] = ReportsPage(self.ctx, self.gate)
        self.pages['مدیریت'] = AdminPage(self.ctx, self.gate, self.ctx.theme_mgr, self)
        for k, p in self.pages.items():
            self.content.addWidget(p)
            install_f1(p, k)

    def show_full_help(self):
        show_help(self, 'راهنمای_کامل')

    def app_instance(self):
        return QApplication.instance()

    def reapply_theme(self):
        bg = self.ctx.theme_mgr.current().get('bg_image', '')
        self.ctx.theme_mgr.apply(QApplication.instance(), bg)

    # ---------------- داشبورد ----------------
    def _build_dashboard(self):
        from .pages_reports import REPORT_VIEWS
        self.ctx.db.conn.executescript(REPORT_VIEWS)
        v = QVBoxLayout(self.dashboard)
        v.setContentsMargins(20, 16, 20, 16)
        head = QHBoxLayout()
        self.welcome = QLabel('')
        self.welcome.setObjectName('PageTitle')
        head.addWidget(self.welcome)
        head.addStretch(1)
        b_att = QPushButton('📥 ایمپورت سریع حضور و غیاب')
        b_att.setObjectName('PrimaryBtn')
        b_att.clicked.connect(lambda: self._nav('حضور'))
        b_pay = QPushButton('⚡ محاسبه حقوق ماه')
        b_pay.clicked.connect(lambda: self._nav('حقوق'))
        head.addWidget(b_att)
        head.addWidget(b_pay)
        v.addLayout(head)
        self.date_label = QLabel('')
        v.addWidget(self.date_label)
        grid = QGridLayout()
        self.cards = {}
        defs = [('تعداد شرکت‌ها', 'companies'), ('پرسنل فعال', 'personnel'),
                ('دوره‌های محاسبه‌شده', 'periods'), ('آخرین جمع قابل پرداخت', 'net'),
                ('کل بیمه ماه آخر', 'ins'), ('کل مالیات ماه آخر', 'tax')]
        for i, (t, k) in enumerate(defs):
            c = StatCard(t)
            self.cards[k] = c
            grid.addWidget(c, i // 3, i % 3)
        v.addLayout(grid)
        v.addWidget(QLabel('آخرین دوره محاسبه‌شده — جدول قابل پرداخت:'))
        self.table = QTableWidget()
        setup_rtl_table(self.table, ['پرسنل', 'کد', 'کارکرد', 'جمع درآمد', 'کسورات', 'قابل پرداخت'])
        v.addWidget(self.table, 1)
        self.ctx.companyChanged.connect(self.refresh_dashboard)
        self.ctx.dataChanged.connect(self.refresh_dashboard)
        self.refresh_dashboard()

    def refresh_dashboard(self):
        t = J.today_jalali()
        self.date_label.setText(f"امروز: {J.weekday_name(t.year, t.month, t.day)} "
                                f"{to_persian_digits(J.format_jalali(t.year, t.month, t.day))}")
        db = self.ctx.db
        if self.ctx.auth.current_user:
            u = self.ctx.auth.current_user
            self.welcome.setText(f"خوش آمدید، {u['full_name'] or u['username']}")
        cur = db.conn.execute("SELECT COUNT(*) c FROM companies")
        self.cards['companies'].set(to_persian_digits(str(cur.fetchone()['c'])))
        cur = db.conn.execute("SELECT COUNT(*) c FROM personnel WHERE status='شاغل'")
        self.cards['personnel'].set(to_persian_digits(str(cur.fetchone()['c'])))
        cur = db.conn.execute("""SELECT COUNT(*) c FROM payroll_periods pp
                                 JOIN fiscal_years fy ON fy.id=pp.fiscal_year_id
                                 WHERE fy.company_id=?""", (self.ctx.company_id or 0,))
        self.cards['periods'].set(to_persian_digits(str(cur.fetchone()['c'])))
        cur = db.conn.execute("""
            SELECT pp.jy, pp.jm, SUM(s.net_pay) net, SUM(s.worker_ins+s.employer_ins+s.unemployment_ins) ins,
                   SUM(s.tax) tax
            FROM payroll_periods pp
            JOIN fiscal_years fy ON fy.id=pp.fiscal_year_id
            JOIN payroll_summary s ON s.period_id=pp.id
            WHERE fy.company_id=?
            GROUP BY pp.id ORDER BY pp.jy DESC, pp.jm DESC LIMIT 1""", (self.ctx.company_id or 0,))
        row = cur.fetchone()
        if row:
            self.cards['net'].set(format_money(row['net'] or 0))
            self.cards['ins'].set(format_money(row['ins'] or 0))
            self.cards['tax'].set(format_money(row['tax'] or 0))
            cur = db.conn.execute("""
                SELECT s.*, p.first_name, p.last_name, p.personnel_code FROM payroll_summary s
                JOIN personnel p ON p.id=s.personnel_id
                JOIN payroll_periods pp ON pp.id=s.period_id
                JOIN fiscal_years fy ON fy.id=pp.fiscal_year_id
                WHERE fy.company_id=? AND pp.jy=? AND pp.jm=?
                ORDER BY s.net_pay DESC LIMIT 12""", (self.ctx.company_id or 0, row['jy'], row['jm']))
            rows = [dict(r) for r in cur.fetchall()]
            fill_table(self.table, [[f"{r['first_name']} {r['last_name']}",
                                     to_persian_digits(str(r['personnel_code'])),
                                     to_persian_digits(f"{r['worked_days']:g}"),
                                     r['gross'], r['total_deductions'], r['net_pay']] for r in rows],
                       formats={3: 'money', 4: 'money', 5: 'money'})
        else:
            for k in ('net', 'ins', 'tax'):
                self.cards[k].set('—')
            fill_table(self.table, [])

    # ---------------- ناوبری ----------------
    def _nav(self, key):
        for k, b in self.navs.items():
            b.setChecked(k == key)
        if key == 'داشبورد':
            self.refresh_dashboard()
            self.content.setCurrentWidget(self.dashboard)
        else:
            page = self.pages.get(key)
            if page:
                if hasattr(page, 'refresh'):
                    try:
                        page.refresh()
                    except Exception:
                        pass
                self.content.setCurrentWidget(page)

    def _on_company(self, idx):
        cid = self.company_combo.currentData()
        if cid and cid != self.ctx.company_id:
            self.ctx.set_company(cid)
            self._load_fy_combo()

    def _on_fy(self, idx):
        fy = self.fy_combo.currentData()
        if fy and fy != self.ctx.fy_id:
            self.ctx.set_fiscal_year(fy)

    def _load_fy_combo(self):
        self.fy_combo.blockSignals(True)
        self.fy_combo.clear()
        for f in self.ctx.fiscal_years():
            self.fy_combo.addItem(f"title or 'سال مالی ' + to_persian_digits(str(f['jy']))", f['id'])
        self.fy_combo.blockSignals(False)

    def load_companies(self):
        self.company_combo.blockSignals(True)
        self.company_combo.clear()
        for c in self.ctx.load_companies():
            self.company_combo.addItem(c['name'], c['id'])
        self.company_combo.blockSignals(False)
        self._load_fy_combo()

    def closeEvent(self, e):
        self.ctx.auth.logout()
        e.accept()
