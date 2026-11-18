# -*- coding: utf-8 -*-
"""
ایمپورت فایل خروجی دستگاه حضور و غیاب («گزارش روزانه فردی»)
ساختار فایل (بررسی‌شده روی فایل واقعی مشتری):
- هر شیت = یک پرسنل؛ کد دستگاه در ردیف «قسمت» (شماره کارت) و نام در ردیف «نام»
- دوره از ردیف ازتاریخ/تاتاریخ
- هدر جدول روزانه در ردیف حاوی «وضعیت/اضافه آزاد/...» با ستون‌های:
  وضعیت | اضافه آزاد | اضافه کار | کسرکار | تعجیل | تاخیر | مرخصی | ماموریت | کارکرد | مجموع |
  خروج3 | ورود3 | خروج2 | ورود2 | خروج1 | ورود1 | روز هفته | تاریخ
- ردیف «مجموع» جمع‌ها و ردیف پایانی خلاصه روزها
تطبیق پرسنل با «شماره کارت» ثبت‌شده در پرونده پرسنل انجام می‌شود.
"""
import xlrd
from core.numbers import parse_hhmm, normalize_digits, parse_jalali_date_str


def _find_cell(sh, text, start_row=0, end_row=None):
    """جستجوی متن در سلول‌ها و برگرداندن (row, col)"""
    end_row = end_row or sh.nrows
    for r in range(start_row, end_row):
        for c in range(sh.ncols):
            v = sh.cell_value(r, c)
            if isinstance(v, str) and text in v:
                return (r, c)
    return None


def _value_right(sh, r, c, max_shift=6):
    """اولین مقدار عددی/متنی در ستون‌های بعدی سلول برچسب"""
    for cc in range(c + 1, min(c + max_shift + 1, sh.ncols)):
        v = sh.cell_value(r, cc)
        if v not in ('', None):
            return v
    return None


def parse_device_file(path, log=print):
    """
    پارس کامل فایل دستگاه →
    {'period': (jy, jm), 'employees': [{card_no, name, daily: [...], totals: {...}}]}
    """
    wb = xlrd.open_workbook(path)
    result = {'period': None, 'employees': []}
    for si in range(wb.nsheets):
        sh = wb.sheet_by_index(si)
        emp = _parse_sheet(sh, log)
        if emp:
            result['employees'].append(emp)
            if emp.get('period') and not result['period']:
                result['period'] = emp['period']
    return result


