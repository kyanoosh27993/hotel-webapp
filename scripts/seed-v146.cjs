// دیتای فرضی کامل علی محمدی + حضورغیاب جامع مهر ۱۴۰۵ + راستی‌آزمایی محاسبات (نسخه ۱٫۴٫۶)
// اجرا: node /tmp/seed146.cjs  (سرور باید از قبل بالا باشد روی 3241 — این اسکریپت فقط DB را می‌نویسد و API را صدا می‌زند)
const { PrismaClient } = require('@prisma/client');
const db = new PrismaClient({ datasources: { db: { url: 'file:/home/z/my-project/webapp-standalone/db/payroll.db' } } });

const PID = 1; // علی محمدی — کد ۱۰۰

async function main() {
  // ۱) پرسنل با همه فیلدها
  await db.personnel.update({
    where: { id: PID },
    data: {
      personnelCode: '100', firstName: 'علی', lastName: 'محمدی', fatherName: 'رضا',
      nationalId: '3050123451', idNumber: '369123', idSerial: '12/ع3/548921', idIssuePlace: 'رفسنجان',
      birthDate: '1368/05/12', birthPlace: 'رفسنجان', gender: 'مرد', maritalStatus: 'متأهل', dependents: 2,
      education: 'دیپلم', mobile: '09135267890', postalCode: '7719143211',
      address: 'رفسنجان، میدان شهدا، بلوار آیت‌الله طالقانی، نبش کوچه ۵۶ و ۵۸، هتل هیلان',
      jobTitle: 'کارگر خدمات هتل', jobCode: '6151', department: 'خانه‌داری',
      ssoNumber: '36912345', insuranceType: 2, ssoInsurer: 'شعبه ۲ رفسنجان', taxExemptionCode: 1,
      militaryStatus: 'معاف', workLocation: 'هتل هیلان رفسنجان', permanentNight: false,
      costCenter: 'خانه‌داری', payslipGroup: 'گروه ۱',
      bankName: 'رفاه کارگران شعبه رفسنجان', bankAccount: '418512090', bankSheba: 'IR5505600000000041851209001',
      hireDate: '1405/01/01', endWorkDate: '', status: 'شاغل',
    },
  });
  console.log('personnel OK');

  // ۲) حکم پرسنلی ۱۴۰۵ (بدون خواروبارِ تکراری — بن کارگری فقط یک‌بار)
  const oldDecrees = await db.decree.findMany({ where: { personnelId: PID } });
  for (const d of oldDecrees) await db.decree.delete({ where: { id: d.id } });
  const eff = '1405/01/01';
  const decree = await db.decree.create({
    data: {
      personnelId: PID, effectiveDate: eff,
      jobWage: 161255500, seniorityWage: 5000000, housing: 30000000, food: 0,
      childAllowance: 16625550, familyAllowance: 5000000, workerBen: 22000000,
      adjustmentDiff: 0, supervision: 0, educationAid: 0, laborMarket: 0,
      attractionPercent: 0, attractionAmount: 0, otherBenefits: 0, fixedOvertime: 0, shiftAllowance: 0,
      notes: 'حکم حقوقی سال ۱۴۰۵ بر اساس بخشنامه وزارت تعاون، کار و رفاه اجتماعی',
      createdAt: new Date('2026-09-23T06:00:00Z'), // ۱ مهر ۱۴۰۵ — تاریخ صدور در سیستم
    },
  });
  console.log('decree OK id=', decree.id);

  // ۳) قرارداد ساعتی بدون ردیف DB (مزد مبنا از حکم) — حذف قراردادهای قبلی
  await db.contract.deleteMany({ where: { personnelId: PID } });
  console.log('contract rows cleared');

  // ۴) شیفت‌ها: صبح/عصر ۱۰٪ و شب ۳۵٪
  const oldShifts = await db.shift.findMany({ where: { companyId: 1, name: { in: ['نوبت صبح و عصر', 'نوبت شب'] } } });
  for (const s of oldShifts) await db.shift.delete({ where: { id: s.id } });
  const shiftA = await db.shift.create({
    data: {
      companyId: 1, name: 'نوبت صبح و عصر', premiumPct: 10,
      schedule: JSON.stringify({ '0': [480, 960], '1': [480, 960], '2': [480, 960], '3': [480, 960], '4': [480, 960] }),
      notes: 'شیفت صبح و عصر ۸ تا ۱۶ — حق شیفت ۱۰٪',
    },
  });
  const shiftB = await db.shift.create({
    data: {
      companyId: 1, name: 'نوبت شب', premiumPct: 35,
      schedule: JSON.stringify({ '0': [1200, 1680], '1': [1200, 1680], '2': [1200, 1680], '3': [1200, 1680], '4': [1200, 1680] }),
      notes: 'شیفت شب ۲۰ تا ۰۴ — حق شیفت ۳۵٪ + شب‌کاری ۳۵٪ (۲۲ تا ۶)',
    },
  });
  console.log('shifts OK', shiftA.id, shiftB.id);

  // انتساب ماه مهر = شیفت صبح/عصر؛ روزهای ۱۱ تا ۳۰ با استثنای روزانه → شیفت شب
  await db.shiftAssignment.deleteMany({ where: { personnelId: PID, jy: 1405, jm: 7 } });
  await db.shiftAssignment.create({ data: { personnelId: PID, jy: 1405, jm: 7, shiftId: shiftA.id } });
  await db.shiftOverride.deleteMany({ where: { personnelId: PID, jy: 1405, jm: 7 } });
  for (let d = 11; d <= 30; d++) {
    await db.shiftOverride.create({ data: { personnelId: PID, jy: 1405, jm: 7, jd: d, kind: 'shift', shiftId: shiftB.id, note: 'شیفت شب' } });
  }
  // جمعه ۳ (کار با روز جایگزین): استثنای off در شنبه ۵ — روز جایگزین
  await db.shiftOverride.create({ data: { personnelId: PID, jy: 1405, jm: 7, jd: 5, kind: 'off', note: 'تعطیل جایگزین جمعه‌کاری سوم مهر (قرارداد ساعتی = بدون حقوق)' } });
  console.log('assignment/overrides OK');

  // ۵) مرخصی‌ها: استحقاقی روز ۶، بدون حقوق روز ۸، استعلاجی روز ۱۳
  await db.leave.deleteMany({ where: { personnelId: PID } });
  await db.leave.create({ data: { personnelId: PID, fromDate: '1405/07/06', toDate: '1405/07/06', days: 1, leaveKind: 'استحقاقی', notes: 'مرخصی استحقاقی یک‌روزه' } });
  await db.leave.create({ data: { personnelId: PID, fromDate: '1405/07/08', toDate: '1405/07/08', days: 1, leaveKind: 'بدون حقوق', notes: 'مرخصی بدون حقوق' } });
  await db.leave.create({ data: { personnelId: PID, fromDate: '1405/07/13', toDate: '1405/07/13', days: 1, leaveKind: 'استعلاجی', notes: 'گواهی پزشکی' } });
  console.log('leaves OK');

  // ۶) حضور و غیاب ماه مهر ۱۴۰۵ — روزبه‌روز
  const fy = await db.fiscalYear.findFirst({ where: { companyId: 1, jy: 1405 } });
  await db.attendanceMonth.deleteMany({ where: { fiscalYearId: fy.id, jy: 1405, jm: 7 } });
  const am = await db.attendanceMonth.create({ data: { fiscalYearId: fy.id, jy: 1405, jm: 7, source: 'دستی' } });
  // جمعه‌های مهر: ۳، ۱۰، ۱۷، ۲۴ — روزهای بدون کار: ۵ (جایگزین)، ۶ (استحقاقی)، ۸ (بدون حقوق)، ۱۳ (استعلاجی)، ۲۴ (جمعه استراحت)
  const noWork = new Set([5, 6, 8, 13, 24]);
  // اضافه‌کاری: روز ۵ ساعت (دقیقه) در روزهای ۴، ۷ (شیفت صبح) و ۱۵۰ دقیقه در روز ۱۵ (شب)
  const otMin = { 4: 120, 7: 120, 15: 180 };
  // تاخیر روز ۲ (ورود ۵۱۰)، تعجیل روز ۴ (خروج ۹۳۰)
  for (let d = 1; d <= 30; d++) {
    const isB = d >= 11; // شیفت شب
    let entry1, exit1, entry2 = -1, exit2 = -1, worked;
    if (noWork.has(d)) {
      entry1 = exit1 = -1; worked = 0;
      if (d === 24) { /* جمعه استراحت — هیچ */ }
    } else if (isB) {
      entry1 = 1200; exit1 = 1680; entry2 = 0; exit2 = 240; worked = 480;
    } else {
      entry1 = 480; exit1 = 960; worked = 480;
      if (d === 2) entry1 = 510;           // تاخیر ۳۰ دقیقه (۲۵ بعد از گریس ۵)
      if (d === 4) exit1 = 930;            // تعجیل ۳۰ دقیقه (۲۵ بعد از گریس ۵)
      if (d === 3 || d === 10 || d === 17) { // جمعه‌کاری — بدون برنامه شیفت
        entry1 = 480; exit1 = 960; worked = 480;
      }
    }
    await db.attendanceDaily.create({
      data: {
        monthId: am.id, personnelId: PID, day: d,
        status: noWork.has(d) ? '' : 'بدون شیفت',
        entry1, exit1, entry2, exit2, entry3: -1, exit3: -1,
        overtimeMin: otMin[d] ?? 0,
        workedMin: worked,
        missionMin: 0, leaveMin: 0, lateMin: 0, earlyMin: 0, missingMin: 0, expectedMin: 0, leaveKind: '',
      },
    });
  }
  console.log('attendance rows OK (30)');

  // ۷) اصلاح پیکربندی (کارشناس تامین اجتماعی): بن کارگری مشمول بیمه + گریس ۵ دقیقه (قانون ۱٫۴٫۳)
  await db.payrollItemConfig.updateMany({ where: { code: 'worker_ben' }, data: { insured: true } });
  await db.fySetting.updateMany({ where: { key: { in: ['late_grace_minutes', 'early_grace_minutes'] }, value: '10' }, data: { value: '5' } });

  // ۸) دوره حقوق مهر — بازمحاسبه حضور سپس حقوق از طریق API در اسکریپت جدا انجام می‌شود
  await db.$disconnect();
  console.log('SEED-DONE');
}
main().catch((e) => { console.error('SEED-ERR', e.message); process.exit(1); });
