'use strict';
// Keep reader navigation aligned with filemoves.resolve_link and the graph.
window.NotrynLinks={resolve(link,source,paths,kind='wiki'){
 let target;try{target=decodeURIComponent(link.split('#')[0].split('?')[0].replace(/\\([\\()\[\] ])/g,'$1'));}catch{return null;}
 if(!target||/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(target)||target.startsWith('//'))return null;
 const parts=[];
 for(const part of [...source.split('/').slice(0,-1),...target.split('/')]){
  if(part==='..'){if(parts.length&&parts.at(-1)!=='..')parts.pop();else parts.push(part);}
  else if(part&&part!=='.')parts.push(part);
 }
 const candidates=target.startsWith('/')?[target.replace(/^\/+/, '')]:kind==='wiki'?[target,parts.join('/')]:[parts.join('/')];
 for(const candidate of candidates){
  if(paths.includes(candidate))return candidate;
  if(kind==='wiki'&&paths.includes(candidate+'.md'))return candidate+'.md';
 }
 if(kind==='wiki'&&!target.startsWith('/')&&!target.split('/').some(part=>part==='.'||part==='..')){
  const matches=paths.filter(path=>path.endsWith('/'+target)||path.endsWith('/'+target+'.md'));
  if(matches.length===1)return matches[0];
 }
 return null;
}};
