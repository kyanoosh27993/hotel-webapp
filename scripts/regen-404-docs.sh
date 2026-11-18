#!/bin/bash
# بازتولید خروجی‌های چهارگانه (قرارداد/حکم/فیش/تسویه) + عکس‌ها برای جبران ۴۰۴
set -x
cd /home/z/my-project/webapp-standalone
OUT=/home/z/my-project/download/preview-outputs
mkdir -p "$OUT"

cp /home/z/my-project/node_modules/.prisma/client/libquery_engine-debian-openssl-3.0.x.so.node node_modules/.prisma/client/ 2>/dev/null || true
mkdir -p db
# دیتابیس نمونه همین پوشه — پرچم تغییر رمز و قفل اکانت admin برداشته می‌شود (نام جدول: User)
python3 -c "
import sqlite3
c = sqlite3.connect('db/payroll.db')
c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
try:
    c.execute(\"UPDATE \\\"User\\\" SET mustChangePassword=0, failedAttempts=0, lockedUntil=NULL, active=1 WHERE username='admin'\")
    c.commit()
    print('admin flag cleared')
except Exception as e:
    print('flag-clear skipped:', e)
"

DATABASE_URL="file:$(pwd)/db/payroll.db" NODE_ENV=production PORT=3241 node server.js > /tmp/webapp-404.log 2>&1 &
SRV=$!
cleanup() { kill $SRV 2>/dev/null || true; }
trap cleanup EXIT
for i in $(seq 1 40); do curl -s -o /dev/null http://127.0.0.1:3241/api/context && break || sleep 0.5; done

J="curl -s -b /tmp/cj404 -c /tmp/cj404"
rm -f /tmp/cj404

# لاگین مقاوم: اگر پرچم تغییر رمز برگشته بود، دوباره پاک و لاگین تکرار می‌شود
for attempt in 1 2 3 4; do
  R=$($J -X POST http://127.0.0.1:3241/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"New@1405!"}')
  CTXV=$($J http://127.0.0.1:3241/api/context | python3 -c "import sys,json;print(json.load(sys.stdin).get('version'))" 2>/dev/null)
  echo "TRY$attempt CTX=$CTXV"
  if [ "$CTXV" != "None" ] && [ -n "$CTXV" ]; then break; fi
  python3 -c "
import sqlite3, base64, os
c = sqlite3.connect('db/payroll.db')
c.execute(\"UPDATE \\\"User\\\" SET mustChangePassword=0, failedAttempts=0, lockedUntil=NULL, active=1 WHERE username='admin'\")
c.commit()
# اگر عکس پرسنلی هم به‌خاطر برگشت وضعیت، خالی شده باشد دوباره درج می‌شود
ph = os.path.expanduser('/home/z/my-project/download/personnel_photo_3x4.png')
if os.path.exists(ph) and (c.execute('SELECT length(photo) FROM Personnel WHERE id=1').fetchone()[0] or 0) < 1000:
    img = base64.b64encode(open(ph,'rb').read()).decode()
    c.execute('UPDATE Personnel SET photo=? WHERE id=1', ('data:image/png;base64,'+img,))
    c.commit()
    print('photo re-inserted')
print('flag re-cleared')
"
  rm -f /tmp/cj404
done
echo "CTX: $($J http://127.0.0.1:3241/api/context | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('version'))" 2>&1)"

PID=$($J "http://127.0.0.1:3241/api/personnel?companyId=1" | python3 -c "
import sys,json
d=json.load(sys.stdin)
rows = d.get('personnel') or d.get('rows') or []
for p in rows:
    if 'محمدی' in (p.get('lastName') or ''):
        print(p['id']); break
")
echo "PERSONNEL-ID: $PID"

# ۱) قرارداد docx
$J -o "$OUT/tmp-contract.docx" "http://127.0.0.1:3241/api/contracts/generate?personnelId=$PID&kind=%D8%B3%D8%A7%D8%B9%D8%AA%DB%8C&format=docx"
# ۲) حکم docx روی سربرگ
$J -o "$OUT/tmp-hokm.docx" "http://127.0.0.1:3241/api/decrees/print?personnelId=$PID&format=docx"
# ۳) تسویه docx روی سربرگ
$J -o "$OUT/tmp-tasviye.docx" "http://127.0.0.1:3241/api/settlement?personnelId=$PID&toDate=1405%2F08%2F30&format=docx"
# ۴) فیش HTML
# دوره محاسبه‌شده — دیتای نمونه: مهر ۱۴۰۵ = id 7
PER=7
# اگر به‌خاطر برگشت وضعیت، محاسبه دوره از بین رفته باشد دوباره محاسبه می‌شود
CALC=$($J -X POST http://127.0.0.1:3241/api/payroll/calculate -H 'Content-Type: application/json' -d "{\"periodId\":$PER}")
echo "CALC: $(echo "$CALC" | head -c 120)"
echo "PERIOD-ID: $PER"
$J -o "$OUT/tmp-fish.html" "http://127.0.0.1:3241/api/exports/payslip?periodId=${PER:-1}&personnelId=$PID"
ls -la "$OUT"/tmp-*
echo "ALL-DONE"
