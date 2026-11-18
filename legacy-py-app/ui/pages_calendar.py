# -*- coding: utf-8 -*-
"""صفحه تقویم شمسی (تا سال ۱۵۰۰):
- نمای ماهانه با تعطیلات رسمی و مناسبت‌ها
- افزودن/حذف دستی تعطیلات و مناسبت‌ها
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QTableWidget, QDialog, QFormLayout, QComboBox, QMessageBox,
                               QLineEdit, QInputDialog)
import jdatetime
from core.numbers import to_persian_digits
from core import jalali as J
from .widgets import setup_rtl_table, fill_table, MonthGrid


class CalendarPage(QWidget):
    def __init__(self, ctx, gate):
        super().__init__()
        self.ctx = ctx
        self.gate = gate
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        title = QLabel('📅 تقویم شمسی و تعطیلات')
        title.setObjectName('PageTitle')
        v.addWidget(title)
        bar = QHBoxLayout()
        self.year_combo = QComboBox()
        for y in range(1404, 1501):
            self.year_combo.addItem(to_persian_digits(str(y)), y)
        t = J.today_jalali()
        self.year_combo.setCurrentIndex(max(0, self.year_combo.findData(t.year)))
        self.year_combo.currentIndexChanged.connect(self.load_month)
        self.month_combo = QComboBox()
        for i, m in enumerate(J.MONTH_NAMES, 1):
            self.month_combo.addItem(m, i)
        self.month_combo.setCurrentIndex(t.month - 1)
        self.month_combo.currentIndexChanged.connect(self.load_month)
        b_add = QPushButton('➕ افزودن تعطیل/مناسبت')
        b_add.setObjectName('PrimaryBtn')
        b_add.clicked.connect(self.add_event)
        b_del = QPushButton('🗑 حذف مورد انتخابی')
        b_del.setObjectName('DangerBtn')
        b_del.clicked.connect(self.del_event)
        bar.addWidget(QLabel('سال:'))
        bar.addWidget(self.year_combo)
        bar.addWidget(QLabel('ماه:'))
        bar.addWidget(self.month_combo)
        bar.addWidget(b_add)
        bar.addWidget(b_del)
        bar.addStretch(1)
        v.addLayout(bar)
        mid = QHBoxLayout()
        self.grid = MonthGrid(self.ctx.cal)
        self.grid.dayClicked.connect(self._day_clicked)
        mid.addWidget(self.grid)
        self.info = QLabel('')
        self.info.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.info.setWordWrap(True)
        mid.addWidget(self.info, 1)
        v.addLayout(mid, 1)
        v.addWidget(QLabel('مناسبت‌های این ماه:'))
        self.table = QTableWidget()
        setup_rtl_table(self.table, ['روز', 'نوع', 'عنوان', 'منبع'])
        v.addWidget(self.table, 1)
        self.load_month()

    def load_month(self):
        y = self.year_combo.currentData() or J.today_jalali().year
        m = self.month_combo.currentData() or 1
        self.grid.set_date(y, m)
        events = self.ctx.cal.events_of_month(y, m)
        fill_table(self.table, [[to_persian_digits(str(r['jd'])),
                                 'تعطیل رسمی' if r['kind'] == 'holiday' else 'مناسبت',
                                 r['title'], r['source']] for r in events])

    def _day_clicked(self, y, m, d):
        evs = self.ctx.cal.events_of_day(y, m, d)
        wd = J.weekday_name(y, m, d)
        hol = self.ctx.cal.is_holiday(y, m, d)
        txt = f"<b>{J.MONTH_NAMES[m-1]} {to_persian_digits(str(d))} {to_persian_digits(str(y))}</b><br>"
        txt += f"روز هفته: {wd}<br>وضعیت: {'🔴 تعطیل' if hol else '🟢 کاری'}<br><br>"
        for kind, title in evs:
            txt += ('تعطیل رسمی: ' if kind == 'holiday' else 'مناسبت: ') + title + '<br>'
        if not evs:
            txt += 'مناسبتی ثبت نشده است.'
        self.info.setText(txt)

    def add_event(self):
        if not self.gate.allowed('edit'):
            return
        y = self.year_combo.currentData()
        m = self.month_combo.currentData()
        dlg = QDialog(self)
        dlg.setWindowTitle('افزودن تعطیل رسمی یا مناسبت')
        f = QFormLayout(dlg)
        day = QComboBox()
        for d in range(1, J.days_in_month(y, m) + 1):
            day.addItem(f"{to_persian_digits(str(d))} {J.MONTH_NAMES[m-1]} ({J.weekday_name(y, m, d)})", d)
        kind = QComboBox()
        kind.addItems(['تعطیل رسمی', 'مناسبت (غیرتعطیل)'])
        title = QLineEdit()
        f.addRow('روز', day)
        f.addRow('نوع', kind)
        f.addRow('عنوان *', title)
        from PySide6.QtWidgets import QDialogButtonBox
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec():
            if not title.text().strip():
                return
            self.ctx.cal.add_event(y, m, day.currentData(),
                                   'holiday' if kind.currentIndex() == 0 else 'occasion',
                                   title.text().strip())
            self.load_month()

    def del_event(self):
        if not self.gate.allowed('edit'):
            return
        r = self.table.currentRow()
        if r < 0:
            return
        events = self.ctx.cal.events_of_month(self.year_combo.currentData(), self.month_combo.currentData())
        ev = events[r]
        if QMessageBox.question(self, 'حذف', f"حذف «{ev['title']}»؟") == QMessageBox.StandardButton.Yes:
            self.ctx.cal.delete_event(ev['id'])
            self.load_month()
