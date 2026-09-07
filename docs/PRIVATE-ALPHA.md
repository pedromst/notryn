# Notryn 0.2.0-alpha.2

This is a private test build for the repository owner. It is not a public release.

Alpha 2 fixes the first connection on Linux: after opening or creating a Brain folder, its folders and Markdown files now appear immediately without restarting Notryn.

The downloads are hosted as assets on this repository's private GitHub Release. The installers do not require administrator access. They verify the downloaded archive, install the application only for the current user, and open Notryn in its own desktop window. The private server binds only to `127.0.0.1`, and Brains and private state stay outside the application directory. Reinstalling or uninstalling the app does not delete those files.

## Omarchy and x86_64 Linux

Install GitHub CLI once if it is not already available, then sign in to the GitHub account that can access this private repository:

```sh
gh auth login
```

Download this private release and install it:

```sh
mkdir -p "$HOME/Downloads/notryn-alpha"
gh release download v0.2.0-alpha.2 --repo pedromst/notryn --clobber --pattern '*linux*' --pattern 'install-notryn-linux.sh' --dir "$HOME/Downloads/notryn-alpha"
sh "$HOME/Downloads/notryn-alpha/install-notryn-linux.sh" "$HOME/Downloads/notryn-alpha/Notryn-0.2.0-alpha.2-linux-x86_64.tar.gz"
```

Close Notryn before reinstalling an updated alpha. Reinstalling replaces the application package and preserves connected Brains and settings.

Notryn appears in the desktop application menu and opens as a normal application, without a browser address bar. Its private local server can also be managed from the terminal:

```sh
notryn status
notryn stop
notryn uninstall
```

If `notryn` is not found in a newly opened terminal, add the standard user binary directory to the shell path:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

The application is installed at `~/.local/lib/notryn`. Its launcher and desktop entry use the normal per-user XDG locations. Brains and settings stay at `~/.local/share/notryn`, or under `$XDG_DATA_HOME/notryn` when that variable is configured.

## Intel macOS private test

```sh
mkdir -p "$HOME/Downloads/notryn-alpha"
gh release download v0.2.0-alpha.2 --repo pedromst/notryn --clobber --pattern '*macos*' --pattern 'install-notryn-macos.sh' --dir "$HOME/Downloads/notryn-alpha"
sh "$HOME/Downloads/notryn-alpha/install-notryn-macos.sh" "$HOME/Downloads/notryn-alpha/Notryn-0.2.0-alpha.2-macos-x86_64.zip"
```

The app is installed at `~/Applications/Notryn.app`, opens in its own macOS window and keeps its separate state at `~/Library/Application Support/Notryn`.

This macOS alpha has an ad-hoc signature for private testing. A public macOS release must be signed with a Developer ID certificate and notarized by Apple. The Linux archive currently supports x86_64; ARM64 packages will be added before a public release.

Because this private macOS build is not notarized, macOS can ask for an explicit first-open decision under **System Settings → Privacy & Security** after a GitHub download. The installer does not remove quarantine or bypass Gatekeeper.

## Existing development state

To copy an existing `.neura` or `.notryn` private state into the installed app without changing the source, add:

```sh
--state-source "/absolute/path/to/.neura"
```

The migration runs only when the installed state has not already been initialized. It copies the private state and rewrites only its internal absolute state paths. The original folder is left unchanged.
