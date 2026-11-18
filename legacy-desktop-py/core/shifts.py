# -*- coding: utf-8 -*-
"""
موتور شیفت کاری و طبقه‌بندی روزانه حضور و غیاب:
- تعریف شیفت برای هر روز هفته (ساعت شروع/پایان) و انتساب به هر پرسنل
- محاسبه خودکار تاخیر/تعجیل/کسرکار/مرخصی از روی ورود/خروج دستگاه + بازه گریس قابل تنظیم
- تشخیص مرخصی روزانه/ساعتی/استعلاجی/بدون حقوق از جدول مرخصی‌ها و وضعیت دستگاه
- آمار ماهانه برای محاسبه حقوق (روزهای پرداختی، اضافه‌کار، تعطیل‌کاری، جمعه‌کاری)
"""
import json
import jdatetime
from . import jalali as J
from .numbers import parse_number

SUNDAY = 0  # شنبه=0 ... جمعه=6 (jdatetime.weekday)

DEFAULT_SCHEDULE = {str(d): [480, 960] for d in range(6)}  # شنبه تا پنجشنبه ۸ تا ۱۶

STATUS_PAID_LEAVES = ('استحقاقی', 'استعلاجی', 'ساعتی', 'مرخصی')
STATUS_UNPAID = ('بدون حقوق', 'بدون حقوق (روزانه)')


def load_shifts(db, company_id):
    cur = db.conn.execute(
        "SELECT * FROM shifts WHERE company_id=? ORDER BY name", (company_id,))
    out = []
    for r in cur.fetchall():
        d = dict(r)
        try:
            d['schedule'] = json.loads(d['schedule'] or '{}')
        except Exception:
            d['schedule'] = {}
        out.append(d)
    return out


def save_shift(db, company_id, name, schedule, notes='', shift_id=None):
    """schedule: dict {int weekday(0-6): [start_min, end_min]} — روزهای غایب اصلا کلید ندارند"""
    s = json.dumps({str(k): list(v) for k, v in schedule.items()}, ensure_ascii=False)
    if shift_id:
        db.conn.execute("UPDATE shifts SET name=?, schedule=?, notes=? WHERE id=?",
                        (name, s, notes, shift_id))
    else:
        db.conn.execute("INSERT INTO shifts(company_id,name,schedule,notes) VALUES(?,?,?,?)",
                        (company_id, name, s, notes))
    db.conn.commit()


def delete_shift(db, shift_id):
    db.conn.execute("DELETE FROM shifts WHERE id=?", (shift_id,))
    db.conn.commit()


def person_shift(db, person, jy, jm):
    """شیفت مؤثر فرد در ماه: اول انتساب ماه، بعد شیفت پیش‌فرض پرونده، بعد پیش‌فرض ۸-۱۶"""
    cur = db.conn.execute(
        "SELECT shift_id FROM shift_assignments WHERE personnel_id=? AND jy=? AND jm=?",
        (person['id'], jy, jm))
    r = cur.fetchone()
    sid = r['shift_id'] if r else person.get('shift_id')
    if sid:
        cur = db.conn.execute("SELECT * FROM shifts WHERE id=?", (sid,))
        sh = cur.fetchone()
        if sh:
            try:
                return json.loads(sh['schedule'] or '{}')
            except Exception:
                pass
    return dict(DEFAULT_SCHEDULE)


def expected_minutes(schedule, weekday):
    """دقیقه موظفی یک روز هفته طبق شیفت؛ ۰ = تعطیل/بدون شیفت"""
    v = schedule.get(str(weekday), schedule.get(weekday))
    if not v:
        return 0
    try:
        s, e = int(v[0]), int(v[1])
        return max(0, e - s)
    except Exception:
        return 0


