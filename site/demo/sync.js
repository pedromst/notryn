'use strict';
// GitHub Sync: one dialog for the account (once per computer) and the current Brain's repository.
window.NotrynSync=(()=>{
 const dialog=$('#sync-dialog');
 let info=null,busy=false,timer=null,seen={},afterCreate=false,editing=false,formKey=null;
 const brainSync=()=>info?.brains?.[state.brain]||null;
 function ago(iso){if(!iso)return'';const s=Math.max(0,(Date.now()-new Date(iso))/1000);if(s<45)return'just now';if(s<3600)return Math.round(s/60)+' min ago';if(s<86400)return Math.round(s/3600)+' h ago';return new Date(iso).toLocaleDateString();}
 function every(minutes){return minutes?'every '+(minutes===60?'hour':minutes+' minutes'):'when you ask';}
 function summary(sync){
  if(!sync?.enabled)return'';
  if(sync.state==='syncing')return'Syncing with '+sync.repo+'…';
  if(sync.state==='error')return sync.error;
  const at=sync.at||sync.lastSyncAt,parts=[at?'Synced '+ago(at):'Not synced yet'];
  if(sync.state==='ok'&&sync.pulled)parts.push(sync.pulled+' change'+(sync.pulled===1?'':'s')+' received');
  if(sync.conflicts?.length)parts.push(sync.conflicts.length+' GitHub cop'+(sync.conflicts.length===1?'y':'ies')+' kept');
  return parts.join(' · ')+'. Syncs '+every(sync.interval)+(sync.onOpen?' and when Notryn opens.':'.');
 }
 function indicator(){
  const button=$('#open-sync'),sync=brainSync();if(!button)return;
  button.hidden=!!state.remotePreview;
  const mode=!info?.license?.allowed&&info?.license?.paywall?'locked':!sync?.enabled?'off':sync.state==='syncing'?'syncing':sync.state==='error'?'error':'on';
  button.dataset.sync=mode;
  button.title=mode==='off'?'Sync across computers with GitHub':mode==='locked'?'GitHub Sync · unlock to use':'GitHub Sync · '+summary(sync);
  $('#brains-sync-detail').textContent=sync?.enabled?'This Brain syncs with '+sync.repo+'.':'Sync with a private GitHub repository you own.';
 }
 async function refresh(){
  if(state.remotePreview)return;
  try{info=await api('/api/sync');}catch{return;}
  for(const[id,sync]of Object.entries(info.brains)){
   // A finished sync may have changed files on disk; reuse the normal external-change check.
   if(sync.at&&seen[id]&&seen[id]!==sync.at&&id===state.brain&&sync.pulled)void refreshGraphIfChanged();
   if(sync.at)seen[id]=sync.at;
  }
  indicator();if(dialog.open&&!busy&&!editing)render();schedule();
 }
 function schedule(){clearTimeout(timer);const active=Object.values(info?.brains||{}).some(b=>b.enabled);timer=setTimeout(refresh,Object.values(info?.brains||{}).some(b=>b.state==='syncing')?3000:active?20000:120000);}
 function show(id,visible){$(id).hidden=!visible;}
 function error(message){$('#sync-error').textContent=message||'';$('#sync-error').hidden=!message;}
 function render(){
  const brain=current(),sync=brainSync(),account=info.account,git=info.git,license=info.license;
  const locked=license.paywall&&!license.allowed;
  show('#sync-locked',locked);
  if(locked){$('#sync-locked-text').textContent=license.problem||'GitHub Sync is a paid feature. Choose a plan, then paste the license key you receive by email.';const plans=$('#sync-plans');plans.replaceChildren();for(const plan of license.checkout){const a=el('a','primary sync-plan',plan.label);a.href=plan.url;a.target='_blank';a.rel='noopener noreferrer';plans.append(a);}if(!license.checkout.length)plans.append(el('p','form-help','Purchasing opens soon.'));}
  $('#sync-git').textContent=git.available?'':'Git is needed for GitHub Sync and was not found on this computer. '+git.help;
  show('#sync-git',!git.available);
  show('#sync-account-form',!account.connected);show('#sync-account-done',account.connected);
  $('#sync-account-state').textContent=account.connected?'Connected on this computer.':'Needed once on each computer.';
  $('#sync-storage').textContent='Stored in '+info.storage+' and only ever sent to GitHub. Notryn never shows it again.';
  if(account.connected)$('#sync-login').textContent='@'+account.login+' · token in '+account.storage;
  $('#sync-account-step').classList.toggle('done',account.connected);
  const disabled=locked||!git.available;
  for(const id of ['#sync-token','#sync-connect'])$(id).disabled=disabled;
  show('#sync-no-brain',!brain);show('#sync-brain-form',!!brain);
  $('#sync-brain-step').classList.toggle('waiting',!account.connected);
  $('#sync-brain-title').textContent=brain?'Choose the repository for “'+brain.name+'”':'Choose the repository';
  $('#sync-brain-state').textContent=!brain?'':brain.readOnly?'This Brain is read-only. Allow reading and writing in Brain access to sync it.':sync?.enabled?'Synced with '+sync.repo+(sync.private===false?' (public)':'')+'.':'Use the same repository on every computer.';
  // Refill the form only when the Brain or its saved settings change, never over typing.
  const key=brain?[brain.id,sync?.enabled,sync?.repo,sync?.interval,sync?.onOpen].join('|'):'';
  if(brain&&key!==formKey){formKey=key;$('#sync-repo').value=sync?.repo||'';$('#sync-interval').value=String(sync?.enabled?sync.interval:10);$('#sync-on-open').checked=sync?.enabled?!!sync.onOpen:true;}
  $('#sync-repo').disabled=disabled||!brain||brain.readOnly||!account.connected||!!sync?.enabled;
  for(const id of ['#sync-interval','#sync-on-open'])$(id).disabled=disabled||!brain||brain.readOnly||!account.connected;
  show('#sync-status',!!sync?.enabled);
  if(sync?.enabled){$('#sync-status-text').textContent=summary(sync);$('#sync-status-dot').dataset.state=sync.state||'idle';}
  const save=$('#sync-save');
  save.hidden=!brain||!account.connected||locked;
  save.textContent=sync?.enabled?(sync.state==='syncing'?'Syncing…':'Sync now'):'Start syncing';
  save.disabled=disabled||brain?.readOnly||sync?.state==='syncing'||busy;
 }
 async function open(){
  if(state.remotePreview)return toast('GitHub Sync is managed on the computer that owns the Brain.');
  $('#brains-dialog').close();error('');showDialog('#sync-dialog');
  if(!info)$('#sync-status-text').textContent='Checking…';
  await refresh();if(!info)return error('The local app did not respond. Check that the server is running.');
  render();(info.account.connected?($('#sync-save').hidden||$('#sync-save').disabled?$('#sync-dialog [data-close]'):($('#sync-repo').disabled?$('#sync-save'):$('#sync-repo'))):$('#sync-token')).focus();
 }
 async function run(action){
  if(busy)return;busy=true;error('');render();
  try{return await action();}
  catch(e){error(e.message);await refresh();}
  finally{busy=false;if(info)render();}
 }
 $('#sync-account-form').onsubmit=e=>{e.preventDefault();run(async()=>{const token=$('#sync-token').value.trim();if(!token)throw Error('Paste the token you created on GitHub.');$('#sync-connect').textContent='Checking…';try{info=await api('/api/sync/account',{action:'connect',token});}finally{$('#sync-connect').textContent='Connect';}$('#sync-token').value='';render();toast('GitHub connected as @'+info.account.login+'.');$('#sync-repo').focus();});};
 $('#sync-disconnect').onclick=()=>run(async()=>{info=await api('/api/sync/account',{action:'disconnect'});render();toast('GitHub disconnected. The token was deleted from this computer.');});
 $('#sync-brain-form').onsubmit=e=>{e.preventDefault();$('#sync-save').click();};
 $('#sync-repo').oninput=()=>{$('#sync-public-wrap').hidden=true;$('#sync-public').checked=false;};
 async function saveSchedule(){const sync=brainSync();if(!sync?.enabled)return;await run(async()=>{info=await api('/api/sync/brain',{action:'schedule',brain:state.brain,interval:Number($('#sync-interval').value),onOpen:$('#sync-on-open').checked});indicator();toast('Sync schedule saved.');});}
 $('#sync-interval').onchange=saveSchedule;$('#sync-on-open').onchange=saveSchedule;
 function finished(result){
  const parts=['Synced'];if(result.pulled)parts.push(result.pulled+' change'+(result.pulled===1?'':'s')+' received');if(result.pushed)parts.push('changes sent');
  if(result.conflicts?.length)parts.push(result.conflicts.length+' conflict'+(result.conflicts.length===1?'':'s')+' kept as GitHub copies');
  toast(parts.join(' · ')+'.');if(result.pulled)void refreshGraphIfChanged();
 }
 const unsaved=()=>state.dirty||state.saving;
 $('#sync-save').onclick=()=>run(async()=>{
  const sync=brainSync();let result;
  if(unsaved())throw Error('Save the note you are editing first, then sync.');
  if(sync?.enabled&&$('#sync-public').checked)result=await api('/api/sync/brain',{action:'configure',brain:state.brain,repo:sync.repo,interval:sync.interval,onOpen:!!sync.onOpen,confirmPublic:true});
  else if(sync?.enabled){try{result=await api('/api/sync/run',{brain:state.brain});}catch(e){if(e.status===428){$('#sync-public-wrap').hidden=false;$('#sync-public').focus();}throw e;}}
  else{
   const repo=$('#sync-repo').value.trim();if(!repo){$('#sync-repo').focus();throw Error('Enter your repository, for example ana/notryn-brain.');}
   $('#sync-save').textContent='Connecting…';
   try{result=await api('/api/sync/brain',{action:'configure',brain:state.brain,repo,interval:Number($('#sync-interval').value),onOpen:$('#sync-on-open').checked,confirmPublic:$('#sync-public').checked});}
   catch(e){if(e.status===428){$('#sync-public-wrap').hidden=false;$('#sync-public').focus();}throw e;}
   await loadBrains();
  }
  $('#sync-public-wrap').hidden=true;$('#sync-public').checked=false;
  seen[state.brain]=result.at;finished(result);await refresh();
 });
 // Stopping asks for a second click instead of a native dialog.
 let stopArmed=null;
 $('#sync-stop').onclick=()=>{
  if(!stopArmed){$('#sync-stop').textContent='Click again to stop';stopArmed=setTimeout(()=>{stopArmed=null;$('#sync-stop').textContent='Stop syncing';},4000);return;}
  clearTimeout(stopArmed);stopArmed=null;$('#sync-stop').textContent='Stop syncing';
  run(async()=>{info=await api('/api/sync/brain',{action:'stop',brain:state.brain});await loadBrains();render();indicator();toast('Sync stopped. Your notes stay in this folder and on GitHub.');});
 };
 $('#sync-license-form').onsubmit=e=>{e.preventDefault();run(async()=>{info=await api('/api/license',{action:'activate',key:$('#sync-license').value.trim()});$('#sync-license').value='';render();indicator();toast('GitHub Sync unlocked. Thank you!');});};
 $('#sync-create-brain').onclick=()=>{afterCreate=true;dialog.close();openBrainForm('create');};
 document.addEventListener('notryn-brainready',()=>{if(afterCreate){afterCreate=false;open();}});
 $('#brain-form-dialog').addEventListener('close',()=>{if(afterCreate&&!state.brains.length)afterCreate=false;});
 for(const id of ['#sync-repo','#sync-token','#sync-license']){$(id).addEventListener('focus',()=>editing=true);$(id).addEventListener('blur',()=>editing=false);}
 $('#open-sync').onclick=open;$('#brains-sync').onclick=open;$('#welcome-sync').onclick=open;
 async function syncNow(){if(state.remotePreview)return;if(!info)await refresh();const sync=brainSync();if(!sync?.enabled)return open();if(unsaved())return toast('Save the note you are editing first, then sync.');toast('Syncing with GitHub…');try{const result=await api('/api/sync/run',{brain:state.brain});seen[state.brain]=result.at;finished(result);}catch(e){toast(e.message);}await refresh();}
 document.addEventListener('notryn-brainchange',indicator);
 setTimeout(refresh,600);
 return {open,syncNow,refresh};
})();
