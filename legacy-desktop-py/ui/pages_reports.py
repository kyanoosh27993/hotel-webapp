# -*- coding: utf-8 -*-
"""
گزارش‌ساز حرفه‌ای — ماژول جداگانه و قابل فروش
- طراحی گزارش: انتخاب جدول منبع + فیلدها + شرط‌های فیلتر + گروه‌بندی + مرتب‌سازی
- ذخیره/ویرایش/حذف گزارش‌ها (config JSON)
- خروجی اکسل و چاپ
- گزارش‌های پیش‌فرض مدیریتی
"""
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QTableWidget, QDialog, QFormLayout, QComboBox, QMessageBox,
                               QLineEdit, QListWidget, QListWidgetItem, QGroupBox, QGridLayout,
                               QFileDialog, QCheckBox, QTabWidget, QInputDialog, QHeaderView)
from core.numbers import to_persian_digits, parse_number, format_money
from .widgets import setup_rtl_table, fill_table

# جداول مجاز گزارش‌ساز — (جدول، عنوان، ستون‌ها، ستون‌های مبلغ)
SOURCE_TABLES = {
    'personnel': ('پرسنل', {
        'personnel_code': 'کد پرسنلی', 'first_name': 'نام', 'last_name': 'نام خانوادگی',
        'national_id': 'کد ملی', 'card_no': 'شماره کارت', 'job_title': 'شغل',
        'cost_center': 'مرکز هزینه', 'payslip_group': 'گروه فیش', 'mobile': 'تلفن',
        'sso_number': 'شماره بیمه', 'bank_name': 'بانک', 'bank_account': 'شماره حساب',
        'marital_status': 'تأهل', 'dependents': 'تحت تکفل', 'education': 'تحصیلات',
        'status': 'وضعیت', 'hire_date': 'تاریخ استخدام'}),
    'decrees_v': ('احکام پرسنلی', {
        'full_name': 'پرسنل', 'personnel_code': 'کد پرسنلی', 'effective_date': 'تاریخ اجرا',
        'job_wage': 'مزد شغل', 'seniority_wage': 'سنوات', 'housing': 'مسکن', 'food': 'خواروبار',
        'worker_ben': 'بن', 'child_allowance': 'حق اولاد', 'other_benefits': 'سایر مزایا',
        'fixed_overtime': 'اضافه‌کار ثابت', 'family_allowance': 'عائله‌مندی'}),
    'payroll_v': ('حقوق ماهانه', {
        'full_name': 'پرسنل', 'personnel_code': 'کد پرسنلی', 'period': 'دوره',
        'worked_days': 'کارکرد', 'leave_days': 'مرخصی', 'gross': 'جمع درآمد',
        'insured_base': 'مشمول بیمه', 'worker_ins': 'بیمه کارگر', 'employer_ins': 'بیمه کارفرما',
        'tax_base': 'مشمول مالیات', 'tax': 'مالیات', 'total_deductions': 'کسورات',
        'net_pay': 'قابل پرداخت'}),
    'attendance_v': ('حضور و غیاب ماهانه', {
        'full_name': 'پرسنل', 'personnel_code': 'کد پرسنلی', 'period': 'دوره',
        'present_days': 'روزهای کارکرد', 'worked_h': 'مجموع کارکرد (ساعت)',
        'overtime_h': 'اضافه‌کار (ساعت)', 'missing_h': 'کسرکار (ساعت)',
        'leave_h': 'مرخصی (ساعت)', 'mission_h': 'ماموریت (ساعت)'}),
}

MONEY_COLS = {
    'decrees_v': ['job_wage', 'seniority_wage', 'housing', 'food', 'worker_ben',
                  'child_allowance', 'other_benefits', 'fixed_overtime', 'family_allowance'],
    'payroll_v': ['gross', 'insured_base', 'worker_ins', 'employer_ins', 'tax_base',
                  'tax', 'total_deductions', 'net_pay'],
}


