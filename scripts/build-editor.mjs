import {build} from 'esbuild';
import {readdir,readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
await mkdir('web/vendor',{recursive:true});
await build({entryPoints:['src/editor.mjs'],bundle:true,minify:true,format:'iife',target:['es2020'],outfile:'web/vendor/editor.js',legalComments:'eof'});
const licenses=[];
const runtime=new Set(),queue=Object.keys(JSON.parse(await readFile('package.json','utf8')).dependencies||{});
while(queue.length){
 const name=queue.shift();if(runtime.has(name))continue;runtime.add(name);
 const pkg=JSON.parse(await readFile(path.join('node_modules',name,'package.json'),'utf8'));
 queue.push(...Object.keys(pkg.dependencies||{}));
}
for(const name of [...runtime].filter(n=>!n.startsWith('@')).sort()){
 const dir=path.join('node_modules',name),pkg=JSON.parse(await readFile(path.join(dir,'package.json'),'utf8'));
 if(name==='esbuild')continue;
 const license=(await readdir(dir)).find(f=>/^licen[cs]e(?:\.|$)/i.test(f));
 if(license)licenses.push(name+' '+pkg.version+'\n'+await readFile(path.join(dir,license),'utf8'));
}
await writeFile('web/vendor/EDITOR-LICENSES.txt',licenses.join('\n\n--------------------\n\n'));
