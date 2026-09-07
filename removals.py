"""Reversible removal from this installation, with optional local file recovery."""
import copy
import hashlib
import json
import os
import secrets
import stat
import time
from pathlib import Path

from store import HERE, Problem, atomic, specific_folder

MAX_SCAN = 100000


def config_revision(store):
    return hashlib.sha256(json.dumps([store.brains, store.removals], sort_keys=True).encode()).hexdigest()


def source_path(store, brain, path, kind, removed=False):
    if kind == 'brain':
        if path not in ('', None):
            raise Problem('A Brain removal cannot include a child path.')
        return Path(brain['root'])
    if kind not in {'note', 'folder'}:
        raise Problem('Choose a note, folder or Brain.')
    return store.safe_path(brain, path, folder=kind == 'folder', allow_removed=removed)


def snapshot(source):
    """Bounded, non-following metadata snapshot; includes hidden files and links."""
    digest = hashlib.sha256()
    counts = {'notes': 0, 'files': 0, 'folders': 0, 'bytes': 0}
    pending, seen, notes = [source], 0, []
    while pending:
        p = pending.pop()
        info = p.lstat()
        seen += 1
        if seen > MAX_SCAN:
            raise Problem('Too many files to safely prepare this operation. Remove it from Notryn only.', 413)
        relative = p.relative_to(source).as_posix()
        link = os.readlink(p) if stat.S_ISLNK(info.st_mode) else ''
        digest.update(json.dumps([relative, info.st_mode, info.st_ino, info.st_dev, info.st_size, info.st_mtime_ns, link]).encode())
        if stat.S_ISDIR(info.st_mode):
            if p != source:
                counts['folders'] += 1
            with os.scandir(p) as entries:
                pending.extend(sorted((Path(e.path) for e in entries), reverse=True))
        else:
            counts['files'] += 1
            counts['bytes'] += info.st_size
            if p.suffix.lower() == '.md' and stat.S_ISREG(info.st_mode):
                counts['notes'] += 1
                notes.append(relative)
    return {**counts, 'fingerprint': digest.hexdigest(), 'notePaths': notes}


def device_reason(store, brain, source, kind):
    if not store.can_write(brain):
        return 'This Brain is read-only. You can remove it from Notryn while keeping its files.'
    if not source.exists():
        return 'The files are not available at this location.'
    if os.path.ismount(source):
        return 'A mounted device cannot be moved to Trash. Remove it from Notryn only.'
    if source.resolve() != source or source.is_symlink():
        return 'The original path now passes through a symbolic link. Files will stay on this device.'
    if (kind != 'note' and not source.is_dir()) or (kind == 'note' and not source.is_file()):
        return 'The item type has changed. Refresh the library first.'
    if not specific_folder(source) or store.home.is_relative_to(source) or HERE.is_relative_to(source):
        return 'System and application folders cannot be moved to Trash.'
    for other in store.brains:
        if other['id'] != brain['id'] and Path(other['root']).is_relative_to(source):
            return 'This folder contains another connected or removed Brain. Manage that Brain separately first.'
    return None


def preview(store, brain_id, path, kind):
    with store.lock:
        brain = store.get(brain_id)
        source = source_path(store, brain, path, kind)
        reason = device_reason(store, brain, source, kind)
        info = None
        try:
            info = snapshot(source)
        except (OSError, Problem):
            reason = reason or 'The contents cannot be fully checked. You can still remove it from Notryn only.'
        token = secrets.token_urlsafe(24)
        store.removal_plans = {k: v for k, v in store.removal_plans.items() if time.monotonic() - v['created'] < 600}
        if len(store.removal_plans) >= 100:
            store.removal_plans.pop(next(iter(store.removal_plans)))
        name = brain['name'] if kind == 'brain' else source.name
        plan = {'id': token, 'brain': brain_id, 'path': path or '', 'kind': kind, 'name': name,
                'brainName': brain['name'], 'source': str(source), 'canTrash': not reason,
                'reason': reason, 'counts': {k: v for k, v in (info or {}).items() if k not in {'fingerprint','notePaths'}},
                'notePaths': [path if kind=='note' else path+'/'+p for p in (info or {}).get('notePaths', [])] if kind!='brain' else [],
                'fingerprint': (info or {}).get('fingerprint'), 'created': time.monotonic(), 'config': config_revision(store)}
        store.removal_plans[token] = plan
        return {k: v for k, v in plan.items() if k not in {'fingerprint', 'created', 'config', 'notePaths'}}


