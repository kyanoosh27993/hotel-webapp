# -*- coding: utf-8 -*-
"""صفحه مدیریت:
- شرکت‌ها و سال‌های مالی (بدون محدودیت تعداد)
- کاربران و نقش‌ها
- تم و شخصی‌سازی (رنگ، فونت، پس‌زمینه، عکس)
- بکاپ و ریستور + لاگ عملیات
"""
import os
import shutil
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QTableWidget, QDialog, QFormLayout, QComboBox, QMessageBox,
                               QLineEdit, QTabWidget, QColorDialog, QFontComboBox, QSpinBox,
                               QFileDialog, QGroupBox, QGridLayout, QDialogButtonBox)
from core.numbers import to_persian_digits
from .widgets import setup_rtl_table, fill_table, enable_enter_navigation
from .help import install_f1
from ui.theme import PRESET_THEMES, PERSIAN_FONTS


class AdminPage(QWidget):
    def __init__(self, ctx, gate, theme_mgr, mainwin):
        super().__init__()
        self.ctx = ctx
        self.gate = gate
        self.theme_mgr = theme_mgr
        self.mainwin = mainwin
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        title = QLabel('🛠 مدیریت سیستم')
        title.setObjectName('PageTitle')
        v.addWidget(title)
        tabs = QTabWidget()
        v.addWidget(tabs, 1)
        tabs.addTab(self._tab_companies(), '🏢 شرکت‌ها و سال مالی')
        tabs.addTab(self._tab_users(), '👥 کاربران و نقش‌ها')
        tabs.addTab(self._tab_theme(), '🎨 تم و شخصی‌سازی')
        tabs.addTab(self._tab_backup(), '💾 بکاپ و لاگ')
        install_f1(self, 'مدیریت')
        self.refresh()

    # ---------------- شرکت‌ها ----------------
    def _tab_companies(self):
        w = QWidget()
        v = QVBoxLayout(w)
        bar = QHBoxLayout()
        b_add = QPushButton('➕ شرکت جدید')
        b_add.setObjectName('PrimaryBtn')
        b_add.clicked.connect(self.add_company)
        b_add_fy = QPushButton('📅 سال مالی جدید برای شرکت انتخابی')
        b_add_fy.clicked.connect(self.add_fy)
        b_sel = QPushButton('✅ انتخاب به‌عنوان شرکت جاری')
        b_sel.clicked.connect(self.select_company)
        b_edit = QPushButton('✏️ ویرایش اطلاعات شرکت')
        b_edit.clicked.connect(self.edit_company)
        for x in (b_add, b_add_fy, b_sel, b_edit):
            bar.addWidget(x)
        bar.addStretch(1)
        v.addLayout(bar)
        self.comp_table = QTableWidget()
        setup_rtl_table(self.comp_table, ['نام شرکت', 'شناسه ملی', 'کد اقتصادی', 'کد شعبه بیمه',
                                          'کد کارگاه بیمه', 'کد پرونده مالیاتی', 'لوگو', 'سال‌های مالی'])
        v.addWidget(self.comp_table, 1)
        return w

    def refresh(self):
        cur = self.ctx.db.conn.execute("SELECT * FROM companies ORDER BY name")
        comps = [dict(r) for r in cur.fetchall()]
        self._comps = comps
        data = []
        for c in comps:
            cur = self.ctx.db.conn.execute(
                "SELECT GROUP_CONCAT(jy) as ys FROM fiscal_years WHERE company_id=?", (c['id'],))
            ys = cur.fetchone()['ys'] or ''
            data.append([c['name'], to_persian_digits(str(c['national_id'] or '')),
                         to_persian_digits(str(c['economic_code'] or '')),
                         to_persian_digits(str(c['sso_branch_code'] or '')),
                         to_persian_digits(str(c.get('sso_workshop_code') or '')),
                         to_persian_digits(str(c['tax_file_code'] or '')),
                         'دارد' if c.get('logo_path') else '—',
                         '، '.join(to_persian_digits(y) for y in ys.split(',')) if ys else ''])
        fill_table(self.comp_table, data)
        # کاربران
        users = self.ctx.auth.list_users()
        self._users = users
        if hasattr(self, 'user_table'):
            fill_table(self.user_table, [[u['username'], u['full_name'],
                                          {'admin': 'مدیر کل', 'operator': 'اپراتور', 'viewer': 'فقط مشاهده'}[u['role']],
                                          'فعال' if u['active'] else 'غیرفعال', to_persian_digits(u['created_at'])]
                                         for u in users])
        if hasattr(self, 'log_table'):
            self.load_log()

    def _selected_company(self):
        r = self.comp_table.currentRow()
        return self._comps[r] if getattr(self, '_comps', None) and 0 <= r < len(self._comps) else None

    def add_company(self):
        if not self.gate.allowed('admin'):
            QMessageBox.warning(self, 'دسترسی', 'فقط مدیر کل')
            return
        dlg = CompanyDialog(self.ctx)
        if dlg.exec():
            self.refresh()

    def edit_company(self):
        c = self._selected_company()
        if not c:
            return
        if not self.gate.allowed('admin'):
            return
        dlg = CompanyDialog(self.ctx, c)
        if dlg.exec():
            self.refresh()

    def add_fy(self):
        c = self._selected_company()
        if not c:
            QMessageBox.information(self, 'انتخاب', 'یک شرکت را انتخاب کنید')
            return
        if not self.gate.allowed('admin'):
            return
        years, ok = QYearsDialog.get(self)
        if not ok:
            return
        import jdatetime
        for y in years:
            self.ctx.db.conn.execute(
                "INSERT OR IGNORE INTO fiscal_years(company_id,jy,title) VALUES(?,?,?)",
                (c['id'], y, f'سال مالی {to_persian_digits(str(y))}'))
            cur = self.ctx.db.conn.execute(
                "SELECT id FROM fiscal_years WHERE company_id=? AND jy=?", (c['id'], y))
            fy = cur.fetchone()['id']
            self.ctx.db.ensure_fy_settings(fy)
        self.ctx.db.conn.commit()
        self.refresh()

    def select_company(self):
        c = self._selected_company()
        if not c:
            return
        self.ctx.set_company(c['id'])
        QMessageBox.information(self, 'شرکت جاری', f"«{c['name']}» انتخاب شد")

    # ---------------- کاربران ----------------
    def _tab_users(self):
        w = QWidget()
        v = QVBoxLayout(w)
        bar = QHBoxLayout()
        b_add = QPushButton('➕ کاربر جدید')
        b_add.setObjectName('PrimaryBtn')
        b_add.clicked.connect(self.add_user)
        b_pass = QPushButton('🔑 تغییر رمز')
        b_pass.clicked.connect(self.change_pass)
        b_role = QPushButton('🎭 تغییر نقش')
        b_role.clicked.connect(self.change_role)
        b_act = QPushButton('فعال/غیرفعال')
        b_act.clicked.connect(self.toggle_user)
        for x in (b_add, b_pass, b_role, b_act):
            bar.addWidget(x)
        bar.addStretch(1)
        v.addLayout(bar)
        self.user_table = QTableWidget()
        setup_rtl_table(self.user_table, ['نام کاربری', 'نام کامل', 'نقش', 'وضعیت', 'تاریخ ایجاد'])
        v.addWidget(self.user_table, 1)
        return w

    def _selected_user(self):
        r = self.user_table.currentRow()
        return self._users[r] if getattr(self, '_users', None) and 0 <= r < len(self._users) else None

    def add_user(self):
        if not self.gate.allowed('admin'):
            return
        dlg = QDialog(self)
        dlg.setWindowTitle('کاربر جدید')
        f = QFormLayout()
        un = QLineEdit()
        fn = QLineEdit()
        pw = QLineEdit(); pw.setEchoMode(QLineEdit.EchoMode.Password)
        role = QComboBox(); role.addItems(['اپراتور', 'فقط مشاهده', 'مدیر کل'])
        f.addRow('نام کاربری *', un)
        f.addRow('نام کامل', fn)
        f.addRow('رمز عبور *', pw)
        f.addRow('نقش', role)
        dlg.setLayout(f)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec():
            try:
                role_map = {'اپراتور': 'operator', 'فقط مشاهده': 'viewer', 'مدیر کل': 'admin'}
                self.ctx.auth.create_user(un.text(), pw.text(), fn.text(), role_map[role.currentText()])
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, 'خطا', 'نام کاربری تکراری است')

    def change_pass(self):
        u = self._selected_user()
        if not u or not self.gate.allowed('admin'):
            return
        text, ok = QNewPassDialog.get(self)
        if ok and text:
            self.ctx.auth.change_password(u['id'], text)
            QMessageBox.information(self, 'انجام شد', 'رمز عبور تغییر کرد')

    def change_role(self):
        u = self._selected_user()
        if not u or not self.gate.allowed('admin'):
            return
        roles = ['اپراتور', 'فقط مشاهده', 'مدیر کل']
        role_map = {'اپراتور': 'operator', 'فقط مشاهده': 'viewer', 'مدیر کل': 'admin'}
        item, ok = QInputDialog_getItem(self, 'تغییر نقش', f"نقش جدید برای {u['username']}:", roles)
        if ok and item:
            self.ctx.auth.set_role(u['id'], role_map[item])
            self.refresh()

    def toggle_user(self):
        u = self._selected_user()
        if not u or not self.gate.allowed('admin'):
            return
        self.ctx.auth.set_active(u['id'], 0 if u['active'] else 1)
        self.refresh()

    # ---------------- تم ----------------
    def _tab_theme(self):
        w = QWidget()
        v = QVBoxLayout(w)
        g1 = QGroupBox('تم‌های آماده')
        h1 = QHBoxLayout(g1)
        for name in PRESET_THEMES:
            b = QPushButton(name)
            b.clicked.connect(lambda _, n=name: self.apply_preset(n))
            h1.addWidget(b)
        v.addWidget(g1)
        g2 = QGroupBox('شخصی‌سازی دقیق')
        g = QGridLayout(g2)
        self.theme_edits = {}
        defs = [('accent', 'رنگ تاکیدی (دکمه‌ها و عناوین)'), ('bg', 'رنگ پس‌زمینه برنامه'),
                ('text', 'رنگ متن'), ('report_bg', 'رنگ پس‌زمینه گزارش‌ها و فیش‌ها'),
                ('sidebar', 'رنگ سایدبار')]
        for i, (key, label) in enumerate(defs):
            g.addWidget(QLabel(label), i, 0)
            b = QPushButton('انتخاب رنگ…')
            b.clicked.connect(lambda _, k=key: self.pick_color(k))
            self.theme_edits[key] = b
            g.addWidget(b, i, 1)
        g.addWidget(QLabel('فونت نوشتار'), len(defs), 0)
        self.font_combo = QFontComboBox()
        g.addWidget(self.font_combo, len(defs), 1)
        g.addWidget(QLabel('اندازه فونت'), len(defs) + 1, 0)
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 16)
        g.addWidget(self.font_size, len(defs) + 1, 1)
        g.addWidget(QLabel('عکس پس‌زمینه برنامه'), len(defs) + 2, 0)
        b_img = QPushButton('انتخاب عکس…')
        b_img.clicked.connect(self.pick_bg_image)
        g.addWidget(b_img, len(defs) + 2, 1)
        b_clear = QPushButton('حذف عکس پس‌زمینه')
        b_clear.clicked.connect(self.clear_bg_image)
        g.addWidget(b_clear, len(defs) + 3, 1)
        v.addWidget(g2)
        b_save = QPushButton('💾 اعمال و ذخیره شخصی‌سازی')
        b_save.setObjectName('PrimaryBtn')
        b_save.clicked.connect(self.save_theme)
        v.addWidget(b_save)
        v.addStretch(1)
        return w

    def apply_preset(self, name):
        if not self.gate.allowed('edit'):
            return
        self.theme_mgr.set_preset(name)
        self.mainwin.reapply_theme()
        self.ctx.themeChanged.emit()

    def pick_color(self, key):
        col = QColorDialog.getColor()
        if col.isValid():
            self._picked = getattr(self, '_picked', {})
            self._picked[key] = col.name()

    def pick_bg_image(self):
        p, _ = QFileDialog.getOpenFileName(self, 'انتخاب عکس پس‌زمینه', '', 'Images (*.png *.jpg *.jpeg)')
        if p:
            self._bg_image = p
            QMessageBox.information(self, 'عکس', 'عکس انتخاب شد — دکمه «اعمال» را بزنید')

    def clear_bg_image(self):
        self._bg_image = ''
        self.ctx.theme_mgr.set_custom(bg_image='')
        self.mainwin.reapply_theme()

    def save_theme(self):
        if not self.gate.allowed('edit'):
            return
        custom = {}
        custom.update(getattr(self, '_picked', {}))
        custom['font'] = self.font_combo.currentFont().family()
        custom['font_size'] = str(self.font_size.value())
        if getattr(self, '_bg_image', ''):
            custom['bg_image'] = self._bg_image
        self.ctx.theme_mgr.set_custom(**custom)
        self.mainwin.reapply_theme()
        self.ctx.themeChanged.emit()
        QMessageBox.information(self, 'ذخیره', 'تم اعمال و ذخیره شد')

    # ---------------- بکاپ ----------------
    def _tab_backup(self):
        w = QWidget()
        v = QVBoxLayout(w)
        g = QGroupBox('بکاپ گیری')
        h = QHBoxLayout(g)
        b_bak = QPushButton('💾 تهیه بکاپ کامل')
        b_bak.setObjectName('PrimaryBtn')
        b_bak.clicked.connect(self.backup)
        b_res = QPushButton('♻️ بازگردانی از بکاپ')
        b_res.clicked.connect(self.restore)
        h.addWidget(b_bak)
        h.addWidget(b_res)
        h.addStretch(1)
        v.addWidget(g)
        v.addWidget(QLabel('📋 لاگ عملیات کاربران (۵۰۰ رکورد آخر):'))
        self.log_table = QTableWidget()
        setup_rtl_table(self.log_table, ['زمان', 'کاربر', 'عملیات', 'جزئیات'])
        v.addWidget(self.log_table, 1)
        return w

    def backup(self):
        import datetime
        default = f"بکاپ_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.db"
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره بکاپ', default, 'Database (*.db)')
        if not path:
            return
        self.ctx.db.conn.commit()
        self.ctx.db.backup(path)
        QMessageBox.information(self, 'بکاپ', 'بکاپ با موفقیت ذخیره شد:\n' + path)

    def restore(self):
        if not self.gate.allowed('admin'):
            return
        path, _ = QFileDialog.getOpenFileName(self, 'انتخاب فایل بکاپ', '', 'Database (*.db)')
        if not path:
            return
        if QMessageBox.question(self, 'بازگردانی',
                                'هیچ داده فعلی در فایل بکاپ بازتاب ندارد و جایگزین کامل می‌شود. '
                                'بعد از بازگردانی برنامه بسته می‌شود. مطمئنید؟') == QMessageBox.StandardButton.Yes:
            self.ctx.db.conn.close()
            shutil.copy2(path, self.ctx.db.path)
            os._exit(0)

    def load_log(self):
        cur = self.ctx.db.conn.execute(
            "SELECT ts,username,action,details FROM audit_log ORDER BY id DESC LIMIT 500")
        fill_table(self.log_table, [[to_persian_digits(r['ts']), r['username'], r['action'], r['details']]
                                    for r in cur.fetchall()])


