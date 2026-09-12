import {DOMSerializer} from 'prosemirror-model';
import {EditorState,TextSelection,NodeSelection,Plugin} from 'prosemirror-state';
import {EditorView} from 'prosemirror-view';
import {baseKeymap,chainCommands,newlineInCode,createParagraphNear,liftEmptyBlock,splitBlock,toggleMark,setBlockType,wrapIn,lift} from 'prosemirror-commands';
import {history,undo,redo,undoDepth,redoDepth} from 'prosemirror-history';
import {keymap} from 'prosemirror-keymap';
import {wrapInList,splitListItem,liftListItem} from 'prosemirror-schema-list';
import {schema,createModel,parseSource,safeLink,findLinkNotes,noteFilename} from './editor-model.mjs';

function rawContent(node,editing=false){
 const box=document.createElement('div');box.className='preserved-block';
 if(editing){const label=document.createElement('span');label.className='preserved-label';label.textContent='Embedded content · Edit in Markdown';box.append(label);}
 const lines=node.attrs.raw.trim().split(/\r?\n/);
 if(lines.length>1&&lines[0].trim().startsWith('|')&&/^\s*\|?[\s:|-]+\|\s*$/.test(lines[1])){
  const table=document.createElement('table');
  for(const [i,line] of lines.entries()){
   if(i===1||!line.trim().startsWith('|'))continue;
   const row=document.createElement('tr');
   for(const value of line.trim().replace(/^\||\|$/g,'').split('|')){
    const cell=document.createElement(i===0?'th':'td'),block=parseSource(value.trim()).doc.firstChild;
    if(block.type.name==='paragraph')cell.append(DOMSerializer.fromSchema(schema).serializeFragment(block.content));else cell.textContent=value.trim();row.append(cell);
   }table.append(row);
  }box.append(table);
 }else{const pre=document.createElement('pre');pre.textContent=node.attrs.raw;box.append(pre);}
 return box;
}
function render(source,stripTitle=false){
 const result=document.createElement('div');result.className='markdown';
 const doc=parseSource(source).doc;
 doc.forEach((node,offset,index)=>{if(stripTitle&&index===0&&node.type.name==='heading'&&node.attrs.level===1)return;result.append(node.type.name==='raw_block'?rawContent(node):DOMSerializer.fromSchema(schema).serializeNode(node));});
 return result;
}

