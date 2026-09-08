# Distribution and trust model

## First phase

Free local desktop app, distributed through GitHub Releases. Linux x86_64 first, macOS x86_64/arm64 next. Windows is explicitly pending until there is a tested package. No cloud login is required by the app. Private alpha downloads require GitHub CLI authentication; public downloads will not.

The domain will host a small bootstrap at `/install.sh`. It detects the target, obtains a standalone setup executable for the selected release, checks SHA-256 and runs it. Setup validates the app archive against the release asset metadata and runs the new sidecar in disposable state before activation. Updating uses the same installation code bundled in the CLI.

GitHub publishes SHA-256 digests in [release asset metadata](https://docs.github.com/en/rest/releases/assets). The private bootstrap checks its setup binary against this digest; the public bootstrap retrieves its checksum from the same tagged HTTPS release. The setup program verifies the app against the API digest in both modes. These checks detect corrupted or substituted downloads relative to the trusted release; they do not protect against a compromised release maintainer or replace independent publisher signatures.

## Safety boundaries

- Fixed repository `pedromst/notryn`; no arbitrary download host or script URL option.
- Validated version tags, expected asset names, SHA-256 and bounded archive/download sizes.
- Archive paths and links validated before extraction. Only internal application symlinks are allowed; special files, duplicate paths and writes through links are refused.
- Setup refuses root and existing unrelated installation paths.
- An installation lock coordinates setup and managed server startup. A live app must be saved and closed by its user.
- New app staged on the same filesystem; the previous version is retained before activation. Failed activation restores it.
- Application metadata stays outside signed macOS bundles.
- No automatic note/state migrations, shell-profile edits, sudo, telemetry, remote access, quarantine removal or sandbox bypass.
- Rollback reverts app files only. User data must be backed up separately.
- Uninstall retains recoverable app backups and all note/state data.

## Build and verification

`packaging/linux/build-alpha.sh` and `packaging/macos/build-alpha.sh` build the app and standalone setup. PyInstaller, Electron and editor dependencies are pinned. `scripts/test-package.py` exercises native archives using disposable homes with spaces, start/status/stop, refusal while running, rollback twice and uninstall/data preservation.

The private packaging workflow runs on Linux, macOS Intel and macOS ARM64. All package checks must pass before a private prerelease is created. Existing release tags/assets are never replaced by this workflow. Bump versions in `notryn_version.py`, `package.json`, `package-lock.json`, bootstrap and documentation for another release.

## Public launch gates

- Confirm license, contributor terms and repository history hygiene.
- Require owner review and passing checks for releases.
- Obtain Apple Developer ID and notarize the Mac app and setup; validate fresh downloads on physical Macs.
- Test Linux in a clean Omarchy session, including native desktop launch/update.
- Define Windows packaging/signing before claiming Windows support.
- Deploy approved static site and bootstrap to HTTPS, configure `notryn.com`, verify downloads from a separate machine.
- Publish only after Pedro approves the site and first release.
