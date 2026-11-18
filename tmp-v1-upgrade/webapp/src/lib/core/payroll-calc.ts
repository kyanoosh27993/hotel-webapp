import { db } from '@/lib/db';
import { calcEmployee, type CalcContext, type CalcItem } from './payroll-engine';
import { getFySettings } from './payroll-engine'; // فرض: این تابع تنظیمات سال مالی را می‌خواند
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

// ---------------- پشتیبان‌گیری خودکار ----------------
const BACKUP_DIR = path.join(os.homedir(), '.payroll-backups');
function autoBackup() {
  try {
    if (!fs.existsSync(BACKUP_DIR)) fs.mkdirSync(BACKUP_DIR, { recursive: true });
    const dbPath = process.env.DATABASE_URL?.replace('file:', '') || 'prisma/dev.db';
    const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const dest = path.join(BACKUP_DIR, `backup-${dateStr}.db`);
    if (fs.existsSync(dbPath)) {
      fs.copyFileSync(dbPath, dest);
      // حذف فایل‌های قدیمی‌تر از ۳۰ روز
      const files = fs.readdirSync(BACKUP_DIR).filter(f => f.startsWith('backup-')).sort();
      const cutoff = Date.now() - 30 * 86400000;
      for (const f of files) {
        const stat = fs.statSync(path.join(BACKUP_DIR, f));
        if (stat.mtimeMs < cutoff) fs.unlinkSync(path.join(BACKUP_DIR, f));
      }
    }
  } catch {
    /* اگر پشتیبان‌گیری ممکن نبود، برنامه متوقف نشود */
  }
}

// ---------------- محاسبه دوره با Batch Fetching ----------------
export async function calculatePeriod(periodId: number, itemsConfig: CalcItem[]) {
  const period = await db.payrollPeriod.findUnique({ 
    where: { id: periodId }, 
    include: { fiscalYear: { include: { company: true } } } 
  });
  if (!period) throw new Error('دوره پیدا نشد');
  
  // قفل دوره‌های تأیید/پرداخت‌شده
  if (['approved', 'paid', 'locked'].includes(period.status)) {
    throw new Error(`دوره ${period.jy}/${period.jm} قبلاً ${period.status === 'approved' ? 'تأیید' : period.status === 'paid' ? 'پرداخت' : 'قفل'} شده است.`);
  }

  const companyId = period.fiscalYear.companyId;
  const fyId = period.fiscalYearId;
  const { jy, jm } = period;

  // ✅ BATCH FETCHING: واکشی یکجای تمام داده‌های مورد نیاز
  const [personnelList, allContracts, allLoans, allAdvances, allSummariesPrev] = await Promise.all([
    db.personnel.findMany({ where: { companyId, status: 'شاغل' } }),
    db.contract.findMany({ where: { personnel: { companyId } }, orderBy: { createdAt: 'desc' } }),
    db.loan.findMany({ where: { personnel: { companyId }, active: true } }),
    db.advance.findMany({ where: { personnel: { companyId }, recovered: false } }),
    db.payrollSummary.findMany({ 
      where: { period: { fiscalYearId: fyId, jy: jm === 1 ? jy - 1 : jy, jm: jm === 1 ? 12 : jm - 1 } } 
    })
  ]);

  // ساخت Map برای دسترسی O(1)
  const contractMap = new Map<number, typeof allContracts[0]>();
  for (const c of allContracts) { if (!contractMap.has(c.personnelId)) contractMap.set(c.personnelId, c); }
  
  const loanMap = new Map<number, typeof allLoans>();
  for (const l of allLoans) {
    const arr = loanMap.get(l.personnelId) || [];
    arr.push(l); loanMap.set(l.personnelId, arr);
  }
  
  const advanceMap = new Map<number, typeof allAdvances>();
  for (const a of allAdvances) {
    const arr = advanceMap.get(a.personnelId) || [];
    arr.push(a); advanceMap.set(a.personnelId, arr);
  }

  const prevBalanceMap = new Map<number, number>();
  for (const s of allSummariesPrev) {
    if (!s.payPaid) prevBalanceMap.set(s.personnelId, s.netPay);
  }

  const settings = await getFySettings(fyId);
  const taxBrackets = JSON.parse(settings['tax_brackets'] || '[]');

  // اجرای محاسبات داخل تراکنش اتمی
  await db.$transaction(async (tx) => {
    // پاک کردن خلاصه‌های قبلی این دوره
    await tx.payrollSummary.deleteMany({ where: { periodId } });

    for (const p of personnelList) {
      const contract = contractMap.get(p.id) || null;
      const loans = loanMap.get(p.id) || [];
      const advances = advanceMap.get(p.id) || [];
      const prevBal = prevBalanceMap.get(p.id) || 0;

      const ctx: CalcContext = {
        settings, taxBrackets,
        decree: { /* مقادیر حکم از دیتابیس */ } as any,
        contract: contract ? {
          contractType: contract.contractType, hourlyRate: contract.hourlyRate,
          dailyRate: contract.dailyRate, monthlyWage: contract.monthlyWage, projectAmount: contract.projectAmount
        } : null,
        loans: loans.map(l => ({ installment: l.installment, active: l.active })),
        advances: advances.map(a => ({ amount: a.amount, recovered: a.recovered })),
        inputs: {}, daysInMonth: 30, paidDays: 30,
        overtimeHours: 0, holidayHours: 0, fridayHours: 0, nightHours: 0,
        leaveDays: 0, insuredBase: 0, taxBase: 0,
      };

      const result = calcEmployee(ctx, itemsConfig);
      
      // ثبت خلاصه
      await tx.payrollSummary.create({
        data: {
          periodId, personnelId: p.id,
          gross: result.summary.gross, insuredBase: result.summary.insuredBase,
          workerIns: result.summary.workerIns, employerIns: result.summary.employerIns,
          unemploymentIns: result.summary.unemploymentIns, taxBase: result.summary.taxBase,
          tax: result.summary.tax, totalDeductions: result.summary.totalDeductions,
          netPay: result.summary.netPay, prevBalance: prevBal,
        }
      });

      // ✅ به‌روزرسانی وام و مساعده پس از محاسبه موفق
      for (const l of loans) {
        const paidCount = l.paidCount + 1;
        const finished = l.installmentsCount > 0 && paidCount >= l.installmentsCount;
        await tx.loan.update({
          where: { id: l.id },
          data: {
            paidCount,
            remaining: Math.max(0, (l.remaining ?? l.totalAmount) - l.installment),
            active: !finished,
          }
        });
      }
      for (const a of advances) {
        await tx.advance.update({
          where: { id: a.id },
          data: { recovered: true, period: `${jy}-${String(jm).padStart(2, '0')}` }
        });
      }
    }

    // تغییر وضعیت دوره به calculated
    await tx.payrollPeriod.update({
      where: { id: periodId },
      data: { status: 'calculated' }
    });
  });

  // پشتیبان‌گیری خودکار پس از محاسبه موفق
  autoBackup();
}