function create({mount,toolbar,formatButton,linkDialog,onChange,getNotes,onRaw,onLeave,onOpenNote}){
 const model=createModel(),q=s=>toolbar.querySelector(s);
 let pinned=false,visible=false,linkBookmark=null,lastFocus=false,positionFrame=0,styleBookmark=null;
 const bindings=Object.fromEntries(Object.entries(baseKeymap).filter(([k])=>['Enter','Backspace','Delete'].includes(k)));
 bindings.Enter=chainCommands(newlineInCode,createParagraphNear,liftEmptyBlock,splitListItem(schema.nodes.list_item),splitBlock);
 bindings['Shift-Enter']=(state,dispatch)=>{if(dispatch)dispatch(state.tr.replaceSelectionWith(schema.nodes.hard_break.create()).scrollIntoView());return true;};
 // Standard text undo/redo, scoped to this editable field. Never registered globally.
 bindings['Mod-z']=undo;bindings['Shift-Mod-z']=redo;
 bindings['Mod-y']=redo;
 bindings['Mod-b']=toggleMark(schema.marks.strong);
 bindings['Mod-i']=toggleMark(schema.marks.em);
 bindings['Mod-k']=()=>{openLink();return true;};
 bindings['Mod-Shift-x']=toggleMark(schema.marks.strike);
 const plugins=[history(),keymap(bindings),new Plugin({props:{handleDOMEvents:{
  focus(){lastFocus=true;styleBookmark=null;queueMicrotask(updateTools);return false;},
  blur(){queueMicrotask(()=>{lastFocus=false;updateTools();});return false;},
  click(editor,event){
   const link=event.target.closest?.('.note-link[data-note-target]');if(!link||!mount.contains(link))return false;
   const nodePos=editor.posAtDOM(link,0),node=editor.state.doc.nodeAt(nodePos);if(node?.type.name!=='wiki_link')return false;
   event.preventDefault();editor.dispatch(editor.state.tr.setSelection(NodeSelection.create(editor.state.doc,nodePos)));openLink();return true;
  }
 }}})];
 const view=new EditorView(mount,{
  state:EditorState.create({schema,doc:model.doc,plugins}),
  attributes:{role:'textbox','aria-label':'Write note','aria-multiline':'true','aria-describedby':'visual-writing-help',spellcheck:'true'},
  editable:()=>visible,
  nodeViews:{raw_block:node=>{const dom=rawContent(node,true);dom.contentEditable='false';return {dom};}},
  dispatchTransaction(tr){view.updateState(view.state.apply(tr));if(tr.docChanged)onChange(model.serialize(view.state.doc));updateTools();},
  handleClickOn(view,pos,node,nodePos,event,direct){
   if(direct&&node.type.name==='raw_block'){onRaw();return true;}
   return false;
  },
  handleKeyDown(view,event){
   // The app's Escape route also leaves contenteditable without changing its draft.
   if(event.key==='Escape'&&!event.ctrlKey&&!event.metaKey&&!event.altKey&&!event.shiftKey&&!event.isComposing){event.preventDefault();pinned=false;toolbar.hidden=true;onLeave();return true;}
   return false;
  }
 });
 function activeMark(name){const {from,to,empty,$from}=view.state.selection;return empty?schema.marks[name].isInSet(view.state.storedMarks||$from.marks()):view.state.doc.rangeHasMark(from,to,schema.marks[name]);}
 function positionTools(){
  positionFrame=0;if(toolbar.hidden||styleBookmark)return;
  let rect;
  try{rect=pinned?formatButton.getBoundingClientRect():view.coordsAtPos(view.state.selection.from);}catch{return;}
  const bounds=mount.getBoundingClientRect();
  if(!pinned&&(rect.bottom<bounds.top||rect.top>bounds.bottom)){toolbar.hidden=true;return;}
  const width=toolbar.offsetWidth,height=toolbar.offsetHeight;
  toolbar.style.left=Math.max(8,Math.min(window.innerWidth-width-8,pinned?rect.left:rect.left-width/2))+'px';
  toolbar.style.top=Math.max(8,Math.min(window.innerHeight-height-8,pinned?rect.bottom+8:rect.top-height-10))+'px';
 }
 function updateTools(){
  const controls=toolbar.contains(document.activeElement);
  const selected=!view.state.selection.empty&&view.state.selection instanceof TextSelection;
  toolbar.hidden=!visible||!!document.querySelector('dialog[open]')||(!pinned&&!styleBookmark&&!(selected&&(view.hasFocus()||lastFocus||controls)));
  formatButton.setAttribute('aria-expanded',String(!toolbar.hidden));
  if(toolbar.hidden)return;
  const parent=view.state.selection.$from.parent;
  // A native select may temporarily focus the document body while its menu opens.
  // Keep its pending value and position until the choice is committed or cancelled.
  if(!styleBookmark)q('select').value=parent.type.name==='heading'?'h'+parent.attrs.level:parent.type.name==='code_block'?'code':'text';
  for(const name of ['strong','em','strike'])q('[data-format="'+name+'"]').setAttribute('aria-pressed',String(!!activeMark(name)));
  q('[data-format="undo"]').disabled=!undoDepth(view.state);q('[data-format="redo"]').disabled=!redoDepth(view.state);
  cancelAnimationFrame(positionFrame);positionFrame=requestAnimationFrame(positionTools);
 }
 function command(fn){fn(view.state,view.dispatch,view);view.focus();updateTools();}
 function inAncestor(name){const {$from}=view.state.selection;for(let d=$from.depth;d>0;d--)if($from.node(d).type.name===name)return true;return false;}
 const commandMap={strong:()=>toggleMark(schema.marks.strong),em:()=>toggleMark(schema.marks.em),strike:()=>toggleMark(schema.marks.strike),undo:()=>undo,redo:()=>redo,
  bullet:()=>inAncestor('bullet_list')?liftListItem(schema.nodes.list_item):wrapInList(schema.nodes.bullet_list),
  ordered:()=>inAncestor('ordered_list')?liftListItem(schema.nodes.list_item):wrapInList(schema.nodes.ordered_list)};
 toolbar.addEventListener('mousedown',e=>{if(e.target.closest('button'))e.preventDefault();});
 function beginStyleChoice(){if(!styleBookmark){positionTools();styleBookmark=view.state.selection.getBookmark();}}
 q('select').addEventListener('pointerdown',beginStyleChoice);
 q('select').addEventListener('focus',beginStyleChoice);
 toolbar.addEventListener('focusout',()=>queueMicrotask(()=>{
  const active=document.activeElement;
  if(active!==document.body&&!toolbar.contains(active)&&!mount.contains(active)){styleBookmark=null;updateTools();}
 }));
 toolbar.addEventListener('click',e=>{const action=e.target.closest('[data-format]')?.dataset.format;if(!action)return;if(action==='link')openLink();else command(commandMap[action]());});
 q('select').onchange=e=>{
  const value=e.target.value;
  const bookmark=styleBookmark;styleBookmark=null;
  if(bookmark)view.dispatch(view.state.tr.setSelection(bookmark.resolve(view.state.doc)));
  command(value==='quote'?wrapIn(schema.nodes.blockquote):value==='code'?setBlockType(schema.nodes.code_block):setBlockType(value==='text'?schema.nodes.paragraph:schema.nodes.heading,value==='text'?null:{level:Number(value.slice(1))}));
 };
 toolbar.addEventListener('keydown',e=>{
  if(e.ctrlKey||e.metaKey||e.altKey||e.isComposing)return;
  if(e.key==='Escape'){e.preventDefault();e.stopPropagation();styleBookmark=null;pinned=false;toolbar.hidden=true;view.focus();}
 });
 formatButton.onclick=()=>{pinned=!pinned;updateTools();if(pinned)q('select').focus({preventScroll:true});else view.focus();};
 document.addEventListener('pointerdown',e=>{
  if(!toolbar.contains(e.target))styleBookmark=null;
  if(!toolbar.contains(e.target)&&!mount.contains(e.target)&&!formatButton.contains(e.target)){pinned=false;updateTools();}
 });
 mount.addEventListener('scroll',()=>{cancelAnimationFrame(positionFrame);positionFrame=requestAnimationFrame(positionTools);});
 window.addEventListener('resize',updateTools);
 // Selection is kept in editor state while the dialog takes keyboard focus.
 const address=linkDialog.querySelector('#link-address'),label=linkDialog.querySelector('#link-label'),results=linkDialog.querySelector('#link-notes'),error=linkDialog.querySelector('#link-error'),openNoteButton=linkDialog.querySelector('#open-link-note'),submitButton=linkDialog.querySelector('button[type="submit"]');
 let editingWiki=false;
 function selectedWiki(){const s=view.state.selection;return s instanceof NodeSelection&&s.node.type.name==='wiki_link'?s.node:null;}
 function visibleWikiLabel(node){return node.attrs.label||node.attrs.target.split('/').pop();}
 function exactNote(value){
  const term=String(value||'').trim().toLowerCase(),matches=getNotes().filter(note=>{
   const file=noteFilename(note).toLowerCase(),stem=file.replace(/\.md$/i,'');
   return [note.id,note.path,file,stem].some(candidate=>String(candidate).toLowerCase()===term);
  });
  return matches.length===1?matches[0]:null;
 }
 function noteResults(){
  const term=address.value.trim()||(editingWiki?'':label.value.trim());results.replaceChildren();
  for(const note of findLinkNotes(getNotes(),term)){
   const button=document.createElement('button'),file=document.createElement('strong'),detail=document.createElement('small');
   button.type='button';button.className='link-note';file.className='link-note-file';file.textContent=noteFilename(note);detail.textContent=note.title+' · '+note.path;button.append(file,detail);button.title=note.title+' · '+note.path;
   button.onclick=()=>{
    restoreLinkSelection();const text=label.value.trim()||note.title;
    view.dispatch(view.state.tr.replaceSelectionWith(schema.nodes.wiki_link.create({target:note.id,label:text})).scrollIntoView());linkDialog.close();
   };results.append(button);
  }
  results.hidden=!results.children.length;
 }
 function restoreLinkSelection(){if(linkBookmark)view.dispatch(view.state.tr.setSelection(linkBookmark.resolve(view.state.doc)));}
 function openLink(){
  let s=view.state.selection;
  const wiki=selectedWiki();
  const existing=s.$from.marks().find(m=>m.type===schema.marks.link)||s.$from.nodeAfter?.marks.find(m=>m.type===schema.marks.link);
  if(s.empty&&existing){
   let start=s.from,end=s.to,pos=s.$from.start();
   s.$from.parent.forEach(node=>{if(node.marks.some(m=>m.eq(existing))&&pos<=end&&pos+node.nodeSize>=start){start=Math.min(start,pos);end=Math.max(end,pos+node.nodeSize);}pos+=node.nodeSize;});
   view.dispatch(view.state.tr.setSelection(TextSelection.create(view.state.doc,start,end)));s=view.state.selection;
  }
  linkBookmark=s.getBookmark();
  editingWiki=!!wiki;label.value=wiki?visibleWikiLabel(wiki):view.state.doc.textBetween(s.from,s.to,' ',' ')||'';address.value=wiki?.attrs.target||existing?.attrs.href||'';error.hidden=true;
  linkDialog.querySelector('#link-title').textContent=wiki||existing?'Edit link':'Add a link';submitButton.textContent=wiki||existing?'Change link':'Apply link';openNoteButton.hidden=!wiki;linkDialog.querySelector('#remove-link').hidden=!wiki&&!existing&&!view.state.doc.rangeHasMark(s.from,s.to,schema.marks.link);
  pinned=false;toolbar.hidden=true;noteResults();linkDialog.showModal();address.focus();
 }
 address.oninput=()=>{error.hidden=true;noteResults();};label.oninput=()=>{if(!address.value.trim())noteResults();};
 address.onkeydown=e=>{if(!e.ctrlKey&&!e.metaKey&&!e.altKey&&!e.isComposing&&e.key==='ArrowDown'&&results.firstChild){e.preventDefault();results.firstChild.focus();}};
 results.onkeydown=e=>{if(e.ctrlKey||e.metaKey||e.altKey||e.isComposing||e.shiftKey)return;const rows=[...results.children],i=rows.indexOf(document.activeElement);if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();rows[(i+(e.key==='ArrowDown'?1:-1)+rows.length)%rows.length]?.focus();}};
 linkDialog.querySelector('form').onsubmit=e=>{
  e.preventDefault();const note=exactNote(address.value);
  if(note){restoreLinkSelection();view.dispatch(view.state.tr.replaceSelectionWith(schema.nodes.wiki_link.create({target:note.id,label:label.value.trim()||note.title})).scrollIntoView());linkDialog.close();return;}
  const href=safeLink(address.value);
  if(!href){error.textContent='Enter a complete web address, or choose a note below.';error.hidden=false;return;}
  restoreLinkSelection();const {from,to,empty}=view.state.selection,mark=schema.marks.link.create({href});let tr=view.state.tr;
  if(empty||label.value!==view.state.doc.textBetween(from,to,' ',' '))tr=tr.replaceSelectionWith(schema.text(label.value.trim()||href,[mark]),false);
  else tr=tr.addMark(from,to,mark);
  view.dispatch(tr.scrollIntoView());linkDialog.close();
 };
 linkDialog.querySelector('#remove-link').onclick=()=>{restoreLinkSelection();const {from,to,$from}=view.state.selection;
  const wiki=selectedWiki();if(wiki){view.dispatch(view.state.tr.replaceSelectionWith(schema.text(visibleWikiLabel(wiki)),false).scrollIntoView());linkDialog.close();return;}
  let start=from,end=to;if(from===to){const parent=$from.parent,offset=$from.parentOffset;let pos=0;parent.forEach(n=>{if(pos<=offset&&pos+n.nodeSize>=offset&&n.marks.some(m=>m.type===schema.marks.link)){start=$from.start()+pos;end=start+n.nodeSize;}pos+=n.nodeSize;});}
  view.dispatch(view.state.tr.removeMark(start,end,schema.marks.link));linkDialog.close();
 };
 openNoteButton.onclick=()=>{const wiki=selectedWiki();if(!wiki)return;const target=wiki.attrs.target;linkDialog.close();onOpenNote?.(target);};
 linkDialog.addEventListener('close',()=>{linkBookmark=null;editingWiki=false;view.focus();updateTools();});
 return {
  load(source){styleBookmark=null;view.updateState(EditorState.create({schema,doc:model.load(source),plugins}));pinned=false;updateTools();},
  setVisible(value){visible=value;mount.hidden=!value;view.setProps({editable:()=>visible});if(!value){pinned=false;styleBookmark=null;}updateTools();},
  focus(end=false){if(end){let tr=view.state.tr;if(tr.doc.lastChild?.type.name==='heading')tr=tr.insert(tr.doc.content.size,schema.nodes.paragraph.create());view.dispatch(tr.setSelection(TextSelection.atEnd(tr.doc)));}view.focus();},
  get dom(){return view.dom;},
  bookmark:()=>view.state.selection.getBookmark(),
  restore(bookmark){view.dispatch(view.state.tr.setSelection(bookmark.resolve(view.state.doc)));view.focus();},
  showTools(){if(visible){pinned=true;updateTools();q('select').focus();}},
  format(action){
   if(!visible)return;
   if(action==='link'){openLink();return;}
   if(commandMap[action]){command(commandMap[action]());return;}
   if(action==='inline-code'){command(toggleMark(schema.marks.code));return;}
   if(action==='quote'){command(inAncestor('blockquote')?lift:wrapIn(schema.nodes.blockquote));return;}
   if(action==='code'){command(setBlockType(schema.nodes.code_block));return;}
   if(action==='text'){command(setBlockType(schema.nodes.paragraph));return;}
   if(/^h[1-6]$/.test(action))command(setBlockType(schema.nodes.heading,{level:Number(action.slice(1))}));
  },
  render
 };
}
window.NotrynRichText={create,render};