def recompute_day(row, expected_min, grace_late, grace_early, is_holiday, sched_start=None, sched_end=None):
    """
    طبقه‌بندی یک روز از روی ورود/خروج‌ها و شیفت.
    row: dict با entry1..3, exit1..3, leave_min, mission_min, status
    sched_start/sched_end: دقیقه شروع/پایان شیفت (برای محاسبه تاخیر/تعجیل)
    خروجی: dict با late_min, early_min, missing_min, leave_min, status, expected_min
    """
    expected = expected_min
    entries = [row.get(k, -1) for k in ('entry1', 'entry2', 'entry3')]
    exits = [row.get(k, -1) for k in ('exit1', 'exit2', 'exit3')]
    entries = [e for e in entries if e is not None and e >= 0]
    exits = [e for e in exits if e is not None and e >= 0]
    worked = row.get('worked_min', 0) or 0
    leave = row.get('leave_min', 0) or 0
    mission = row.get('mission_min', 0) or 0
    late = early = missing = 0
    status = row.get('status', '') or ''
    if status == 'بدون شیفت':
        status = ''  # مقدار پیش‌فرض دیتابیس — وضعیت خودکار محاسبه شود

    if expected <= 0:
        # روز تعطیل طبق شیفت: کارکرد = تعطیل‌کاری/اضافه‌کار، تاخیر معنا ندارد
        return {'late_min': 0, 'early_min': 0, 'missing_min': 0,
                'leave_min': leave, 'status': status or ('تعطیل' if worked <= 0 else 'تعطیل‌کاری'),
                'expected_min': 0}

    if entries:
        first_in = min(entries)
        # مرخصی ساعتی ابتدای روز: ورود موقت در شروع شیفت نیست، مبنای تاخیر = اولین ورود
        raw_late = max(0, first_in - (sched_start if sched_start is not None else 0))
        late = max(0, raw_late - grace_late) if not _full_day_leave(leave, expected, mission) else 0
    if exits:
        last_out = max(exits)
        if sched_end is not None:
            raw_early = max(0, sched_end - last_out)
            early = max(0, raw_early - grace_early)
    if not _full_day_leave(leave, expected, mission):
        missing = max(0, expected - worked - leave - mission)
        if missing > 0 and leave >= expected:
            missing = 0    # وضعیت خودکار اگر دستگاه وضعیت نداده باشد
    if not status:
        if _full_day_leave(leave, expected, mission):
            status = 'مرخصی'
        elif worked <= 0 and leave <= 0 and mission <= 0:
            status = 'غایب'
        elif late > 0 and early > 0:
            status = 'تاخیر و تعجیل'
        elif late > 0:
            status = 'تاخیر'
        elif early > 0:
            status = 'تعجیل'
        elif mission > 0 and worked <= 0:
            status = 'ماموریت'
        else:
            status = 'حاضر'
    return {'late_min': late, 'early_min': early, 'missing_min': missing,
            'leave_min': leave, 'status': status, 'expected_min': expected}


def _full_day_leave(leave, expected, mission=0):
    return expected > 0 and (leave + mission) >= expected


def recalc_month(db, month_id, cal_service, grace_late=10, grace_early=10, leave_map=None):
    """
    بازمحاسبه همه روزهای ماه بر اساس شیفت هر فرد + گریس + جدول مرخصی‌ها.
    leave_map: {(personnel_id, day): (kind, minutes)} — از جدول leaves (مرخصی روزانه)
    خروجی: تعداد روزهای بازمحاسبه‌شده
    """
    cur = db.conn.execute("SELECT jy, jm FROM attendance_months WHERE id=?", (month_id,))
    m = cur.fetchone()
    if not m:
        return 0
    jy, jm = m['jy'], m['jm']
    cur = db.conn.execute("""SELECT ad.*, p.shift_id
        FROM attendance_daily ad JOIN personnel p ON p.id=ad.personnel_id
        WHERE ad.month_id=?""", (month_id,))
    rows = cur.fetchall()
    people = {}
    for r in rows:
        people[r['personnel_id']] = {'id': r['personnel_id'], 'shift_id': r['shift_id']}
    schedules = {}
    for pid, p in people.items():
        schedules[pid] = person_shift(db, p, jy, jm)
    n = 0
    for r in rows:
        pid = r['personnel_id']
        d = r['day']
        sched = schedules[pid]
        wd = jdatetime.date(jy, jm, d).weekday()
        exp = expected_minutes(sched, wd)
        # مرخصی ثبت‌شده در جدول leaves (روزانه)
        kind = ''
        if leave_map and (pid, d) in leave_map:
            kind, lm = leave_map[(pid, d)]
            if lm > (r['leave_min'] or 0):
                r = dict(r)
                r['leave_min'] = lm
        # بازه شیفت این روز (اولین شیفت فعال)
        v = sched.get(str(wd), sched.get(wd))
        ss, se = (int(v[0]), int(v[1])) if v else (None, None)
        out = recompute_day(dict(r), exp, grace_late, grace_early,
                            cal_service.is_holiday(jy, jm, d), sched_start=ss, sched_end=se)
        if kind:
            out['status'] = 'مرخصی ' + kind if kind in ('استعلاجی', 'بدون حقوق') else 'مرخصی'
        db.conn.execute(
            """UPDATE attendance_daily SET late_min=?, early_min=?, missing_min=?, leave_min=?,
               status=?, expected_min=?, leave_kind=? WHERE id=?""",
            (out['late_min'], out['early_min'], out['missing_min'], out['leave_min'],
             out['status'], out['expected_min'], kind, r['id']))
        n += 1
    db.conn.commit()
    return n


