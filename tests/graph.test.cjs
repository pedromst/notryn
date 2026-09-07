const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const context={window:{},document:{hidden:false,activeElement:null,body:{classList:{contains:()=>false}}},requestAnimationFrame:()=>{}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../web/graph.js'),'utf8'),context);
function camera(){
 const graph=Object.create(context.window.NeuraGraph.prototype);
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
test('mobile respects available space and keyboard focus always reveals a hidden name',()=>{
 const g=labelsGraph(30);g.width=390;g.height=690;
 g.nodes.forEach(n=>g.points.set(n.id,{x:195,y:330,z:0,s:1}));
 const labels=g.layoutLabels();assert.ok(labels.length<g.nodes.length);assertLegible(g,labels);
 const hidden=g.nodes.find(n=>!labels.some(r=>r.id===n.id));
 context.document.activeElement=g.canvas;g.keyboardId=hidden.id;
 assert.ok(g.layoutLabels().some(r=>r.id===hidden.id));context.document.activeElement=null;
});
