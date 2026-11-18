// تست پارس فایل واقعی دستگاه حضور و غیاب
import * as fs from 'fs';
import { parseDeviceFile } from '../src/lib/core/device-import';

const buf = fs.readFileSync('/home/z/my-project/upload/ساعات کارکرد دستگاه mehr1405.xls');
const logs: string[] = [];
const parsed = parseDeviceFile(buf, (m) => logs.push(m));
console.log('دوره:', JSON.stringify(parsed.period));
console.log('تعداد شیت/پرسنل:', parsed.employees.length);
console.log('لاگ‌ها:', logs.slice(0, 5));
for (const e of parsed.employees.slice(0, 3)) {
  console.log(`- کارت=${e.cardNo} نام=${e.name} روزها=${e.daily.length} مجموع=${JSON.stringify(e.totals)}`);
  console.log('  روز اول:', JSON.stringify(e.daily[0]));
}
