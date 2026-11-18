# -*- coding: utf-8 -*-
"""
لایه دیتابیس — SQLite چندشرکتی
طراحی جداول بر اساس فایل‌های واقعی کاربر (پرسنل ۲۸ فیلدی، احکام ۱۵ آیتمی،
خروجی دستگاه حضور و غیاب، فیش حقوقی ۴۳ ستونی) + نیازهای لیست بیمه و مالیات.
"""
import os
import sqlite3
import json

APP_VERSION = '0.3.0'

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'payroll.db')

SCHEMA = """
-- ---------------- کاربران و امنیت ----------------
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    full_name TEXT DEFAULT '',
    role TEXT NOT NULL DEFAULT 'viewer',   -- admin / operator / viewer
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT DEFAULT (datetime('now','localtime')),
    username TEXT,
    action TEXT,
    details TEXT
);

-- ---------------- شرکت‌ها و سال‌های مالی (بدون محدودیت) ----------------
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    national_id TEXT DEFAULT '',
    economic_code TEXT DEFAULT '',
    sso_branch_code TEXT DEFAULT '',      -- کد شعبه تامین اجتماعی
    sso_workshop_code TEXT DEFAULT '',    -- کد کارگاه تامین اجتماعی (۱۰ رقمی)
    sso_contract_row TEXT DEFAULT '',     -- ردیف پیمان تامین اجتماعی
    tax_file_code TEXT DEFAULT '',        -- کد پرونده مالیاتی
    postal_code TEXT DEFAULT '',
    manager_name TEXT DEFAULT '',
    logo_path TEXT DEFAULT '',            -- مسیر لوگو (در همه خروجی‌ها چاپ می‌شود)
    address TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fiscal_years (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    jy INTEGER NOT NULL,                  -- سال شمسی
    title TEXT DEFAULT '',
    UNIQUE(company_id, jy)
);

CREATE TABLE IF NOT EXISTS fy_settings (
    fiscal_year_id INTEGER NOT NULL REFERENCES fiscal_years(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT DEFAULT '',
    PRIMARY KEY (fiscal_year_id, key)
);

CREATE TABLE IF NOT EXISTS tax_brackets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fiscal_year_id INTEGER NOT NULL REFERENCES fiscal_years(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    from_amount REAL DEFAULT 0,
    to_amount REAL,                       -- NULL = بی‌نهایت
    rate_percent REAL NOT NULL
);

-- ---------------- پرسنل ----------------
CREATE TABLE IF NOT EXISTS personnel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    personnel_code TEXT NOT NULL,          -- شماره پرسنلی
    card_no TEXT DEFAULT '',               -- شماره کارت دستگاه حضور و غیاب
    first_name TEXT DEFAULT '',
    last_name TEXT DEFAULT '',
    father_name TEXT DEFAULT '',
    national_id TEXT DEFAULT '',           -- کد ملی
    id_number TEXT DEFAULT '',             -- شماره شناسنامه
    id_serial TEXT DEFAULT '',             -- سریال شناسنامه
    id_issue_place TEXT DEFAULT '',        -- محل صدور
    birth_date TEXT DEFAULT '',            -- تاریخ تولد (شمسی)
    gender TEXT DEFAULT 'مرد',             -- مرد / زن
    marital_status TEXT DEFAULT 'مجرد',    -- مجرد / متاهل
    dependents INTEGER DEFAULT 0,          -- تحت تکفل
    education TEXT DEFAULT '',
    mobile TEXT DEFAULT '',
    job_title TEXT DEFAULT '',             -- شغل
    cost_center TEXT DEFAULT '',           -- مرکز هزینه
    payslip_group TEXT DEFAULT '',         -- گروه فیش حقوقی
    bank_name TEXT DEFAULT '',
    bank_account TEXT DEFAULT '',          -- شماره حساب
    bank_sheba TEXT DEFAULT '',
    sso_number TEXT DEFAULT '',            -- شماره بیمه تامین اجتماعی
    sso_insurer TEXT DEFAULT '',           -- شرکت بیمه‌شونده
    military_status TEXT DEFAULT '',
    is_veteran INTEGER DEFAULT 0,          -- جانبازی
    work_location TEXT DEFAULT '',         -- محل خدمت
    permanent_night INTEGER DEFAULT 0,     -- شب‌کار دائم
    shift_id INTEGER,                      -- شیفت پیش‌فرض فرد (بدون شیفت = ۸ ساعت روزهای عادی)
    sso_worker_pct REAL,                   -- درصد بیمه شخصی (NULL = پیش‌فرض تنظیمات سال)
    sso_employer_pct REAL,                 -- درصد بیمه کارفرما شخصی
    sso_unemp_pct REAL,                    -- درصد بیمه بیکاری شخصی
    address TEXT DEFAULT '',
    postal_code TEXT DEFAULT '',
    birth_place TEXT DEFAULT '',
    insurance_type INTEGER DEFAULT 2,      -- 1خدمات درمانی/2تامین اجتماعی/3بیمه سلامت/4سایر/5ندارد
    employment_type INTEGER DEFAULT 1,     -- 1قراردادی/2شرکتی/3رسمی/4پیمانی/8ساعتی/9روزمزد/12سایر
    job_category INTEGER DEFAULT 12,       -- رسته (جدول مالیات): 12خدمات/17کارگری/10تولیدی…
    status TEXT DEFAULT 'شاغل',            -- شاغل / خروج / بازنشسته / غیرفعال (پرسنل جدید از دستگاه)
    hire_date TEXT DEFAULT '',             -- تاریخ استخدام
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_personnel_code ON personnel(company_id, personnel_code);

-- ---------------- قراردادها ----------------
CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    contract_type TEXT NOT NULL DEFAULT 'ماهانه ثابت', -- ساعتی/روزانه/ماهانه ثابت/پیمانی/سایر
    hourly_rate REAL DEFAULT 0,            -- نرخ ساعت (ساعتی)
    daily_rate REAL DEFAULT 0,             -- نرخ روز (روزانه)
    monthly_wage REAL DEFAULT 0,           -- مزد ماهانه (ثابت)
    project_amount REAL DEFAULT 0,         -- مبلغ پیمان
    start_date TEXT DEFAULT '',
    end_date TEXT DEFAULT '',
    pay_cycle TEXT DEFAULT 'ماهانه',
    insurance_required INTEGER DEFAULT 1,  -- مشمول بیمه
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ---------------- احکام پرسنلی (تاریخ اجرا = قابل تغییر ماهانه) ----------------
CREATE TABLE IF NOT EXISTS decrees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    effective_date TEXT NOT NULL,          -- تاریخ اجرا (شمسی)
    job_wage REAL DEFAULT 0,               -- مزد شغل
    seniority_wage REAL DEFAULT 0,         -- مزد سنوات
    child_allowance REAL DEFAULT 0,        -- حق اولاد
    housing REAL DEFAULT 0,                -- حق مسکن
    food REAL DEFAULT 0,                   -- خواروبار
    adjustment_diff REAL DEFAULT 0,        -- تفاوت تطبیق
    supervision REAL DEFAULT 0,            -- حق سرپرستی
    education_aid REAL DEFAULT 0,          -- کمک‌هزینه تحصیلی
    labor_market REAL DEFAULT 0,           -- فوق‌العاده بازار کار
    attraction_percent REAL DEFAULT 0,     -- درصد حق جذب
    attraction_amount REAL DEFAULT 0,      -- مبلغ حق جذب
    other_benefits REAL DEFAULT 0,         -- اضافه‌کاری/سایر مزایا
    worker_ben REAL DEFAULT 0,             -- بن کارگری
    fixed_overtime REAL DEFAULT 0,         -- اضافه‌کار ثابت
    family_allowance REAL DEFAULT 0,       -- حق عائله‌مندی (تأهل)
    shift_allowance REAL DEFAULT 0,        -- حق شیفت
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ---------------- شیفت کاری (قابل تعریف برای هر فرد) ----------------
-- schedule: JSONی مثل {"0":[480,1020],"1":[480,1020]} — کلید = روز هفته (شنبه=0)، [شروع,پایان] دقیقه از نیمه‌شب، نبود = تعطیل
CREATE TABLE IF NOT EXISTS shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    schedule TEXT NOT NULL DEFAULT '{}',
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS shift_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    jy INTEGER NOT NULL, jm INTEGER NOT NULL,
    shift_id INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    UNIQUE(personnel_id, jy, jm)
);

-- ---------------- حضور و غیاب ----------------
CREATE TABLE IF NOT EXISTS attendance_months (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fiscal_year_id INTEGER NOT NULL REFERENCES fiscal_years(id) ON DELETE CASCADE,
    jy INTEGER NOT NULL,
    jm INTEGER NOT NULL,
    source TEXT DEFAULT 'دستی',
    imported_at TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(fiscal_year_id, jy, jm)
);

CREATE TABLE IF NOT EXISTS attendance_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month_id INTEGER NOT NULL REFERENCES attendance_months(id) ON DELETE CASCADE,
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    day INTEGER NOT NULL,                  -- روز ماه
    status TEXT DEFAULT 'بدون شیفت',
    entry1 INTEGER DEFAULT -1, exit1 INTEGER DEFAULT -1,   -- دقیقه از نیمه‌شب؛ -1 = خالی
    entry2 INTEGER DEFAULT -1, exit2 INTEGER DEFAULT -1,
    entry3 INTEGER DEFAULT -1, exit3 INTEGER DEFAULT -1,
    late_min INTEGER DEFAULT 0,            -- تاخیر
    early_min INTEGER DEFAULT 0,           -- تعجیل
    missing_min INTEGER DEFAULT 0,         -- کسرکار
    leave_min INTEGER DEFAULT 0,           -- مرخصی
    mission_min INTEGER DEFAULT 0,         -- ماموریت
    overtime_min INTEGER DEFAULT 0,        -- اضافه کار (دستگاه)
    free_overtime_min INTEGER DEFAULT 0,   -- اضافه آزاد
    worked_min INTEGER DEFAULT 0,          -- مجموع کارکرد
    expected_min INTEGER DEFAULT 0,        -- ساعات موظفی طبق شیفت این روز
    leave_kind TEXT DEFAULT '',            -- نوع مرخصی: استحقاقی/استعلاجی/بدون حقوق/ساعتی
    UNIQUE(month_id, personnel_id, day)
);

-- ---------------- وام، مساعده، مرخصی ----------------
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'وام',
    total_amount REAL NOT NULL,
    installment REAL NOT NULL,
    installments_count INTEGER DEFAULT 0,
    paid_count INTEGER DEFAULT 0,
    start_period TEXT DEFAULT '',           -- '1405/07'
    remaining REAL DEFAULT 0,
    active INTEGER DEFAULT 1,
    notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS advances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    pay_date TEXT DEFAULT '',
    amount REAL NOT NULL,
    recovered INTEGER DEFAULT 0,            -- بازپرداخت شده
    period TEXT DEFAULT '',
    notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS leaves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    from_date TEXT NOT NULL,
    to_date TEXT NOT NULL,
    days REAL NOT NULL DEFAULT 0,
    leave_kind TEXT DEFAULT 'استحقاقی',     -- استحقاقی/استعلاجی/بدون حقوق/ساعتی
    approved INTEGER DEFAULT 1,
    notes TEXT DEFAULT ''
);

-- ---------------- موتور حقوق و دستمزد ----------------
CREATE TABLE IF NOT EXISTS payroll_items_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,              -- کلید انگلیسی آیتم
    title TEXT NOT NULL,                    -- عنوان فارسی
    kind TEXT NOT NULL DEFAULT 'earning',   -- earning / deduction / employer
    formula_key TEXT DEFAULT 'manual',      -- کلید فرمول پیش‌فرض
    tax_mode TEXT DEFAULT 'm84',            -- none / m84 / lump / percent
    tax_percent REAL DEFAULT 0,             -- برای حالت percent
    insured INTEGER DEFAULT 1,              -- مشمول بیمه
    active INTEGER DEFAULT 1,
    sort INTEGER DEFAULT 100,
    system_locked INTEGER DEFAULT 0         -- آیتم‌های سیستمی قابل حذف نیستند ولی فرمول‌شان قابل ویرایش است
);

CREATE TABLE IF NOT EXISTS payroll_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fiscal_year_id INTEGER NOT NULL REFERENCES fiscal_years(id) ON DELETE CASCADE,
    jy INTEGER NOT NULL, jm INTEGER NOT NULL,
    status TEXT DEFAULT 'پیش‌نویس',          -- پیش‌نویس / نهایی
    calculated_at TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(fiscal_year_id, jy, jm)
);

CREATE TABLE IF NOT EXISTS payroll_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id INTEGER NOT NULL REFERENCES payroll_periods(id) ON DELETE CASCADE,
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    item_code TEXT NOT NULL,
    amount REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_pl ON payroll_lines(period_id, personnel_id);

CREATE TABLE IF NOT EXISTS payroll_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id INTEGER NOT NULL REFERENCES payroll_periods(id) ON DELETE CASCADE,
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    worked_days REAL DEFAULT 0,
    leave_days REAL DEFAULT 0,
    leave_balance REAL DEFAULT 0,
    overtime_min INTEGER DEFAULT 0,
    gross REAL DEFAULT 0,
    insured_base REAL DEFAULT 0,
    worker_ins REAL DEFAULT 0,
    employer_ins REAL DEFAULT 0,
    unemployment_ins REAL DEFAULT 0,
    tax_base REAL DEFAULT 0,
    tax REAL DEFAULT 0,
    total_deductions REAL DEFAULT 0,
    net_pay REAL DEFAULT 0,
    prev_balance REAL DEFAULT 0,           -- مانده حقوق پرداخت‌نشده ماه قبل
    pay_approved INTEGER DEFAULT 1,        -- تایید برای پرداخت در لیست بانک
    pay_paid INTEGER DEFAULT 0,            -- پرداخت شده؟
    pay_note TEXT DEFAULT '',
    UNIQUE(period_id, personnel_id)
);

CREATE TABLE IF NOT EXISTS payroll_manual (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id INTEGER NOT NULL REFERENCES payroll_periods(id) ON DELETE CASCADE,
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    item_code TEXT NOT NULL,               -- کد آیتم یا '__night_hours' برای ساعات شب‌کاری
    amount REAL DEFAULT 0,
    UNIQUE(period_id, personnel_id, item_code)
);

-- ---------------- گزارش‌ساز (ماژول جدا) ----------------
CREATE TABLE IF NOT EXISTS report_defs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    config TEXT NOT NULL,                   -- JSON: جدول منبع، ستون‌ها، فیلترها، گروه‌بندی
    is_builtin INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- ---------------- ماژول‌های نصب‌شده ----------------
CREATE TABLE IF NOT EXISTS installed_modules (
    key TEXT PRIMARY KEY,
    title TEXT,
    enabled INTEGER DEFAULT 1,
    license_note TEXT DEFAULT ''
);

-- ---------------- تقویم ----------------
CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jy INTEGER NOT NULL, jm INTEGER NOT NULL, jd INTEGER NOT NULL,
    kind TEXT NOT NULL,                     -- holiday / occasion
    title TEXT NOT NULL,
    source TEXT DEFAULT 'دستی'
);
"""