# ---------------- نمای‌های SQL ماژول گزارش‌ساز ----------------
REPORT_VIEWS = """
CREATE VIEW IF NOT EXISTS decrees_v AS
SELECT d.*, p.first_name || ' ' || p.last_name AS full_name, p.personnel_code
FROM decrees d JOIN personnel p ON p.id=d.personnel_id;

CREATE VIEW IF NOT EXISTS payroll_v AS
SELECT s.personnel_id, s.worked_days, s.leave_days, s.gross, s.insured_base, s.worker_ins,
       s.employer_ins, s.tax_base, s.tax, s.total_deductions, s.net_pay,
       p.first_name || ' ' || p.last_name AS full_name, p.personnel_code,
       pp.jy || '/' || printf('%02d', pp.jm) AS period
FROM payroll_summary s
JOIN payroll_periods pp ON pp.id=s.period_id
JOIN personnel p ON p.id=s.personnel_id;

CREATE VIEW IF NOT EXISTS attendance_v AS
SELECT ad.personnel_id, am.jy || '/' || printf('%02d', am.jm) AS period,
       SUM(CASE WHEN ad.worked_min>0 THEN 1 ELSE 0 END) AS present_days,
       ROUND(SUM(ad.worked_min)/60.0, 2) AS worked_h,
       ROUND(SUM(ad.overtime_min)/60.0, 2) AS overtime_h,
       ROUND(SUM(ad.missing_min)/60.0, 2) AS missing_h,
       ROUND(SUM(ad.leave_min)/60.0, 2) AS leave_h,
       ROUND(SUM(ad.mission_min)/60.0, 2) AS mission_h,
       p.first_name || ' ' || p.last_name AS full_name, p.personnel_code
FROM attendance_daily ad
JOIN attendance_months am ON am.id=ad.month_id
JOIN personnel p ON p.id=ad.personnel_id
GROUP BY ad.personnel_id, am.jy, am.jm;
"""

# گزارش‌های پیش‌فرض مدیریتی
DEFAULT_REPORTS = [
    {'name': 'خلاصه حقوق و دستمزد ماهانه', 'table': 'payroll_v',
     'fields': ['period', 'personnel_code', 'full_name', 'worked_days', 'gross', 'insured_base',
                'worker_ins', 'tax', 'net_pay'],
     'filters': [], 'order_by': 'period, personnel_code',
     'desc': 'مقایسه درآمد و قابل‌پرداخت همه پرسنل در همه دوره‌ها'},
    {'name': 'لیست پرسنل با شماره کارت دستگاه', 'table': 'personnel',
     'fields': ['personnel_code', 'first_name', 'last_name', 'card_no', 'job_title',
                'cost_center', 'sso_number', 'bank_account', 'status'],
     'filters': [], 'order_by': 'personnel_code',
     'desc': 'کنترل تطبیق شماره کارت دستگاه با پرونده پرسنل'},
    {'name': 'کارکرد و اضافه‌کاری ماهانه پرسنل', 'table': 'attendance_v',
     'fields': ['period', 'personnel_code', 'full_name', 'present_days', 'worked_h',
                'overtime_h', 'missing_h', 'leave_h'],
     'filters': [], 'order_by': 'period, overtime_h DESC',
     'desc': 'شناسایی بیشترین اضافه‌کاری و کسرکار در هر ماه'},
    {'name': 'اقلام احکام پرسنلی', 'table': 'decrees_v',
     'fields': ['personnel_code', 'full_name', 'effective_date', 'job_wage', 'seniority_wage',
                'housing', 'worker_ben', 'child_allowance', 'fixed_overtime'],
     'filters': [], 'order_by': 'personnel_code, effective_date DESC',
     'desc': 'تاریخچه احکام و مزایای هر پرسنل'},
    {'name': 'مالیات و بیمه پرداختنی به تفکیک دوره', 'table': 'payroll_v',
     'fields': ['period', 'full_name', 'tax_base', 'tax', 'worker_ins', 'employer_ins'],
     'filters': [], 'order_by': 'period, tax DESC',
     'desc': 'کنترل بار مالیاتی و بیمه‌ای شرکت در طول سال'},
    {'name': 'پرسنل متاهل دارای تحت‌تکفل', 'table': 'personnel',
     'fields': ['personnel_code', 'first_name', 'last_name', 'marital_status', 'dependents',
                'job_title', 'cost_center'],
     'filters': [['marital_status', '=', 'متاهل'], ['dependents', '>', 0]],
     'order_by': 'dependents DESC',
     'desc': 'برای کنترل حق اولاد و عائله‌مندی'},
]


