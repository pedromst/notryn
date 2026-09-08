# Notryn 0.2.0-beta.3

This public beta adds safe renaming and clearer file actions to the local Markdown desktop app. Free to use under PolyForm Shield 1.0.0. No account, subscription or note telemetry.

- Rename a focused note or folder with **F2**, from the searchable command menu, or from its **⋯** menu.
- The action menu now shows **N**, **Shift N**, **F2**, **M** and **D** beside new note, new folder, rename, move and removal.
- `.md` is kept automatically when a note is renamed.
- Resolved wiki links, Markdown links and attachment paths are updated after a rename, with recovery copies before files change.
- Rename follows the same write-access, conflict, size, symlink and collision protections as moving files.
- The interactive website demo supports the same rename and move flows using sample notes held only in the browser tab.
- Linux x86_64 and experimental macOS Intel/Apple-silicon packages include installation, update, rollback and uninstall commands.
- Windows and Linux ARM packages remain unavailable.

Install: https://notryn.com/guide.html

Fallback installer: https://github.com/pedromst/notryn/releases/download/v0.2.0-beta.3/install.sh

Save and quit before updating. Keep your own note backups. macOS packages are ad-hoc signed and not Apple-notarized; macOS may block them. Do not disable Gatekeeper. The index currently supports up to 2,000 notes, up to 1 MB each.

Downloads are on GitHub Releases. Package SHA-256 values are verified against GitHub; this is integrity checking, not independent publisher signing.
