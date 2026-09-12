'use strict';
// Carry browser preferences across the Neura -> Notryn rename once.
try{
 for(const suffix of ['brain','interface-hints','motion','note-side','single-keys','theme','workspace','writing-mode']){
  const current='notryn-'+suffix,legacy='neura-'+suffix;
  if(localStorage.getItem(current)===null&&localStorage.getItem(legacy)!==null)localStorage.setItem(current,localStorage.getItem(legacy));
 }
}catch{}
// Restore workspace hints before paint, independently of keyboard bindings.
try{document.documentElement.dataset.interfaceHints=localStorage.getItem('notryn-interface-hints')==='off'?'off':'on';}catch{}
// Runs before paint so a saved light theme never flashes a dark workspace.
window.NotrynThemes=(()=>{
 const presets=[
  {id:'glass',name:'Glass',description:'Quiet light in a deep blue space.',bg:'#070e18',panel:'#101e2a',text:'#e3eff0',accent:'#b4ebd9',secondary:'#95bee6',colors:['#aeeed8','#b8c4ef','#e0c49c','#a7d9ef','#d3dfb0','#dcbcd9']},
  {id:'daylight',name:'Daylight',description:'Frosted glass. A clear place to write.',bg:'#edf1ee',panel:'#fcfdf9',text:'#213a3c',accent:'#217564',secondary:'#416d9c',colors:['#287867','#6668a1','#9c6831','#376f97','#647830','#a05d7c']},
  {id:'matrix',name:'Matrix',description:'Phosphor green. Focus after dark.',bg:'#050c08',panel:'#0d1911',text:'#d5f3dc',accent:'#81ef9c',secondary:'#37a862',colors:['#8cf7a6','#54d785','#bce68b','#52bfa8','#b3f1c1','#80b780']},
  {id:'jarvis',name:'Jarvis',description:'Cyan telemetry around a calm reactor core.',bg:'#02070d',panel:'#071923',text:'#d9f7ff',accent:'#48dfff',secondary:'#208acb',colors:['#48dfff','#67aef4','#75ead7','#b4dcff','#58b5d4','#91cfff']},
  {id:'command',name:'Command',description:'Amber signals. Precise, structured panels.',bg:'#111318',panel:'#1c2027',text:'#eeeae1',accent:'#efbb71',secondary:'#8fa9bf',colors:['#efbb71','#8fb5ce','#d79171','#cbd7da','#c1c791','#b3a3ce']},
  {id:'dusk',name:'Dusk',description:'Warm ink for slower evenings.',bg:'#19141a',panel:'#261f29',text:'#efe3e5',accent:'#e3b3c5',secondary:'#a8a3d1',colors:['#e3b3c5','#b8addb','#ddb991','#9fc7c5','#b9c79a','#c99fb8']}
 ];
 const hex=v=>/^#[0-9a-f]{6}$/i.test(v),rgb=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));
 const mix=(a,b,t)=>'#'+rgb(a).map((v,i)=>Math.round(v+(rgb(b)[i]-v)*t).toString(16).padStart(2,'0')).join('');
 const luminance=h=>rgb(h).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
 const contrast=(a,b)=>(Math.max(luminance(a),luminance(b))+.05)/(Math.min(luminance(a),luminance(b))+.05);
 function readable(color,bg,min=4.5){const end=luminance(bg)>.35?'#111111':'#f5ffff';for(let t=0;t<=1;t+=.025){const c=mix(color,end,t);if(contrast(c,bg)>=min)return c;}return end;}
 function build(theme){
  const {bg,panel}=theme,light=theme.mode?theme.mode==='light':luminance(bg)>.4;
  const text=readable(theme.text,panel,7),accent=readable(theme.accent,panel),muted=readable(mix(panel,text,.65),panel),secondary=theme.secondary||theme.accent;
  const line=mix(panel,text,light?.20:.17),soft=mix(panel,theme.accent,light?.085:.065),field=mix(bg,panel,.28),strong=mix(panel,text,.075);
  const primary=theme.accent,onAccent=contrast(primary,'#111111')>contrast(primary,'#ffffff')?'#111111':'#ffffff';
  const vars={bg,panel,text,accent,muted,line,amber:readable(light?'#93600c':'#e5bc83',panel),
   'theme-secondary':secondary,'theme-soft':soft,'theme-field':field,'theme-strong':strong,'theme-primary':primary,'theme-on-accent':onAccent,
   'theme-on-selection':contrast(primary,'#000000')>contrast(primary,'#ffffff')?'#000000':'#ffffff',
   'theme-ink':mix(text,panel,.10),'theme-edge':mix(panel,text,light?.36:.27),'theme-error':readable(light?'#a23e31':'#efb4a2',panel),
   'theme-shadow':light?'#1b343c13':'#00000040','theme-backdrop':light?'#34454142':'#02060ca0',
   'theme-wash':secondary+(light?'0c':'16'),'theme-tint':theme.accent+(light?'07':'08'),
   glass:`linear-gradient(135deg,${text}09,${text}00 55%,${theme.accent}04),${panel}de`,
   'glass-edge':`inset 0 1px 0 ${text}0e,0 12px 40px ${light?'#2137390a':'#00000022'}`,
   'theme-radius':theme.id==='command'?'7px':theme.id==='jarvis'?'10px':'17px'};
  const mesh=light?mix(accent,text,.25):mix(secondary,theme.accent,.45);
  const selectedLabel=primary+'d6',linkedLabel=mix(panel,primary,.28)+'cc';
  // Translucent fills show the cortex underneath. Choose ink against the
  // composited color, rather than the opaque accent swatch.
  const selectedBase=mix(bg,primary,214/255),linkedBase=mix(bg,linkedLabel,.8);
  const selectedInk=contrast(selectedBase,'#000000')>contrast(selectedBase,'#ffffff')?'#000000':'#ffffff';
  const graph={colors:theme.colors,mesh,light,accent:theme.accent,secondary,rgb:rgb(mesh).join(','),pulse:light?accent:mix(theme.accent,'#ffffff',.6),
   labelSelected:selectedLabel,labelSelectedText:selectedInk,labelLinked:linkedLabel,labelLinkedText:readable(text,linkedBase,7),
   label:panel+(light?'f5':'e8'),labelActive:soft+'f5',labelText:text,labelMuted:mix(text,panel,.14),line,pearl:light?mix(theme.accent,'#ffffff',.5):'#f0ffff'};
  return {vars,graph,light};
 }
 let saved=null;try{saved=localStorage.getItem('notryn-theme');}catch{}
 let choice=presets.some(t=>t.id===saved)||saved==='omarchy'?saved:'glass',current;
 function apply(theme){
  current=theme;const data=build(theme),root=document.documentElement;
  Object.entries(data.vars).forEach(([k,v])=>root.style.setProperty('--'+k,v));
  root.dataset.theme=theme.id;root.dataset.colorMode=data.light?'light':'dark';root.style.colorScheme=data.light?'light':'dark';
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content',theme.bg);
  document.dispatchEvent(new CustomEvent('notryn-themechange',{detail:data.graph}));
 }
 function choose(id,omarchy){
  choice=id;saved=id;try{localStorage.setItem('notryn-theme',id);}catch{}
  apply(id==='omarchy'&&omarchy?omarchy:presets.find(t=>t.id===id)||presets[0]);
 }
 function fromOmarchy(data){
  const p=data?.palette;if(!data?.available||!p||!hex(p.background)||!hex(p.foreground)||!hex(p.accent))return null;
  const color=(key,fallback)=>hex(p[key])?p[key]:fallback,light=p.mode?p.mode==='light':luminance(p.background)>.4;
  const colors=['green','blue','yellow','cyan','magenta','red'].map((k,i)=>readable(color(k,color('color'+[2,4,3,6,5,1][i],p.accent)),p.background,3));
  return {id:'omarchy',name:String(data.name||'Omarchy'),bg:p.background,panel:mix(p.background,p.foreground,light?.035:.045),text:p.foreground,accent:p.accent,secondary:color('cyan',p.accent),colors,mode:p.mode};
 }
 // Omarchy follows its live palette after the local bridge responds.
 apply(presets.find(t=>t.id===choice)||presets[0]);
 return {presets,choose,apply,fromOmarchy,build,get choice(){return choice;},get current(){return current;},get firstVisit(){return !saved;}};
})();
