# -*- coding: utf-8 -*-
"""صفحات پرسنل + قراردادها + احکام پرسنلی (با ایمپورت اکسل لیست پرسنل)"""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QLineEdit, QTableWidget, QTableWidgetItem, QDialog,
                               QFormLayout, QComboBox, QGroupBox, QTabWidget, QMessageBox,
                               QFileDialog, QGridLayout, QCheckBox, QInputDialog, QScrollArea)
from core.numbers import to_persian_digits, parse_number, normalize_digits, format_money
from core import jalali as J
from .widgets import (MoneyEdit, JalaliDatePicker, setup_rtl_table, fill_table,
                      PercentEdit, TimeMinutesEdit)

CONTRACT_TYPES = ['ماهانه ثابت', 'ساعتی', 'روزانه', 'پیمانی', 'سایر']
EDUCATION = ['', 'زیر دیپلم', 'سيكل', 'ديپلم', 'فوق ديپلم', 'ليسانس', 'فوق ليسانس', 'دكتري']
MILITARY = ['', 'انجام داده', 'انجام نداده', 'معاف از خدمت', 'کفالت', 'مشمول']

# نقشه ستون‌های فایل «لیست پرسنل این ماه» (بر اساس فایل واقعی کاربر)
PERSONNEL_IMPORT_MAP = {
    'شماره پرسنلی': 'personnel_code', 'نام': 'first_name', 'نام خانوادگی': 'last_name',
    'نام پدر': 'father_name', 'کد ملی': 'national_id', 'شماره شناسنامه': 'id_number',
    'سریال شناسنامه': 'id_serial', 'محل صدور': 'id_issue_place', 'تاریخ تولد': 'birth_date',
    'وضعیت تاهل': 'marital_status', 'تحت تکفل': 'dependents', 'مدرک تحصیلی': 'education',
    'موبایل': 'mobile', 'مرکز هزینه': 'cost_center', 'گروه فیش حقوقی': 'payslip_group',
    'بانک حقوق': 'bank_name', 'شماره حساب': 'bank_account',
    'بیمه': 'sso_insurer', 'شماره بیمه': 'sso_number', 'شبکار دائم': 'permanent_night',
    'جانبازی': 'is_veteran', 'محل خدمت': 'work_location', 'تاریخ شروع قرارداد': 'hire_date',
    'وضعیت نظام وظیفه': 'military_status', 'شغل': 'job_title', 'شماره کارت': 'card_no',
}


