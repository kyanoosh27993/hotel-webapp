# -*- coding: utf-8 -*-
"""
فایل‌های استاندارد بارگذاری مستقیم در سامانه‌های دولتی — نسخه ۰.۲:

【مالیات بر درآمد حقوق】 طبق «راهنمای تولید فایل الکترونیکی مالیات بر درآمد حقوق»
نسخه ۱.۷.۰.۴ سازمان امور مالیاتی (۱۴۰۴/۰۱/۲۵):
  - WPYYYYMM.TXT  فایل فهرست کارکنان (۲۳ فیلد، CSV، UTF-8، جداکننده کاما، سطرها CRLF)
  - WHYYYYMM.TXT  فایل فهرست حقوق (۳۹ فیلد ریالی، همان قالب)
  - فایل WK در ساختار جدید (۱۴۰۳ به بعد) حذف شده است.
  منبع: راهنمای رسمی اداره کل فناوری اطلاعات سازمان امور مالیاتی
  (نمونه بارگذاری: salary.tax.gov.ir → فهرست حقوق → فهرست حقوق جدید)

【بیمه تامین اجتماعی】 فایل‌های استاندارد نرم‌افزار رسمی «لیست دیسک» سازمان تامین اجتماعی:
  - DSKKAR00.dbf  فایل اطلاعات ماهیانه کارگاه
  - DSKWOR00.dbf  فایل اطلاعات ماهیانه بیمه‌شدگان (ریزکارکرد)
  محل بارگذاری: eservices.tamin.ir → کارفرمایان → لیست حق بیمه → بارگذاری فایل اطلاعات
  به‌علاوه فایل اکسل مرجع «لیست ماهانه + ریزکارکرد» با همان فیلدهای فرم سامانه
  (کد کارگاه، ردیف پیمان، سال، ماه، تعداد نفرات، روزهای کارکرد، دستمزد روزانه، مزایای مشمول)
"""
import os
import struct
from core.numbers import normalize_digits, to_persian_digits
from core import jalali as J

# ---------------------------------------------------------------- DBF (dBase III)
def dbf_write(path, fields, records, encoding='cp1256'):
    """
    نوشتن فایل DBF استاندارد dBase III.
    fields: [(name, type('C'/'N'), length, decimals), ...]
    records: list[dict] — کلید = نام فیلد
    """
    header_len = 32 + 32 * len(fields) + 1
    rec_len = sum(f[2] for f in fields) + 1
    nrec = len(records)
    buf = bytearray()
    # هدر ۳۲ بایتی dBase III
    buf += struct.pack('<BBBB', 3, 0, 0, 0)
    buf += struct.pack('<I', 0)          # تعداد رکورد — بعدا بازنویسی می‌شود
    buf += struct.pack('<HH', header_len, rec_len)
    buf += b'\x00' * 16        # رزرو
    buf += b'\x00'             # پرچم MDX
    buf += b'\x00'             # کدپیج (زبان)
    buf += b'\x00' * 2         # رزرو
    for (name, ftype, length, dec) in fields:
        nm = name.encode('ascii')[:11].ljust(11, b'\x00')
        buf += nm
        buf += ftype.encode()
        buf += b'\x00' * 4
        buf += struct.pack('<BB', length, dec)
        buf += b'\x00' * 14
    buf += b'\x0d'
    for rec in records:
        buf += b' '
        for (name, ftype, length, dec) in fields:
            v = rec.get(name, '')
            if ftype == 'N':
                if isinstance(v, float) and dec:
                    s = f"{v:.{dec}f}"
                else:
                    s = str(int(v or 0))
                s = s.rjust(length)
            else:
                s = str(v if v is not None else '')
                try:
                    s = s.encode(encoding, errors='replace').decode(encoding)
                except Exception:
                    pass
            if len(s.encode(encoding, errors='replace')) > length:
                # برش در سطح بایت (فارسی ۸ بیتی)
                b = s.encode(encoding, errors='replace')[:length]
                s = b.decode(encoding, errors='ignore')
            b = s.encode(encoding, errors='replace')
            buf += b.ljust(length)[:length]
    # تاریخ/تعداد — بازنویسی تعداد رکورد
    buf[4:8] = struct.pack('<I', nrec)
    with open(path, 'wb') as f:
        f.write(bytes(buf))
    return path


