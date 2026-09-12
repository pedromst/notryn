<p align="center"><img src="web/favicon.svg" alt="Notryn" width="76"></p>
<h1 align="center">Notryn</h1>
<p align="center">Your notes. Your context. Connected.</p>

A local Markdown app for notes, projects and the connections between them. Use your mouse or keyboard. Keep your files in folders you control, ready for other editors or the AI tools you choose to give access to.

**Public beta. Free local app, source-available under PolyForm Shield.** No account or cloud subscription required. [Try the demo](https://notryn.com/#experience) · [Installation guide](https://notryn.com/guide.html)

## Install

Linux first, then macOS. The installer detects your computer, downloads the matching desktop app, verifies its checksum and creates the launcher. Python and Node.js are bundled; you do not need to install them to run Notryn.

| Platform | Package |
| --- | --- |
| Linux x86_64, including Omarchy | AppImage, installed for your user |
| macOS Intel | Desktop app in `~/Applications` |
| macOS Apple silicon | Native ARM64 package |
| Windows | Not available yet |

Run as your normal user, after saving and quitting an older Notryn:

```sh
curl -fsSL https://notryn.com/install.sh | sh
```

If the domain is unavailable, use the same versioned installer directly from GitHub:

```sh
curl -fsSL https://github.com/pedromst/notryn/releases/download/v0.2.0-beta.10/install.sh | sh
```

The installer opens the desktop app when finished. **macOS packages are experimental: ad-hoc signed, not Apple-notarized.** macOS may block them; do not disable Gatekeeper. Linux requires an x86_64 graphical system with Electron's standard system libraries. Omarchy has been tested; not every distribution is verified.

[Full installation guide](docs/INSTALL.md) · [Release notes](docs/RELEASE-NOTES.md) · [Downloads](https://github.com/pedromst/notryn/releases/tag/v0.2.0-beta.10)

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

- Write visually or in Markdown, with explicit saving, conflict protection and editable note links.
- Choose exactly where every new Brain folder is created and see its full path before confirming.
- Navigate your actual folders and see connections in an interactive Brain.
- Rename or move notes and folders while Notryn updates their resolved links.
- Use the mouse, direct shortcuts or a searchable command menu.
- Keep a personal notebook or project context for tools that can read Markdown.
- Work locally, without a Notryn account, cloud subscription or connected AI model.

[Workspace and keyboard guide](docs/USAGE.md)

## Your files stay yours

Connected folders stay where you put them. The application, settings and Brains are separate:

| System | Application | Settings and recovery data |
| --- | --- | --- |
| Linux | `~/.local/lib/notryn` | `$XDG_DATA_HOME/notryn`, normally `~/.local/share/notryn` |
| macOS | `~/Applications/Notryn.app` | `~/Library/Application Support/Notryn` |

New Brains are stored in the location you choose. Brains created by older versions remain in their existing private-state location. The local server listens only on `127.0.0.1`. Nothing is automatically uploaded to an AI model. Uninstalling keeps your data and retains recoverable application backups. Back up your own folders and private state independently.

## Current limits

The public beta is still being tested. macOS public signing/notarization and Windows packaging remain pending. There is no cloud sync or built-in generative model. Markdown plugins, HTML execution and full Obsidian plugin compatibility are not included. The index currently has safety limits of 2,000 notes and 1 MB per note.

Downloads are hosted on GitHub Releases. Your app runs on your computer and does not depend on the developer's Mac. No install telemetry is collected; GitHub package download counts do not measure unique users or completed installations.

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

Copyright 2026 Pedro Teixeira. [PolyForm Shield 1.0.0](LICENSE) permits free use for allowed purposes, including use within businesses, and restricts competing products. This is source-available, not an OSI open-source license. Third-party components retain their [own licenses](THIRD_PARTY_NOTICES.md). Optional paid sync may come later. [Contribution terms](CONTRIBUTOR-AGREEMENT.md).
