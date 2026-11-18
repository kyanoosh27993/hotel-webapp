# -*- coding: utf-8 -*-
"""پنجره راهنمای F1 — نمایش دستورالعمل کامل هر بخش"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTextBrowser, QPushButton,
                               QHBoxLayout, QFileDialog, QMessageBox)
from core.help_texts import HELP


def show_help(parent, key, app_title='راهنما'):
    """باز کردن پنجره راهنمای بخش؛ اگر کلید نبود پیام می‌دهد"""
    text = HELP.get(key)
    if not text:
        text = '<p>برای این بخش راهنمایی ثبت نشده است.</p>'
    dlg = QDialog(parent)
    dlg.setWindowTitle(f"راهنما — {key}")
    dlg.resize(760, 620)
    dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    v = QVBoxLayout(dlg)
    tb = QTextBrowser()
    tb.setOpenExternalLinks(True)
    tb.setHtml(f"<div dir='rtl' style='font-family:Vazirmatn,Tahoma; font-size:10pt'>{text}</div>")
    v.addWidget(tb, 1)
    bar = QHBoxLayout()
    b_pdf = QPushButton('🖨 چاپ / ذخیره PDF راهنما')
    b_pdf.clicked.connect(lambda: _export_pdf(dlg, key, tb))
    b_close = QPushButton('بستن')
    b_close.setObjectName('PrimaryBtn')
    b_close.clicked.connect(dlg.accept)
    bar.addWidget(b_pdf)
    bar.addStretch(1)
    bar.addWidget(b_close)
    v.addLayout(bar)
    dlg.exec()


def _export_pdf(parent, key, browser):
    path, _ = QFileDialog.getSaveFileName(parent, 'ذخیره راهنما', f'راهنما - {key}.pdf', 'PDF (*.pdf)')
    if not path:
        return
    try:
        from PySide6.QtPrintSupport import QPrinter
        from PySide6.QtGui import QTextDocument, QPageLayout, QPageSize
        from PySide6.QtCore import QMarginsF
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4),
                                          QPageLayout.Orientation.Portrait,
                                          QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter))
        doc = QTextDocument()
        doc.setDefaultFont(QFont('Vazirmatn', 10))
        doc.setHtml(browser.toHtml())
        doc.print_(printer)
        QMessageBox.information(parent, 'ذخیره شد', path)
    except Exception as e:
        QMessageBox.critical(parent, 'خطا', str(e))


def install_f1(widget, key, replace_key=None):
    """کلید F1 را به ویجت (صفحه/دیالوگ) وصل می‌کند"""
    from PySide6.QtGui import QShortcut, QKeySequence
    sc = QShortcut(QKeySequence(Qt.Key.Key_F1), widget)
    sc.activated.connect(lambda: show_help(widget, key))
    return sc
