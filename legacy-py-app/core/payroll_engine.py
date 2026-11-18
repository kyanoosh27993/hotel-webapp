# -*- coding: utf-8 -*-
"""
موتور محاسبه حقوق و دستمزد — مطابق قانون کار، تامین اجتماعی و مالیات مستقیم
- هر آیتم فیش یک formula_key دارد که از رجیستری فرمول‌ها گرفته می‌شود
- کاربر می‌تواند فرمول هر آیتم را از بین فرمول‌های موجود عوض کند، آیتم اضافه/حذف کند
- نحوه مالیات هر آیتم: بدون مالیات / ماده ۸۴ (پله‌ای) / مقطوع (درصد ثابت) / درصد دلخواه
- بیمه: هر آیتم می‌تواند مشمول/غیرمشمول باشد (سقف مشمول بیمه اعمال می‌شود)
"""
import jdatetime
from .numbers import parse_number
from . import jalali


class FormulaRegistry:
    """رجیستری فرمول‌های قابل انتخاب برای هر آیتم حقوق"""
    _formulas = {}

    @classmethod
    def register(cls, key, title):
        def deco(fn):
            cls._formulas[key] = (title, fn)
            return fn
        return deco

    @classmethod
    def get(cls, key):
        return cls._formulas.get(key)

    @classmethod
    def available(cls):
        return [(k, t) for k, (t, _) in cls._formulas.items()]


def _hourly_rate(ctx):
    """نرخ ساعتی = مزد ماهانه مبنا ÷ ساعات موظفی ماه"""
    req_h = parse_number(ctx.settings.get('monthly_required_hours', '176'), 176)
    if req_h <= 0:
        req_h = 176
    return ctx.base_wage / req_h


def _prorate(ctx, amount):
    """نسبت به کارکرد ماه (برای اقلام روزشمار)"""
    if ctx.days_in_month <= 0:
        return amount
    return amount * ctx.paid_days / ctx.days_in_month


# ---------------- فرمول‌های اقلام درآمد ----------------
@FormulaRegistry.register('decree_job_wage', 'مزد شغل حکم × (کارکرد ÷ روزهای ماه)')
def f_base_wage(ctx, item, inputs):
    return round(_prorate(ctx, ctx.decree['job_wage']))


@FormulaRegistry.register('decree_job_wage_full', 'مزد شغل حکم (بدون تناسب)')
def f_base_wage_full(ctx, item, inputs):
    return round(ctx.decree['job_wage'])


@FormulaRegistry.register('contract_hourly', 'نرخ ساعتی قرارداد × ساعات کارکرد')
def f_contract_hourly(ctx, item, inputs):
    return round(ctx.contract['hourly_rate'] * ctx.paid_hours)


@FormulaRegistry.register('contract_daily', 'نرخ روزانه قرارداد × روزهای کارکرد')
def f_contract_daily(ctx, item, inputs):
    return round(ctx.contract['daily_rate'] * ctx.paid_days)


@FormulaRegistry.register('contract_peyman', 'مبلغ پیمان قرارداد')
def f_contract_peyman(ctx, item, inputs):
    return round(ctx.contract['project_amount'])


@FormulaRegistry.register('decree_field:job_wage', 'فیلد حکم: مزد شغل')
def _(ctx, item, inputs): return round(ctx.decree['job_wage'])


def _mk_decree_field(field):
    def fn(ctx, item, inputs):
        return round(_prorate(ctx, ctx.decree.get(field, 0)))
    return fn


@FormulaRegistry.register('decree_field:seniority_wage', 'فیلد حکم: مزد سنوات')
def _(ctx, item, inputs): return round(ctx.decree.get('seniority_wage', 0))

@FormulaRegistry.register('decree_field:housing', 'فیلد حکم: حق مسکن')
def _(ctx, item, inputs): return round(_prorate(ctx, ctx.decree.get('housing', 0)))

@FormulaRegistry.register('decree_field:food', 'فیلد حکم: خواروبار')
def _(ctx, item, inputs): return round(_prorate(ctx, ctx.decree.get('food', 0)))

@FormulaRegistry.register('decree_field:child_allowance', 'فیلد حکم: حق اولاد')
def _(ctx, item, inputs): return round(ctx.decree.get('child_allowance', 0))

@FormulaRegistry.register('decree_field:worker_ben', 'فیلد حکم: بن کارگری')
def _(ctx, item, inputs): return round(_prorate(ctx, ctx.decree.get('worker_ben', 0)))

@FormulaRegistry.register('decree_field:shift_allowance', 'فیلد حکم: حق شیفت')
def _(ctx, item, inputs): return round(ctx.decree.get('shift_allowance', 0))

@FormulaRegistry.register('decree_field:attraction_amount', 'فیلد حکم: مبلغ حق جذب')
def _(ctx, item, inputs): return round(ctx.decree.get('attraction_amount', 0))

