import {Schema} from 'prosemirror-model';
import {schema as baseSchema,defaultMarkdownParser,defaultMarkdownSerializer,MarkdownParser,MarkdownSerializer} from 'prosemirror-markdown';
import MarkdownIt from 'markdown-it';

export function safeLink(value){
 const v=String(value||'').trim();
 if(/^(https?:\/\/|mailto:)/i.test(v)){try{return ['http:','https:','mailto:'].includes(new URL(v).protocol)?v:null;}catch{return null;}}
 if(v.startsWith('#'))return v;
 return v&&!/[\u0000-\u0020\\]/.test(v)&&!v.startsWith('//')&&!/^[a-z][\w+.-]*:/i.test(v)&&/\.md(?:#.*)?$/i.test(v)?v:null;
}
export function noteFilename(note){return String(note?.path||'').split('/').pop()||String(note?.title||'');}
function searchText(value){return String(value||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();}
export function findLinkNotes(notes,term='',limit=30){
 const query=searchText(term);
 return notes.map((note,index)=>{
  const file=searchText(noteFilename(note)),stem=file.replace(/\.md$/i,''),title=searchText(note.title),path=searchText(note.path);
  let rank=0;
  if(query){
   if(file===query||stem===query||path===query)rank=0;
   else if(file.startsWith(query)||stem.startsWith(query))rank=1;
   else if(title===query)rank=2;
   else if(path.startsWith(query))rank=3;
   else if(file.includes(query)||stem.includes(query))rank=4;
   else if(title.includes(query))rank=5;
   else if(path.includes(query))rank=6;
   else rank=Infinity;
  }
  return {note,index,rank,file};
 }).filter(item=>Number.isFinite(item.rank)).sort((a,b)=>a.rank-b.rank||a.file.localeCompare(b.file)||a.index-b.index).slice(0,limit).map(item=>item.note);
}
let nodes=baseSchema.spec.nodes.update('heading',{...baseSchema.spec.nodes.get('heading'),content:'inline*'});
nodes=nodes.update('image',{...nodes.get('image'),toDOM:n=>['span',{class:'note-image-placeholder',contenteditable:'false'},'Image: '+(n.attrs.alt||n.attrs.src)]});
nodes=nodes.addToEnd('wiki_link',{
 inline:true,group:'inline',atom:true,attrs:{target:{},label:{default:null}},
 toDOM:n=>['span',{class:'note-link','data-note-target':n.attrs.target,contenteditable:'false'},n.attrs.label||n.attrs.target.split('/').pop()],
 leafText:n=>n.attrs.label||n.attrs.target
});
nodes=nodes.addToEnd('raw_block',{
 group:'block',atom:true,isolating:true,attrs:{raw:{}},
 toDOM:n=>['div',{class:'preserved-block',contenteditable:'false'},['span',{class:'preserved-label'},'Embedded content · preserved'],['pre',n.attrs.raw]],
 leafText:n=>n.attrs.raw
});
let marks=baseSchema.spec.marks.update('link',{
 ...baseSchema.spec.marks.get('link'),
 parseDOM:[{tag:'a[href]',getAttrs:n=>safeLink(n.getAttribute('href'))?{href:safeLink(n.getAttribute('href')),title:n.getAttribute('title')}:false}],
 toDOM:m=>['a',{href:safeLink(m.attrs.href)||undefined,title:m.attrs.title,rel:'noopener noreferrer',target:/^https?:/i.test(m.attrs.href)?'_blank':undefined},0]
}).addToEnd('strike',{parseDOM:[{tag:'s'},{tag:'del'}],toDOM:()=>['s',0]});
export const schema=new Schema({nodes,marks});

const tokenizer=new MarkdownIt('commonmark',{html:true}).enable(['table','strikethrough']);
tokenizer.inline.ruler.before('link','wiki_link',(state,silent)=>{
 const m=state.src.slice(state.pos).match(/^\[\[([^\]\n|]+)(?:\|([^\]\n]*))?\]\]/);
 if(!m||state.src[state.pos-1]==='!')return false;
 if(!silent){const t=state.push('wiki_link','',0);t.meta={target:m[1],label:m[2]??null};}
 state.pos+=m[0].length;return true;
});
const tokenRules={...defaultMarkdownParser.tokens,wiki_link:{node:'wiki_link',getAttrs:t=>t.meta},s:{mark:'strike'}};
const serializer=new MarkdownSerializer({
 ...defaultMarkdownSerializer.nodes,
 wiki_link:(s,n)=>s.write('[['+n.attrs.target+(n.attrs.label!==null?'|'+n.attrs.label:'')+']]'),
 raw_block:(s,n)=>{s.write(n.attrs.raw);s.closeBlock(n);}
},{...defaultMarkdownSerializer.marks,strike:{open:'~~',close:'~~',mixable:true,expelEnclosingWhitespace:true}});
const rawNode=raw=>schema.nodes.raw_block.create({raw});

