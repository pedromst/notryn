'use strict';
// This picker lists folders on the local server. Choosing never connects or edits them.
const folderBrowser={data:null,serial:0,opening:0,loading:false,timer:null};
function folderBusy(value){
 folderBrowser.loading=value;$('#folder-results').setAttribute('aria-busy',String(value));
 $$('#folder-results button').forEach(b=>b.disabled=value);
 $('#folder-parent').disabled=value||!folderBrowser.data?.parent;
 $('#folder-choose').disabled=value||!(brainAction==='create'?folderBrowser.data?.creatable:folderBrowser.data?.selectable);
 $('#folder-more').disabled=value;
}
function focusFolderResult(){
 const first=$('#folder-results button:not([disabled])');
 (first||(!$('#folder-choose').disabled?$('#folder-choose'):$('#folder-filter'))).focus();
}
function folderRow(folder){
 const button=el('button','folder-entry');button.type='button';button.tabIndex=-1;
 button.append(icon('folder'),el('span','',folder.name),icon('chevron'));button.title=folder.path;
 button.setAttribute('aria-label','Open '+folder.name);button.onclick=()=>navigateFolder(folder.path,true);return button;
}
async function loadFolders(path,query='',offset=0,focusResults=false){
 const serial=++folderBrowser.serial;folderBusy(true);$('#folder-feedback').textContent='Loading folders…';
 try{
  const data=await api('/api/folders/browse',{path,query,offset});
  if(serial!==folderBrowser.serial||!$('#folder-dialog').open)return false;
  folderBrowser.data=data;$('#folder-location').textContent=data.path;$('#folder-location').title=data.path;
  const places=$('#folder-places');places.replaceChildren();
  for(const place of data.places){const button=el('button','',place.name);button.type='button';button.setAttribute('aria-pressed',String(data.path===place.path));button.onclick=()=>navigateFolder(place.path,true);places.append(button);}
  const results=$('#folder-results');if(offset===0)results.replaceChildren();
  for(const folder of data.folders)results.append(folderRow(folder));
  const rows=[...results.querySelectorAll('button')];rows.forEach((row,i)=>row.tabIndex=i===0?0:-1);
  const allowed=brainAction==='create'?data.creatable:data.selectable;
  if(!rows.length)results.append(el('p','empty-list',query?'No matching folders.':allowed?'No subfolders. You can choose this location.':'No folders here. Choose another location.'));
  $('#folder-more').hidden=data.nextOffset===null;
  $('#folder-feedback').textContent=allowed?(data.total===1?'1 folder':data.total+' folders'):(brainAction==='create'?'Choose a writable personal location.':'Open a specific folder to use as a Brain.');
  folderBusy(false);if(focusResults)focusFolderResult();return true;
 }catch(error){
  if(serial===folderBrowser.serial){$('#folder-feedback').textContent=error.message;folderBusy(false);}
  return false;
 }finally{if(serial===folderBrowser.serial)folderBusy(false);}
}
function navigateFolder(path,focusResults=false){
 clearTimeout(folderBrowser.timer);$('#folder-filter').value='';return loadFolders(path,'',0,focusResults);
}
async function openFolderBrowser(){
 if(state.remotePreview)return;
 const opening=++folderBrowser.opening;
 const creating=brainAction==='create';
 $('#folder-dialog-title').textContent=creating?'Choose a location':'Choose a folder';
 $('#folder-dialog-title').nextElementSibling.textContent=creating?'Your new Brain will be created inside this folder.':'Open a folder, then choose it.';
 $('#folder-choose').textContent=creating?'Choose this location':'Use this folder';
 folderBrowser.data=null;$('#folder-location').textContent='';$('#folder-results').replaceChildren();$('#folder-places').replaceChildren();$('#folder-more').hidden=true;
 $('#folder-keyboard-help').textContent='↑ ↓ navigate · Enter opens · Tab to choose';
 showDialog('#folder-dialog');$('#folder-filter').focus();
 const initial=$('#brain-form-path').value.trim()||null;
 if(!await navigateFolder(initial)&&initial&&opening===folderBrowser.opening&&$('#folder-dialog').open)await navigateFolder(null);
}
function chooseFolder(){
 const data=folderBrowser.data,allowed=brainAction==='create'?data?.creatable:data?.selectable;if(!allowed||folderBrowser.loading)return;
 $('#brain-form-path').value=data.path;$('#brain-form-path').setCustomValidity('');
 if(brainAction==='connect'&&!$('#brain-form-name').value.trim()){$('#brain-form-name').value=data.name.slice(0,80);$('#brain-form-name').setCustomValidity('');}
 updateBrainForm();
 $('#brain-form-dialog .form-error').hidden=true;$('#folder-dialog').close();$('#brain-submit').focus();
}
$('#browse-folders').onclick=openFolderBrowser;$('#folder-choose').onclick=chooseFolder;
$('#folder-parent').onclick=()=>{if(folderBrowser.data?.parent)navigateFolder(folderBrowser.data.parent,true);};
$('#folder-more').onclick=()=>{const data=folderBrowser.data;if(data&&data.nextOffset!==null&&!folderBrowser.loading)loadFolders(data.path,$('#folder-filter').value,data.nextOffset);};
$('#folder-filter').oninput=()=>{
 clearTimeout(folderBrowser.timer);++folderBrowser.serial;folderBusy(true);
 folderBrowser.timer=setTimeout(()=>loadFolders(folderBrowser.data?.path||null,$('#folder-filter').value),160);
};
$('#folder-filter').onkeydown=e=>{if(NotrynKeyboard.available(e)&&!e.shiftKey&&['ArrowDown','Enter'].includes(e.key)){e.preventDefault();if(!folderBrowser.loading)focusFolderResult();}};
$('#folder-results').onfocusin=e=>{if(!e.target.matches('button'))return;$$('#folder-results button').forEach(b=>b.tabIndex=b===e.target?0:-1);};
$('#folder-results').onkeydown=e=>{
 if(!NotrynKeyboard.available(e)||e.shiftKey||!['ArrowDown','ArrowUp','ArrowRight','ArrowLeft','Home','End'].includes(e.key))return;
 const rows=$$('#folder-results button:not([disabled])'),i=rows.indexOf(e.target);if(i<0)return;e.preventDefault();
 if(e.key==='ArrowRight'){rows[i].click();return;}
 if(e.key==='ArrowLeft'){if(folderBrowser.data?.parent)navigateFolder(folderBrowser.data.parent,true);return;}
 const next=e.key==='Home'?0:e.key==='End'?rows.length-1:Math.max(0,Math.min(rows.length-1,i+(e.key==='ArrowDown'?1:-1)));rows[next].focus();
};
$('#folder-dialog').addEventListener('close',()=>{clearTimeout(folderBrowser.timer);++folderBrowser.serial;++folderBrowser.opening;folderBrowser.loading=false;});
