# -*- coding: utf-8 -*-
"""صفحه حضور و غیاب (نسخه ۰.۲):
- ایمپورت فایل دستگاه + تشخیص خودکار پرسنل جدید (غیرفعال) + بازمحاسبه تاخیر/تعجیل طبق شیفت و بازه مجاز
- مدیریت شیفت‌های کاری (تعریف + انتساب ماهانه به هر فرد)
- جزئیات روزانه هر نفر: ویرایش/حذف دستی + بازمحاسبه
- خروجی فردی دقیقا مطابق فرمت «گزارش روزانه فردی» دستگاه (اکسل + PDF) و خروجی خلاصه ماه
"""
import os
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
                               QComboBox, QMessageBox, QFileDialog, QLineEdit,
                               QDialogButtonBox, QHeaderView, QInputDialog, QGridLayout,
                               QGroupBox, QTabWidget, QListWidget)
import jdatetime
from core.numbers import to_persian_digits, minutes_to_hhmm, parse_hhmm, normalize_digits
from core import jalali as J
from core import attendance_import as AI
from core import shifts as SH
from core import exports as EX
from .widgets import (setup_rtl_table, fill_table, make_table, JalaliMonthPicker,
                      JalaliDatePicker, TimeMinutesEdit, enable_enter_navigation)
from .help import install_f1

DEVICE_EXPORT_COLS = [('تاریخ', 'date'), ('روز هفته', 'wd'), ('ورود1', 'entry1'), ('خروج1', 'exit1'),
                      ('ورود2', 'entry2'), ('خروج2', 'exit2'), ('ورود3', 'entry3'), ('خروج3', 'exit3'),
                      ('مجموع', 'worked_min'), ('کارکرد', 'work_min'), ('ماموریت', 'mission_min'),
                      ('مرخصی', 'leave_min'), ('تاخیر', 'late_min'), ('تعجیل', 'early_min'),
                      ('کسرکار', 'missing_min'), ('اضافه کار', 'overtime_min'),
                      ('اضافه آزاد', 'free_overtime_min'), ('وضعیت', 'status')]


