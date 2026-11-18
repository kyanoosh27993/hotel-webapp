# -*- coding: utf-8 -*-
"""
خروجی‌های استاندارد حقوق و دستمزد — نسخه ۰.۲:
- همه خروجی‌ها سربرگ رسمی دارند: لوگو + نام شرکت + شناسه ملی/کد اقتصادی + آدرس/تلفن + اطلاعات فرم و دوره
- ردیف‌های رنگی (زیبرا) برای خوانایی + shrink-to-fit (متن هر کادر داخل کادر می‌ماند)
- بهینه برای چاپ A4 (پرتره/لنداسکیپ، تکرار سرستون‌ها، حاشیه استاندارد، فیت شدن در عرض صفحه)
- فیش حقوقی طراحی حرفه‌ای سیاه‌وسفید-بهینه: لوگو، کادر اطلاعات، دو جدول، خلاصه، مانده حقوق ماه قبل، محل امضا
"""
import os
import jdatetime
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from core.numbers import format_money, to_persian_digits
from core import jalali as J

THIN = Border(*[Side(style='thin', color='94A3B8')] * 4)
# پس‌زمینه‌ها: سفید + خاکستری خیلی کمرنگ — متن همیشه مشکی (خوانایی کامل و چاپ تمیز)
HEADER_FILL = PatternFill('solid', fgColor='E8EAED')      # هدر: خاکستری خیلی کمرنگ
ZEBRA_FILL = PatternFill('solid', fgColor='F5F6F8')       # سطرهای زوج: تقریبا سفید
SUM_FILL = PatternFill('solid', fgColor='E8EAED')
TITLE_FONT = Font(name='Tahoma', size=12, bold=True, color='111827')
HDR_FONT = Font(name='Tahoma', size=9, bold=True, color='111827')   # متن هدر مشکی
CELL_FONT = Font(name='Tahoma', size=9, color='111827')
MONEY_FMT = '#,##0'
COMPANY_FONT = Font(name='Tahoma', size=10, bold=True, color='111827')


# ---------------------------------------------------------------- ابزار سربرگ
def company_header_lines(company, form_title, subtitle):
    """خطوط سربرگ رسمی مشترک همه خروجی‌ها"""
    c = company or {}
    lines = [c.get('name') or c.get('company_name') or '']
    extra = []
    if c.get('national_id'):
        extra.append('شناسه ملی: ' + str(c['national_id']))
    if c.get('economic_code'):
        extra.append('کد اقتصادی: ' + str(c['economic_code']))
    if c.get('sso_workshop_code'):
        extra.append('کد کارگاه بیمه: ' + str(c['sso_workshop_code']))
    if c.get('phone'):
        extra.append('تلفن: ' + str(c['phone']))
    if extra:
        lines.append('   |   '.join(extra))
    if c.get('address'):
        lines.append('نشانی: ' + str(c['address']))
    return lines


