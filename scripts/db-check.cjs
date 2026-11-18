const {PrismaClient}=require('@prisma/client');
const db=new PrismaClient();
(async()=>{
  const ms = await db.attendanceMonth.findMany();
  console.log('months:', JSON.stringify(ms.map(m=>({id:m.id,jy:m.jy,jm:m.jm}))));
  const am = ms.find(m=>m.jy===1405&&m.jm===7);
  const rows = await db.attendanceDaily.findMany({where:{monthId:am.id, personnelId:1, day:{in:[3,5,6,8,13,17,24]}}, select:{day:true,status:true,leaveMin:true,leaveKind:true,workedMin:true,lateMin:true,earlyMin:true,overtimeMin:true}});
  for(const r of rows) console.log(JSON.stringify(r));
  await db.$disconnect();
})();