class ReportsPage(QWidget):
    """ماژول گزارش‌ساز — قابل نصب/حذف به‌صورت پلاگین"""
    MODULE_KEY = 'report_builder'

    def __init__(self, ctx, gate):
        super().__init__()
        self.ctx = ctx
        self.gate = gate
        self.ctx.db.conn.executescript(REPORT_VIEWS)
        self.ctx.db.conn.commit()
        self._seed_defaults()
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        title = QLabel('📊 گزارش‌ساز حرفه‌ای (ماژول مستقل)')
        title.setObjectName('PageTitle')
        v.addWidget(title)
        bar = QHBoxLayout()
        b_new = QPushButton('➕ گزارش جدید')
        b_new.setObjectName('PrimaryBtn')
        b_new.clicked.connect(self.new_report)
        b_edit = QPushButton('✏️ ویرایش طراحی')
        b_edit.clicked.connect(self.edit_report)
        b_run = QPushButton('▶ اجرای گزارش')
        b_run.clicked.connect(self.run_report)
        b_del = QPushButton('🗑 حذف')
        b_del.setObjectName('DangerBtn')
        b_del.clicked.connect(self.del_report)
        b_xls = QPushButton('📤 خروجی اکسل نتیجه')
        b_xls.clicked.connect(self.export_result)
        for x in (b_new, b_edit, b_run, b_del, b_xls):
            bar.addWidget(x)
        bar.addStretch(1)
        v.addLayout(bar)
        self.rep_list = QListWidget()
        self.rep_list.itemDoubleClicked.connect(lambda _: self.run_report())
        v.addWidget(self.rep_list, 0)
        v.addWidget(QLabel('نتیجه:'))
        self.table = QTableWidget()
        setup_rtl_table(self.table, [])
        v.addWidget(self.table, 1)
        self.load_reports()

    def _seed_defaults(self):
        cur = self.ctx.db.conn.execute("SELECT COUNT(*) FROM report_defs WHERE is_builtin=1")
        if cur.fetchone()[0] == 0:
            for r in DEFAULT_REPORTS:
                self.ctx.db.conn.execute(
                    "INSERT INTO report_defs(name,description,config,is_builtin) VALUES(?,?,?,1)",
                    (r['name'], r['desc'], json.dumps(r, ensure_ascii=False)))
            self.ctx.db.conn.commit()

    def load_reports(self):
        self.rep_list.clear()
        cur = self.ctx.db.conn.execute("SELECT id,name,description,is_builtin FROM report_defs ORDER BY is_builtin DESC, name")
        self._reports = [dict(r) for r in cur.fetchall()]
        for r in self._reports:
            label = ('⭐ ' if r['is_builtin'] else '') + r['name']
            it = QListWidgetItem(label)
            it.setToolTip(r['description'])
            self.rep_list.addItem(it)

    def _selected(self):
        r = self.rep_list.currentRow()
        return self._reports[r] if 0 <= r < len(self._reports) else None

    def new_report(self):
        if not self.gate.allowed('edit'):
            return
        dlg = ReportDesigner(self.ctx, None)
        if dlg.exec():
            self.load_reports()

    def edit_report(self):
        r = self._selected()
        if not r:
            return
        if not self.gate.allowed('edit'):
            return
        dlg = ReportDesigner(self.ctx, r)
        if dlg.exec():
            self.load_reports()

    def del_report(self):
        r = self._selected()
        if not r:
            return
        if not self.gate.allowed('edit'):
            return
        if QMessageBox.question(self, 'حذف', f"حذف گزارش «{r['name']}»؟") == QMessageBox.StandardButton.Yes:
            self.ctx.db.conn.execute("DELETE FROM report_defs WHERE id=?", (r['id'],))
            self.ctx.db.conn.commit()
            self.load_reports()

    def run_report(self):
        r = self._selected()
        if not r:
            return
        cfg = json.loads(r['config'])
        sql, headers, money, args = build_query(cfg)
        try:
            cur = self.ctx.db.conn.execute(sql, args)
            rows = cur.fetchall()
        except Exception as e:
            QMessageBox.critical(self, 'خطای گزارش', str(e))
            return
        data = [[row[i] for i in range(len(headers))] for row in rows]
        fill_table(self.table, data, formats={i: 'money' for i in money} if money else {})
        self.table.setWindowTitle(r['name'])
        self._result = {'headers': headers, 'rows': [[row[i] for i in range(len(headers))] for row in rows]}
        self._result_name = r['name']

    def export_result(self):
        if not getattr(self, '_result', None):
            return
        from core import exports
        path, _ = QFileDialog.getSaveFileName(self, 'ذخیره خروجی', f"{self._result_name}.xlsx", 'Excel (*.xlsx)')
        if not path:
            return
        exports.export_table_xlsx(path, self._result_name, self.ctx.company_name,
                                  self._result['headers'], self._result['rows'])


