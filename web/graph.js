'use strict';
// Original filament geometry with refined glass reflections and luminous notes.
// The glass cortex is illustrative. Bright nodes and their links come from Markdown.
window.NeuraGraph=class{
 constructor(canvas,onSelect){
  this.canvas=canvas;this.ctx=canvas.getContext('2d');this.onSelect=onSelect;
  this.nodes=[];this.edges=[];this.zoom=1;this.rotation=.32;this.tilt=-.12;this.cameraTarget=null;
  this.motionPreference=matchMedia('(prefers-reduced-motion:reduce)');this.mobile=matchMedia('(max-width:900px)');
  this.moving=!this.motionPreference.matches;
  try{if(localStorage.getItem('neura-motion')==='paused')this.moving=false;}catch{}
  this.points=new Map();this.pointers=new Map();this.labelRects=[];this.filter=()=>true;
  this.selected=null;this.hover=null;this.keyboardId=null;this.time=0;this.last=0;this.dirty=true;
  this.setTheme(window.NeuraThemes.build(window.NeuraThemes.current).graph);
  this.cortex=this.buildCortex();
  this.motionPreference.addEventListener('change',e=>{if(e.matches){this.moving=false;document.dispatchEvent(new Event('neura-motionchange'));}this.dirty=true;});
  new ResizeObserver(()=>this.resize()).observe(canvas);this.events();
  this.tick=this.tick.bind(this);requestAnimationFrame(this.tick);document.fonts.ready.then(()=>this.dirty=true);
 }
 setTheme(palette){this.palette=palette;this.colors=palette.colors;this.meshColors=['0d','20','30','40','4c'].map(alpha=>palette.mesh+alpha);this.dirty=true;}
 color(group){return this.colors[this.groups?.indexOf(group)%this.colors.length]||this.colors[0];}
 hash(s){let h=2166136261;for(const c of s)h=Math.imul(h^c.charCodeAt(0),16777619);return(h>>>0)/4294967296;}
 setData(data){
  this.nodes=data.nodes||[];this.edges=data.edges||[];this.groups=data.colorGroups||[...new Set(this.nodes.map(n=>n.group))];
  this.ids=new Map(this.nodes.map(n=>[n.id,n]));this.nodes.forEach(n=>n.degree=0);
  this.edges.forEach(e=>{const source=this.ids.get(e.source),target=this.ids.get(e.target);if(source&&target){source.degree++;target.degree++;}});
  this.nodes.forEach((n,i)=>{n.brain=this.brainPoint(i%2?1:-1,.3+(i+.5)/Math.max(1,this.nodes.length)*(Math.PI-.6),i*2.39996);});
  const ranked=[...this.nodes].sort((a,b)=>Number(b.kind==='folder')-Number(a.kind==='folder')||b.degree-a.degree||a.title.localeCompare(b.title));
  this.labelRank=new Map(ranked.map((n,i)=>[n.id,i]));
  if(!this.ids.has(this.keyboardId))this.keyboardId=null;this.fit(true);
 }
 brainPoint(side,lat,lon){
  const s=Math.sin(lat),fold=1+.045*Math.sin(lon*7+lat*8)+.023*Math.sin(lat*17-lon*3);
  const x=side*Math.max(.025,.065+s*.46+Math.cos(lon)*s*.56*fold),y=Math.cos(lat)*(.9+.07*s)*fold;
  return{x,y:y<0?y*.9:y,z:Math.sin(lon)*s*.82*fold};
 }
 buildCortex(){
  // Precompute irregular local filaments once, rather than a rectangular wire grid per frame.
  return [-1,1].map(side=>{
   const vertices=[],edges=[],ridges=[],rows=29,cols=48;
   for(let a=0;a<rows;a++)for(let b=0;b<cols;b++){
    const seed=side+':'+a+':'+b,lat=(a+.5+(this.hash(seed+'a')-.5)*.65)/rows*Math.PI;
    const lon=(b+(this.hash(seed+'b')-.5)*.8)/cols*Math.PI*2;
    vertices.push(this.brainPoint(side,lat,lon));
    const i=a*cols+b;
    edges.push([i,a*cols+(b+1)%cols]);
    if(a){edges.push([i,i-cols]);if((a+b)%2===0)edges.push([i,(a-1)*cols+(b+1)%cols]);}
   }
   // Curved folds provide a continuous cortex silhouette within the fine mesh.
   for(let r=0;r<13;r++){
    const ridge=[];
    for(let t=0;t<=70;t++){
     const lon=t/70*Math.PI*2,lat=.2+r/12*(Math.PI-.4)+.045*Math.sin(lon*5+r);
     ridge.push(this.brainPoint(side,lat,lon));
    }ridges.push(ridge);
   }
   return {side,vertices,edges,ridges};
  });
 }
 resize(){
  const r=this.canvas.getBoundingClientRect();this.width=r.width;this.height=r.height;
  const d=Math.min(devicePixelRatio||1,2);this.canvas.width=r.width*d;this.canvas.height=r.height*d;this.ctx.setTransform(d,0,0,d,0,0);this.dirty=true;
 }
 cameraTo(values,immediate=false){
  const base=this.cameraTarget||this;
  const target={zoom:base.zoom,rotation:base.rotation,tilt:base.tilt,...values};
  target.zoom=Math.max(.4,Math.min(3,target.zoom));target.tilt=Math.max(-1,Math.min(1,target.tilt));
  if(immediate||this.motionPreference.matches){Object.assign(this,target);this.cameraTarget=null;}
  else this.cameraTarget=target;
  this.dirty=true;
 }
 zoomBy(factor){this.cameraTo({zoom:(this.cameraTarget||this).zoom*factor});}
 rotateBy(horizontal,vertical){const view=this.cameraTarget||this;this.cameraTo({rotation:view.rotation+horizontal,tilt:view.tilt+vertical});}
 advanceCamera(dt){
  if(!this.cameraTarget)return false;
  // Time-based easing keeps repeated inputs continuous at any display refresh rate.
  const target=this.cameraTarget,amount=this.motionPreference.matches?1:1-Math.exp(-dt/90);
  let settled=true;
  for(const key of ['zoom','rotation','tilt']){
   this[key]+=(target[key]-this[key])*amount;
   if(Math.abs(target[key]-this[key])<.0001)this[key]=target[key];else settled=false;
  }
  if(settled)this.cameraTarget=null;
  return true;
 }
 fit(immediate=false){
  // Recenter by the shortest turn, even after several complete revolutions.
  this.rotation=.32+Math.atan2(Math.sin(this.rotation-.32),Math.cos(this.rotation-.32));
  this.cameraTo({zoom:1,rotation:.32,tilt:-.12},immediate);
 }
 select(id){this.selected=id;if(this.ids?.has(id))this.keyboardId=id;this.neighbors=new Set([id]);this.edges.forEach(e=>{if(e.source===id)this.neighbors.add(e.target);if(e.target===id)this.neighbors.add(e.source);});this.dirty=true;}
 project(p){
  let{x,y,z}=p;
  const a=x*Math.cos(this.rotation)+z*Math.sin(this.rotation);z=-x*Math.sin(this.rotation)+z*Math.cos(this.rotation);x=a;
  const b=y*Math.cos(this.tilt)-z*Math.sin(this.tilt);z=y*Math.sin(this.tilt)+z*Math.cos(this.tilt);y=b;
  const perspective=4.6/(4.6+z),size=Math.min(this.width*.4,Math.max(40,this.height-140)*.46)*this.zoom;
  return{x:this.width*.5+x*size*perspective,y:this.height*.48-y*size*perspective,z,s:perspective};
 }
 line(a,b,color,width=.6){const c=this.ctx;c.beginPath();c.moveTo(a.x,a.y);c.lineTo(b.x,b.y);c.lineWidth=width;c.strokeStyle=color;c.stroke();}
 hull(points){
  const p=[...points].sort((a,b)=>a.x-b.x||a.y-b.y),cross=(a,b,c)=>(b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x),lower=[],upper=[];
  for(const n of p){while(lower.length>1&&cross(lower.at(-2),lower.at(-1),n)<=0)lower.pop();lower.push(n);}
  for(let i=p.length-1;i>=0;i--){const n=p[i];while(upper.length>1&&cross(upper.at(-2),upper.at(-1),n)<=0)upper.pop();upper.push(n);}
  return lower.slice(0,-1).concat(upper.slice(0,-1));
 }
 glow(x,y,r,color,alpha){
  const c=this.ctx,g=c.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,`rgba(${color},${alpha})`);g.addColorStop(1,`rgba(${color},0)`);c.fillStyle=g;c.fillRect(x-r,y-r,r*2,r*2);
 }
 atmosphere(){
  const c=this.ctx,w=this.width,h=this.height,s=Math.min(w,h),drift=this.time*.006;
  this.glow(w*.48,h*.44,s*.57,this.palette.rgb,.065);
  this.glow(w*.67,h*.33,s*.33,this.palette.rgb,.035);
  for(let i=0;i<44;i++){
   const x=this.hash(i+'sky-x')*w+Math.sin(drift+i)*3,y=this.hash(i+'sky-y')*h;
   c.fillStyle=i%9===0?this.palette.mesh+'54':this.palette.mesh+'22';c.beginPath();c.arc(x,y,i%9===0?1:.55,0,Math.PI*2);c.fill();
  }
 }
 glassShell(shell,points){
  const c=this.ctx,hull=this.hull(points.filter((_,i)=>i%3===0));if(hull.length<3)return;
  const xs=hull.map(p=>p.x),ys=hull.map(p=>p.y),left=Math.min(...xs),right=Math.max(...xs),top=Math.min(...ys),bottom=Math.max(...ys);
  const skin=new Path2D();skin.moveTo(hull[0].x,hull[0].y);hull.slice(1).forEach(p=>skin.lineTo(p.x,p.y));skin.closePath();
  const catchlight=.32+Math.sin(this.rotation+shell.side*.4)*.12,fill=c.createLinearGradient(left,top,right,bottom);
  fill.addColorStop(0,this.palette.mesh+'19');fill.addColorStop(catchlight,this.palette.secondary+'08');fill.addColorStop(.65,this.palette.label.slice(0,7)+'28');fill.addColorStop(1,this.palette.secondary+'12');
  c.fillStyle=fill;c.fill(skin);
  const rim=c.createLinearGradient(left,top,right,bottom);
  rim.addColorStop(0,this.palette.pulse+'ac');rim.addColorStop(.26,this.palette.mesh+'23');rim.addColorStop(.65,this.palette.accent+'0b');rim.addColorStop(1,this.palette.mesh+'69');
  c.strokeStyle=rim;c.lineWidth=1;c.stroke(skin);
  // A broad, faint reflection catches the glass without covering the notes.
  c.save();c.clip(skin);
  const sheen=c.createLinearGradient(left,top,right,top+(bottom-top)*.7);
  sheen.addColorStop(0,this.palette.mesh+'00');sheen.addColorStop(catchlight,this.palette.mesh+'00');sheen.addColorStop(catchlight+.12,this.palette.mesh+'09');sheen.addColorStop(catchlight+.15,this.palette.mesh+'19');sheen.addColorStop(catchlight+.23,this.palette.mesh+'00');sheen.addColorStop(1,this.palette.mesh+'00');
  c.fillStyle=sheen;c.fillRect(left,top,right-left,bottom-top);c.restore();
 }
 drawCortex(){
  const c=this.ctx;
  const shells=this.cortex.map(shell=>({shell,p:shell.vertices.map(v=>this.project(v)),depth:this.project({x:shell.side*.45,y:0,z:0}).z})).sort((a,b)=>b.depth-a.depth);
  for(const {shell,p} of shells)this.glassShell(shell,p);
  for(const {shell,p} of shells){
   const paths=Array.from({length:5},()=>new Path2D());
   for(const[a,b]of shell.edges){
    const depth=(p[a].z+p[b].z)*.5,band=Math.max(0,Math.min(4,Math.floor((1.3-depth)*1.8))),path=paths[band];
    path.moveTo(p[a].x,p[a].y);path.lineTo(p[b].x,p[b].y);
   }
   const colors=this.meshColors;
   paths.forEach((path,i)=>{c.strokeStyle=colors[i];c.lineWidth=.5;c.stroke(path);});
   for(let i=0;i<shell.ridges.length;i++){
    const points=shell.ridges[i].map(p=>this.project(p)),path=new Path2D();path.moveTo(points[0].x,points[0].y);points.slice(1).forEach(p=>path.lineTo(p.x,p.y));
    c.strokeStyle=i%3===0?this.palette.mesh+'2a':this.palette.mesh+'1b';c.lineWidth=i%3===0?.9:.55;c.stroke(path);
   }
   const light=1+Math.sin(this.time*.45+shell.side)*.12;
   for(let i=0;i<p.length;i+=3){
    const n=p[i],front=Math.max(.12,Math.min(1,(1.2-n.z)*.5));
    c.fillStyle=`rgba(${this.palette.rgb},${front*.34*light})`;c.fillRect(n.x,n.y,n.z<-.3?1.25:.8,n.z<-.3?1.25:.8);
   }
  }
 }
 drawConnections(){
  const c=this.ctx,density=Math.max(.045,Math.min(.22,.22/Math.sqrt(Math.max(1,this.edges.length/100))));
  let sparks=0;
  for(let i=0;i<this.edges.length;i++){
   const e=this.edges[i],a=this.ids.get(e.source),b=this.ids.get(e.target);if(!this.filter(a)||!this.filter(b))continue;
   const p=this.points.get(a.id),q=this.points.get(b.id),active=this.selected&&(a.id===this.selected||b.id===this.selected);
   this.line(p,q,`rgba(${this.palette.rgb},${active?.64:this.selected?.028:density})`,active?1.05:.65);
   if((!this.selected||active)&&i%Math.max(1,Math.ceil(this.edges.length/24))===0&&sparks++<24){
    const t=(this.time*(.07+this.hash(e.source+e.target)*.035)+this.hash('pulse'+i))%1,tail=Math.max(0,t-.1);
    const x=p.x+(q.x-p.x)*t,y=p.y+(q.y-p.y)*t,tx=p.x+(q.x-p.x)*tail,ty=p.y+(q.y-p.y)*tail;
    const streak=c.createLinearGradient(tx,ty,x+.01,y+.01);streak.addColorStop(0,this.palette.pulse+'00');streak.addColorStop(1,this.palette.pulse+'aa');
    this.line({x:tx,y:ty},{x,y},streak,1.2);this.glow(x,y,6,this.palette.rgb,.12);
    c.fillStyle=this.palette.pulse;c.beginPath();c.arc(x,y,1.1,0,Math.PI*2);c.fill();
   }
  }
 }
 noteRadius(n,p){return((n.kind==='folder'?5.6:3.4)+Math.min(3.6,Math.sqrt(n.degree)*.62))*p.s;}
 layoutLabels(){
  const c=this.ctx,w=this.width,h=this.height,keyboard=document.activeElement===this.canvas,labels=[],cells=new Map(),cellSize=64;
  const focused=n=>this.selected===n.id||this.hover===n.id||(keyboard&&this.keyboardId===n.id);
  const buckets=rect=>{const keys=[];for(let x=Math.floor(rect.x/cellSize);x<=Math.floor((rect.x+rect.w)/cellSize);x++)for(let y=Math.floor(rect.y/cellSize);y<=Math.floor((rect.y+rect.h)/cellSize);y++)keys.push(x+':'+y);return keys;};
  const occupy=rect=>{for(const key of buckets(rect)){if(!cells.has(key))cells.set(key,[]);cells.get(key).push(rect);}};
  const overlaps=rect=>buckets(rect).some(key=>(cells.get(key)||[]).some(b=>rect.x<b.x+b.w+3&&rect.x+rect.w+3>b.x&&rect.y<b.y+b.h+3&&rect.y+rect.h+3>b.y));
  const items=this.nodes.filter(n=>{const p=this.points.get(n.id);return p&&this.filter(n)&&(focused(n)||(!this.selected||this.neighbors.has(n.id))&&p.x>=0&&p.x<=w&&p.y>=54&&p.y<=h-66);});
  // Protect the dots as well as other names; labels stay beside their own node.
  for(const n of items){const p=this.points.get(n.id),r=this.noteRadius(n,p)+2;occupy({x:p.x-r,y:p.y-r,w:r*2,h:r*2});}
  items.sort((a,b)=>Number(focused(b))-Number(focused(a))||this.labelRank.get(a.id)-this.labelRank.get(b.id));
  for(const n of items){
   const p=this.points.get(n.id),r=this.noteRadius(n,p),isFocused=focused(n),dense=items.length>18||w<620;
   const size=dense?10:11,font=(isFocused?'500 ':'')+size+'px JetBrains';c.font=font;
   const limit=Math.max(12,Math.min(dense?22:30,Math.floor((w-40)/(dense?6:6.6)))),name=n.title.length>limit?n.title.slice(0,limit-2)+'…':n.title;
   const tw=c.measureText(name).width,lw=tw+12,lh=dense?21:23,right=p.x+r+9,left=p.x-r-9-lw,center=p.x-lw/2;
   const positions=[[right,p.y-lh/2],[left,p.y-lh/2],[center,p.y-r-9-lh],[center,p.y+r+9]];
   for(const dy of [-27,27,-54,54])positions.push([right,p.y-lh/2+dy],[left,p.y-lh/2+dy]);
   // A dense folder can still show every direct item. Search progressively
   // around its node before using the nearest free slot in the canvas.
   const phase=this.hash(n.id+'label')*Math.PI*2;
   for(let distance=42;distance<=126;distance+=21)for(let step=0;step<12;step++){
    const angle=phase+step*Math.PI/6;
    positions.push([p.x+Math.cos(angle)*distance-lw/2,p.y+Math.sin(angle)*distance-lh/2]);
   }
   let rect=positions.map(([x,y])=>({x,y,w:lw,h:lh})).find(b=>b.x>=8&&b.x+b.w<=w-8&&b.y>=54&&b.y+b.h<=h-66&&!overlaps(b));
   if(!rect&&!this.mobile.matches){
    let nearest=null,distance=Infinity;
    for(let y=54;y+lh<=h-66;y+=lh+3)for(let x=8;x+lw<=w-8;x+=8){
     const candidate={x,y,w:lw,h:lh};if(overlaps(candidate))continue;
     const score=(x+lw/2-p.x)**2+(y+lh/2-p.y)**2;
     if(score<distance){nearest=candidate;distance=score;}
    }
    rect=nearest;
   }
   if(!rect&&isFocused)rect={x:Math.max(8,Math.min(w-lw-8,right)),y:Math.max(54,Math.min(h-lh-66,p.y-lh/2)),w:lw,h:lh};
   if(rect){labels.push({...rect,id:n.id,name,font,focused:isFocused});occupy(rect);}
  }
  return labels;
 }
 drawNotes(){
  const c=this.ctx,keyboard=document.activeElement===this.canvas;
  const sorted=[...this.nodes].sort((a,b)=>this.points.get(b.id).z-this.points.get(a.id).z);
  for(const n of sorted){
   const p=this.points.get(n.id),color=this.color(n.group),visible=this.filter(n);
   const focused=this.selected===n.id||this.hover===n.id||(keyboard&&this.keyboardId===n.id),active=!this.selected||this.neighbors.has(n.id);
   const r=this.noteRadius(n,p);
   c.globalAlpha=visible?(active?1:.16):.04;
   const aura=c.createRadialGradient(p.x,p.y,0,p.x,p.y,r*5);aura.addColorStop(0,color+'55');aura.addColorStop(.3,color+'18');aura.addColorStop(1,color+'00');
   c.fillStyle=aura;c.fillRect(p.x-r*5,p.y-r*5,r*10,r*10);
   const pearl=c.createRadialGradient(p.x-r*.3,p.y-r*.4,.1,p.x,p.y,r);
   pearl.addColorStop(0,this.palette.pearl);pearl.addColorStop(.35,color);pearl.addColorStop(1,color+'8c');
   c.fillStyle=pearl;c.beginPath();c.arc(p.x,p.y,r,0,Math.PI*2);c.fill();
   if(n.kind==='folder'){c.strokeStyle=color+'99';c.lineWidth=1;c.beginPath();c.arc(p.x,p.y,r+4,0,Math.PI*2);c.stroke();c.strokeStyle=color+'2d';c.beginPath();c.arc(p.x,p.y,r+8,0,Math.PI*2);c.stroke();}
   if(focused){
    c.strokeStyle=color+'aa';c.lineWidth=1;c.beginPath();c.arc(p.x,p.y,r+6,0,Math.PI*2);c.stroke();
    c.strokeStyle=color+'27';c.beginPath();c.arc(p.x,p.y,r+11,0,Math.PI*2);c.stroke();
   }
   c.globalAlpha=1;
  }
  this.labelRects=this.layoutLabels();
  for(const rect of this.labelRects){
   c.font=rect.font;c.fillStyle=rect.focused?this.palette.labelActive:this.palette.label;c.beginPath();c.roundRect(rect.x,rect.y,rect.w,rect.h,5);c.fill();
   c.strokeStyle=rect.focused?this.palette.accent+'55':this.palette.line+'55';c.lineWidth=.6;c.stroke();c.fillStyle=rect.focused?this.palette.labelText:this.palette.labelMuted;c.fillText(rect.name,rect.x+6,rect.y+15);
  }
 }
 tick(now){
  requestAnimationFrame(this.tick);if(document.hidden||now-this.last<(this.cameraTarget||this.drag?0:32))return;
  const dt=Math.min(50,now-this.last);this.last=now;
  if(!this.width||!this.height||document.body.classList.contains('notes-only')||document.body.classList.contains('note-focus')||(this.mobile.matches&&document.body.dataset.mobile!=='map'))return;
  const navigating=this.advanceCamera(dt);
  if(!this.moving&&!this.dirty&&!navigating)return;
  if(this.moving){this.time+=dt/1000;if(!navigating&&!this.drag&&document.activeElement!==this.canvas)this.rotation+=dt*.000018;}
  this.draw();this.dirty=false;
 }
 draw(){
  const c=this.ctx,w=this.width,h=this.height;if(!w||!h)return;c.clearRect(0,0,w,h);this.atmosphere();
  if(!this.nodes.length){this.points.clear();this.labelRects=[];return;}
  c.globalAlpha=this.selected ? .65 : 1;this.drawCortex();c.globalAlpha=1;this.points.clear();this.nodes.forEach(n=>this.points.set(n.id,this.project(n.brain)));
  this.drawConnections();this.drawNotes();
 }
 hit(x,y){for(const label of this.labelRects)if(x>=label.x&&x<=label.x+label.w&&y>=label.y&&y<=label.y+label.h)return this.ids.get(label.id);let best=null,min=18;for(const n of this.nodes){if(!this.filter(n))continue;const p=this.points.get(n.id);if(!p)continue;const d=Math.hypot(p.x-x,p.y-y);if(d<min){best=n;min=d;}}return best;}
 events(){const c=this.canvas,tip=document.querySelector('#graph-tooltip'),pos=e=>{const r=c.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top};};c.onpointerdown=e=>{this.cameraTarget=null;const p=pos(e);this.pointers.set(e.pointerId,p);c.setPointerCapture(e.pointerId);this.drag={...p,startX:p.x,startY:p.y,moved:false};if(this.pointers.size>1){this.pinching=true;const[a,b]=[...this.pointers.values()];this.distance=Math.hypot(a.x-b.x,a.y-b.y);}tip.hidden=true;};c.onpointermove=e=>{const p=pos(e);if(this.pointers.has(e.pointerId))this.pointers.set(e.pointerId,p);if(this.pointers.size>1){const[a,b]=[...this.pointers.values()],d=Math.hypot(a.x-b.x,a.y-b.y);if(this.distance)this.zoom=Math.max(.4,Math.min(3,this.zoom*d/this.distance));this.distance=d;this.dirty=true;return;}if(this.drag){const dx=p.x-this.drag.x,dy=p.y-this.drag.y;if(Math.hypot(p.x-this.drag.startX,p.y-this.drag.startY)>5)this.drag.moved=true;this.rotation+=dx*.006;this.tilt=Math.max(-1,Math.min(1,this.tilt+dy*.006));this.drag.x=p.x;this.drag.y=p.y;this.dirty=true;return;}const n=this.hit(p.x,p.y);this.hover=n?.id||null;c.style.cursor=n?'pointer':'grab';tip.hidden=!n;if(n){tip.textContent=n.kind==='folder'?n.title+' · Folder · '+n.count+(n.count===1?' item':' items'):n.title+' · '+n.degree+(n.degree===1?' connection':' connections');tip.style.left=Math.max(10,Math.min(p.x+17,this.width-240))+'px';tip.style.top=Math.max(75,p.y-35)+'px';}this.dirty=true;};const release=e=>{const p=pos(e);if(this.drag&&!this.drag.moved&&!this.pinching){const n=this.hit(p.x,p.y);if(n)this.onSelect(n.id);}this.pointers.delete(e.pointerId);this.drag=null;this.distance=null;if(!this.pointers.size)this.pinching=false;};c.onpointerup=release;c.onpointercancel=e=>{this.pointers.delete(e.pointerId);this.drag=null;this.pinching=false;};c.onpointerleave=()=>{tip.hidden=true;this.hover=null;this.dirty=true;};c.addEventListener('wheel',e=>{if(e.ctrlKey||e.metaKey||e.altKey||e.shiftKey)return;e.preventDefault();const units=e.deltaMode===1?16:e.deltaMode===2?this.height:1;this.zoomBy(Math.exp(-Math.max(-240,Math.min(240,e.deltaY*units))*.001));},{passive:false});}
};
