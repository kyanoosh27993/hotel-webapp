# -*- coding: utf-8 -*-
"""
ویجت‌های پایه:
- MoneyEdit: ورود مبلغ با پذیرش خودکار ارقام فارسی/انگلیسی + جداکننده هزارگان زنده
- JalaliDatePicker: انتخاب آسان تاریخ شمسی از تقویم پاپ‌آپ (تا سال ۱۵۰۰، تعطیلات مشخص)
- TimeMinutesEdit: ورود زمان H:MM
- setup_rtl_table: جدول راست‌به‌چپ استاندارد
"""
from PySide6.QtCore import Qt, QDate, Signal, QObject
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QLineEdit, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                               QPushButton, QDialog, QGridLayout, QToolButton,
                               QComboBox, QTableWidget, QHeaderView, QFrame, QSizePolicy)
import jdatetime
from core.numbers import (normalize_digits, to_persian_digits, parse_number,
                          format_money, minutes_to_hhmm, parse_hhmm)
from core import jalali as J


# ---------------------------------------------------------------- مبلغ
class MoneyEdit(QLineEdit):
    """ورود مبلغ ریالی: عدد فارسی یا انگلیسی بپذیرد، ذخیره همیشه انگلیسی، نمایش فارسی"""
    valueChanged = Signal(float)

    def __init__(self, value=0, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.textEdited.connect(self._on_edit)
        self.set_value(value)

    def _on_edit(self, text):
        cursor = self.cursorPosition()
        seps_before = text.count('٬') + text.count(',')
        raw = text
        v = parse_number(raw, None)
        if v is None:
            v = 0
        s = f"{int(v):,}".replace(',', '٬') if v == int(v) else f"{v:,.3f}".replace(',', '٬')
        s = to_persian_digits(s)
        if s != text:
            seps_after = s.count('٬')
            self.blockSignals(True)
            self.setText(s)
            self.blockSignals(False)
            self.setCursorPosition(max(0, cursor + (seps_after - seps_before)))
        self.valueChanged.emit(self.value())

    def value(self) -> float:
        return parse_number(self.text(), 0.0) or 0.0

    def set_value(self, v):
        if v is None:
            v = 0
        s = f"{int(v):,}".replace(',', '٬') if float(v) == int(v) else f"{float(v):,.3f}".replace(',', '٬')
        self.setText(to_persian_digits(s))


class PercentEdit(QLineEdit):
    def __init__(self, value=0, parent=None):
        super().__init__(parent)
        self.set_value(value)

    def value(self):
        return parse_number(self.text(), 0.0) or 0.0

    def set_value(self, v):
        self.setText(to_persian_digits(f"{parse_number(v, 0):g}"))


class TimeMinutesEdit(QLineEdit):
    """ورود ساعت به فرمت H:MM؛ ذخیره به دقیقه"""
    def __init__(self, minutes=0, parent=None):
        super().__init__(parent)
        self.set_minutes(minutes)

    def minutes(self) -> int:
        return parse_hhmm(self.text(), 0)

    def set_minutes(self, m):
        self.setText(to_persian_digits(minutes_to_hhmm(m or 0)))


# ---------------------------------------------------------------- تقویم شمسی
class MonthGrid(QFrame):
    """گرید یک ماه با هایلایت تعطیلات"""
    dayClicked = Signal(int, int, int)  # y, m, d

    def __init__(self, cal_service=None, parent=None):
        super().__init__(parent)
        self.cal = cal_service
        self._jd = J.today_jalali()
        self._build()

    def set_date(self, y, m):
        self._jd = jdatetime.date(y, m, 1)
        self._build()

    def _build(self):
        old = self.layout()
        lay = None
        if old is not None:
            while old.count():
                it = old.takeAt(0)
                w = it.widget()
                if w:
                    w.deleteLater()
            lay = old
        else:
            lay = QGridLayout(self)
            lay.setSpacing(2)
        jd = self._jd
        y, m = jd.year, jd.month
        # سربرگ ماه
        title = QLabel(f"{J.MONTH_NAMES[m-1]} {to_persian_digits(y)}")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight:bold; font-size:12pt; padding:4px;")
        lay.addWidget(title, 0, 0, 1, 7)
        for i, wd in enumerate(['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج']):
            h = QLabel(wd)
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.setStyleSheet("color:#64748b; font-weight:bold;")
            lay.addWidget(h, 1, i)
        first_wd = jdatetime.date(y, m, 1).weekday()  # شنبه=0
        dim = J.days_in_month(y, m)
        row = 2
        col = first_wd
        for d in range(1, dim + 1):
            btn = QPushButton(to_persian_digits(d))
            btn.setFixedSize(38, 34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            is_hol = J.weekday_name(y, m, d) == 'جمعه'
            events = []
            if self.cal:
                is_hol = self.cal.is_holiday(y, m, d)
                events = self.cal.events_of_day(y, m, d)
            tip = '\n'.join(t for (_, t) in events) if events else ''
            if tip:
                btn.setToolTip(tip)
            if is_hol:
                btn.setStyleSheet("QPushButton{color:#dc2626; background:rgba(220,38,38,0.08);"
                                  "border-radius:6px; padding:2px;}"
                                  "QPushButton:hover{background:#dc2626; color:white;}")
            else:
                btn.setStyleSheet("QPushButton{border:none; border-radius:6px; padding:2px;}"
                                  "QPushButton:hover{background:rgba(37,99,235,0.15);}")
            btn.clicked.connect(lambda _, yy=y, mm=m, dd=d: self.dayClicked.emit(yy, mm, dd))
            lay.addWidget(btn, row, col)
            col += 1
            if col == 7:
                col = 0
                row += 1
        self.setLayout(lay)


class JalaliDatePicker(QWidget):
    """انتخابگر تاریخ شمسی: فیلد نمایش + دکمه تقویم پاپ‌آپ"""
    dateChanged = Signal(object)  # (y, m, d)

    def __init__(self, cal_service=None, parent=None):
        super().__init__(parent)
        self.cal_service = cal_service
        self._date = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.edit = QLineEdit()
        self.edit.setReadOnly(True)
        self.edit.setPlaceholderText("انتخاب تاریخ…")
        self.btn = QToolButton()
        self.btn.setText('📅')
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._popup)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.btn)
        self.set_today()

    def set_today(self):
        t = J.today_jalali()
        self.set_date((t.year, t.month, t.day))

    def set_date(self, d):
        self._date = d
        if d:
            self.edit.setText(to_persian_digits(J.format_jalali(*d)))
            self.dateChanged.emit(d)

    def date(self):
        return self._date

    def _popup(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('انتخاب تاریخ شمسی')
        dlg.setModal(True)
        v = QVBoxLayout(dlg)
        nav = QHBoxLayout()
        b_prev = QPushButton('◀ ماه قبل')
        b_next = QPushButton('ماه بعد ▶')
        ylbl = QLabel('')
        ylbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(b_prev)
        nav.addWidget(ylbl, 1)
        nav.addWidget(b_next)
        v.addLayout(nav)
        grid = MonthGrid(self.cal_service)
        v.addWidget(grid)
        cur = self._date or (J.today_jalali().year, J.today_jalali().month, J.today_jalali().day)
        grid.set_date(cur[0], cur[1])
        ylbl.setText(f"{to_persian_digits(cur[0])}")

        def shift(n):
            ny, nm = cur[0], cur[1] + n
            if nm > 12:
                nm, ny = 1, ny + 1
            if nm < 1:
                nm, ny = 12, ny - 1
            if 1000 <= ny <= 1500:
                grid.set_date(ny, nm)
                ylbl.setText(f"{to_persian_digits(ny)}")
        b_prev.clicked.connect(lambda: shift(-1))
        b_next.clicked.connect(lambda: shift(1))

        def pick(y, m, d):
            self.set_date((y, m, d))
            dlg.accept()
        grid.dayClicked.connect(pick)
        dlg.resize(300, 340)
        dlg.exec()


class JalaliMonthPicker(QComboBox):
    """انتخاب ماه شمسی برای یک سال"""
    def __init__(self, years=(1404, 1405, 1406), parent=None):
        super().__init__(parent)
        import jdatetime as jd
        ty = jd.date.today().year
        years = sorted(set(list(years) + [ty - 1, ty, ty + 1]))
        for y in years:
            for m in range(1, 13):
                self.addItem(f"{J.MONTH_NAMES[m-1]} {to_persian_digits(y)}", (y, m))

    def current_period(self):
        return self.currentData()


# ---------------------------------------------------------------- جدول
class FilterHeader(QHeaderView):
    """هدر با ردیف فیلتر داخل خودش — فیلتر هر ستون در هدر + منوی راست‌کلیک نمایش/مخفی ستون"""
    filtersChanged = Signal()

    def __init__(self, table: QTableWidget, headers):
        super().__init__(Qt.Orientation.Horizontal, table)
        self._table = table
        self._editors = []
        self._pad = 3
        self.setSectionsClickable(True)
        self.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.setStretchLastSection(True)
        self.setFixedHeight(56)
        self.setFilters(headers)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._col_menu)
        self.sectionResized.connect(lambda *_: self._position())
        self.sectionMoved.connect(lambda *_: self._position())

    def setFilters(self, headers):
        for e in self._editors:
            e.deleteLater()
        self._editors = []
        for i, h in enumerate(headers):
            ed = QLineEdit(self)
            ed.setPlaceholderText('همه')
            ed.setClearButtonEnabled(True)
            ed.setStyleSheet('QLineEdit{margin:1px; border-radius:4px; padding:1px 4px; font-size:7.5pt;}')
            ed.textChanged.connect(lambda *_: self.filtersChanged.emit())
            self.addWidgetToHeader(ed)
            self._editors.append(ed)
        self._position()

    def addWidgetToHeader(self, w):
        # قرار دادن ویجت داخل ویوپورت هدر
        w.setParent(self.viewport())

    def filter_text(self, col):
        return normalize_digits(self._editors[col].text()).strip() \
            if 0 <= col < len(self._editors) else ''

    def has_filters(self):
        return any(e.text().strip() for e in self._editors)

    def updateGeometries(self):
        super().updateGeometries()
        self._position()

    def _position(self):
        for i, ed in enumerate(self._editors):
            if self.isSectionHidden(i):
                ed.hide()
                continue
            x = self.sectionViewportPosition(i)
            w = self.sectionSize(i)
            ed.setGeometry(x + self._pad, self.height() // 2 + 1,
                           max(20, w - 2 * self._pad), self.height() // 2 - self._pad - 1)
            ed.show()

    def _col_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        idx = self.logicalIndexAt(pos)
        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        for i in range(len(self._editors)):
            t = self.model().headerData(i, Qt.Orientation.Horizontal) or f'ستون {i+1}'
            act = menu.addAction(t)
            act.setCheckable(True)
            act.setChecked(not self.isSectionHidden(i))
            act.toggled.connect(lambda chk, ii=i: self._toggle_col(ii, chk))
        menu.exec(self.mapToGlobal(pos))

    def _toggle_col(self, i, show):
        self.setSectionHidden(i, not show)
        self._position()
        self.filtersChanged.emit()


class SmartTable(QTableWidget):
    """جدول استاندارد با فیلتر هدر، مخفی/نمایش ستون و رنگ ردیف‌های متناوب"""
    def __init__(self, headers, stretch_all=True, parent=None):
        super().__init__(parent)
        self._headers = list(headers)
        setup_rtl_table(self, self._headers, stretch_all=False)
        self.filter_header = FilterHeader(self, self._headers)
        self.setHorizontalHeader(self.filter_header)
        self.filter_header.filtersChanged.connect(self.apply_filters)
        if stretch_all:
            self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._row_meta = []

    def apply_filters(self):
        """مخفی کردن ردیف‌هایی که با فیلتر هدر نمی‌خوانند"""
        hdr = self.filter_header
        if not hdr.has_filters():
            for r in range(self.rowCount()):
                self.setRowHidden(r, False)
            return
        texts = [hdr.filter_text(c) for c in range(len(self._headers))]
        for r in range(self.rowCount()):
            ok = True
            for c, q in enumerate(texts):
                if not q:
                    continue
                it = self.item(r, c)
                if it is None or q not in normalize_digits(it.text()).strip():
                    ok = False
                    break
            self.setRowHidden(r, not ok)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        self.filter_header._position()


def setup_rtl_table(table: QTableWidget, headers, stretch_all=True):
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.setWordWrap(False)
    hh = table.horizontalHeader()
    hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    if stretch_all:
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.verticalHeader().setDefaultSectionSize(30)
    return table


def make_table(headers, stretch_all=True):
    """ساخت SmartTable آماده با فیلتر هدر (برای جدول‌های گزارش)"""
    return SmartTable(headers, stretch_all=stretch_all)


def enable_enter_navigation(widget):
    """انتقال فوکوس با Enter در فرم‌ها — ورود اطلاعات فقط با کیبورد"""
    from PySide6.QtCore import QEvent

    class _Filter(QObject):
        def eventFilter(self, obj, ev):
            if ev.type() == QEvent.Type.KeyPress and ev.key() in (
                    Qt.Key.Key_Return, Qt.Key.Key_Enter):
                widget.focusNextChild()
                return True
            return False
    if not getattr(widget, '_enter_nav_installed', False):
        f = _Filter(widget)
        widget._enter_filter = f
        widget.installEventFilter(f)
        widget._enter_nav_installed = True
    for child in widget.findChildren(QLineEdit):
        child.installEventFilter(widget._enter_filter)
    for child in widget.findChildren(QComboBox):
        child.installEventFilter(widget._enter_filter)


def fill_table(table: QTableWidget, rows, formats=None, persian_numbers=True):
    """rows: list[list]؛ formats: dict col→'money'|'text'|'pct'"""
    formats = formats or {}
    table.setRowCount(0)
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            fmt = formats.get(c, 'text')
            if fmt == 'money':
                txt = format_money(val, persian=persian_numbers)
            elif fmt == 'pct':
                txt = to_persian_digits(f"{parse_number(val, 0):g}٪") if persian_numbers else f"{val:g}%"
            elif fmt == 'int':
                txt = to_persian_digits(str(val or 0)) if persian_numbers else str(val or 0)
            else:
                txt = '' if val is None else str(val)
            it = table.item(r, c) or _mk_item()
            it.setText(txt)
            table.setItem(r, c, it)
    return table


def _mk_item():
    from PySide6.QtWidgets import QTableWidgetItem
    it = QTableWidgetItem()
    return it
