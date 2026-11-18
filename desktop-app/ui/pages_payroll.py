# -*- coding: utf-8 -*-
"""صفحه حقوق و دستمزد (نسخه ۰.۲):
- محاسبه ماه با درصدهای بیمه فردی + هشدار پرسنل غیرفعال جدید
- لیست بانک با انتخاب ردیف‌های پرداختی + ثبت پرداخت + پیگیری مانده حقوق ماه قبل
- خروجی‌های استاندارد: فایل‌های WP/WH مالیات (راهنمای رسمی ۱.۷.۰.۴)، فایل‌های بیمه DSKKAR/DSKWOR
  + اکسل مرجع ای‌سرویس، لیست‌های اکسل بانک/مالیات/بیمه، فیش حقوقی حرفه‌ای
"""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
                               QMessageBox, QFileDialog, QComboBox, QHeaderView,
                               QProgressDialog, QApplication, QCheckBox, QLineEdit)
from core.numbers import to_persian_digits, parse_number, format_money, minutes_to_hhmm
from core import jalali as J
from core import payroll_engine as PE
from core import exports as EX
from core import standard_exports as SE
from .widgets import (setup_rtl_table, fill_table, make_table, JalaliMonthPicker,
                      MoneyEdit, TimeMinutesEdit, enable_enter_navigation)
from .help import install_f1


