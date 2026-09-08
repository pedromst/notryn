'use strict';
// Speech-state visualization, not a microphone or audio-amplitude analyser.
// The local speech APIs expose lifecycle events; the wave is illustrative.
window.IrisPresence=(()=>{
 const orb=document.querySelector('#orb'),wave=document.querySelector('#iris-wave'),echo=document.querySelector('#iris-wave-echo'),status=document.querySelector('#voice-status'),panel=document.querySelector('#agent');
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 let speaking=false,frame=0,started=0,lastBoundary=0;
 function flat(){wave.setAttribute('d','M35 120H205');echo.setAttribute('d','M35 120H205');}
 function draw(now){
  frame=0;if(!speaking||reduced.matches||document.hidden||panel.hidden)return;
  const time=(now-started)/1000,beat=Math.exp(-Math.max(0,now-lastBoundary)/190),amplitude=Math.min(1,time*5)*(10+8*Math.sin(time*3.1)**2+beat*9);
  let main='',second='';
  for(let i=0;i<=100;i++){
   const x=35+i*1.7,u=i/100,envelope=Math.sin(Math.PI*u)**2;
   const motion=Math.sin(u*27-time*8)*.62+Math.sin(u*49+time*5)*.24+Math.sin(u*14-time*3)*.14;
   main+=(i?'L':'M')+x.toFixed(1)+' '+(120+envelope*motion*amplitude).toFixed(2);
   second+=(i?'L':'M')+x.toFixed(1)+' '+(120+envelope*Math.sin(u*24-time*6)*amplitude*.57).toFixed(2);
  }
  wave.setAttribute('d',main);echo.setAttribute('d',second);frame=requestAnimationFrame(draw);
 }
 function sync(){cancelAnimationFrame(frame);frame=0;if(speaking&&!reduced.matches&&!document.hidden&&!panel.hidden)frame=requestAnimationFrame(draw);else flat();}
 return {
  set(mode,voice=false){speaking=mode==='speaking';orb.classList.toggle('speaking',speaking);orb.dataset.state=mode;status.textContent=mode==='preparing'?'Preparing voice…':speaking?'Speaking':voice?'Voice ready':'Ready when you are';if(speaking)started=performance.now();sync();},
  pulse(){lastBoundary=performance.now();},
  init(){new MutationObserver(sync).observe(panel,{attributes:true,attributeFilter:['hidden']});document.addEventListener('visibilitychange',sync);reduced.addEventListener('change',sync);}
 };
})();
IrisPresence.init();
