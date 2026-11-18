# -*- coding: utf-8 -*-
"""
امنیت برنامه:
- هش پسورد با PBKDF2-HMAC-SHA256 (۲۰۰٬۰۰۰ تکرار) + Salt یکتا برای هر کاربر
- نقش‌ها: مدیر کل (admin) / اپراتور (operator) / فقط مشاهده (viewer)
- لاگ کامل عملیات در audit_log
- قفل شدن حساب بعد از ۵ ورود ناموفق به مدت ۵ دقیقه
"""
import hashlib
import secrets
import time
from .numbers import normalize_digits

PBKDF2_ITERATIONS = 200_000
LOCKOUT_ATTEMPTS = 5
LOCKOUT_SECONDS = 300


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS).hex()


class AuthService:
    def __init__(self, db):
        self.db = db
        # شمارش ورود ناموفق در حافظه
        self._failed = {}
        self.current_user = None  # dict

    def ensure_admin_exists(self):
        """ایجاد مدیر کل پیش‌فرض در اولین اجرا: کاربر admin با رمز admin123"""
        cur = self.db.conn.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            self.create_user('admin', 'admin123', 'مدیر کل', 'admin')

    def create_user(self, username, password, full_name='', role='operator'):
        salt = secrets.token_bytes(16)
        pw_hash = _hash_password(password, salt)
        self.db.conn.execute(
            "INSERT INTO users(username,password_hash,salt,full_name,role) VALUES(?,?,?,?,?)",
            (normalize_digits(username).strip(), pw_hash, salt.hex(), full_name, role))
        self.db.conn.commit()

    def change_password(self, user_id, new_password):
        salt = secrets.token_bytes(16)
        pw_hash = _hash_password(new_password, salt)
        self.db.conn.execute(
            "UPDATE users SET password_hash=?, salt=? WHERE id=?", (pw_hash, salt.hex(), user_id))
        self.db.conn.commit()

    def set_role(self, user_id, role):
        self.db.conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        self.db.conn.commit()

    def set_active(self, user_id, active):
        self.db.conn.execute("UPDATE users SET active=? WHERE id=?", (active, user_id))
        self.db.conn.commit()

    def list_users(self):
        cur = self.db.conn.execute("SELECT id,username,full_name,role,active,created_at FROM users ORDER BY id")
        return [dict(r) for r in cur.fetchall()]

    def login(self, username, password):
        """ورود موفق → dict کاربر و None در غیر این صورت"""
        uname = normalize_digits(username).strip()
        now = time.time()
        st = self._failed.get(uname, {'n': 0, 't': 0})
        if st['n'] >= LOCKOUT_ATTEMPTS and now - st['t'] < LOCKOUT_SECONDS:
            remaining = int(LOCKOUT_SECONDS - (now - st['t']))
            return {'error': f'حساب موقتاً قفل است. {remaining} ثانیه دیگر تلاش کنید.'}
        cur = self.db.conn.execute(
            "SELECT id,username,password_hash,salt,full_name,role,active FROM users WHERE username=?", (uname,))
        row = cur.fetchone()
        ok = False
        if row and row['active']:
            try:
                salt = bytes.fromhex(row['salt'])
                ok = secrets.compare_digest(row['password_hash'], _hash_password(password, salt))
            except ValueError:
                ok = False
        if not ok:
            self._failed[uname] = {'n': st['n'] + 1 if now - st['t'] < LOCKOUT_SECONDS else 1, 't': now}
            self.db.log_audit(uname, 'ورود ناموفق', '')
            return None if row else {'error': 'کاربر یافت نشد'}
        self._failed.pop(uname, None)
        self.current_user = {'id': row['id'], 'username': row['username'],
                             'full_name': row['full_name'], 'role': row['role']}
        self.db.log_audit(uname, 'ورود موفق', '')
        return self.current_user

    def logout(self):
        if self.current_user:
            self.db.log_audit(self.current_user['username'], 'خروج', '')
            self.current_user = None

    # ---------- کنترل دسترسی بر اساس نقش ----------
    @staticmethod
    def can(role, perm):
        """perm: view / edit / admin"""
        matrix = {
            'viewer':   {'view'},
            'operator': {'view', 'edit'},
            'admin':    {'view', 'edit', 'admin'},
        }
        return perm in matrix.get(role, set())


class RoleGate:
    """تابع کمکی برای اعمال سطح دسترسی در UI"""
    def __init__(self, auth):
        self.auth = auth

    def allowed(self, perm):
        if not self.auth.current_user:
            return False
        return AuthService.can(self.auth.current_user['role'], perm)