# کلیدهای پیش‌فرض تنظیمات سال مالی
FY_DEFAULTS = {
    'monthly_required_hours': '176',        # ساعات موظفی کارکرد ماهانه
    'sso_worker_rate': '7',
    'sso_employer_rate': '23',
    'sso_unemployment_rate': '3',
    'sso_ceiling_30d': '1163788500',        # سقف مشمول بیمه ماه ۳۰ روزه ۱۴۰۵
    'sso_ceiling_31d': '1202581450',
    'overtime_factor': '1.4',               # اضافه‌کاری قانون کار
    'holiday_work_factor': '1.7',           # تعطیل‌کاری
    'friday_work_factor': '1.4',            # جمعه‌کاری
    'night_work_percent': '35',             # شب‌کاری مازاد
    'shift1_percent': '10', 'shift2_percent': '15', 'shift3_percent': '22.5',
    'm84_monthly_exemption': '400000000',   # معافیت ماهانه ماده ۸۴ سال ۱۴۰۵
    'late_grace_minutes': '10',             # بازه مجاز تاخیر (تا این تعداد دقیقه تاخیر محسوب نمی‌شود)
    'early_grace_minutes': '10',            # بازه مجاز تعجیل در خروج
}

TAX_BRACKETS_1405 = [  # ماهانه - ریال (سامانه مالیات حقوق ۱۴۰۵)
    (1, 0, 400_000_000, 0),
    (2, 400_000_000, 800_000_000, 10),
    (3, 800_000_000, 1_000_000_000, 15),
    (4, 1_000_000_000, 1_200_000_000, 20),
    (5, 1_200_000_000, 1_400_000_000, 25),
    (6, 1_400_000_000, None, 30),
]

