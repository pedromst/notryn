<p align="center"><img src="web/favicon.svg" alt="Notryn" width="76"></p>
<h1 align="center">Notryn</h1>
<p align="center">Your notes. Your context. Connected.</p>

A local Markdown app for notes, projects and the connections between them. Use your mouse or keyboard. Keep your files in folders you control, ready for other editors or the AI tools you choose to give access to.

**Private alpha.** Public launch, the website and the code license are still under review. No cloud account is needed to use the app; access to this private repository is required to download it for now.

## Install

Linux first, then macOS. The installer detects your computer, downloads the matching desktop app, verifies its checksum and creates the launcher. Python and Node.js are bundled; you do not need to install them to run Notryn.

| Platform | Package |
| --- | --- |
| Linux x86_64, including Omarchy | AppImage, installed for your user |
| macOS Intel | Desktop app in `~/Applications` |
| macOS Apple silicon | Native ARM64 package |
| Windows | Not available yet |

For private testing, install [GitHub CLI](https://cli.github.com/) and sign in once:

```sh
gh auth login
```

Then download and run the installer for this release:

```sh
(notryn_setup_dir=$(mktemp -d) && gh release download v0.2.0-alpha.3 --repo pedromst/notryn --pattern install.sh --dir "$notryn_setup_dir" && sh "$notryn_setup_dir/install.sh" --private)
```

Close Notryn before upgrading an earlier alpha. The installer opens the desktop application when it finishes. macOS packages are still ad-hoc signed, not Apple-notarized; this is a private test, not the finished public macOS distribution.

[Full installation guide](docs/INSTALL.md) · [Release notes](docs/PRIVATE-ALPHA.md) · [Private downloads](https://github.com/pedromst/notryn/releases/tag/v0.2.0-alpha.3)

## Everyday commands

| Task | Command |
| --- | --- |
| Open the desktop app | `notryn` |
| Check the installed version | `notryn version` |
| Update after saving and quitting the app | `notryn update` |
| Return to the previous application version | `notryn rollback` |
| Uninstall, keeping notes and settings | `notryn uninstall` |

If your shell cannot find `notryn`, use `~/.local/bin/notryn` or add `~/.local/bin` to your PATH. The installer does not edit your shell profile.

Updating downloads the package first and checks its integrity and local server before replacing the app. A failed replacement restores the previous app. Notes and settings stay separate. Rollback changes the application only; it is not a note backup.

## What you can do

- Write visually or in Markdown, with explicit saving and conflict protection.
- Navigate your actual folders and see connections in an interactive Brain.
- Use the mouse, direct shortcuts or a searchable command menu.
- Keep a personal notebook or project context for tools that can read Markdown.
- Work locally, without a Notryn account, cloud subscription or connected AI model.

[Workspace and keyboard guide](docs/USAGE.md)

## Your files stay yours

Connected folders stay where you put them. The application, settings and Brains are separate:

| System | Application | Settings and app-created Brains |
| --- | --- | --- |
| Linux | `~/.local/lib/notryn` | `$XDG_DATA_HOME/notryn`, normally `~/.local/share/notryn` |
| macOS | `~/Applications/Notryn.app` | `~/Library/Application Support/Notryn` |

The local server listens only on `127.0.0.1`. Nothing is automatically uploaded to an AI model. Uninstalling keeps your data and retains recoverable application backups. Back up your own folders and private state independently.

## Current limits

The private alpha is still being tested. macOS public signing/notarization and Windows packaging remain pending. There is no cloud sync or built-in generative model. Markdown plugins, HTML execution and full Obsidian plugin compatibility are not included. The index currently has safety limits of 2,000 notes and 1 MB per note.

The first public installation endpoint will be `https://notryn.com/install.sh` **after approval and HTTPS deployment**. The domain is not an active installer yet. Downloads will live on GitHub Releases, not on the developer's Mac.

## Development and project

```sh
python3 server.py
```

Open `http://127.0.0.1:4783`. Source development requires Python 3.10+. To rebuild the editor or run checks:

```sh
npm ci
npm test
python3 -m unittest discover -s tests -v
```

[Distribution and trust model](docs/DISTRIBUTION.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Public release checklist](docs/PUBLIC-RELEASE-CHECKLIST.md)

Code remains `UNLICENSED` while the license and contributor terms are decided. No public redistribution rights are granted yet. The intended model is a free local app with optional paid sync later.