@FormulaRegistry.register('decree_field:family_allowance', 'فیلد حکم: حق عائله‌مندی')
def _(ctx, item, inputs): return round(ctx.decree.get('family_allowance', 0))

@FormulaRegistry.register('decree_field:adjustment_diff', 'فیلد حکم: تفاوت تطبیق')
def _(ctx, item, inputs): return round(ctx.decree.get('adjustment_diff', 0))

@FormulaRegistry.register('decree_field:supervision', 'فیلد حکم: حق سرپرستی')
def _(ctx, item, inputs): return round(ctx.decree.get('supervision', 0))

@FormulaRegistry.register('decree_field:labor_market', 'فیلد حکم: بازار کار')
def _(ctx, item, inputs): return round(ctx.decree.get('labor_market', 0))

@FormulaRegistry.register('decree_field:education_aid', 'فیلد حکم: کمک‌هزینه تحصیلی')
def _(ctx, item, inputs): return round(ctx.decree.get('education_aid', 0))

@FormulaRegistry.register('decree_field:fixed_overtime', 'فیلد حکم: اضافه‌کار ثابت')
def _(ctx, item, inputs): return round(ctx.decree.get('fixed_overtime', 0))

@FormulaRegistry.register('decree_field:other_benefits', 'فیلد حکم: سایر مزایا')
def _(ctx, item, inputs): return round(ctx.decree.get('other_benefits', 0))


@FormulaRegistry.register('overtime_140', 'اضافه‌کاری = نرخ ساعتی × ۱.۴ × ساعات اضافه‌کار')
def f_ot(ctx, item, inputs):
    factor = parse_number(ctx.settings.get('overtime_factor', '1.4'), 1.4)
    return round(_hourly_rate(ctx) * factor * ctx.overtime_hours)


@FormulaRegistry.register('holiday_work_170', 'تعطیل‌کاری = نرخ ساعتی × ۱.۷ × ساعات تعطیل‌کاری')
def f_hol(ctx, item, inputs):
    factor = parse_number(ctx.settings.get('holiday_work_factor', '1.7'), 1.7)
    return round(_hourly_rate(ctx) * factor * ctx.holiday_hours)


@FormulaRegistry.register('friday_work_140', 'جمعه‌کاری = نرخ ساعتی × ۱.۴ × ساعات جمعه‌کاری')
def f_fri(ctx, item, inputs):
    factor = parse_number(ctx.settings.get('friday_work_factor', '1.4'), 1.4)
    return round(_hourly_rate(ctx) * factor * ctx.friday_hours)


@FormulaRegistry.register('night_work_35', 'شب‌کاری = نرخ ساعتی × ۳۵٪ × ساعات شب‌کاری')
def f_night(ctx, item, inputs):
    pct = parse_number(ctx.settings.get('night_work_percent', '35'), 35) / 100.0
    return round(_hourly_rate(ctx) * pct * ctx.night_hours)


@FormulaRegistry.register('manual', 'ثابت - مقدار دستی (از جدول ورود دستی)')
def f_manual(ctx, item, inputs):
    return round(parse_number(inputs.get('manual:' + item['code'], 0), 0))


# ---------------- فرمول‌های کسورات و سهم کارفرما ----------------
@FormulaRegistry.register('worker_insurance', 'بیمه سهم کارگر = نرخ٪ × مشمول بیمه')
def f_wins(ctx, item, inputs):
    rate = parse_number(ctx.settings.get('sso_worker_rate', '7'), 7) / 100.0
    return round(ctx.insured_base * rate)


@FormulaRegistry.register('employer_insurance', 'بیمه سهم کارفرما = نرخ٪ × مشمول بیمه')
def f_eins(ctx, item, inputs):
    rate = parse_number(ctx.settings.get('sso_employer_rate', '23'), 23) / 100.0
    return round(ctx.insured_base * rate)


@FormulaRegistry.register('unemployment_insurance', 'بیمه بیکاری = نرخ٪ × مشمول بیمه')
def f_uins(ctx, item, inputs):
    rate = parse_number(ctx.settings.get('sso_unemployment_rate', '3'), 3) / 100.0
    return round(ctx.insured_base * rate)


@FormulaRegistry.register('salary_tax', 'مالیات پله‌ای ماده ۸۴ (جدول سال مالی)')
def f_tax(ctx, item, inputs):
    return calc_progressive_tax(ctx.tax_base, ctx.tax_brackets)


@FormulaRegistry.register('loan_installment', 'قسط وام فعال پرسنل')
def f_loan(ctx, item, inputs):
    return round(sum(l['installment'] for l in ctx.loans if l.get('active')))


