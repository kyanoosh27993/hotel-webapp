# -*- coding: utf-8 -*-
"""زمینه مشترک برنامه (Context) — دیتابیس، کاربر جاری، شرکت/سال مالی جاری، تم"""
from PySide6.QtCore import QObject, Signal


class AppContext(QObject):
    companyChanged = Signal()
    themeChanged = Signal()
    dataChanged = Signal()

    def __init__(self, db, auth, theme_mgr, cal_service):
        super().__init__()
        self.db = db
        self.auth = auth
        self.theme_mgr = theme_mgr
        self.cal = cal_service
        self.company_id = None
        self.company_name = ''
        self.fy_id = None
        self.fy_jy = None

    # ---------------- شرکت و سال مالی جاری ----------------
    def load_companies(self):
        cur = self.db.conn.execute("SELECT id,name FROM companies WHERE active=1 ORDER BY name")
        return [dict(r) for r in cur.fetchall()]

    def fiscal_years(self, company_id=None):
        cid = company_id or self.company_id
        if not cid:
            return []
        cur = self.db.conn.execute(
            "SELECT id,jy,title FROM fiscal_years WHERE company_id=? ORDER BY jy DESC", (cid,))
        return [dict(r) for r in cur.fetchall()]

    def set_company(self, company_id):
        self.company_id = company_id
        cur = self.db.conn.execute("SELECT name FROM companies WHERE id=?", (company_id,))
        row = cur.fetchone()
        self.company_name = row['name'] if row else ''
        fys = self.fiscal_years()
        self.fy_id = fys[0]['id'] if fys else None
        self.fy_jy = fys[0]['jy'] if fys else None
        self.companyChanged.emit()

    def set_fiscal_year(self, fy_id):
        for f in self.fiscal_years():
            if f['id'] == fy_id:
                self.fy_id = fy_id
                self.fy_jy = f['jy']
                self.companyChanged.emit()
                return

    def fy_setting(self, key, default=''):
        if not self.fy_id:
            return default
        return self.db.get_fy_setting(self.fy_id, key, default)

    def tax_brackets(self):
        if not self.fy_id:
            return []
        return self.db.get_tax_brackets(self.fy_id)
