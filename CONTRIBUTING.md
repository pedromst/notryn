# Contributing to Notryn

Bug reports, documentation improvements and pull requests are welcome. Please discuss large changes in an issue first. Keep each PR focused on a concrete problem, with reproduction steps and relevant checks.

## Rights and review

Notryn is source-available under [PolyForm Shield 1.0.0](LICENSE). It is free to use, including in a business, for purposes permitted by that license. Competing products are restricted. It is not MIT or an OSI open-source license.

Before submitting code, read the [contributor agreement](CONTRIBUTOR-AGREEMENT.md) and confirm acceptance in your PR. You retain ownership of your contribution. The agreement allows the project owner to maintain, distribute and commercially license the combined project. Contributions from an employer require their permission where applicable.

The owner reviews PRs before merging. Passing checks are required but do not guarantee a change is safe or will be accepted. Do not upload real notes, Brain state, credentials, personal paths or recovery files. Use fictional fixtures only. Report security concerns [privately](SECURITY.md).

## Development

Python 3.10+ and Node.js 20+ are required for source development. They are not prerequisites for the packaged app.

```sh
npm ci
python3 server.py
```

Open http://127.0.0.1:4783. Run relevant checks before submitting:

```sh
npm test
python3 -m unittest discover -s tests -v
node scripts/build-site.mjs --check
node scripts/build-demo.mjs --check
node scripts/test-demo.cjs
```

For UI changes, include desktop and mobile screenshots. Demo UI is built from the app; refresh it with `node scripts/build-site.mjs` and `node scripts/build-demo.mjs`. Interface text and project documentation are in English.

Be respectful, specific and constructive. Harassment, discriminatory abuse and disclosure of private information are not welcome. The maintainer may remove disruptive content and decline contributions.
