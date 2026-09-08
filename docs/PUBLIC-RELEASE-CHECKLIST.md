# Public release checklist

The private repository is a preparation and backup space. Complete this review before changing its visibility.

## Product safety

- [ ] Review every path boundary, symbolic-link guard and read-only check.
- [ ] Verify that save, move, remove and restore cannot overwrite unrelated files.
- [ ] Test fresh installation without any personal Brain, `.notryn/` state or legacy `.neura/` state.
- [x] Install and open the private x86_64 package on Linux/Omarchy.
- [ ] Complete native interaction coverage on Linux/Omarchy and Windows.
- [ ] Confirm external file deletion refreshes the library and Brain safely.
- [ ] Review the temporary sharing gateway and document its limits.

## Repository hygiene

- [ ] Confirm `.notryn/`, legacy `.neura/`, notes, backups, logs, environment files and credentials are absent from the entire Git history.
- [ ] Scan tracked files for personal paths and temporary tunnel URLs.
- [ ] Review bundled fonts, icons and editor dependency notices.
- [ ] Choose and publish the code license and contributor terms.
- [ ] Enable private vulnerability reporting and branch protection or a ruleset.
- [ ] Require pull requests, passing tests and owner review for the default branch.

## Distribution

- [ ] Choose the public license and contributor terms after legal review. Document clearly whether Notryn is open source or source-available, and how the optional commercial sync component remains separate.
- [x] Define and test install, update, rollback and uninstall while preserving Brains (alpha.3).
- [x] Document tested Linux x86_64 and macOS Intel/ARM64 terminal installation, update and uninstall.
- [ ] Add and test Windows packaging before advertising support.
- [x] Verify SHA-256 release digests and native package lifecycle on Linux and both Mac architectures.
- [ ] Complete public publisher signing/notarization.
- [x] Publish private tagged alpha.3 with explicit platform support; public release remains gated.
- [ ] Change repository visibility only after the release candidate passes review.
- [ ] Enable GitHub Pages and verify the public landing page on desktop and mobile.

## Communication

- [ ] Replace the illustrative landing Brain with a faithful interactive demo of the real Notryn Brain, using safe demonstration data and supporting pointer, touch and keyboard navigation.
- [ ] Replace private-preview wording on the landing page and README.
- [ ] State clearly what is local, what is optional and what is not included.
- [ ] Publish a security contact, contribution guide and code of conduct.
- [ ] Explain the future sync plugin separately from the free local core.
