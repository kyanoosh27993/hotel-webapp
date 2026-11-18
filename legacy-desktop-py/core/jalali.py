# -*- coding: utf-8 -*-
"""
موتور تقویم هجری شمسی تا سال ۱۵۰۰ — مبتنی بر jdatetime (دقیق بر اساس گاه‌شماری جلالی)
+ مدیریت تعطیلات رسمی و مناسبت‌ها (ذخیره در دیتابیس، قابل افزودن/حذف دستی)
"""
import jdatetime
from .numbers import to_persian_digits, normalize_digits

MONTH_NAMES = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
               'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']

WEEKDAY_NAMES = {0: 'شنبه', 1: 'یکشنبه', 2: 'دوشنبه', 3: 'سه‌شنبه',
                 4: 'چهارشنبه', 5: 'پنجشنبه', 6: 'جمعه'}


def today_jalali():
    return jdatetime.date.today()


def days_in_month(jy: int, jm: int) -> int:
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    # اسفند: کبیسه ۳۰ روز
    return 30 if jdatetime.date(jy, 1, 1).isleap() else 29


def is_leap(jy: int) -> bool:
    return jdatetime.date(jy, 1, 1).isleap()


def year_days(jy: int) -> int:
    return 366 if is_leap(jy) else 365


def weekday_name(jy, jm, jd) -> str:
    d = jdatetime.date(jy, jm, jd)
    # jdatetime: شنبه=0 ... جمعه=6
    return WEEKDAY_NAMES[d.weekday()]


def to_gregorian(jy, jm, jd):
    return jdatetime.date(jy, jm, jd).togregorian()


def from_gregorian(gy, gm, gd):
    return jdatetime.date.fromgregorian(date=__import__('datetime').date(gy, gm, gd))


def format_jalali(jy, jm, jd, persian=True) -> str:
    s = f"{jy:04d}/{jm:02d}/{jd:02d}"
    return to_persian_digits(s) if persian else s


def month_days_list(jy, jm):
    """فهرست روزهای ماه به صورت (y, m, d, weekday_name)"""
    out = []
    for d in range(1, days_in_month(jy, jm) + 1):
        out.append((jy, jm, d, weekday_name(jy, jm, d)))
    return out


def date_range_jalali(y1, m1, d1, y2, m2, d2):
    """تولید فهرست تاریخ‌های شمسی بین دو تاریخ (شامل دو سر)"""
    start = jdatetime.date(y1, m1, d1)
    end = jdatetime.date(y2, m2, d2)
    out = []
    cur = start
    one = jdatetime.timedelta(days=1)
    while cur <= end:
        out.append((cur.year, cur.month, cur.day))
        cur += one
    return out