class PayrollPage(QWidget):
    def __init__(self, ctx, gate):
        super().__init__()
        self.ctx = ctx
        self.gate = gate
        self.period_id = None
        self._build()
        install_f1(self, 'حقوق')
        self.ctx.companyChanged.connect(self.refresh)
        self.refresh()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        title = QLabel('💰 حقوق و دستمزد')
        title.setObjectName('PageTitle')
        v.addWidget(title)
        bar = QHBoxLayout()
        bar.addWidget(QLabel('دوره:'))
        self.month_pick = JalaliMonthPicker()
        self.month_pick.currentIndexChanged.connect(self._on_month)
        btn_calc = QPushButton('⚡ محاسبه حقوق ماه')
        btn_calc.setObjectName('PrimaryBtn')
        btn_calc.clicked.connect(self.run_calc)
        btn_manual = QPushButton('✍ ورود دستی اقلام')
        btn_manual.clicked.connect(self.manual_input)
        btn_prev = QPushButton('↩ مانده حقوق ماه قبل')
        btn_prev.clicked.connect(self.edit_prev_balance)
        btn_export = QPushButton('📤 خروجی اکسل خلاصه')
        btn_export.clicked.connect(self.export_summary)
        for w in (self.month_pick, btn_calc, btn_manual, btn_prev, btn_export):
            bar.addWidget(w)
        bar.addStretch(1)
        v.addLayout(bar)
        bar2 = QHBoxLayout()
        b_bank = QPushButton('🏦 لیست بانک و پرداخت')
        b_bank.clicked.connect(self.bank_dialog)
        b_tax = QPushButton('🧾 لیست مالیات ماده ۹۷ (اکسل)')
        b_tax.clicked.connect(self.out_tax)
        b_ins = QPushButton('🛡 لیست بیمه (اکسل کامل)')
        b_ins.clicked.connect(self.out_insurance)
        for w in (b_bank, b_tax, b_ins):
            bar2.addWidget(w)
        bar2.addStretch(1)
        v.addLayout(bar2)
        bar3 = QHBoxLayout()
        b_taxfiles = QPushButton('🗃 فایل‌های استاندارد مالیات (WP/WH)')
        b_taxfiles.setObjectName('PrimaryBtn')
        b_taxfiles.clicked.connect(self.out_tax_files)
        b_insfiles = QPushButton('🗃 فایل‌های استاندارد بیمه (ای‌سرویس)')
        b_insfiles.setObjectName('PrimaryBtn')
        b_insfiles.clicked.connect(self.out_ins_files)
        b_fish = QPushButton('🧾 فیش حقوقی PDF (نفر انتخابی)')
        b_fish.clicked.connect(self.out_fish)
        b_fish_all = QPushButton('📚 فیش همه پرسنل (PDF)')
        b_fish_all.clicked.connect(self.out_fish_all)
        for w in (b_taxfiles, b_insfiles, b_fish, b_fish_all):
            bar3.addWidget(w)
        bar3.addStretch(1)
        v.addLayout(bar3)
        self.info = QLabel('')
        self.info.setStyleSheet('color:#64748b;')
        v.addWidget(self.info)
        self.table = make_table(['ردیف', 'پرسنل', 'کد', 'کارکرد (روز)', 'مرخصی', 'اضافه‌کار',
                                 'مانده ماه قبل', 'جمع درآمد', 'مشمول بیمه', 'بیمه کارگر',
                                 'مشمول مالیات', 'مالیات', 'جمع کسورات', 'قابل پرداخت',
                                 'وضعیت پرداخت'], stretch_all=False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.doubleClicked.connect(self.show_lines)
        v.addWidget(self.table, 1)
        self.totals = QLabel('')
        self.totals.setStyleSheet('font-weight:bold; color:#2563eb;')
        v.addWidget(self.totals)

    def _on_month(self):
        self.refresh()

    def _company(self):
        cur = self.ctx.db.conn.execute("SELECT * FROM companies WHERE id=?", (self.ctx.company_id,))
        r = cur.fetchone()
        return dict(r) if r else {}

    def refresh(self):
        per = self.month_pick.current_period()
        if not per or not self.ctx.fy_id:
            fill_table(self.table, [])
            return
        jy, jm = per
        cur = self.ctx.db.conn.execute(
            "SELECT id,status FROM payroll_periods WHERE fiscal_year_id=? AND jy=? AND jm=?",
            (self.ctx.fy_id, jy, jm))
        m = cur.fetchone()
        self.period_id = m['id'] if m else None
        self.info.setText(
            f"دوره {J.MONTH_NAMES[jm-1]} {to_persian_digits(str(jy))} — "
            + (f"وضعیت: {m['status']}" if m else 'هنوز محاسبه نشده — دکمه «محاسبه حقوق ماه» را بزنید'))
        if not m:
            fill_table(self.table, [])
            self.totals.setText('')
            return
        cur = self.ctx.db.conn.execute("""
            SELECT s.*, p.first_name, p.last_name, p.personnel_code
            FROM payroll_summary s JOIN personnel p ON p.id=s.personnel_id
            WHERE s.period_id=? ORDER BY p.last_name""", (self.period_id,))
        rows = [dict(r) for r in cur.fetchall()]
        self._rows = rows
        data = []
        for i, r in enumerate(rows, 1):
            data.append([to_persian_digits(str(i)), f"{r['first_name']} {r['last_name']}",
                         to_persian_digits(str(r['personnel_code'])),
                         to_persian_digits(f"{r['worked_days']:g}"), to_persian_digits(f"{r['leave_days']:g}"),
                         to_persian_digits(minutes_to_hhmm(int(r['overtime_min'] or 0))),
                         r.get('prev_balance', 0) or 0,
                         r['gross'], r['insured_base'], r['worker_ins'], r['tax_base'], r['tax'],
                         r['total_deductions'], r['net_pay'],
                         '✔ پرداخت شده' if r.get('pay_paid') else
                         ('— بدون تایید' if not r.get('pay_approved', 1) else 'در انتظار پرداخت')])
        fill_table(self.table, data, formats={5: 'money', 6: 'money', 7: 'money', 8: 'money',
                                              9: 'money', 10: 'money', 11: 'money', 12: 'money', 13: 'money'})
        if rows:
            tot_g = sum(r['gross'] for r in rows)
            tot_n = sum(r['net_pay'] for r in rows)
            tot_i = sum(r['worker_ins'] + r['employer_ins'] + r['unemployment_ins'] for r in rows)
            tot_t = sum(r['tax'] for r in rows)
            tot_p = sum(r.get('prev_balance', 0) or 0 for r in rows)
            self.totals.setText(
                f"جمع کل — درآمد: {format_money(tot_g)} | قابل پرداخت: {format_money(tot_n)} | "
                f"مانده ماه قبل: {format_money(tot_p)} | "
                f"بیمه (کارگر+کارفرما+بیکاری): {format_money(tot_i)} | مالیات: {format_money(tot_t)}")

    # ---------------- محاسبه ----------------
    def run_calc(self):
        if not self.gate.allowed('edit'):
            return
        if not self.ctx.fy_id:
            QMessageBox.warning(self, 'خطا', 'اول شرکت و سال مالی را انتخاب کنید')
            return
        per = self.month_pick.current_period()
        jy, jm = per
        db = self.ctx.db
        fy = self.ctx.fy_id
        db.conn.execute(
            "INSERT OR IGNORE INTO payroll_periods(fiscal_year_id,jy,jm) VALUES(?,?,?)", (fy, jy, jm))
        db.conn.commit()
        cur = db.conn.execute("SELECT id FROM payroll_periods WHERE fiscal_year_id=? AND jy=? AND jm=?",
                              (fy, jy, jm))
        period_id = cur.fetchone()['id']
        dim = J.days_in_month(jy, jm)
        base_settings = {k: db.get_fy_setting(fy, k) for k in
                         ['monthly_required_hours', 'sso_worker_rate', 'sso_employer_rate',
                          'sso_unemployment_rate', 'sso_ceiling_30d', 'sso_ceiling_31d',
                          'overtime_factor', 'holiday_work_factor', 'friday_work_factor',
                          'night_work_percent', 'm84_monthly_exemption']}
        brackets = db.get_tax_brackets(fy)
        items = [dict(r) for r in db.conn.execute(
            "SELECT * FROM payroll_items_config WHERE active=1 ORDER BY sort").fetchall()]
        cur = db.conn.execute("""SELECT p.* FROM personnel p WHERE p.company_id=? AND p.status='شاغل'""",
                               (self.ctx.company_id,))
        people = [dict(r) for r in cur.fetchall()]
        att = {}
        cur = db.conn.execute("SELECT id FROM attendance_months WHERE fiscal_year_id=? AND jy=? AND jm=?",
                              (fy, jy, jm))
        am = cur.fetchone()
        if am:
            att = PE.month_attendance_stats(db, am['id'], self.ctx.cal)
        # پرسنل غیرفعال/جدید با حضور در این ماه (هشدار)
        inactive = []
        cur = db.conn.execute("""SELECT p.first_name, p.last_name FROM personnel p
            JOIN attendance_daily ad ON ad.personnel_id=p.id
            JOIN attendance_months am2 ON am2.id=ad.month_id
            WHERE am2.fiscal_year_id=? AND am2.jy=? AND am2.jm=? AND p.status!='شاغل'
            GROUP BY p.id""", (fy, jy, jm))
        inactive = [dict(r) for r in cur.fetchall()]
        # مانده حقوق پرداخت‌نشده ماه قبل (همان سال مالی، ماه قبل)
        prev_map = {}
        pm = (jy, jm - 1) if jm > 1 else (jy - 1, 12)
        cur = db.conn.execute("""SELECT s.personnel_id, s.net_pay FROM payroll_summary s
            JOIN payroll_periods pp ON pp.id=s.period_id
            WHERE pp.fiscal_year_id=? AND pp.jy=? AND pp.jm=? AND s.pay_paid=0""", (fy, pm[0], pm[1]))
        for r in cur.fetchall():
            prev_map[r['personnel_id']] = r['net_pay'] or 0
        prog = QProgressDialog('در حال محاسبه حقوق…', 'لغو', 0, len(people), self)
        prog.setWindowModality(Qt.WindowModality.WindowModal)
        db.conn.execute("DELETE FROM payroll_lines WHERE period_id=?", (period_id,))
        db.conn.execute("DELETE FROM payroll_summary WHERE period_id=?", (period_id,))
        calc_count = 0
        month_end = J.format_jalali(jy, jm, dim, persian=False)
        for i, p in enumerate(people):
            prog.setValue(i)
            QApplication.processEvents()
            if prog.wasCanceled():
                break
            cur = db.conn.execute(
                "SELECT * FROM decrees WHERE personnel_id=? AND effective_date<=? ORDER BY effective_date DESC LIMIT 1",
                (p['id'], month_end))
            decree = cur.fetchone()
            decree = dict(decree) if decree else {'job_wage': 0, 'seniority_wage': 0, 'housing': 0,
                                                  'food': 0, 'child_allowance': 0, 'worker_ben': 0,
                                                  'shift_allowance': 0, 'attraction_amount': 0,
                                                  'family_allowance': 0, 'adjustment_diff': 0,
                                                  'supervision': 0, 'labor_market': 0, 'education_aid': 0,
                                                  'fixed_overtime': 0, 'other_benefits': 0,
                                                  'attraction_percent': 0}
            cur = db.conn.execute(
                "SELECT * FROM contracts WHERE personnel_id=? ORDER BY id DESC LIMIT 1", (p['id'],))
            c = cur.fetchone()
            contract = dict(c) if c else {'contract_type': 'ماهانه ثابت', 'hourly_rate': 0,
                                          'daily_rate': 0, 'project_amount': 0}
            cur = db.conn.execute("SELECT * FROM loans WHERE personnel_id=? AND active=1", (p['id'],))
            loans = [dict(r) for r in cur.fetchall()]
            cur = db.conn.execute("SELECT * FROM advances WHERE personnel_id=? AND recovered=0", (p['id'],))
            advances = [dict(r) for r in cur.fetchall()]
            cur = db.conn.execute(
                "SELECT item_code, amount FROM payroll_manual WHERE period_id=? AND personnel_id=?",
                (period_id, p['id']))
            manual = {r['item_code']: r['amount'] for r in cur.fetchall()}
            a = att.get(p['id'], {'paid_days': 0, 'overtime_hours': 0, 'holiday_hours': 0,
                                  'friday_hours': 0, 'leave_days': 0})
            # درصدهای بیمه فردی (خالی = پیش‌فرض)
            settings = dict(base_settings)
            if p.get('sso_worker_pct') is not None:
                settings['sso_worker_rate'] = str(p['sso_worker_pct'])
            if p.get('sso_employer_pct') is not None:
                settings['sso_employer_rate'] = str(p['sso_employer_pct'])
            if p.get('sso_unemp_pct') is not None:
                settings['sso_unemployment_rate'] = str(p['sso_unemp_pct'])
            if not (p.get('marital_status') == 'متاهل' and (p.get('dependents') or 0) > 0):
                decree['child_allowance'] = 0
            if p.get('marital_status') != 'متاهل':
                decree['family_allowance'] = 0
            ctx_calc = PE.EmployeeCalcContext(
                settings, brackets, decree, contract, loans, advances, manual,
                days_in_month=dim,
                paid_days=a['paid_days'],
                overtime_hours=a['overtime_hours'],
                holiday_hours=a['holiday_hours'],
                friday_hours=a['friday_hours'],
                night_hours=parse_number(manual.get('__night_hours', 0), 0),
                leave_days=a['leave_days'])
            lines, summary = PE.calc_employee(ctx_calc, items)
            for l in lines:
                db.conn.execute(
                    "INSERT INTO payroll_lines(period_id,personnel_id,item_code,amount) VALUES(?,?,?,?)",
                    (period_id, p['id'], l['item_code'], l['amount']))
            db.conn.execute(
                """INSERT INTO payroll_summary(period_id,personnel_id,worked_days,leave_days,leave_balance,
                   overtime_min,gross,insured_base,worker_ins,employer_ins,unemployment_ins,tax_base,tax,
                   total_deductions,net_pay,prev_balance,pay_approved,pay_paid)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,0)""",
                (period_id, p['id'], a['paid_days'], a['leave_days'], 0,
                 int(a['overtime_hours'] * 60), summary['gross'], summary['insured_base'],
                 summary['worker_ins'], summary['employer_ins'], summary['unemployment_ins'],
                 summary['tax_base'], summary['tax'], summary['total_deductions'], summary['net_pay'],
                 prev_map.get(p['id'], 0)))
            calc_count += 1
        prog.setValue(len(people))
        db.conn.commit()
        db.log_audit(self.ctx.auth.current_user['username'] if self.ctx.auth.current_user else '?',
                     'محاسبه حقوق', f"{jy}/{jm} — {calc_count} نفر")
        self.ctx.dataChanged.emit()
        msg = (f"حقوق {to_persian_digits(str(calc_count))} پرسنل برای "
               f"{J.MONTH_NAMES[jm-1]} {to_persian_digits(str(jy))} محاسبه شد.")
        if inactive:
            names = '، '.join(f"{r['first_name']} {r['last_name']}" for r in inactive)
            msg += ("\n\n⚠ پرسنل زیر در این ماه ساعات کارکرد دارند ولی «شاغل» نیستند و در محاسبه نیامدند —\n"
                    f"پرونده و قراردادشان را کامل کنید:\n{names}")
        QMessageBox.information(self, 'محاسبه انجام شد', msg)
        self.refresh()

    def _selected(self):
        r = self.table.currentRow()
        return self._rows[r] if getattr(self, '_rows', None) and 0 <= r < len(self._rows) else None

    def _require_period(self):
        if not self.period_id:
            QMessageBox.warning(self, 'خطا', 'اول حقوق این ماه را محاسبه کنید')
            return False
        return True

    # ---------------- مانده حقوق ماه قبل ----------------
    def edit_prev_balance(self):
        if not self._require_period() or not self.gate.allowed('edit'):
            return
        p = self._selected()
        if not p:
            QMessageBox.information(self, 'انتخاب', 'یک پرسنل را انتخاب کنید')
            return
        dlg = QDialog(self)
        dlg.setWindowTitle('مانده حقوق ماه قبل')
        f = QFormLayout(dlg)
        ed = MoneyEdit(p.get('prev_balance', 0) or 0)
        f.addRow(f"مانده پرداخت‌نشده {p['first_name']} {p['last_name']} (ریال)", ed)
        note = QLabel('این مبلغ در فیش حقوقی و لیست بانک به قابل پرداخت اضافه می‌شود. صفر = حذف مانده.')
        note.setWordWrap(True)
        f.addRow(note)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec():
            self.ctx.db.conn.execute(
                "UPDATE payroll_summary SET prev_balance=? WHERE period_id=? AND personnel_id=?",
                (ed.value(), self.period_id, p['personnel_id']))
            self.ctx.db.conn.commit()
            self.refresh()

    # ---------------- لیست بانک و پرداخت ----------------
    def bank_dialog(self):
        if not self._require_period():
            return
        dlg = BankPayDialog(self.ctx, self.period_id, self.gate)
        dlg.exec()
        self.refresh()

    # ---------------- جزئیات آیتم‌ها ----------------
    def show_lines(self):
        p = self._selected()
        if not p or not self.period_id:
            return
        cur = self.ctx.db.conn.execute("""
            SELECT i.title, l.amount, i.kind FROM payroll_lines l
            JOIN payroll_items_config i ON i.code=l.item_code
            WHERE l.period_id=? AND l.personnel_id=? ORDER BY i.sort""",
            (self.period_id, p['personnel_id']))
        rows = [dict(r) for r in cur.fetchall()]
        dlg = QDialog(self)
        dlg.setWindowTitle(f"ریز اقلام — {p['first_name']} {p['last_name']}")
        dlg.resize(500, 480)
        v = QVBoxLayout(dlg)
        t = make_table(['عنوان', 'مبلغ (ریال)'], stretch_all=True)
        earn = [r for r in rows if r['kind'] == 'earning']
        ded = [r for r in rows if r['kind'] != 'earning']
        fill_table(t, [[r['title'], r['amount']] for r in earn] +
                      [[r['title'], -r['amount']] for r in ded],
                   formats={1: 'money'})
        v.addWidget(t)
        dlg.exec()

    # ---------------- ورود دستی ----------------
    def manual_input(self):
        if not self._require_period() or not self.gate.allowed('edit'):
            return
        p = self._selected()
        if not p:
            QMessageBox.information(self, 'انتخاب', 'یک پرسنل را انتخاب کنید')
            return
        dlg = ManualInputDialog(self.ctx, self.period_id, p)
        if dlg.exec():
            self.refresh()

    # ---------------- خروجی‌ها ----------------
    def out_bank(self):
        if not self._require_period():
            return
        per, rows = EX.get_period_data(self.ctx.db, self.period_id)
        rows = [r for r in rows if r.get('pay_approved', 1)]
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره لیست بانک', f"لیست بانک {per['jy']}-{per['jm']}.xlsx", 'Excel (*.xlsx)')
        if not path:
            return
        data = EX.bank_list_rows(rows)
        EX.export_table_xlsx(
            path, 'لیست پرداخت حقوق از بانک', f"{per['company_name']} — {_period_title_fa(per)}",
            ['ردیف', 'نام و نام خانوادگی', 'کد ملی', 'شماره حساب', 'بانک',
             'مانده ماه قبل', 'خالص حقوق', 'جمع قابل پرداخت (ریال)', 'وضعیت'],
            data, money_cols={5, 6, 7}, sum_cols={5, 6, 7},
            company=self._company())
        QMessageBox.information(self, 'ذخیره شد', path)

    def out_tax(self):
        if not self._require_period():
            return
        per, rows = EX.get_period_data(self.ctx.db, self.period_id)
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره لیست مالیات', f"لیست مالیات {per['jy']}-{per['jm']}.xlsx", 'Excel (*.xlsx)')
        if not path:
            return
        data = EX.tax_list_rows(rows)
        EX.export_table_xlsx(
            path, 'فهرست مالیات حقوق (ماده ۹۷)', f"{per['company_name']} — {_period_title_fa(per)}",
            ['ردیف', 'نام و نام خانوادگی', 'کد ملی', 'جمع درآمد', 'درآمد مشمول مالیات', 'مالیات پرداختی'],
            data, money_cols={3, 4, 5}, sum_cols={3, 4, 5}, company=self._company())
        QMessageBox.information(self, 'ذخیره شد', path)

    def out_insurance(self):
        if not self._require_period():
            return
        per, rows = EX.get_period_data(self.ctx.db, self.period_id)
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره لیست بیمه', f"لیست بیمه {per['jy']}-{per['jm']}.xlsx", 'Excel (*.xlsx)')
        if not path:
            return
        data = EX.insurance_list_rows(rows)
        EX.export_table_xlsx(
            path, 'لیست بیمه تامین اجتماعی', f"{per['company_name']} — {_period_title_fa(per)}",
            ['ردیف', 'شماره بیمه', 'نام و نام خانوادگی', 'روز بیمه', 'حقوق مشمول بیمه',
             'سهم کارگر (۷٪)', 'سهم کارفرما (۲۰٪)', 'بیکاری (۳٪)', 'جمع حق بیمه'],
            data, money_cols={4, 5, 6, 7, 8}, sum_cols={4, 5, 6, 7, 8},
            company=self._company())
        QMessageBox.information(self, 'ذخیره شد', path)

    def out_tax_files(self):
        """فایل‌های استاندارد مالیات WP/WH + اکسل کنترلی WH"""
        if not self._require_period():
            return
        folder = QFileDialog.getExistingDirectory(self, 'پوشه ذخیره فایل‌های مالیات')
        if not folder:
            return
        per, rows = EX.get_period_data(self.ctx.db, self.period_id)
        try:
            wp, wh = SE.make_tax_files(self.ctx.db, self.period_id, rows, self._company(), folder)
            path_x = os.path.join(folder, f"کنترل WH {per['jy']}-{per['jm']}.xlsx")
            SE.make_wh_excel(path_x, SE.tax_wh_records(self.ctx.db, self.period_id, rows),
                             self._company(), _period_title_fa(per))
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'ساخت فایل ممکن نشد: {e}')
            return
        QMessageBox.information(
            self, 'فایل‌های مالیات ساخته شد',
            f"دو فایل استاندارد طبق راهنمای رسمی سازمان امور مالیاتی (نسخه ۱.۷.۰.۴) ساخته شد:\n\n"
            f"• {os.path.basename(wp)}  ← فهرست کارکنان\n"
            f"• {os.path.basename(wh)}  ← فهرست حقوق\n"
            f"• {os.path.basename(path_x)}  ← اکسل کنترلی\n\n"
            "بارگذاری در: salary.tax.gov.ir → فهرست حقوق → فهرست حقوق جدید\n"
            "(فایل WP فقط بار اول یا برای پرسنل جدید/تغییری لازم است؛ فایل WK در ساختار جدید حذف شده است)")

    def out_ins_files(self):
        """فایل‌های استاندارد بیمه DSKKAR/DSKWOR + اکسل مرجع"""
        if not self._require_period():
            return
        folder = QFileDialog.getExistingDirectory(self, 'پوشه ذخیره فایل‌های بیمه')
        if not folder:
            return
        per, rows = EX.get_period_data(self.ctx.db, self.period_id)
        try:
            kar, wor = SE.make_insurance_files(self.ctx.db, self.period_id, rows,
                                               self._company(), folder)
            path_x = os.path.join(folder, f"ریزکارکرد بیمه {per['jy']}-{per['jm']}.xlsx")
            SE.insurance_excel(path_x, rows, self._company(), _period_title_fa(per))
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'ساخت فایل ممکن نشد: {e}')
            return
        QMessageBox.information(
            self, 'فایل‌های بیمه ساخته شد',
            "فایل‌های استاندارد «لیست دیسک» تامین اجتماعی ساخته شد:\n\n"
            "• DSKKAR00.dbf ← اطلاعات ماهیانه کارگاه\n"
            "• DSKWOR00.dbf ← اطلاعات ماهیانه بیمه‌شدگان (ریزکارکرد)\n"
            f"• {os.path.basename(path_x)} ← اکسل مرجع (لیست ماهانه + ریزکارکرد)\n\n"
            "بارگذاری در: eservices.tamin.ir → کارفرمایان → لیست حق بیمه → بارگذاری فایل اطلاعات\n"
            "نکته: ساختار DBF مطابق قالب نرم‌افزار رسمی است؛ بار اول یک بار آزمایشی در سامانه "
            "بارگذاری کنید. اکسل مرجع برای ورود آنلاین مطمئن است.")

    def out_fish(self):
        if not self._require_period():
            return
        p = self._selected()
        if not p:
            QMessageBox.information(self, 'انتخاب', 'یک پرسنل را انتخاب کنید')
            return
        path, _ = QFileDialog.getSaveFileName(
            self, 'ذخیره فیش', f"فیش {p['last_name']}.pdf", 'PDF (*.pdf)')
        if not path:
            return
        self._make_fish(p['personnel_id'], path)
        QMessageBox.information(self, 'ذخیره شد', path)

    def out_fish_all(self):
        if not self._require_period():
            return
        folder = QFileDialog.getExistingDirectory(self, 'پوشه ذخیره فیش‌ها')
        if not folder:
            return
        per, rows = EX.get_period_data(self.ctx.db, self.period_id)
        prog = QProgressDialog('صدور فیش‌ها…', 'لغو', 0, len(rows), self)
        prog.setWindowModality(Qt.WindowModality.WindowModal)
        for i, r in enumerate(rows):
            prog.setValue(i)
            QApplication.processEvents()
            if prog.wasCanceled():
                break
            fname = f"فیش {r['personnel_code']} - {r['last_name']}.pdf".replace('/', '-')
            self._make_fish(r['personnel_id'], os.path.join(folder, fname))
        prog.setValue(len(rows))
        QMessageBox.information(self, 'انجام شد', f"{to_persian_digits(str(len(rows)))} فیش در پوشه ذخیره شد.")

    def _make_fish(self, personnel_id, path):
        per, rows = EX.get_period_data(self.ctx.db, self.period_id)
        person = next(r for r in rows if r['personnel_id'] == personnel_id)
        cur = self.ctx.db.conn.execute("""
            SELECT i.title, l.amount, i.kind FROM payroll_lines l
            JOIN payroll_items_config i ON i.code=l.item_code
            WHERE l.period_id=? AND l.personnel_id=? ORDER BY i.sort""",
            (self.period_id, personnel_id))
        items_rows = [(r['title'], r['amount'], '', r['kind']) for r in cur.fetchall()]
        theme = self.ctx.theme_mgr.current()
        EX.payslip_pdf(path, per, person, _period_title_fa(per), items_rows,
                       person, report_bg=theme.get('report_bg', '#ffffff'))

    def export_summary(self):
        if not self._require_period():
            return
        per, rows = EX.get_period_data(self.ctx.db, self.period_id)
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره خلاصه', f"خلاصه حقوق {per['jy']}-{per['jm']}.xlsx", 'Excel (*.xlsx)')
        if not path:
            return
        headers = ['کد پرسنلی', 'نام و نام خانوادگی', 'کارکرد (روز)', 'مرخصی', 'مانده ماه قبل',
                   'جمع درآمد', 'مشمول بیمه', 'بیمه کارگر', 'بیمه کارفرما', 'بیکاری',
                   'مشمول مالیات', 'مالیات', 'جمع کسورات', 'قابل پرداخت']
        data = [[r['personnel_code'], f"{r['first_name']} {r['last_name']}", r['worked_days'],
                 r['leave_days'], r.get('prev_balance', 0) or 0, r['gross'], r['insured_base'],
                 r['worker_ins'], r['employer_ins'], r['unemployment_ins'], r['tax_base'], r['tax'],
                 r['total_deductions'], r['net_pay']] for r in rows]
        EX.export_table_xlsx(path, 'خلاصه حقوق و دستمزد', f"{per['company_name']} — {_period_title_fa(per)}",
                             headers, data, money_cols=set(range(4, 14)), sum_cols=set(range(4, 14)),
                             company=self._company())
        QMessageBox.information(self, 'ذخیره شد', path)


