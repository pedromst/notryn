# Notryn 0.2.0-beta.9

Find the right Markdown file and repair note links without rewriting the surrounding text.

- Link search now leads with the real `.md` filename, followed by the note title and complete path.
- Exact filename and filename-stem matches appear before partial title or path matches.
- Clicking an existing note link in Write opens **Edit link** with **Open note**, **Remove link**, **Cancel** and **Change link**.
- Changing a link preserves its visible text. Removing it keeps that text as ordinary writing and can be undone before saving.
- The editor license manifest is again generated only from runtime editor dependencies.

Validated with 117 Python tests, 66 Node tests and an isolated Chromium flow at desktop and 390 px. The test changed a wrong target to `BRAIN.md`, saved it, reopened it, navigated through it, removed it and undid the removal. Physical-device confirmation remains useful after updating.

Free to use under PolyForm Shield 1.0.0. No account, subscription or note telemetry.

Install: https://notryn.com/guide.html

Fallback installer: https://github.com/pedromst/notryn/releases/download/v0.2.0-beta.9/install.sh

Linux x86_64 and experimental macOS Intel/Apple-silicon packages include installation, update, rollback and uninstall commands. Windows and Linux ARM packages remain unavailable.

Save and quit before updating. Keep your own note backups. macOS packages are ad-hoc signed and not Apple-notarized; macOS may block them. Do not disable Gatekeeper. The index currently supports up to 2,000 notes, up to 1 MB each.

Downloads are on GitHub Releases. Package SHA-256 values are verified against GitHub; this is integrity checking, not independent publisher signing.
