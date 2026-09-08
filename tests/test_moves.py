import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from store import Store, Problem, atomic
from filemoves import link_spans, resolve_link


class MoveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / 'state')
        self.brain = self.store.add('Move laboratory')
        self.bid, self.root = self.brain['id'], Path(self.brain['root'])
        for folder in ['Ideas', 'Projects', 'Projects/Nested']:
            self.store.folder(self.bid, folder)

    def tearDown(self):
        self.temp.cleanup()

    def note(self, path, text):
        self.store.write(self.bid, path, text, None)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_graph_and_reader_share_shortest_unique_path_resolution(self):
        cases = json.loads((Path(__file__).parent / 'link-resolution.json').read_text())
        for item in cases:
            with self.subTest(item['name']):
                self.assertEqual(resolve_link(item['target'], item['source'], set(item['paths']), item['kind']), item['expected'])

    def test_shortened_wikilinks_produce_edges_from_full_brain_and_survive_move(self):
        self.store.folder(self.bid, 'wiki')
        self.store.folder(self.bid, 'wiki/topics')
        self.note('wiki/topics/migration.md', '# Migration\n[[topics/code|Code]] and [[topics/routines#Setup]]')
        self.note('wiki/topics/code.md', '# Code')
        self.note('wiki/topics/routines.md', '# Routines')
        graph = self.store.graph(self.bid)
        adjacent = {edge['target'] if edge['source'] == 'wiki/topics/migration' else edge['source'] for edge in graph['edges']}
        self.assertEqual(adjacent, {'wiki/topics/code', 'wiki/topics/routines'})
        self.store.move(self.bid, 'wiki/topics/code.md', 'Projects', 'note')
        self.assertIn('[[Projects/code|Code]]', (self.root / 'wiki/topics/migration.md').read_text())
        self.assertEqual(len(self.store.graph(self.bid)['edges']), 2)

    def test_move_note_and_return_to_root_keeps_identity_content_and_links(self):
        self.note('One.md', '# One\n[Next](Ideas/Two.md#section)\n')
        self.note('Ideas/Two.md', '# Two\n[[One|Start]] and [Start](../One.md)\n')
        before = self.snapshot()
        result = self.store.move(self.bid, 'One.md', 'Projects', 'note')
        self.assertTrue(result['changed'])
        self.assertFalse((self.root / 'One.md').exists())
        self.assertIn('[Next](../Ideas/Two.md#section)', (self.root / 'Projects/One.md').read_text())
        self.assertEqual((self.root / 'Ideas/Two.md').read_text(), '# Two\n[[One|Start]] and [Start](../Projects/One.md)\n')
        self.store.move(self.bid, 'Projects/One.md', '', 'note')
        self.assertEqual(before, self.snapshot())
        self.assertEqual(len(self.store.graph(self.bid)['edges']), 1)

    def test_nested_folder_moves_every_file_and_preserves_internal_and_external_links(self):
        self.note('Ideas/One.md', '# One\n[[Projects/Nested/Two|Two]]\n[Two](../Projects/Nested/Two.md)\n')
        self.note('Projects/Nested/Two.md', '# Two\n[One](../../Ideas/One.md)\n![Picture](pic.png)')
        (self.root / 'Projects/Nested/pic.png').write_bytes(b'attachment')
        (self.root / 'Projects/Nested/.metadata').write_bytes(b'hidden attachment')
        self.store.folder(self.bid, 'Projects/Nested/Empty')
        result = self.store.move(self.bid, 'Projects', 'Ideas', 'folder')
        self.assertEqual(result['path'], 'Ideas/Projects')
        self.assertFalse((self.root / 'Projects').exists())
        self.assertTrue((self.root / 'Ideas/Projects/Nested/Empty').is_dir())
        self.assertEqual((self.root / 'Ideas/Projects/Nested/pic.png').read_bytes(), b'attachment')
        self.assertEqual((self.root / 'Ideas/Projects/Nested/.metadata').read_bytes(), b'hidden attachment')
        self.assertEqual((self.root / 'Ideas/One.md').read_text(), '# One\n[[Projects/Nested/Two|Two]]\n[Two](Projects/Nested/Two.md)\n')
        self.assertIn('[One](../../One.md)', (self.root / 'Ideas/Projects/Nested/Two.md').read_text())
        self.assertIn('![Picture](pic.png)', (self.root / 'Ideas/Projects/Nested/Two.md').read_text())

    def test_spaces_unicode_anchors_titles_references_and_images(self):
        self.note('Ideas/Olá mundo.md', '# Original')
        self.note('Start.md', '[Go](<Ideas/Olá mundo.md#Olá> "A title")\n[ref]: Ideas/Ol%C3%A1%20mundo.md#part "Title"\n[[Ideas/Olá mundo#Heading|Alias]]\n[Site](https://example.com/Ideas/Olá.md)\n![Map](Ideas/map.png)')
        (self.root / 'Ideas/map.png').write_bytes(b'image')
        self.store.move(self.bid, 'Ideas', 'Projects', 'folder')
        content = (self.root / 'Start.md').read_text()
        self.assertIn('<Projects/Ideas/Ol%C3%A1%20mundo.md#Olá> "A title"', content)
        self.assertIn('[ref]: Projects/Ideas/Ol%C3%A1%20mundo.md#part "Title"', content)
        # The shortened wikilink remains unique after the folder move.
        self.assertIn('[[Ideas/Olá mundo#Heading|Alias]]', content)
        self.assertEqual(resolve_link('Ideas/Olá mundo', 'Start.md', {'Projects/Ideas/Olá mundo.md'}, 'wiki'), 'Projects/Ideas/Olá mundo.md')
        self.assertIn('(https://example.com/Ideas/Olá.md)', content)
        self.assertIn('![Map](Projects/Ideas/map.png)', content)

    def test_metadata_code_and_unchanged_bytes_are_not_reserialized(self):
        self.note('Ideas/A.md', '# A')
        content = '---\r\nexample: "[[Ideas/A]]"\r\n---\r\n\r\n~~~md\r\n[[Ideas/A]]\r\n~~~\r\n`[x](Ideas/A.md)`\r\n    [[Ideas/A]]\r\n\r\n[[Ideas/A|Alias]]  \r\n'
        self.note('Guide.md', content)
        self.store.move(self.bid, 'Ideas/A.md', 'Projects', 'note')
        expected = content.replace('[[Ideas/A|Alias]]', '[[Projects/A|Alias]]')
        self.assertEqual((self.root / 'Guide.md').read_bytes(), expected.encode())

    def test_relative_links_keep_the_right_note_when_basenames_collide(self):
        self.note('One.md', '# Root One')
        self.note('Ideas/One.md', '# Ideas One')
        self.note('Ideas/Reader.md', '[One](One.md)\n[[Ideas/One]]')
        self.store.move(self.bid, 'Ideas/Reader.md', 'Projects', 'note')
        self.assertEqual((self.root / 'Projects/Reader.md').read_text(), '[One](../Ideas/One.md)\n[[Ideas/One]]')

    def test_noop_collision_self_and_descendants_do_not_change_files(self):
        self.note('A.md', 'original')
        self.note('Ideas/A.md', 'destination')
        before = self.snapshot()
        self.assertFalse(self.store.move(self.bid, 'A.md', '', 'note')['changed'])
        for source, destination, kind in [('A.md', 'Ideas', 'note'), ('Projects', 'Projects', 'folder'), ('Projects', 'Projects/Nested', 'folder'), ('Ideas', 'missing', 'folder'), ('missing.md', 'Ideas', 'note')]:
            with self.assertRaises(Problem):
                self.store.move(self.bid, source, destination, kind)
            self.assertEqual(self.snapshot(), before)

    def test_readonly_symlinks_path_escape_and_invalid_kinds_are_rejected(self):
        self.note('A.md', 'original')
        outside = Path(self.temp.name) / 'outside';outside.mkdir();(outside / 'B.md').write_text('outside')
        read_only = self.store.add('Protected', str(outside), False)
        with self.assertRaises(Problem) as error:
            self.store.move(read_only['id'], 'B.md', '', 'note')
        self.assertEqual(error.exception.status, 403)
        (self.root / 'Linked').symlink_to(outside)
        for source, destination, kind in [('A.md', '../outside', 'note'), ('A.md', 'Linked', 'note'), ('A.md', '/tmp', 'note'), ('../outside/B.md', '', 'note'), ('A.md', '.hidden', 'note'), ('A.md', '', 'other')]:
            with self.assertRaises(Problem):
                self.store.move(self.bid, source, destination, kind)
        (self.root / 'Ideas/.private').mkdir()
        (self.root / 'Ideas/.private/link').symlink_to(outside)
        with self.assertRaises(Problem):
            self.store.move(self.bid, 'Ideas', 'Projects', 'folder')
        self.assertEqual((outside / 'B.md').read_text(), 'outside')
        self.assertEqual((self.root / 'A.md').read_text(), 'original')

    def test_stale_open_note_revision_prevents_move(self):
        self.note('A.md', 'old')
        opened = self.store.read(self.bid, 'A.md')
        (self.root / 'A.md').write_text('external edit')
        with self.assertRaises(Problem) as error:
            self.store.move(self.bid, 'A.md', 'Ideas', 'note', opened)
        self.assertEqual(error.exception.status, 409)
        self.assertEqual((self.root / 'A.md').read_text(), 'external edit')
        self.assertFalse((self.root / 'Ideas/A.md').exists())

    def test_link_update_failure_rolls_back_folder_and_rewritten_notes(self):
        self.note('Ideas/A.md', '[B](../B.md)')
        self.note('B.md', '[A](Ideas/A.md)')
        before = self.snapshot()
        calls = 0
        def fail_once(path, data):
            nonlocal calls
            if str(path).endswith('.md'):
                calls += 1
                if calls == 2:
                    raise OSError('Simulated disk failure')
            return atomic(path, data)
        with patch('filemoves.atomic', side_effect=fail_once):
            with self.assertRaises(Problem) as error:
                self.store.move(self.bid, 'Ideas', 'Projects', 'folder')
        self.assertEqual(error.exception.status, 500)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.root / 'Projects/Ideas').exists())
        manifest = next((self.store.home / 'backups').rglob('move.json'))
        self.assertEqual(json.loads(manifest.read_text())['state'], 'rolled-back')

    def test_recovery_copies_preserve_exact_originals_and_open_note_can_save_after_move(self):
        self.note('A.md', '[B](Ideas/B.md)')
        self.note('Ideas/B.md', 'content')
        opened = self.store.read(self.bid, 'A.md')
        self.store.move(self.bid, 'A.md', 'Projects', 'note', opened)
        manifest_path = next((self.store.home / 'backups').rglob('move.json'))
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest['state'], 'complete')
        self.assertEqual((manifest_path.parent / manifest['notes']['A.md']).read_text(), opened['content'])
        relocated = self.store.read(self.bid, 'Projects/A.md')
        self.store.write(self.bid, relocated['path'], relocated['content'] + '\nNew line', relocated['revision'])
        self.assertFalse((self.root / 'A.md').exists())


if __name__ == '__main__':
    unittest.main()