@FormulaRegistry.register('advance_amount', 'مساعده‌های بازپرداخت‌نشده')
def f_adv(ctx, item, inputs):
    return round(sum(a['amount'] for a in ctx.advances if not a.get('recovered')))


def calc_progressive_tax(amount, brackets):
    """محاسبه مالیات پله‌ای — brackets: dict یا tuple (seq, from, to, rate)"""
    if amount <= 0 or not brackets:
        return 0.0
    tax = 0.0
    for b in brackets:
        if isinstance(b, dict):
            lo = parse_number(b.get('from_amount', 0), 0)
            hi = parse_number(b.get('to_amount'), None) if b.get('to_amount') not in (None, '') else None
            rate = parse_number(b.get('rate_percent', 0), 0)
        else:
            _, lo, hi, rate = b[0], b[1], b[2], b[3]
            hi = None if hi in (None, '') else parse_number(hi, None)
            lo = parse_number(lo, 0)
            rate = parse_number(rate, 0)
        rate = rate / 100.0
        if hi is None:
            if amount > lo:
                tax += (amount - lo) * rate
        else:
            if amount > lo:
                tax += (min(amount, hi) - lo) * rate
    return round(max(tax, 0.0))


class EmployeeCalcContext:
    """زمینه محاسبه یک پرسنل در یک دوره"""
    def __init__(self, settings, tax_brackets, decree, contract, loans, advances, inputs,
                 days_in_month, paid_days, overtime_hours=0, holiday_hours=0,
                 friday_hours=0, night_hours=0, leave_days=0):
        self.settings = settings
        self.tax_brackets = tax_brackets
        self.decree = decree
        self.contract = contract
        self.loans = loans
        self.advances = advances
        self.inputs = inputs
        self.days_in_month = days_in_month
        self.paid_days = paid_days
        self.paid_hours = paid_days * 8
        self.overtime_hours = overtime_hours
        self.holiday_hours = holiday_hours
        self.friday_hours = friday_hours
        self.night_hours = night_hours
        self.leave_days = leave_days
        # مزد مبنا برای اضافه‌کاری: مزد شغل یا نرخ قرارداد
        if contract and contract.get('contract_type') == 'ساعتی' and contract.get('hourly_rate'):
            self.base_wage = contract['hourly_rate'] * parse_number(settings.get('monthly_required_hours', '176'), 176)
        elif contract and contract.get('contract_type') == 'روزانه' and contract.get('daily_rate'):
            self.base_wage = contract['daily_rate'] * days_in_month
        else:
            self.base_wage = decree.get('job_wage', 0) if decree else 0
        self.insured_base = 0.0
        self.tax_base = 0.0


def calc_employee(ctx, items_config):
    """محاسبه همه آیتم‌های فعال برای یک پرسنل → (lines, summary)"""
    lines = []
    earnings = 0.0
    deductions = 0.0
    employer_part = 0.0
    ceiling30 = parse_number(ctx.settings.get('sso_ceiling_30d', '1163788500'), 1163788500)
    ceiling31 = parse_number(ctx.settings.get('sso_ceiling_31d', '1202581450'), 1202581450)

    for item in items_config:
        if not item.get('active'):
            continue
        reg = FormulaRegistry.get(item['formula_key'])
        if not reg:
            continue
        try:
            amount = float(reg[1](ctx, item, ctx.inputs))
        except Exception:
            amount = 0.0
        if amount < 0:
            amount = 0.0
        lines.append({'item_code': item['code'], 'amount': amount})
        if item['kind'] == 'earning':
            earnings += amount
            if item.get('insured'):
                ctx.insured_base += amount
            # مالیات هر آیتم
            tm = item.get('tax_mode', 'none')
            if tm == 'm84':
                ctx.tax_base += amount
            elif tm == 'lump':
                pass  # در جمع نهایی مالیات به‌صورت مقطوع اضافه می‌شود
            elif tm == 'percent':
                pass
        elif item['kind'] == 'deduction':
            deductions += amount
        elif item['kind'] == 'employer':
            employer_part += amount

    # اعمال سقف مشمول بیمه (بر اساس روزهای ماه)
    ceiling = ceiling31 if ctx.days_in_month == 31 else ceiling30
    if ctx.days_in_month == 29:
        ceiling = ceiling30 * 29 / 30
    if ctx.insured_base > ceiling:
        ctx.insured_base = ceiling

    # مالیات: پله‌ای + اقلام مقطوع/درصدی
    lump_tax = 0.0
    for item in items_config:
        if not item.get('active') or item['kind'] != 'earning':
            continue
        tm = item.get('tax_mode', 'none')
        if tm == 'lump':
            pct = parse_number(ctx.settings.get('lump_tax_' + item['code'], '0'), 0)
            if pct <= 0 and item.get('tax_percent'):
                pct = parse_number(item['tax_percent'], 0)
            amt = next((l['amount'] for l in lines if l['item_code'] == item['code']), 0)
            lump_tax += amt * pct / 100.0
        elif tm == 'percent':
            pct = parse_number(item.get('tax_percent', 0), 0)
            amt = next((l['amount'] for l in lines if l['item_code'] == item['code']), 0)
            lump_tax += amt * pct / 100.0

    # کسر اقلام با بیمه از مشمول بیمه اگر برچسب دارند (پیش‌فرض همه با بیمه هستند)
    tax = calc_progressive_tax(ctx.tax_base, ctx.tax_brackets) + round(lump_tax)

    # بازمحاسبه کسورات وابسته به مشمول بیمه (بیمه بعد از سقف‌گذاری)
    worker_ins = round(ctx.insured_base * parse_number(ctx.settings.get('sso_worker_rate', '7'), 7) / 100.0)
    employer_ins = round(ctx.insured_base * parse_number(ctx.settings.get('sso_employer_rate', '23'), 23) / 100.0)
    unemployment = round(ctx.insured_base * parse_number(ctx.settings.get('sso_unemployment_rate', '3'), 3) / 100.0)
    for l in lines:
        if l['item_code'] == 'worker_ins':
            l['amount'] = worker_ins
        elif l['item_code'] == 'employer_ins':
            l['amount'] = employer_ins
        elif l['item_code'] == 'unemployment':
            l['amount'] = unemployment
        elif l['item_code'] == 'tax':
            l['amount'] = tax

    deductions = worker_ins + tax + sum(l['amount'] for l in lines
                                        if l['item_code'] in ('loan_install', 'advance', 'other_deduct'))

    summary = {
        'gross': round(earnings),
        'insured_base': round(ctx.insured_base),
        'worker_ins': worker_ins,
        'employer_ins': employer_ins,
        'unemployment_ins': unemployment,
        'tax_base': round(ctx.tax_base),
        'tax': tax,
        'total_deductions': round(deductions),
        'net_pay': round(earnings - deductions),
    }
    return lines, summary


