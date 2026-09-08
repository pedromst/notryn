import {readdir,readFile,writeFile,mkdir,copyFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url)),source=path.join(root,'web'),destination=path.join(root,'site/demo');
const check=process.argv.includes('--check');
const entries=[];
async function inventory(dir,prefix=''){for(const item of await readdir(dir,{withFileTypes:true})){const name=prefix+item.name;if(item.isDirectory())await inventory(path.join(dir,item.name),name+'/');else entries.push(name);}}
await inventory(source);
const assets=new Set(entries);
for(const name of entries){
  const target=path.join(destination,name);let content=await readFile(path.join(source,name));
  if(/\.(html|css|js)$/.test(name)){
    let text=content.toString();
    // Only paths change for static hosting; UI, styles and behavior come from web/.
    text=text.replace(/(["'])\/([^"']+)\1/g,(whole,quote,value)=>{
      const file=value.split(/[?#]/)[0];return assets.has(file)?quote+value+quote:whole;
    });
    if(name.endsWith('.js'))text=text.replace(/\blocalStorage\b/g,'NotrynDemoStorage');
    if(name==='app.js')text=text.replaceAll('Saved to disk','Saved in this demo').replaceAll('saved to disk','saved in this demo').replaceAll('Saving to disk','Saving in this demo').replace("'Local files'","'Demo files'");
    if(name==='index.html')text=text.replace('<title>notryn</title>','<title>notryn demo · sample notes</title><meta name="robots" content="noindex,nofollow"><script src="../demo-seed.js"></script><script src="../demo-api.js"></script>');
    content=Buffer.from(text);
  }
  if(check){if(!(await readFile(target)).equals(content))throw Error('Demo asset differs: '+name);}
  else{await mkdir(path.dirname(target),{recursive:true});await writeFile(target,content);}
}
console.log('Demo uses the actual app HTML, styles, editor, navigation and Brain. Only static paths, temporary storage and save wording differ.');