def _excel_logo(ws, company, row, col):
    """درج لوگو در اکسل (اگر موجود باشد) و برگرداندن ارتفاع ردیف‌های مصرفی"""
    lp = (company or {}).get('logo_path') or ''
    if lp and os.path.exists(lp):
        try:
            img = XLImage(lp)
            scale = min(1.0, 90.0 / max(img.width, 1))
            img.width = int(img.width * scale)
            img.height = int(img.height * scale)
            ws.add_image(img, f"{get_column_letter(col)}{row}")
            return max(1, int(img.height // 18))
        except Exception:
            pass
    return 0


# ---------------------------------------------------------------- اکسل استاندارد
def export_table_xlsx(path, title, subtitle, headers, rows, money_cols=(), sum_cols=(),
                      extra_note=None, company=None, landscape=False):
    """خروجی اکسل استاندارد با سربرگ شرکت/لوگو، ردیف‌های رنگی، shrink-to-fit و تنظیمات چاپ A4"""
    wb = Workbook()
    ws = wb.active
    ws.title = 'گزارش'
    ws.sheet_view.rightToLeft = True
    ncol = len(headers)
    r = 1
    logo_rows = _excel_logo(ws, company, r, ncol)
    head = company_header_lines(company, title, subtitle)
    start = r + (logo_rows if logo_rows else 0)
    rr = start
    for i, line in enumerate(head):
        if not line:
            continue
        cell = ws.cell(rr, 1, line)
        cell.font = COMPANY_FONT if i == 0 else Font(name='Tahoma', size=8, color='374151')
        cell.alignment = Alignment(horizontal='right', shrink_to_fit=True)
        ws.merge_cells(start_row=rr, start_column=1, end_row=rr, end_column=ncol)
        rr += 1
    ws.merge_cells(start_row=rr, start_column=1, end_row=rr, end_column=ncol)
    c = ws.cell(rr, 1, title)
    c.font = TITLE_FONT
    c.alignment = Alignment(horizontal='center', vertical='center')
    rr += 1
    ws.merge_cells(start_row=rr, start_column=1, end_row=rr, end_column=ncol)
    c = ws.cell(rr, 1, subtitle or '')
    c.font = Font(name='Tahoma', size=9, color='475569')
    c.alignment = Alignment(horizontal='center', shrink_to_fit=True)
    rr += 2
    r0 = rr
    for i, h in enumerate(headers, 1):
        cell = ws.cell(r0, i, h)
        cell.font = HDR_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = THIN
    for ri, row in enumerate(rows, r0 + 1):
        zebra = (ri - r0) % 2 == 0
        for ci, val in enumerate(row, 1):
            cell = ws.cell(ri, ci, val)
            cell.font = CELL_FONT
            cell.border = THIN
            cell.alignment = Alignment(horizontal='center', vertical='center',
                                       wrap_text=False, shrink_to_fit=True)
            if zebra:
                cell.fill = ZEBRA_FILL
            if ci - 1 in money_cols and isinstance(val, (int, float)):
                cell.number_format = MONEY_FMT
    if sum_cols:
        rsum = r0 + 1 + len(rows)
        ws.cell(rsum, 1, 'جمع کل').font = Font(name='Tahoma', size=9, bold=True)
        for ci in sum_cols:
            col = ci + 1
            letter = get_column_letter(col)
            cell = ws.cell(rsum, col, f"=SUM({letter}{r0+1}:{letter}{r0+len(rows)})")
            cell.font = Font(name='Tahoma', size=9, bold=True)
            cell.number_format = MONEY_FMT
            cell.fill = SUM_FILL
            cell.border = THIN
    # عرض ستون‌ها بر اساس طول محتوا (کپ‌شده)
    for i, h in enumerate(headers, 1):
        maxlen = len(str(h)) * 1.1
        for row in rows[:80]:
            if len(row) >= i:
                maxlen = max(maxlen, len(str(row[i - 1] or '')))
        ws.column_dimensions[get_column_letter(i)].width = max(10, min(30, maxlen * 1.25 + 4))
    if logo_rows:
        for lr in range(r, r + logo_rows):
            ws.row_dimensions[lr].height = 18
    ws.freeze_panes = ws.cell(r0 + 1, 1)
    if extra_note:
        ws.cell(r0 + len(rows) + 3, 1, extra_note).font = Font(name='Tahoma', size=8, color='64748B')
    # تنظیمات چاپ A4
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.orientation = 'landscape' if landscape else 'portrait'
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f'{r0}:{r0}'  # تکرار سرستون در هر صفحه چاپ
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.5
    wb.save(path)
    return path


# ---------------------------------------------------------------- فیش حقوقی PDF (طراحی حرفه‌ای سیاه‌وسفید)
def _period_title(jy, jm):
    return f"حقوق و دستمزد {J.MONTH_NAMES[jm-1]} ماه {to_persian_digits(jy)}"


def _logo_html(company):
    lp = (company or {}).get('logo_path') or ''
    if lp and os.path.exists(lp):
        return f"<img src='file:///{lp}' width='72' height='72'>"
    return ''


def payslip_html(company, person, period_title, items_rows, summary, report_bg='#ffffff'):
    """HTML فیش حقوقی — پس‌زمینه سفید، سطرها خاکستری خیلی کمرنگ، متن مشکی (چاپ تمیز B/W)"""
    earn = [r for r in items_rows if r[3] == 'earning' and r[1]]
    ded = [r for r in items_rows if r[3] == 'deduction' and r[1]]
    G, LG, HG = '#111827', '#f6f7f8', '#e8eaed'  # G=حاشیه/متن مشکی، LG=زبرا خیلی کمرنگ، HG=هدر/جمع

    def rows_html(rows, title):
        if not rows:
            return ''
        body = ''
        for i, r in enumerate(rows):
            z = f"background:{LG};" if i % 2 else ''
            body += (f"<tr style='{z}'>"
                     f"<td style='text-align:center'>{to_persian_digits(str(i+1))}</td>"
                     f"<td style='text-align:right'>{r[0]}</td>"
                     f"<td style='white-space:nowrap;text-align:left'>{format_money(r[1])}</td></tr>")
        total = format_money(sum(r[1] for r in rows))
        return (f"<p style='background:{HG};color:#111827;padding:4px 8px;margin:6px 0 3px 0;"
                f"font-weight:bold;font-size:9pt;border:1px solid {G}'>{title}</p>"
                f"<table width='100%' cellspacing='0' cellpadding='3' "
                f"style='border:1px solid {G};border-collapse:collapse;font-size:8.5pt'>"
                f"<tr style='background:{HG};font-weight:bold'>"
                f"<td style='width:10%;border:1px solid {G};text-align:center'>ردیف</td>"
                f"<td style='border:1px solid {G};text-align:center'>شرح</td>"
                f"<td style='width:38%;border:1px solid {G};text-align:center'>مبلغ (ریال)</td></tr>"
                f"{body}<tr style='background:{HG};font-weight:bold'>"
                f"<td colspan='2' style='border:1px solid {G}'>جمع {title}</td>"
                f"<td style='border:1px solid {G};white-space:nowrap;text-align:left'>{total}</td></tr></table>")

    def info_cell(label, value):
        return (f"<td style='background:{LG};border:1px solid {G};font-size:8pt;padding:2px 6px'>"
                f"<b>{label}</b></td>"
                f"<td style='border:1px solid {G};font-size:8.5pt;padding:2px 6px'>{value}</td>")

    prev = float(summary.get('prev_balance', 0) or 0)
    prev_row = ''
    if abs(prev) > 0.5:
        prev_row = info_cell('مانده حقوق ماه قبل', format_money(prev) + ' ریال')
    info = f"""
    <table width='100%' cellspacing='0' cellpadding='0' style='border-collapse:collapse'>
      <tr>{info_cell('نام و نام خانوادگی', person['full_name'])}
          {info_cell('شماره پرسنلی', to_persian_digits(str(person['personnel_code'])))}</tr>
      <tr>{info_cell('کد ملی', to_persian_digits(str(person['national_id'] or '')))}
          {info_cell('شماره بیمه', to_persian_digits(str(person['sso_number'] or '')))}</tr>
      <tr>{info_cell('شغل', person.get('job_title', '') or '—')}
          {info_cell('مرکز هزینه', person.get('cost_center', '') or '—')}</tr>
      <tr>{info_cell('کارکرد (روز)', to_persian_digits(f"{float(summary.get('worked_days',0)):g}"))}
          {info_cell('مرخصی (روز)', to_persian_digits(f"{float(summary.get('leave_days',0)):g}"))}</tr>
      <tr>{info_cell('مانده مرخصی', to_persian_digits(str(summary.get('leave_balance', 0) or 0)))}
          {prev_row if prev_row else info_cell('تاریخ صدور', to_persian_digits(
              jdatetime.date.today().strftime('%Y/%m/%d')))}</tr>
    </table>"""
    pay_total = float(summary['net_pay']) + prev
    summary_html = f"""
    <table width='100%' cellspacing='0' cellpadding='0' style='border-collapse:collapse;margin-top:8px;font-size:8.5pt'>
      <tr>{info_cell('جمع درآمد', format_money(summary['gross']))}
          {info_cell('مشمول بیمه', format_money(summary['insured_base']))}</tr>
      <tr>{info_cell('بیمه سهم کارگر', format_money(summary['worker_ins']))}
          {info_cell('مشمول مالیات', format_money(summary['tax_base']))}</tr>
      <tr>{info_cell('جمع کسورات', format_money(summary['total_deductions']))}
          {info_cell('مالیات حقوق', format_money(summary['tax']))}</tr>
      {'<tr>' + info_cell('مانده حقوق ماه قبل', format_money(prev)) if prev_row else ''}
      <tr style='background:{HG}'>
        <td style='border:1px solid {G};font-size:9pt;padding:4px 6px'><b>خالص قابل پرداخت</b></td>
        <td style='border:1px solid {G};font-size:9pt;padding:4px 6px'><b>{format_money(summary['net_pay'])}</b></td>
        <td style='border:1px solid {G};font-size:9pt;padding:4px 6px'><b>قابل پرداخت با مانده قبلی</b></td>
        <td style='border:1px solid {G};font-size:9pt;padding:4px 6px'><b>{format_money(pay_total)}</b> ریال</td></tr>
    </table>"""
    comp_lines = company_header_lines(company, '', '')
    addr = ''
    if len(comp_lines) > 2:
        addr = f"<p style='font-size:7.5pt;color:#374151;margin:1px;text-align:center'>{comp_lines[2]}</p>"
    ident = ''
    if len(comp_lines) > 1:
        ident = f"<p style='font-size:7.5pt;color:#374151;margin:1px;text-align:center'>{comp_lines[1]}</p>"
    return f"""
    <div dir='rtl' style='font-family:Vazirmatn,Tahoma; background:#ffffff; color:{G}; padding:10px'>
      <table width='100%' cellspacing='0'><tr>
        <td style='width:90px;text-align:left'>{_logo_html(company)}</td>
        <td style='text-align:center'>
          <p style='font-size:13pt;font-weight:bold;margin:2px'>{comp_lines[0]}</p>
          {ident}{addr}
          <p style='font-size:11pt;font-weight:bold;margin:6px 0 2px 0;border-top:2px solid {G};border-bottom:2px solid {G};padding:3px'>
            فیش حقوقی — {period_title}</p>
        </td>
        <td style='width:90px'></td></tr></table>
      {info}
      <table width='100%' cellspacing='6' cellpadding='0'><tr>
        <td width='50%' valign='top'>{rows_html(earn, 'مزایا و درآمدها')}</td>
        <td width='50%' valign='top'>{rows_html(ded, 'کسورات')}</td></tr></table>
      {summary_html}
      <table width='100%' cellspacing='0' style='margin-top:14px;font-size:8pt'>
        <tr><td style='text-align:center'>امضای کارمند</td>
            <td style='text-align:center'>تایید واحد منابع انسانی</td>
            <td style='text-align:center'>امضای مدیر مالی / کارفرما</td></tr>
        <tr><td style='height:34px;border-bottom:1px solid {G}'></td>
            <td style='border-bottom:1px solid {G}'></td>
            <td style='border-bottom:1px solid {G}'></td></tr>
      </table>
      <p style='font-size:7pt;color:#6b7280;margin-top:8px;text-align:center'>
        این فیش به‌صورت سیستمی صادر شده است — مبلغ‌ها به ریال</p>
    </div>"""


def payslip_pdf(path, company, person, period_title, items_rows, summary, report_bg='#ffffff',
                landscape=False):
    """صدور فیش حقوقی PDF با موتور Qt (پشتیبانی کامل RTL فارسی) — چندصفحه‌ای خودکار"""
    from PySide6.QtCore import QMarginsF, QTimer
    from PySide6.QtGui import QTextDocument, QFont, QPageLayout, QPageSize
    from PySide6.QtPrintSupport import QPrinter
    html = payslip_html(company, person, period_title, items_rows, summary, report_bg)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    printer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4),
                                      QPageLayout.Orientation.Landscape if landscape
                                      else QPageLayout.Orientation.Portrait,
                                      QMarginsF(10, 10, 10, 10),
                                      QPageLayout.Unit.Millimeter))
    doc = QTextDocument()
    doc.setDefaultFont(QFont('Vazirmatn', 9))
    doc.setHtml(html)
    doc.print_(printer)
    return path


