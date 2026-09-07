const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const web=path.join(__dirname,'../web');

function presence(){
 const nodes={};
 for(const id of ['orb','iris-wave','iris-wave-echo','voice-status','agent'])nodes['#'+id]={hidden:false,dataset:{},attrs:{},classes:new Set(),setAttribute(k,v){this.attrs[k]=v;},classList:{toggle(k,v){v?nodes['#'+id].classes.add(k):nodes['#'+id].classes.delete(k);}}};
 const frames=new Map(),events={},media={matches:false,addEventListener(_,fn){this.changed=fn;}};
 let tick=0,now=0,mutated;
 const c={document:{hidden:false,querySelector:id=>nodes[id],addEventListener:(name,fn)=>events[name]=fn},matchMedia:()=>media,performance:{now:()=>now},requestAnimationFrame:fn=>{frames.set(++tick,fn);return tick;},cancelAnimationFrame:id=>frames.delete(id),MutationObserver:class{constructor(fn){mutated=fn;}observe(){}}};
 c.window=c;vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(web,'iris.js'),'utf8'),c);
 return {c,nodes,frames,media,events,mutate:()=>mutated(),frame(time){now=time;const next=frames.entries().next().value;if(next){frames.delete(next[0]);next[1](time);}}};
}
test('voice wave starts on speaking, changes over time and stops completely at idle',()=>{
 const p=presence();assert.equal(p.frames.size,0);
 p.c.IrisPresence.set('preparing',true);assert.equal(p.frames.size,0);
 p.c.IrisPresence.set('speaking',true);p.frame(300);
 const first=p.nodes['#iris-wave'].attrs.d;
 assert.notEqual(first,'M35 120H205');assert(!first.includes('NaN'));
 p.frame(480);assert.notEqual(p.nodes['#iris-wave'].attrs.d,first);
 p.c.IrisPresence.set('idle',true);
 assert.equal(p.nodes['#iris-wave'].attrs.d,'M35 120H205');assert.equal(p.frames.size,0);
 assert.equal(p.nodes['#voice-status'].textContent,'Voice ready');
});
test('reduced motion, hidden panel and background tab do not keep animation frames running',()=>{
 const p=presence();p.media.matches=true;p.c.IrisPresence.set('speaking');
 assert.equal(p.frames.size,0);assert.equal(p.nodes['#voice-status'].textContent,'Speaking');
 p.media.matches=false;p.media.changed();assert.equal(p.frames.size,1);
 p.nodes['#agent'].hidden=true;p.mutate();assert.equal(p.frames.size,0);
 p.nodes['#agent'].hidden=false;p.mutate();assert.equal(p.frames.size,1);
 p.c.document.hidden=true;p.events.visibilitychange();assert.equal(p.frames.size,0);
 p.c.document.hidden=false;p.events.visibilitychange();assert.equal(p.frames.size,1);
 p.c.IrisPresence.set('idle');assert.equal(p.frames.size,0);
});
function speech(){
 const states=[],utterances=[],voiceNode={setAttribute(){}};
 const c={state:{voice:true,nativeVoice:false},IrisPresence:{set:(...v)=>states.push(v),pulse(){}},$:()=>voiceNode,toast(){},speechSynthesis:{getVoices:()=>[{localService:true,lang:'en-US'}],cancel(){},speak:u=>utterances.push(u)},SpeechSynthesisUtterance:class{constructor(text){this.text=text;}},api:async()=>({})};
 c.window=c;vm.createContext(c);
 const source=fs.readFileSync(path.join(web,'app.js'),'utf8');
 vm.runInContext(source.slice(source.indexOf('let speechSerial=0'),source.indexOf('function say(text)')),c);
 return {c,states,utterances};
}
test('browser speech lifecycle drives presence, including pause, resume and stop',async()=>{
 const p=speech();await p.c.speak('Hello');assert.equal(p.states.at(-1)[0],'preparing');
 const u=p.utterances[0];u.onstart();assert.equal(p.states.at(-1)[0],'speaking');
 u.onpause();assert.equal(p.states.at(-1)[0],'idle');u.onresume();assert.equal(p.states.at(-1)[0],'speaking');
 u.onend();assert.equal(p.states.at(-1)[0],'idle');
 await p.c.speak('Again');p.utterances[1].onstart();p.c.stopSpeech();
 assert.equal(p.states.at(-1)[0],'idle');
 const count=p.states.length;p.utterances[1].onstart();p.utterances[1].onerror();assert.equal(p.states.length,count);
});
test('cancelled utterances cannot overwrite a newer voice state; errors return to idle',async()=>{
 const p=speech();await p.c.speak('First');const old=p.utterances[0];
 await p.c.speak('Second');const current=p.utterances[1];current.onstart();
 old.onend();old.onerror();assert.equal(p.states.at(-1)[0],'speaking');assert.equal(p.c.state.voice,true);
 current.onerror();assert.equal(p.states.at(-1)[0],'idle');assert.equal(p.c.state.voice,false);
});
