#!/bin/bash
# آماده‌سازی دیتای نمونه: seed حضور/شیفت مهر ۱۴۰۵ + محاسبه حقوق دوره
set -e
cd /home/z/my-project/webapp-standalone
cp /home/z/my-project/node_modules/.prisma/client/libquery_engine-debian-openssl-3.0.x.so.node node_modules/.prisma/client/ 2>/dev/null || true

python3 -c "
import sqlite3
c = sqlite3.connect('db/payroll.db')
c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
c.execute(\"UPDATE \\\"User\\\" SET mustChangePassword=0, failedAttempts=0, lockedUntil=NULL, active=1 WHERE username='admin'\")
c.commit()
print('admin flag cleared')
"

DATABASE_URL="file:$(pwd)/db/payroll.db" NODE_ENV=production PORT=3245 node server.js > /tmp/webapp-seed.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -s -o /dev/null http://127.0.0.1:3245/api/context && break || sleep 0.5; done

J="curl -s -b /tmp/cjseed -c /tmp/cjseed"
rm -f /tmp/cjseed
echo "LOGIN: $($J -X POST http://127.0.0.1:3245/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"New@1405!"}' | head -c 80)"

node /home/z/my-project/scripts/seed-v146.cjs 2>&1 | tail -3

PERIOD=$(python3 -c "
import sqlite3
c = sqlite3.connect('db/payroll.db')
r = c.execute('SELECT id FROM PayrollPeriod WHERE jy=1405 AND jm=7').fetchone()
print(r[0] if r else 1)
")
echo "PERIOD=$PERIOD"

echo "CALC: $($J -X POST http://127.0.0.1:3245/api/payroll/calculate -H 'Content-Type: application/json' -d "{\"periodId\":$PERIOD}" | head -c 200)"
echo "CTX-VERSION: $($J http://127.0.0.1:3245/api/context | python3 -c 'import sys,json;print(json.load(sys.stdin).get("version"))' 2>&1)"