# ---------------------------------------------------------------- گزارش عمومی PDF (هر جدول با سربرگ رسمی)
# پالت مشترک گزارش‌ها: سفید + خاکستری خیلی کمرنگ، متن مشکی
REPORT_BORDER = '#111827'   # خطوط جدول
REPORT_ZEBRA = '#f6f7f8'    # سطرهای متناوب — تقریبا سفید
REPORT_HEADER = '#e8eaed'   # ردیف هدر/جمع — خاکستری خیلی کمرنگ


def html_table(headers, rows, money_cols=(), with_totals=True):
    """HTML جدول گزارش — سطرها سفید/خاکستری خیلی کمرنگ، هدر کمرنگ با متن مشکی (برای PDF و خروجی HTML)"""
    G, LG, HG = REPORT_BORDER, REPORT_ZEBRA, REPORT_HEADER
    head_cells = ''.join(
        f"<td style='background:{HG};color:#111827;border:1px solid {G};padding:3px 4px;"
        f"font-weight:bold;text-align:center;font-size:8pt'>{h}</td>" for h in headers)
    body = ''
    for i, row in enumerate(rows):
        z = f"background:{LG};" if i % 2 else ''
        cells = ''.join(
            f"<td style='border:1px solid {G};padding:2px 4px;text-align:center;"
            f"white-space:nowrap;font-size:8pt;color:#111827'>"
            f"{format_money(v) if (ci - 1 in money_cols and isinstance(v, (int, float))) else v}</td>"
            for ci, v in enumerate(row, 1))
        body += f"<tr style='{z}'>{cells}</tr>"
    if with_totals and money_cols:
        tot_cells = []
        for ci in range(1, len(headers) + 1):
            if ci - 1 == 0:
                tot_cells.append(f"<td style='border:1px solid {G};background:{HG};color:#111827;"
                                 f"font-weight:bold;text-align:center'>جمع کل</td>")
            elif ci - 1 in money_cols:
                s = sum(float(r[ci - 1] or 0) for r in rows if ci - 1 < len(r)
                        and isinstance(r[ci - 1], (int, float)))
                tot_cells.append(f"<td style='border:1px solid {G};background:{HG};color:#111827;"
                                 f"font-weight:bold;white-space:nowrap;text-align:center'>{format_money(s)}</td>")
            else:
                tot_cells.append(f"<td style='border:1px solid {G};background:{HG}'></td>")
        body += '<tr>' + ''.join(tot_cells) + '</tr>'
    return f"<table width='100%' cellspacing='0' cellpadding='0' style='border-collapse:collapse'>" \
           f"<tr>{head_cells}</tr>{body}</table>"


