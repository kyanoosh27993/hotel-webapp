import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';

export const dynamic = 'force-dynamic';

/**
 * گزارش مرکز هزینه (Cost Center Report)
 * GET /api/reports/cost-center?fyId=1&jy=1405&jm=8
 * خروجی: حقوق و اضافه‌کار به تفکیک بخش (پذیرش، خانه‌داری، آشپزخانه، نگهبانی، عمومی)
 */
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const fyId = Number(url.searchParams.get('fyId'));
  const jy = Number(url.searchParams.get('jy'));
  const jm = Number(url.searchParams.get('jm'));

  if (!fyId || !jy || !jm) {
    return NextResponse.json({ error: 'پارامترهای fyId، jy و jm الزامی هستند.' }, { status: 400 });
  }

  const period = await db.payrollPeriod.findFirst({
    where: { fiscalYearId: fyId, jy, jm },
    include: { summaries: { include: { personnel: true } } }
  });

  if (!period) {
    return NextResponse.json({ error: 'دوره محاسبه‌شده‌ای برای این ماه یافت نشد.' }, { status: 404 });
  }

  // گروه‌بندی بر اساس department
  const departments = new Map<string, { count: number; gross: number; netPay: number; overtimeMin: number; workerIns: number; tax: number }>();
  
  for (const s of period.summaries) {
    const dept = s.personnel.department || 'عمومی';
    const existing = departments.get(dept) || { count: 0, gross: 0, netPay: 0, overtimeMin: 0, workerIns: 0, tax: 0 };
    existing.count += 1;
    existing.gross += s.gross || 0;
    existing.netPay += s.netPay || 0;
    existing.overtimeMin += s.overtimeMin || 0;
    existing.workerIns += s.workerIns || 0;
    existing.tax += s.tax || 0;
    departments.set(dept, existing);
  }

  const report = Array.from(departments.entries()).map(([dept, data]) => ({
    department: dept,
    personnelCount: data.count,
    totalGross: data.gross,
    totalNetPay: data.netPay,
    totalOvertimeHours: Math.round(data.overtimeMin / 60),
    totalWorkerIns: data.workerIns,
    totalTax: data.tax,
  })).sort((a, b) => b.totalNetPay - a.totalNetPay);

  const totals = report.reduce((acc, r) => ({
    count: acc.count + r.personnelCount,
    gross: acc.gross + r.totalGross,
    netPay: acc.netPay + r.totalNetPay,
    overtimeHours: acc.overtimeHours + r.totalOvertimeHours,
    workerIns: acc.workerIns + r.totalWorkerIns,
    tax: acc.tax + r.totalTax,
  }), { count: 0, gross: 0, netPay: 0, overtimeHours: 0, workerIns: 0, tax: 0 });

  return NextResponse.json({
    period: `${jy}/${String(jm).padStart(2, '0')}`,
    departments: report,
    totals,
  });
}
