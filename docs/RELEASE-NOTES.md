# Notryn 0.2.0-beta.10

Keep Recent notes current and give the Brain a restrained cinematic HUD.

- Saving updates that note's position in **Recent** immediately, while the complete Brain continues reindexing in the background.
- Opening **Recent** or returning to Notryn detects Markdown or folder changes made in another application. The full Brain reloads only when the lightweight inventory revision changes; there is no continuous background scan.
- An open clean note follows disk changes. An unsaved draft is never replaced; external edits or removal produce a visible warning while the draft stays open.
- The new **Jarvis** theme brings crisp cyan telemetry and one slow reactor dial to the Brain while preserving Notryn's layout, controls, contrast and reduced-motion behavior.
- Theme commands also understand “HUD” and “reactor” as aliases for Jarvis.

Validated with Python, Node and isolated Chromium coverage for inventory revisions, immediate Recent ordering, external file changes, draft preservation, theme contrast and desktop/mobile layout. Physical-device confirmation remains useful after updating.

Free to use under PolyForm Shield 1.0.0. No account, subscription or note telemetry.

Install: https://notryn.com/guide.html

Fallback installer: https://github.com/pedromst/notryn/releases/download/v0.2.0-beta.10/install.sh

Linux x86_64 and experimental macOS Intel/Apple-silicon packages include installation, update, rollback and uninstall commands. Windows and Linux ARM packages remain unavailable.

Save and quit before updating. Keep your own note backups. macOS packages are ad-hoc signed and not Apple-notarized; macOS may block them. Do not disable Gatekeeper. The index currently supports up to 2,000 notes, up to 1 MB each.

Downloads are on GitHub Releases. Package SHA-256 values are verified against GitHub; this is integrity checking, not independent publisher signing.
