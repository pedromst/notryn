# Notryn 0.2.0-beta.14

GitHub Sync now works on Linux systems with a recent OpenSSL.

- **Sync fixed on Linux.** On distributions with OpenSSL 3.5 or newer (for example Arch and Omarchy), every sync stopped with "Git could not finish the sync: ... libssl.so.3: version `OPENSSL_3.5.0' not found". Notryn handed its own bundled libraries to Git; Git now always uses your system's OpenSSL.
- **Nothing to set up again.** Your GitHub account, repositories and sync interval are kept. After updating, open the Brain and sync runs on its own, or press sync once.

macOS is not affected by this issue.

Validated with Python and Node tests, including a regression test for the launcher and AppImage library paths, and a reproduction of the failure on Omarchy with OpenSSL 3.6.

Free to use under PolyForm Shield 1.0.0. No account, subscription or note telemetry.

Install: https://notryn.com/guide.html

Fallback installer: https://github.com/pedromst/notryn/releases/download/v0.2.0-beta.14/install.sh

Linux x86_64 and experimental macOS Intel/Apple-silicon packages include installation, update, rollback and uninstall commands. Windows and Linux ARM packages remain unavailable.

Save and quit before updating. Keep your own note backups. macOS packages are ad-hoc signed and not Apple-notarized; macOS may block them. Do not disable Gatekeeper. The index currently supports up to 2,000 notes, up to 1 MB each.

Downloads are on GitHub Releases. Package SHA-256 values are verified against GitHub; this is integrity checking, not independent publisher signing.
