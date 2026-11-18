# -*- coding: utf-8 -*-
"""
لایه نرمال‌سازی اعداد — قلب یکپارچگی داده‌ها
هر عددی که از هر منبعی وارد شود (ارقام فارسی، عربی، انگلیسی، با جداکننده هزارگان،
فرمت ساعت H:MM از دستگاه حضور و غیاب) به عدد انگلیسی استاندارد تبدیل و در دیتابیس ذخیره می‌شود.
"""
import re

# جدول تبدیل ارقام فارسی و عربی به انگلیسی
DIGIT_MAP = str.maketrans({
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5',
    '۶': '6', '۷': '7', '۸': '8', '۹': '9',
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5',
    '٦': '6', '٧': '7', '٨': '8', '٩': '9',
})

# جداکننده‌های هزارگان رایج (فارسی، عربی، انگلیسی، فاصله)
THOUSAND_SEPS = '،٬, \u200f\u200e'

_FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
_AR_DIGITS = '٠١٢٣٤٥٦٧٨٩'
_EN_DIGITS = '0123456789'


def normalize_digits(text) -> str:
    """تبدیل همه ارقام فارسی/عربی داخل متن به انگلیسی"""
    if text is None:
        return ''
    return str(text).translate(DIGIT_MAP)


def to_english_digits(text) -> str:
    return normalize_digits(text)


def to_persian_digits(text) -> str:
    """تبدیل ارقام انگلیسی به فارسی (برای نمایش)"""
    if text is None:
        return ''
    s = str(text)
    table = str.maketrans(_EN_DIGITS, _FA_DIGITS)
    return s.translate(table)


def parse_number(value, default=None) -> float:
    """
    پارس هر ورودی عددی به float انگلیسی:
    - ۱۲۳٬۴۵۶ / 123,456 / 123456 / 12 345 → 123456.0
    - جداکننده اعشار فارسی/انگلیسی هندل می‌شود
    - متن خالی یا نامعتبر → default
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = normalize_digits(value).strip()
    if not s:
        return default
    # حذف جداکننده هزارگان (، ٬ , و فاصله) — فقط وقتی بین ارقام است
    s = re.sub(r'(?<=\d)[،٬,\s](?=\d)', '', s)
    s = s.replace('٫', '.')  # اعشار فارسی
    s = s.replace('/', '.', 1) if re.fullmatch(r'\d+/\d+', s) else s
    # حذف هر کاراکتر غیر مجاز باقی‌مانده
    s = re.sub(r'[^0-9.\-+]', '', s)
    if s in ('', '.', '-', '+', '-.', '+.'):
        return default
    try:
        return float(s)
    except ValueError:
        return default


def parse_int(value, default=0) -> int:
    v = parse_number(value, None)
    if v is None:
        return default
    return int(round(v))


def parse_jalali_date_str(value):
    """
    پارس تاریخ شمسی از هر قالبی: ۱۴۰۵/۰۷/۰۱ یا 1405-7-1 یا ۱۴۰۵.۷.۱
    خروجی: (y, m, d) یا None
    """
    if value is None:
        return None
    s = normalize_digits(value).strip().replace('-', '/').replace('.', '/')
    m = re.search(r'(\d{3,4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})', s)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1000 <= y <= 1500 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return (y, mo, d)


def parse_hhmm(value, default=0) -> int:
    """
    پارس زمان دستگاه حضور و غیاب به «دقیقه»:
    - '216:02' → 216*60+2 ، '8:15' → 495 ، '08:16' → 496
    - فرمت اعشاری ساعت مثل 8.5 → 510 دقیقه
    - علامت * ابتدای برخی مقادیر دستگاه (خروج تکراری/فراموش‌شده) نادیده گرفته می‌شود
    - عدد صرف (دقیقه) هم پذیرفته می‌شود
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return int(round(value))
    s = normalize_digits(value).strip().lstrip('*').strip()
    if not s:
        return default
    m = re.fullmatch(r'(\d{1,6}):(\d{1,2})', s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    # فرمت اعشاری ساعت
    v = parse_number(s, None)
    if v is None:
        return default
    return int(round(v * 60))


def minutes_to_hhmm(minutes: int) -> str:
    """تبدیل دقیقه به فرمت استاندارد H:MM برای نمایش و گزارش‌ها"""
    if minutes is None:
        minutes = 0
    sign = '-' if minutes < 0 else ''
    minutes = abs(int(minutes))
    return f"{sign}{minutes // 60}:{minutes % 60:02d}"


def format_money(value, persian: bool = True, thousand_sep: str = ',') -> str:
    """قالب‌بندی مبلغ با جداکننده هزارگان (نمایش فارسی یا انگلیسی)"""
    if value is None:
        value = 0
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = 0.0
    neg = v < 0
    v = abs(v)
    if v == int(v):
        s = f"{int(v):,}".replace(',', thousand_sep)
    else:
        s = f"{v:,.2f}".replace(',', thousand_sep)
    if neg:
        s = '-' + s
    return to_persian_digits(s) if persian else s


def format_percent(value, persian: bool = True) -> str:
    """نمایش درصد مثل ۷٪"""
    if value is None:
        value = 0
    s = f"{parse_number(value, 0):g}"
    return to_persian_digits(s) + '٪' if persian else s + '%'


def clean_text(value) -> str:
    """پاکسازی متن: نیم‌فاصله‌ها، فاصله‌های اضافی، ارقام نگه داشته می‌شوند"""
    if value is None:
        return ''
    s = str(value).replace('\u200c', ' ')  # نیم‌فاصله → فاصله برای جستجو
    s = re.sub(r'\s+', ' ', s).strip()
    return s
