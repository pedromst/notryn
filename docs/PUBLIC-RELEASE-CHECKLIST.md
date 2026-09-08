# Public beta release record

Owner authorized public launch on 8 September 2026. This is a beta, with limits stated in the installation guide.

- [x] License: PolyForm Shield 1.0.0; contributor agreement and third-party notices prepared.
- [x] Review current Git history for credentials, personal paths and note contents. Remaining note-name references are minimal synthetic regression fixtures.
- [x] Real app demo uses fictional notes and in-memory edits.
- [x] Local Python and Node tests pass; install/update/rollback/uninstall use temporary fixtures.
- [x] Installation guide states Linux x86_64, experimental macOS Intel/ARM64, no Windows or Linux ARM package.
- [x] Native CI package lifecycle on Linux x86_64 and both Mac architectures: [run 34262733898](https://github.com/pedromst/notryn/actions/runs/34262733898), all jobs passed; beta.1 released from `084beb7`.
- [x] Both repositories public; main PR/review rules verified (owner admin exception retained), CI required for app contributions, private vulnerability reporting and secret push protection enabled.
- [x] Site and 17 core assets compared over public HTTPS against source; versioned release bootstrap matched. Real Mac Intel setup/archive downloaded without authentication, hashes checked, isolated install/update/start/stop/uninstall passed with fictional note preservation.
- [x] `notryn.com` and `www` DNS verified. Certificate approved; HTTPS enforced, HTTP and www redirect to https://notryn.com/.

Follow-up before a stable release: broader physical-device testing, Apple Developer ID/notarization, external-deletion refresh verification. Never claim these are complete based only on a successful build. There is no promise of universal Linux compatibility or Windows support.

Local tests: 98 Python and 64 Node passed. Browser inspection of the local app/demo was completed before publication; final public verification used HTTPS content checks because the in-app browser timed out. Physical Omarchy testing of this exact beta and Mac Gatekeeper/notarization remain follow-up checks.
