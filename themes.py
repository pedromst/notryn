"""Read Omarchy's active palette, without running hooks or modifying its files."""
import os
import re
from pathlib import Path

COLOR = re.compile(r'#[0-9a-fA-F]{6}\Z')
KEYS = {'background', 'foreground', 'accent', 'red', 'green', 'yellow',
        'blue', 'magenta', 'cyan', *('color'+str(i) for i in range(16))}


def parse_palette(text):
    # Omarchy colors.toml is a flat palette. Accept only quoted hex values and
    # mode; never interpolate, evaluate or import arbitrary theme configuration.
    palette = {}
    for line in text.splitlines():
        if line.strip().startswith('['):
            break
        match = re.fullmatch(r'\s*(\w+)\s*=\s*([\'"])(.*?)\2\s*(?:#.*)?', line)
        if not match:
            continue
        key, _, value = match.groups()
        if key in KEYS and COLOR.fullmatch(value):
            palette[key] = value.lower()
        elif key == 'mode' and value in {'light', 'dark'}:
            palette[key] = value
    if not all(k in palette for k in ('background', 'foreground')):
        return None
    palette.setdefault('accent', palette.get('blue', palette.get('color4', palette['foreground'])))
    return palette


def read_small(path, limit=32768):
    if not path.is_file():
        return ''
    with path.open('r', encoding='utf-8') as source:
        text = source.read(limit + 1)
    return text if len(text) <= limit else ''


def omarchy_theme(home=None, env=None):
    home = Path(home) if home is not None else Path.home()
    env = os.environ if env is None else env
    # Quattro moved current/ from config to state. Support both generations,
    # plus XDG locations. The standard paths remain useful with Omarchy scripts
    # which use HOME directly rather than the XDG variables.
    roots = [Path(env.get('XDG_STATE_HOME') or home/'.local/state')/'omarchy/current',
             home/'.local/state/omarchy/current',
             Path(env.get('XDG_CONFIG_HOME') or home/'.config')/'omarchy/current',
             home/'.config/omarchy/current']
    for root in dict.fromkeys(roots):
        try:
            theme = root/'theme'
            palette = parse_palette(read_small(theme/'colors.toml'))
            if not palette:
                continue
            if 'mode' not in palette and (theme/'light.mode').is_file():
                palette['mode'] = 'light'
            name = read_small(root/'theme.name', 160).strip()
            if not name and theme.is_symlink():
                name = theme.resolve().name
            name = re.sub(r'[^\w .+\-]', '', name)[:80].replace('-', ' ').strip()
            return {'available': True, 'name': name.title() or 'Omarchy', 'palette': palette}
        except (OSError, UnicodeError, RuntimeError):
            continue
    return {'available': False}
