import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from store import Store, Problem

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.store=Store(self.root/'state');self.brain=self.store.add('Research');self.bid=self.brain['id']
    def tearDown(self):self.temp.cleanup()
    def test_new_install_is_empty_and_portable(self):
        self.assertEqual(Store(self.root/'empty').state()['brains'],[])
        self.assertEqual(Store(self.root/'state').brains[0]['id'],self.bid)
    def test_create_edit_backup_and_graph(self):
        self.store.folder(self.bid,'Ideas')
        self.store.write(self.bid,'Start.md','# Start\n\n[[Ideas/Next]]',None)
        self.store.write(self.bid,'Ideas/Next.md','# Next\n\n[Back](../Start.md)',None)
        graph=self.store.graph(self.bid);self.assertEqual(len(graph['edges']),1);self.assertEqual(len(graph['nodes']),2)
        first=self.store.read(self.bid,'Start.md');self.store.write(self.bid,'Start.md','# New content',first['revision'])
        backups=list((self.store.home/'backups'/self.bid).glob('*.md'));self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_text(),first['content'])
    def test_external_edit_is_not_overwritten(self):
        self.store.write(self.bid,'A.md','before',None);first=self.store.read(self.bid,'A.md');path=Path(self.brain['root'])/'A.md';path.write_text('written in another app')
        with self.assertRaises(Problem) as caught:self.store.write(self.bid,'A.md','my edit',first['revision'])
        self.assertEqual(caught.exception.status,409);self.assertEqual(path.read_text(),'written in another app')
    def test_duplicate_creation_does_not_replace(self):
        self.store.write(self.bid,'A.md','original',None)
        with self.assertRaises(Problem):self.store.write(self.bid,'A.md','replacement',None)
        self.assertEqual(self.store.read(self.bid,'A.md')['content'],'original')
    def test_readonly_vault_stays_intact(self):
        folder=self.root/'existing';folder.mkdir();(folder/'A.md').write_text('# Original');brain=self.store.add('Read only',str(folder),False)
        for action in [lambda:self.store.write(brain['id'],'A.md','changed',None),lambda:self.store.folder(brain['id'],'new')]:
            with self.assertRaises(Problem) as caught:action()
            self.assertEqual(caught.exception.status,403)
        self.assertEqual((folder/'A.md').read_text(),'# Original');self.assertEqual(list(folder.iterdir()),[folder/'A.md'])
    def test_brain_access_can_be_changed_without_touching_existing_files(self):
        folder=self.root/'access';folder.mkdir();note=folder/'A.md';note.write_text('# Original')
        brain=self.store.add('Access',str(folder),False);before=note.read_bytes()
        changed=self.store.set_access(brain['id'],True);self.assertFalse(changed['readOnly']);self.assertEqual(note.read_bytes(),before)
        self.store.write(brain['id'],'A.md','# Changed',self.store.read(brain['id'],'A.md')['revision'])
        changed=self.store.set_access(brain['id'],False);self.assertTrue(changed['readOnly'])
        with self.assertRaises(Problem):self.store.write(brain['id'],'A.md','# Again',self.store.read(brain['id'],'A.md')['revision'])
    def test_write_access_cannot_bypass_an_overlapping_readonly_brain(self):
        parent=self.root/'overlap';child=parent/'child';child.mkdir(parents=True)
        protected=self.store.add('Protected',str(parent),False);candidate=self.store.add('Candidate',str(child),False)
        with self.assertRaises(Problem) as caught:self.store.set_access(candidate['id'],True)
        self.assertEqual(caught.exception.status,403);self.assertTrue(self.store.get(protected['id'])['readOnly']);self.assertTrue(self.store.get(candidate['id'])['readOnly'])
    def test_readonly_cannot_be_reopened_through_parent(self):
        folder=self.root/'existing';folder.mkdir();self.store.add('Read only',str(folder),False)
        with self.assertRaises(Problem):self.store.add('Alias',str(self.root),True)
    def test_traversal_hidden_paths_symlinks_refused(self):
        external=self.root/'outside.md';external.write_text('outside');(Path(self.brain['root'])/'link.md').symlink_to(external);(Path(self.brain['root'])/'linked').symlink_to(self.root,target_is_directory=True)
        for path in ['../outside.md','/tmp/A.md','.env.md','a/../../x.md','linked/outside.md','link.md','x.txt','a\\b.md']:
            with self.assertRaises(Problem):self.store.write(self.bid,path,'changed',None)
        self.assertEqual(external.read_text(),'outside');self.assertFalse(any(n['id']=='link' for n in self.store.graph(self.bid)['nodes']))
    def test_same_content_does_not_create_backup(self):
        self.store.write(self.bid,'A.md','same',None);first=self.store.read(self.bid,'A.md');result=self.store.write(self.bid,'A.md','same',first['revision'])
        self.assertFalse(result['changed']);self.assertFalse((self.store.home/'backups').exists())
    def test_deleted_note_not_recreated_on_save(self):
        self.store.write(self.bid,'A.md','original',None);first=self.store.read(self.bid,'A.md');(Path(self.brain['root'])/'A.md').unlink()
        with self.assertRaises(Problem):self.store.write(self.bid,'A.md','new',first['revision'])
        self.assertFalse((Path(self.brain['root'])/'A.md').exists())
    def test_two_brains_are_separate(self):
        second=self.store.add('Another');self.store.write(self.bid,'A.md','one',None);self.store.write(second['id'],'A.md','two',None)
        self.assertEqual(self.store.read(self.bid,'A.md')['content'],'one');self.assertEqual(self.store.read(second['id'],'A.md')['content'],'two')
    def test_connected_folder_includes_wiki_logs_indexes_and_nested_notes_without_changing_files(self):
        root=self.root/'imported';root.mkdir()
        originals={'wiki/log.md':'# Alterações materiais', 'wiki/index.md':'# Índice compacto',
                   'wiki/perfil-pedro.md':'# Perfil do Pedro', 'wiki/projects/deep/project.md':'# Project',
                   'raw/archive/note.md':'# Archived note'}
        for path,content in originals.items():
            target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content,encoding='utf-8')
        (root/'wiki/empty').mkdir()
        brain=self.store.add('Imported',str(root),False)
        graph=self.store.graph(brain['id'])
        self.assertEqual({n['path'] for n in graph['nodes']},set(originals))
        self.assertEqual(graph['skipped'],0);self.assertIn('wiki/empty',graph['folders'])
        for path,content in originals.items():self.assertEqual((root/path).read_text(encoding='utf-8'),content)
if __name__=='__main__':unittest.main()
