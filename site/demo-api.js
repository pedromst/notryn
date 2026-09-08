'use strict';
// The real app UI talks to this in-memory sample workspace, never a local server.
(() => {
  const preferences = new Map();
  window.NotrynDemoStorage = {getItem:key=>preferences.get(key)??null,setItem:(key,value)=>preferences.set(key,String(value)),removeItem:key=>preferences.delete(key)};
  let serial=1;
  const brains=[{id:'example-brain',name:'Example Brain',root:'Demo / Example Brain',scope:'all',readOnly:false,available:true}];
  const workspaces=new Map([[brains[0].id,{notes:new Map(Object.entries(window.NOTRYN_DEMO_NOTES)),folders:new Set(['Projects','Projects/Studio','Ideas','Knowledge'])}]]);
  const originalFetch=window.fetch.bind(window);
  const clone=value=>JSON.parse(JSON.stringify(value));
  const fail=(message,status=400)=>{const error=new Error(message);error.status=status;throw error;};
  const pathOf=value=>{
    if(typeof value!=='string'||!value||value.startsWith('/')||value.split('/').some(p=>!p||p==='.'||p==='..')||/[\\\x00-\x1f]/.test(value))fail('Choose a relative path inside this demo Brain.');
    return value;
  };
  const parent=path=>path.split('/').slice(0,-1).join('/');
  function workspace(id){const brain=brains.find(b=>b.id===id);if(!brain)fail('This demo Brain is not connected.',404);return {brain,...workspaces.get(id)};}
  function graph(id){
    const {brain,notes,folders}=workspace(id),paths=[...notes.keys()].sort(),nodes=[],edges=new Map();
    for(const path of paths){
      const note=notes.get(path),title=note.content.match(/^#\s+(.+)/m)?.[1]||path.split('/').pop().slice(0,-3);
      nodes.push({id:path.slice(0,-3),path,title,folder:parent(path),group:path.includes('/')?path.split('/')[0]:'Notes',size:new TextEncoder().encode(note.content).length,updatedAt:note.updatedAt||'2026-09-08T12:00:00Z'});
      const text=note.content.replace(/^\s*(```|~~~)[\s\S]*?^\s*\1[^\n]*$/gm,'').replace(/`[^`\n]+`/g,'');
      const add=(link,kind)=>{const target=window.NotrynLinks.resolve(link,path,paths,kind);if(target&&target!==path){const [source,destination]=[path.slice(0,-3),target.slice(0,-3)].sort();edges.set(source+'\0'+destination,{source,target:destination});}};
      for(const match of text.matchAll(/\[\[([^\]|]+)(?:\|[^\]]*)?\]\]/g))add(match[1],'wiki');
      for(const match of text.matchAll(/\[[^\]\n]*\]\(([^)\n]+)\)/g))add(match[1],'markdown');
    }
    return {brain,nodes,edges:[...edges.values()],folders:[...folders].sort(),linkPaths:paths,skipped:0,loadedAt:new Date().toISOString()};
  }
  function request(url,data){
    const route=url.pathname;
    if(route==='/api/state')return {brains,token:'sample-only',version:'0.2.0-alpha.3',agent:{connected:false,mode:'local-guide'}};
    if(route==='/api/runtime')return {app:'notryn-demo',version:'0.2.0-alpha.3'};
    if(route==='/api/voice')return {available:false,local:true};
    if(route==='/api/theme')return {available:false};
    if(route==='/api/graph')return graph(url.searchParams.get('brain'));
    if(route==='/api/note'){
      const {brain,notes}=workspace(url.searchParams.get('brain')),note=notes.get(url.searchParams.get('path'));
      if(!note)fail('This sample note no longer exists.',404);return {...note,readOnly:brain.readOnly};
    }
    if(route==='/api/notes'){
      const {brain,notes,folders}=workspace(data.brain),path=pathOf(data.path),old=notes.get(path);
      if(brain.readOnly)fail('This Brain is read-only.',403);
      if(!path.endsWith('.md'))fail('Use a Markdown filename.');
      if(typeof data.content!=='string'||new TextEncoder().encode(data.content).length>1024*1024)fail('Notes must be smaller than 1 MB.');
      if(!old&&data.revision!==null||old&&data.revision!==old.revision)fail('This note changed. Reopen it before saving.',409);
      if(parent(path)&&!folders.has(parent(path)))fail('Create the destination folder first.');
      const revision='demo-'+(++serial);notes.set(path,{path,content:data.content,revision,readOnly:false,updatedAt:new Date().toISOString()});return {path,revision};
    }
    if(route==='/api/folders'){
      const {brain,notes,folders}=workspace(data.brain),path=pathOf(data.path);
      if(brain.readOnly)fail('This Brain is read-only.',403);
      if(folders.has(path)||notes.has(path))fail('This name already exists.',409);
      if(parent(path)&&!folders.has(parent(path)))fail('Create the parent folder first.');
      folders.add(path);return {path};
    }
    if(route==='/api/brains'){
      if(data.action==='access'){const {brain}=workspace(data.brain);brain.readOnly=!data.writable;return {brain};}
      if(data.action==='create'){
        const name=String(data.name||'').trim();if(!name||name.length>80)fail('Choose a name between 1 and 80 characters.');
        const brain={id:'demo-brain-'+(++serial),name,root:'Demo / '+name,scope:'all',readOnly:false,available:true};
        brains.push(brain);workspaces.set(brain.id,{notes:new Map(),folders:new Set()});return {brain,graph:graph(brain.id)};
      }
      fail('Install Notryn to connect folders from your computer. This demo uses sample notes only.');
    }
    if(route==='/api/removals/list')return {items:[]};
    if(route==='/api/notes/reveal'||route==='/api/folders/browse')fail('Computer folders are available in the installed app. These sample notes live only in this browser tab.');
    if(route.startsWith('/api/removals')||route==='/api/move')fail('Moving and removing files can be tried in the installed app. In this demo you can browse, write, create notes and folders, and follow connections.');
    fail('This device action is available in the installed app.',403);
  }
  window.fetch=async(input,options={})=>{
    const url=new URL(typeof input==='string'?input:input.url,location.href);
    if(url.origin!==location.origin) return new Response(JSON.stringify({error:'External requests are disabled in this demo.'}),{status:403,headers:{'Content-Type':'application/json'}});
    if(!url.pathname.startsWith('/api/'))return originalFetch(input,options);
    try {return new Response(JSON.stringify(clone(request(url,options.body?JSON.parse(options.body):{}))),{status:200,headers:{'Content-Type':'application/json'}});}
    catch(error){return new Response(JSON.stringify({error:error.message}),{status:error.status||400,headers:{'Content-Type':'application/json'}});}
  };
})();