# ---------------------------------------------------------------------------
# تعطیلات رسمی و مناسبت‌های پیش‌فرض (منابع: تقویم رسمی ۱۴۰۴ و ۱۴۰۵)
# kind: 'holiday' = تعطیل رسمی ، 'occasion' = مناسبت (غیر تعطیل)
# ---------------------------------------------------------------------------
DEFAULT_CALENDAR_EVENTS = [
    # ---------------- ۱۴۰۴ ----------------
    (1404, 1, 1, 'holiday', 'عید نوروز'),
    (1404, 1, 2, 'holiday', 'عید نوروز / شهادت حضرت علی (ع)'),
    (1404, 1, 3, 'holiday', 'عید نوروز'),
    (1404, 1, 4, 'holiday', 'عید نوروز'),
    (1404, 1, 11, 'holiday', 'عید سعید فطر'),
    (1404, 1, 12, 'holiday', 'عید سعید فطر / روز جمهوری اسلامی'),
    (1404, 1, 13, 'holiday', 'روز طبیعت (سیزده‌بدر)'),
    (1404, 2, 4, 'holiday', 'شهادت امام جعفر صادق (ع)'),
    (1404, 2, 11, 'holiday', 'روز جهانی کارگر'),
    (1404, 3, 14, 'holiday', 'رحلت امام خمینی (ره)'),
    (1404, 3, 15, 'holiday', 'قیام ۱۵ خرداد'),
    (1404, 3, 16, 'holiday', 'عید سعید قربان'),
    (1404, 3, 24, 'holiday', 'عید سعید غدیر خم'),
    (1404, 4, 14, 'holiday', 'تاسوعای حسینی'),
    (1404, 4, 15, 'holiday', 'عاشورای حسینی'),
    (1404, 5, 23, 'holiday', 'اربعین حسینی'),
    (1404, 5, 31, 'holiday', 'رحلت رسول اکرم (ص) / شهادت امام حسن مجتبی (ع)'),
    (1404, 6, 2, 'holiday', 'شهادت امام رضا (ع)'),
    (1404, 6, 10, 'holiday', 'شهادت امام حسن عسکری (ع)'),
    (1404, 6, 19, 'holiday', 'میلاد رسول اکرم (ص) و امام صادق (ع)'),
    (1404, 9, 3, 'holiday', 'شهادت حضرت فاطمه زهرا (س)'),
    (1404, 10, 13, 'holiday', 'ولادت امام علی (ع) / روز پدر'),
    (1404, 10, 27, 'holiday', 'مبعث رسول اکرم (ص)'),
    (1404, 11, 15, 'holiday', 'ولادت حضرت قائم (ع) / نیمه شعبان'),
    (1404, 11, 22, 'holiday', 'پیروزی انقلاب اسلامی'),
    (1404, 12, 20, 'holiday', 'شهادت حضرت علی (ع)'),
    (1404, 12, 29, 'holiday', 'روز ملی شدن صنعت نفت'),
    # مناسبت‌های ۱۴۰۴
    (1404, 2, 1, 'occasion', 'روز بزرگداشت سعدی'),
    (1404, 2, 10, 'occasion', 'روز ملی خلیج فارس'),
    (1404, 2, 12, 'occasion', 'روز معلم'),
    (1404, 2, 25, 'occasion', 'روز بزرگداشت فردوسی'),
    (1404, 3, 1, 'occasion', 'روز بهره‌وری'),
    (1404, 7, 13, 'occasion', 'روز نیروی انتظامی'),
    (1404, 7, 24, 'occasion', 'روز پیوند اولیا و مربیان'),
    (1404, 8, 13, 'occasion', 'روز دانش‌آموز'),
    (1404, 8, 24, 'occasion', 'روز کتاب و کتابخوانی'),
    (1404, 11, 19, 'occasion', 'روز نیروی هوایی'),
    # ---------------- ۱۴۰۵ ----------------
    (1405, 1, 1, 'holiday', 'عید نوروز'),
    (1405, 1, 2, 'holiday', 'عید نوروز'),
    (1405, 1, 3, 'holiday', 'عید نوروز'),
    (1405, 1, 4, 'holiday', 'عید نوروز'),
    (1405, 1, 12, 'holiday', 'روز جمهوری اسلامی'),
    (1405, 1, 13, 'holiday', 'روز طبیعت (سیزده‌بدر)'),
    (1405, 1, 28, 'holiday', 'عید سعید فطر'),
    (1405, 1, 29, 'holiday', 'عید سعید فطر (دوم)'),
    (1405, 2, 11, 'holiday', 'روز جهانی کارگر'),
    (1405, 3, 14, 'holiday', 'رحلت امام خمینی (ره)'),
    (1405, 3, 15, 'holiday', 'قیام ۱۵ خرداد'),
    (1405, 3, 17, 'holiday', 'عید سعید قربان'),
    (1405, 3, 25, 'holiday', 'عید سعید غدیر خم'),
    (1405, 5, 7, 'holiday', 'تاسوعای حسینی'),
    (1405, 5, 8, 'holiday', 'عاشورای حسینی'),
    (1405, 6, 30, 'holiday', 'اربعین حسینی'),
    (1405, 7, 13, 'holiday', 'رحلت رسول اکرم (ص)'),
    (1405, 7, 14, 'holiday', 'شهادت امام حسن مجتبی (ع)'),
    (1405, 7, 15, 'holiday', 'شهادت امام رضا (ع)'),
    (1405, 8, 13, 'holiday', 'روز دانش‌آموز / تسخیر لانه جاسوسی'),
    (1405, 8, 14, 'holiday', 'میلاد رسول اکرم (ص) و امام صادق (ع)'),
    (1405, 10, 27, 'holiday', 'ولادت حضرت فاطمه زهرا (س) / روز زن'),
    (1405, 11, 22, 'holiday', 'پیروزی انقلاب اسلامی'),
    (1405, 12, 29, 'holiday', 'روز ملی شدن صنعت نفت'),
    # مناسبت‌های ۱۴۰۵
    (1405, 2, 12, 'occasion', 'روز معلم'),
    (1405, 2, 10, 'occasion', 'روز ملی خلیج فارس'),
    (1405, 2, 25, 'occasion', 'روز بزرگداشت فردوسی'),
    (1405, 7, 13, 'occasion', 'روز نیروی انتظامی'),
    (1405, 8, 24, 'occasion', 'روز کتاب و کتابخوانی'),
    (1405, 12, 5, 'occasion', 'روز مهندسی'),
]


