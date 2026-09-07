import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from store import Store, Problem, folder_path

class FolderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name).resolve()
        self.store=Store(self.root/'state')
        self.folder=self.root/"Writer's Brain with spaces"
        self.folder.mkdir()
        (self.folder/'Original.md').write_text('Original note, unchanged.')
    def tearDown(self):
        self.temp.cleanup()
    def test_copied_path_formats_preserve_spaces_and_apostrophes(self):
        path=str(self.folder)
        variants=[path,'  '+path+'  ',"'"+path+"'",'"'+path+'"','“'+path+'”','‘'+path+'’',self.folder.as_uri()]
        if os.name!='nt':variants.append(path.replace(' ','\\ ').replace("'","\\'"))
        for value in variants:
            with self.subTest(value=value):self.assertEqual(folder_path(value),self.folder)
    def test_quoted_folder_connects_readonly_without_changing_notes(self):
        brain=self.store.add('Tester',"'"+str(self.folder)+"'")
        self.assertEqual(brain['root'],str(self.folder));self.assertTrue(brain['readOnly'])
        self.assertEqual(self.store.graph(brain['id'])['nodes'][0]['title'],'Original')
        self.assertEqual((self.folder/'Original.md').read_text(),'Original note, unchanged.')
        with self.assertRaises(Problem):self.store.add('Duplicate',str(self.folder))
    def test_normalized_paths_do_not_bypass_readonly_protection(self):
        self.store.add('Protected',str(self.folder))
        with self.assertRaises(Problem) as caught:self.store.add('Parent alias','"'+str(self.root)+'"',True)
        self.assertEqual(caught.exception.status,403)
    def test_invalid_path_does_not_accidentally_create_a_brain(self):
        original=self.store.config.read_bytes()
        for value in ['', '""',{},'\x00','file://remote.example/folder']:
            with self.subTest(value=value),self.assertRaises(Problem):self.store.add('Invalid',value)
        self.assertEqual(self.store.config.read_bytes(),original)
    def test_browser_lists_only_folders_and_does_not_connect_or_modify(self):
        for name in ['Zulu','Alpha','.hidden']:(self.folder/name).mkdir()
        config=self.store.config.read_bytes()
        data=self.store.browse("'"+str(self.folder)+"'")
        self.assertEqual([f['name'] for f in data['folders']],['Alpha','Zulu'])
        self.assertEqual(data['parent'],str(self.root));self.assertTrue(data['selectable'])
        self.assertEqual(self.store.config.read_bytes(),config)
        self.assertEqual((self.folder/'Original.md').read_text(),'Original note, unchanged.')
    def test_folder_search_and_pagination_include_later_entries(self):
        for i in range(205):(self.folder/f'Folder {i:03}').mkdir()
        (self.folder/'Étoiles').mkdir()
        first=self.store.browse(str(self.folder));second=self.store.browse(str(self.folder),offset=first['nextOffset'])
        self.assertEqual(len(first['folders']),200);self.assertEqual(len(second['folders']),6)
        self.assertIsNone(second['nextOffset'])
        self.assertEqual(len({f['path'] for f in first['folders']+second['folders']}),206)
        matches=self.store.browse(str(self.folder),query='etoiles')
        self.assertEqual([f['name'] for f in matches['folders']],['Étoiles'])
    def test_permission_denied_is_reported_instead_of_an_empty_folder(self):
        with patch('store.os.scandir',side_effect=PermissionError),self.assertRaises(Problem) as caught:self.store.browse(str(self.folder))
        self.assertEqual(caught.exception.status,403)
    def test_picker_home_has_desktop_shortcut_but_requires_specific_folder(self):
        (self.root/'Desktop').mkdir()
        with patch('store.Path.home',return_value=self.root):
            data=self.store.browse()
        self.assertFalse(data['selectable'])
        self.assertIn({'name':'Desktop','path':str(self.root/'Desktop')},data['places'])
    def test_invalid_search_and_missing_folder_return_clear_errors(self):
        for args in [{'query':{}},{'offset':-1},{'offset':True}]:
            with self.subTest(args=args),self.assertRaises(Problem):self.store.browse(str(self.folder),**args)
        with self.assertRaises(Problem) as caught:self.store.browse(str(self.root/'missing'))
        self.assertEqual(caught.exception.status,404)

if __name__=='__main__':unittest.main()