# اقلام پیش‌فرض فیش حقوقی (بر اساس فایل 5.xlsx کاربر) — فرمول‌ها قابل ویرایش‌اند
DEFAULT_PAYROLL_ITEMS = [
    # code, title, kind, formula_key, tax_mode, insured, sort, system_locked
    ('base_wage',      'حقوق (مزد شغل)',        'earning', 'decree_job_wage',   'm84', 1, 10, 1),
    ('seniority',      'مزد سنوات',              'earning', 'decree_field:seniority_wage', 'm84', 1, 20, 1),
    ('housing',        'حق مسکن',                'earning', 'decree_field:housing', 'm84', 1, 30, 1),
    ('food',           'خواروبار',               'earning', 'decree_field:food', 'm84', 1, 40, 1),
    ('child_allow',    'حق اولاد',               'earning', 'decree_field:child_allowance', 'none', 0, 50, 1),
    ('worker_ben',     'بن کارگری',              'earning', 'decree_field:worker_ben', 'none', 0, 60, 1),
    ('overtime',       'اضافه‌کاری',             'earning', 'overtime_140',      'm84', 1, 70, 1),
    ('holiday_work',   'تعطیل‌کاری',             'earning', 'holiday_work_170',  'm84', 1, 80, 1),
    ('friday_work',    'جمعه‌کاری',              'earning', 'friday_work_140',   'm84', 1, 90, 1),
    ('night_work',     'شب‌کاری',                'earning', 'night_work_35',     'm84', 1, 100, 1),
    ('shift_allow',    'حق شیفت / نوبت‌کاری',    'earning', 'decree_field:shift_allowance', 'm84', 1, 110, 1),
    ('attraction',     'حق جذب',                 'earning', 'decree_field:attraction_amount', 'm84', 1, 120, 1),
    ('family_allow',   'حق عائله‌مندی',          'earning', 'decree_field:family_allowance', 'none', 0, 130, 1),
    ('adjustment',     'تفاوت تطبیق',            'earning', 'decree_field:adjustment_diff', 'm84', 1, 140, 1),
    ('supervision',    'حق سرپرستی',             'earning', 'decree_field:supervision', 'm84', 1, 150, 1),
    ('labor_market',   'فوق‌العاده بازار کار',   'earning', 'decree_field:labor_market', 'm84', 1, 160, 1),
    ('education_aid',  'کمک‌هزینه تحصیلی',       'earning', 'decree_field:education_aid', 'm84', 1, 170, 1),
    ('fixed_ot',       'اضافه‌کار ثابت',         'earning', 'decree_field:fixed_overtime', 'm84', 1, 180, 1),
    ('other_ben',      'سایر مزایا (با بیمه و مالیات)', 'earning', 'decree_field:other_benefits', 'm84', 1, 190, 1),
    ('tax_free_other', 'سایر مزایا (بدون بیمه و مالیات)', 'earning', 'manual', 'none', 0, 200, 0),
    # کسورات
    ('worker_ins',     'بیمه سهم کارگر (۷٪)',    'deduction', 'worker_insurance', 'none', 0, 500, 1),
    ('tax',            'مالیات حقوق',            'deduction', 'salary_tax', 'none', 0, 510, 1),
    ('loan_install',   'قسط وام',                'deduction', 'loan_installment', 'none', 0, 520, 0),
    ('advance',        'مساعده',                 'deduction', 'advance_amount', 'none', 0, 530, 0),
    ('other_deduct',   'سایر کسورات',            'deduction', 'manual', 'none', 0, 540, 0),
    # سهم کارفرما (گزارشی - در فیش نمی‌آید)
    ('employer_ins',   'بیمه سهم کارفرما (۲۳٪)', 'employer', 'employer_insurance', 'none', 0, 900, 1),
    ('unemployment',   'بیمه بیکاری (۳٪)',       'employer', 'unemployment_insurance', 'none', 0, 910, 1),
]