# ---------------------------------------------------------------------------
# تعطیلات سال‌های ۱۴۰۶ تا ۱۵۰۰
# ثابت شمسی (دقیق) + قمری (محاسباتی، تقریبی ±۱ روز — بعد از اعلام تقویم رسمی قابل اصلاح دستی است)
# ---------------------------------------------------------------------------
FIXED_SOLAR_HOLIDAYS = [
    (1, 1, 'عید نوروز'), (1, 2, 'عید نوروز'), (1, 3, 'عید نوروز'), (1, 4, 'عید نوروز'),
    (1, 12, 'روز جمهوری اسلامی'), (1, 13, 'روز طبیعت (سیزده‌بدر)'),
    (2, 11, 'روز جهانی کارگر'),
    (3, 14, 'رحلت امام خمینی (ره)'), (3, 15, 'قیام ۱۵ خرداد'),
    (11, 22, 'پیروزی انقلاب اسلامی'),
    (12, 29, 'روز ملی شدن صنعت نفت'),
]

# تعطیلات قمری رسمی ایران: (ماه هجری، روز، عنوان)
LUNAR_HOLIDAYS = [
    (1, 9, 'تاسوعای حسینی'),
    (1, 10, 'عاشورای حسینی'),
    (2, 20, 'اربعین حسینی'),
    (2, 28, 'رحلت رسول اکرم (ص) / شهادت امام حسن مجتبی (ع)'),
    (2, 30, 'شهادت امام رضا (ع)'),
    (3, 8, 'شهادت امام حسن عسکری (ع)'),
    (3, 17, 'میلاد رسول اکرم (ص) و امام جعفر صادق (ع)'),
    (5, 3, 'شهادت حضرت فاطمه زهرا (س)'),
    (6, 20, 'ولادت حضرت فاطمه زهرا (س) / روز زن'),
    (7, 13, 'ولادت امام علی (ع) / روز پدر'),
    (7, 27, 'مبعث رسول اکرم (ص)'),
    (9, 21, 'شهادت حضرت علی (ع)'),
    (10, 1, 'عید سعید فطر'),
    (10, 2, 'عید سعید فطر (دوم)'),
    (12, 10, 'عید سعید قربان'),
    (12, 18, 'عید سعید غدیر خم'),
]

# تصحیح اختلاف تبدیل تقریبی هجری با تقویم رسمی ایران (کالیبره‌شده روی ۱۴۰۴-۱۴۰۵)
LUNAR_DELTA = 0


def hijri_to_jd(hy, hm, hd):
    """تبدیل تاریخ هجری قمری (تقویم محاسباتی civil) به Julian Day — الگوریتم استاندارد"""
    return (int((11 * hy + 3) / 30) + 354 * hy + 30 * hm - int((hm - 1) / 2)
            + hd + 1948440 - 385)


def jd_to_gregorian(jd):
    a = jd + 32044
    b = int((4 * a + 3) / 146097)
    c = a - int(146097 * b / 4)
    d = int((4 * c + 3) / 1461)
    e = c - int(1461 * d / 4)
    m = int((5 * e + 2) / 153)
    day = e - int((153 * m + 2) / 5) + 1
    month = m + 3 - 12 * int(m / 10)
    year = 100 * b + d - 4800 + int(m / 10)
    return year, month, day


def hijri_to_jalali(hy, hm, hd, delta=0):
    """هجری قمری → شمسی (تقریبی)؛ delta: تعداد روز تصحیح"""
    try:
        jd = hijri_to_jd(hy, hm, hd) + delta
        gy, gm, gd = jd_to_gregorian(jd)
        j = from_gregorian(gy, gm, gd)
        return (j.year, j.month, j.day)
    except Exception:
        return None