def trash_slot(store, brain, source):
    # Never copy-then-delete across volumes. Keep an atomic rename on the same device.
    root = store.home / 'trash'
    if source.stat().st_dev != store.home.stat().st_dev:
        root = Path(brain['root']).parent / '.notryn-trash'
        if root.parent.stat().st_dev != source.stat().st_dev:
            root = Path(brain['root']) / '.notryn-trash'
    if root.is_symlink() or root.resolve() != root:
        raise Problem('The recovery folder is not safe to use. Files have not been moved.', 403)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    slot = root / secrets.token_hex(16)
    slot.mkdir(mode=0o700)
    return slot


def remove(store, preview_id, device=False, confirm_name=''):
    if type(device) is not bool or not isinstance(preview_id, str):
        raise Problem('Choose explicitly whether files should stay on this device.')
    with store.lock:
        plan = store.removal_plans.get(preview_id)
        if not plan or time.monotonic() - plan['created'] >= 600:
            raise Problem('This review has expired. Open Remove from Notryn again.', 409)
        if plan['config'] != config_revision(store):
            raise Problem('The library changed. Close this review and open it again.', 409)
        brain = store.get(plan['brain'])
        source = source_path(store, brain, plan['path'], plan['kind'])
        if device:
            reason = device_reason(store, brain, source, plan['kind'])
            if not plan['canTrash'] or reason:
                raise Problem(reason or plan['reason'] or 'Files cannot be moved to Trash.', 403)
            if plan['kind'] == 'brain' and confirm_name != brain['name']:
                raise Problem('Type the Brain name exactly to confirm moving its entire folder.')
            if snapshot(source)['fingerprint'] != plan['fingerprint']:
                raise Problem('The files changed after this review. Open it again before moving them to Trash.', 409)
        entry = {'id': secrets.token_hex(16), 'brain': brain['id'], 'kind': plan['kind'], 'path': plan['path'],
                 'name': plan['name'], 'brainName': brain['name'], 'mode': 'trash' if device else 'hidden',
                 'removedAt': store.now(), 'counts': plan['counts'], 'fingerprint': plan['fingerprint'], 'notePaths': plan['notePaths']}
        if device:
            slot = trash_slot(store, brain, source)
            entry['payload'] = str(slot / 'files')
            atomic(slot / 'recovery.json', json.dumps({**entry, 'original': str(source)}, ensure_ascii=False).encode())
        before_brains, before_removals = copy.deepcopy(store.brains), copy.deepcopy(store.removals)
        store.removals.append(entry)
        if plan['kind'] == 'brain':
            brain['removedAt'] = entry['removedAt']
        try:
            # Commit recovery coordinates before a rename, so an interrupted operation is recoverable.
            store.persist()
        except OSError:
            store.brains, store.removals = before_brains, before_removals
            raise Problem('Could not update Notryn. Your files and library have not changed.', 500)
        if device:
            try:
                source.rename(entry['payload'])
            except OSError:
                after_brains, after_removals = store.brains, store.removals
                store.brains, store.removals = before_brains, before_removals
                try:
                    store.persist()
                except OSError:
                    store.brains, store.removals = after_brains, after_removals
                    raise Problem('Files stayed at their original location. Restore this item from Removed items to show it again.', 500)
                raise Problem('Could not move the files to Trash. Nothing was removed from Notryn.', 500)
        del store.removal_plans[preview_id]
        return {'removed': True, 'entry': entry['id'], 'brain': brain['id'], 'kind': entry['kind'],
                'path': entry['path'], 'mode': entry['mode']}


def removed_items(store):
    with store.lock:
        result = []
        for entry in reversed(store.removals):
            brain = next((b for b in store.brains if b['id'] == entry['brain']), None)
            reason = None
            if not brain:
                reason = 'The original Brain registration is unavailable.'
            elif entry['kind'] != 'brain' and brain.get('removedAt'):
                reason = 'Restore this Brain first.'
            elif entry['kind'] != 'brain' and store.is_removed(brain, entry['path'], except_id=entry['id']):
                reason = 'Restore the containing folder first.'
            result.append({k: v for k, v in entry.items() if k not in {'payload', 'fingerprint', 'notePaths'}} | {'restoreBlocked': reason})
        return {'items': result}


