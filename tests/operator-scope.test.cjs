const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const dir=process.env.NOTRYN_SITE_DIR||path.join(__dirname,'../site');
const pages=fs.readdirSync(dir).filter(f=>f.endsWith('.html')).map(f=>({file:f,text:fs.readFileSync(path.join(dir,f),'utf8')}));
const NIF=/PT\d{9}/g, FULL='Pedro Miguel da Silva Teixeira';
const withNif=pages.filter(p=>p.text.match(NIF)).map(p=>p.file).sort();

test('o NIF só aparece nas páginas de identificação e nos Termos',()=>{
 assert.deepEqual(withNif,['contact.html','terms.html']);
});
test('o NIF tem formato e dígito de controlo válidos',()=>{
 for(const p of pages)for(const m of p.text.match(NIF)||[]){
  const d=m.slice(2).split('').map(Number);
  const sum=d.slice(0,8).reduce((a,v,i)=>a+v*(9-i),0);
  const c=11-(sum%11)>=10?0:11-(sum%11);
  assert.equal(d[8],c,p.file);
 }
});
test('o nome completo só aparece ao lado do NIF',()=>{
 const users=pages.filter(p=>p.text.includes(FULL)).map(p=>p.file).sort();
 assert.deepEqual(users,['contact.html','terms.html']);
});
test('rodapés e privacidade não têm NIF nem nome completo',()=>{
 for(const p of pages){
  for(const f of p.text.match(/<footer[\s\S]*?<\/footer>/g)||[])assert.ok(!NIF.test(f)&&!f.includes(FULL),'rodapé em '+p.file);
  NIF.lastIndex=0;
 }
 const privacy=pages.find(p=>p.file==='privacy.html').text;
 assert.ok(!privacy.match(NIF)&&!privacy.includes(FULL));
 assert.ok(privacy.includes('Data controller')&&privacy.includes('Rua 8, n.º 589, 4500-370 Espinho, Portugal'));
});
test('a morada é sempre escrita da mesma forma',()=>{
 for(const p of pages)for(const m of p.text.match(/Rua 8[^<]*/g)||[])assert.equal(m,'Rua 8, n.º 589, 4500-370 Espinho, Portugal',p.file);
});