def QInputDialog_getItem(parent, title, label, items):
    from PySide6.QtWidgets import QInputDialog
    return QInputDialog.getItem(parent, title, label, items, 0, False)


class QNewPassDialog:
    @staticmethod
    def get(parent):
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(parent, 'رمز جدید', 'رمز عبور جدید را وارد کنید:')
        return text, ok


class QYearsDialog:
    @staticmethod
    def get(parent):
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(parent, 'سال مالی جدید',
                                        'سال یا سال‌ها (با کاما جدا کنید) مثال: ۱۴۰۵,۱۴۰۶')
        if not ok:
            return [], False
        from core.numbers import normalize_digits, parse_int
        years = []
        for part in normalize_digits(text).split(','):
            part = part.strip()
            if part:
                y = parse_int(part, 0)
                if 1350 <= y <= 1500:
                    years.append(y)
        return years, bool(years)


class CompanyDialog(QDialog):
    """فرم کامل شرکت: اطلاعات بیمه/مالیات + لوگو (در همه خروجی‌ها چاپ می‌شود)"""
    def __init__(self, ctx, company=None):
        super().__init__()
        self.ctx = ctx
        self.company = company
        self.setWindowTitle('شرکت جدید' if not company else 'ویرایش شرکت')
        self.resize(560, 560)
        f = QFormLayout(self)
        self.name = QLineEdit(company['name'] if company else '')
        self.national = QLineEdit(company['national_id'] if company else '')
        self.econ = QLineEdit(company['economic_code'] if company else '')
        self.sso = QLineEdit(company['sso_branch_code'] if company else '')
        self.workshop = QLineEdit(company['sso_workshop_code'] if company else '')
        self.workshop.setPlaceholderText('کد ۱۰ رقمی کارگاه تامین اجتماعی')
        self.contract_row = QLineEdit(company['sso_contract_row'] if company else '')
        self.tax = QLineEdit(company['tax_file_code'] if company else '')
        self.postal = QLineEdit(company['postal_code'] if company else '')
        self.manager = QLineEdit(company['manager_name'] if company else '')
        self.addr = QLineEdit(company['address'] if company else '')
        self.phone = QLineEdit(company['phone'] if company else '')
        self.logo_path = (company['logo_path'] if company else '') or ''
        self.logo_lbl = QLabel('(بدون لوگو)')
        b_logo = QPushButton('انتخاب لوگو…')
        b_logo.clicked.connect(self.pick_logo)
        f.addRow('نام شرکت *', self.name)
        f.addRow('شناسه ملی', self.national)
        f.addRow('کد اقتصادی', self.econ)
        f.addRow('کد شعبه تامین اجتماعی', self.sso)
        f.addRow('کد کارگاه تامین اجتماعی', self.workshop)
        f.addRow('ردیف پیمان', self.contract_row)
        f.addRow('کد پرونده مالیاتی', self.tax)
        f.addRow('کدپستی', self.postal)
        f.addRow('نام کارفرما', self.manager)
        f.addRow('آدرس', self.addr)
        f.addRow('تلفن', self.phone)
        hlogo = QHBoxLayout()
        hlogo.addWidget(b_logo)
        hlogo.addWidget(self.logo_lbl, 1)
        f.addRow('لوگو (در همه خروجی‌ها چاپ می‌شود)', hlogo)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.save)
        bb.rejected.connect(self.reject)
        f.addRow(bb)
        enable_enter_navigation(self)
        if company and self.logo_path:
            self.logo_lbl.setText(os.path.basename(self.logo_path))

    def pick_logo(self):
        p, _ = QFileDialog.getOpenFileName(self, 'انتخاب لوگو', '', 'Images (*.png *.jpg *.jpeg *.bmp)')
        if p:
            self.logo_path = p
            self.logo_lbl.setText(os.path.basename(p))

    def save(self):
        from core.numbers import normalize_digits
        import shutil
        if not self.name.text().strip():
            return
        # لوگو به پوشه داده کپی شود تا در بکاپ/انتقال از بین نرود
        logo = self.logo_path
        if logo and os.path.exists(logo):
            from core.db import DATA_DIR
            dst = os.path.join(DATA_DIR, 'logos')
            os.makedirs(dst, exist_ok=True)
            target = os.path.join(dst, os.path.basename(logo))
            try:
                if os.path.abspath(logo) != os.path.abspath(target):
                    shutil.copy2(logo, target)
                logo = target
            except Exception:
                pass
        vals = [self.name.text().strip(), normalize_digits(self.national.text().strip()),
                normalize_digits(self.econ.text().strip()), normalize_digits(self.sso.text().strip()),
                normalize_digits(self.workshop.text().strip()),
                normalize_digits(self.contract_row.text().strip()),
                normalize_digits(self.tax.text().strip()),
                normalize_digits(self.postal.text().strip()), self.manager.text().strip(),
                self.addr.text().strip(), normalize_digits(self.phone.text().strip()), logo or '']
        if self.company:
            self.ctx.db.conn.execute(
                "UPDATE companies SET name=?,national_id=?,economic_code=?,sso_branch_code=?,"
                "sso_workshop_code=?,sso_contract_row=?,tax_file_code=?,postal_code=?,manager_name=?,"
                "address=?,phone=?,logo_path=? WHERE id=?", vals + [self.company['id']])
        else:
            self.ctx.db.conn.execute(
                "INSERT INTO companies(name,national_id,economic_code,sso_branch_code,"
                "sso_workshop_code,sso_contract_row,tax_file_code,postal_code,manager_name,"
                "address,phone,logo_path) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", vals)
        self.ctx.db.conn.commit()
        self.accept()
