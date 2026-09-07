'use strict';
const stage=document.querySelector('.brain-stage');
const brain=document.querySelector('.brain');
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
if(stage&&brain&&!reduced.matches){
  stage.addEventListener('pointermove',event=>{
    const box=stage.getBoundingClientRect();
    const x=(event.clientX-box.left)/box.width-.5;
    const y=(event.clientY-box.top)/box.height-.5;
    brain.style.setProperty('--brain-x',`${(-y*4).toFixed(2)}deg`);
    brain.style.setProperty('--brain-y',`${(x*6).toFixed(2)}deg`);
  });
  stage.addEventListener('pointerleave',()=>{
    brain.style.setProperty('--brain-x','0deg');
    brain.style.setProperty('--brain-y','0deg');
  });
}
