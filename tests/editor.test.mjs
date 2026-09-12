import {test} from 'node:test';
import assert from 'node:assert/strict';
import {EditorState,TextSelection} from 'prosemirror-state';
import {toggleMark,setBlockType} from 'prosemirror-commands';
import {parseSource,serializeSource,schema,safeLink,findLinkNotes,noteFilename} from '../src/editor-model.mjs';

const fixtures=[
 '', '\n\n', '# New idea\n\n',
 '\uFEFF---\r\nkind: idea\r\n---\r\n\r\n# Title\r\n\r\nText with  spaces.\r\n',
 '---\ntags: [one, two]\n---\n\n# Title\n\nOne *italic*, **bold**, ~~gone~~ and `code`.\n\n- One\n  - Nested\n\n2. Next\n3. Last\n',
 '# Links\n\n[[Projects/Another|A note]] and [site](https://example.com "Title").\n',
 'A [reference][id].\n\n[id]: https://example.com\n\nAnother paragraph.\n',
 '---\nmeta: keep\n---\n\n# Title\n\n| Name | Value |\n|---|---|\n| X | **Two** |\n\n- [ ] Task\n\n> [!note]\n> Callout\n\n<div data-x="keep">Original</div>\n\n$$math$$\n\n![[picture.png]]\n\n```dataview\nLIST\n```\n'
];
test('opening and saving without changes preserves exact source, including extensions and CRLF',()=>{
 for(const source of fixtures){const loaded=parseSource(source);assert.equal(serializeSource(loaded.doc,loaded),source);}
});
test('editing ordinary text preserves frontmatter, unrelated formatting, tables, tasks, HTML and references',()=>{
 const source='---\nkind: project\n---\n\n# Title\n\nChange this paragraph.\n\n|A|B|\n|-|-|\n|1|2|\n\n- [x] Done\n\n<div>preserve</div>\n\n[ref]: https://example.com\n';
 const loaded=parseSource(source);let pos;
 loaded.doc.descendants((n,p)=>{if(n.isText&&n.text==='Change this paragraph.')pos=p;});
 const doc=EditorState.create({doc:loaded.doc}).tr.insertText('Revised',pos,pos+6).doc;
 const result=serializeSource(doc,loaded);
 assert(result.startsWith('---\nkind: project\n---\n\n# Title\n\nRevised this paragraph.'));
 assert(result.includes(source.slice(source.indexOf('|A|B|'))));
});
test('visual headings, bold and note links serialize into editable Markdown and round-trip semantically',()=>{
 const loaded=parseSource('A plain idea.\n'),state=EditorState.create({doc:loaded.doc});
 let next=state.apply(state.tr.setSelection(TextSelection.create(state.doc,1,2)));
 toggleMark(schema.marks.strong)(next,tr=>next=next.apply(tr));
 setBlockType(schema.nodes.heading,{level:2})(next,tr=>next=next.apply(tr));
 let result=serializeSource(next.doc,loaded);assert.match(result,/^## \*\*A\*\* plain idea\./);
 assert(parseSource(result).doc.eq(next.doc));
 const link=schema.nodes.wiki_link.create({target:'Projects/Another',label:'Related idea'});
 next=next.apply(next.tr.replaceSelectionWith(link));result=serializeSource(next.doc,loaded);
 assert(result.includes('[[Projects/Another|Related idea]]'));assert(parseSource(result).doc.eq(next.doc));
});
test('ordinary editing preserves wiki targets within the changed paragraph',()=>{
 const loaded=parseSource('Hello [[Other|friend]] and [example](https://example.com).\n');
 const doc=EditorState.create({doc:loaded.doc}).tr.insertText('Welcome',1,6).doc;
 const result=serializeSource(doc,loaded);assert(result.includes('Welcome [[Other|friend]]'));assert(parseSource(result).doc.eq(doc));
});
test('unsafe URLs do not become executable links; HTML and images stay inert',()=>{
 for(const url of ['javascript:alert(1)','data:text/html,<script>','file:///tmp/test','//example.com','vbscript:x'])assert.equal(safeLink(url),null);
 for(const url of ['https://example.com/a','mailto:hello@example.com','Notes/One.md'])assert.equal(safeLink(url),url);
 const doc=parseSource('<script>alert(1)</script>\n\n![Image](https://example.com/track.png)\n').doc;
 assert.equal(doc.firstChild.type.name,'raw_block');
 assert.equal(schema.nodes.image.spec.toDOM(doc.child(1).firstChild)[0],'span');
});
test('link search leads with Markdown filenames and ranks exact filename matches first',()=>{
 const notes=[
  {path:'wiki/topics/brain-lint.md',title:'Brain lint'},
  {path:'BRAIN.md',title:'Pedro Brain'},
  {path:'wiki/home.md',title:'Pedro Brain home'}
 ];
 assert.equal(noteFilename(notes[1]),'BRAIN.md');
 assert.deepEqual(findLinkNotes(notes,'brain').map(n=>n.path),['BRAIN.md','wiki/topics/brain-lint.md','wiki/home.md']);
 assert.deepEqual(findLinkNotes(notes,'pedro brain').map(n=>n.path),['BRAIN.md','wiki/home.md']);
});