# ---------------------------------------------------------------- مالیات: جدول‌های کدگذاری رسمی
TAX_EDUCATION_MAP = {'': 1, 'زیر دیپلم': 1, 'سیکل': 1, 'سيكل': 1, 'سیکل اول متوسطه': 1,
                     'دیپلم': 2, 'فوق دیپلم': 3, 'ليسانس': 4, 'لیسانس': 4,
                     'فوق ليسانس': 5, 'فوق لیسانس': 5, 'دكتري': 6, 'دکتری': 6, 'فوق دکتری': 7}
TAX_INSURANCE_TYPE = {'خدمات درمانی': 1, 'تامین اجتماعی': 2, 'تأمین اجتماعی': 2, 'بیمه سلامت': 3,
                      'سایر': 4, 'ندارد': 5}
TAX_EXEMPTION_MAP = {'': 1, 'عدم معافیت': 1, 'جانباز': 2, 'فرزند شاهد': 3, 'آزاده': 4,
                     'ماده 10': 10, 'ماده 18': 11}  # کد ۱۰/۱۱ قابل ویرایش در فرم پرسنل
TAX_EMPLOYMENT_MAP = {'قراردادی': 1, 'شرکتی': 2, 'رسمی': 3, 'پیمانی': 4, 'مامور': 5, 'کارمزدی': 6,
                      'خرید خدمت': 7, 'ساعتی': 8, 'روزمزد': 9, 'رسمی-آزمایشی': 10,
                      'رسمی فصلی': 11, 'سایر': 12}


def _digits(s, maxlen=None):
    s = normalize_digits(str(s or '')).replace('-', '').strip()
    return s[:maxlen] if maxlen else s


def _jdate8(dstr):
    """YYYY/MM/DD شمسی → YYYYMMDD"""
    from core.numbers import parse_jalali_date_str
    p = parse_jalali_date_str(str(dstr or ''))
    if not p:
        return ''
    return f"{p[0]}{p[1]:02d}{p[2]:02d}"


def tax_wp_records(rows, company):
    """ردیف‌های فایل WP (فهرست کارکنان) — ۲۳ فیلد طبق جدول اقلام مشخصات کارکنان"""
    out = []
    for r in rows:
        edu = TAX_EDUCATION_MAP.get(str(r.get('education', '') or '').strip(), 1)
        ins_type = int(r.get('insurance_type', 2) or 2)
        rec = {
            'f1_nationality': 1,                            # 1=ایرانی
            'f2_national_id': _digits(r.get('national_id')),  # بدون خط تیره
            'f3_first': str(r.get('first_name') or ''),
            'f4_last': str(r.get('last_name') or ''),
            'f5_father': str(r.get('father_name') or ''),
            'f6_birth': _jdate8(r.get('birth_date')),
            'f7_idnum': _digits(r.get('id_number')),
            'f8_birthplace': str(r.get('birth_place') or r.get('id_issue_place') or ''),
            'f9_education': edu,
            'f10_ins_type': ins_type,
            'f11_ins_no': _digits(r.get('sso_number'), 10),
            'f12_ins_name': 'تامین اجتماعی' if ins_type == 2 else str(r.get('sso_insurer') or ''),
            'f13_exemption': int(r.get('tax_exemption_code', 1) or 1),
            'f14_country_citizen': 103,                     # 103=جمهوری اسلامی ایران
            'f15_country_living': 103,
            'f16_postal': _digits(r.get('postal_code'), 10),
            'f17_address': str(r.get('address') or ''),
            'f18_job_category': int(r.get('job_category', 12) or 12),
            'f19_position': str(r.get('job_title') or ''),
            'f20_employment': int(r.get('employment_type', 1) or 1),
            'f21_start': _jdate8(r.get('hire_date')),
            'f22_end': _jdate8(r.get('end_work_date', '')),
            'f23_retire': '',
        }
        out.append(rec)
    return out


WP_FIELDS = [
    ('F1', 'N', 1, 0), ('F2', 'C', 10, 0), ('F3', 'C', 30, 0), ('F4', 'C', 30, 0),
    ('F5', 'C', 30, 0), ('F6', 'C', 8, 0), ('F7', 'C', 10, 0), ('F8', 'C', 30, 0),
    ('F9', 'N', 1, 0), ('F10', 'N', 1, 0), ('F11', 'C', 10, 0), ('F12', 'C', 30, 0),
    ('F13', 'C', 5, 0), ('F14', 'N', 3, 0), ('F15', 'N', 3, 0), ('F16', 'C', 10, 0),
    ('F17', 'C', 100, 0), ('F18', 'N', 2, 0), ('F19', 'C', 50, 0), ('F20', 'N', 2, 0),
    ('F21', 'C', 8, 0), ('F22', 'C', 8, 0), ('F23', 'C', 8, 0)]

