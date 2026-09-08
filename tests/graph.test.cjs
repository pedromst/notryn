const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const context={window:{},document:{hidden:false,activeElement:null,body:{classList:{contains:()=>false}}},requestAnimationFrame:()=>{}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../web/graph.js'),'utf8'),context);
function camera(){
 const graph=Object.create(context.window.NotrynGraph.prototype);
 Object.assign(graph,{zoom:1,rotation:.32,tilt:-.12,cameraTarget:null,motionPreference:{matches:false},mobile:{matches:false},moving:false,dirty:false,last:0,time:0,width:800,height:600,canvas:{},draw(){this.draws=(this.draws||0)+1;}});
 return graph;
}
function settle(graph){for(let i=0;i<100;i++)graph.advanceCamera(16);assert.equal(graph.cameraTarget,null);}

test('navigation eases without overshoot and converges independently of frame rate',()=>{
 const a=camera(),b=camera();
 for(const g of [a,b]){g.rotateBy(.07,.06);g.zoomBy(1.12);assert.equal(g.zoom,1);}
 let previous=a.rotation;
 for(let i=0;i<20;i++){a.advanceCamera(16);assert.ok(a.rotation>previous&&a.rotation<.39);previous=a.rotation;}
 for(let i=0;i<10;i++)b.advanceCamera(32);
 assert.ok(Math.abs(a.rotation-b.rotation)<1e-12);
 assert.ok(Math.abs(a.zoom-b.zoom)<1e-12);
 settle(a);assert.equal(a.rotation,.39);assert.equal(a.zoom,1.12);
});
test('repeated controls accumulate, reverse smoothly, and retain zoom and tilt limits',()=>{
 const g=camera();
 for(let i=0;i<20;i++){g.rotateBy(.07,.06);g.zoomBy(1.12);g.advanceCamera(8);}
 assert.equal(g.cameraTarget.zoom,3);assert.equal(g.cameraTarget.tilt,1);
 const before=g.rotation;g.rotateBy(-.07,0);assert.equal(g.rotation,before);
 settle(g);assert.ok(Math.abs(g.rotation-(.32+19*.07))<1e-12);
 g.zoomBy(.001);g.rotateBy(0,-10);settle(g);assert.equal(g.zoom,.4);assert.equal(g.tilt,-1);
});
test('manual navigation finishes while ambient motion is paused, then stops redrawing',()=>{
 const g=camera();g.zoomBy(1.12);
 for(let i=1;i<80;i++)g.tick(i*16);
 assert.equal(g.zoom,1.12);assert.equal(g.cameraTarget,null);assert.equal(g.time,0);
 const draws=g.draws;for(let i=80;i<100;i++)g.tick(i*16);
 assert.equal(g.draws,draws);assert.equal(g.rotation,.32);
});
test('reset takes the shortest turn and reduced motion applies controls immediately',()=>{
 const g=camera();g.rotation=20*Math.PI+.5;g.fit();
 assert.ok(Math.abs(g.rotation-g.cameraTarget.rotation)<Math.PI);settle(g);
 assert.equal(g.rotation,.32);assert.equal(g.zoom,1);
 g.motionPreference.matches=true;g.zoomBy(1.12);g.rotateBy(.07,0);
 assert.equal(g.cameraTarget,null);assert.equal(g.zoom,1.12);assert.equal(g.rotation,.39);
 g.motionPreference.matches=false;g.zoomBy(1.12);g.motionPreference.matches=true;g.advanceCamera(16);
 assert.equal(g.cameraTarget,null);
});

function labelsGraph(count=26){
 const g=camera();Object.assign(g,{width:1200,height:700,points:new Map(),filter:()=>true,ctx:{measureText:text=>({width:text.length*6.6})},fit(){}});
 g.setData({nodes:Array.from({length:count},(_,i)=>({id:String(i),title:'Project '+(i+1),group:'projects'})),edges:[]});
 g.nodes.forEach((n,i)=>g.points.set(n.id,{x:50+(i%5)*230,y:100+Math.floor(i/5)*85,z:0,s:1}));
 return g;
}
function assertLegible(g,labels){
 for(const a of labels){
  assert.ok(a.x>=8&&a.x+a.w<=g.width-8&&a.y>=54&&a.y+a.h<=g.height-66);
  for(const b of labels)if(a!==b)assert.ok(a.x>=b.x+b.w||a.x+a.w<=b.x||a.y>=b.y+b.h||a.y+a.h<=b.y);
 }
}
test('every project can have a clickable name; no fixed label count hides low-degree notes',()=>{
 const g=labelsGraph();const labels=g.layoutLabels();
 assert.equal(labels.length,26);assertLegible(g,labels);
 g.labelRects=labels;for(const rect of labels)assert.equal(g.hit(rect.x+rect.w/2,rect.y+rect.h/2).id,rect.id);
});
test('nearby notes use alternate local positions without overlapping names or covering controls',()=>{
 const g=labelsGraph(4);g.nodes.forEach((n,i)=>g.points.set(n.id,{x:400+i*4,y:320+i*4,z:0,s:1}));
 const labels=g.layoutLabels();assert.equal(labels.length,4);assertLegible(g,labels);
 for(const rect of labels){const p=g.points.get(rect.id);assert.ok(Math.abs((rect.y+rect.h/2)-p.y)<=60);}
});
test('a narrow desktop Brain labels every direct folder and file',()=>{
 const g=labelsGraph(16);g.width=430;g.height=620;
 g.nodes.forEach((n,i)=>{n.kind=i<10?'folder':'note';g.points.set(n.id,{x:150+(i%4)*42,y:180+Math.floor(i/4)*48,z:0,s:1});});
 const labels=g.layoutLabels();assert.equal(labels.length,g.nodes.length);assertLegible(g,labels);
});
test('mobile keeps every direct item named without overlaps',()=>{
 const g=labelsGraph(30);g.width=390;g.height=690;g.mobile.matches=true;
 g.nodes.forEach(n=>g.points.set(n.id,{x:195,y:330,z:0,s:1}));
 const labels=g.layoutLabels();assert.equal(labels.length,g.nodes.length);assertLegible(g,labels);
});

test('opening an unconnected note keeps every sibling label and its filename visible',()=>{
 const g=labelsGraph(16);
 g.nodes[0].title='Alterações materiais';g.nodes[0].displayName='log.md';
 g.select(g.nodes[1].id);
 const labels=g.layoutLabels();assert.equal(labels.length,16);assertLegible(g,labels);
 assert.equal(labels.find(label=>label.id===g.nodes[0].id).name,'log.md');
});

test('selection and hover isolate direct neighbors; moving away restores the selection',()=>{
 const g=labelsGraph(4),fills=[];
 g.edges=[{source:'0',target:'1'},{source:'1',target:'2'}];g.select('0');
 g.colors=['#aeeed8'];g.groups=['projects'];
 g.palette={labelSelected:'#b4ebd9d6',labelSelectedText:'#000000',labelLinked:'#3e585bcc',labelLinkedText:'#e3eff0',label:'#101e2ae8',labelActive:'#1b2b35f5',labelText:'#e3eff0',labelMuted:'#c0cdd0',accent:'#b4ebd9',line:'#33444b',pearl:'#ffffff'};
 g.ctx={measureText:text=>({width:text.length*6.6}),createRadialGradient:()=>({addColorStop(){}}),fillRect(){},beginPath(){},arc(){},fill(){},stroke(){},roundRect(){},fillText(text){fills.push({text,color:this.fillStyle,alpha:this.globalAlpha});}};
 g.drawNotes();
 assert.equal(fills.find(x=>x.text==='Project 1').color,g.palette.labelSelectedText);
 assert.equal(fills.find(x=>x.text==='Project 2').color,g.palette.labelLinkedText);
 assert.equal(fills.find(x=>x.text==='Project 2').alpha,1);
 assert.equal(fills.find(x=>x.text==='Project 3').alpha,.18);
 const positions=JSON.stringify(g.labelRects);
 g.hover='1';fills.length=0;g.drawNotes();
 assert.equal(JSON.stringify(g.labelRects),positions,'hover must not move labels');
 assert.equal(fills.find(x=>x.text==='Project 2').color,g.palette.labelSelectedText);
 for(const title of ['Project 1','Project 2','Project 3'])assert.equal(fills.find(x=>x.text===title).alpha,1);
 assert.equal(fills.find(x=>x.text==='Project 4').alpha,.18);
 g.hover='3';assert.deepEqual(Array.from(g.focusState().neighbors),['3']);
 g.hover=null;assert.equal(g.focusState().id,'0');
 g.select(null);fills.length=0;g.drawNotes();assert.ok(fills.every(x=>x.alpha===1));
 assert.equal(g.ctx.globalAlpha,1);
});

test('keyboard focus uses the same direct neighborhood as hover',()=>{
 const g=labelsGraph(4);g.edges=[{source:'0',target:'1'},{source:'1',target:'2'}];g.select('3');g.keyboardId='1';
 context.document.activeElement=g.canvas;
 assert.equal(g.focusState().id,'1');assert.deepEqual(Array.from(g.focusState().neighbors).sort(),['0','1','2']);
 g.hover='0';assert.equal(g.focusState().id,'0');
 context.document.activeElement=null;g.hover=null;assert.equal(g.focusState().id,'3');
});

test('selected connections get multiple travelling points even beyond the old edge sampling stride',()=>{
 const g=labelsGraph(4),dots=[];
 g.edges=Array.from({length:80},()=>({source:'2',target:'3'}));g.edges[1]={source:'1',target:'0'};g.select('0');
 g.palette={rgb:'170,220,200',accent:'#b4ebd9',pulse:'#ecfff7'};
 g.ctx={createLinearGradient:()=>({addColorStop(){}}),beginPath(){},arc(x,y,r){dots.push({x,y,r});},fill(){}};g.line=()=>{};g.glow=()=>{};
 g.drawConnections();assert.equal(dots.length,3);
 const start=g.points.get('0'),end=g.points.get('1');
 for(const dot of dots)assert.ok(dot.x>=start.x&&dot.x<=end.x&&dot.r>1.1);
 const previous=dots.map(d=>d.x);dots.length=0;g.time+=.5;g.drawConnections();assert.notDeepEqual(dots.map(d=>d.x),previous);
 g.edges=Array.from({length:120},()=>({source:'0',target:'1'}));dots.length=0;g.drawConnections();assert.ok(dots.length<=96);
});

test('selection label text stays readable in every preset and custom Omarchy palettes',()=>{
 const sandbox={window:{},localStorage:{getItem:()=>null},CustomEvent:class{},document:{documentElement:{dataset:{},style:{setProperty(){}}},querySelector:()=>null,dispatchEvent(){}}};
 vm.createContext(sandbox);vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../web/theme-core.js'),'utf8'),sandbox);
 const themes=sandbox.window.NotrynThemes;
 const luminance=hex=>[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
 const contrast=(a,b)=>(Math.max(luminance(a),luminance(b))+.05)/(Math.min(luminance(a),luminance(b))+.05);
 const custom=['#111111','#ffffff','#808080','#ff00ff'].map(accent=>({...themes.presets[0],id:'omarchy',accent}));
 for(const theme of [...themes.presets,...custom]){
  const p=themes.build(theme).graph;
  const composite=(fill,bg)=>'#'+[1,3,5].map(i=>Math.round(parseInt(bg.slice(i,i+2),16)*(1-parseInt(fill.slice(7),16)/255)+parseInt(fill.slice(i,i+2),16)*parseInt(fill.slice(7),16)/255).toString(16).padStart(2,'0')).join('');
  for(const background of [theme.bg,theme.panel]){
   assert.ok(contrast(composite(p.labelSelected,background),p.labelSelectedText)>=4.5,theme.id+' selected');
   assert.ok(contrast(composite(p.labelLinked,background),p.labelLinkedText)>=4.5,theme.id+' linked');
  }
  for(const fill of [p.labelSelected,p.labelLinked])assert.ok(parseInt(fill.slice(7),16)<255);
  assert.notEqual(p.labelSelected,p.labelLinked);
 }
});
