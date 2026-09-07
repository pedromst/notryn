import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from store import Store, Problem


class RemovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name).resolve() / 'state'
        self.store = Store(self.home)
        self.brain = self.store.add('Ideas laboratory')
        self.bid = self.brain['id'];self.root = Path(self.brain['root'])
        self.store.folder(self.bid, 'Projects');self.store.folder(self.bid, 'Projects/Nested');self.store.folder(self.bid, 'Archive')
        self.store.write(self.bid, 'Start.md', '# Start\n[[Projects/Next]]\n[Next](Projects/Next.md)', None)
        self.store.write(self.bid, 'Projects/Next.md', '# Next\n[[Start]]', None)
        self.store.write(self.bid, 'Projects/Nested/Deep.md', '# Deep\n[[Start]]', None)

    def tearDown(self):
        self.temp.cleanup()

    def contents(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}

    def remove(self, path, kind='note', device=False, brain=None):
        preview = self.store.removal_preview(brain or self.bid, path, kind)
        return self.store.remove(preview['id'], device, preview['name'] if device and kind=='brain' else '')

    def forget(self, entry):
        return self.store.forget(entry, self.store.forget_preview(entry)['revision'])

    def test_forget_removed_brain_allows_reconnect_and_keeps_all_files(self):
        before=self.contents()
        child=self.remove('Projects/Next.md')
        whole=self.remove('', 'brain')
        self.assertEqual(self.store.forget_preview(whole['entry'])['count'],2)
        result=self.forget(whole['entry'])
        self.assertEqual(before,self.contents())
        reopened=Store(self.home)
        self.assertEqual(reopened.brains,[]);self.assertEqual(reopened.removed_items()['items'],[])
        fresh=reopened.add('Connected again',str(self.root),False)
        self.assertTrue(fresh['readOnly']);self.assertEqual(len(reopened.graph(fresh['id'])['nodes']),3)
        archive=json.loads(Path(result['recoveryPath']).read_text())
        self.assertEqual(len(archive['items']),2)
        self.assertEqual(archive['brain']['root'],str(self.root))

    def test_forget_hidden_note_or_folder_clears_mask_without_changing_files(self):
        before=self.contents()
        entry=self.remove('Projects', 'folder');self.forget(entry['entry'])
        entry=self.remove('Start.md');self.forget(entry['entry'])
        self.assertEqual(before,self.contents());self.assertEqual(len(self.store.graph(self.bid)['nodes']),3)
        self.assertEqual(self.store.removed_items()['items'],[])

    def test_forget_brain_preserves_child_trash_and_recovery_metadata(self):
        child=self.remove('Start.md',device=True)
        entry=next(r for r in self.store.removals if r['id']==child['entry'])
        payload=Path(entry['payload']);raw=payload.read_bytes();inode=payload.stat().st_ino
        whole=self.remove('', 'brain')
        self.assertTrue(self.store.forget_preview(whole['entry'])['hasTrash'])
        result=self.forget(whole['entry'])
        self.assertEqual(payload.read_bytes(),raw);self.assertEqual(payload.stat().st_ino,inode)
        self.assertTrue((payload.parent/'recovery.json').is_file());self.assertFalse((self.root/'Start.md').exists())
        self.assertEqual(json.loads(Path(result['recoveryPath']).read_text())['items'][0]['payload'],str(payload))

    def test_forget_checks_stale_review_and_rolls_back_failed_persistence(self):
        removed=self.remove('Start.md');review=self.store.forget_preview(removed['entry'])
        self.remove('Projects/Next.md')
        with self.assertRaises(Problem) as error:self.store.forget(removed['entry'],review['revision'])
        self.assertEqual(error.exception.status,409)
        before=self.contents();config=self.store.config.read_bytes()
        with patch.object(self.store,'persist',side_effect=OSError('full')):
            with self.assertRaises(Problem):self.forget(removed['entry'])
        self.assertEqual(self.store.config.read_bytes(),config);self.assertEqual(before,self.contents())
        self.assertEqual(len(self.store.removed_items()['items']),2)
        with self.assertRaises(Problem):self.store.forget('missing','anything')

    def test_note_default_removes_from_index_and_direct_api_not_from_device(self):
        before=self.contents();result=self.remove('Projects/Next.md')
        self.assertEqual(before,self.contents());self.assertEqual(result['mode'],'hidden')
        self.assertNotIn('Projects/Next', {n['id'] for n in self.store.graph(self.bid)['nodes']})
        with self.assertRaises(Problem):self.store.read(self.bid,'Projects/Next.md')
        with self.assertRaises(Problem):self.store.write(self.bid,'Projects/Next.md','overwrite',None)
        persisted=Store(self.home);self.assertEqual(len(persisted.removed_items()['items']),1)
        persisted.restore(result['entry']);self.assertEqual(before,self.contents())
        self.assertEqual(len(persisted.graph(self.bid)['nodes']),3)

    def test_folder_default_includes_descendants_and_keeps_every_byte(self):
        (self.root/'Projects/asset.bin').write_bytes(b'attachment');(self.root/'Projects/.metadata').write_text('local settings')
        before=self.contents();result=self.remove('Projects','folder')
        graph=self.store.graph(self.bid);self.assertEqual([n['id'] for n in graph['nodes']],['Start'])
        self.assertEqual(graph['folders'],['Archive']);self.assertEqual(before,self.contents())
        for fn in [lambda:self.store.folder(self.bid,'Projects/New'),lambda:self.store.move(self.bid,'Start.md','Projects','note')]:
            with self.assertRaises(Problem):fn()
        self.store.restore(result['entry']);self.assertEqual(before,self.contents());self.assertEqual(len(self.store.graph(self.bid)['nodes']),3)

    def test_remove_and_restore_brain_keeps_folder_and_settings_and_last_brain_works(self):
        before=self.contents();result=self.remove('','brain')
        self.assertEqual(self.store.state()['brains'],[]);self.assertEqual(before,self.contents())
        with self.assertRaises(Problem):self.store.graph(self.bid)
        with self.assertRaises(Problem):self.store.add('Again',str(self.root),True)
        persisted=Store(self.home);persisted.restore(result['entry'])
        brain=persisted.state()['brains'][0];self.assertEqual(brain['id'],self.bid);self.assertFalse(brain['readOnly']);self.assertEqual(before,self.contents())

    def test_readonly_can_be_hidden_but_cannot_trash_or_bypass_protection_after_disconnect(self):
        root=Path(self.temp.name).resolve()/'readonly';root.mkdir();(root/'A.md').write_text('original')
        brain=self.store.add('Protected',str(root),False)
        preview=self.store.removal_preview(brain['id'],'A.md','note');self.assertFalse(preview['canTrash'])
        with self.assertRaises(Problem) as error:self.store.remove(preview['id'],True)
        self.assertEqual(error.exception.status,403)
        result=self.store.remove(preview['id']);self.store.restore(result['entry'])
        result=self.remove('','brain',brain=brain['id'])
        with self.assertRaises(Problem):self.store.add('Alias',str(root.parent),True)
        self.store.restore(result['entry']);self.assertTrue(self.store.get(brain['id'])['readOnly'])
        self.assertEqual((root/'A.md').read_text(),'original')

    def test_trash_note_restores_exact_bytes_inode_and_no_overwrite_on_collision(self):
        original=self.root/'Start.md';raw=original.read_bytes();inode=original.stat().st_ino
        result=self.remove('Start.md',device=True);self.assertFalse(original.exists())
        entry=self.store.removals[0];self.assertEqual(Path(entry['payload']).read_bytes(),raw)
        self.assertNotIn('payload',self.store.removed_items()['items'][0])
        original.write_text('new external note')
        with self.assertRaises(Problem) as error:self.store.restore(result['entry'])
        self.assertEqual(error.exception.status,409);self.assertEqual(original.read_text(),'new external note')
        original.rename(self.root/'External.md');self.store.restore(result['entry'])
        self.assertEqual(original.read_bytes(),raw);self.assertEqual(original.stat().st_ino,inode)

    def test_entire_brain_trash_requires_exact_name_and_preserves_hidden_files_and_symlinks(self):
        (self.root/'.obsidian').mkdir();(self.root/'.obsidian/preferences.json').write_text('{}')
        outside=Path(self.temp.name)/'outside.md';outside.write_text('outside')
        (self.root/'shortcut').symlink_to(outside)
        before=self.contents();preview=self.store.removal_preview(self.bid,'','brain')
        with self.assertRaises(Problem):self.store.remove(preview['id'],True,'wrong name')
        self.assertTrue(self.root.exists())
        result=self.store.remove(preview['id'],True,self.brain['name']);self.assertFalse(self.root.exists());self.assertEqual(self.store.state()['brains'],[])
        self.store.restore(result['entry']);self.assertEqual(self.contents(),before);self.assertTrue((self.root/'shortcut').is_symlink());self.assertEqual(outside.read_text(),'outside')

    def test_folder_trash_and_restore_preserve_nested_items(self):
        before=self.contents();result=self.remove('Projects','folder',device=True)
        self.assertFalse((self.root/'Projects').exists());self.assertEqual(len(self.store.graph(self.bid)['nodes']),1)
        self.store.restore(result['entry']);self.assertEqual(before,self.contents())

    def test_restore_parent_before_child_and_brain_before_items(self):
        note=self.remove('Projects/Next.md');folder=self.remove('Projects','folder');brain=self.remove('','brain')
        with self.assertRaises(Problem):self.store.restore(note['entry'])
        self.store.restore(brain['entry'])
        with self.assertRaises(Problem):self.store.restore(note['entry'])
        self.store.restore(folder['entry']);self.store.restore(note['entry']);self.assertEqual(self.store.removals,[])

    def test_changed_files_stale_review_explicit_option_and_consumed_tokens(self):
        preview=self.store.removal_preview(self.bid,'Start.md','note')
        with self.assertRaises(Problem):self.store.remove(preview['id'],'true')
        (self.root/'Start.md').write_text('external change')
        with self.assertRaises(Problem) as error:self.store.remove(preview['id'],True)
        self.assertEqual(error.exception.status,409)
        # View-only removal can still hide the path without overwriting the external edit.
        result=self.store.remove(preview['id']);self.assertEqual((self.root/'Start.md').read_text(),'external change')
        with self.assertRaises(Problem):self.store.remove(preview['id'])
        preview=self.store.removal_preview(self.bid,'Projects','folder')
        self.store.restore(result['entry'])
        with self.assertRaises(Problem):self.store.remove(preview['id'])

    def test_path_escape_and_nested_brain_are_not_trashed(self):
        for path in ['../outside.md','/tmp/secret.md','.hidden.md','Projects/../Start.md']:
            with self.assertRaises(Problem):self.store.removal_preview(self.bid,path,'note')
        child=self.store.add('Nested',str(self.root/'Projects/Nested'),True)
        preview=self.store.removal_preview(self.bid,'Projects','folder');self.assertFalse(preview['canTrash'])
        with self.assertRaises(Problem):self.store.remove(preview['id'],True)
        self.assertTrue(Path(child['root']).exists())

    def test_metadata_failure_does_not_remove_any_file_or_brain(self):
        before=self.contents();preview=self.store.removal_preview(self.bid,'Start.md','note')
        with patch.object(self.store,'persist',side_effect=OSError('disk full')):
            with self.assertRaises(Problem):self.store.remove(preview['id'],True)
        self.assertEqual(before,self.contents());self.assertEqual(self.store.removals,[]);self.assertEqual(len(Store(self.home).state()['brains']),1)

    def test_rename_failure_rolls_back_registration(self):
        preview=self.store.removal_preview(self.bid,'','brain');before=self.contents()
        with patch.object(Path,'rename',side_effect=OSError('permission denied')):
            with self.assertRaises(Problem):self.store.remove(preview['id'],True,self.brain['name'])
        self.assertEqual(before,self.contents());self.assertEqual(self.store.removals,[]);self.assertEqual(len(Store(self.home).state()['brains']),1)

    def test_restore_write_failure_keeps_recoverable_files(self):
        result=self.remove('Start.md',device=True)
        with patch.object(self.store,'persist',side_effect=OSError('disk full')):
            with self.assertRaises(Problem):self.store.restore(result['entry'])
        self.assertFalse((self.root/'Start.md').exists());self.assertTrue(Path(self.store.removals[0]['payload']).is_file())
        self.store.restore(result['entry']);self.assertTrue((self.root/'Start.md').exists())

    def test_interrupted_remove_and_restore_can_be_completed_after_restart(self):
        preview=self.store.removal_preview(self.bid,'Start.md','note')
        with patch.object(Path,'rename',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.store.remove(preview['id'],True)
        recovered=Store(self.home);self.assertTrue((self.root/'Start.md').exists());recovered.restore(recovered.removals[0]['id'])
        preview=recovered.removal_preview(self.bid,'Start.md','note');result=recovered.remove(preview['id'],True)
        with patch.object(recovered,'persist',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):recovered.restore(result['entry'])
        recovered=Store(self.home);self.assertTrue((self.root/'Start.md').exists());recovered.restore(result['entry']);self.assertEqual(recovered.removals,[])

    def test_hidden_and_trashed_paths_follow_a_parent_move(self):
        hidden=self.remove('Projects/Next.md');trashed=self.remove('Projects/Nested/Deep.md',device=True)
        self.store.move(self.bid,'Projects','Archive','folder')
        self.assertNotIn('Archive/Projects/Next',{n['id'] for n in self.store.graph(self.bid)['nodes']})
        self.store.restore(hidden['entry']);self.store.restore(trashed['entry'])
        self.assertTrue((self.root/'Archive/Projects/Next.md').exists());self.assertTrue((self.root/'Archive/Projects/Nested/Deep.md').exists())

    def test_removing_short_link_target_does_not_redirect_to_another_note(self):
        self.store.write(self.bid,'Next.md','# Another',None)
        self.store.write(self.bid,'Reader.md','# Reader\n[[Next]]',None)
        self.remove('Next.md',device=True)
        graph=self.store.graph(self.bid)
        self.assertIn('Next.md',graph['linkPaths'])
        self.assertFalse(any('Reader' in (e['source'],e['target']) for e in graph['edges']))


if __name__=='__main__':unittest.main()