def _parse_sheet(sh, log):
    # کد دستگاه (قسمت)
    loc = _find_cell(sh, 'قسمت')
    card_no = ''
    if loc:
        v = _value_right(sh, loc[0], loc[1])
        card_no = normalize_digits(v).strip()
    # نام
    loc = _find_cell(sh, 'نام')
    name = ''
    if loc:
        for cc in range(loc[1] - 8, loc[1]):
            v = sh.cell_value(loc[0], cc) if cc >= 0 else ''
            if isinstance(v, str) and v.strip():
                name = v.strip()
    # دوره
    period = None
    loc = _find_cell(sh, 'ازتاریخ')
    if loc:
        v = sh.cell_value(loc[0], loc[1] - 6) if loc[1] >= 6 else ''
        period = parse_jalali_date_str(v)
    if period is None:
        loc = _find_cell(sh, 'تاتاریخ')
        if loc:
            v = sh.cell_value(loc[0], loc[1] - 7) if loc[1] >= 7 else ''
            period = parse_jalali_date_str(v)
    if not card_no and not name:
        return None

    # هدر جدول روزانه: ردیف حاوی «روز هفته»
    hdr = _find_cell(sh, 'روز هفته')
    if not hdr:
        log(f'  ⚠ شیت {card_no or name}: جدول روزانه یافت نشد')
        return None
    hr = hdr[0]
    # نگاشت برچسب → ستون
    colmap = {}
    for c in range(sh.ncols):
        v = sh.cell_value(hr, c)
        if isinstance(v, str):
            t = v.strip().lstrip(':').strip()
            colmap[t] = c
    g = lambda key: colmap.get(key)

    daily = []
    totals = {'overtime_min': 0, 'missing_min': 0, 'late_min': 0, 'early_min': 0,
              'leave_min': 0, 'mission_min': 0, 'free_overtime_min': 0, 'worked_min': 0}
    for r in range(hr + 1, sh.nrows):
        dv = sh.cell_value(r, g('تاریخ')) if g('تاریخ') is not None else ''
        day_period = parse_jalali_date_str(dv)
        if day_period is None:
            # ردیف جمع / خلاصه
            if g('وضعیت') is not None and isinstance(sh.cell_value(r, g('وضعیت')), str) \
                    and 'مجموع' in str(sh.cell_value(r, g('وضعیت'))):
                totals['free_overtime_min'] = parse_hhmm(sh.cell_value(r, g('اضافه آزاد')), 0) if g('اضافه آزاد') is not None else 0
                totals['overtime_min'] = parse_hhmm(sh.cell_value(r, g('اضافه کار')), 0) if g('اضافه کار') is not None else 0
                totals['missing_min'] = parse_hhmm(sh.cell_value(r, g('کسرکار')), 0) if g('کسرکار') is not None else 0
                totals['late_min'] = parse_hhmm(sh.cell_value(r, g('تاخیر')), 0) if g('تاخیر') is not None else 0
                totals['early_min'] = parse_hhmm(sh.cell_value(r, g('تعجیل')), 0) if g('تعجیل') is not None else 0
                totals['leave_min'] = parse_hhmm(sh.cell_value(r, g('مرخصی')), 0) if g('مرخصی') is not None else 0
                totals['mission_min'] = parse_hhmm(sh.cell_value(r, g('ماموریت')), 0) if g('ماموریت') is not None else 0
                totals['worked_min'] = parse_hhmm(sh.cell_value(r, g('مجموع')), 0) if g('مجموع') is not None else 0
            continue
        if period and day_period[0] == period[0] and day_period[1] != period[1]:
            continue  # فقط روزهای ماه دوره
        def minute(key):
            c = g(key)
            return parse_hhmm(sh.cell_value(r, c), 0) if c is not None else 0
        def clock(key):
            c = g(key)
            if c is None:
                return -1
            v = sh.cell_value(r, c)
            if v in ('', None):
                return -1
            s = normalize_digits(v).strip().lstrip('*').strip()
            if not s:
                return -1
            return parse_hhmm(s, -1)
        status = ''
        c = g('وضعیت')
        if c is not None:
            status = str(sh.cell_value(r, c) or '').strip()
        daily.append({
            'date': (day_period[0], day_period[1], day_period[2]),
            'status': status,
            'entry1': clock('ورود1'), 'exit1': clock('خروج1'),
            'entry2': clock('ورود2'), 'exit2': clock('خروج2'),
            'entry3': clock('ورود3'), 'exit3': clock('خروج3'),
            'late_min': minute('تاخیر'), 'early_min': minute('تعجیل'),
            'missing_min': minute('کسرکار'), 'leave_min': minute('مرخصی'),
            'mission_min': minute('ماموریت'), 'overtime_min': minute('اضافه کار'),
            'free_overtime_min': minute('اضافه آزاد'),
            'worked_min': minute('مجموع'),
        })
    return {'card_no': card_no, 'name': name, 'period': period, 'daily': daily, 'totals': totals}


