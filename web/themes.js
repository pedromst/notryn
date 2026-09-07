'use strict';
(()=>{
 const themes=window.NeuraThemes,dialog=$('#theme-dialog'),list=$('#theme-list');
 let index=0,origin=null,omarchy=null,syncing=false,lastPalette='',initial=true,typeahead='',typeTimer;
 const options=()=>[...themes.presets,{id:'omarchy',name:'Follow Omarchy',description:omarchy?'Live palette · '+omarchy.name:'Use your Linux desktop colors automatically.'}];
 function status(){
  $('#theme-status').textContent=themes.choice==='omarchy'?(omarchy?'Following '+omarchy.name+'. Desktop changes appear automatically.':'Omarchy is unavailable. Glass is active until a desktop palette is found.'):(omarchy?'Omarchy detected: '+omarchy.name+'. Choose Follow Omarchy to keep them in sync.':'Your choice stays on this browser. Omarchy sync is available when installed.');
 }
 function highlight(){
  [...list.children].forEach((row,i)=>row.setAttribute('aria-selected',String(i===index)));
  const row=list.children[index];if(row){list.setAttribute('aria-activedescendant',row.id);row.scrollIntoView({block:'nearest'});}
 }
 function render(){
  list.replaceChildren();
  for(const item of options()){
   const row=el('div','theme-option'),mini=el('span','theme-mini'),info=el('span','theme-option-info'),swatch=item.id==='omarchy'?(omarchy||themes.presets[0]):item;
   row.id='theme-option-'+item.id;row.setAttribute('role','option');row.dataset.theme=item.id;
   mini.setAttribute('aria-hidden','true');mini.style.setProperty('--swatch-bg',swatch.bg);mini.style.setProperty('--swatch-accent',swatch.accent);mini.style.setProperty('--swatch-edge',swatch.accent+'45');
   info.append(el('strong','',item.name),el('small','',item.description));row.append(mini,info,el('span','theme-active',themes.choice===item.id?'✓':''));
   row.onclick=()=>{index=options().findIndex(t=>t.id===item.id);applySelection();};list.append(row);
  }highlight();status();
 }
 function restoreFocus(){if(origin?.isConnected)origin.focus({preventScroll:true});}
 function applySelection(){const item=options()[index];themes.choose(item.id,omarchy);dialog.close();toast(item.id==='omarchy'?(omarchy?'Following Omarchy: '+omarchy.name:'Omarchy unavailable. Using Glass until a palette is found.'):item.name+' theme applied.');}
 window.openThemes=()=>{
  if($('dialog[open]'))return;
  origin=document.activeElement;index=Math.max(0,options().findIndex(t=>t.id===themes.choice));render();dialog.showModal();list.focus({preventScroll:true});highlight();sync();
 };
 dialog.addEventListener('close',restoreFocus);
 list.addEventListener('keydown',e=>{
  if(!NeuraKeyboard.available(e)||e.shiftKey)return;
  if(['ArrowDown','ArrowUp','ArrowLeft','ArrowRight','Home','End','Enter',' '].includes(e.key)){
   e.preventDefault();e.stopPropagation();
   if(e.key==='Enter'||e.key===' '){applySelection();return;}
   const n=options().length;index=e.key==='Home'?0:e.key==='End'?n-1:(index+(['ArrowDown','ArrowRight'].includes(e.key)?1:-1)+n)%n;highlight();
  }else if(/^[a-z]$/i.test(e.key)){
   e.preventDefault();e.stopPropagation();clearTimeout(typeTimer);typeahead+=e.key.toLowerCase();typeTimer=setTimeout(()=>typeahead='',650);
   const match=options().findIndex(t=>t.name.toLowerCase().startsWith(typeahead));if(match>=0){index=match;highlight();}
  }
 });
 $('#open-themes').onclick=window.openThemes;$('#open-themes').title='Themes (T outside text fields)';
 document.addEventListener('neura-themechange',e=>{
  graph.setTheme(e.detail);
  // Updating swatches in place preserves library and legend keyboard focus.
  $$('#legend button[data-color-group]').forEach(b=>b.style.setProperty('--color',graph.color(b.dataset.colorGroup)));
  $('#open-themes').setAttribute('aria-label','Themes: '+(themes.choice==='omarchy'?'Follow Omarchy':themes.current.name));
 });
 graph.setTheme(themes.build(themes.current).graph);
 async function sync(){
  if(syncing||document.hidden)return;syncing=true;
  try{
   const data=await api('/api/theme');omarchy=themes.fromOmarchy(data);
   if(initial&&themes.firstVisit&&omarchy)themes.choose('omarchy',omarchy);
   const signature=JSON.stringify(omarchy),changed=signature!==lastPalette;
   if(themes.choice==='omarchy'&&changed)themes.apply(omarchy||themes.presets[0]);
   lastPalette=signature;if(dialog.open&&changed)render();
  }catch{omarchy=null;if(themes.choice==='omarchy'){$('#theme-status').textContent='Desktop sync is unavailable. Your current colors are kept.';}}
  finally{syncing=false;initial=false;}
 }
 // Never install hooks or change the desktop: read its tiny active palette.
 setInterval(()=>{if(themes.choice==='omarchy'||dialog.open)sync();},2000);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden&&themes.choice==='omarchy')sync();});
 window.addEventListener('focus',()=>{if(themes.choice==='omarchy')sync();});sync();
 window.askTheme=async question=>{
  const q=question.toLowerCase().trim().replace(/[.!?]+$/,'').replace(/^please\s+/,'').replace(/^(?:can|could|would) you\s+/,'');
  if(/^(?:(?:show|open|choose|change|switch)\s+(?:the\s+)?(?:themes?|appearance)|what themes(?: are available)?)$/.test(q)){window.openThemes();say('Choose a theme with the arrow keys, then press Enter.');return true;}
  const match=q.match(/^(?:(?:switch|change)(?:\s+(?:the\s+)?theme)?\s+to|(?:use|set|apply)(?:\s+(?:the\s+)?theme(?:\s+to)?)?|follow)\s+(?:the\s+)?(.+?)(?:\s+theme)?$/);
  if(!match)return false;
  const name=match[1].replace(/^the\s+/,''),aliases={light:'daylight',dark:'glass','control panel':'command','command panel':'command','system':'omarchy','desktop':'omarchy','follow omarchy':'omarchy'};
  const id=aliases[name]||options().find(t=>t.id===name||t.name.toLowerCase()===name)?.id;
  if(!id)return false;
  if(id==='omarchy')await sync();themes.choose(id,omarchy);
  say(id==='omarchy'?(omarchy?'Following Omarchy: '+omarchy.name+'. I will keep the colors in sync.':'Omarchy is not detected. Glass will stay active until a desktop palette is available.'):(themes.current.name+' is now active.'));return true;
 };
})();