WH_ORDER = [  # (کلید داخلی، توضیح) — ۳۹ فیلد فهرست حقوق (ریالی)
    'f1_national_id', 'f2_paytype', 'f3_service_place', 'f4_budget_except', 'f5_currency',
    'f6_fx_rate', 'f7_gross_sustainable_cash', 'f8_arrears_sus_cash', 'f9_housing',
    'f10_housing_deduct', 'f11_car', 'f12_car_deduct', 'f13_other_sus_noncash',
    'f14_arrears_sus_noncash', 'f15_honorary', 'f16_research', 'f17_overtime', 'f18_travel',
    'f19_mission', 'f20_karaneh', 'f21_bonus', 'f22_year_end_bonus', 'f23_annual_eydi',
    'f24_severance', 'f25_firing_damages', 'f26_buyback', 'f27_seniority_pay',
    'f28_unused_leave', 'f29_other_non_sus_cash', 'f30_arrears_non_sus_cash',
    'f31_non_sus_noncash', 'f32_arrears_non_sus_noncash', 'f33_ins137_health',
    'f34_ins137_life', 'f35_net_paid', 'f36_teaching', 'f37_watchman', 'f38_welfare',
    'f39_effort']

# نگاشت آیتم‌های فیش → فیلد WH (قابل ویرایش در فرم خروجی)
DEFAULT_WH_ITEM_MAP = {
    'base_wage': 7, 'seniority': 7, 'housing': 7, 'food': 7, 'child_allow': 7,
    'worker_ben': 7, 'shift_allow': 7, 'attraction': 7, 'family_allow': 7,
    'adjustment': 7, 'supervision': 7, 'labor_market': 7, 'education_aid': 7,
    'fixed_ot': 7, 'other_ben': 7,          # مزایای مستمر نقدی → فیلد ۷
    'overtime': 17,                          # اضافه‌کاری → فیلد ۱۷
    'holiday_work': 29, 'friday_work': 29, 'night_work': 29,
    'tax_free_other': 29,                    # سایر غیرمستمر نقدی → فیلد ۲۹
    'eydi': 23, 'year_end_bonus': 22, 'bonus': 21, 'seniority_settle': 27,
    'unused_leave': 28, 'severance': 24,
}


def tax_wh_records(db, period_id, rows):
    """ردیف‌های فایل WH (فهرست حقوق ریالی) — ۳۹ فیلد. مبلغ‌ها از اقلام محاسبه‌شده فیش"""
    cur = db.conn.execute(
        """SELECT l.personnel_id, l.item_code, l.amount FROM payroll_lines l
           JOIN payroll_items_config i ON i.code=l.item_code
           WHERE l.period_id=? AND i.kind='earning'""", (period_id,))
    per_amounts = {}
    for r in cur.fetchall():
        per_amounts.setdefault(r['personnel_id'], {})[r['item_code']] = r['amount'] or 0
    out = []
    for r in rows:
        amounts = per_amounts.get(r['personnel_id'], {})
        fields = {i: 0 for i in range(1, 40)}
        for code, amt in amounts.items():
            idx = DEFAULT_WH_ITEM_MAP.get(code)
            if idx:
                fields[idx] += amt
        fields[9] = 1        # نحوه استفاده از مسکن: عدم استفاده
        fields[11] = 1       # اتومبیل: عدم استفاده
        fields[35] = (r['net_pay'] or 0) + (r.get('prev_balance', 0) or 0)
        rec = {
            'f1_national_id': _digits(r.get('national_id')),
            'f2_paytype': 1, 'f3_service_place': 1, 'f4_budget_except': 1,
            'f5_currency': 84, 'f6_fx_rate': 1,
        }
        for i in range(7, 40):
            rec[WH_ORDER[i - 1]] = round(fields[i])
        out.append(rec)
    return out


from openpyxl.utils import get_column_letter

WH_FIELDS = [('F' + str(i), 'N', 15 if i >= 7 else 5, 0) for i in range(1, 40)]  # مرجع طول فیلدها


