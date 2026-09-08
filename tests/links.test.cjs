const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const context={window:{}};vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/links.js'),'utf8'),context);
for(const item of require('./link-resolution.json'))test('reader links: '+item.name,()=>{
 assert.equal(context.window.NotrynLinks.resolve(item.target,item.source,item.paths,item.kind),item.expected);
});
