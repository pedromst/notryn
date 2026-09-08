"""Move local notes/folders while preserving ordinary Markdown and wiki links."""
import json
import copy
import os
import posixpath
import re
import secrets
from pathlib import Path
from urllib.parse import quote, unquote

from store import Problem, MAX_NOTE_BYTES, MAX_NODES, SKIP, atomic


def link_spans(text):
    """Yield destination spans only; never reserialize the rest of a document."""
    # Metadata and code are opaque, even when they contain example links.
    masked = list(text)
    def hide(start, end):
        masked[start:end] = ['\n' if c == '\n' else ' ' for c in text[start:end]]
    front = re.match(r'\A(?:\ufeff)?---\r?\n[\s\S]*?\r?\n(?:---|\.\.\.)(?:\r?\n|$)', text)
    if front:
        hide(*front.span())
    fence = None
    offset = 0
    for line in text.splitlines(True):
        m = re.match(r' {0,3}(`{3,}|~{3,})', line)
        if fence:
            hide(offset, offset + len(line))
            if m and m[1][0] == fence[0] and len(m[1]) >= len(fence) and not line[m.end():].strip():
                fence = None
        elif m:
            fence = m[1]
            hide(offset, offset + len(line))
        elif line.startswith(('    ', '\t')):
            hide(offset, offset + len(line))
        offset += len(line)
    visible = ''.join(masked)
    for m in re.finditer(r'(`+)(?!`)([\s\S]*?)(?<!`)\1(?!`)|<!--[\s\S]*?-->', visible):
        hide(*m.span())
    visible = ''.join(masked)
    for m in re.finditer(r'(?<!\\)\[\[([^\]\n]+)\]\]', visible):
        target = m[1].split('|', 1)[0]
        stripped = target.strip()
        start = m.start(1) + len(target) - len(target.lstrip())
        if stripped:
            yield start, start + len(stripped), 'wiki'
    # Inline links/images, including balanced parentheses and optional titles.
    for m in re.finditer(r'(?<!\\)\]\([ \t]*', visible):
        start = m.end()
        if start >= len(visible):
            continue
        if visible[start] == '<':
            end = visible.find('>', start + 1)
            if end != -1 and '\n' not in visible[start:end]:
                yield start + 1, end, 'markdown'
            continue
        depth, end = 0, start
        while end < len(visible):
            c = visible[end]
            if c == '\\' and end + 1 < len(visible):
                end += 2
                continue
            if c.isspace() or (c == ')' and depth == 0):
                break
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            end += 1
        if end > start and depth == 0:
            yield start, end, 'markdown'
    for m in re.finditer(r'^ {0,3}\[[^\]\n]+\]:[ \t]*(?:<([^>\n]+)>|([^\s]+))', visible, re.M):
        yield (*m.span(1 if m[1] is not None else 2), 'markdown')


def resolve_link(target, source, paths, kind):
    target = unquote(re.sub(r'\\([\\()\[\] ])', r'\1', target.split('#', 1)[0].split('?', 1)[0]))
    if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('//'):
        return None
    relative = posixpath.normpath(posixpath.join(posixpath.dirname(source), target))
    candidates = [target, relative] if kind == 'wiki' else [relative]
    if target.startswith('/'):
        candidates = [target.lstrip('/')]
    for candidate in candidates:
        if candidate in paths:
            return candidate
        if kind == 'wiki' and candidate + '.md' in paths:
            return candidate + '.md'
    # Obsidian also writes shortest unique paths, e.g. topics/Note for
    # wiki/topics/Note.md. Never guess when two suffixes match, or reinterpret
    # an explicitly absolute/relative path as a shortened vault path.
    if kind == 'wiki' and not target.startswith('/') and not {'.', '..'} & set(target.split('/')):
        suffixes = ('/' + target, '/' + target + '.md')
        matches = [p for p in paths if p.endswith(suffixes)]
        if len(matches) == 1:
            return matches[0]
    return None


def rewrite_links(text, source, new_source, paths, new_paths, relocate):
    edits = []
    for start, end, kind in link_spans(text):
        value = text[start:end]
        target = resolve_link(value, source, paths, kind)
        if not target:
            continue
        new_target = relocate(target)
        if resolve_link(value, new_source, new_paths, kind) == new_target:
            continue
        suffix = re.search(r'[?#].*', value)
        suffix = suffix[0] if suffix else ''
        if kind == 'wiki':
            path = new_target
            if path.endswith('.md') and not value.split('#', 1)[0].endswith('.md'):
                path = path[:-3]
        else:
            path = '/' + new_target if value.startswith('/') else posixpath.relpath(new_target, posixpath.dirname(new_source) or '.')
            path = quote(path, safe='/-._~')
        edits.append((start, end, path + suffix))
    for start, end, replacement in sorted(set(edits), reverse=True):
        text = text[:start] + replacement + text[end:]
    return text