def save_to_db(db, fy_id, parsed, cal_service=None, progress=None, company_id=None):
    """
    ذخیره نتیجه پارس در دیتابیس.
    تطبیق پرسنل: اول با شماره کارت (کد دستگاه)، اگر نبود با شباهت نام؛
    اگر هیچ تطبیقی نبود، پرسنل به‌صورت خودکار با وضعیت «غیرفعال» ساخته می‌شود
    (ساعات کارکردش وارد برنامه می‌شود ولی در محاسبه حقوق نمی‌آید تا اطلاعات تکمیل شود).
    خروجی: {'saved': n, 'unmatched': [(card_no, name), ...], 'new_employees': [نام‌ها], 'month_id': id}
    """
    import re as _re
    from core import jalali as J
    from core.numbers import clean_text

    if not parsed['employees']:
        return {'saved': 0, 'unmatched': [], 'new_employees': [], 'month_id': None, 'no_period': True}

    per = parsed['period'] or parsed['employees'][0].get('period')
    if not per:
        return {'saved': 0, 'unmatched': [], 'new_employees': [], 'month_id': None, 'no_period': True}
    jy, jm = per[0], per[1]

    cur = db.conn.execute(
        "INSERT OR REPLACE INTO attendance_months(fiscal_year_id,jy,jm,source,imported_at)"
        " VALUES(?,?,?,?,datetime('now','localtime'))", (fy_id, jy, jm, 'فایل دستگاه'))
    db.conn.commit()
    cur = db.conn.execute("SELECT id FROM attendance_months WHERE fiscal_year_id=? AND jy=? AND jm=?",
                          (fy_id, jy, jm))
    month_id = cur.fetchone()['id']
    db.conn.execute("DELETE FROM attendance_daily WHERE month_id=?", (month_id,))

    # فهرست پرسنل این شرکت
    cur = db.conn.execute("""SELECT p.id, p.card_no, p.first_name, p.last_name FROM personnel p
                             JOIN fiscal_years fy ON fy.company_id=p.company_id WHERE fy.id=?""", (fy_id,))
    plist = [dict(r) for r in cur.fetchall()]
    if company_id is None:
        cur = db.conn.execute("SELECT company_id FROM fiscal_years WHERE id=?", (fy_id,))
        company_id = cur.fetchone()['company_id']

    def norm_name(s):
        return _re.sub(r'\s+', '', clean_text(s).replace('ی', 'ی').replace('ك', 'ک'))

    saved, unmatched, new_employees = 0, [], []
    for emp in parsed['employees']:
        pid = None
        card = normalize_digits(emp['card_no']).strip()
        # ۱) تطبیق با شماره کارت
        for p in plist:
            if card and normalize_digits(str(p['card_no'] or '')).strip() == card:
                pid = p['id']
                break
        # ۲) تطبیق با نام
        if pid is None:
            en = norm_name(emp['name'])
            if en:
                for p in plist:
                    full = norm_name(str(p['first_name'] or '') + ' ' + str(p['last_name'] or ''))
                    if en and (en in full or full in en):
                        pid = p['id']
                        break
        created_new = False
        if pid is None:
            # ۳) پرسنل جدید خودکار — غیرفعال تا اطلاعات پرونده کامل شود
            name = clean_text(emp['name'] or '')
            parts = name.split()
            first = parts[0] if parts else ''
            last = ' '.join(parts[1:]) if len(parts) > 1 else ''
            base = card or 'D'
            code = base
            i = 2
            while True:
                cur = db.conn.execute(
                    "SELECT 1 FROM personnel WHERE company_id=? AND personnel_code=?",
                    (company_id, code))
                if not cur.fetchone():
                    break
                code = f"{base}-{i}"
                i += 1
            cur = db.conn.execute(
                """INSERT INTO personnel(company_id,personnel_code,card_no,first_name,last_name,status,notes)
                   VALUES(?,?,?,?,?,?,?)""",
                (company_id, code, card, first, last, 'غیرفعال',
                 'ایجاد خودکار از فایل دستگاه — اطلاعات پرسنل و قرارداد باید تکمیل شود'))
            pid = cur.lastrowid
            plist.append({'id': pid, 'card_no': card, 'first_name': first, 'last_name': last})
            unmatched.append((card, name))
            new_employees.append(name or card)
            created_new = True
        for d in emp['daily']:
            db.conn.execute(
                """INSERT OR REPLACE INTO attendance_daily
                   (month_id,personnel_id,day,status,entry1,exit1,entry2,exit2,entry3,exit3,
                    late_min,early_min,missing_min,leave_min,mission_min,overtime_min,free_overtime_min,worked_min)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (month_id, pid, d['date'][2], d['status'],
                 d['entry1'], d['exit1'], d['entry2'], d['exit2'], d['entry3'], d['exit3'],
                 d['late_min'], d['early_min'], d['missing_min'], d['leave_min'],
                 d['mission_min'], d['overtime_min'], d['free_overtime_min'], d['worked_min']))
        saved += 1
        if progress:
            progress(emp['name'], saved)
    db.conn.commit()
    # بازمحاسبه تاخیر/تعجیل/کسرکار بر اساس شیفت و گریس
    try:
        from core import shifts as SH
        from core.numbers import parse_number
        grace_l = int(parse_number(db.get_fy_setting(fy_id, 'late_grace_minutes', '10'), 10))
        grace_e = int(parse_number(db.get_fy_setting(fy_id, 'early_grace_minutes', '10'), 10))
        lm = SH.leaves_map_for_month(db, month_id, jy, jm)
        SH.recalc_month(db, month_id, cal_service, grace_l, grace_e, lm)
    except Exception:
        pass
    return {'saved': saved, 'unmatched': unmatched, 'new_employees': new_employees,
            'month_id': month_id, 'period': (jy, jm)}
