const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const context={window:{}};vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/hierarchy.js'),'utf8'),context);
const hierarchy=context.window.NeuraHierarchy;
const data={
 folders:['core','projects','projects/archive','projects/live'],
 nodes:[
  {id:'home',title:'Home',path:'home.md',folder:'',group:'Notes'},
  {id:'core/profile',title:'Profile',path:'core/profile.md',folder:'core',group:'System'},
  {id:'projects/alpha',title:'Alpha',path:'projects/alpha.md',folder:'projects',group:'Projects'},
  {id:'projects/archive/old',title:'Old',path:'projects/archive/old.md',folder:'projects/archive',group:'Projects'},
  {id:'projects/live/new',title:'New',path:'projects/live/new.md',folder:'projects/live',group:'Projects'}
 ],
 edges:[{source:'home',target:'projects/alpha'},{source:'projects/alpha',target:'projects/live/new'},{source:'projects/archive/old',target:'projects/live/new'}]
};

test('Brain root shows only direct folders and files, with deeper notes collapsed into folders',()=>{
 const view=hierarchy.view(data);
 assert.deepEqual(Array.from(view.nodes,n=>n.id),['@folder:core','@folder:projects','home']);
 assert.equal(view.folderCount,2);assert.equal(view.noteCount,1);
 assert.deepEqual(Array.from(view.edges,e=>[e.source,e.target]),[['home','@folder:projects']]);
});

test('opening a folder shows only that layer and projects links between visible items',()=>{
 const view=hierarchy.view(data,'projects');
 assert.deepEqual(Array.from(view.nodes,n=>n.id),['@folder:projects/archive','@folder:projects/live','projects/alpha']);
 assert.equal(view.folderCount,2);assert.equal(view.noteCount,1);
 assert.deepEqual(Array.from(view.edges,e=>[e.source,e.target]),[
  ['projects/alpha','@folder:projects/live'],
  ['@folder:projects/archive','@folder:projects/live']
 ]);
 assert.deepEqual(Array.from(hierarchy.ancestors('projects/live'),part=>part.path),['projects','projects/live']);
});

test('search remains global while folder browsing stays layered',()=>{
 const view=hierarchy.view(data,'projects/archive','new');
 assert.equal(view.search,true);assert.deepEqual(Array.from(view.nodes,n=>n.id),['projects/live/new']);
});

test('folder navigation keeps only the current layer, including a leaf with no subfolders',()=>{
 assert.deepEqual(Array.from(hierarchy.navigation(data)),['core','projects']);
 assert.deepEqual(Array.from(hierarchy.navigation(data,'projects')),['projects','projects/archive','projects/live']);
 assert.deepEqual(Array.from(hierarchy.navigation(data,'projects/live')),['projects/live']);
 assert.deepEqual(Array.from(hierarchy.navigation({...data,folders:[...data.folders,'projects/live/Notes']},'projects/live/Notes')),['projects/live/Notes']);
});

test('folder colors match their notes and remain stable when navigating, searching and changing theme',()=>{
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/graph.js'),'utf8'),context);
 const graph=Object.create(context.window.NeuraGraph.prototype);
 graph.brainPoint=()=>({x:0,y:0,z:0});graph.fit=()=>{};
 const views=[hierarchy.view(data),hierarchy.view(data,'projects'),hierarchy.view(data,'projects/live'),hierarchy.view(data,'core','new')];
 const original=JSON.stringify(data);
 for(const colors of [['#00ccaa','#cc99ff','#ffcc99','#99ccff','#cccc99'],['#00ff00','#aaff00','#00ffaa','#ffff00','#66aa66']]){
  graph.setTheme({colors,mesh:'#ffffff'});graph.setData(views[0]);
  assert.notEqual(graph.color(hierarchy.folderId('core')),graph.color(hierarchy.folderId('projects')));
  const projectColor=graph.color(hierarchy.folderId('projects')),liveColor=graph.color(hierarchy.folderId('projects/live'));
  graph.setData(views[1]);assert.equal(graph.color(graph.ids.get('projects/alpha').group),projectColor);
  assert.equal(graph.color(graph.ids.get('@folder:projects/live').group),liveColor);
  for(const view of views.slice(2)){
   graph.setData(view);assert.equal(graph.color(graph.ids.get('projects/live/new').group),liveColor);
  }
 }
 assert.equal(JSON.stringify(data),original);
});
