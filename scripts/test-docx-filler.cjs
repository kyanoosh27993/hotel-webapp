// تست مستقیم پرکن قرارداد — بدون Next
const path = require('path');
process.env.PAYROLL_WEBAPP_DIR = '/home/z/my-project';
const { execSync } = require('child_process');
// از طریق tsx؟ نه — با esbuild-register یا مستقیم ts-node سخت است؛ از tsx استفاده می‌کنیم اگر هست
const hasTsx = (() => { try { require.resolve('tsx'); return true; } catch { return false; } })();
console.log('tsx:', hasTsx);