def month_stats(db, month_id, cal_service):
    """
    آمار کارکرد ماهانه هر پرسنل برای حقوق:
    paid_days, leave_days(پرداختی), unpaid_days, overtime_hours, holiday_hours, friday_hours,
    late_minutes, early_minutes, present_days
    مرخصی روزانه پرداختی/بدون حقوق از جدول leaves + وضعیت روزها.
    """
    cur = db.conn.execute("SELECT jy, jm FROM attendance_months WHERE id=?", (month_id,))
    m = cur.fetchone()
    if not m:
        return {}
    jy, jm = m['jy'], m['jm']
    dim = J.days_in_month(jy, jm)
    cur = db.conn.execute(
        """SELECT personnel_id, day, status, worked_min, overtime_min, late_min, early_min,
                  missing_min, expected_min, leave_min, leave_kind
           FROM attendance_daily WHERE month_id=?""", (month_id,))
    people = {}
    for r in cur.fetchall():
        s = people.setdefault(r['personnel_id'], {
            'paid_days': 0, 'present_days': 0, 'ot_min': 0, 'holiday_min': 0, 'friday_min': 0,
            'leave_min': 0, 'unpaid_min': 0, 'late_min': 0, 'early_min': 0, 'missing_min': 0})
        st = (r['status'] or '')
        lv = r['leave_min'] or 0
        exp = r['expected_min'] or 0
        worked = r['worked_min'] or 0
        full_leave = exp > 0 and lv >= exp
        is_paid_leave = full_leave and ('بدون حقوق' not in st)
        is_unpaid = full_leave and 'بدون حقوق' in st
        if worked > 0:
            s['present_days'] += 1
            s['paid_days'] += 1
        elif is_paid_leave:
            s['paid_days'] += 1
        if is_unpaid:
            s['unpaid_min'] += lv
        elif not is_unpaid:
            s['leave_min'] += lv
        s['ot_min'] += r['overtime_min'] or 0
        s['late_min'] += r['late_min'] or 0
        s['early_min'] += r['early_min'] or 0
        s['missing_min'] += r['missing_min'] or 0
        d = r['day']
        if 1 <= d <= dim:
            wd = jdatetime.date(jy, jm, d).weekday()
            if wd == 6:
                s['friday_min'] += worked
            elif cal_service.is_holiday(jy, jm, d):
                s['holiday_min'] += worked
    out = {}
    for pid, s in people.items():
        leave_days = s['leave_min'] / 480.0
        unpaid_days = s['unpaid_min'] / 480.0
        out[pid] = {
            'paid_days': round(s['paid_days'] + leave_days, 2),
            'present_days': s['present_days'],
            'overtime_hours': s['ot_min'] / 60.0,
            'holiday_hours': s['holiday_min'] / 60.0,
            'friday_hours': s['friday_min'] / 60.0,
            'leave_days': round(leave_days, 2),
            'unpaid_days': round(unpaid_days, 2),
            'late_minutes': s['late_min'],
            'early_minutes': s['early_min'],
            'missing_minutes': s['missing_min'],
        }
    return out


def leaves_map_for_month(db, month_id, jy, jm):
    """مرخصی‌های روزانه ثبت‌شده در جدول leaves → {(pid, day): (kind, minutes)}"""
    dim = J.days_in_month(jy, jm)
    cur = db.conn.execute(
        """SELECT l.personnel_id, l.from_date, l.to_date, l.days, l.leave_kind
           FROM leaves l JOIN attendance_months am ON am.id=?
           WHERE l.leave_kind IN ('استحقاقی','استعلاجی','بدون حقوق')""", (month_id,))
    out = {}
    for r in cur.fetchall():
        try:
            from core.numbers import parse_jalali_date_str
            f = parse_jalali_date_str(r['from_date'])
            t = parse_jalali_date_str(r['to_date'])
        except Exception:
            continue
        if not f or not t:
            continue
        for (yy, mm, dd) in J.date_range_jalali(f[0], f[1], f[2], t[0], t[1], t[2]):
            if yy == jy and mm == jm and 1 <= dd <= dim:
                out[(r['personnel_id'], dd)] = (r['leave_kind'], 480)
    return out
