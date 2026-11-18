// تست صحت هسته نسخه ۰.۴ (پورت موتور ۰.۳)
import { parseNumber, parseHHMM, formatMoney, parseJalaliDateStr, minutesToHHMM } from '../src/lib/core/numbers';
import { daysInMonth, weekday, WEEKDAY_NAMES, hijriToJalali } from '../src/lib/core/jalali';
import { calcProgressiveTax } from '../src/lib/core/payroll-engine';
import { recomputeDay } from '../src/lib/core/shifts';
import { dbfWrite } from '../src/lib/core/standard-exports';
import iconv from 'iconv-lite';

let ok = 0, fail = 0;
function check(name: string, cond: boolean, detail = '') {
  if (cond) { ok++; console.log(`PASS ${name}`); }
  else { fail++; console.log(`FAIL ${name} ${detail}`); }
}

// اعداد
check('parseNumber فارسی', parseNumber('۱۲۳٬۴۵۶') === 123456);
check('parseNumber خالی', parseNumber('', 5) === 5);
check('parseHHMM دستگاه', parseHHMM('216:02') === 216 * 60 + 2);
check('parseHHMM اعشاری', parseHHMM('8.5') === 510);
check('minutesToHHMM', minutesToHHMM(496) === '8:16');
check('formatMoney', formatMoney(1234567) === '۱٬۲۳۴٬۵۶۷');
check('parseJalaliDate', JSON.stringify(parseJalaliDateStr('۱۴۰۵/۰۷/۰۱')) === '[1405,7,1]');

// تقویم
check('daysInMonth 1405/7', daysInMonth(1405, 7) === 30);
check('daysInMonth اسفند کبیسه 1403', daysInMonth(1403, 12) === 30);
check('weekday 1405/7/1 چهارشنبه', weekday(1405, 7, 1) === 4, WEEKDAY_NAMES[weekday(1405, 7, 1)]);
check('weekday 1405/7/2 پنجشنبه', weekday(1405, 7, 2) === 5, WEEKDAY_NAMES[weekday(1405, 7, 2)]);
check('weekday 1404/7/5 شنبه', weekday(1404, 7, 5) === 0, WEEKDAY_NAMES[weekday(1404, 7, 5)]);
// عاشورای ۱۴۰۴ رسمی = ۱۵ تیر ۱۴۰۴ ← هجری 1447/1/10
const ash = hijriToJalali(1447, 1, 10);
check('عاشورا ۱۴۰۴/۴/۱۵ قمری', !!ash && ash[0] === 1404 && ash[1] === 4 && ash[2] === 15, JSON.stringify(ash));

// مالیات ماده ۸۴ — ۵۰۰ میلیون: ۱۰۰م در پله ۱۰٪ = ۱۰٬۰۰۰٬۰۰۰
check('مالیات ۵۰۰م', calcProgressiveTax(500_000_000, [
  { fromAmount: 0, toAmount: 400_000_000, ratePercent: 0 },
  { fromAmount: 400_000_000, toAmount: 800_000_000, ratePercent: 10 },
]) === 10_000_000);

// شیفت
const day = recomputeDay(
  { entry1: 8 * 60 + 20, exit1: 17 * 60, entry2: -1, exit2: -1, entry3: -1, exit3: -1, workedMin: 510, leaveMin: 0, missionMin: 0, status: '' },
  480, 10, 10, 480, 960,
);
check('تاخیر ۲۰ دقیقه با گریس ۱۰', day.lateMin === 10, JSON.stringify(day));
const day2 = recomputeDay(
  { entry1: 8 * 60 + 5, exit1: 16 * 60, entry2: -1, exit2: -1, entry3: -1, exit3: -1, workedMin: 475, leaveMin: 0, missionMin: 0, status: '' },
  480, 10, 10, 480, 960,
);
check('گریس تاخیر', day2.lateMin === 0);
check('تعجیل', day2.earlyMin === 0 && day2.status === 'حاضر', JSON.stringify(day2));
const day3 = recomputeDay(
  { entry1: 480, exit1: 960, entry2: -1, exit2: -1, entry3: -1, exit3: -1, workedMin: 0, leaveMin: 480, missionMin: 0, status: '' },
  480, 10, 10, 480, 960,
);
check('مرخصی روزانه', day3.status === 'مرخصی' && day3.missingMin === 0);

// DBF
const buf = dbfWrite(
  [{ name: 'KARGAH', type: 'C', length: 10, decimals: 0 }, { name: 'DAY', type: 'N', length: 5, decimals: 0 }],
  [{ KARGAH: '12345', DAY: 30 }],
);
check('DBF هدر', buf[0] === 3 && buf.readUInt32LE(4) === 1 && buf.readUInt16LE(8) === 32 + 64 + 1 && buf.readUInt16LE(10) === 16);
check('DBF نام فیلد', buf.toString('ascii', 32, 38) === 'KARGAH');
check('DBF فارسی cp1256', dbfWrite([{ name: 'NAME', type: 'C', length: 40, decimals: 0 }], [{ NAME: 'علی' }]).length === 32 + 32 + 1 + 1 + 40);

console.log(`\n=== ${ok} پاس / ${fail} خطا ===`);
process.exit(fail ? 1 : 0);
