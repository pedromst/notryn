# Notryn 0.2.0-beta.5

See what is happening while Notryn installs or updates, with clear progress from download to completion.

- Public app downloads show a live bar with measured percentage, transferred size and average speed.
- Checking, unpacking, preparing and installing show an animated activity indicator, elapsed time and completion marks. Percentages describe the download only.
- The one-line installer shows download progress too, including when its input comes from a pipe.
- Narrow terminals use a compact display. Redirected logs remain plain text; terminal colours respect `NO_COLOR`.
- Interrupted or failed transfers stop clearly. Cancelling during app replacement restores the previous managed app and its version record when recovery can complete.

**Already installed?** Your old updater still uses its old display for this one update. Save and quit, then run `curl -fsSL https://notryn.com/install.sh | sh` to use the new progress immediately. Future `notryn update` runs will show it too.

Free to use under PolyForm Shield 1.0.0. No account, subscription or note telemetry.

Install: https://notryn.com/guide.html

Fallback installer: https://github.com/pedromst/notryn/releases/download/v0.2.0-beta.5/install.sh

Linux x86_64 and experimental macOS Intel/Apple-silicon packages include installation, update, rollback and uninstall commands. Windows and Linux ARM packages remain unavailable.

Save and quit before updating. Keep your own note backups. macOS packages are ad-hoc signed and not Apple-notarized; macOS may block them. Do not disable Gatekeeper. The index currently supports up to 2,000 notes, up to 1 MB each.

Downloads are on GitHub Releases. Package SHA-256 values are verified against GitHub; this is integrity checking, not independent publisher signing.
