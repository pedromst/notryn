'use strict';
// Convert a complete Markdown index into one navigable folder layer.
window.NeuraHierarchy=(()=>{
 const normalize=path=>String(path||'').replace(/^\/+|\/+$/g,'');
 const parent=path=>normalize(path).split('/').slice(0,-1).join('/');
 const name=path=>normalize(path).split('/').pop()||'';
 const clean=value=>String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 const folderId=path=>'@folder:'+normalize(path);
 function ancestors(path){
  const parts=normalize(path).split('/').filter(Boolean),result=[];
  for(let i=0;i<parts.length;i++)result.push({path:parts.slice(0,i+1).join('/'),name:parts[i]});
  return result;
 }
 function directFolders(data,path=''){
  path=normalize(path);return(data.folders||[]).filter(folder=>parent(folder)===path).sort((a,b)=>name(a).localeCompare(name(b)));
 }
 function navigation(data,path=''){
  path=normalize(path);return[...(path?[path]:[]),...directFolders(data,path)];
 }
 function view(data,path='',query=''){
  path=normalize(path);query=clean(query.trim());const allNodes=data.nodes||[],allEdges=data.edges||[];
  // Keep folder colors consistent across layers, search and theme changes.
  const foldersByPath=[...new Set([...(data.folders||[]),...allNodes.map(node=>normalize(node.folder))])].filter(Boolean).sort((a,b)=>a.localeCompare(b));
  const colorGroups=['',...foldersByPath].map(folderId),asNote=node=>({...node,kind:'note',group:folderId(node.folder)});
  if(query){
   const nodes=allNodes.filter(node=>clean(node.title+' '+node.path).includes(query)).map(asNote);
   const ids=new Set(nodes.map(node=>node.id));
   return{path,nodes,colorGroups,edges:allEdges.filter(edge=>ids.has(edge.source)&&ids.has(edge.target)),folderCount:0,noteCount:nodes.length,search:true};
  }
  const folders=directFolders(data,path),folderSet=new Set(folders),notes=allNodes.filter(node=>normalize(node.folder)===path).map(asNote);
  const folderNodes=folders.map(folder=>{
   const directNoteCount=allNodes.filter(node=>normalize(node.folder)===folder).length,directFolderCount=directFolders(data,folder).length;
   const totalNotes=allNodes.filter(node=>normalize(node.folder)===folder||normalize(node.folder).startsWith(folder+'/')).length;
   return{id:folderId(folder),title:name(folder),path:folder,folder:path,kind:'folder',group:folderId(folder),count:directNoteCount+directFolderCount,totalNotes};
  });
  const nodes=[...folderNodes,...notes],byId=new Map(allNodes.map(node=>[node.id,node]));
  function bucket(node){
   if(!node)return null;const nodeFolder=normalize(node.folder);if(nodeFolder===path)return node.id;
   const prefix=path?path+'/':'';if(!nodeFolder.startsWith(prefix))return null;
   const first=nodeFolder.slice(prefix.length).split('/')[0],folder=prefix+first;
   return folderSet.has(folder)?folderId(folder):null;
  }
  const seen=new Set(),edges=[];
  for(const edge of allEdges){
   const source=bucket(byId.get(edge.source)),target=bucket(byId.get(edge.target));if(!source||!target||source===target)continue;
   const key=[source,target].sort().join('\n');if(seen.has(key))continue;seen.add(key);edges.push({source,target});
  }
  return{path,nodes,colorGroups,edges,folderCount:folderNodes.length,noteCount:notes.length,search:false};
 }
 return{normalize,parent,name,folderId,ancestors,directFolders,navigation,view};
})();
