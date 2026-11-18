#!/bin/bash
# تست ورود پیش‌فرض همیشه‌فعال روی webapp-standalone v1.4.8
set -e
cd /home/z/my-project/webapp-standalone
export DATABASE_URL=file:$(pwd)/db/test-login.db
mkdir -p db
PORT=3241 NODE_ENV=production node server.js >/tmp/v148-server.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT

for i in $(seq 1 40); do
  curl -s -o /dev/null http://127.0.0.1:3241/api/health 2>/dev/null && break || sleep 1
done

echo "--- ۱) ورود با admin / New@1405! (باید موفق باشد) ---"
curl -s -X POST http://127.0.0.1:3241/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"New@1405!"}' | head -c 300; echo

echo "--- ۲) ورود با رمز اشتباه (باید رد شود) ---"
curl -s -X POST http://127.0.0.1:3241/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"WrongPass123"}' | head -c 300; echo

echo "--- ۳) ورود با admin / Admin@1405 (fallback قدیمی — بسته به دیتابیس) ---"
curl -s -X POST http://127.0.0.1:3241/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@1405"}' | head -c 300; echo
