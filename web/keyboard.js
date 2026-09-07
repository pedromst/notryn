'use strict';
// Global letter bindings preserve system chords. The note editor opts into
// two explicit modifier shortcuts, without changing normal text input.
window.NeuraKeyboard={
 matchEditor(actions,e,{editing=false}={}){
  if(!editing||e.defaultPrevented||e.isComposing||e.keyCode===229||e.shiftKey||e.altKey||e.getModifierState?.('AltGraph')||!!e.ctrlKey===!!e.metaKey)return null;
  const key=e.key.toLowerCase();return actions.find(a=>a.editorKey===key)||null;
 },
 available(e){return !e.defaultPrevented&&!e.isComposing&&e.keyCode!==229&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&!e.getModifierState?.('AltGraph');},
 match(actions,e,{typing=false,graph=false,selected=false,enabled=true}={}){
  if(!this.available(e)||typing||selected)return null;
  const key=e.key.length===1?e.key.toLowerCase():e.key;
  if(!enabled&&key.length===1)return null;
  return actions.find(a=>{
   const keys=Array.isArray(a.plain)?a.plain:[a.plain];
   if(!keys.includes(key)||a.context==='graph'&&!graph)return false;
   // Punctuation follows the produced character across keyboard layouts.
   if(key.length===1&&!/[a-z0-9 ]/i.test(key))return true;
   return a.anyShift||!!a.plainShift===!!e.shiftKey;
  })||null;
 }
};
