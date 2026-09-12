"""Optional browser regression: isolated local files plus the real static demo.

Requires Playwright and its Chromium browser. No personal Brain is opened.
Run: python3 scripts/test-library-ui.py [--screenshots /tmp/notryn-ui]
"""
import argparse
import functools
import os
import secrets
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import Handler
from store import Store


class QuietApp(Handler):
    def log_message(self, *args):
        pass


class QuietStatic(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run(screenshots):
    with tempfile.TemporaryDirectory(prefix='notryn-library-test-') as temp:
        store = Store(Path(temp) / 'state')
        brain = store.add('My Brain')
        bid, folder = brain['id'], Path(brain['root'])
        for path in ['Projects', 'Projects/Notryn', 'Ideas', 'Empty',
                     'Projects/A folder with a very long name to check the layout']:
            store.folder(bid, path)
        store.write(bid, 'BRAIN.md', '# Pedro Brain\n\nThe root instructions.', None)
        store.write(bid, 'Start.md', '# Start\n\n[[Projects/Notryn/Plan|Brain]]', None)
        store.write(bid, 'Projects/Notryn/Plan.md', '# Plan\n\n[[Start]]', None)
        readonly = Path(temp) / 'readonly'
        readonly.mkdir()
        (readonly / 'Read.md').write_text('# Read only')
        store.add('Read only', str(readonly), False)
        app = ThreadingHTTPServer(('127.0.0.1', 0), QuietApp)
        app.store, app.token, app.instance_id = store, secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        demo = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietStatic, directory=str(ROOT / 'site')))
        for server in [app, demo]:
            threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                errors = []
                page = browser.new_page(viewport={'width': 1440, 'height': 950})
                media = page.context.new_cdp_session(page)
                media.send('Emulation.setEmulatedMedia', {
                    'features': [{'name': 'prefers-reduced-transparency', 'value': 'no-preference'}]
                })
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{app.server_port}')
                page.wait_for_load_state('networkidle')
                expect(page.locator('#library-location-name')).to_have_text('My Brain')
                expect(page.locator('#library-back')).to_be_disabled()
                expect(page.locator('.library-top #new-folder')).to_have_count(0)
                expect(page.locator('#mobile-create')).to_have_count(0)

                # Jarvis keeps Notryn's controls inside a distinct holographic glass cockpit.
                page.locator('#open-themes').click()
                expect(page.locator('#theme-option-jarvis')).to_be_visible()
                page.locator('#theme-option-jarvis').click()
                expect(page.locator('html')).to_have_attribute('data-theme', 'jarvis')
                jarvis_style = page.evaluate("""() => {
                    const style = getComputedStyle(document.querySelector('.topbar'));
                    return {
                        background: style.backgroundColor,
                        backdrop: style.backdropFilter || style.webkitBackdropFilter,
                        clip: style.clipPath,
                        radius: style.borderRadius,
                    };
                }""")
                assert 'rgba(' in jarvis_style['background'] or '/' in jarvis_style['background']
                assert 'blur(' in jarvis_style['backdrop']
                assert jarvis_style['clip'] not in ('', 'none')
                assert jarvis_style['radius'] == '1px'
                media.send('Emulation.setEmulatedMedia', {
                    'features': [{'name': 'prefers-reduced-transparency', 'value': 'reduce'}]
                })
                assert page.evaluate("getComputedStyle(document.querySelector('.topbar')).backdropFilter") == 'none'
                media.send('Emulation.setEmulatedMedia', {
                    'features': [{'name': 'prefers-reduced-transparency', 'value': 'no-preference'}]
                })
                page.wait_for_function("getComputedStyle(document.querySelector('.topbar')).backdropFilter.includes('blur')")
                if screenshots:
                    page.screenshot(path=str(screenshots / 'jarvis-theme-desktop.png'))
                    page.set_viewport_size({'width': 390, 'height': 844})
                    page.screenshot(path=str(screenshots / 'jarvis-theme-mobile.png'))
                    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
                    page.set_viewport_size({'width': 1440, 'height': 950})

                def row(path, kind='folder'):
                    key = kind + ':' + (path[:-3] if kind == 'note' else path)
                    return page.locator(f'.tree-row[data-key="{key}"]')

                def create(kind, name, destination):
                    page.locator('#new-folder' if kind == 'folder' else '#library-new-note').click()
                    expect(page.locator('#create-folder')).to_have_value(destination)
                    page.locator('#create-name').fill(name)
                    page.locator('#create-submit').click()
                    expect(page.locator('#create-dialog')).not_to_be_visible()

                # An opened note or a focused child must never steal the destination.
                row('Start.md', 'note').click()
                page.locator('#edit-toggle').click()
                expect(page.locator('.ProseMirror .note-link')).to_have_text('Brain')
                page.locator('.ProseMirror .note-link').click()
                expect(page.locator('#link-dialog')).to_be_visible()
                expect(page.locator('#link-title')).to_have_text('Edit link')
                expect(page.locator('#open-link-note')).to_be_visible()
                expect(page.locator('#remove-link')).to_be_visible()
                page.locator('#link-address').fill('brain')
                first_link = page.locator('#link-notes .link-note').first
                expect(first_link.locator('.link-note-file')).to_have_text('BRAIN.md')
                expect(first_link.locator('small')).to_contain_text('Pedro Brain · BRAIN.md')
                if screenshots:
                    page.screenshot(path=str(screenshots / 'link-search-desktop.png'))
                    page.set_viewport_size({'width': 390, 'height': 844})
                    page.screenshot(path=str(screenshots / 'link-search-mobile.png'))
                    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
                    page.set_viewport_size({'width': 1440, 'height': 950})
                page.locator('#link-dialog button[type="submit"]').click()
                expect(page.locator('#link-dialog')).not_to_be_visible()
                page.locator('#save-note').click()
                expect(page.locator('#document-read')).to_be_visible()
                assert '[[BRAIN|Brain]]' in (folder / 'Start.md').read_text()

                # Clicking a linked word exposes open, change and removal without rewriting it.
                page.locator('#edit-toggle').click()
                page.locator('.ProseMirror .note-link').click()
                page.locator('#open-link-note').click()
                expect(page.locator('#doc-folder')).to_have_text('BRAIN.md')
                expect(page.locator('#document-read h1')).to_have_text('Pedro Brain')
                row('Start.md', 'note').click()
                page.locator('#edit-toggle').click()
                page.locator('.ProseMirror .note-link').click()
                page.locator('#remove-link').click()
                expect(page.locator('.ProseMirror .note-link')).to_have_count(0)
                expect(page.locator('.ProseMirror')).to_contain_text('Brain')
                page.keyboard.press('Meta+z')
                expect(page.locator('.ProseMirror .note-link')).to_have_text('Brain')

                # Recent revalidates disk state, while an open draft is never replaced.
                page.locator('#recent-notes').click()
                expect(page.locator('#file-tree .tree-row').first).to_contain_text('Start.md')
                plan = folder / 'Projects/Notryn/Plan.md'
                plan.write_text('# Plan changed outside Notryn\n\n[[Start]]')
                future = time.time_ns() + 2_000_000_000
                os.utime(plan, ns=(future, future))
                page.evaluate("window.dispatchEvent(new Event('focus'))")
                expect(page.locator('#file-tree .tree-row').first).to_contain_text('Plan.md')
                page.locator('#source-mode').click()
                saved_start = page.locator('#editor').input_value()
                page.locator('#editor').fill('# Local draft kept\n\n[[BRAIN|Brain]]')
                plan.write_text('# A second external change\n\n[[Start]]')
                future += 2_000_000_000
                os.utime(plan, ns=(future, future))
                with page.expect_response(lambda response: '/api/graph?' in response.url):
                    page.evaluate("window.dispatchEvent(new Event('focus'))")
                expect(page.locator('#editor')).to_have_value('# Local draft kept\n\n[[BRAIN|Brain]]')
                page.locator('#editor').fill(saved_start)
                expect(page.locator('#save-status')).to_have_text('All changes saved')

                page.locator('#all-notes').click()
                row('Projects').click()
                expect(page.locator('#library-location-name')).to_have_text('Projects')
                create('folder', 'Scratch', 'Projects')
                expect(row('Projects/Scratch')).to_be_focused()
                create('folder', 'Second', 'Projects')
                assert (folder / 'Projects/Second').is_dir()
                assert not (folder / 'Projects/Scratch/Second').exists()
                row('Projects/Scratch').click()
                expect(page.locator('#file-tree')).to_have_text('This folder is empty.')
                create('note', 'Draft', 'Projects/Scratch')
                page.locator('#source-mode').click()
                page.locator('#editor').fill('# Draft\n\nStill here.')
                page.locator('#new-folder').click()
                expect(page.locator('#discard-dialog')).to_be_visible()
                page.locator('#keep-editing').click()
                expect(page.locator('#editor')).to_have_value('# Draft\n\nStill here.')
                page.locator('#save-note').click()
                expect(page.locator('#document-read')).to_be_visible()
                assert (folder / 'Projects/Scratch/Draft.md').read_text() == '# Draft\n\nStill here.'

                # Back is also a drag destination and resolves to the current parent.
                row('Projects/Scratch/Draft.md', 'note').drag_to(page.locator('#library-back'))
                expect(row('Projects/Scratch/Draft.md', 'note')).to_have_count(0)
                assert (folder / 'Projects/Draft.md').exists()
                page.locator('#library-back').click()
                expect(page.locator('#library-location-name')).to_have_text('Projects')
                expect(row('Projects/Scratch')).to_be_focused()
                page.locator('#library-back').click()
                expect(page.locator('#library-back')).to_be_disabled()
                expect(row('Projects')).to_be_focused()

                # Context menus intentionally create inside the item they belong to.
                row('Projects').locator('..').locator('.file-options').click()
                page.locator('#item-new-folder').click()
                expect(page.locator('#create-folder')).to_have_value('Projects')
                page.locator('#create-dialog [data-close]').first.click()
                page.locator('#new-folder').hover()
                expect(page.locator('#new-folder')).to_have_attribute('title', 'New folder in My Brain (Shift N)')
                page.locator('#open-shortcuts').click()
                page.locator('#single-key-toggle').uncheck()
                page.locator('#shortcuts-dialog [data-close]').click()
                page.locator('#new-folder').hover()
                expect(page.locator('#new-folder')).to_have_attribute('title', 'New folder in My Brain')
                page.locator('#open-shortcuts').click()
                page.locator('#single-key-toggle').check()
                page.locator('#interface-hints-toggle').uncheck()
                page.locator('#shortcuts-dialog [data-close]').click()
                page.locator('#refresh').hover()
                expect(page.locator('#refresh')).to_have_attribute('title', 'Refresh notes')
                page.locator('#open-shortcuts').click()
                page.locator('#interface-hints-toggle').check()
                page.locator('#shortcuts-dialog [data-close]').click()
                page.locator('#refresh').hover()
                expect(page.locator('#refresh')).to_have_attribute('title', 'Refresh notes (R)')

                # Long folder labels and touch controls fit narrow windows.
                row('Projects').click()
                row('Projects/A folder with a very long name to check the layout').click()
                for width in [1440, 1100, 768, 390, 320]:
                    page.set_viewport_size({'width': width, 'height': 844})
                    if width <= 900:
                        page.locator('.mobile-nav [data-mobile="notes"]').click()
                    expect(page.locator('#library-new-note')).to_be_visible()
                    overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth')
                    assert not overflow, f'Horizontal overflow at {width}px'
                    for selector in ['#library-new-note', '#new-folder', '#library-back']:
                        box = page.locator(selector).bounding_box()
                        assert box['x'] >= 0 and box['x'] + box['width'] <= width
                        if width <= 900:
                            assert box['height'] >= 44
                    if screenshots:
                        page.screenshot(path=str(screenshots / f'library-{width}.png'))
                page.set_viewport_size({'width': 1440, 'height': 950})
                # Creating a Brain always exposes and uses the location chosen by the user.
                chosen_parent = (Path(temp) / 'Chosen location').resolve()
                chosen_parent.mkdir()
                page.locator('#brain-picker').click()
                page.locator('#add-new-brain').click()
                expect(page.locator('#brain-form-path-label')).to_have_text('Create inside')
                page.locator('#brain-form-name').fill('Visible Brain')
                expect(page.locator('#brain-submit')).to_be_disabled()
                page.locator('#brain-form-path').fill(str(chosen_parent))
                expect(page.locator('#brain-form-destination code')).to_have_text(str(chosen_parent / 'Visible Brain'))
                page.locator('#browse-folders').click()
                expect(page.locator('#folder-dialog-title')).to_have_text('Choose a location')
                expect(page.locator('#folder-location')).to_have_text(str(chosen_parent))
                page.locator('#folder-choose').click()
                page.locator('#brain-submit').click()
                expect(page.locator('#brain-name')).to_have_text('Visible Brain')
                assert (chosen_parent / 'Visible Brain').is_dir()
                page.locator('#brain-picker').click()
                page.locator('.brain-card').filter(has_text='My Brain').click()
                page.locator('#brain-picker').click()
                page.locator('.brain-card').filter(has_text='Read only').click()
                expect(page.locator('#library-location-name')).to_have_text('Read only')
                expect(page.locator('#new-folder')).to_be_disabled()
                expect(page.locator('#library-new-note')).to_be_disabled()
                assert list(readonly.iterdir()) == [readonly / 'Read.md']
                assert (readonly / 'Read.md').read_text() == '# Read only'

                # The public demo uses the same controls and resets on reload.
                page.goto(f'http://127.0.0.1:{demo.server_port}/demo/index.html')
                page.wait_for_load_state('networkidle')
                row('Projects').click()
                create('folder', 'Demo folder', 'Projects')
                expect(row('Projects/Demo folder')).to_be_visible()
                row('Projects/Demo folder').click()
                create('note', 'Demo note', 'Projects/Demo folder')
                page.locator('#save-note').click()
                expect(page.locator('#document-read')).to_be_visible()
                page.reload()
                page.wait_for_load_state('networkidle')
                row('Projects').click()
                expect(row('Projects/Demo folder')).to_have_count(0)
                page.locator('#brain-picker').click()
                page.locator('#add-new-brain').click()
                page.locator('#brain-form-name').fill('Demo Brain')
                page.locator('#browse-folders').click()
                page.locator('#folder-results .folder-entry').filter(has_text='Documents').click()
                page.locator('#folder-choose').click()
                expect(page.locator('#brain-form-destination code')).to_have_text('Demo computer/Documents/Demo Brain')
                page.locator('#brain-submit').click()
                expect(page.locator('#brain-name')).to_have_text('Demo Brain')
                assert not errors, errors
                browser.close()
                print('PASS: chosen Brain location, current-folder creation, stale selection, empty folders, draft protection, save, drag up, back focus, context menus, shortcut preferences, read-only, responsive 320–1440px and demo reset.')
        finally:
            for server in [app, demo]:
                server.shutdown()
                server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    run(args.screenshots)