class BankPayDialog(QDialog):
    """لیست بانک با تیک پرداخت + ثبت وضعیت + خروجی فقط تاییدشده‌ها"""
    def __init__(self, ctx, period_id, gate):
        super().__init__()
        self.ctx = ctx
        self.gate = gate
        self.period_id = period_id
        self.setWindowTitle('لیست بانک و کنترل پرداخت')
        self.resize(980, 560)
        v = QVBoxLayout(self)
        bar = QHBoxLayout()
        b_pay = QPushButton('✅ ثبت پرداخت انتخاب‌ها')
        b_pay.setObjectName('PrimaryBtn')
        b_pay.clicked.connect(lambda: self.mark(1))
        b_unpay = QPushButton('↩ ثبت نپرداخته انتخاب‌ها')
        b_unpay.clicked.connect(lambda: self.mark(0))
        b_xls = QPushButton('📤 خروجی اکسل (فقط تاییدشده)')
        b_xls.clicked.connect(self.export_xlsx)
        b_pdf = QPushButton('🖨 چاپ PDF (فقط تاییدشده)')
        b_pdf.clicked.connect(self.export_pdf)
        b_all = QPushButton('انتخاب همه')
        b_all.clicked.connect(lambda: self.check_all(True))
        b_none = QPushButton('لغو انتخاب همه')
        b_none.clicked.connect(lambda: self.check_all(False))
        for w in (b_pay, b_unpay, b_xls, b_pdf, b_all, b_none):
            bar.addWidget(w)
        bar.addStretch(1)
        v.addLayout(bar)
        self.table = make_table(['پرداخت شود', 'پرسنل', 'کد', 'شماره حساب', 'بانک',
                                 'مانده ماه قبل', 'خالص حقوق', 'جمع قابل پرداخت', 'وضعیت فعلی'],
                                stretch_all=False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        v.addWidget(self.table, 1)
        self.load()

    def load(self):
        per, rows = EX.get_period_data(self.ctx.db, self.period_id)
        self._rows = rows
        self.table.setRowCount(len(rows))
        for r, p in enumerate(rows):
            cb = QCheckBox()
            cb.setChecked(bool(p.get('pay_approved', 1)))
            self.table.setCellWidget(r, 0, cb)
            vals = [f"{p['first_name']} {p['last_name']}",
                    to_persian_digits(str(p['personnel_code'])),
                    to_persian_digits(str(p['bank_account'] or '')),
                    p['bank_name'] or '',
                    p.get('prev_balance', 0) or 0, p['net_pay'],
                    (p['net_pay'] or 0) + (p.get('prev_balance', 0) or 0),
                    '✔ پرداخت شده' if p.get('pay_paid') else 'در انتظار پرداخت']
            for c, val in enumerate(vals, 1):
                it = QTableWidgetItem(val if not isinstance(val, (int, float)) else format_money(val))
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, it)

    def check_all(self, state):
        for r in range(self.table.rowCount()):
            cb = self.table.cellWidget(r, 0)
            if cb:
                cb.setChecked(state)

    def mark(self, paid):
        if not self.gate.allowed('edit'):
            return
        n = 0
        for r, p in enumerate(self._rows):
            cb = self.table.cellWidget(r, 0)
            if cb and cb.isChecked():
                self.ctx.db.conn.execute(
                    "UPDATE payroll_summary SET pay_paid=?, pay_approved=1 WHERE period_id=? AND personnel_id=?",
                    (paid, self.period_id, p['personnel_id']))
                n += 1
        self.ctx.db.conn.commit()
        self.ctx.db.log_audit(self.ctx.auth.current_user['username'] if self.ctx.auth.current_user else '?',
                              'ثبت پرداخت بانکی', f"period={self.period_id} — {n} نفر — paid={paid}")
        self.load()
        QMessageBox.information(self, 'ثبت شد', f"وضعیت {to_persian_digits(str(n))} نفر به‌روزرسانی شد.")

    def _approved_rows(self):
        out = []
        for r, p in enumerate(self._rows):
            cb = self.table.cellWidget(r, 0)
            if cb and cb.isChecked():
                out.append(p)
        return out

    def export_xlsx(self):
        rows = self._approved_rows()
        if not rows:
            QMessageBox.information(self, 'خروجی', 'هیچ ردیفی تایید نشده است')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره', 'لیست بانک.xlsx', 'Excel (*.xlsx)')
        if not path:
            return
        data = EX.bank_list_rows(rows)
        cur = self.ctx.db.conn.execute("SELECT * FROM companies WHERE id=?", (self.ctx.company_id,))
        comp = dict(cur.fetchone() or {})
        EX.export_table_xlsx(
            path, 'لیست پرداخت حقوق از بانک',
            f"{comp.get('name', self.ctx.company_name)} — "
            f"{J.MONTH_NAMES[self.month_pick_month()[1]-1]} {to_persian_digits(str(self.month_pick_month()[0]))}",
            ['ردیف', 'نام و نام خانوادگی', 'کد ملی', 'شماره حساب', 'بانک',
             'مانده ماه قبل', 'خالص حقوق', 'جمع قابل پرداخت (ریال)', 'وضعیت'],
            data, money_cols={5, 6, 7}, sum_cols={5, 6, 7}, company=comp)

    def export_pdf(self):
        rows = self._approved_rows()
        if not rows:
            QMessageBox.information(self, 'چاپ', 'هیچ ردیفی تایید نشده است')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره', 'لیست بانک.pdf', 'PDF (*.pdf)')
        if not path:
            return
        cur = self.ctx.db.conn.execute("SELECT * FROM companies WHERE id=?", (self.ctx.company_id,))
        comp = dict(cur.fetchone() or {})
        jy, jm = self.month_pick_month()
        data = EX.bank_list_rows(rows)
        EX.report_pdf(path, comp, 'لیست پرداخت حقوق از بانک',
                      f"{J.MONTH_NAMES[jm-1]} {to_persian_digits(str(jy))}",
                      ['ردیف', 'نام و نام خانوادگی', 'کد ملی', 'شماره حساب', 'بانک',
                       'مانده ماه قبل', 'خالص حقوق', 'جمع قابل پرداخت', 'وضعیت'],
                      data, money_cols={5, 6, 7})

    def month_pick_month(self):
        cur = self.ctx.db.conn.execute("SELECT jy, jm FROM payroll_periods WHERE id=?", (self.period_id,))
        r = cur.fetchone()
        return (r['jy'], r['jm']) if r else (0, 0)


