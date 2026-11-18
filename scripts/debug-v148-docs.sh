#!/bin/bash
# دیباگ: سرور standalone + لاگین + دیدن context و personnel خام
cd /home/z/my-project/webapp-standalone
cp /home/z/my-project/node_modules/.prisma/client/libquery_engine-debian-openssl-3.0.x.so.node node_modules/.prisma/client/ 2>/dev/null || true
mkdir -p db
[ -f db/payroll.db ] || cp /home/z/my-project/db/custom.db db/payroll.db
DATABASE_URL="file:$(pwd)/db/payroll.db" NODE_ENV=production PORT=3244 node server.js > /tmp/webapp-dbg.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -s -o /dev/null http://127.0.0.1:3244/api/context && break || sleep 0.5; done
J="curl -s -b /tmp/cjdbg -c /tmp/cjdbg"
rm -f /tmp/cjdbg
echo "LOGIN: $($J -X POST http://127.0.0.1:3244/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"New@1405!"}' | head -c 150)"
echo "--- context ---"
$J http://127.0.0.1:3244/api/context | head -c 400; echo
echo "--- personnel?companyId=1 ---"
$J "http://127.0.0.1:3244/api/personnel?companyId=1" | head -c 400; echo
echo "--- personnel (no param) ---"
$J "http://127.0.0.1:3244/api/personnel" | head -c 400; echo