class PersonnelPage(QWidget):
    def __init__(self, ctx, gate):
        super().__init__()
        self.ctx = ctx
        self.gate = gate
        self._build()
        self.refresh()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        title = QLabel('👤 مدیریت پرسنل')
        title.setObjectName('PageTitle')
        v.addWidget(title)
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('جستجو بر اساس نام، کد پرسنلی، کد ملی یا شماره کارت…')
        self.search.textChanged.connect(self.refresh)
        btn_add = QPushButton('➕ پرسنل جدید')
        btn_add.setObjectName('PrimaryBtn')
        btn_add.clicked.connect(self.add_person)
        btn_edit = QPushButton('✏️ ویرایش')
        btn_edit.clicked.connect(self.edit_person)
        btn_del = QPushButton('🗑 حذف')
        btn_del.setObjectName('DangerBtn')
        btn_del.clicked.connect(self.delete_person)
        btn_import = QPushButton('📥 ایمپورت اکسل پرسنل')
        btn_import.clicked.connect(self.import_xlsx)
        btn_export = QPushButton('📤 خروجی اکسل')
        btn_export.clicked.connect(self.export_xlsx)
        for w in (self.search, btn_add, btn_edit, btn_del, btn_import, btn_export):
            bar.addWidget(w)
        v.addLayout(bar)
        self.table = QTableWidget()
        setup_rtl_table(self.table, ['ردیف', 'کد پرسنلی', 'نام', 'نام خانوادگی', 'کد ملی',
                                     'شماره کارت دستگاه', 'شغل', 'مرکز هزینه', 'تلفن',
                                     'شماره بیمه', 'نوع قرارداد', 'وضعیت'])
        v.addWidget(self.table, 1)

    def rows_query(self):
        if not self.ctx.fy_id:
            return []
        q = """SELECT p.* FROM personnel p JOIN fiscal_years fy ON fy.company_id=p.company_id
               WHERE fy.id=?"""
        args = [self.ctx.fy_id]
        s = normalize_digits(self.search.text()).strip()
        if s:
            q += """ AND (p.first_name LIKE ? OR p.last_name LIKE ? OR p.personnel_code LIKE ?
                    OR p.national_id LIKE ? OR p.card_no LIKE ?)"""
            like = f'%{s}%'
            args += [like] * 5
        q += " ORDER BY p.last_name, p.first_name"
        cur = self.ctx.db.conn.execute(q, args)
        return [dict(r) for r in cur.fetchall()]

    def refresh(self):
        rows = self.rows_query()
        data = []
        for i, r in enumerate(rows, 1):
            data.append([to_persian_digits(str(i)), to_persian_digits(str(r['personnel_code'])),
                         r['first_name'], r['last_name'], to_persian_digits(str(r['national_id'] or '')),
                         to_persian_digits(str(r['card_no'] or '')), r['job_title'],
                         r['cost_center'], to_persian_digits(str(r['mobile'] or '')),
                         to_persian_digits(str(r['sso_number'] or '')),
                         r.get('contract_type', '') or '', r['status']])
        fill_table(self.table, data)
        self.table.itemSelectionChanged.connect(lambda: None)
        self._rows = rows

    def _selected(self):
        r = self.table.currentRow()
        if 0 <= r < len(self._rows):
            return self._rows[r]
        return None

    # ---------------- فرم پرسنل ----------------
    def add_person(self):
        if not self.gate.allowed('edit'):
            QMessageBox.warning(self, 'دسترسی', 'شما مجوز ویرایش ندارید')
            return
        dlg = PersonnelDialog(self.ctx, None)
        if dlg.exec():
            self.refresh()

    def edit_person(self):
        p = self._selected()
        if not p:
            QMessageBox.information(self, 'انتخاب', 'یک ردیف را انتخاب کنید')
            return
        if not self.gate.allowed('edit'):
            QMessageBox.warning(self, 'دسترسی', 'شما مجوز ویرایش ندارید')
            return
        dlg = PersonnelDialog(self.ctx, p)
        if dlg.exec():
            self.refresh()

    def delete_person(self):
        p = self._selected()
        if not p:
            return
        if not self.gate.allowed('edit'):
            QMessageBox.warning(self, 'دسترسی', 'شما مجوز حذف ندارید')
            return
        if QMessageBox.question(self, 'حذف', f"حذف «{p['first_name']} {p['last_name']}» و همه اطلاعات وابسته؟") == QMessageBox.StandardButton.Yes:
            self.ctx.db.conn.execute("DELETE FROM personnel WHERE id=?", (p['id'],))
            self.ctx.db.conn.commit()
            self.ctx.db.log_audit(self.ctx.auth.current_user['username'] if self.ctx.auth.current_user else '?',
                                  'حذف پرسنل', p['personnel_code'])
            self.refresh()

    # ---------------- ایمپورت اکسل ----------------
    def import_xlsx(self):
        if not self.gate.allowed('edit'):
            return
        path, _ = QFileDialog.getOpenFileName(self, 'انتخاب فایل اکسل پرسنل', '', 'Excel (*.xlsx *.xls)')
        if not path:
            return
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=True)
            sh = wb.active
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خواندن فایل ممکن نشد: {e}')
            return
        # یافتن ردیف هدر (حاوی «شماره پرسنلی» یا «نام خانوادگی»)
        header_row, colmap = None, {}
        for r in range(1, min(sh.max_row, 12) + 1):
            vals = {}
            for c in range(1, sh.max_column + 1):
                v = sh.cell(r, c).value
                if v and isinstance(v, str):
                    vals[c] = v.strip().lstrip(':').strip()
            if 'نام خانوادگی' in vals.values() and ('شماره پرسنلی' in vals.values() or 'ردیف' in vals.values()):
                header_row = r
                for c, name in vals.items():
                    if name in PERSONNEL_IMPORT_MAP:
                        colmap[PERSONNEL_IMPORT_MAP[name]] = c
                break
        if not header_row:
            QMessageBox.critical(self, 'خطا', 'ساختار فایل شناسایی نشد (هدر «نام خانوادگی» و «شماره پرسنلی» لازم است)')
            return
        added, updated, skipped = 0, 0, []
        for r in range(header_row + 1, sh.max_row + 1):
            rec = {}
            for field, c in colmap.items():
                v = sh.cell(r, c).value
                if v is None:
                    rec[field] = ''
                else:
                    rec[field] = str(v).strip() if not isinstance(v, (int, float)) else (str(int(v)) if float(v) == int(v) else str(v))
            code = normalize_digits(rec.get('personnel_code', ''))
            if not code:
                continue
            fname = rec.get('first_name', '')
            if not fname or fname in ('نام',):
                continue
            data = dict(rec)
            data['personnel_code'] = code
            data['dependents'] = int(parse_number(rec.get('dependents', 0), 0))
            for bkey in ('permanent_night', 'is_veteran'):
                data[bkey] = 1 if str(rec.get(bkey, '')).strip() in ('بله', 'خیر'[::-1][::-1], '1', 'True', 'yes', 'دارد') else 0
                if str(rec.get(bkey, '')).strip() == 'بله':
                    data[bkey] = 1
                elif str(rec.get(bkey, '')).strip() in ('خیر', ''):
                    data[bkey] = 0
            data['national_id'] = normalize_digits(rec.get('national_id', ''))
            data['sso_number'] = normalize_digits(rec.get('sso_number', ''))
            data['card_no'] = normalize_digits(rec.get('card_no', ''))
            data['mobile'] = normalize_digits(rec.get('mobile', ''))
            data['bank_account'] = normalize_digits(rec.get('bank_account', ''))
            cur = self.ctx.db.conn.execute(
                "SELECT id FROM personnel WHERE company_id=? AND personnel_code=?",
                (self.ctx.company_id, code))
            exist = cur.fetchone()
            cols = ['company_id'] + list(data.keys())
            vals = [self.ctx.company_id] + list(data.values())
            if exist:
                sets = ', '.join(f"{c}=?" for c in data.keys())
                self.ctx.db.conn.execute(f"UPDATE personnel SET {sets} WHERE id=?",
                                         vals[1:] + [exist['id']])
                updated += 1
            else:
                ph = ', '.join('?' * len(cols))
                self.ctx.db.conn.execute(
                    f"INSERT INTO personnel({','.join(cols)}) VALUES({ph})", vals)
                added += 1
        self.ctx.db.conn.commit()
        # ثبت قرارداد پیش‌فرض
        self.refresh()
        msg = f"اضافه‌شده: {to_persian_digits(str(added))} | به‌روزرسانی: {to_persian_digits(str(updated))}"
        if skipped:
            msg += '\nردشده: ' + ', '.join(skipped[:5])
        QMessageBox.information(self, 'ایمپورت پرسنل', msg)

    def export_xlsx(self):
        rows = self.rows_query()
        headers = ['کد پرسنلی', 'نام', 'نام خانوادگی', 'کد ملی', 'شماره کارت', 'شغل',
                   'مرکز هزینه', 'گروه فیش', 'تلفن', 'شماره بیمه', 'بانک', 'شماره حساب',
                   'تولد', 'تأهل', 'تحت تکفل', 'تحصیلات', 'وضعیت']
        data = []
        for r in rows:
            data.append([r['personnel_code'], r['first_name'], r['last_name'], r['national_id'],
                         r['card_no'], r['job_title'], r['cost_center'], r['payslip_group'],
                         r['mobile'], r['sso_number'], r['bank_name'], r['bank_account'],
                         r['birth_date'], r['marital_status'], r['dependents'], r['education'], r['status']])
        from core import exports
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره خروجی', 'پرسنل.xlsx', 'Excel (*.xlsx)')
        if path:
            exports.export_table_xlsx(path, 'لیست پرسنل', self.ctx.company_name, headers, data)
            QMessageBox.information(self, 'خروجی', 'فایل اکسل ذخیره شد:\n' + path)


