"""Optional GitHub sync for Brains, in the spirit of Obsidian Git.

Notes go only to a GitHub repository the person owns. The access token stays
in the operating system's credential store (or a private 0600 file when none
is available). It is never returned to the interface, written to .git/config
or the remote URL, or placed on a command line: git receives it through
environment-scoped configuration that applies only to https://github.com/.
"""
import base64
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from store import Problem

FEATURE = 'github-sync'
REMOTE = 'notryn'
API = 'https://api.github.com'
SERVICE = 'Notryn'
ACCOUNT = 'github-token'
INTERVALS = (0, 5, 10, 15, 30, 60)
TOKEN_PATTERN = re.compile(r'(github_pat_[A-Za-z0-9_]{20,255}|gh[pousr]_[A-Za-z0-9]{20,255})')
REPO_PATTERN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}')
BRANCH_PATTERN = re.compile(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,99}')
EXCLUDES = ('.notryn-*', '.DS_Store', 'Thumbs.db', 'desktop.ini')


def now():
    return datetime.now(timezone.utc).isoformat()


def parse_repo(value):
    """Accept owner/name, a github.com URL or an SSH-style address."""
    text = str(value or '').strip()
    text = re.sub(r'^(?:https?://)?(?:www\.)?github\.com[/:]', '', text, flags=re.I)
    text = re.sub(r'^git@github\.com:', '', text, flags=re.I)
    text = re.sub(r'(?:\.git)?/*$', '', text)
    if not REPO_PATTERN.fullmatch(text) or text.endswith(('.', '..')) or '..' in text:
        raise Problem('Enter the repository as owner/name, for example ana/notes.')
    return text


def child_env(extra=None):
    """Environment for helper programs, without PyInstaller's private libraries."""
    env = dict(os.environ)
    if getattr(sys, 'frozen', False):
        original = env.pop('LD_LIBRARY_PATH_ORIG', None)
        if original is not None:
            env['LD_LIBRARY_PATH'] = original
        else:
            env.pop('LD_LIBRARY_PATH', None)
    env.update(extra or {})
    return env


# ------------------------------------------------------------ token vault
class SecretStore:
    """Keep one secret in the OS keychain, falling back to a private file."""

    def __init__(self, home, backend=None):
        self.home = Path(home)
        self.file = self.home / 'secrets' / 'github.json'
        self.backend = backend or os.environ.get('NOTRYN_SECRET_BACKEND') or self.detect()

    @staticmethod
    def detect():
        if sys.platform == 'darwin' and shutil.which('security'):
            return 'keychain'
        if sys.platform.startswith('linux') and shutil.which('secret-tool') and os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
            return 'secret-service'
        return 'file'

    @staticmethod
    def label(backend):
        return {'keychain': 'macOS Keychain', 'secret-service': 'system keyring',
                'file': 'a private file readable only by your user'}.get(backend, backend)

    def _run(self, args, data=None):
        return subprocess.run(args, input=data, capture_output=True, text=True, timeout=30, env=child_env())

    def set(self, value):
        """Store the token; return the backend that holds it."""
        if not TOKEN_PATTERN.fullmatch(value):
            raise Problem('This does not look like a GitHub access token.')
        try:
            if self.backend == 'keychain':
                # Commands go through stdin, so the token never appears in a process list.
                result = self._run(['security', '-i'], f'add-generic-password -U -a {ACCOUNT} -s {SERVICE} -l "Notryn GitHub Sync" -w {value}\n')
                if result.returncode == 0:
                    return 'keychain'
            elif self.backend == 'secret-service':
                result = self._run(['secret-tool', 'store', '--label=Notryn GitHub Sync', 'service', SERVICE, 'account', ACCOUNT], value)
                if result.returncode == 0:
                    return 'secret-service'
        except (OSError, subprocess.TimeoutExpired):
            pass
        self.backend = 'file'
        self.file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.file.parent, 0o700)
        fd, temporary = tempfile.mkstemp(prefix='.notryn-', dir=self.file.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'token': value}, stream)
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.file)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return 'file'

    def get(self, backend=None):
        backend = backend or self.backend
        try:
            if backend == 'keychain':
                result = self._run(['security', 'find-generic-password', '-a', ACCOUNT, '-s', SERVICE, '-w'])
                return result.stdout.strip() if result.returncode == 0 else None
            if backend == 'secret-service':
                result = self._run(['secret-tool', 'lookup', 'service', SERVICE, 'account', ACCOUNT])
                return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
        try:
            value = json.loads(self.file.read_text(encoding='utf-8')).get('token')
            return value if isinstance(value, str) else None
        except (OSError, ValueError, AttributeError):
            return None

    def delete(self, backend=None):
        backend = backend or self.backend
        try:
            if backend == 'keychain':
                self._run(['security', 'delete-generic-password', '-a', ACCOUNT, '-s', SERVICE])
            elif backend == 'secret-service':
                self._run(['secret-tool', 'clear', 'service', SERVICE, 'account', ACCOUNT])
        except (OSError, subprocess.TimeoutExpired):
            pass
        self.file.unlink(missing_ok=True)