class CalendarService:
    """سرویس تقویم: خواندن/نوشتن تعطیلات از دیتابیس + پرس‌وجوی تعطیل بودن روز
    تعطیلات تا سال ۱۵۰۰: ثابت‌های شمسی دقیق + تعطیلات قمری محاسباتی (تقریبی، قابل اصلاح دستی)"""

    def __init__(self, db):
        self.db = db
        self._ensured_years = set()

    def seed_defaults(self):
        """درج مناسبت‌های پیش‌فرض فقط اگر جدول خالی باشد"""
        cur = self.db.conn.execute("SELECT COUNT(*) FROM calendar_events")
        if cur.fetchone()[0] > 0:
            return
        rows = [(y, m, d, k, t, 'پیش‌فرض تقویم رسمی') for (y, m, d, k, t) in DEFAULT_CALENDAR_EVENTS]
        self.db.conn.executemany(
            "INSERT INTO calendar_events(jy,jm,jd,kind,title,source) VALUES(?,?,?,?,?,?)", rows)
        self.db.conn.commit()

    def ensure_year(self, jy):
        """تولید تعطیلات سال‌های خارج از ۱۴۰۴/۱۴۰۵ (قمری تقریبی + ثابت شمسی) — یک بار برای هر سال"""
        if jy in (1404, 1405) or jy in self._ensured_years:
            return
        cur = self.db.conn.execute(
            "SELECT COUNT(*) FROM calendar_events WHERE jy=? AND source='پیش‌فرض تقویم رسمی'", (jy,))
        if cur.fetchone()[0] > 0:
            self._ensured_years.add(jy)
            return
        rows = []
        for (jm, jd, title) in FIXED_SOLAR_HOLIDAYS:
            rows.append((jy, jm, jd, 'holiday', title, 'پیش‌فرض تقویم رسمی'))
        for (hm, hd, title) in LUNAR_HOLIDAYS:
            # جستجوی سال هجری متناظر (به‌دلیل رانش تقویم قمری، آفست ثابت نیست)
            for hy in range(jy + 40, jy + 49):
                j = hijri_to_jalali(hy, hm, hd, delta=LUNAR_DELTA)
                if j and j[0] == jy:
                    rows.append((jy, j[1], j[2], 'holiday', title,
                                 'محاسباتی (تقریبی — با تقویم رسمی اصلاح کنید)'))
                    break
        if rows:
            self.db.conn.executemany(
                "INSERT INTO calendar_events(jy,jm,jd,kind,title,source) VALUES(?,?,?,?,?,?)", rows)
            self.db.conn.commit()
        self._ensured_years.add(jy)

    def is_holiday(self, jy, jm, jd) -> bool:
        self.ensure_year(jy)
        cur = self.db.conn.execute(
            "SELECT 1 FROM calendar_events WHERE jy=? AND jm=? AND jd=? AND kind='holiday'",
            (jy, jm, jd))
        if cur.fetchone():
            return True
        # جمعه‌ها همیشه تعطیل
        return jdatetime.date(jy, jm, jd).weekday() == 6

    def events_of_day(self, jy, jm, jd):
        cur = self.db.conn.execute(
            "SELECT kind,title FROM calendar_events WHERE jy=? AND jm=? AND jd=?",
            (jy, jm, jd))
        return cur.fetchall()

    def events_of_month(self, jy, jm):
        cur = self.db.conn.execute(
            "SELECT jd,kind,title,source FROM calendar_events WHERE jy=? AND jm=? ORDER BY jd",
            (jy, jm))
        return cur.fetchall()

    def add_event(self, jy, jm, jd, kind, title, source='دستی'):
        self.db.conn.execute(
            "INSERT INTO calendar_events(jy,jm,jd,kind,title,source) VALUES(?,?,?,?,?,?)",
            (jy, jm, jd, kind, title, source))
        self.db.conn.commit()

    def delete_event(self, event_id):
        self.db.conn.execute("DELETE FROM calendar_events WHERE id=?", (event_id,))
        self.db.conn.commit()

    def month_title(self, jy, jm) -> str:
        return f"{MONTH_NAMES[jm-1]} {to_persian_digits(jy)}"