class AttendancePage(QWidget):
    def __init__(self, ctx, gate):
        super().__init__()
        self.ctx = ctx
        self.gate = gate
        self.month_id = None
        self._build()
        install_f1(self, 'حضور')
        self.ctx.companyChanged.connect(self.refresh)
        self.refresh()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        title = QLabel('⏱ حضور و غیاب')
        title.setObjectName('PageTitle')
        v.addWidget(title)
        bar = QHBoxLayout()
        self.month_pick = JalaliMonthPicker()
        self.month_pick.currentIndexChanged.connect(self.refresh)
        btn_import = QPushButton('📥 ایمپورت فایل دستگاه')
        btn_import.setObjectName('PrimaryBtn')
        btn_import.clicked.connect(self.import_device)
        btn_shifts = QPushButton('⏲ شیفت‌های کاری')
        btn_shifts.clicked.connect(self.manage_shifts)
        btn_recalc = QPushButton('♻️ بازمحاسبه ماه')
        btn_recalc.clicked.connect(self.recalc_month)
        btn_daily = QPushButton('📋 جزئیات روزانه پرسنل')
        btn_daily.clicked.connect(self.show_daily)
        btn_leave = QPushButton('🌴 ثبت مرخصی')
        btn_leave.clicked.connect(self.add_leave)
        btn_leaves = QPushButton('📄 لیست مرخصی‌ها')
        btn_leaves.clicked.connect(self.show_leaves)
        for w in (QLabel('ماه:'), self.month_pick, btn_import, btn_shifts, btn_recalc,
                  btn_daily, btn_leave, btn_leaves):
            bar.addWidget(w)
        bar.addStretch(1)
        v.addLayout(bar)
        bar2 = QHBoxLayout()
        b_exp1 = QPushButton('📤 خروجی فردی مطابق دستگاه (اکسل)')
        b_exp1.clicked.connect(self.export_person_xlsx)
        b_exp2 = QPushButton('🖨 خروجی فردی (PDF)')
        b_exp2.clicked.connect(self.export_person_pdf)
        b_exp3 = QPushButton('📤 خروجی اکسل ماه (همه پرسنل)')
        b_exp3.clicked.connect(self.export_xlsx)
        for w in (b_exp1, b_exp2, b_exp3):
            bar2.addWidget(w)
        bar2.addStretch(1)
        v.addLayout(bar2)
        self.info = QLabel('')
        self.info.setStyleSheet('color:#64748b;')
        v.addWidget(self.info)
        self.table = make_table(['ردیف', 'پرسنل', 'کد', 'شماره کارت', 'وضعیت پرسنل', 'روزهای کارکرد',
                                 'مجموع کارکرد', 'اضافه‌کار', 'اضافه آزاد', 'کسرکار',
                                 'تاخیر', 'تعجیل', 'مرخصی', 'ماموریت'])
        v.addWidget(self.table, 1)

    # ---------------- ایمپورت دستگاه ----------------
    def import_device(self):
        if not self.gate.allowed('edit'):
            return
        if not self.ctx.fy_id:
            QMessageBox.warning(self, 'خطا', 'اول شرکت و سال مالی را انتخاب کنید')
            return
        path, _ = QFileDialog.getOpenFileName(
            self, 'انتخاب فایل خروجی دستگاه حضور و غیاب', '', 'Excel (*.xls *.xlsx)')
        if not path:
            return
        try:
            parsed = AI.parse_device_file(path)
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خواندن فایل دستگاه ممکن نشد:\n{e}')
            return
        if not parsed['employees']:
            QMessageBox.critical(self, 'خطا', 'هیچ پرسنلی در فایل پیدا نشد — ساختار فایل مطابق «گزارش روزانه فردی» نیست')
            return
        per = parsed['period'] or parsed['employees'][0].get('period')
        jy, jm = per[0], per[1]
        confirm = QMessageBox.question(
            self, 'تایید ایمپورت',
            f"فایل شامل {to_persian_digits(str(len(parsed['employees'])))} پرسنل برای "
            f"«{J.MONTH_NAMES[jm-1]} {to_persian_digits(str(jy))}» است.\n"
            "داده‌های قبلی این ماه جایگزین می‌شود. ادامه می‌دهید؟")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        res = AI.save_to_db(self.ctx.db, self.ctx.fy_id, parsed, self.ctx.cal,
                            company_id=self.ctx.company_id)
        self.ctx.dataChanged.emit()
        msg = (f"ذخیره شد برای {to_persian_digits(str(res['saved']))} پرسنل.\n"
               f"دوره: {J.MONTH_NAMES[jm-1]} {to_persian_digits(str(jy))}\n"
               "تاخیر/تعجیل/کسرکار طبق شیفت و بازه مجاز بازمحاسبه شد.")
        if res.get('new_employees'):
            names = '، '.join(res['new_employees'])
            msg += ("\n\n⚠ پرسنل جدید برای این ماه ثبت شد (وضعیت: غیرفعال) — اطلاعات پرسنل و "
                    f"قرارداد این افراد را در صفحه «پرسنل» کامل کنید:\n{names}")
        QMessageBox.information(self, 'ایمپورت حضور و غیاب', msg)
        self.refresh()

    def recalc_month(self):
        if not self.month_id:
            QMessageBox.information(self, 'بازمحاسبه', 'برای این ماه داده‌ای نیست — اول ایمپورت کنید')
            return
        if not self.gate.allowed('edit'):
            return
        from core.numbers import parse_number
        gl = int(parse_number(self.ctx.fy_setting('late_grace_minutes', '10'), 10))
        ge = int(parse_number(self.ctx.fy_setting('early_grace_minutes', '10'), 10))
        cur = self.ctx.db.conn.execute("SELECT jy,jm FROM attendance_months WHERE id=?", (self.month_id,))
        m = cur.fetchone()
        lm = SH.leaves_map_for_month(self.ctx.db, self.month_id, m['jy'], m['jm'])
        n = SH.recalc_month(self.ctx.db, self.month_id, self.ctx.cal, gl, ge, lm)
        QMessageBox.information(self, 'بازمحاسبه شد',
                                f"{to_persian_digits(str(n))} روز بر اساس شیفت و بازه مجاز "
                                f"({to_persian_digits(str(gl))} دقیقه تاخیر / "
                                f"{to_persian_digits(str(ge))} دقیقه تعجیل) بازمحاسبه شد.")
        self.refresh()

    # ---------------- خلاصه ماه ----------------
    def refresh(self):
        per = self.month_pick.current_period()
        if not per or not self.ctx.fy_id:
            fill_table(self.table, [])
            self.month_id = None
            return
        jy, jm = per
        cur = self.ctx.db.conn.execute(
            "SELECT id FROM attendance_months WHERE fiscal_year_id=? AND jy=? AND jm=?",
            (self.ctx.fy_id, jy, jm))
        m = cur.fetchone()
        self.month_id = m['id'] if m else None
        if not m:
            self.info.setText('⚠ برای این ماه هنوز داده‌ای وارد نشده — فایل دستگاه را ایمپورت کنید یا دستی ثبت کنید.')
            fill_table(self.table, [])
            return
        self.info.setText('')
        cur = self.ctx.db.conn.execute("""
            SELECT p.id, p.first_name, p.last_name, p.personnel_code, p.card_no, p.status as pstatus,
                   SUM(CASE WHEN ad.worked_min>0 THEN 1 ELSE 0 END) as present_days,
                   SUM(ad.worked_min) as worked, SUM(ad.overtime_min) as ot,
                   SUM(ad.free_overtime_min) as fot, SUM(ad.missing_min) as missing,
                   SUM(ad.late_min) as late, SUM(ad.early_min) as early,
                   SUM(ad.leave_min) as lv, SUM(ad.mission_min) as mission
            FROM attendance_daily ad JOIN personnel p ON p.id=ad.personnel_id
            WHERE ad.month_id=? GROUP BY p.id ORDER BY p.last_name""", (self.month_id,))
        rows = [dict(r) for r in cur.fetchall()]
        self._rows = rows
        data = []
        for i, r in enumerate(rows, 1):
            data.append([to_persian_digits(str(i)),
                         f"{r['first_name']} {r['last_name']}",
                         to_persian_digits(str(r['personnel_code'])),
                         to_persian_digits(str(r['card_no'] or '')),
                         r['pstatus'] or '',
                         to_persian_digits(str(r['present_days'] or 0)),
                         to_persian_digits(minutes_to_hhmm(r['worked'] or 0)),
                         to_persian_digits(minutes_to_hhmm(r['ot'] or 0)),
                         to_persian_digits(minutes_to_hhmm(r['fot'] or 0)),
                         to_persian_digits(minutes_to_hhmm(r['missing'] or 0)),
                         to_persian_digits(minutes_to_hhmm(r['late'] or 0)),
                         to_persian_digits(minutes_to_hhmm(r['early'] or 0)),
                         to_persian_digits(minutes_to_hhmm(r['lv'] or 0)),
                         to_persian_digits(minutes_to_hhmm(r['mission'] or 0))])
        fill_table(self.table, data)

    def _selected(self):
        r = self.table.currentRow()
        return self._rows[r] if getattr(self, '_rows', None) and 0 <= r < len(self._rows) else None

    # ---------------- جزئیات روزانه ----------------
    def show_daily(self):
        p = self._selected()
        if not p:
            QMessageBox.information(self, 'انتخاب', 'یک پرسنل را انتخاب کنید')
            return
        dlg = DailyDialog(self.ctx, self.month_id, p, self.gate)
        dlg.exec()
        self.refresh()

    # ---------------- شیفت‌ها ----------------
    def manage_shifts(self):
        if not self.ctx.company_id:
            QMessageBox.warning(self, 'خطا', 'اول شرکت را انتخاب کنید')
            return
        dlg = ShiftsDialog(self.ctx)
        dlg.exec()
        self.ctx.dataChanged.emit()
        self.refresh()

    # ---------------- مرخصی ----------------
    def add_leave(self):
        if not self.gate.allowed('edit'):
            return
        p = self._selected()
        if not p:
            QMessageBox.information(self, 'انتخاب', 'ابتدا یک پرسنل را در جدول انتخاب کنید')
            return
        dlg = LeaveDialog(self.ctx, p)
        if dlg.exec():
            self.refresh()

    def show_leaves(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('لیست مرخصی‌ها')
        dlg.resize(820, 440)
        v = QVBoxLayout(dlg)
        t = make_table(['پرسنل', 'از تاریخ', 'تا تاریخ', 'روز', 'نوع', 'تاییدشده'])
        if self.ctx.fy_id:
            cur = self.ctx.db.conn.execute("""
                SELECT l.*, p.first_name, p.last_name FROM leaves l
                JOIN personnel p ON p.id=l.personnel_id
                JOIN fiscal_years fy ON fy.company_id=p.company_id WHERE fy.id=?
                ORDER BY l.from_date DESC""", (self.ctx.fy_id,))
            fill_table(t, [[f"{r['first_name']} {r['last_name']}",
                            to_persian_digits(str(r['from_date'])), to_persian_digits(str(r['to_date'])),
                            to_persian_digits(str(r['days'])), r['leave_kind'],
                            'بله' if r['approved'] else 'خیر'] for r in cur.fetchall()])
        v.addWidget(t)
        dlg.exec()

    # ---------------- خروجی‌ها ----------------
    def _person_daily_rows(self, person):
        """ردیف‌های روزانه یک نفر در ماه جاری به فرمت دستگاه"""
        cur = self.ctx.db.conn.execute("SELECT jy,jm FROM attendance_months WHERE id=?", (self.month_id,))
        m = cur.fetchone()
        if not m:
            return None, []
        jy, jm = m['jy'], m['jm']
        cur = self.ctx.db.conn.execute(
            "SELECT * FROM attendance_daily WHERE month_id=? AND personnel_id=? ORDER BY day",
            (self.month_id, person['id']))
        rows = {r['day']: dict(r) for r in cur.fetchall()}
        out = []
        for d in range(1, J.days_in_month(jy, jm) + 1):
            r = rows.get(d)

            def t(key, r=r):
                if not r:
                    return ''
                v = r.get(key)
                if key in ('entry1', 'exit1', 'entry2', 'exit2', 'entry3', 'exit3'):
                    return minutes_to_hhmm(v) if v is not None and v >= 0 else ''
                return minutes_to_hhmm(v or 0)
            date = f"{jy}/{jm:02d}/{d:02d}"
            worked = (r.get('worked_min') or 0) if r else 0
            ot = ((r.get('overtime_min') or 0) + (r.get('free_overtime_min') or 0)) if r else 0
            out.append({
                'date': to_persian_digits(date), 'wd': J.weekday_name(jy, jm, d),
                'entry1': t('entry1'), 'exit1': t('exit1'), 'entry2': t('entry2'), 'exit2': t('exit2'),
                'entry3': t('entry3'), 'exit3': t('exit3'),
                'worked_min': t('worked_min'),
                'work_min': minutes_to_hhmm(max(0, worked - ot)) if r else '',
                'mission_min': t('mission_min'), 'leave_min': t('leave_min'),
                'late_min': t('late_min'), 'early_min': t('early_min'),
                'missing_min': t('missing_min'), 'overtime_min': t('overtime_min'),
                'free_overtime_min': t('free_overtime_min'),
                'status': (r.get('status') or '') if r else '',
            })
        return (jy, jm), out

    def export_person_xlsx(self):
        p = self._selected()
        if not p or not self.month_id:
            QMessageBox.information(self, 'انتخاب', 'یک پرسنل را انتخاب کنید')
            return
        per, rows = self._person_daily_rows(p)
        path, _ = QFileDialog.getSaveFileName(
            self, 'ذخیره', f"گزارش روزانه فردی {p['last_name']}.xlsx", 'Excel (*.xlsx)')
        if not path:
            return
        headers = [c[0] for c in DEVICE_EXPORT_COLS]
        data = [[r[c[1]] for c in DEVICE_EXPORT_COLS] for r in rows]
        company = self._company()
        EX.export_table_xlsx(
            path, 'گزارش روزانه فردی',
            f"{company.get('name', '')} — {p['first_name']} {p['last_name']} — "
            f"{J.MONTH_NAMES[per[1]-1]} {to_persian_digits(str(per[0]))}",
            headers, data, company=company)
        QMessageBox.information(self, 'ذخیره شد', path)

    def export_person_pdf(self):
        p = self._selected()
        if not p or not self.month_id:
            QMessageBox.information(self, 'انتخاب', 'یک پرسنل را انتخاب کنید')
            return
        per, rows = self._person_daily_rows(p)
        path, _ = QFileDialog.getSaveFileName(
            self, 'ذخیره', f"گزارش روزانه فردی {p['last_name']}.pdf", 'PDF (*.pdf)')
        if not path:
            return
        headers = [c[0] for c in DEVICE_EXPORT_COLS]
        data = [[r[c[1]] for c in DEVICE_EXPORT_COLS] for r in rows]
        company = self._company()
        EX.report_pdf(path, company, 'گزارش روزانه فردی',
                      f"{p['first_name']} {p['last_name']} — "
                      f"{J.MONTH_NAMES[per[1]-1]} {to_persian_digits(str(per[0]))}",
                      headers, data, landscape=True)
        QMessageBox.information(self, 'ذخیره شد', path)

    def _company(self):
        cur = self.ctx.db.conn.execute("SELECT * FROM companies WHERE id=?", (self.ctx.company_id,))
        r = cur.fetchone()
        return dict(r) if r else {}

    def export_xlsx(self):
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره', 'حضور و غیاب.xlsx', 'Excel (*.xlsx)')
        if not path:
            return
        per = self.month_pick.current_period()
        headers = ['پرسنل', 'کد', 'وضعیت', 'روزهای کارکرد', 'مجموع کارکرد', 'اضافه‌کار', 'اضافه آزاد',
                   'کسرکار', 'تاخیر', 'تعجیل', 'مرخصی', 'ماموریت']
        data = [[f"{r['first_name']} {r['last_name']}", r['personnel_code'], r.get('pstatus', ''),
                 r['present_days'] or 0, minutes_to_hhmm(r['worked'] or 0),
                 minutes_to_hhmm(r['ot'] or 0), minutes_to_hhmm(r['fot'] or 0),
                 minutes_to_hhmm(r['missing'] or 0), minutes_to_hhmm(r['late'] or 0),
                 minutes_to_hhmm(r['early'] or 0), minutes_to_hhmm(r['lv'] or 0),
                 minutes_to_hhmm(r['mission'] or 0)] for r in getattr(self, '_rows', [])]
        EX.export_table_xlsx(path, 'گزارش حضور و غیاب',
                             f"{self.ctx.company_name} — {J.MONTH_NAMES[per[1]-1]} {to_persian_digits(str(per[0]))}",
                             headers, data, company=self._company())


# ================= شیفت‌های کاری =================
WEEKDAYS = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']


class ShiftsDialog(QDialog):
    """تعریف شیفت‌ها و انتساب ماهانه به پرسنل"""
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle('شیفت‌های کاری')
        self.resize(860, 560)
        v = QVBoxLayout(self)
        tabs = QTabWidget()
        v.addWidget(tabs, 1)
        tabs.addTab(self._tab_defs(), 'تعریف شیفت')
        tabs.addTab(self._tab_assign(), 'انتساب به پرسنل')
        self.load_list()

    def _tab_defs(self):
        w = QWidget()
        h = QHBoxLayout(w)
        # لیست شیفت‌ها
        left = QVBoxLayout()
        left.addWidget(QLabel('شیفت‌های تعریف‌شده:'))
        self.listw = QListWidget()
        self.listw.currentRowChanged.connect(self.load_editor)
        left.addWidget(self.listw, 1)
        b_new = QPushButton('➕ شیفت جدید')
        b_new.clicked.connect(self.new_shift)
        b_del = QPushButton('🗑 حذف شیفت')
        b_del.setObjectName('DangerBtn')
        b_del.clicked.connect(self.del_shift)
        left.addWidget(b_new)
        left.addWidget(b_del)
        lw = QWidget(); lw.setLayout(left)
        h.addWidget(lw, 1)
        # فرم ویرایش
        right = QVBoxLayout()
        right.addWidget(QLabel('نام شیفت:'))
        self.name = QLineEdit()
        right.addWidget(self.name)
        grid = QGridLayout()
        grid.addWidget(QLabel('روز هفته'), 0, 0)
        grid.addWidget(QLabel('شروع (H:MM)'), 0, 1)
        grid.addWidget(QLabel('پایان (H:MM)'), 0, 2)
        self.day_edits = []
        for i, wd in enumerate(WEEKDAYS):
            grid.addWidget(QLabel(wd), i + 1, 0)
            s = TimeMinutesEdit(480)
            e = TimeMinutesEdit(960)
            self.day_edits.append((s, e))
            grid.addWidget(s, i + 1, 1)
            grid.addWidget(e, i + 1, 2)
        right.addLayout(grid)
        note = QLabel('روزهایی که شروع/پایان خالی است = آن روز تعطیل است.\n'
                      'پرسنل بدون شیفت = پیش‌فرض ۸ تا ۱۶ شنبه تا پنجشنبه.')
        note.setStyleSheet('color:#64748b;')
        right.addWidget(note)
        b_save = QPushButton('💾 ذخیره شیفت')
        b_save.setObjectName('PrimaryBtn')
        b_save.clicked.connect(self.save_shift)
        right.addWidget(b_save)
        right.addStretch(1)
        rw = QWidget(); rw.setLayout(right)
        h.addWidget(rw, 2)
        return w

    def _tab_assign(self):
        w = QWidget()
        v = QVBoxLayout(w)
        bar = QHBoxLayout()
        bar.addWidget(QLabel('ماه:'))
        self.asg_month = JalaliMonthPicker()
        bar.addWidget(self.asg_month)
        b = QPushButton('💾 ذخیره انتساب‌ها')
        b.setObjectName('PrimaryBtn')
        b.clicked.connect(self.save_assign)
        bar.addWidget(b)
        bar.addStretch(1)
        v.addLayout(bar)
        self.assign_table = QTableWidget()
        setup_rtl_table(self.assign_table, ['پرسنل', 'کد', 'شیفت این ماه', 'شیفت پیش‌فرض پرونده'])
        v.addWidget(self.assign_table, 1)
        self.asg_month.currentIndexChanged.connect(self.load_assign)
        self.load_assign()
        return w

    def shifts(self):
        return SH.load_shifts(self.ctx.db, self.ctx.company_id)

    def load_list(self):
        self._shifts = self.shifts()
        self.listw.clear()
        for s in self._shifts:
            self.listw.addItem(s['name'])
        if self._shifts:
            self.listw.setCurrentRow(0)
            self.load_editor(0)
        else:
            self._clear_editor()

    def _clear_editor(self):
        self.name.setText('')
        for s, e in self.day_edits:
            s.setText(''); e.setText('')

    def load_editor(self, row):
        if not (0 <= row < len(self._shifts)):
            self._clear_editor()
            return
        s = self._shifts[row]
        self._edit_id = s['id']
        self.name.setText(s['name'])
        sched = s.get('schedule') or {}
        for i, (se, ee) in enumerate(self.day_edits):
            v = sched.get(str(i))
            if v:
                se.set_minutes(int(v[0]))
                ee.set_minutes(int(v[1]))
            else:
                se.setText(''); ee.setText('')

    def new_shift(self):
        self._edit_id = None
        self._clear_editor()
        self.name.setFocus()

    def del_shift(self):
        row = self.listw.currentRow()
        if not (0 <= row < len(self._shifts)):
            return
        s = self._shifts[row]
        if QMessageBox.question(self, 'حذف', f"حذف شیفت «{s['name']}»؟") == QMessageBox.StandardButton.Yes:
            SH.delete_shift(self.ctx.db, s['id'])
            self.load_list()

    def save_shift(self):
        if not self.gate.allowed('edit'):
            return
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, 'خطا', 'نام شیفت الزامی است')
            return
        sched = {}
        for i, (se, ee) in enumerate(self.day_edits):
            if se.text().strip() and ee.text().strip():
                sched[str(i)] = [se.minutes(), ee.minutes()]
        SH.save_shift(self.ctx.db, self.ctx.company_id, name, sched, shift_id=getattr(self, '_edit_id', None))
        self.load_list()
        self.load_assign()

    def load_assign(self):
        per = self.asg_month.current_period()
        if not per or not self.ctx.company_id:
            return
        jy, jm = per
        self._asg_jyjm = (jy, jm)
        cur = self.ctx.db.conn.execute(
            """SELECT id, first_name, last_name, personnel_code, shift_id FROM personnel
               WHERE company_id=? AND status='شاغل' ORDER BY last_name""", (self.ctx.company_id,))
        people = [dict(r) for r in cur.fetchall()]
        self._people = people
        shifts = self.shifts()
        self.assign_table.setRowCount(len(people))
        self._combo_boxes = []
        for r, p in enumerate(people):
            it = QTableWidgetItem(f"{p['first_name']} {p['last_name']}")
            it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.assign_table.setItem(r, 0, it)
            it2 = QTableWidgetItem(to_persian_digits(str(p['personnel_code'])))
            it2.setFlags(it2.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.assign_table.setItem(r, 1, it2)
            cb = QComboBox()
            cb.addItem('— بدون شیفت (۸ تا ۱۶ عادی) —', 0)
            for s in shifts:
                cb.addItem(s['name'], s['id'])
            cur = self.ctx.db.conn.execute(
                "SELECT shift_id FROM shift_assignments WHERE personnel_id=? AND jy=? AND jm=?",
                (p['id'], jy, jm))
            a = cur.fetchone()
            sid = a['shift_id'] if a else p['shift_id']
            idx = cb.findData(sid or 0)
            cb.setCurrentIndex(max(0, idx))
            self.assign_table.setCellWidget(r, 2, cb)
            self._combo_boxes.append((p['id'], cb))
            it3 = QTableWidgetItem('—')
            it3.setFlags(it3.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.assign_table.setItem(r, 3, it3)

    def save_assign(self):
        if not self.gate.allowed('edit'):
            return
        jy, jm = self._asg_jyjm
        for pid, cb in self._combo_boxes:
            sid = cb.currentData() or 0
            if sid:
                self.ctx.db.conn.execute(
                    "INSERT OR REPLACE INTO shift_assignments(personnel_id,jy,jm,shift_id) VALUES(?,?,?,?)",
                    (pid, jy, jm, sid))
            else:
                self.ctx.db.conn.execute(
                    "DELETE FROM shift_assignments WHERE personnel_id=? AND jy=? AND jm=?",
                    (pid, jy, jm))
        self.ctx.db.conn.commit()
        QMessageBox.information(self, 'ذخیره', 'انتساب شیفت ماه ذخیره شد')


class DailyDialog(QDialog):
    """جزئیات روزانه یک پرسنل — ویرایش دستی کامل + حذف روز + بازمحاسبه"""
    def __init__(self, ctx, month_id, person, gate):
        super().__init__()
        self.ctx = ctx
        self.gate = gate
        self.month_id = month_id
        self.person = person
        self.setWindowTitle(f"جزئیات روزانه — {person['first_name']} {person['last_name']}")
        self.resize(1080, 580)
        v = QVBoxLayout(self)
        cur = ctx.db.conn.execute("SELECT jy,jm FROM attendance_months WHERE id=?", (month_id,))
        m = cur.fetchone()
        self.jy, self.jm = (m['jy'], m['jm']) if m else (0, 0)
        hint = QLabel('زمان‌ها به فرمت H:MM — ویرایش هر سلول با دابل‌کلیک و Enter؛ '
                      'برای حذف داده یک روز، دکمه «حذف داده روز» با انتخاب سطر')
        hint.setStyleSheet('color:#64748b;')
        v.addWidget(hint)
        bar = QHBoxLayout()
        b_del = QPushButton('🗑 حذف داده روز انتخابی')
        b_del.setObjectName('DangerBtn')
        b_del.clicked.connect(self.delete_day)
        b_save = QPushButton('💾 ذخیره و بازمحاسبه')
        b_save.setObjectName('PrimaryBtn')
        b_save.clicked.connect(self.recalc)
        bar.addWidget(b_del)
        bar.addWidget(b_save)
        bar.addStretch(1)
        v.addLayout(bar)
        self.table = QTableWidget()
        setup_rtl_table(self.table, ['روز', 'روز هفته', 'وضعیت', 'ورود1', 'خروج1', 'ورود2', 'خروج2',
                                     'تاخیر', 'تعجیل', 'کسرکار', 'مرخصی', 'ماموریت', 'اضافه‌کار', 'مجموع'],
                        stretch_all=False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemChanged.connect(self._edit_cell)
        v.addWidget(self.table, 1)
        self._loading = False
        self.load()

    def load(self):
        self._loading = True
        cur = self.ctx.db.conn.execute(
            "SELECT * FROM attendance_daily WHERE month_id=? AND personnel_id=? ORDER BY day",
            (self.month_id, self.person['id']))
        rows = {r['day']: dict(r) for r in cur.fetchall()}
        days = J.days_in_month(self.jy, self.jm)
        self.table.setRowCount(days)
        for d in range(1, days + 1):
            r = rows.get(d)
            vals = [
                to_persian_digits(str(d)),
                J.weekday_name(self.jy, self.jm, d),
                r['status'] if r else '',
                minutes_to_hhmm(r['entry1']) if r and r['entry1'] >= 0 else '',
                minutes_to_hhmm(r['exit1']) if r and r['exit1'] >= 0 else '',
                minutes_to_hhmm(r['entry2']) if r and r['entry2'] is not None and r['entry2'] >= 0 else '',
                minutes_to_hhmm(r['exit2']) if r and r['exit2'] >= 0 else '',
                minutes_to_hhmm(r['late_min']) if r else '',
                minutes_to_hhmm(r['early_min']) if r else '',
                minutes_to_hhmm(r['missing_min']) if r else '',
                minutes_to_hhmm(r['leave_min']) if r else '',
                minutes_to_hhmm(r['mission_min']) if r else '',
                minutes_to_hhmm(r['overtime_min']) if r else '',
                minutes_to_hhmm(r['worked_min']) if r else '',
            ]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c in (0, 1):
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    it.setForeground(Qt.GlobalColor.gray)
                self.table.setItem(d - 1, c, it)
        self._loading = False

    def delete_day(self):
        if not self.gate.allowed('edit'):
            return
        r = self.table.currentRow()
        if r < 0:
            return
        day = r + 1
        self.ctx.db.conn.execute(
            "DELETE FROM attendance_daily WHERE month_id=? AND personnel_id=? AND day=?",
            (self.month_id, self.person['id'], day))
        self.ctx.db.conn.commit()
        self.load()

    def recalc(self):
        if not self.gate.allowed('edit'):
            return
        from core.numbers import parse_number
        gl = int(parse_number(self.ctx.fy_setting('late_grace_minutes', '10'), 10))
        ge = int(parse_number(self.ctx.fy_setting('early_grace_minutes', '10'), 10))
        lm = SH.leaves_map_for_month(self.ctx.db, self.month_id, self.jy, self.jm)
        SH.recalc_month(self.ctx.db, self.month_id, self.ctx.cal, gl, ge, lm)
        self.load()
        QMessageBox.information(self, 'بازمحاسبه', 'طبق شیفت و بازه مجاز بازمحاسبه شد')

    def _edit_cell(self, item):
        if self._loading:
            return
        if not self.gate.allowed('edit'):
            return
        row, col = item.row(), item.column()
        day = row + 1
        cols = {3: 'entry1', 4: 'exit1', 5: 'entry2', 6: 'exit2', 7: 'late_min', 8: 'early_min',
                9: 'missing_min', 10: 'leave_min', 11: 'mission_min', 12: 'overtime_min', 13: 'worked_min'}
        if col not in cols:
            return
        key = cols[col]
        text = normalize_digits(item.text()).strip()
        if key in ('entry1', 'exit1', 'entry2', 'exit2'):
            val = parse_hhmm(text, -1) if text else -1
        else:
            val = parse_hhmm(text, 0)
        cur = self.ctx.db.conn.execute(
            "SELECT id FROM attendance_daily WHERE month_id=? AND personnel_id=? AND day=?",
            (self.month_id, self.person['id'], day))
        ex = cur.fetchone()
        if not ex:
            cur = self.ctx.db.conn.execute(
                "INSERT INTO attendance_daily(month_id,personnel_id,day) VALUES(?,?,?)",
                (self.month_id, self.person['id'], day))
        self.ctx.db.conn.execute(
            f"UPDATE attendance_daily SET {key}=? WHERE month_id=? AND personnel_id=? AND day=?",
            (val, self.month_id, self.person['id'], day))
        self.ctx.db.conn.commit()


class LeaveDialog(QDialog):
    def __init__(self, ctx, person):
        super().__init__()
        self.ctx = ctx
        self.person = person
        self.setWindowTitle(f"ثبت مرخصی — {person['first_name']} {person['last_name']}")
        self.resize(440, 260)
        v = QVBoxLayout(self)
        f = QFormLayout()
        self.from_d = JalaliDatePicker(ctx.cal)
        self.to_d = JalaliDatePicker(ctx.cal)
        self.kind = QComboBox()
        self.kind.addItems(['استحقاقی', 'استعلاجی', 'بدون حقوق', 'ساعتی'])
        f.addRow('از تاریخ', self.from_d)
        f.addRow('تا تاریخ', self.to_d)
        f.addRow('نوع مرخصی', self.kind)
        v.addLayout(f)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.save)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        enable_enter_navigation(self)

    def save(self):
        fd, td = self.from_d.date(), self.to_d.date()
        if not fd or not td:
            QMessageBox.warning(self, 'خطا', 'تاریخ‌ها الزامی است')
            return
        import jdatetime as jd
        d1 = jd.date(*fd)
        d2 = jd.date(*td)
        if d2 < d1:
            QMessageBox.warning(self, 'خطا', 'تاریخ پایان قبل از شروع است')
            return
        days = (d2 - d1).days + 1
        self.ctx.db.conn.execute(
            "INSERT INTO leaves(personnel_id,from_date,to_date,days,leave_kind) VALUES(?,?,?,?,?)",
            (self.person['id'], J.format_jalali(*fd, persian=False),
             J.format_jalali(*td, persian=False), days, self.kind.currentText()))
        self.ctx.db.conn.commit()
        self.accept()