# ----------------------------------------------------------- GitHub API
def github_api(token, path):
    from notryn_install import https_context
    request = Request(API + path, headers={
        'Accept': 'application/vnd.github+json', 'Authorization': 'Bearer ' + token,
        'User-Agent': 'Notryn', 'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with urlopen(request, timeout=20, context=https_context()) as response:
            return json.loads(response.read())
    except HTTPError as error:
        if error.code == 401:
            raise Problem('GitHub did not accept this token. It may be expired or revoked.', 401)
        if error.code in {403, 404}:
            raise Problem('GitHub could not find this repository with this token. Check the name and that the token includes it.', 404)
        raise Problem('GitHub returned an error. Try again in a moment.', 502)
    except (URLError, OSError, ValueError):
        raise Problem('Could not reach GitHub. Check your internet connection.', 502)


# ------------------------------------------------------------------ git
class Git:
    def __init__(self, root, token=None, identity=None):
        self.root = Path(root)
        self.token = token
        self.identity = identity or {}

    def env(self):
        config = [('credential.helper', ''), ('core.quotePath', 'false'), ('commit.gpgSign', 'false'),
                  ('push.negotiate', 'false'), ('advice.detachedHead', 'false')]
        if self.token:
            basic = base64.b64encode(('x-access-token:' + self.token).encode()).decode()
            config.append(('http.https://github.com/.extraHeader', 'Authorization: Basic ' + basic))
        extra = {'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'Never', 'GIT_ASKPASS': '', 'SSH_ASKPASS': '',
                 'LC_ALL': 'C', 'GIT_CONFIG_COUNT': str(len(config))}
        for index, (key, value) in enumerate(config):
            extra[f'GIT_CONFIG_KEY_{index}'] = key
            extra[f'GIT_CONFIG_VALUE_{index}'] = value
        if self.identity:
            extra.update({'GIT_AUTHOR_NAME': self.identity['name'], 'GIT_AUTHOR_EMAIL': self.identity['email'],
                          'GIT_COMMITTER_NAME': self.identity['name'], 'GIT_COMMITTER_EMAIL': self.identity['email']})
        return child_env(extra)

    def scrub(self, text):
        if self.token:
            text = text.replace(self.token, '***')
            text = text.replace(base64.b64encode(('x-access-token:' + self.token).encode()).decode(), '***')
        return text

    def run(self, *args, check=True, timeout=60, binary=False):
        try:
            result = subprocess.run(['git', *args], cwd=self.root, capture_output=True, timeout=timeout, env=self.env())
        except FileNotFoundError:
            raise Problem('Git is not installed on this computer.', 412)
        except subprocess.TimeoutExpired:
            raise Problem('Git took too long to answer. Check your connection and try again.', 504)
        if check and result.returncode:
            raise GitError(self.scrub(result.stderr.decode('utf-8', 'replace')).strip(), result.returncode)
        if binary:
            return result
        result.stdout = result.stdout.decode('utf-8', 'replace')
        result.stderr = self.scrub(result.stderr.decode('utf-8', 'replace'))
        return result

    def out(self, *args, **options):
        return self.run(*args, **options).stdout.strip()


class GitError(Exception):
    def __init__(self, detail, code):
        self.detail, self.code = detail, code
        super().__init__(detail)


_GIT_STATUS = {}


def git_status():
    """Report whether a compatible git (2.31+, for env-scoped config) exists."""
    cached = _GIT_STATUS.get('value')
    if cached and cached['available'] and time.time() - _GIT_STATUS['at'] < 600:
        return cached
    _GIT_STATUS.update(value=probe_git(), at=time.time())
    return _GIT_STATUS['value']


def probe_git():
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True, timeout=10, env=child_env())
    except (OSError, subprocess.TimeoutExpired):
        return {'available': False, 'version': None, 'help': install_help()}
    match = re.search(r'(\d+)\.(\d+)', result.stdout or '')
    if result.returncode or not match:
        return {'available': False, 'version': None, 'help': install_help()}
    version = (int(match.group(1)), int(match.group(2)))
    if version < (2, 31):
        return {'available': False, 'version': match.group(0), 'help': 'Notryn needs Git 2.31 or newer. ' + install_help()}
    return {'available': True, 'version': match.group(0), 'help': ''}


def install_help():
    if sys.platform == 'darwin':
        return 'Install Git with the command: xcode-select --install'
    return 'Install Git with your package manager, for example: sudo apt install git, sudo dnf install git or sudo pacman -S git.'


def explain(error):
    """Turn a git failure into a short, actionable message."""
    text = error.detail if isinstance(error, GitError) else str(error)
    lower = text.lower()
    if 'could not resolve host' in lower or 'unable to access' in lower and 'resolve' in lower:
        return 'Could not reach GitHub. Check your internet connection.'
    if '403' in lower or 'permission' in lower and 'denied' in lower or 'write access' in lower:
        return 'GitHub refused the upload. Give the token "Contents: Read and write" access to this repository.'
    if 'authentication failed' in lower or '401' in lower or 'terminal prompts disabled' in lower:
        return 'GitHub did not accept the token. Reconnect your account with a new token.'
    if 'repository not found' in lower or 'not found' in lower and 'repository' in lower:
        return 'Repository not found. Check the name and that the token includes this repository.'
    if 'exceeds github' in lower or 'file size limit' in lower or 'large files detected' in lower:
        return 'A file in this Brain is larger than GitHub allows (100 MB). Move it out of the Brain folder.'
    last = [line for line in text.splitlines() if line.strip()][-3:]
    return 'Git could not finish the sync: ' + (' '.join(last)[:300] or 'unknown error.')


def inside(root, relative):
    """Resolve a repository path for writing without following links out of the Brain."""
    target = root / relative
    current = root
    for part in Path(relative).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise Problem('A synced folder is a symbolic link. Notryn stopped to protect your files.', 409)
    if target.is_symlink() or not target.resolve().is_relative_to(root):
        raise Problem('A synced file points outside this Brain. Notryn stopped to protect your files.', 409)
    return target


# --------------------------------------------------------------- service
class SyncService:
    def __init__(self, store, secrets=None, entitlements=None, api=github_api):
        from notryn_license import Entitlements
        self.store = store
        self.secrets = secrets or SecretStore(store.home)
        self.entitlements = entitlements or Entitlements(store.home)
        self.api = api
        self.settings_path = store.home / 'sync.json'
        self.status = {}
        self.locks = {}
        self.guard = threading.Lock()
        self.stopped = threading.Event()
        self.thread = None
        try:
            self.settings = json.loads(self.settings_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            self.settings = {}
        self.settings.setdefault('account', None)

    # ------------------------------------------------------------ state
    def save(self):
        from store import atomic
        atomic(self.settings_path, json.dumps(self.settings, ensure_ascii=False, indent=2).encode())
        try:
            os.chmod(self.settings_path, 0o600)
        except OSError:
            pass

    def config(self, brain):
        value = brain.get('sync')
        return value if isinstance(value, dict) and value.get('provider') == 'github' else None

    def remote_url(self, repo):
        return f'https://github.com/{repo}.git'

    def describe(self):
        account = self.settings.get('account')
        brains = {}
        for brain in self.store.brains:
            if brain.get('removedAt'):
                continue
            config = self.config(brain)
            brains[brain['id']] = {**(config or {}), 'enabled': bool(config), **self.status.get(brain['id'], {})}
        return {
            'git': git_status(),
            'account': {'connected': True, 'login': account['login'], 'storage': SecretStore.label(account['backend'])} if account else {'connected': False},
            'storage': SecretStore.label(self.secrets.backend),
            'intervals': list(INTERVALS),
            'license': self.entitlements.describe(FEATURE),
            'brains': brains,
        }

    def require_feature(self):
        if not self.entitlements.allows(FEATURE):
            raise Problem('GitHub Sync is a paid feature. Unlock it to continue.', 402)

    def token(self):
        account = self.settings.get('account')
        if not account:
            raise Problem('Connect your GitHub account first.', 409)
        token = self.secrets.get(account['backend'])
        if not token:
            raise Problem('The saved GitHub token is missing from this computer. Connect your account again.', 409)
        return token

    # ---------------------------------------------------------- account
    def connect_account(self, token):
        self.require_feature()
        token = str(token or '').strip()
        if not TOKEN_PATTERN.fullmatch(token):
            raise Problem('Paste a GitHub token. It starts with github_pat_ or ghp_.')
        user = self.api(token, '/user')
        if not isinstance(user, dict) or not user.get('login'):
            raise Problem('GitHub did not return the account for this token.', 502)
        previous = self.settings.get('account')
        if previous:
            self.secrets.delete(previous['backend'])
        backend = self.secrets.set(token)
        self.settings['account'] = {'login': user['login'], 'id': user.get('id'), 'backend': backend, 'connectedAt': now()}
        self.save()
        return self.describe()

    def disconnect_account(self):
        account = self.settings.get('account')
        if account:
            self.secrets.delete(account['backend'])
        self.settings['account'] = None
        self.save()
        return self.describe()

    # ------------------------------------------------------------ brain
    def configure(self, brain_id, repo, interval=10, on_open=True, confirm_public=False, branch=None):
        self.require_feature()
        brain = self.store.get(brain_id)
        if not self.store.can_write(brain):
            raise Problem('Sync changes files, so this Brain must allow reading and writing. Change its access first.', 403)
        if interval not in INTERVALS:
            raise Problem('Choose a sync interval from the list.')
        if git_status()['available'] is False:
            raise Problem('Git is required for GitHub Sync. ' + install_help(), 412)
        repo = parse_repo(repo)
        token = self.token()
        info = self.api(token, '/repos/' + repo)
        if not isinstance(info, dict):
            raise Problem('GitHub returned an unexpected answer.', 502)
        if not info.get('private') and not confirm_public:
            raise Problem('This repository is public: anyone could read your notes. Use a private repository, or confirm that you want a public one.', 428)
        branch = branch or info.get('default_branch') or 'main'
        if not BRANCH_PATTERN.fullmatch(branch) or '..' in branch:
            raise Problem('This branch name is not supported.')
        for other in self.store.brains:
            other_config = self.config(other)
            if other['id'] != brain_id and not other.get('removedAt') and other_config and other_config['repo'].lower() == repo.lower() and other_config['branch'] == branch:
                raise Problem('Another Brain on this computer already syncs with this repository.', 409)
        with self.store.lock:
            previous = brain.get('sync')
            brain['sync'] = {'provider': 'github', 'repo': repo, 'branch': branch, 'interval': interval,
                             'onOpen': bool(on_open), 'private': bool(info.get('private')),
                             'connectedAt': (previous or {}).get('connectedAt') or now()}
            try:
                self.store.persist()
            except Exception:
                brain['sync'] = previous
                raise
        return self.sync(brain_id, reason='setup')

    def update_schedule(self, brain_id, interval, on_open):
        brain = self.store.get(brain_id)
        config = self.config(brain)
        if not config:
            raise Problem('This Brain is not synced with GitHub.', 404)
        if interval not in INTERVALS:
            raise Problem('Choose a sync interval from the list.')
        with self.store.lock:
            config['interval'], config['onOpen'] = interval, bool(on_open)
            self.store.persist()
        return self.describe()

    def stop(self, brain_id):
        brain = self.store.get(brain_id)
        with self.store.lock:
            config = brain.pop('sync', None)
            self.store.persist()
        self.status.pop(brain_id, None)
        if config and (Path(brain['root']) / '.git').is_dir():
            # History stays in the folder; Notryn only stops talking to GitHub.
            git = Git(brain['root'])
            if self.managed_remote(git):
                git.run('remote', 'remove', REMOTE, check=False)
        return self.describe()

    # ------------------------------------------------------------- sync
    def identity(self, repo):
        configured = repo.run('config', '--get', 'user.email', check=False).stdout.strip()
        if configured:
            return {}
        account = self.settings.get('account') or {}
        login = account.get('login') or 'notryn'
        email = f"{account['id']}+{login}@users.noreply.github.com" if account.get('id') else f'{login}@users.noreply.github.com'
        return {'name': login, 'email': email}

    def prepare(self, brain, config, token):
        root = Path(brain['root'])
        if not root.is_dir():
            raise Problem('This Brain folder is unavailable.', 404)
        git = Git(root, token)
        if not (root / '.git').exists():
            git.run('init', '-q')
            git.run('symbolic-ref', 'HEAD', 'refs/heads/' + config['branch'])
        elif (root / '.git').is_symlink() or not (root / '.git').is_dir():
            raise Problem('This Brain uses a linked Git folder that Notryn cannot manage.', 409)
        current_branch = git.run('symbolic-ref', '-q', '--short', 'HEAD', check=False).stdout.strip()
        if current_branch and current_branch != config['branch'] and self.head(git) is None:
            # A repository without commits (for example "git init" on master) has nothing to protect.
            git.run('symbolic-ref', 'HEAD', 'refs/heads/' + config['branch'])
            current_branch = config['branch']
        if current_branch != config['branch']:
            # Never publish another branch (or a detached checkout) into the synced one.
            shown = current_branch or 'a detached commit'
            raise Problem(f'This folder is on {shown}, but GitHub Sync uses the branch "{config["branch"]}". Switch the folder to "{config["branch"]}" (git switch {config["branch"]}) and sync again.', 409)
        if (root / '.git' / 'MERGE_HEAD').exists():
            # An interrupted sync left a merge open. Local edits were committed
            # before it began, so aborting returns to them without losing work.
            git.run('merge', '--abort', check=False)
        url = self.remote_url(config['repo'])
        current = git.run('remote', 'get-url', REMOTE, check=False)
        if current.returncode:
            git.run('remote', 'add', REMOTE, url)
            git.run('config', f'remote.{REMOTE}.notrynManaged', 'true')
        elif not self.managed_remote(git):
            raise Problem(f'This folder already has a Git remote named "{REMOTE}". Rename it, then try again.', 409)
        elif current.stdout.strip() != url:
            git.run('remote', 'set-url', REMOTE, url)
        exclude = root / '.git' / 'info' / 'exclude'
        exclude.parent.mkdir(exist_ok=True)
        existing = exclude.read_text(encoding='utf-8') if exclude.exists() else ''
        missing = [line for line in EXCLUDES if line not in existing.splitlines()]
        if missing:
            exclude.write_text(existing + ('' if not existing or existing.endswith('\n') else '\n') + '# Added by Notryn\n' + '\n'.join(missing) + '\n', encoding='utf-8')
        return Git(root, token, self.identity(git))

    @staticmethod
    def managed_remote(git):
        return git.run('config', '--get', f'remote.{REMOTE}.notrynManaged', check=False).stdout.strip() == 'true'

    def head(self, git):
        result = git.run('rev-parse', '--verify', '-q', 'HEAD', check=False)
        return result.stdout.strip() or None

    def commit_local(self, git):
        git.run('add', '-A')
        if git.run('diff', '--cached', '--quiet', check=False).returncode:
            git.run('commit', '-q', '--no-verify', '-m', 'Notryn sync from ' + (platform.node() or 'a computer')[:60])
            return True
        return False

    def conflict_name(self, path, root):
        stem, suffix = os.path.splitext(path)
        stamp = datetime.now().strftime('%Y-%m-%d %H%M')
        candidate = f'{stem} (GitHub copy {stamp}){suffix}'
        counter = 2
        while (root / candidate).exists():
            candidate = f'{stem} (GitHub copy {stamp} {counter}){suffix}'
            counter += 1
        return candidate

    def resolve_conflicts(self, git):
        """Keep this computer's version and save GitHub's as a visible copy."""
        listing = git.run('ls-files', '-u', '-z').stdout
        stages = {}
        for record in filter(None, listing.split('\0')):
            meta, path = record.split('\t', 1)
            _, sha, stage = meta.split()
            stages.setdefault(path, {})[stage] = sha
        copies = []
        root = git.root.resolve()
        for path, versions in sorted(stages.items()):
            target = inside(root, path)
            ours, theirs = versions.get('2'), versions.get('3')
            blob = lambda sha: git.run('cat-file', 'blob', sha, binary=True).stdout
            if ours and theirs:
                target.write_bytes(blob(ours))
                copy = self.conflict_name(path, root)
                inside(root, copy).write_bytes(blob(theirs))
                copies.append(copy)
            elif ours or theirs:
                # One side deleted the file and the other edited it: keep the edit.
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(blob(ours or theirs))
        git.run('add', '-A')
        git.run('commit', '-q', '--no-verify', '--no-edit')
        return copies

    def integrate(self, git, branch):
        """Merge GitHub's branch into this computer's. Return (changed paths, conflict copies)."""
        remote = f'{REMOTE}/{branch}'
        if git.run('rev-parse', '--verify', '-q', remote, check=False).returncode:
            return [], []
        before = self.head(git)
        if before is None:
            git.run('checkout', '-q', '-B', branch, remote)
            return git.out('ls-tree', '-r', '--name-only', 'HEAD').splitlines(), []
        args = ['merge', '-q', '--no-edit', '--no-verify', remote]
        if git.run('merge-base', 'HEAD', remote, check=False).returncode:
            args.insert(1, '--allow-unrelated-histories')
        copies = []
        result = git.run(*args, check=False)
        if result.returncode:
            if not git.out('ls-files', '-u'):
                git.run('merge', '--abort', check=False)
                raise GitError(result.stderr or result.stdout, result.returncode)
            copies = self.resolve_conflicts(git)
        after = self.head(git)
        changed = git.out('diff', '--name-only', before, after).splitlines() if after != before else []
        return changed, copies

    def check_visibility(self, token, config):
        """Pause before sending notes to a repository that became public."""
        info = self.api(token, '/repos/' + config['repo'])
        if isinstance(info, dict) and not info.get('private') and config.get('private', True):
            raise Problem('This repository is now public: anyone could read your notes. Sync is paused until you confirm or make it private again.', 428)

    def sync(self, brain_id, reason='manual'):
        self.require_feature()
        brain = self.store.get(brain_id)
        config = self.config(brain)
        if not config:
            raise Problem('This Brain is not synced with GitHub yet.', 404)
        if not self.store.can_write(brain):
            raise Problem('Sync needs read and write access to this Brain.', 403)
        with self.guard:
            lock = self.locks.setdefault(brain_id, threading.Lock())
        if not lock.acquire(blocking=False):
            raise Problem('This Brain is already syncing.', 409)
        started = time.time()
        self.status[brain_id] = {**self.status.get(brain_id, {}), 'state': 'syncing', 'startedAt': now()}
        branch = config['branch']
        tracking = f'refs/remotes/{REMOTE}/{branch}'
        try:
            token = self.token()
            self.check_visibility(token, config)
            with self.store.lock:
                git = self.prepare(brain, config, token)
            changed, copies, pushed = [], [], False
            for _ in range(3):
                # ls-remote checks access and tells an empty repository from a failure.
                exists = bool(git.out('ls-remote', '--heads', REMOTE, 'refs/heads/' + branch, timeout=120))
                if exists:
                    git.run('fetch', '-q', '--no-tags', REMOTE, f'+refs/heads/{branch}:{tracking}', timeout=180)
                else:
                    git.run('update-ref', '-d', tracking, check=False)
                with self.store.lock:
                    self.commit_local(git)
                    step_changed, step_copies = self.integrate(git, branch)
                changed += step_changed
                copies += step_copies
                head = self.head(git)
                if head is None or exists and head == git.out('rev-parse', '--verify', '-q', tracking):
                    break
                push = git.run('push', '-q', REMOTE, f'HEAD:refs/heads/{branch}', check=False, timeout=180)
                if not push.returncode:
                    pushed = True
                    break
                if not any(word in push.stderr for word in ('rejected', 'fetch first', 'non-fast-forward')):
                    raise GitError(push.stderr, push.returncode)
            else:
                raise GitError('GitHub kept changing during the sync. Try again in a moment.', 1)
            result = {'state': 'ok', 'at': now(), 'reason': reason, 'pulled': len(set(changed)),
                      'pushed': pushed, 'conflicts': copies, 'seconds': round(time.time() - started, 1)}
            self.status[brain_id] = result
            with self.store.lock:
                current = self.config(brain)
                if current:
                    current['lastSyncAt'] = result['at']
                    self.store.persist()
            return {**result, 'sync': self.describe()['brains'].get(brain_id)}
        except GitError as error:
            message = explain(error)
            self.status[brain_id] = {'state': 'error', 'at': now(), 'error': message, 'reason': reason}
            raise Problem(message, 502)
        except Problem as error:
            self.status[brain_id] = {'state': 'error', 'at': now(), 'error': error.message, 'reason': reason}
            raise
        except (OSError, UnicodeError, ValueError) as error:
            message = 'Sync stopped because a file in this Brain could not be read or written (' + type(error).__name__ + ').'
            self.status[brain_id] = {'state': 'error', 'at': now(), 'error': message, 'reason': reason}
            raise Problem(message, 500)
        finally:
            lock.release()

    # -------------------------------------------------------- scheduler
    def due(self, brain_id, config, startup):
        if startup:
            return config.get('onOpen')
        minutes = config.get('interval') or 0
        if not minutes:
            return False
        last = self.status.get(brain_id, {}).get('at') or config.get('lastSyncAt')
        if not last:
            return True
        try:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds()
        except ValueError:
            return True
        return elapsed >= minutes * 60

    def tick(self, startup=False):
        self.entitlements.refresh()
        if not self.settings.get('account') or not self.entitlements.allows(FEATURE):
            return
        for brain in list(self.store.brains):
            config = self.config(brain)
            if brain.get('removedAt') or not config or not self.due(brain['id'], config, startup):
                continue
            try:
                self.sync(brain['id'], reason='startup' if startup else 'schedule')
            except Exception:
                pass  # Recorded in status for the interface; other Brains keep syncing.

    def start(self, every=30):
        def loop():
            startup = True
            while True:
                try:
                    self.tick(startup=startup)
                except Exception:
                    pass  # The scheduler must outlive any single failure.
                startup = False
                if self.stopped.wait(every):
                    return
        self.thread = threading.Thread(target=loop, name='notryn-sync', daemon=True)
        self.thread.start()

    def shutdown(self):
        self.stopped.set()
