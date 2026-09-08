# Install, update and uninstall

Private alpha `0.2.0-alpha.3`. Linux/Omarchy first; macOS Intel and Apple silicon packages use the same commands. Windows has no installer yet.

## Before installing

- Use your normal account, without `sudo`.
- Save your notes and quit Notryn before installing or updating.
- For private downloads only: install GitHub CLI from https://cli.github.com/ and run `gh auth login` with the account that has repository access. No token is placed in the command or saved by Notryn.
- No destination Python or Node.js installation is needed: the setup program and app are bundled.

## Private installation

```sh
(notryn_setup_dir=$(mktemp -d) && gh release download v0.2.0-alpha.3 --repo pedromst/notryn --pattern install.sh --dir "$notryn_setup_dir" && sh "$notryn_setup_dir/install.sh" --private)
```

The command uses a fresh temporary directory. If you prefer separate steps:

```sh
notryn_download_dir=$(mktemp -d)
gh release download v0.2.0-alpha.3 --repo pedromst/notryn --pattern install.sh --dir "$notryn_download_dir"
sh "$notryn_download_dir/install.sh" --private
```

Add `--no-open` to install without opening the app. The bootstrap detects the OS and architecture, verifies the setup checksum, and runs the setup program. The setup then downloads the app, compares its SHA-256 with the GitHub release asset digest, checks the archive paths and tests its local server in disposable state. It then installs the app and creates the launcher.

On Linux, open **Notryn** from the app menu. On macOS, open **Notryn.app** in your user's **Applications** folder. Running `notryn` opens this same desktop app, not a browser tab.

### macOS private alpha

The packages use an ad-hoc signature checked during installation. They are not signed with an Apple Developer ID or notarized yet. A downloaded alpha may be blocked by macOS. Do not disable Gatekeeper or remove quarantine as part of installation. Public release requires Developer ID signing, notarization and a fresh download test on a separate Mac.

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

The private installation uses GitHub CLI and selects the newest published alpha. Public installations will select stable releases. Your authenticated GitHub session must still have repository access for private updates.

To choose a specific newer release:

```sh
notryn update --version 0.2.0-alpha.3
```

The app refuses downgrades through update. It keeps the current version if the download, checksum, package validation or local-server test fails. When replacement fails, it restores the previous app. It does not close an open editor or discard an unsaved draft for you.

**Coming from alpha.2:** run the new installer above once. The old `notryn update` command only printed instructions; the new lifecycle commands arrive with alpha.3.

## Return to the previous version

Save and quit, then:

```sh
notryn rollback
```

This switches to the previous application backup. Notes and settings remain current. Notryn also keeps the version you left, so a second rollback can switch back. If no previous app exists, it tells you instead of downloading an arbitrary old version.

If rolling back to alpha.2, that older program has no real update/rollback implementation; run the alpha.3 installer again to move forward.

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
| State and app-created Brains | `$XDG_DATA_HOME/notryn` or `~/.local/share/notryn` | `~/Library/Application Support/Notryn` |

Use the same normal user and state location when updating. A custom `NOTRYN_HOME` remains supported for terminal server work; it is not a way to relocate the desktop installation.

## Troubleshooting

- **Private release not found:** confirm `gh auth status`, repository access and the release tag. Never paste a token into a support report.
- **Notryn still running:** quit the desktop app. For a server started from the terminal, use `notryn stop`.
- **Port 4783 is occupied:** stop your other Notryn test server before opening the desktop app. The installer tests on a temporary free port and does not kill another process.
- **Checksum mismatch:** stop and retry the verified release download. Do not bypass the check.
- **Interrupted installer:** confirm no installer is running. A leftover `installation.lock` folder in the state directory can then be removed; app backups remain in the locations above.
- **Linux desktop dependencies:** the AppImage includes Electron and Python. The OS still needs a working graphical session and Electron's standard system libraries. Extraction mode avoids requiring FUSE; the installer does not disable Electron's sandbox.

## After public approval

The planned command is `curl -fsSL https://notryn.com/install.sh | sh`. It is not live yet. Public files will be downloaded from GitHub Releases over HTTPS; your app runs on your computer and does not depend on the developer's Mac remaining online.
