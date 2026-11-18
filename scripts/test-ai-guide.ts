// تست پایگاه دانش راهنمای دستیار — اجرا: bun scripts/test-ai-guide.ts
import { matchGuideTopic, isGuideIntent, GUIDE_TOPICS } from '../src/lib/ai/guide';

const CASES: Array<[string, string | null, boolean]> = [
  // [پرسش، شناسه موضوع موردانتظار، انتظار تشخیص guide-intent]
  ['چجوری میتونم ساعات کاری پرسنل را ببینم یا اصلاح کنم؟', 'attendance-view-hours', true],
  ['چطور میتوانم ساعات کاری کارمندان را مشاهده کنم', 'attendance-view-hours', true],
  ['فایل دستگاه را از کجا ایمپورت کنم؟', 'attendance-import', true],
  ['چگونه شیفت جدید تعریف کنم', 'shifts-define', true],
  ['شیفت را چطور به پرسنل اختصاص بدهم', 'shifts-assign', true],
  ['کارمند جدید چطور ثبت میشه', 'personnel-add', true],
  ['وضعیت پرسنل رو چطور شاغل کنم', 'personnel-edit-status', true],
  ['نرخ بیمه اختصاصی برای یک نفر چطور بدهم', 'personnel-insurance', true],
  ['حکم پرسنلی کجا ثبت میشود', 'decrees', true],
  ['قرارداد ساعتی چطور ثبت کنم', 'contracts', true],
  ['دوره حقوق ماهانه چطور محاسبه میشود', 'payroll-calculate', true],
  ['فیش حقوقی را چطور چاپ کنم', 'payroll-payslip', true],
  ['وام و کسورات دستی کجا وارد کنم', 'payroll-manual-items', true],
  ['لیست بانک و ثبت پرداخت چطوریه', 'payroll-bank', true],
  ['مانده حقوق ماه قبل کجا نمایش داده میشود', 'payroll-prev-balance', true],
  ['فایل مالیات wp wh چطور بگیرم', 'std-tax', true],
  ['فایل بیمه تامین اجتماعی و dbf', 'std-insurance', false],
  ['گزارش آمار مرخصی چطور بگیرم', 'reports', true],
  ['تعطیل قمری را چطور اصلاح کنم', 'calendar-holidays', true],
  ['شرکت جدید و لوگو کجا ثبت میشود', 'companies-setup', true],
  ['سال مالی جدید چطور بسازم', 'companies-fy', true],
  ['پله های مالیات را کجا تغییر دهم', 'settings-tax-brackets', true],
  ['فرمول اقلام فیش را چطور ویرایش کنم', 'settings-items', true],
  ['گریس تاخیر و ساعات موظفی کجاست', 'settings-fy-params', true],
  ['ollama را چطور وصل کنم', 'settings-ollama', true],
  ['از کجا شروع کنم', 'general-quickstart', true],
  ['حالت تیره چطوریه', 'general-dark-print', true],
  // — پرسش‌های داده‌ای که نباید به راهنما بروند —
  ['جمع خالص حقوق مهر ۱۴۰۵', null, false],
  ['خالص حقوق علی محمدی', null, false],
  ['تعداد پرسنل', null, false],
  ['مالیات علی محمدی چقدر بود', null, false],
  ['تعطیلات آبان ۱۴۰۵', null, false],
];

let pass = 0;
let fail = 0;
for (const [q, expectedId, expectedGuide] of CASES) {
  const gi = isGuideIntent(q);
  const topic = matchGuideTopic(q);
  const okGuide = gi === expectedGuide;
  const okTopic = expectedId ? topic?.id === expectedId : topic === null;
  const ok = okGuide && okTopic;
  if (ok) {
    pass++;
    console.log(`PASS  ${q}  →  ${topic?.id ?? '(بدون موضوع)'}`);
  } else {
    fail++;
    console.log(`FAIL  ${q}\n      expected topic=${expectedId}, got=${topic?.id ?? 'null'} | guide-intent expected=${expectedGuide}, got=${gi}`);
  }
}
console.log(`\nموضوعات پایگاه دانش: ${GUIDE_TOPICS.length}`);
console.log(`نتیجه: ${pass} پاس / ${fail} خطا`);
if (fail > 0) process.exit(1);