class Database:
    def __init__(self, path=None):
        self.path = path or DB_PATH
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")

    def init_schema(self):
        self.conn.executescript(SCHEMA)
        self.migrate()
        self.conn.commit()
        self._seed()

    def migrate(self):
        """مهاجرت دیتابیس‌های نسخه‌های قبلی (بدون از دست رفتن داده‌ها)"""
        cols = {
            'personnel': [('shift_id', 'INTEGER'), ('sso_worker_pct', 'REAL'),
                          ('sso_employer_pct', 'REAL'), ('sso_unemp_pct', 'REAL'),
                          ('address', "TEXT DEFAULT ''"), ('postal_code', "TEXT DEFAULT ''"),
                          ('birth_place', "TEXT DEFAULT ''"), ('insurance_type', 'INTEGER DEFAULT 2'),
                          ('employment_type', 'INTEGER DEFAULT 1'), ('job_category', 'INTEGER DEFAULT 12')],
            'companies': [('sso_workshop_code', "TEXT DEFAULT ''"), ('sso_contract_row', "TEXT DEFAULT ''"),
                          ('postal_code', "TEXT DEFAULT ''"), ('manager_name', "TEXT DEFAULT ''"),
                          ('logo_path', "TEXT DEFAULT ''")],
            'attendance_daily': [('expected_min', 'INTEGER DEFAULT 0'), ("leave_kind", "TEXT DEFAULT ''")],
            'payroll_summary': [('prev_balance', 'REAL DEFAULT 0'), ('pay_approved', 'INTEGER DEFAULT 1'),
                                ('pay_paid', 'INTEGER DEFAULT 0'), ("pay_note", "TEXT DEFAULT ''")],
        }
        for table, newcols in cols.items():
            cur = self.conn.execute(f"PRAGMA table_info({table})")
            existing = {r[1] for r in cur.fetchall()}
            for name, decl in newcols:
                if name not in existing:
                    try:
                        self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
                    except sqlite3.OperationalError:
                        pass
        self.conn.commit()

    def _seed(self):
        # اقلام پیش‌فرض فیش
        cur = self.conn.execute("SELECT COUNT(*) FROM payroll_items_config")
        if cur.fetchone()[0] == 0:
            self.conn.executemany(
                "INSERT INTO payroll_items_config(code,title,kind,formula_key,tax_mode,tax_percent,insured,sort,system_locked)"
                " VALUES(?,?,?,?,?,?,1,?,?)",
                [(c, t, k, f, tm, 0, s, lk) for (c, t, k, f, tm, _, s, lk) in DEFAULT_PAYROLL_ITEMS])
        # ماژول‌های نصب‌شده
        cur = self.conn.execute("SELECT COUNT(*) FROM installed_modules")
        if cur.fetchone()[0] == 0:
            self.conn.executemany(
                "INSERT OR REPLACE INTO installed_modules(key,title,enabled,license_note) VALUES(?,?,1,?)",
                [('core_companies', 'شرکت‌ها و سال مالی', 'پایه'),
                 ('personnel', 'پرسنل و قراردادها', 'پایه'),
                 ('decrees', 'احکام پرسنلی', 'پایه'),
                 ('attendance', 'حضور و غیاب', 'پایه'),
                 ('payroll', 'حقوق و دستمزد', 'پایه'),
                 ('outputs', 'خروجی‌های استاندارد', 'پایه'),
                 ('calendar', 'تقویم و تعطیلات', 'پایه'),
                 ('report_builder', 'گزارش‌ساز حرفه‌ای', 'ماژول قابل فروش')])
        self.conn.commit()

    def get_fy_setting(self, fy_id, key, default=''):
        cur = self.conn.execute("SELECT value FROM fy_settings WHERE fiscal_year_id=? AND key=?", (fy_id, key))
        row = cur.fetchone()
        if row:
            return row['value']
        return FY_DEFAULTS.get(key, default)

    def set_fy_setting(self, fy_id, key, value):
        from .numbers import normalize_digits
        self.conn.execute(
            "INSERT OR REPLACE INTO fy_settings(fiscal_year_id,key,value) VALUES(?,?,?)",
            (fy_id, key, normalize_digits(str(value))))
        self.conn.commit()

    def ensure_fy_settings(self, fy_id):
        """ایجاد تنظیمات پیش‌فرض برای سال مالی جدید"""
        cur = self.conn.execute("SELECT COUNT(*) FROM fy_settings WHERE fiscal_year_id=?", (fy_id,))
        if cur.fetchone()[0] == 0:
            for k, v in FY_DEFAULTS.items():
                self.conn.execute("INSERT INTO fy_settings(fiscal_year_id,key,value) VALUES(?,?,?)", (fy_id, k, v))
        # پله‌های مالیاتی پیش‌فرض ۱۴۰۵
        cur = self.conn.execute("SELECT COUNT(*) FROM tax_brackets WHERE fiscal_year_id=?", (fy_id,))
        if cur.fetchone()[0] == 0:
            for (seq, f, t, r) in TAX_BRACKETS_1405:
                self.conn.execute(
                    "INSERT INTO tax_brackets(fiscal_year_id,seq,from_amount,to_amount,rate_percent) VALUES(?,?,?,?,?)",
                    (fy_id, seq, f, t, r))
        self.conn.commit()

    def get_tax_brackets(self, fy_id):
        cur = self.conn.execute(
            "SELECT * FROM tax_brackets WHERE fiscal_year_id=? ORDER BY seq", (fy_id,))
        return [dict(r) for r in cur.fetchall()]

    def backup(self, dest_path):
        """بکاپ کامل: فایل دیتابیس + تنظیمات به یک فایل"""
        import shutil
        shutil.copy2(self.path, dest_path)
        return dest_path

    def log_audit(self, username, action, details=''):
        self.conn.execute(
            "INSERT INTO audit_log(username,action,details) VALUES(?,?,?)", (username, action, details))
        self.conn.commit()
