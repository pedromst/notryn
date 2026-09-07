import {build} from 'esbuild';
import {readdir,readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
await mkdir('web/vendor',{recursive:true});
await build({entryPoints:['src/editor.mjs'],bundle:true,minify:true,format:'iife',target:['es2020'],outfile:'web/vendor/editor.js',legalComments:'eof'});
const licenses=[];
for(const name of (await readdir('node_modules')).filter(n=>!n.startsWith('.')&&!n.startsWith('@'))){
 const dir=path.join('node_modules',name),pkg=JSON.parse(await readFile(path.join(dir,'package.json'),'utf8'));
 if(name==='esbuild')continue;
 const license=(await readdir(dir)).find(f=>/^licen[cs]e(?:\.|$)/i.test(f));
 if(license)licenses.push(name+' '+pkg.version+'\n'+await readFile(path.join(dir,license),'utf8'));
}
await writeFile('web/vendor/EDITOR-LICENSES.txt',licenses.join('\n\n--------------------\n\n'));
