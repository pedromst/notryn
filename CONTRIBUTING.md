# Contributing to Notryn

Thank you for helping make local-first note taking simpler, safer and more accessible.

Notryn is preparing for a public release. Every change arrives through a pull request and is reviewed before it reaches the default branch. A pull request is a proposal, not automatic permission to change the product.

## Before you start

- Search existing issues and pull requests first.
- Open an issue before a large feature or architectural change.
- Never include real Brains, notes, paths, backups, tokens, `.notryn/` data or legacy `.neura/` data.
- Keep the interface, commands, accessibility labels and documentation in English.
- Preserve normal Markdown files as the source of truth.
- Do not add a required account, cloud service, AI provider or telemetry.

## Local setup

Notryn requires Python 3.10 or later to run. Node.js is needed only for frontend development and rebuilding the visual editor.

```sh
git clone https://github.com/pedromst/notryn.git
cd notryn
python3 server.py
```

For frontend development:

```sh
npm ci
npm run build:editor
npm test
python3 -m unittest discover -s tests -v
```

All tests that write files must use temporary fixture folders. Never connect a test to a personal Brain.

## Pull requests

Keep each pull request focused. Explain:

1. The concrete problem.
2. The resulting behavior.
3. How you tested it.
4. Any effect on local files, permissions, privacy or keyboard access.

Screenshots help for visual changes. Include desktop and mobile views when layout changes. Test keyboard focus, reduced motion and readable contrast.

The repository owner reviews every pull request. Automated checks must pass, but passing checks does not guarantee acceptance.

## Security

Do not open a public issue for a vulnerability. Follow [SECURITY.md](SECURITY.md) and use GitHub's private vulnerability reporting route.

## Licensing

The public code license and contributor terms are still under review. Contributions are not being accepted until those terms are published. This private preparation repository remains unlicensed.
