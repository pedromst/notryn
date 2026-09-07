import tempfile
import unittest
from pathlib import Path
from themes import omarchy_theme, parse_palette

DARK = 'background = "#1a1b26"\nforeground = "#a9b1d6"\naccent = "#7aa2f7"\n'


class ThemeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def palette(self, relative, content=DARK, name='Tokyo Night'):
        root = self.home/relative
        (root/'theme').mkdir(parents=True, exist_ok=True)
        (root/'theme/colors.toml').write_text(content)
        (root/'theme.name').write_text(name)
        return root

    def test_missing_is_not_detected_and_creates_nothing(self):
        self.assertEqual(omarchy_theme(self.home, {}), {'available': False})
        self.assertEqual(list(self.home.iterdir()), [])

    def test_new_state_path_and_live_palette_change(self):
        root = self.palette('.local/state/omarchy/current')
        self.assertEqual(omarchy_theme(self.home, {})['palette']['accent'], '#7aa2f7')
        new = DARK.replace('#1a1b26', '#fffcef') + 'mode = "light"\n'
        (root/'theme/colors.toml').write_text(new)
        actual = omarchy_theme(self.home, {})
        self.assertEqual(actual['palette']['background'], '#fffcef')
        self.assertEqual(actual['palette']['mode'], 'light')
        self.assertEqual((root/'theme/colors.toml').read_text(), new)
        self.assertNotIn(str(self.home), str(actual))

    def test_old_config_symlink_and_light_marker(self):
        theme = self.home/'themes/flexoki-light'
        theme.mkdir(parents=True)
        (theme/'colors.toml').write_text(DARK)
        (theme/'light.mode').touch()
        current = self.home/'.config/omarchy/current'
        current.mkdir(parents=True)
        (current/'theme').symlink_to(theme, target_is_directory=True)
        actual = omarchy_theme(self.home, {})
        self.assertEqual(actual['name'], 'Flexoki Light')
        self.assertEqual(actual['palette']['mode'], 'light')

    def test_state_takes_precedence_over_legacy_config(self):
        self.palette('.config/omarchy/current', name='Old')
        self.palette('.local/state/omarchy/current', name='New')
        self.assertEqual(omarchy_theme(self.home, {})['name'], 'New')

    def test_xdg_locations(self):
        self.palette('custom-state/omarchy/current')
        self.assertTrue(omarchy_theme(self.home, {'XDG_STATE_HOME': str(self.home/'custom-state')})['available'])

    def test_only_flat_hex_colors_are_accepted(self):
        actual = parse_palette(DARK+'red = "url(https://example.com)"\ncommand = "run me"\n[other]\naccent = "#ffffff"')
        self.assertNotIn('red', actual)
        self.assertNotIn('command', actual)
        self.assertEqual(actual['accent'], '#7aa2f7')
        self.assertIsNone(parse_palette('background = "#123456"'))

    def test_large_or_invalid_palette_falls_back(self):
        self.palette('.local/state/omarchy/current', DARK+' ' * 33000)
        self.assertFalse(omarchy_theme(self.home, {})['available'])


if __name__ == '__main__':
    unittest.main()