def _wh_line(rec, keys):
    vals = []
    for k in keys:
        v = rec.get(k, '')
        if isinstance(v, float) and v == int(v):
            v = int(v)
        vals.append(str(v))
    return ','.join(vals)


def make_tax_files(db, period_id, rows, company, out_dir):
    """ساخت فایل‌های استاندارد مالیات: WPYYYYMM.TXT + WHYYYYMM.TXT در پوشه out_dir"""
    per, rows2 = None, rows
    cur = db.conn.execute("SELECT jy, jm FROM payroll_periods WHERE id=?", (period_id,))
    p = cur.fetchone()
    if not p:
        raise ValueError('دوره یافت نشد')
    stamp = f"{p['jy']}{p['jm']:02d}"
    wp_recs = tax_wp_records(rows, company)
    wh_recs = tax_wh_records(db, period_id, rows)
    wp_path = os.path.join(out_dir, f"WP{stamp}.TXT")
    wh_path = os.path.join(out_dir, f"WH{stamp}.TXT")
    wp_keys = ['f1_nationality', 'f2_national_id', 'f3_first', 'f4_last', 'f5_father', 'f6_birth',
               'f7_idnum', 'f8_birthplace', 'f9_education', 'f10_ins_type', 'f11_ins_no',
               'f12_ins_name', 'f13_exemption', 'f14_country_citizen', 'f15_country_living',
               'f16_postal', 'f17_address', 'f18_job_category', 'f19_position', 'f20_employment',
               'f21_start', 'f22_end', 'f23_retire']
    with open(wp_path, 'w', encoding='utf-8', newline='') as f:
        f.write('\r\n'.join(_wh_line(r, wp_keys) for r in wp_recs))
        if wp_recs:
            f.write('\r\n')
    with open(wh_path, 'w', encoding='utf-8', newline='') as f:
        f.write('\r\n'.join(_wh_line(r, WH_ORDER) for r in wh_recs))
        if wh_recs:
            f.write('\r\n')
    return wp_path, wh_path


def make_wh_excel(path, rows, company, subtitle):
    """قالب اکسل WH مطابق فایل رسمی سامانه (۳۹ ستون) — برای کنترل/ورود دستی"""
    from core import exports as EX
    headers = ['کد ملی', 'نوع پرداخت', 'وضعیت محل خدمت', 'استثنائات قانون بودجه', 'نوع ارز',
               'نرخ تسعیر', 'جمع ناخالص مستمر نقدی', 'مستمر نقدی معوق', 'مسکن',
               'کسر مسکن', 'اتومبیل', 'کسر اتومبیل', 'سایر مستمر غیرنقدی', 'مستمر غیرنقدی معوق',
               'حق‌الزحمه/مشاوره', 'قراردادهای پژوهشی', 'اضافه‌کاری', 'هزینه سفر',
               'فوق‌العاده ماموریت', 'کارانه', 'پاداش', 'پاداش آخر سال', 'عیدی سالانه',
               'پاداش پایان خدمت', 'خسارت اخراج', 'بازخرید خدمت', 'حق سنوات',
               'مرخصی استفاده نشده', 'سایر غیرمستمر نقدی', 'غیرمستمر نقدی معوق',
               'غیرمستمر غیرنقدی', 'غیرمستمر غیرنقدی معوق', 'بیمه درمان ماده ۱۳۷',
               'بیمه عمر ماده ۱۳۷', 'خالص پرداختی', 'حق‌التدریس', 'حق‌کشیک',
               'رفاهی و بهره‌وری', 'حق‌السعی']
    data = []
    for r in rows:
        data.append([r.get('f1_national_id'), 1, 1, 1, 84, 1] +
                    [r.get(WH_ORDER[i - 1], 0) for i in range(7, 40)])
    money = set(range(6, 39))
    EX.export_table_xlsx(path, 'فایل فهرست حقوق WH (قالب سامانه مالیات حقوق)',
                         subtitle, headers, data, money_cols=money,
                         sum_cols=money, company=company)
    return path