def report_html(company, title, subtitle, headers, rows, money_cols=(), footer_note=None):
    """HTML کامل گزارش (برای پیش‌نمایش مرورگر / ذخیره فایل HTML) — همان طرح چاپی"""
    comp_lines = company_header_lines(company, title, subtitle)
    note = f"<p style='font-size:8pt;color:#6b7280;margin-top:6px'>{footer_note}</p>" if footer_note else ''
    logo = _logo_html(company)
    return f"""<!DOCTYPE html>
<html dir='rtl' lang='fa'><head><meta charset='utf-8'>
<title>{title}</title>
<style>
  body {{ font-family: Vazirmatn, Tahoma, sans-serif; background: #ffffff; color: #111827;
         margin: 24px auto; max-width: 1000px; }}
  @media print {{ body {{ margin: 8mm; }} }}
</style></head><body>
<table width='100%' cellspacing='0'><tr>
  <td style='width:90px;text-align:left'>{logo}</td>
  <td style='text-align:center'>
    <p style='font-size:14pt;font-weight:bold;margin:2px'>{comp_lines[0]}</p>
    <p style='font-size:8pt;color:#374151;margin:1px'>{comp_lines[1] if len(comp_lines) > 1 else ''}</p>
    <p style='font-size:11pt;font-weight:bold;margin:5px 0 2px 0'>{title}</p>
    <p style='font-size:9pt;color:#475569;margin:1px'>{subtitle or ''}</p>
  </td>
  <td style='width:90px'></td></tr></table>
{html_table(headers, rows, money_cols)}
{note}
<p style='font-size:7.5pt;color:#9ca3af;text-align:center;margin-top:6px'>
  تاریخ چاپ: {to_persian_digits(jdatetime.date.today().strftime('%Y/%m/%d'))}</p>
</body></html>"""