class ManualInputDialog(QDialog):
    """ورود دستی اقلام برای پرسنل انتخابی + ساعات شب‌کاری"""
    def __init__(self, ctx, period_id, person):
        super().__init__()
        self.ctx = ctx
        self.period_id = period_id
        self.person = person
        self.setWindowTitle(f"ورود دستی اقلام — {person['first_name']} {person['last_name']}")
        self.resize(500, 440)
        v = QVBoxLayout(self)
        f = QFormLayout()
        cur = ctx.db.conn.execute(
            "SELECT * FROM payroll_items_config WHERE active=1 ORDER BY kind, sort")
        self._items = [dict(r) for r in cur.fetchall()]
        self.edits = {}
        for it in self._items:
            if it['kind'] == 'employer' or it['system_locked']:
                continue
            if it['formula_key'] != 'manual':
                continue
            ed = MoneyEdit(0)
            self.edits[it['code']] = ed
            f.addRow(it['title'], ed)
        night = TimeMinutesEdit(0)
        self.edits['__night_hours'] = night
        f.addRow('ساعات شب‌کاری (H:MM — ۲۲ تا ۶)', night)
        cur = ctx.db.conn.execute(
            "SELECT item_code, amount FROM payroll_manual WHERE period_id=? AND personnel_id=?",
            (period_id, person['id']))
        for r in cur.fetchall():
            if r['item_code'] in self.edits:
                ed = self.edits[r['item_code']]
                if isinstance(ed, TimeMinutesEdit):
                    ed.set_minutes(int(r['amount']))
                else:
                    ed.set_value(r['amount'])
        v.addLayout(f)
        note = QLabel('نکته: اقلامی که فرمولشان «ثابت - مقدار دستی» است اینجا وارد می‌شوند و در محاسبه بعدی اعمال می‌شوند.')
        note.setWordWrap(True)
        note.setStyleSheet('color:#64748b;')
        v.addWidget(note)
        from PySide6.QtWidgets import QDialogButtonBox
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.save)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        enable_enter_navigation(self)

    def save(self):
        for code, ed in self.edits.items():
            if isinstance(ed, TimeMinutesEdit):
                amount = float(ed.minutes())
            else:
                amount = ed.value()
            self.ctx.db.conn.execute(
                "INSERT OR REPLACE INTO payroll_manual(period_id,personnel_id,item_code,amount) VALUES(?,?,?,?)",
                (self.period_id, self.person['id'], code, amount))
        self.ctx.db.conn.commit()
        self.accept()


def _period_title_fa(per):
    return f"{J.MONTH_NAMES[per['jm']-1]} {to_persian_digits(str(per['jy']))}"
