# Notryn 0.2.0-beta.7

Use Notryn in split windows and finish saving without waiting for the whole Brain to refresh.

- Desktop windows can shrink to 320 × 320 pixels, allowing Omarchy and other tiling window managers to activate the compact layout instead of clipping the desktop view.
- Narrow windows keep navigation and toolbar controls within reach. Short windows use tighter spacing and scrollable Library controls.
- Resizing preserves the open note and unsaved draft. Brain and Notes remain available through the compact navigation.
- Save confirms once the server has persisted the note. Graph indexing continues separately, so a large Brain no longer delays finishing the edit.
- Edits typed during a save remain unsaved and open. Write errors and conflicts still preserve the draft.
- The public demo uses the same responsive interface and temporary sample notes.

Validated with 117 Python tests, 64 Node tests and browser checks at 320 × 320, 480 × 360, 640 × 720, 960 × 540 and 1440 × 950. Physical testing on Omarchy remains useful; the screenshot report was reproduced through the desktop minimum-size constraint and short browser viewports.

Free to use under PolyForm Shield 1.0.0. No account, subscription or note telemetry.

Install: https://notryn.com/guide.html

Fallback installer: https://github.com/pedromst/notryn/releases/download/v0.2.0-beta.7/install.sh

Linux x86_64 and experimental macOS Intel/Apple-silicon packages include installation, update, rollback and uninstall commands. Windows and Linux ARM packages remain unavailable.

Save and quit before updating. Keep your own note backups. macOS packages are ad-hoc signed and not Apple-notarized; macOS may block them. Do not disable Gatekeeper. The index currently supports up to 2,000 notes, up to 1 MB each.

Downloads are on GitHub Releases. Package SHA-256 values are verified against GitHub; this is integrity checking, not independent publisher signing.
