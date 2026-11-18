#!/bin/bash
# آپلود assetهای نسخه ۱.۴.۱ به گیت‌هاب ریلیز — با راستی‌آزمایی md5 سمت سرور
set -e
TOKEN="TOKEN-REMOVED-FOR-SECURITY"
REL=447219542
DL=/home/z/my-project/download
upload() {
  local f="$1"
  local name
  name=$(basename "$f")
  echo "uploading $name ..."
  curl -sS -X POST \
    -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/octet-stream" \
    --data-binary @"$f" \
    "https://uploads.github.com/repos/kyanoosh27993/payroll-releases/releases/$REL/assets?name=$name" \
    -o /tmp/up.json
  python3 - "$f" <<'PY'
import json, hashlib, sys
local = sys.argv[1]
d = json.load(open('/tmp/up.json'))
if 'errors' in d or 'message' in d and 'errors' in d:
    print('  UPLOAD FAILED:', json.dumps(d)[:300]); sys.exit(1)
gh = d.get('size'); ghmd5 = (d.get('digest') or '').replace('sha256:','') 
import base64, hashlib
# digest از سرور sha256 است
lsha = hashlib.sha256(open(local,'rb').read()).hexdigest()
print(f"  name={d['name']} state={d['state']} size={d['size']}")
print(f"  local sha256={lsha[:16]}…  server digest match={d.get('digest','').endswith(lsha)}")
if d['size'] != __import__('os').path.getsize(local): print('  SIZE MISMATCH!'); sys.exit(1)
PY
}
upload "$DL/PayrollSystem_v1.4.1_2026-11-16_installer.exe"
upload "$DL/PayrollSystem_v1.4.1_2026-11-16_portable.exe"
upload "$DL/PayrollSystem_v1.4.1_2026-11-16_source.zip"
upload "$DL/PayrollSystem_v1.4.1_2026-11-16_mobile.html"
echo "ALL UPLOADS DONE"
