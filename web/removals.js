'use strict';
window.NeuraRemoval=(()=>{
 let plan=null,serial=0,busy=false,returnFocus=null,entries=[],forgetPlan=null,forgetSerial=0;
 const review=$('#remove-dialog'),recovery=$('#removed-dialog');
 function ready(){
  if(busy||state.remotePreview)return false;
  if(state.dirty){toast('Save your draft before removing or restoring items. Your writing is still here.');return false;}
  if(state.saving||state.selected&&!state.note){toast('Wait for the note to finish opening or saving first.');return false;}
  return true;
 }
 function returnToWorkspace(){
  if($('dialog[open]'))return;
  const target=returnFocus?.isConnected&&returnFocus.getClientRects().length?returnFocus:$('#open-command');target.focus({preventScroll:true});
 }
 async function openItem(item=window.NeuraFiles.currentItem()){
  if(!item)return toast('Choose a note or folder in the library first.');
  return open({brain:item.brain||state.brain,path:item.path,kind:item.kind});
 }
 async function openBrain(id=state.brain){
  if(!id)return toast('Choose a Brain first.');
  return open({brain:id,path:'',kind:'brain'});
 }
 async function open(item){
  if(!ready())return;
  returnFocus=document.activeElement;$('#item-dialog').close();$('#brains-dialog').close();
  const request=++serial;plan=null;
  $('#remove-title').textContent='Remove from Neura?';$('#remove-name').textContent=item.kind==='brain'?'Brain':item.path.split('/').pop();
  $('#remove-location').textContent='Checking this location…';$('#remove-counts').textContent='';$('#remove-error').hidden=true;
  $('#remove-device').checked=false;$('#remove-device').disabled=true;$('#remove-confirm').value='';$('#remove-confirm-wrap').hidden=true;
  $('#remove-submit').disabled=true;$('#remove-submit').textContent='Remove from Neura';$('#remove-submit').classList.remove('destructive');
  $('#remove-effect').textContent='Your files will stay on this device. You can bring this item back from Removed items.';
  $('#remove-reason').hidden=true;showDialog('#remove-dialog');$('#remove-cancel').focus();
  try{
   const data=await api('/api/removals/preview',item);if(request!==serial||!review.open)return;
   plan=data;$('#remove-name').textContent=data.name;$('#remove-location').textContent=data.source;
   const c=data.counts,countText=c.notes===undefined?'Contents unavailable':c.notes+' note'+(c.notes===1?'':'s')+' · '+c.files+' file'+(c.files===1?'':'s');
   $('#remove-counts').textContent=data.kind==='note'?'Note · '+data.brainName:(data.kind==='brain'?'Brain':'Folder')+' · '+countText;
   $('#remove-device').disabled=!data.canTrash;$('#remove-reason').hidden=!data.reason;$('#remove-reason').textContent=data.reason||'';updateChoice();
  }catch(error){if(request===serial&&review.open){$('#remove-error').textContent=error.message;$('#remove-error').hidden=false;}}
 }
 function updateChoice(){
  const device=$('#remove-device').checked,whole=plan?.kind==='brain';
  $('#remove-confirm-wrap').hidden=!device||!whole;$('#remove-confirm-label').textContent=whole?'Type “'+plan.name+'” to confirm':'Confirm name';
  $('#remove-title').textContent=device?'Move files to Trash?':'Remove from Neura?';
  $('#remove-submit').textContent=device?'Move files to Trash':'Remove from Neura';$('#remove-submit').classList.toggle('destructive',device);
  $('#remove-effect').textContent=device?'Files leave their current location and move to Neura Trash. Restore them from Removed items. Nothing is permanently erased.':'Your files will stay on this device. You can bring this item back from Removed items.';
  $('#remove-submit').disabled=busy||!plan||device&&(!plan.canTrash||whole&&$('#remove-confirm').value!==plan.name);
 }
 $('#remove-device').onchange=updateChoice;$('#remove-confirm').oninput=updateChoice;
 review.addEventListener('close',()=>{serial++;plan=null;returnToWorkspace();});
 review.addEventListener('cancel',e=>{if(busy)e.preventDefault();});
 async function withBusy(task){
  busy=true;const workspace=$('.workspace'),top=$('.topbar'),nav=$('.mobile-nav');workspace.inert=true;top.inert=true;nav.inert=true;
  const progress=showDialog('#removal-progress');progress.oncancel=e=>e.preventDefault();
  try{return await task();}finally{busy=false;workspace.inert=false;top.inert=false;nav.inert=false;progress.close();updateChoice();}
 }
 async function refreshWorkspace(result,restoring=false){
  const oldBrain=state.brain;
  await loadBrains();
  const affected=result.brain===oldBrain;
  if(result.kind==='brain'&&(affected||restoring)){
   closeDocumentUnsafe();state.brain=restoring?result.brain:state.brains[0]?.id||null;state.query='';state.group=null;state.folderPath='';state.recent=false;state.closed.clear();state.libraryKey=null;state.folderPolicyBrain=null;$('#search').value='';
   if(state.brain)localStorage.setItem('neura-brain',state.brain);else localStorage.removeItem('neura-brain');
  }else if(affected&&!restoring&&state.note&&(state.note.path===result.path||result.kind==='folder'&&state.note.path.startsWith(result.path+'/'))){closeDocumentUnsafe();state.libraryKey=null;}
  if(affected||result.kind==='brain'){
   await loadGraph();if(state.note&&!state.editing)renderDocument();
  }
 }
 $('#remove-form').onsubmit=async event=>{
  event.preventDefault();if(!plan||$('#remove-submit').disabled||!ready())return;
  const payload={preview:plan.id,device:$('#remove-device').checked,confirmName:$('#remove-confirm').value};let result;
  await withBusy(async()=>{
   $('#remove-error').hidden=true;
   try{
    result=await api('/api/removals',payload);await refreshWorkspace(result);review.close();
    toast(result.mode==='trash'?'Files moved to Neura Trash. Restore them in Removed items.':'Removed from Neura. Files kept on this device.');
   }catch(error){$('#remove-error').textContent=result?'Removal completed. Refresh Neura to update the view.':error.message;$('#remove-error').hidden=false;}
  });returnToWorkspace();
 };
 async function openRemoved(){
  if(!ready())return;
  returnFocus=document.activeElement;$('#brains-dialog').close();$('#item-dialog').close();
  $('#removed-filter').value='';$('#removed-error').hidden=true;$('#removed-list').replaceChildren(el('p','empty-list','Loading removed items…'));
  showDialog('#removed-dialog');$('#removed-filter').focus();
  try{const result=await api('/api/removals/list',{});entries=result.items;renderRemoved();}catch(error){$('#removed-error').textContent=error.message;$('#removed-error').hidden=false;}
 }
 function renderRemoved(){
  const list=$('#removed-list'),q=clean($('#removed-filter').value);list.replaceChildren();
  for(const entry of entries.filter(e=>clean(e.name+' '+e.path+' '+e.brainName).includes(q))){
   const row=el('div','removed-entry'),details=el('div','removed-info'),name=el('strong','',entry.name),where=el('span','',entry.kind==='brain'?'Brain':entry.brainName+' · '+(entry.path||'Brain root'));
   details.append(name,where,el('small','removed-badge',entry.mode==='trash'?'Files in Neura Trash':'Files kept on device'));
   if(entry.restoreBlocked)details.append(el('small','restore-reason',entry.restoreBlocked));
   const button=el('button','secondary','Restore');button.setAttribute('aria-label','Restore '+entry.name);button.disabled=!!entry.restoreBlocked;button.onclick=()=>restoreEntry(entry);
   const actions=el('div','removed-actions'),forget=el('button','secondary','Remove from list');
   forget.setAttribute('aria-label','Remove '+entry.name+' from list');forget.onclick=()=>reviewForget(entry);
   actions.append(button,forget);row.append(icon(entry.kind==='brain'?'brain':entry.kind==='folder'?'folder':'note'),details,actions);list.append(row);
  }
  if(!list.children.length)list.append(el('p','empty-list',entries.length?'No removed items match this name.':'Nothing here. Removed notes, folders and Brains can be restored from this space.'));
 }
 async function restoreEntry(entry){
  if(!ready())return;let result;
  await withBusy(async()=>{
   $('#removed-error').hidden=true;
   try{
    result=await api('/api/removals/restore',{id:entry.id});await refreshWorkspace(result,true);entries=entries.filter(e=>e.id!==entry.id);
    // Parent restoration changes which child entries can be restored.
    entries=(await api('/api/removals/list',{})).items;renderRemoved();
    toast(result.available?'Restored to Neura.':'Restored to Neura. The original files are currently unavailable.');
   }catch(error){$('#removed-error').textContent=result?'Restored successfully. Refresh Neura to update the view.':error.message;$('#removed-error').hidden=false;}
  });$('#removed-filter').focus();
 }
 async function reviewForget(entry){
  if(!ready())return;
  const request=++forgetSerial;forgetPlan=null;
  $('#forget-name').textContent=entry.name;$('#forget-effect').textContent='Checking this entry…';
  $('#forget-error').hidden=true;$('#forget-submit').disabled=true;
  showDialog('#forget-dialog');$('#forget-cancel').focus();
  try{
   const data=await api('/api/removals/forget/preview',{id:entry.id});
   if(request!==forgetSerial||!$('#forget-dialog').open)return;
   forgetPlan=data;
   let effect=data.kind==='brain'?'Forget this Brain registration so you can connect its folder again.':data.mode==='hidden'?'Remove this entry. Because the files are still on this device, the note or folder can appear again in a connected Brain.':'Remove this entry from the recovery list.';
   if(data.count>1)effect+=' This also removes '+(data.count-1)+' other removed '+(data.count===2?'entry':'entries')+' belonging to this Brain.';
   effect+=' No files will be deleted or moved.';
   if(data.hasTrash)effect+=' Files in Neura Trash stay there. You will receive the location of their recovery record; Restore will no longer be available here.';
   $('#forget-effect').textContent=effect;$('#forget-submit').disabled=false;
  }catch(error){if(request===forgetSerial){$('#forget-error').textContent=error.message;$('#forget-error').hidden=false;}}
 }
 $('#forget-dialog').addEventListener('close',()=>{forgetSerial++;forgetPlan=null;if(recovery.open)$('#removed-filter').focus({preventScroll:true});});
 $('#forget-dialog').addEventListener('cancel',e=>{if(busy)e.preventDefault();});
 $('#forget-form').onsubmit=async e=>{
  e.preventDefault();if(!forgetPlan||$('#forget-submit').disabled||!ready())return;
  const payload={id:forgetPlan.id,revision:forgetPlan.revision},hasTrash=forgetPlan.hasTrash;let result;
  await withBusy(async()=>{
   try{
    result=await api('/api/removals/forget',payload);await refreshWorkspace(result);
    entries=(await api('/api/removals/list',{})).items;renderRemoved();$('#forget-dialog').close();
    $('#removed-history').hidden=!hasTrash;
    $('#removed-history').textContent=hasTrash?'Files remain in Neura Trash. Recovery record: '+result.recoveryPath:'';
    toast('Removed from list. Files kept on this device.');
   }catch(error){$('#forget-error').textContent=result?'Entry removed. Refresh Neura to update the list.':error.message;$('#forget-error').hidden=false;}
  });$('#removed-filter').focus({preventScroll:true});
 };
 $('#removed-filter').oninput=renderRemoved;
 recovery.addEventListener('close',returnToWorkspace);recovery.addEventListener('cancel',e=>{if(busy)e.preventDefault();});
 recovery.addEventListener('keydown',event=>{
  if(!NeuraKeyboard.available(event)||event.shiftKey||!['ArrowUp','ArrowDown'].includes(event.key))return;
  const buttons=$$('#removed-list button:not(:disabled)');if(!buttons.length)return;
  event.preventDefault();const index=buttons.indexOf(document.activeElement);buttons[Math.max(0,Math.min(buttons.length-1,index+(event.key==='ArrowDown'?1:-1)))]?.focus();
 });
 $('#open-removed').onclick=openRemoved;$('#brains-removed').onclick=openRemoved;
 $('#item-remove').onclick=()=>{const item=window.NeuraFiles.contextItem();$('#item-dialog').close();openItem(item);};
 return {openItem,openBrain,openRemoved};
})();