def restore(store, entry_id):
    with store.lock:
        entry = next((r for r in store.removals if r['id'] == entry_id), None)
        if not entry:
            raise Problem('This item is no longer in Removed items.', 404)
        state = next(r for r in removed_items(store)['items'] if r['id'] == entry_id)
        if state['restoreBlocked']:
            raise Problem(state['restoreBlocked'], 409)
        brain = next(b for b in store.brains if b['id'] == entry['brain'])
        source = source_path(store, brain, entry['path'], entry['kind'], removed=True)
        payload, moved = None, False
        if entry['mode'] == 'trash':
            if not store.can_write(brain):
                raise Problem('The original location is protected. Its files have not been changed.', 403)
            payload = Path(entry['payload'])
            if payload.is_symlink() or payload.resolve() != payload or source.resolve() != source:
                raise Problem('The recovery path changed. Files have not been restored.', 403)
            if payload.exists():
                if os.path.lexists(source):
                    raise Problem('The original location is occupied. Move that item elsewhere before restoring; nothing was replaced.', 409)
                if not source.parent.is_dir():
                    raise Problem('The original parent folder is unavailable. Restore or recreate it first.', 409)
                payload.rename(source)
                moved = True
            elif not source.exists() or snapshot(source)['fingerprint'] != entry['fingerprint']:
                raise Problem('The recovery files are unavailable. Check that their device is connected.', 404)
            # If interrupted before trashing or after restoring, the original already exists unchanged.
        before_brains, before_removals = copy.deepcopy(store.brains), copy.deepcopy(store.removals)
        store.removals = [r for r in store.removals if r['id'] != entry_id]
        if entry['kind'] == 'brain':
            brain.pop('removedAt', None)
        try:
            store.persist()
        except OSError:
            store.brains, store.removals = before_brains, before_removals
            if moved:
                try:
                    source.rename(payload)
                except OSError:
                    raise Problem('The files are back at their original location. Restore this entry again to update Notryn.', 500)
            raise Problem('Could not update Notryn. The item remains in Removed items.', 500)
        return {'restored': True, 'brain': brain['id'], 'kind': entry['kind'], 'path': entry['path'], 'available': source.exists()}


def forget_preview(store, entry_id):
    with store.lock:
        entry = next((r for r in store.removals if r['id'] == entry_id), None)
        if not entry:
            raise Problem('This item is no longer in Removed items.', 404)
        affected = [r for r in store.removals if r['brain'] == entry['brain']] if entry['kind'] == 'brain' else [entry]
        brain = next((b for b in store.brains if b['id'] == entry['brain']), None)
        if entry['kind'] == 'brain' and brain and not brain.get('removedAt'):
            raise Problem('This Brain is connected. Refresh Removed items first.', 409)
        return {'id':entry_id, 'name':entry['name'], 'kind':entry['kind'], 'mode':entry['mode'],
                'count':len(affected), 'hasTrash':any(r['mode'] == 'trash' for r in affected),
                'revision':config_revision(store)}


def forget(store, entry_id, expected_revision):
    """Forget registrations only. Preserve original files and all Trash recovery data."""
    with store.lock:
        review = forget_preview(store, entry_id)
        if not isinstance(expected_revision, str) or expected_revision != review['revision']:
            raise Problem('Removed items changed. Review this action again.', 409)
        entry = next(r for r in store.removals if r['id'] == entry_id)
        affected = [r for r in store.removals if r['brain'] == entry['brain']] if entry['kind'] == 'brain' else [entry]
        brain = next((b for b in store.brains if b['id'] == entry['brain']), None)
        archive = store.home / 'recovery-history'
        if archive.is_symlink() or archive.resolve() != archive:
            raise Problem('The recovery history folder is unavailable. Nothing was removed.', 403)
        before_brains, before_removals = copy.deepcopy(store.brains), copy.deepcopy(store.removals)
        try:
            archive.mkdir(mode=0o700, exist_ok=True)
            record = archive / (secrets.token_hex(16) + '.json')
            atomic(record, json.dumps({'forgottenAt':store.now(), 'brain':brain, 'items':affected}, ensure_ascii=False, indent=2).encode())
            ids = {r['id'] for r in affected}
            store.removals = [r for r in store.removals if r['id'] not in ids]
            if entry['kind'] == 'brain':
                store.brains = [b for b in store.brains if b['id'] != entry['brain']]
            store.persist()
        except OSError:
            store.brains, store.removals = before_brains, before_removals
            raise Problem('Could not update Notryn. The item remains in Removed items.', 500)
        return {'forgotten':True, 'brain':entry['brain'], 'kind':entry['kind'], 'path':entry['path'],
                'count':len(affected), 'recoveryPath':str(record)}