# ---------------------------------------------------------------- بیمه تامین اجتماعی
def insurance_summary_row(company, rows, jy, jm):
    """سطر خلاصه لیست ماهانه (فیلدهای فرم سامانه): تعداد نفرات، جمع روز کارکرد، جمع دستمزد، جمع مزایا"""
    n = len(rows)
    total_days = sum(int((r.get('worked_days') or 0)) or 30 for r in rows)
    daily_rates = []
    for r in rows:
        base = r.get('insured_base', 0) or 0
        daily_rates.append(base / max(total_days / max(n, 1), 1) if n else 0)
    total_daily = sum(daily_rates)
    total_monthly = sum(r.get('insured_base', 0) or 0 for r in rows)
    total_ben = 0  # مزایای غیرنقدی مشمول جداگانه؛ پیش‌فرض صفر
    return {'count': n, 'days': total_days, 'daily': round(total_daily),
            'monthly': round(total_monthly), 'ben': total_ben}


def make_insurance_files(db, period_id, rows, company, out_dir, cal_days=30):
    """
    ساخت فایل‌های بیمه:
    - DSKKAR00.dbf (اطلاعات ماهیانه کارگاه)
    - DSKWOR00.dbf (اطلاعات ماهیانه بیمه‌شدگان — ریزکارکرد)
    - اکسل مرجع (لیست ماهانه + ریزکارکرد مطابق فیلدهای فرم سامانه)
    ساختار رکورد DBF مطابق قالب نرم‌افزار رسمی «لیست دیسک» است؛ پیش از ارسال قطعی،
    یک بار در سامانه بارگذاری آزمایشی کنید. فایل اکسل همیشه مبنای مطمئن ورود آنلاین است.
    """
    cur = db.conn.execute("SELECT jy, jm FROM payroll_periods WHERE id=?", (period_id,))
    p = cur.fetchone()
    jy, jm = p['jy'], p['jm']
    workshop = normalize_digits(str((company or {}).get('sso_workshop_code') or ''))
    branch = normalize_digits(str((company or {}).get('sso_branch_code') or ''))[:3]
    contract_row = normalize_digits(str((company or {}).get('sso_contract_row') or '')) or '000'
    kar_name = (company or {}).get('manager_name') or (company or {}).get('name') or ''
    ins_rows = [r for r in rows if r.get('sso_number')]
    n = len(ins_rows)
    total_days = sum(int(r.get('worked_days') or 0) or cal_days for r in ins_rows)
    total_daily = round(sum((r.get('insured_base', 0) or 0) * cal_days / max(total_days, 1)
                            for r in ins_rows))
    total_ben = 0
    kar = {
        'KARGAH': workshop, 'ROW': contract_row, 'NAME': kar_name,
        'BRANCH': branch, 'YY': f"{jy % 100:02d}", 'MM': f"{jm:02d}",
        'PNUM': n, 'DAY': total_days, 'DAILY': total_daily, 'MSTMR': total_ben,
    }
    wor = []
    for r in ins_rows:
        days = int(r.get('worked_days') or 0) or cal_days
        base = r.get('insured_base', 0) or 0
        wor.append({
            'KARGAH': workshop, 'ROW': contract_row,
            'CODE': _digits(r.get('sso_number'), 10),
            'NATCODE': _digits(r.get('national_id'), 10),
            'NAME': str(r.get('first_name') or ''),
            'FAM': str(r.get('last_name') or ''),
            'DAY': days,
            'DAILY': round(base * cal_days / max(total_days, 1)),
            'MS': 0,
            'BASE': round(base),
            'WINS': round(r.get('worker_ins', 0) or 0),
            'EINS': round(r.get('employer_ins', 0) or 0),
            'UINS': round(r.get('unemployment_ins', 0) or 0),
        })
    kar_fields = [('KARGAH', 'C', 10, 0), ('ROW', 'C', 3, 0), ('NAME', 'C', 40, 0),
                  ('BRANCH', 'C', 3, 0), ('YY', 'C', 2, 0), ('MM', 'C', 2, 0),
                  ('PNUM', 'N', 4, 0), ('DAY', 'N', 5, 0), ('DAILY', 'N', 14, 0),
                  ('MSTMR', 'N', 14, 0)]
    wor_fields = [('KARGAH', 'C', 10, 0), ('ROW', 'C', 3, 0), ('CODE', 'C', 10, 0),
                  ('NATCODE', 'C', 10, 0), ('NAME', 'C', 15, 0), ('FAM', 'C', 25, 0),
                  ('DAY', 'N', 3, 0), ('DAILY', 'N', 10, 0), ('MS', 'N', 12, 0),
                  ('BASE', 'N', 14, 0), ('WINS', 'N', 12, 0), ('EINS', 'N', 12, 0),
                  ('UINS', 'N', 12, 0)]
    kar_path = dbf_write(os.path.join(out_dir, 'DSKKAR00.dbf'), kar_fields, [kar])
    wor_path = dbf_write(os.path.join(out_dir, 'DSKWOR00.dbf'), wor_fields, wor)
    return kar_path, wor_path