def report_pdf(path, company, title, subtitle, headers, rows, money_cols=(), landscape=False,
               footer_note=None):
    """چاپ PDF هر گزارش جدولی: سربرگ رسمی + لوگو + سطرهای سفید/کمرنگ + A4 فیت عرض"""
    from PySide6.QtCore import QMarginsF
    from PySide6.QtGui import QTextDocument, QFont, QPageLayout, QPageSize
    from PySide6.QtPrintSupport import QPrinter
    G = REPORT_BORDER
    body_table = html_table(headers, rows, money_cols)
    comp_lines = company_header_lines(company, title, subtitle)
    note = f"<p style='font-size:7.5pt;color:#6b7280;margin-top:6px'>{footer_note}</p>" if footer_note else ''
    html = f"""
    <div dir='rtl' style='font-family:Vazirmatn,Tahoma;color:{G};background:#ffffff;padding:8px'>
      <table width='100%' cellspacing='0'><tr>
        <td style='width:84px;text-align:left'>{_logo_html(company)}</td>
        <td style='text-align:center'>
          <p style='font-size:12pt;font-weight:bold;margin:2px'>{comp_lines[0]}</p>
          <p style='font-size:7.5pt;color:#374151;margin:1px'>{comp_lines[1] if len(comp_lines) > 1 else ''}</p>
          <p style='font-size:10.5pt;font-weight:bold;margin:5px 0 2px 0'>{title}</p>
          <p style='font-size:8.5pt;color:#475569;margin:1px'>{subtitle or ''}</p>
        </td>
        <td style='width:84px'></td></tr></table>
      <div style='margin-top:6px'>{body_table}</div>
      {note}
      <p style='font-size:7pt;color:#9ca3af;text-align:center;margin-top:4px'>
        تاریخ چاپ: {to_persian_digits(jdatetime.date.today().strftime('%Y/%m/%d'))}</p>
    </div>"""
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    printer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4),
                                      QPageLayout.Orientation.Landscape if landscape
                                      else QPageLayout.Orientation.Portrait,
                                      QMarginsF(8, 8, 8, 8), QPageLayout.Unit.Millimeter))
    doc = QTextDocument()
    doc.setDefaultFont(QFont('Vazirmatn', 9))
    doc.setHtml(html)
    doc.print_(printer)
    return path