def month_attendance_stats(db, month_id, cal_service):
    """آمار کارکرد هر پرسنل از جدول حضور (مبتنی بر شیفت و نوع مرخصی) →
    (paid_days, overtime_h, holiday_h, friday_h, leave_days, present_days, unpaid_days)"""
    try:
        from . import shifts as SH
        return SH.month_stats(db, month_id, cal_service)
    except Exception:
        pass
    # نسخه ساده بدون شیفت (پشتیبان)
    cur = db.conn.execute(
        """SELECT ad.personnel_id,
                  SUM(CASE WHEN ad.worked_min > 0 THEN 1 ELSE 0 END) as present_days,
                  SUM(ad.overtime_min) as ot_min
           FROM attendance_daily ad WHERE ad.month_id=? GROUP BY ad.personnel_id""",
        (month_id,))
    base = {r['personnel_id']: dict(r) for r in cur.fetchall()}
    # ساعات تعطیل‌کاری/جمعه‌کاری روزبه‌روز + روزهای مرخصی
    hol = {}
    cur = db.conn.execute(
        "SELECT am.jy, am.jm FROM attendance_months am WHERE am.id=?", (month_id,))
    mrow = cur.fetchone()
    if not mrow:
        return {}
    jy, jm = mrow['jy'], mrow['jm']
    dim = jalali.days_in_month(jy, jm)
    cur = db.conn.execute(
        "SELECT personnel_id, day, worked_min, leave_min FROM attendance_daily WHERE month_id=?", (month_id,))
    stats = {}
    for r in cur.fetchall():
        pid = r['personnel_id']
        s = stats.setdefault(pid, {'holiday_min': 0, 'friday_min': 0, 'leave_min': 0})
        d = r['day']
        if 1 <= d <= dim:
            wd = jdatetime.date(jy, jm, d).weekday()
            if wd == 6:  # جمعه
                s['friday_min'] += r['worked_min']
            elif cal_service.is_holiday(jy, jm, d):
                s['holiday_min'] += r['worked_min']
        s['leave_min'] += r['leave_min']
    out = {}
    for pid in set(list(base.keys()) + list(stats.keys())):
        b = base.get(pid, {'present_days': 0, 'ot_min': 0})
        s = stats.get(pid, {'holiday_min': 0, 'friday_min': 0, 'leave_min': 0})
        leave_days = s['leave_min'] / 480.0
        out[pid] = {
            'paid_days': (b['present_days'] or 0) + round(leave_days, 2),
            'overtime_hours': (b['ot_min'] or 0) / 60.0,
            'holiday_hours': s['holiday_min'] / 60.0,
            'friday_hours': s['friday_min'] / 60.0,
            'leave_days': round(leave_days, 2),
        }
    return out