def build_query(cfg):
    """ساخت SQL از config گزارش → (sql, headers, money_cols, args)"""
    table = cfg['table']
    meta, fields = SOURCE_TABLES[table][1], cfg['fields']
    cols = ', '.join(fields)
    where = ''
    args = []
    for (f, op, val) in cfg.get('filters', []):
        if op == '=':
            where += (f" AND {f}=?" if where else f" WHERE {f}=?")
            args.append(val)
        elif op == '!=':
            where += (f" AND {f}<>" if where else f" WHERE {f}<>") + '?'
            args.append(val)
        elif op in ('>', '<', '>=', '<='):
            where += (f" AND {f}{op}?" if where else f" WHERE {f}{op}?")
            args.append(parse_number(val, 0))
        elif op == 'like':
            where += (f" AND {f} LIKE ?" if where else f" WHERE {f} LIKE ?")
            args.append(f"%{val}%")
    order = f" ORDER BY {cfg['order_by']}" if cfg.get('order_by') else ''
    sql = f"SELECT {cols} FROM {table}{where}{order}"
    money = [i for i, f in enumerate(fields) if f in MONEY_COLS.get(table, [])]
    headers = [meta.get(f, f) for f in fields]
    return sql, headers, money, args


class ReportDesigner(QDialog):
    """طراح گزارش: انتخاب جدول، فیلدها، فیلترها، مرتب‌سازی"""
    def __init__(self, ctx, report):
        super().__init__()
        self.ctx = ctx
        self.report = report
        self.setWindowTitle('طراح گزارش')
        self.resize(680, 560)
        v = QVBoxLayout(self)
        f = QFormLayout()
        self.name = QLineEdit()
        self.desc = QLineEdit()
        self.src = QComboBox()
        for key, (title, _) in SOURCE_TABLES.items():
            self.src.addItem(title, key)
        f.addRow('نام گزارش *', self.name)
        f.addRow('توضیح', self.desc)
        f.addRow('جدول منبع', self.src)
        v.addLayout(f)
        g = QGridLayout()
        g.addWidget(QLabel('فیلدهای گزارش:'), 0, 0)
        g.addWidget(QLabel('فیلترها:'), 0, 1)
        self.fields = QListWidget()
        self.fields.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        g.addWidget(self.fields, 1, 0)
        fv = QVBoxLayout()
        self.filters = []
        b_add_f = QPushButton('➕ شرط فیلتر')
        b_add_f.clicked.connect(self.add_filter)
        b_rm_f = QPushButton('➖ حذف شرط')
        b_rm_f.clicked.connect(self.rm_filter)
        fv.addWidget(b_add_f)
        fv.addWidget(b_rm_f)
        self.filter_list = QListWidget()
        fv.addWidget(self.filter_list)
        fw = QWidget()
        fw.setLayout(fv)
        g.addWidget(fw, 1, 1)
        v.addLayout(g)
        f2 = QFormLayout()
        self.order = QLineEdit()
        f2.addRow('مرتب‌سازی بر اساس (فیلدها با کاما)', self.order)
        v.addLayout(f2)
        bb = QHBoxLayout()
        ok = QPushButton('💾 ذخیره گزارش')
        ok.setObjectName('PrimaryBtn')
        ok.clicked.connect(self.save)
        cancel = QPushButton('انصراف')
        cancel.clicked.connect(self.reject)
        bb.addStretch(1)
        bb.addWidget(ok)
        bb.addWidget(cancel)
        v.addLayout(bb)
        self.src.currentTextChanged.connect(self.load_fields)
        self.load_fields()
        if report:
            cfg = json.loads(report['config'])
            self.name.setText(report['name'])
            self.desc.setText(report['description'])
            idx = self.src.findData(cfg['table'])
            if idx >= 0:
                self.src.setCurrentIndex(idx)
            for fld in cfg['fields']:
                for i in range(self.fields.count()):
                    if self.fields.item(i).data(Qt.ItemDataRole.UserRole) == fld:
                        self.fields.item(i).setSelected(True)
            self._filters = cfg.get('filters', [])
            self._render_filters()
            self.order.setText(cfg.get('order_by', ''))
        else:
            self._filters = []

    def load_fields(self):
        self.fields.clear()
        key = self.src.currentData()
        for fld, title in SOURCE_TABLES[key][1].items():
            it = QListWidgetItem(title)
            it.setData(Qt.ItemDataRole.UserRole, fld)
            self.fields.addItem(it)

    def add_filter(self):
        key = self.src.currentData()
        flds = list(SOURCE_TABLES[key][1].keys())
        fld, ok = QInputDialog.getItem(self, 'فیلد', 'انتخاب فیلد:', flds, 0, False)
        if not ok:
            return
        op, ok = QInputDialog.getItem(self, 'شرط', 'عملگر:', ['=', '<>', '>', '<', '>=', '<=', 'شامل متن'], 0, False)
        if not ok:
            return
        val, ok = QInputDialog.getText(self, 'مقدار', 'مقدار شرط:')
        if not ok:
            return
        op_map = {'=': '=', '<>': '!=', '>': '>', '<': '<', '>=': '>=', '<=': '<=', 'شامل متن': 'like'}
        self._filters.append([fld, op_map[op], val])
        self._render_filters()

    def rm_filter(self):
        r = self.filter_list.currentRow()
        if r >= 0:
            del self._filters[r]
            self._render_filters()

    def _render_filters(self):
        self.filter_list.clear()
        meta = SOURCE_TABLES[self.src.currentData()][1]
        for f, op, val in self._filters:
            self.filter_list.addItem(f"{meta.get(f, f)} {op} «{val}»")

    def save(self):
        if not self.name.text().strip():
            return
        fields = [i.data(Qt.ItemDataRole.UserRole) for i in self.fields.selectedItems()]
        if not fields:
            QMessageBox.warning(self, 'خطا', 'حداقل یک فیلد انتخاب کنید')
            return
        cfg = {'table': self.src.currentData(), 'fields': fields,
               'filters': self._filters, 'order_by': self.order.text().strip()}
        if self.report:
            self.ctx.db.conn.execute(
                "UPDATE report_defs SET name=?,description=?,config=? WHERE id=?",
                (self.name.text().strip(), self.desc.text().strip(),
                 json.dumps(cfg, ensure_ascii=False), self.report['id']))
        else:
            self.ctx.db.conn.execute(
                "INSERT INTO report_defs(name,description,config) VALUES(?,?,?)",
                (self.name.text().strip(), self.desc.text().strip(),
                 json.dumps(cfg, ensure_ascii=False)))
        self.ctx.db.conn.commit()
        self.accept()