def move_item(store, brain_id, source, destination, kind, guard=None):
    brain = store.get(brain_id)
    if not store.can_write(brain):
        raise Problem('This Brain is protected and read-only.', 403)
    if kind not in {'note', 'folder'} or not isinstance(destination, str):
        raise Problem('Choose a note or folder and its destination.')
    with store.lock:
        base = store.base(brain).resolve()
        src = store.safe_path(brain, source, folder=kind == 'folder')
        parent = store.safe_path(brain, destination, folder=True) if destination else base
        if not parent.is_dir():
            raise Problem('The destination folder no longer exists. Refresh and try again.', 404)
        if not (src.is_dir() if kind == 'folder' else src.is_file()):
            raise Problem('This item no longer exists at its original location. Refresh and try again.', 404)
        if kind == 'folder' and (parent == src or parent.is_relative_to(src)):
            raise Problem('A folder cannot be moved inside itself or one of its subfolders.')
        target = parent / src.name
        if target == src:
            return {'path': source, 'source': source, 'changed': False, 'updatedLinks': 0}
        if os.path.lexists(target):
            raise Problem('An item with this name already exists in that folder. Nothing was replaced.', 409)
        new_source = target.relative_to(base).as_posix()
        def relocate(path):
            return new_source + path[len(source):] if path == source or (kind == 'folder' and path.startswith(source + '/')) else path

        if guard is not None:
            if not isinstance(guard, dict):
                raise Problem('Invalid open-note revision.')
            opened = store.read(brain_id, guard.get('path'))
            if opened['revision'] != guard.get('revision'):
                raise Problem('Your open note changed elsewhere. Reopen it before moving files.', 409)

        paths, originals = set(), {}
        # Include attachments in a folder move and in relative-link resolution.
        for root, dirs, files in os.walk(base, followlinks=False):
            directory = Path(root)
            inside = directory == src or directory.is_relative_to(src)
            for name in dirs + files:
                p = directory / name
                if inside and (p.is_symlink() or name in SKIP):
                    raise Problem('This folder contains a symbolic link or app data. Move those separately before trying again.')
            dirs[:] = [n for n in dirs if n not in SKIP and not n.startswith('.') and not (directory / n).is_symlink()]
            for name in files:
                p = directory / name
                if name.startswith('.') or p.is_symlink() or not p.is_file():
                    continue
                path = p.relative_to(base).as_posix()
                paths.add(path)
                if p.suffix.lower() == '.md':
                    if p.stat().st_size > MAX_NOTE_BYTES or len(originals) >= MAX_NODES:
                        raise Problem('This Brain exceeds the safe link-update limit (2,000 notes, 1 MB per note). Nothing was moved.', 413)
                    originals[path] = p.read_bytes()
        # Hidden subfolders travel intact; reject symlinks even inside them.
        if kind == 'folder':
            for root, dirs, files in os.walk(src, followlinks=False):
                if any((Path(root) / n).is_symlink() or n in SKIP for n in dirs + files):
                    raise Problem('This folder contains a symbolic link or app data. Move those separately before trying again.')

        new_paths = {relocate(p) for p in paths}
        updates = {}
        for path, raw in originals.items():
            try:
                content = raw.decode('utf-8')
            except UnicodeError:
                raise Problem('A Markdown note is not UTF-8. Convert it before moving files so its links can be preserved.')
            rewritten = rewrite_links(content, path, relocate(path), paths, new_paths, relocate).encode('utf-8')
            if rewritten != raw:
                if len(rewritten) > MAX_NOTE_BYTES:
                    raise Problem('Updating links would exceed the note size limit. Nothing was moved.', 413)
                updates[path] = rewritten

        # Store originals before the first mutation, with a recovery manifest.
        backup = store.home / 'backups' / brain_id / ('move-' + secrets.token_hex(8))
        backup.mkdir(parents=True)
        manifest = {'source': source, 'destination': new_source, 'state': 'prepared', 'notes': {}}
        for index, path in enumerate(updates):
            name = str(index) + '.md'
            (backup / name).write_bytes(originals[path])
            manifest['notes'][path] = name
        atomic(backup / 'move.json', json.dumps(manifest, ensure_ascii=False).encode())
        for path, raw in originals.items():
            if path in updates or relocate(path) != path or (guard and path == guard.get('path')):
                if (base / path).read_bytes() != raw:
                    raise Problem('A note changed while preparing the move. Nothing was moved. Try again.', 409)
        # Recheck destination and symlink boundaries after reading the notes.
        store.safe_path(brain, source, folder=kind == 'folder')
        store.safe_path(brain, new_source, folder=kind == 'folder')
        if os.path.lexists(target):
            raise Problem('An item with this name already exists in that folder. Nothing was replaced.', 409)
        moved, written = False, []
        old_removals = copy.deepcopy(store.removals)
        metadata_changed = False
        try:
            src.rename(target)
            moved = True
            for path, raw in updates.items():
                atomic(base / relocate(path), raw)
                written.append(path)
            for entry in store.removals:
                if entry['brain'] == brain_id and entry['kind'] != 'brain':
                    new_path = relocate(entry['path'])
                    if new_path != entry['path']:
                        metadata_changed = True
                        entry['path'] = new_path
                        entry['notePaths'] = [relocate(p) for p in entry.get('notePaths', [])]
            if metadata_changed:
                store.persist()
            manifest['state'] = 'complete'
            atomic(backup / 'move.json', json.dumps(manifest, ensure_ascii=False).encode())
        except OSError:
            try:
                for path in reversed(written):
                    atomic(base / relocate(path), originals[path])
                if moved:
                    if os.path.lexists(src):
                        raise OSError('Original path is occupied')
                    target.rename(src)
                store.removals = old_removals
                if metadata_changed:
                    store.persist()
                manifest['state'] = 'rolled-back'
                atomic(backup / 'move.json', json.dumps(manifest, ensure_ascii=False).encode())
            except OSError:
                raise Problem('The move was interrupted. Recovery copies were kept. Stop editing and check the local backup before continuing.', 500)
            raise Problem('Could not finish the move. The original location and notes were restored.', 500)
        return {'source': source, 'path': new_source, 'changed': True, 'updatedLinks': len(updates)}
