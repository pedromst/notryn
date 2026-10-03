# Notryn 0.2.0-beta.13

Clearer GitHub Sync setup and a cloud that shows when your notes move.

- **Two clear options.** Setup now asks where your notes live: *Option 1* creates a new private repository, *Option 2* uses a repository you already have. The token steps follow for both.
- **A living cloud.** While notes are sent or received, the top-bar cloud turns blue and fills up. Background syncs show a short message when changes arrive or are sent, or when something goes wrong.
- **Safer with existing repositories.** If the folder is checked out on another Git branch, sync stops and asks you to switch, so a side branch is never pushed into your main notes. An empty repository created on another branch name is adopted automatically.
- **Several Brains.** The help page explains syncing many Brains, one repository each, with a single token.

Help: https://notryn.com/sync.html

Validated with Python, Node and isolated Chromium coverage for the sync flows, branch protection, the transfer animation and desktop/mobile layout.

Free to use under PolyForm Shield 1.0.0. No account, subscription or note telemetry.

Install: https://notryn.com/guide.html

Fallback installer: https://github.com/pedromst/notryn/releases/download/v0.2.0-beta.13/install.sh

Linux x86_64 and experimental macOS Intel/Apple-silicon packages include installation, update, rollback and uninstall commands. Windows and Linux ARM packages remain unavailable.

Save and quit before updating. Keep your own note backups. macOS packages are ad-hoc signed and not Apple-notarized; macOS may block them. Do not disable Gatekeeper. The index currently supports up to 2,000 notes, up to 1 MB each.

Downloads are on GitHub Releases. Package SHA-256 values are verified against GitHub; this is integrity checking, not independent publisher signing.
