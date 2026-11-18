# -*- coding: utf-8 -*-
"""اطلاعات اصلی برنامه:
- ساعات موظفی ماهانه، نرخ‌های بیمه، سقف مشمول بیمه، معافیت ماده ۸۴، ضرایب قانون کار
- جدول پله‌های مالیاتی (قابل ویرایش کامل)
- اقلام فیش حقوقی: اضافه/حذف/ویرایش + تغییر فرمول + نوع مالیات + مشمول بیمه
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QTableWidget, QDialog, QFormLayout, QComboBox, QMessageBox,
                               QGroupBox, QGridLayout, QLineEdit, QTabWidget, QHeaderView,
                               QDoubleSpinBox, QCheckBox, QFileDialog)
from core.numbers import to_persian_digits, parse_number, format_money
from core.payroll_engine import FormulaRegistry
from .widgets import setup_rtl_table, fill_table, MoneyEdit, PercentEdit


class CoreSettingsPage(QWidget):
    def __init__(self, ctx, gate):
        super().__init__()
        self.ctx = ctx
        self.gate = gate
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        title = QLabel('⚙ اطلاعات اصلی برنامه')
        title.setObjectName('PageTitle')
        v.addWidget(title)
        tabs = QTabWidget()
        v.addWidget(tabs, 1)
        tabs.addTab(self._tab_params(), 'پارامترهای محاسباتی')
        tabs.addTab(self._tab_tax(), 'جدول پله‌های مالیاتی')
        tabs.addTab(self._tab_items(), 'اقلام فیش حقوقی و فرمول‌ها')
        self.ctx.companyChanged.connect(self.refresh)
        self.refresh()

    # ---------------- پارامترها ----------------
    def _tab_params(self):
        w = QWidget()
        g = QGridLayout(w)
        g.setVerticalSpacing(10)
        self.params = {}
        defs = [
            ('monthly_required_hours', 'ساعات موظفی کارکرد ماهانه', 'مثال: ۱۷۶'),
            ('m84_monthly_exemption', 'معافیت ماهانه ماده ۸۴ (ریال)', 'مثال: ۴۰۰٬۰۰۰٬۰۰۰'),
            ('sso_worker_rate', 'نرخ بیمه سهم کارگر (٪)', 'پیش‌فرض: ۷'),
            ('sso_employer_rate', 'نرخ بیمه سهم کارفرما (٪)', 'پیش‌فرض: ۲۳'),
            ('sso_unemployment_rate', 'نرخ بیمه بیکاری - کارفرما (٪)', 'پیش‌فرض: ۳'),
            ('sso_ceiling_30d', 'سقف حقوق مشمول بیمه - ماه ۳۰ روزه (ریال)', '۱۴۰۵: ۱٬۱۶۳٬۷۸۸٬۵۰۰'),
            ('sso_ceiling_31d', 'سقف حقوق مشمول بیمه - ماه ۳۱ روزه (ریال)', ''),
            ('overtime_factor', 'ضریب اضافه‌کاری', 'قانون کار: ۱.۴'),
            ('holiday_work_factor', 'ضریب تعطیل‌کاری', 'قانون کار: ۱.۷'),
            ('friday_work_factor', 'ضریب جمعه‌کاری', 'قانون کار: ۱.۴'),
            ('night_work_percent', 'درصد مازاد شب‌کاری', 'قانون کار: ۳۵٪ (۲۲ تا ۶ صبح)'),
            ('late_grace_minutes', 'بازه مجاز تاخیر در ورود (دقیقه)', 'مثال: ۱۰ یا ۵ یا ۰ — صفر = حتی ۱ دقیقه تاخیر حساب می‌شود'),
            ('early_grace_minutes', 'بازه مجاز تعجیل در خروج (دقیقه)', 'مثال: ۱۰ یا ۵ یا ۰ — صفر = حتی ۱ دقیقه تعجیل حساب می‌شود'),
        ]
        for i, (key, label, hint) in enumerate(defs):
            row, col = i // 2, (i % 2) * 2
            g.addWidget(QLabel(label), row, col)
            ed = MoneyEdit(0)
            ed.setToolTip(hint)
            self.params[key] = ed
            g.addWidget(ed, row, col + 1)
        btn_save = QPushButton('💾 ذخیره پارامترها')
        btn_save.setObjectName('PrimaryBtn')
        btn_save.clicked.connect(self.save_params)
        g.addWidget(btn_save, (len(defs) + 1) // 2, 0, 1, 2)
        g.setColumnStretch(1, 1)
        g.setColumnStretch(3, 1)
        return w

    # ---------------- پله‌های مالیاتی ----------------
    def _tab_tax(self):
        w = QWidget()
        v = QVBoxLayout(w)
        hint = QLabel('پله‌ها بر اساس درآمد مشمول مالیات «ماهانه» (ریال) تعریف می‌شوند. سطر «تا» خالی = بی‌نهایت.')
        hint.setStyleSheet('color:#64748b;')
        v.addWidget(hint)
        bar = QHBoxLayout()
        b_add = QPushButton('➕ پله جدید')
        b_add.clicked.connect(self.add_bracket)
        b_del = QPushButton('🗑 حذف پله')
        b_del.setObjectName('DangerBtn')
        b_del.clicked.connect(self.del_bracket)
        b_save = QPushButton('💾 ذخیره تغییرات')
        b_save.setObjectName('PrimaryBtn')
        b_save.clicked.connect(self.save_brackets)
        for x in (b_add, b_del, b_save):
            bar.addWidget(x)
        bar.addStretch(1)
        v.addLayout(bar)
        self.tax_table = QTableWidget()
        setup_rtl_table(self.tax_table, ['از مبلغ (ریال)', 'تا مبلغ (ریال)', 'نرخ (٪)'], stretch_all=False)
        self.tax_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.tax_table, 1)
        return w

    # ---------------- اقلام فیش ----------------
    def _tab_items(self):
        w = QWidget()
        v = QVBoxLayout(w)
        hint = QLabel('برای هر آیتم: فرمول پیش‌فرض از قانون کار/تامین اجتماعی — می‌توانید فرمول را عوض کنید، '
                      'نوع مالیات (بدون/ماده ۸۴/مقطوع/درصد دلخواه) و مشمولیت بیمه را تعیین و آیتم جدید اضافه کنید.')
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#64748b;')
        v.addWidget(hint)
        bar = QHBoxLayout()
        b_add = QPushButton('➕ آیتم جدید')
        b_add.clicked.connect(self.add_item)
        b_edit = QPushButton('✏️ ویرایش آیتم')
        b_edit.clicked.connect(self.edit_item)
        b_del = QPushButton('🗑 حذف آیتم')
        b_del.setObjectName('DangerBtn')
        b_del.clicked.connect(self.del_item)
        for x in (b_add, b_edit, b_del):
            bar.addWidget(x)
        bar.addStretch(1)
        v.addLayout(bar)
        self.items_table = QTableWidget()
        setup_rtl_table(self.items_table, ['عنوان آیتم', 'نوع', 'فرمول محاسبه', 'مالیات', 'مشمول بیمه', 'فعال', 'ترتیب'], stretch_all=False)
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.items_table, 1)
        return w

    # ---------------- بارگذاری ----------------
    def refresh(self):
        if not self.ctx.fy_id:
            return
        for key, ed in self.params.items():
            ed.set_value(parse_number(self.ctx.fy_setting(key, ''), 0))
        self.load_brackets()
        self.load_items()

    def load_brackets(self):
        brackets = self.ctx.tax_brackets()
        self.tax_table.setRowCount(len(brackets))
        for r, b in enumerate(brackets):
            e_from = MoneyEdit(b['from_amount'])
            e_to = MoneyEdit(b['to_amount'] if b['to_amount'] is not None else 0)
            e_rate = PercentEdit(b['rate_percent'])
            e_to.setPlaceholderText('بی‌نهایت')
            self.tax_table.setCellWidget(r, 0, e_from)
            self.tax_table.setCellWidget(r, 1, e_to)
            self.tax_table.setCellWidget(r, 2, e_rate)
            self.tax_table.item(r, 0) if False else None
        self._brackets = brackets

    def load_items(self):
        cur = self.ctx.db.conn.execute("SELECT * FROM payroll_items_config ORDER BY kind, sort")
        rows = [dict(r) for r in cur.fetchall()]
        self._items = rows
        formulas = FormulaRegistry.available()
        data = []
        for r in rows:
            ftitle = dict(formulas).get(r['formula_key'], r['formula_key'])
            kind = {'earning': 'درآمد', 'deduction': 'کسر', 'employer': 'سهم کارفرما'}[r['kind']]
            tax = {'none': 'بدون مالیات', 'm84': 'ماده ۸۴ (پله‌ای)', 'lump': 'مقطوع', 'percent': 'درصد دلخواه'}[r['tax_mode']]
            data.append([r['title'], kind, ftitle, tax, 'بله' if r['insured'] else 'خیر',
                         'بله' if r['active'] else 'خیر', to_persian_digits(str(r['sort']))])
        fill_table(self.items_table, data)

    # ---------------- ذخیره ----------------
    def save_params(self):
        if not self.gate.allowed('edit'):
            return
        for key, ed in self.params.items():
            self.ctx.db.set_fy_setting(self.ctx.fy_id, key, str(ed.value()))
        QMessageBox.information(self, 'ذخیره', 'پارامترهای محاسباتی ذخیره شد')

    def save_brackets(self):
        if not self.gate.allowed('edit'):
            return
        db = self.ctx.db
        db.conn.execute("DELETE FROM tax_brackets WHERE fiscal_year_id=?", (self.ctx.fy_id,))
        for r in range(self.tax_table.rowCount()):
            e_from = self.tax_table.cellWidget(r, 0)
            e_to = self.tax_table.cellWidget(r, 1)
            e_rate = self.tax_table.cellWidget(r, 2)
            if not e_from or not e_rate:
                continue
            frm = e_from.value()
            to = e_to.value() if e_to else 0
            db.conn.execute(
                "INSERT INTO tax_brackets(fiscal_year_id,seq,from_amount,to_amount,rate_percent) VALUES(?,?,?,?,?)",
                (self.ctx.fy_id, r + 1, frm, to if to > 0 else None, e_rate.value()))
        db.conn.commit()
        QMessageBox.information(self, 'ذخیره', 'جدول مالیات ذخیره شد')

    def add_bracket(self):
        if not self.gate.allowed('edit'):
            return
        r = self.tax_table.rowCount()
        self.tax_table.insertRow(r)
        self.tax_table.setCellWidget(r, 0, MoneyEdit(0))
        self.tax_table.setCellWidget(r, 1, MoneyEdit(0))
        self.tax_table.setCellWidget(r, 2, PercentEdit(0))

    def del_bracket(self):
        if not self.gate.allowed('edit'):
            return
        r = self.tax_table.currentRow()
        if r >= 0:
            self.tax_table.removeRow(r)

    # ---------------- اقلام ----------------
    def add_item(self):
        if not self.gate.allowed('edit'):
            return
        dlg = ItemDialog(self.ctx, None)
        if dlg.exec():
            self.load_items()

    def edit_item(self):
        r = self.items_table.currentRow()
        if r < 0:
            return
        if not self.gate.allowed('edit'):
            return
        dlg = ItemDialog(self.ctx, self._items[r])
        if dlg.exec():
            self.load_items()

    def del_item(self):
        if not self.gate.allowed('edit'):
            return
        r = self.items_table.currentRow()
        if r < 0:
            return
        it = self._items[r]
        if it['system_locked']:
            QMessageBox.warning(self, 'آیتم سیستمی', 'این آیتم حذف‌شدنی نیست (در محاسبات لازم است) — فقط می‌توانید فرمول آن را تغییر دهید یا آن را غیرفعال کنید.')
            return
        if QMessageBox.question(self, 'حذف', f"حذف آیتم «{it['title']}»؟") == QMessageBox.StandardButton.Yes:
            self.ctx.db.conn.execute("DELETE FROM payroll_items_config WHERE id=?", (it['id'],))
            self.ctx.db.conn.commit()
            self.load_items()


class ItemDialog(QDialog):
    def __init__(self, ctx, item):
        super().__init__()
        self.ctx = ctx
        self.item = item
        self.setWindowTitle('آیتم فیش حقوقی')
        self.resize(520, 420)
        v = QVBoxLayout(self)
        f = QFormLayout()
        self.title = QLineEdit(item['title'] if item else '')
        self.kind = QComboBox()
        self.kind.addItems(['درآمد', 'کسر', 'سهم کارفرما'])
        self.formula = QComboBox()
        for k, t in FormulaRegistry.available():
            self.formula.addItem(t, k)
        self.tax_mode = QComboBox()
        self.tax_mode.addItems(['ماده ۸۴ (پله‌ای)', 'بدون مالیات', 'مقطوع', 'درصد دلخواه'])
        self.tax_percent = PercentEdit(0)
        self.insured = QCheckBox('مشمول بیمه تامین اجتماعی')
        self.active = QCheckBox('فعال')
        self.active.setChecked(True)
        self.sort = QLineEdit('100')
        f.addRow('عنوان آیتم *', self.title)
        f.addRow('نوع', self.kind)
        f.addRow('فرمول محاسبه', self.formula)
        f.addRow('نحوه مالیات', self.tax_mode)
        f.addRow('درصد مالیات (برای مقطوع/درصدی)', self.tax_percent)
        f.addRow('', self.insured)
        f.addRow('', self.active)
        f.addRow('ترتیب نمایش', self.sort)
        v.addLayout(f)
        bb = QHBoxLayout()
        ok = QPushButton('💾 ذخیره')
        ok.setObjectName('PrimaryBtn')
        ok.clicked.connect(self.save)
        cancel = QPushButton('انصراف')
        cancel.clicked.connect(self.reject)
        bb.addStretch(1)
        bb.addWidget(ok)
        bb.addWidget(cancel)
        v.addLayout(bb)
        if item:
            self.title.setText(item['title'])
            self.kind.setCurrentIndex({'earning': 0, 'deduction': 1, 'employer': 2}[item['kind']])
            idx = self.formula.findData(item['formula_key'])
            if idx >= 0:
                self.formula.setCurrentIndex(idx)
            self.tax_mode.setCurrentIndex({'m84': 0, 'none': 1, 'lump': 2, 'percent': 3}[item['tax_mode']])
            self.tax_percent.set_value(item['tax_percent'] or 0)
            self.insured.setChecked(bool(item['insured']))
            self.active.setChecked(bool(item['active']))
            self.sort.setText(str(item['sort']))

    def save(self):
        t = self.title.text().strip()
        if not t:
            return
        vals = {
            'title': t,
            'kind': ['earning', 'deduction', 'employer'][self.kind.currentIndex()],
            'formula_key': self.formula.currentData(),
            'tax_mode': ['m84', 'none', 'lump', 'percent'][self.tax_mode.currentIndex()],
            'tax_percent': self.tax_percent.value(),
            'insured': 1 if self.insured.isChecked() else 0,
            'active': 1 if self.active.isChecked() else 0,
            'sort': int(parse_number(self.sort.text(), 100)),
        }
        if self.item:
            sets = ', '.join(f"{k}=?" for k in vals)
            self.ctx.db.conn.execute(f"UPDATE payroll_items_config SET {sets} WHERE id=?",
                                     list(vals.values()) + [self.item['id']])
        else:
            code = 'item_' + str(int(parse_number(self.sort.text(), 100))) + '_' + t.replace(' ', '_')[:20]
            vals['code'] = code
            cols = ', '.join(vals.keys())
            ph = ', '.join('?' * len(vals))
            try:
                self.ctx.db.conn.execute(f"INSERT INTO payroll_items_config({cols}) VALUES({ph})", list(vals.values()))
            except Exception:
                import random
                vals['code'] += f"_{random.randint(100,999)}"
                cols = ', '.join(vals.keys())
                ph = ', '.join('?' * len(vals))
                self.ctx.db.conn.execute(f"INSERT INTO payroll_items_config({cols}) VALUES({ph})", list(vals.values()))
        self.ctx.db.conn.commit()
        self.accept()