// Parse mapped top-level blocks independently using already-resolved inline tokens.
// Unsupported extensions remain opaque nodes. Untouched blocks retain their exact source.
export function parseSource(source){
 const eol=source.includes('\r\n')?'\r\n':'\n';
 let prefix='',body=source;
 const metadata=body.match(/^(?:\uFEFF)?---[^\S\r\n]*\r?\n[\s\S]*?\r?\n(?:---|\.\.\.)[^\S\r\n]*(?:\r?\n|$)/);
 if(metadata){prefix=metadata[0];body=body.slice(prefix.length);}
 const lines=body.match(/[^\n]*\n|[^\n]+$/g)||[];
 const tokens=tokenizer.parse(body,{}),blocks=[];
 for(let i=0;i<tokens.length;i++){
  const t=tokens[i];if(t.level!==0||!t.map||t.nesting<0)continue;
  let end=i+1;if(t.nesting===1){let depth=1;while(end<tokens.length&&depth){depth+=tokens[end].nesting;end++;}}
  blocks.push({start:t.map[0],end:t.map[1],tokens:tokens.slice(i,end)});i=end-1;
 }
 const records=[],children=[];
 let cursor=0;
 const append=(node,raw)=>{children.push(node);records.push({node,raw});};
 for(const block of blocks){
  const gap=lines.slice(cursor,block.start).join('');
  if(gap.trim())append(rawNode(gap),gap);else if(!children.length)prefix+=gap;else records[records.length-1].raw+=gap;
  const raw=lines.slice(block.start,block.end).join('');
  let node;
  try{
   // Preserve task-list markers, embeds, callouts and math until dedicated controls exist.
   if(/!\[\[|^\s*[-*+] \[[ xX]\]|^\s*>\s*\[!|\$\$|^\s*(?:::|%%)|\[\^[^\]]+\]/m.test(raw))throw Error('extension');
   const parsed=new MarkdownParser(schema,{parse:()=>block.tokens},tokenRules).parse('');
   if(parsed.childCount!==1)throw Error('unsupported block');
   node=parsed.firstChild;
  }catch{node=rawNode(raw);}
  append(node,raw);cursor=block.end;
 }
 const tail=lines.slice(cursor).join('');
 if(tail.trim())append(rawNode(tail),tail);else if(records.length)records[records.length-1].raw+=tail;else prefix+=tail;
 const doc=schema.node('doc',null,children.length?children:[schema.nodes.paragraph.create()]);
 return {source,prefix,eol,doc,records};
}

export function serializeSource(doc,loaded){
 if(doc.eq(loaded.doc))return loaded.source;
 const parts=[];
 doc.forEach(node=>{
  const old=loaded.records.find(r=>r.node===node)||loaded.records.find(r=>r.node.eq(node));
  let text=old?old.raw:node.type.name==='raw_block'?node.attrs.raw:serializer.serialize(schema.node('doc',null,[node])).replace(/\n/g,loaded.eol);
  if(!old&&text&&!text.endsWith(loaded.eol))text+=loaded.eol;
  parts.push({text,index:old?loaded.records.indexOf(old):-1});
 });
 let out=loaded.prefix;
 for(let i=0;i<parts.length;i++){
  const adjacent=i&&parts[i-1].index>=0&&parts[i].index===parts[i-1].index+1;
  const boundary=(out.match(/(?:\r?\n)*$/)?.[0]||'')+(parts[i].text.match(/^(?:\r?\n)*/)?.[0]||'');
  if(i&&!adjacent&&out&&!boundary.includes(loaded.eol+loaded.eol))out+=out.endsWith(loaded.eol)?loaded.eol:loaded.eol+loaded.eol;
  out+=parts[i].text;
 }
 return out;
}

export function createModel(source=''){
 let loaded=parseSource(source);
 return {get doc(){return loaded.doc;},load(next){loaded=parseSource(next);return loaded.doc;},serialize:doc=>serializeSource(doc,loaded)};
}
