# Notryn 0.2.0-beta.12

Keep a Brain the same on every computer with GitHub Sync.

- **GitHub Sync** connects a Brain to a private GitHub repository you own, in the spirit of the Obsidian Git plugin. Notes go only to GitHub, never to a Notryn server, and no Notryn account is needed.
- Sync **when Notryn opens**, **every 5 to 60 minutes**, or on demand with **Sync now** (**Shift Y**). Open the guided setup from the new cloud button in the top bar, the **Your Brains** hub, the first-run screen or **Y**.
- On a new computer, create an empty Brain and choose the same repository: your notes arrive on the first sync. Existing folders on both sides are merged.
- **Conflicts never lose an edit.** When two computers change the same note, this computer's version stays and the other is saved beside it as a “GitHub copy”, without Git conflict markers.
- **The token stays private.** It lives in macOS Keychain or the Linux keyring (or a `0600` file when no keyring exists), is only sent to GitHub, and is never shown again, written to the Brain, `.git/config` or the command line. A fine-grained token for one repository with *Contents: Read and write* is all that is needed. Public repositories require explicit confirmation.
- Sync requires Git 2.31 or newer and a Brain with read and write access. **Stop syncing** keeps notes and history in the folder and on GitHub.

GitHub Sync is free during the beta. The app now includes an offline, signed license check that stays switched off, so sync may become an optional paid feature later without changing how your notes are stored. Setup guide: https://notryn.com/guide.html#sync

Validated with Python, Node and isolated Chromium coverage for two-computer sync through a local repository, conflict copies, token privacy, public-repository confirmation, read-only protection, schedules, license signatures and desktop/mobile layout.

Free to use under PolyForm Shield 1.0.0. No account, subscription or note telemetry.

Install: https://notryn.com/guide.html

Fallback installer: https://github.com/pedromst/notryn/releases/download/v0.2.0-beta.12/install.sh

Linux x86_64 and experimental macOS Intel/Apple-silicon packages include installation, update, rollback and uninstall commands. Windows and Linux ARM packages remain unavailable.

Save and quit before updating. Keep your own note backups. macOS packages are ad-hoc signed and not Apple-notarized; macOS may block them. Do not disable Gatekeeper. The index currently supports up to 2,000 notes, up to 1 MB each.

Downloads are on GitHub Releases. Package SHA-256 values are verified against GitHub; this is integrity checking, not independent publisher signing.
