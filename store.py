"""Markdown vault storage. No database, cloud account or third-party dependencies."""
import hashlib
import json
import os
import re
import secrets
import tempfile
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
MAX_NOTE_BYTES = 1024 * 1024
MAX_NODES = 2000
SKIP = {'.git', '.obsidian', '.notryn', '.neura', 'node_modules', '__pycache__', '.venv', 'venv'}
LABELS = {'projects':'Projects','topics':'Knowledge','core':'System','learning':'System','financas':'Finance'}

class Problem(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status
        super().__init__(message)

def folder_path(value):
    """Accept paths copied from Finder, a terminal or a file URL; never execute them."""
    if not isinstance(value,str) or not value.strip() or '\x00' in value or len(value)>32768:
        raise Problem('Enter a folder path or use Browse folders.')
    text=value.strip()
    candidates=[text]
    pairs={'"':'"',"'":"'",'“':'”','‘':'’'}
    if len(text)>1 and pairs.get(text[0])==text[-1]:
        text=text[1:-1].strip()
        if not text:
            raise Problem('Enter a folder path or use Browse folders.')
        candidates.append(text)
    if text.lower().startswith('file:'):
        url=urlsplit(text)
        if url.netloc not in {'','localhost'}:
            raise Problem('Choose a folder on this computer.')
        text=unquote(url.path)
        if os.name=='nt' and re.match(r'^/[A-Za-z]:',text):
            text=text[1:]
        candidates.append(text)
    elif os.name!='nt':
        # Only clipboard-style escaping, not shell parsing or environment expansion.
        unescaped=re.sub(r'\\([ \t()\[\]{}\'"&;#!$`])',r'\1',text)
        if unescaped!=text:
            candidates.append(unescaped)
    try:
        for candidate in candidates:
            path=Path(candidate).expanduser()
            if path.is_dir():
                return path.resolve()
        return Path(candidates[-1]).expanduser().resolve()
    except (OSError,ValueError,RuntimeError):
        raise Problem('This path cannot be opened. Use Browse folders to choose a location.')

def specific_folder(root):
    return root!=Path(root.anchor) and root!=Path.home().resolve() and root not in HERE.parents and root!=HERE

def revision(content):
    return hashlib.sha256(content).hexdigest()

def slug(value):
    text = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')[:70] or 'brain'

def atomic(path, data):
    fd, temporary = tempfile.mkstemp(prefix='.notryn-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

class Store:
    def __init__(self, home=None):
        # Prefer the Notryn namespace, while continuing to open pre-rename Neura
        # installations without losing their connected Brains or recovery data.
        configured = home or os.environ.get('NOTRYN_HOME') or os.environ.get('NEURA_HOME')
        default = HERE / '.notryn'
        legacy = HERE / '.neura'
        self.home = Path(configured or (legacy if not default.exists() and legacy.exists() else default)).expanduser().resolve()
        self.home.mkdir(parents=True, exist_ok=True)
        self.config = self.home / 'brains.json'
        self.lock = threading.RLock()
        self.removal_plans = {}
        if self.config.exists():
            saved = json.loads(self.config.read_text())
            self.brains = saved['brains']
            self.removals = saved.get('removals', [])
        else:
            self.brains = []
            self.removals = []
            self.persist()

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def persist(self):
        atomic(self.config, json.dumps({'version':1,'brains':self.brains,'removals':self.removals}, ensure_ascii=False, indent=2).encode())

    def get(self, brain_id):
        brain = next((b for b in self.brains if b['id'] == brain_id and not b.get('removedAt')), None)
        if not brain:
            raise Problem('This Brain is not connected.', 404)
        return brain

    def is_protected(self, root, except_id=None):
        return any(b['id'] != except_id and (root.is_relative_to(Path(b['root']).resolve()) or Path(b['root']).resolve().is_relative_to(root)) for b in self.brains if b.get('readOnly'))

    def can_write(self, brain):
        return not brain['readOnly'] and not self.is_protected(Path(brain['root']).resolve())

    def summary(self, brain):
        return {**brain,'readOnly':not self.can_write(brain),'available':Path(brain['root']).is_dir()}

    def state(self):
        return {'brains':[self.summary(b) for b in self.brains if not b.get('removedAt')], 'version':'0.2.0','agent':{'connected':False,'mode':'local-guide'}}

    def is_removed(self, brain, path, except_id=None):
        return any(r['id'] != except_id and r['brain'] == brain['id'] and r['kind'] != 'brain' and
                   (path == r['path'] or r['kind'] == 'folder' and path.startswith(r['path'] + '/')) for r in self.removals)

    def add(self, name, existing=None, writable=False):
        name = str(name).strip()
        if not name or len(name) > 80:
            raise Problem('Choose a name between 1 and 80 characters.')
        with self.lock:
            ident = slug(name) + '-' + secrets.token_hex(3)
            if existing is not None:
                root = folder_path(existing)
                if not root.is_dir():
                    raise Problem('This folder does not exist on this computer.')
                if not specific_folder(root):
                    raise Problem('Choose a specific Brain folder, not a system or application folder.')
                try:
                    with os.scandir(root):
                        pass
                except OSError:
                    raise Problem('This folder cannot be read. Check its permissions or choose another folder.',403)
                duplicate = next((b for b in self.brains if Path(b['root']).resolve() == root), None)
                if duplicate:
                    if duplicate.get('removedAt'):
                        raise Problem('This Brain is in Removed items. Restore it to keep its settings, or use Remove from list there to connect the folder again.', 409)
                    raise Problem('This folder is already connected as “' + duplicate['name'] + '”.', 409)
                if writable and self.is_protected(root):
                    raise Problem('This folder overlaps with a read-only Brain.', 403)
            else:
                root = self.home / 'brains' / ident
                root.mkdir(parents=True, exist_ok=False)
                writable = True
            scope = 'all'
            brain = {'id':ident,'name':name,'root':str(root),'readOnly':not writable,'scope':scope,'createdAt':self.now()}
            self.brains.append(brain)
            self.persist()
            return self.summary(brain)

    def set_access(self, brain_id, writable):
        if type(writable) is not bool:
            raise Problem('Choose read-only or read and write access.')
        with self.lock:
            brain = self.get(brain_id)
            root = Path(brain['root']).resolve()
            if writable:
                if not root.is_dir():
                    raise Problem('This Brain folder is unavailable.', 404)
                if self.is_protected(root, brain['id']):
                    raise Problem('This folder overlaps with another read-only Brain.', 403)
                if not os.access(root, os.W_OK):
                    raise Problem('This folder cannot be changed. Check its permissions first.', 403)
            previous = brain['readOnly']
            brain['readOnly'] = not writable
            try:
                self.persist()
            except Exception:
                brain['readOnly'] = previous
                raise
            return self.summary(brain)

    def browse(self, path=None, query='', offset=0):
        """List one directory without connecting it, reading notes or writing files."""
        if not isinstance(query,str) or len(query)>256 or type(offset) is not int or offset<0:
            raise Problem('Invalid folder search.')
        root=folder_path(str(Path.home()) if path is None else path)
        if not root.is_dir():
            raise Problem('This folder does not exist on this computer.',404)
        folders=[]
        def search_key(text):
            return ''.join(c for c in unicodedata.normalize('NFD',text) if not unicodedata.combining(c)).casefold()
        search=search_key(query)
        try:
            with os.scandir(root) as entries:
                for entry in entries:
                    if entry.name.startswith('.') or search not in search_key(entry.name):
                        continue
                    try:
                        if entry.is_dir():
                            folders.append({'name':entry.name,'path':str(root/entry.name)})
                    except OSError:
                        continue
        except OSError:
            raise Problem('This folder cannot be read. Check its permissions or choose another folder.',403)
        folders.sort(key=lambda f:(f['name'].casefold(),f['name']))
        home=Path.home()
        locations=[('Home',home),('Desktop',home/'Desktop'),('Documents',home/'Documents'),('Downloads',home/'Downloads')]
        if os.name=='nt':
            locations.extend((letter+':',Path(letter+':\\')) for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        else:
            locations.append(('Computer',Path('/')))
        places=[{'name':name,'path':str(p.resolve())} for name,p in locations if p.is_dir()]
        page=folders[offset:offset+200]
        return {'path':str(root),'name':root.name or str(root),'parent':str(root.parent) if root.parent!=root else None,
                'folders':page,'places':places,'total':len(folders),'nextOffset':offset+len(page) if offset+len(page)<len(folders) else None,
                'selectable':specific_folder(root)}

    def base(self, brain):
        root = Path(brain['root'])
        return root / 'wiki' if brain['scope'] == 'wiki' else root

    def safe_path(self, brain, relative, folder=False, allow_removed=False):
        if not isinstance(relative,str) or not relative or '\\' in relative or '\x00' in relative:
            raise Problem('Invalid path.')
        parts = relative.split('/')
        if any(not p or p in {'.','..'} or p.startswith('.') or any(ord(c)<32 for c in p) for p in parts):
            raise Problem('Use simple names without hidden folders or relative path segments.')
        if Path(relative).is_absolute() or (not folder and Path(relative).suffix.lower() != '.md'):
            raise Problem('Note filenames must end in .md.')
        base = self.base(brain).resolve()
        target = base / relative
        current = base
        for part in parts:
            current = current / part
            if current.is_symlink():
                raise Problem('Symbolic links cannot be opened or modified.',403)
        if not target.resolve().is_relative_to(base):
            raise Problem('The path is outside this Brain.',403)
        if not allow_removed and self.is_removed(brain, relative):
            raise Problem('This item was removed from Notryn. Restore it from Removed items first.',404)
        return target

    def inventory(self, brain, include_removed=False):
        base = self.base(brain)
        if not base.is_dir():
            raise Problem('This Brain folder is unavailable.',404)
        files, folders, skipped = [], set(), 0
        for directory, dirs, names in os.walk(base, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith('.') and not (Path(directory)/d).is_symlink())
            rel_dir = Path(directory).relative_to(base)
            if not include_removed:
                dirs[:] = [d for d in dirs if not self.is_removed(brain, (rel_dir / d).as_posix())]
            if brain['scope'] == 'wiki':
                if rel_dir == Path('.'):
                    dirs[:] = [d for d in dirs if d in LABELS]
                else:
                    dirs[:] = []
            for d in dirs:
                folders.add((rel_dir / d).as_posix())
            for filename in sorted(names):
                p = Path(directory)/filename
                if not include_removed and self.is_removed(brain, p.relative_to(base).as_posix()):
                    continue
                if p.is_symlink() or filename.startswith('.') or p.suffix.lower() != '.md':
                    continue
                if brain['scope']=='wiki' and filename in {'log.md','index.md'}:
                    continue
                if p.stat().st_size > MAX_NOTE_BYTES or len(files)>=MAX_NODES:
                    skipped += 1
                    continue
                files.append(p)
        return files, sorted(folders), skipped

    def graph(self, brain_id):
        brain = self.get(brain_id)
        files, folders, skipped = self.inventory(brain)
        base = self.base(brain)
        nodes, contents = [], {}
        for p in files:
            try:
                text = p.read_text(encoding='utf-8')
            except (OSError, UnicodeError):
                skipped += 1
                continue
            relative = p.relative_to(base).as_posix()
            ident = relative[:-3]
            title = re.search(r'^#\s+(.+)',text,re.M)
            parent = Path(relative).parent.as_posix()
            category = relative.split('/')[0] if '/' in relative else 'Notes'
            group = LABELS.get(category,category.replace('-',' ').capitalize())
            nodes.append({'id':ident,'path':relative,'title':title.group(1).strip() if title else p.stem,'group':group,'folder':'' if parent=='.' else parent,'updatedAt':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),'size':p.stat().st_size})
            contents[ident] = text
        from filemoves import link_spans, resolve_link
        paths = {p.relative_to(base).as_posix() for p in self.inventory(brain, include_removed=True)[0]} if any(r['brain']==brain_id for r in self.removals) else {n['path'] for n in nodes}
        paths.update(p for r in self.removals if r['brain']==brain_id for p in r.get('notePaths',[]))
        ids = {n['path']: n['id'] for n in nodes}
        edges = set()
        for node in nodes:
            source = node['id']
            text = contents[source]
            for start, end, kind in link_spans(text):
                link = text[start:end]
                if brain['scope'] == 'wiki' and link.startswith('wiki/'):
                    link = link[5:]
                target_path = resolve_link(link, node['path'], paths, kind)
                target = ids.get(target_path)
                if target and target != source:
                    edges.add(tuple(sorted((source, target))))
        return {'brain':self.summary(brain),'nodes':nodes,'edges':[{'source':a,'target':b} for a,b in sorted(edges)],'folders':folders,'linkPaths':sorted(paths),'skipped':skipped,'loadedAt':self.now()}

    def removal_preview(self, brain_id, path, kind):
        from removals import preview
        return preview(self, brain_id, path, kind)

    def remove(self, preview_id, device=False, confirm_name=''):
        from removals import remove
        return remove(self, preview_id, device, confirm_name)

    def removed_items(self):
        from removals import removed_items
        return removed_items(self)

    def restore(self, entry_id):
        from removals import restore
        return restore(self, entry_id)

    def forget_preview(self, entry_id):
        from removals import forget_preview
        return forget_preview(self, entry_id)

    def forget(self, entry_id, expected_revision):
        from removals import forget
        return forget(self, entry_id, expected_revision)

    def read(self, brain_id, path):
        brain = self.get(brain_id)
        p = self.safe_path(brain,path)
        if not p.is_file():
            raise Problem('The note no longer exists at this path.',404)
        if p.stat().st_size>MAX_NOTE_BYTES:
            raise Problem('This note exceeds the 1 MB limit.',413)
        # The protected vault exposes only its active inventory.
        if brain['scope']=='wiki' and p not in self.inventory(brain)[0]:
            raise Problem('This note is not included in the active view.',403)
        data=p.read_bytes()
        try:
            content=data.decode('utf-8')
        except UnicodeError:
            raise Problem('The note must use UTF-8 encoding.')
        return {'path':path,'content':content,'revision':revision(data),'readOnly':not self.can_write(brain)}

    def write(self, brain_id, path, content, expected):
        brain = self.get(brain_id)
        if not self.can_write(brain):
            raise Problem('This Brain is protected and read-only.',403)
        if not isinstance(content,str) or len(content.encode('utf-8'))>MAX_NOTE_BYTES:
            raise Problem('The note must be no larger than 1 MB.',413)
        with self.lock:
            p=self.safe_path(brain,path)
            if not p.parent.is_dir():
                raise Problem('Create the destination folder before saving the note.')
            payload=content.encode('utf-8')
            if p.exists():
                if not p.is_file():
                    raise Problem('This path is already a folder.',409)
                old=p.read_bytes()
                if expected is None or not hmac_equal(expected,revision(old)):
                    raise Problem('This note has changed elsewhere. Your edit is still here; copy it before reopening the current version.',409)
                if old==payload:
                    return {'path':path,'revision':revision(old),'saved':True,'changed':False}
                backup=self.home/'backups'/brain_id
                backup.mkdir(parents=True,exist_ok=True)
                backup_name=slug(p.stem)+'-'+secrets.token_hex(8)+'.md'
                (backup/backup_name).write_bytes(old)
                atomic(p,payload)
            else:
                if expected is not None:
                    raise Problem('This note was removed outside the app. It has not been recreated.',409)
                fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
                with os.fdopen(fd,'wb') as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
            return {'path':path,'revision':revision(payload),'saved':True,'changed':True}

    def move(self, brain_id, source, destination, kind, guard=None):
        from filemoves import move_item
        return move_item(self, brain_id, source, destination, kind, guard)

    def folder(self, brain_id, path):
        brain=self.get(brain_id)
        if not self.can_write(brain):
            raise Problem('This Brain is protected and read-only.',403)
        with self.lock:
            p=self.safe_path(brain,path,folder=True)
            if p.exists():
                raise Problem('A note or folder with this name already exists.',409)
            if not p.parent.is_dir():
                raise Problem('The destination folder does not exist.')
            p.mkdir()
            return {'path':path,'created':True}

def hmac_equal(a,b):
    import hmac
    return isinstance(a,str) and hmac.compare_digest(a,b)