def insurance_excel(path, rows, company, subtitle, cal_days=30):
    """اکسل مرجع بیمه: برگه ۱ = لیست ماهانه (خلاصه کارگاه)، برگه ۲ = ریزکارکرد بیمه‌شدگان"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    wb = Workbook()
    thin = Border(*[Side(style='thin', color='94A3B8')] * 4)
    hdr_font = Font(name='Tahoma', size=9, bold=True, color='111827')
    hdr_fill = PatternFill('solid', fgColor='E8EAED')
    cell_font = Font(name='Tahoma', size=9, color='111827')

    def fill_sheet(ws, headers, data, money_cols=(), total_row=True):
        ws.sheet_view.rightToLeft = True
        for i, h in enumerate(headers, 1):
            c = ws.cell(1, i, h)
            c.font, c.fill, c.border = hdr_font, hdr_fill, thin
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True,
                                    shrink_to_fit=True)
        for ri, row in enumerate(data, 2):
            for ci, v in enumerate(row, 1):
                c = ws.cell(ri, ci, v)
                c.font, c.border = cell_font, thin
                c.alignment = Alignment(horizontal='center', vertical='center', shrink_to_fit=True)
                if (ri - 2) % 2:
                    c.fill = PatternFill('solid', fgColor='F5F6F8')
                if ci - 1 in money_cols and isinstance(v, (int, float)):
                    c.number_format = '#,##0'
        if total_row and data:
            rr = len(data) + 2
            ws.cell(rr, 1, 'جمع کل').font = Font(name='Tahoma', size=9, bold=True)
            for ci in money_cols:
                letter = get_column_letter(ci + 1)
                c = ws.cell(rr, ci + 1, f"=SUM({letter}2:{letter}{rr-1})")
                c.font = Font(name='Tahoma', size=9, bold=True)
                c.number_format = '#,##0'
                c.border = thin
        for i, h in enumerate(headers, 1):
            ws.column_dimensions[get_column_letter(i)].width = 16

    ws1 = wb.active
    ws1.title = 'لیست ماهانه کارگاه'
    ins_rows = [r for r in rows if r.get('sso_number')]
    n = len(ins_rows)
    total_days = sum(int(r.get('worked_days') or 0) or cal_days for r in ins_rows)
    total_base = sum(r.get('insured_base', 0) or 0 for r in ins_rows)
    fill_sheet(ws1, ['شرح', 'مقدار'], [
        ['کد کارگاه', (company or {}).get('sso_workshop_code', '')],
        ['ردیف پیمان', (company or {}).get('sso_contract_row', '') or '000'],
        ['سال', subtitle.split()[-1] if subtitle else ''],
        ['ماه', subtitle],
        ['تعداد بیمه‌شدگان', n],
        ['جمع روزهای کارکرد', total_days],
        ['جمع مزایای ماهانه مشمول (مستمر)', round(total_base)],
        ['جمع دستمزد ماهانه (روز×دستمزد)', round(total_base)],
    ], money_cols=(), total_row=False)
    ws2 = wb.create_sheet('ریزکارکرد بیمه‌شدگان')
    data = []
    for i, r in enumerate(ins_rows, 1):
        days = int(r.get('worked_days') or 0) or cal_days
        base = r.get('insured_base', 0) or 0
        total_ins = (r['worker_ins'] or 0) + (r['employer_ins'] or 0) + (r['unemployment_ins'] or 0)
        data.append([i, r.get('sso_number'), r.get('national_id'),
                     f"{r['first_name']} {r['last_name']}", days,
                     round(base * cal_days / max(total_days, 1)), round(base),
                     r['worker_ins'], r['employer_ins'], r['unemployment_ins'], total_ins])
    fill_sheet(ws2, ['ردیف', 'شماره بیمه', 'کد ملی', 'نام و نام خانوادگی', 'روزهای کارکرد',
                     'دستمزد روزانه', 'جمع دستمزد و مزایای مشمول', 'سهم کارگر',
                     'سهم کارفرما (۲۰٪)', 'بیکاری (۳٪)', 'جمع حق بیمه'],
               data, money_cols={5, 6, 7, 8, 9, 10})
    wb.save(path)
    return path
