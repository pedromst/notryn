# Install, update and uninstall

Public beta `0.2.0-beta.10`. Linux/Omarchy first; macOS Intel and Apple silicon packages use the same commands. Windows has no installer yet.

## Before installing

- Use your normal account, without `sudo`.
- Save your notes and quit Notryn before installing or updating.
- Public downloads need an internet connection and curl, but no GitHub login.
- No destination Python or Node.js installation is needed: the setup program and app are bundled.

## Installation

```sh
curl -fsSL https://notryn.com/install.sh | sh
```

This downloads and executes the published bootstrap. To inspect it first:

```sh
curl -fSL https://notryn.com/install.sh -o notryn-install.sh
less notryn-install.sh
sh notryn-install.sh
```

Fallback if the domain is unavailable:

```sh
curl -fsSL https://github.com/pedromst/notryn/releases/download/v0.2.0-beta.10/install.sh | sh
```

Add `--no-open` to install without opening the app. The bootstrap detects the OS and architecture, verifies the setup checksum, and runs the setup program. The setup then downloads the app, compares its SHA-256 with the GitHub release asset digest, checks the archive paths and tests its local server in disposable state. It then installs the app and creates the launcher.

During download, the terminal shows the measured percentage, transferred size and average speed. Checking, unpacking and installing each have an animated activity indicator, then a completion mark. Redirected output stays readable as plain progress messages; set `NO_COLOR=1` to disable terminal colours.

On Linux, open **Notryn** from the app menu. On macOS, open **Notryn.app** in your user's **Applications** folder. Running `notryn` opens this same desktop app, not a browser tab.

### macOS experimental beta

The packages use an ad-hoc signature checked during installation. They are not signed with an Apple Developer ID or notarized yet. A downloaded package may be blocked by macOS. Do not disable Gatekeeper or remove quarantine as part of installation. The finished Mac distribution still requires Developer ID signing, notarization and a fresh download test on a separate Mac.

### If the command is not found

Use the complete command:

```sh
~/.local/bin/notryn version
```

Or enable the standard user binary directory for your current terminal:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

To keep this for future terminals, add that line to the relevant shell profile (`~/.zshrc` for zsh, usually `~/.bashrc` for interactive bash). Notryn does not change those files automatically. Fish users can use `fish_add_path ~/.local/bin`.

## Update

1. Save your open notes.
2. Quit the desktop app.
3. Run:

```sh
notryn update
```

Public beta installations follow newer preview releases, then stable releases. Once installed on a stable version, updates select stable releases only. No GitHub login is required. If migrating from a private alpha, run the public installer once to switch to public downloads.

**Upgrading from beta.4 or earlier:** that installed updater still has the old progress display for this one update. To see the new display immediately, save and quit, then run the public installation command above. It also updates an existing installation. Subsequent `notryn update` runs use the new progress display.

To choose a specific newer release:

```sh
notryn update --version 0.2.0-beta.10
```

The app refuses downgrades through update. It keeps the current version if the download, checksum, package validation or local-server test fails. When replacement fails, it restores the previous app. It does not close an open editor or discard an unsaved draft for you.

**Coming from alpha.2:** run the new installer above once. The old `notryn update` command only printed instructions; the new lifecycle commands arrive with alpha.3.

## Return to the previous version

Save and quit, then:

```sh
notryn rollback
```

This switches to the previous application backup. Notes and settings remain current. Notryn also keeps the version you left, so a second rollback can switch back. If no previous app exists, it tells you instead of downloading an arbitrary old version.

If rolling back to alpha.2, that older program has no real update/rollback implementation; run the current installer again to move forward.

## Uninstall

Save and quit, then:

```sh
notryn uninstall
```

This removes the current app and its launcher/menu entry. It keeps:

- Connected folders in their original locations.
- App-created Brains, settings, note backups and recovery state.
- The removed app under the application's `.notryn-backups` directory.

It does not delete your data or empty Trash. There is no destructive `--purge` flag.

## Locations

| Item | Linux | macOS |
| --- | --- | --- |
| App | `~/.local/lib/notryn` | `~/Applications/Notryn.app` |
| App backups | `~/.local/lib/.notryn-backups` | `~/Applications/.notryn-backups` |
| Command | `~/.local/bin/notryn` | `~/.local/bin/notryn` |
| Settings, recovery data and older app-created Brains | `$XDG_DATA_HOME/notryn` or `~/.local/share/notryn` | `~/Library/Application Support/Notryn` |

New Brains are folders in the location selected during creation. Use the same normal user and state location when updating. A custom `NOTRYN_HOME` remains supported for terminal server work; it is not a way to relocate the desktop installation.

## Troubleshooting

### Split windows

The desktop app supports windows down to 320 × 320 pixels. Below 900 pixels wide it uses compact Brain/Notes navigation. Short windows keep the Library scrollable. Save your work, update and reopen the app to pick up changes to desktop window limits.

### Installing alongside a development checkout

The macOS installer writes to `~/Applications/Notryn.app`, not your source checkout. Use a separate data directory and port for development: the installed desktop app uses port 4783 and its normal private state. The supported `notryn uninstall` command removes managed application files while keeping notes and settings. Third-party cleanup utilities can remove additional files, so their behaviour is outside the installer's control.

- **Private release not found:** confirm `gh auth status`, repository access and the release tag. Never paste a token into a support report.
- **Notryn still running:** quit the desktop app. For a server started from the terminal, use `notryn stop`.
- **Port 4783 is occupied:** stop your other Notryn test server before opening the desktop app. The installer tests on a temporary free port and does not kill another process.
- **Checksum mismatch:** stop and retry the verified release download. Do not bypass the check.
- **Interrupted installer:** confirm no installer is running. A leftover `installation.lock` folder in the state directory can then be removed; app backups remain in the locations above.
- **Linux desktop dependencies:** the AppImage includes Electron and Python. The OS still needs a working graphical session and Electron's standard system libraries. Extraction mode avoids requiring FUSE; the installer does not disable Electron's sandbox.

## Hosting and privacy

Downloads are served by GitHub Releases over HTTPS. The desktop app runs locally. It does not depend on the developer's Mac or report completed installations. GitHub counts downloads, including repeats and updates.