# ---------------------------------------------------------------- داده‌های دوره و ردیف‌ها
def get_period_data(db, period_id):
    """داده کامل یک دوره: شرکت، سال، ماه، ردیف‌های پرسنل+خلاصه"""
    cur = db.conn.execute("""
        SELECT pp.jy, pp.jm, fy.id as fy_id, fy.company_id, c.*,
               c.name as company_name
        FROM payroll_periods pp
        JOIN fiscal_years fy ON fy.id=pp.fiscal_year_id
        JOIN companies c ON c.id=fy.company_id
        WHERE pp.id=?""", (period_id,))
    per = cur.fetchone()
    if not per:
        return None, []
    cur = db.conn.execute("""
        SELECT s.*, p.personnel_code, p.first_name, p.last_name,
               p.first_name || ' ' || p.last_name AS full_name,
               p.national_id,
               p.bank_name, p.bank_account, p.sso_number, p.job_title, p.cost_center,
               p.dependents, p.marital_status
        FROM payroll_summary s
        JOIN personnel p ON p.id=s.personnel_id
        WHERE s.period_id=? ORDER BY p.last_name, p.first_name""", (period_id,))
    rows = [dict(r) for r in cur.fetchall()]
    return dict(per), rows


def bank_list_rows(rows, only_approved=False):
    """لیست بانک: نام، کد ملی، شماره حساب، مانده ماه قبل، خالص، جمع قابل پرداخت"""
    out = []
    i = 0
    for r in rows:
        if only_approved and not r.get('pay_approved', 1):
            continue
        i += 1
        total = (r['net_pay'] or 0) + (r.get('prev_balance', 0) or 0)
        out.append([to_persian_digits(str(i)), f"{r['first_name']} {r['last_name']}",
                    to_persian_digits(str(r['national_id'] or '')),
                    to_persian_digits(str(r['bank_account'] or '')),
                    to_persian_digits(str(r['bank_name'] or '')),
                    r.get('prev_balance', 0) or 0, r['net_pay'], total,
                    'پرداخت شده' if r.get('pay_paid') else 'در انتظار پرداخت'])
    return out


def tax_list_rows(rows):
    """لیست مالیات حقوق (ماده ۹۷): نام، کد ملی، حقوق، مزایای مشمول، معاف، مشمول مالیات، مالیات"""
    out = []
    for i, r in enumerate(rows, 1):
        out.append([to_persian_digits(str(i)), f"{r['first_name']} {r['last_name']}",
                    to_persian_digits(str(r['national_id'] or '')),
                    r['gross'], r['tax_base'], r['tax']])
    return out


def insurance_list_rows(rows, days_worked=30):
    """لیست بیمه: شماره بیمه، نام، روز بیمه، مشمول بیمه، سهم کارگر، سهم کارفرما (۲۰٪)، بیکاری (۳٪)، جمع"""
    out = []
    for i, r in enumerate(rows, 1):
        total_ins = (r['worker_ins'] or 0) + (r['employer_ins'] or 0) + (r['unemployment_ins'] or 0)
        out.append([to_persian_digits(str(i)), to_persian_digits(str(r['sso_number'] or '')),
                    f"{r['first_name']} {r['last_name']}", to_persian_digits(str(days_worked)),
                    r['insured_base'], r['worker_ins'], r['employer_ins'],
                    r['unemployment_ins'], total_ins])
    return out