class PersonnelDialog(QDialog):
    """فرم کامل مشخصات پرسنل (۲۸ فیلد فایل واقعی + قرارداد و حکم)"""
    def __init__(self, ctx, person):
        super().__init__()
        self.ctx = ctx
        self.person = person
        self.setWindowTitle('پرسنل جدید' if not person else 'ویرایش پرسنل')
        self.resize(760, 640)
        v = QVBoxLayout(self)
        tabs = QTabWidget()
        v.addWidget(tabs, 1)

        # --- تب هویتی ---
        f1 = QFormLayout()
        self.code = QLineEdit()
        self.first = QLineEdit()
        self.last = QLineEdit()
        self.father = QLineEdit()
        self.national = QLineEdit()
        self.idnum = QLineEdit()
        self.idserial = QLineEdit()
        self.idplace = QLineEdit()
        self.birth = JalaliDatePicker(ctx.cal)
        self.gender = QComboBox(); self.gender.addItems(['مرد', 'زن'])
        self.marital = QComboBox(); self.marital.addItems(['مجرد', 'متاهل'])
        self.dependents = QLineEdit('0')
        self.education = QComboBox(); self.education.addItems(EDUCATION)
        self.military = QComboBox(); self.military.addItems(MILITARY)
        self.veteran = QCheckBox('جانبازی')
        f1.addRow('شماره پرسنلی *', self.code)
        f1.addRow('نام *', self.first)
        f1.addRow('نام خانوادگی', self.last)
        f1.addRow('نام پدر', self.father)
        f1.addRow('کد ملی', self.national)
        f1.addRow('شماره شناسنامه', self.idnum)
        f1.addRow('سریال شناسنامه', self.idserial)
        f1.addRow('محل صدور', self.idplace)
        f1.addRow('تاریخ تولد', self.birth)
        f1.addRow('جنسیت', self.gender)
        f1.addRow('وضعیت تأهل', self.marital)
        f1.addRow('تحت تکفل (نفر)', self.dependents)
        f1.addRow('مدرک تحصیلی', self.education)
        f1.addRow('نظام وظیفه', self.military)
        f1.addRow('', self.veteran)
        w1 = QWidget(); w1.setLayout(f1)
        tabs.addTab(w1, 'هویتی')

        # --- تب شغلی/بیمه/بانک ---
        f2 = QFormLayout()
        self.cardno = QLineEdit()
        self.hire = JalaliDatePicker(ctx.cal)
        self.job = QLineEdit()
        self.cost = QLineEdit()
        self.pgroup = QLineEdit()
        self.workloc = QLineEdit()
        self.mobile = QLineEdit()
        self.sso_num = QLineEdit()
        self.sso_ins = QLineEdit()
        self.bank = QLineEdit()
        self.account = QLineEdit()
        self.sheba = QLineEdit()
        self.status = QComboBox(); self.status.addItems(['شاغل', 'خروج', 'بازنشسته'])
        self.notes = QLineEdit()
        f2.addRow('شماره کارت دستگاه حضور و غیاب *', self.cardno)
        f2.addRow('تاریخ استخدام', self.hire)
        f2.addRow('شغل', self.job)
        f2.addRow('مرکز هزینه', self.cost)
        f2.addRow('گروه فیش حقوقی', self.pgroup)
        f2.addRow('محل خدمت', self.workloc)
        f2.addRow('تلفن همراه', self.mobile)
        f2.addRow('شماره بیمه تامین اجتماعی', self.sso_num)
        f2.addRow('شرکت بیمه‌شونده', self.sso_ins)
        f2.addRow('بانک حقوق', self.bank)
        f2.addRow('شماره حساب', self.account)
        f2.addRow('شماره شبا', self.sheba)
        f2.addRow('وضعیت', self.status)
        f2.addRow('یادداشت', self.notes)
        w2 = QWidget(); w2.setLayout(f2)
        tabs.addTab(w2, 'شغلی و بیمه و بانک')

        # --- تب قرارداد ---
        f3 = QFormLayout()
        self.ctype = QComboBox(); self.ctype.addItems(CONTRACT_TYPES)
        self.cstart = JalaliDatePicker(ctx.cal)
        self.cend = JalaliDatePicker(ctx.cal)
        self.hourly = MoneyEdit(0)
        self.daily = MoneyEdit(0)
        self.monthly = MoneyEdit(0)
        self.project = MoneyEdit(0)
        self.insured = QCheckBox('مشمول بیمه تامین اجتماعی')
        self.insured.setChecked(True)
        f3.addRow('نوع قرارداد *', self.ctype)
        f3.addRow('تاریخ شروع', self.cstart)
        f3.addRow('تاریخ پایان', self.cend)
        f3.addRow('نرخ ساعتی (ریال)', self.hourly)
        f3.addRow('نرخ روزانه (ریال)', self.daily)
        f3.addRow('مزد ماهانه ثابت (ریال)', self.monthly)
        f3.addRow('مبلغ پیمان (ریال)', self.project)
        f3.addRow('', self.insured)
        w3 = QWidget(); w3.setLayout(f3)
        tabs.addTab(w3, 'قرارداد')

        # --- تب شیفت و بیمه اختصاصی ---
        f5 = QFormLayout()
        self.shift_combo = QComboBox()
        self.shift_combo.addItem('— بدون شیفت (پیش‌فرض ۸ تا ۱۶ روزهای عادی) —', 0)
        try:
            from core import shifts as SH
            for s in SH.load_shifts(ctx.db, ctx.company_id):
                self.shift_combo.addItem(s['name'], s['id'])
        except Exception:
            pass
        self.pct_worker = PercentEdit(0)
        self.pct_employer = PercentEdit(0)
        self.pct_unemp = PercentEdit(0)
        for ed in (self.pct_worker, self.pct_employer, self.pct_unemp):
            ed.setPlaceholderText('پیش‌فرض')
            ed.setText('')
        f5.addRow('شیفت کاری فرد', self.shift_combo)
        f5.addRow('درصد بیمه سهم کارگر (خالی = پیش‌فرض ۷٪)', self.pct_worker)
        f5.addRow('درصد بیمه سهم کارفرما (خالی = پیش‌فرض ۲۰٪)', self.pct_employer)
        f5.addRow('درصد بیمه بیکاری (خالی = پیش‌فرض ۳٪)', self.pct_unemp)
        note5 = QLabel('اگر برای این فرد درصدهای بیمه باید متفاوت باشد، فقط همین کادرها را پر کنید؛\n'
                       'محاسبات بیمه، لیست بیمه و فیش او دقیقا با همین درصدها انجام می‌شود.')
        note5.setWordWrap(True)
        note5.setStyleSheet('color:#64748b;')
        f5.addRow('', note5)
        w5 = QWidget(); w5.setLayout(f5)
        tabs.addTab(w5, 'شیفت و بیمه اختصاصی')

        # --- تب حکم حقوقی ---
        f4 = QFormLayout()
        self.d_effective = JalaliDatePicker(ctx.cal)
        self.decree_fields = {}
        DF = [('job_wage', 'مزد شغل'), ('seniority_wage', 'مزد سنوات'),
              ('housing', 'حق مسکن'), ('food', 'خواروبار'),
              ('adjustment_diff', 'تفاوت تطبیق'), ('supervision', 'حق سرپرستی'),
              ('education_aid', 'کمک‌هزینه تحصیلی'), ('labor_market', 'فوق‌العاده بازار کار'),
              ('attraction_percent', 'درصد حق جذب'), ('attraction_amount', 'مبلغ حق جذب'),
              ('other_benefits', 'اضافه‌کاری/سایر مزایا'), ('worker_ben', 'بن کارگری'),
              ('fixed_overtime', 'اضافه‌کار ثابت'), ('family_allowance', 'حق عائله‌مندی (تأهل)'),
              ('child_allowance', 'حق اولاد'), ('shift_allowance', 'حق شیفت')]
        for key, title in DF:
            if key == 'attraction_percent':
                ed = PercentEdit(0)
            else:
                ed = MoneyEdit(0)
            self.decree_fields[key] = ed
            f4.addRow(title, ed)
        w4 = QWidget(); sw = QScrollArea(); sw.setWidget(w4); sw.setWidgetResizable(True)
        w4.setLayout(f4)
        tabs.addTab(sw, 'حکم حقوقی (اول)')

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
        if person:
            self._load(person)

    def _load(self, p):
        self.code.setText(p['personnel_code'])
        self.first.setText(p['first_name'] or '')
        self.last.setText(p['last_name'] or '')
        self.father.setText(p['father_name'] or '')
        self.national.setText(p['national_id'] or '')
        self.idnum.setText(p['id_number'] or '')
        self.idserial.setText(p['id_serial'] or '')
        self.idplace.setText(p['id_issue_place'] or '')
        if p['birth_date']:
            d = parse_number.__self__ if False else None
            from core.numbers import parse_jalali_date_str
            pd = parse_jalali_date_str(p['birth_date'])
            if pd:
                self.birth.set_date(pd)
        self.gender.setCurrentText(p['gender'] or 'مرد')
        self.marital.setCurrentText(p['marital_status'] or 'مجرد')
        self.dependents.setText(to_persian_digits(str(p['dependents'] or 0)))
        self.education.setCurrentText(p['education'] or '')
        self.military.setCurrentText(p['military_status'] or '')
        self.veteran.setChecked(bool(p['is_veteran']))
        self.cardno.setText(p['card_no'] or '')
        from core.numbers import parse_jalali_date_str
        if p['hire_date']:
            pd = parse_jalali_date_str(p['hire_date'])
            if pd:
                self.hire.set_date(pd)
        self.job.setText(p['job_title'] or '')
        self.cost.setText(p['cost_center'] or '')
        self.pgroup.setText(p['payslip_group'] or '')
        self.workloc.setText(p['work_location'] or '')
        self.mobile.setText(p['mobile'] or '')
        self.sso_num.setText(p['sso_number'] or '')
        self.sso_ins.setText(p['sso_insurer'] or '')
        self.bank.setText(p['bank_name'] or '')
        self.account.setText(p['bank_account'] or '')
        self.sheba.setText(p['bank_sheba'] or '')
        self.status.setCurrentText(p['status'] or 'شاغل')
        self.notes.setText(p['notes'] or '')
        if p.get('shift_id'):
            idx = self.shift_combo.findData(p['shift_id'])
            self.shift_combo.setCurrentIndex(max(0, idx))
        if p.get('sso_worker_pct') is not None:
            self.pct_worker.setText(to_persian_digits(f"{p['sso_worker_pct']:g}"))
        if p.get('sso_employer_pct') is not None:
            self.pct_employer.setText(to_persian_digits(f"{p['sso_employer_pct']:g}"))
        if p.get('sso_unemp_pct') is not None:
            self.pct_unemp.setText(to_persian_digits(f"{p['sso_unemp_pct']:g}"))
        # قرارداد فعال
        cur = self.ctx.db.conn.execute(
            "SELECT * FROM contracts WHERE personnel_id=? ORDER BY id DESC LIMIT 1", (p['id'],))
        c = cur.fetchone()
        if c:
            self.ctype.setCurrentText(c['contract_type'])
            if c['start_date']:
                pd = parse_jalali_date_str(c['start_date'])
                if pd:
                    self.cstart.set_date(pd)
            if c['end_date']:
                pd = parse_jalali_date_str(c['end_date'])
                if pd:
                    self.cend.set_date(pd)
            self.hourly.set_value(c['hourly_rate'])
            self.daily.set_value(c['daily_rate'])
            self.monthly.set_value(c['monthly_wage'])
            self.project.set_value(c['project_amount'])
            self.insured.setChecked(bool(c['insurance_required']))
        # حکم
        cur = self.ctx.db.conn.execute(
            "SELECT * FROM decrees WHERE personnel_id=? ORDER BY effective_date DESC LIMIT 1", (p['id'],))
        d = cur.fetchone()
        if d:
            if d['effective_date']:
                pd = parse_jalali_date_str(d['effective_date'])
                if pd:
                    self.d_effective.set_date(pd)
            for key, ed in self.decree_fields.items():
                ed.set_value(d[key] or 0)

    def _opt_pct(self, ed):
        t = normalize_digits(ed.text()).strip()
        if not t:
            return None
        return parse_number(t, 0)

    def save(self):
        code = normalize_digits(self.code.text()).strip()
        if not code or not self.first.text().strip():
            QMessageBox.warning(self, 'خطا', 'شماره پرسنلی و نام الزامی است')
            return
        data = {
            'personnel_code': code, 'first_name': self.first.text().strip(),
            'last_name': self.last.text().strip(), 'father_name': self.father.text().strip(),
            'national_id': normalize_digits(self.national.text().strip()),
            'id_number': normalize_digits(self.idnum.text().strip()),
            'id_serial': normalize_digits(self.idserial.text().strip()),
            'id_issue_place': self.idplace.text().strip(),
            'birth_date': J.format_jalali(*self.birth.date(), persian=False) if self.birth.date() else '',
            'gender': self.gender.currentText(), 'marital_status': self.marital.currentText(),
            'dependents': int(parse_number(self.dependents.text(), 0)),
            'education': self.education.currentText(),
            'military_status': self.military.currentText(),
            'is_veteran': 1 if self.veteran.isChecked() else 0,
            'card_no': normalize_digits(self.cardno.text().strip()),
            'hire_date': J.format_jalali(*self.hire.date(), persian=False) if self.hire.date() else '',
            'job_title': self.job.text().strip(), 'cost_center': self.cost.text().strip(),
            'payslip_group': self.pgroup.text().strip(),
            'work_location': self.workloc.text().strip(),
            'mobile': normalize_digits(self.mobile.text().strip()),
            'sso_number': normalize_digits(self.sso_num.text().strip()),
            'sso_insurer': self.sso_ins.text().strip(),
            'bank_name': self.bank.text().strip(),
            'bank_account': normalize_digits(self.account.text().strip()),
            'bank_sheba': normalize_digits(self.sheba.text().strip()),
            'status': self.status.currentText(), 'notes': self.notes.text().strip(),
            'shift_id': self.shift_combo.currentData() or None,
            'sso_worker_pct': self._opt_pct(self.pct_worker),
            'sso_employer_pct': self._opt_pct(self.pct_employer),
            'sso_unemp_pct': self._opt_pct(self.pct_unemp),
        }
        db = self.ctx.db
        if self.person:
            sets = ', '.join(f"{k}=?" for k in data)
            db.conn.execute(f"UPDATE personnel SET {sets} WHERE id=?",
                            list(data.values()) + [self.person['id']])
            pid = self.person['id']
        else:
            cols = ['company_id'] + list(data.keys())
            vals = [self.ctx.company_id] + list(data.values())
            ph = ', '.join('?' * len(cols))
            cur = db.conn.execute(f"INSERT INTO personnel({','.join(cols)}) VALUES({ph})", vals)
            pid = cur.lastrowid
        # قرارداد
        contract = {
            'contract_type': self.ctype.currentText(),
            'hourly_rate': self.hourly.value(), 'daily_rate': self.daily.value(),
            'monthly_wage': self.monthly.value(), 'project_amount': self.project.value(),
            'start_date': J.format_jalali(*self.cstart.date(), persian=False) if self.cstart.date() else '',
            'end_date': J.format_jalali(*self.cend.date(), persian=False) if self.cend.date() else '',
            'insurance_required': 1 if self.insured.isChecked() else 0,
        }
        cur = db.conn.execute(
            "SELECT id FROM contracts WHERE personnel_id=? ORDER BY id DESC LIMIT 1", (pid,))
        ex = cur.fetchone()
        if ex:
            sets = ', '.join(f"{k}=?" for k in contract)
            db.conn.execute(f"UPDATE contracts SET {sets} WHERE id=?",
                            list(contract.values()) + [ex['id']])
        else:
            cols = ['personnel_id'] + list(contract.keys())
            vals = [pid] + list(contract.values())
            ph = ', '.join('?' * len(cols))
            db.conn.execute(f"INSERT INTO contracts({','.join(cols)}) VALUES({ph})", vals)
        # حکم (فقط اگر مزد شغل وارد شده یا ویرایش)
        job_wage = self.decree_fields['job_wage'].value()
        if job_wage > 0:
            decree = {k: ed.value() for k, ed in self.decree_fields.items()}
            decree['effective_date'] = J.format_jalali(*self.d_effective.date(), persian=False) if self.d_effective.date() else ''
            db.conn.execute(
                """INSERT INTO decrees(personnel_id,effective_date,job_wage,seniority_wage,child_allowance,
                   housing,food,adjustment_diff,supervision,education_aid,labor_market,attraction_percent,
                   attraction_amount,other_benefits,worker_ben,fixed_overtime,family_allowance,shift_allowance)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (pid, decree['effective_date'], decree['job_wage'], decree['seniority_wage'],
                 decree['child_allowance'], decree['housing'], decree['food'], decree['adjustment_diff'],
                 decree['supervision'], decree['education_aid'], decree['labor_market'],
                 decree['attraction_percent'], decree['attraction_amount'], decree['other_benefits'],
                 decree['worker_ben'], decree['fixed_overtime'], decree['family_allowance'],
                 decree['shift_allowance']))
        db.conn.commit()
        db.log_audit(self.ctx.auth.current_user['username'], 'ثبت/ویرایش پرسنل', code)
        self.accept()


class DecreesPage(QWidget):
    """احکام پرسنلی — با تاریخ اجرا (قابل تغییر هر ماه)"""
    def __init__(self, ctx, gate):
        super().__init__()
        self.ctx = ctx
        self.gate = gate
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        title = QLabel('📜 احکام پرسنلی')
        title.setObjectName('PageTitle')
        v.addWidget(title)
        bar = QHBoxLayout()
        btn_add = QPushButton('➕ حکم جدید')
        btn_add.setObjectName('PrimaryBtn')
        btn_add.clicked.connect(self.add)
        btn_edit = QPushButton('✏️ ویرایش حکم انتخابی')
        btn_edit.clicked.connect(self.edit)
        btn_hist = QPushButton('🕘 تاریخچه حکم پرسنل')
        btn_hist.clicked.connect(self.history)
        btn_export = QPushButton('📤 خروجی اکسل')
        btn_export.clicked.connect(self.export)
        for w in (btn_add, btn_edit, btn_hist, btn_export):
            bar.addWidget(w)
        bar.addStretch(1)
        v.addLayout(bar)
        self.table = QTableWidget()
        setup_rtl_table(self.table, ['پرسنل', 'کد پرسنلی', 'تاریخ اجرا', 'مزد شغل', 'مزد سنوات',
                                     'حق مسکن', 'بن کارگری', 'حق اولاد', 'سایر مزایا', 'اضافه‌کار ثابت'])
        v.addWidget(self.table, 1)
        self.refresh()

    def refresh(self):
        if not self.ctx.fy_id:
            fill_table(self.table, [])
            return
        cur = self.ctx.db.conn.execute("""
            SELECT d.*, p.first_name, p.last_name, p.personnel_code FROM decrees d
            JOIN personnel p ON p.id=d.personnel_id
            JOIN fiscal_years fy ON fy.company_id=p.company_id
            WHERE fy.id=? ORDER BY p.last_name, d.effective_date DESC""", (self.ctx.fy_id,))
        rows = [dict(r) for r in cur.fetchall()]
        self._rows = rows
        data = [[f"{r['first_name']} {r['last_name']}", to_persian_digits(str(r['personnel_code'])),
                 to_persian_digits(str(r['effective_date'] or '')), r['job_wage'], r['seniority_wage'],
                 r['housing'], r['worker_ben'], r['child_allowance'], r['other_benefits'], r['fixed_overtime']]
                for r in rows]
        fill_table(self.table, data, formats={3: 'money', 4: 'money', 5: 'money', 6: 'money',
                                              7: 'money', 8: 'money', 9: 'money'})

    def _selected(self):
        r = self.table.currentRow()
        return self._rows[r] if 0 <= r < len(self._rows) else None

    def add(self):
        if not self.gate.allowed('edit'):
            return
        dlg = DecreeDialog(self.ctx, None)
        if dlg.exec():
            self.refresh()

    def edit(self):
        d = self._selected()
        if not d:
            QMessageBox.information(self, 'انتخاب', 'یک حکم را انتخاب کنید')
            return
        if not self.gate.allowed('edit'):
            return
        dlg = DecreeDialog(self.ctx, d)
        if dlg.exec():
            self.refresh()

    def history(self):
        d = self._selected()
        if not d:
            return
        cur = self.ctx.db.conn.execute(
            "SELECT * FROM decrees WHERE personnel_id=? ORDER BY effective_date DESC", (d['personnel_id'],))
        rows = [dict(r) for r in cur.fetchall()]
        dlg = QDialog(self)
        dlg.setWindowTitle(f"تاریخچه احکام — {d['first_name']} {d['last_name']}")
        dlg.resize(820, 420)
        v = QVBoxLayout(dlg)
        t = QTableWidget()
        setup_rtl_table(t, ['تاریخ اجرا', 'مزد شغل', 'سنوات', 'مسکن', 'خواروبار', 'بن', 'اولاد', 'سایر'])
        fill_table(t, [[to_persian_digits(str(r['effective_date'] or '')), r['job_wage'], r['seniority_wage'],
                        r['housing'], r['food'], r['worker_ben'], r['child_allowance'], r['other_benefits']]
                       for r in rows],
                   formats={1: 'money', 2: 'money', 3: 'money', 4: 'money', 5: 'money', 6: 'money', 7: 'money'})
        v.addWidget(t)
        dlg.exec()

    def export(self):
        from core import exports
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره', 'احکام پرسنلی.xlsx', 'Excel (*.xlsx)')
        if not path:
            return
        headers = ['پرسنل', 'کد', 'تاریخ اجرا', 'مزد شغل', 'سنوات', 'مسکن', 'خواروبار', 'بن',
                   'اولاد', 'سرپرستی', 'جذب', 'سایر', 'اضافه‌کار ثابت', 'عائله‌مندی', 'شیفت']
        data = [[f"{r['first_name']} {r['last_name']}", r['personnel_code'], r['effective_date'],
                 r['job_wage'], r['seniority_wage'], r['housing'], r['food'], r['worker_ben'],
                 r['child_allowance'], r['supervision'], r['attraction_amount'], r['other_benefits'],
                 r['fixed_overtime'], r['family_allowance'], r['shift_allowance']]
                for r in self._rows]
        exports.export_table_xlsx(path, 'لیست احکام پرسنلی', self.ctx.company_name, headers, data,
                                  money_cols=set(range(3, 15)))


class DecreeDialog(QDialog):
    def __init__(self, ctx, decree):
        super().__init__()
        self.ctx = ctx
        self.decree = decree
        self.setWindowTitle('حکم پرسنلی جدید' if not decree else 'ویرایش حکم پرسنلی')
        self.resize(560, 620)
        v = QVBoxLayout(self)
        f = QFormLayout()
        self.person = QComboBox()
        cur = ctx.db.conn.execute("""SELECT p.id, p.first_name, p.last_name, p.personnel_code FROM personnel p
                                     JOIN fiscal_years fy ON fy.company_id=p.company_id WHERE fy.id=?""",
                                   (ctx.fy_id,))
        self._people = [dict(r) for r in cur.fetchall()]
        for p in self._people:
            self.person.addItem(f"{p['last_name']} {p['first_name']} — {to_persian_digits(str(p['personnel_code']))}", p['id'])
        self.effective = JalaliDatePicker(ctx.cal)
        f.addRow('پرسنل *', self.person)
        f.addRow('تاریخ اجرا *', self.effective)
        self.fields = {}
        DF = [('job_wage', 'مزد شغل'), ('seniority_wage', 'مزد سنوات'),
              ('housing', 'حق مسکن'), ('food', 'خواروبار'),
              ('adjustment_diff', 'تفاوت تطبیق'), ('supervision', 'حق سرپرستی'),
              ('education_aid', 'کمک‌هزینه تحصیلی'), ('labor_market', 'فوق‌العاده بازار کار'),
              ('attraction_percent', 'درصد حق جذب'), ('attraction_amount', 'مبلغ حق جذب'),
              ('other_benefits', 'اضافه‌کاری/سایر مزایا'), ('worker_ben', 'بن کارگری'),
              ('fixed_overtime', 'اضافه‌کار ثابت'), ('family_allowance', 'حق عائله‌مندی (تأهل)'),
              ('child_allowance', 'حق اولاد'), ('shift_allowance', 'حق شیفت')]
        for key, title in DF:
            ed = PercentEdit(0) if key == 'attraction_percent' else MoneyEdit(0)
            self.fields[key] = ed
            f.addRow(title, ed)
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
        if decree:
            idx = self.person.findData(decree['personnel_id'])
            if idx >= 0:
                self.person.setCurrentIndex(idx)
            from core.numbers import parse_jalali_date_str
            pd = parse_jalali_date_str(decree['effective_date'] or '')
            if pd:
                self.effective.set_date(pd)
            for key, ed in self.fields.items():
                ed.set_value(decree[key] or 0)

    def save(self):
        pid = self.person.currentData()
        if not pid or not self.effective.date():
            QMessageBox.warning(self, 'خطا', 'پرسنل و تاریخ اجرا الزامی است')
            return
        vals = [pid, J.format_jalali(*self.effective.date(), persian=False)] + \
               [self.fields[k].value() for k in ['job_wage', 'seniority_wage', 'child_allowance',
                                                 'housing', 'food', 'adjustment_diff', 'supervision',
                                                 'education_aid', 'labor_market', 'attraction_percent',
                                                 'attraction_amount', 'other_benefits', 'worker_ben',
                                                 'fixed_overtime', 'family_allowance', 'shift_allowance']]
        if self.decree:
            sets = "personnel_id=?, effective_date=?, job_wage=?, seniority_wage=?, child_allowance=?," \
                   "housing=?, food=?, adjustment_diff=?, supervision=?, education_aid=?, labor_market=?," \
                   "attraction_percent=?, attraction_amount=?, other_benefits=?, worker_ben=?," \
                   "fixed_overtime=?, family_allowance=?, shift_allowance=?"
            self.ctx.db.conn.execute(f"UPDATE decrees SET {sets} WHERE id=?", vals + [self.decree['id']])
        else:
            self.ctx.db.conn.execute(
                """INSERT INTO decrees(personnel_id,effective_date,job_wage,seniority_wage,child_allowance,
                   housing,food,adjustment_diff,supervision,education_aid,labor_market,attraction_percent,
                   attraction_amount,other_benefits,worker_ben,fixed_overtime,family_allowance,shift_allowance)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", vals)
        self.ctx.db.conn.commit()
        self.accept()
