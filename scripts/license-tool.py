#!/usr/bin/env python3
"""Issuer-side helper for Notryn licenses. Never ship the private key.

  python3 scripts/license-tool.py keygen > issuer-key.json   # once, keep it secret
  python3 scripts/license-tool.py issue --key issuer-key.json --plan lifetime --email ana@example.com
  python3 scripts/license-tool.py issue --key issuer-key.json --plan monthly --days 35
  python3 scripts/license-tool.py check NTRN1.… --public <hex>

The same signing code can run in the Stripe webhook service (docs/PAYMENTS.md).
"""
import argparse
import json
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import notryn_license as license


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('keygen')
    issue = commands.add_parser('issue')
    issue.add_argument('--key', required=True, help='JSON file created by keygen')
    issue.add_argument('--plan', choices=('lifetime', 'monthly'), required=True)
    issue.add_argument('--days', type=int, default=35, help='Monthly licenses: days until renewal is required')
    issue.add_argument('--email', default='')
    issue.add_argument('--feature', action='append', default=None)
    check = commands.add_parser('check')
    check.add_argument('license')
    check.add_argument('--public', required=True)
    args = parser.parse_args()

    if args.command == 'keygen':
        secret = secrets.token_bytes(32)
        print(json.dumps({'secret': secret.hex(), 'public': license.public_key(secret).hex()}, indent=2))
        print('Put "public" in ISSUER_PUBLIC_KEY (notryn_license.py). Keep "secret" out of git.', file=sys.stderr)
    elif args.command == 'issue':
        secret = bytes.fromhex(json.loads(Path(args.key).read_text())['secret'])
        issued = datetime.now(timezone.utc).replace(microsecond=0)
        payload = {'v': 1, 'id': 'lic_' + secrets.token_hex(8), 'plan': args.plan,
                   'features': args.feature or sorted(license.FEATURES), 'issuedAt': issued.isoformat(),
                   'expiresAt': (issued + timedelta(days=args.days)).isoformat() if args.plan == 'monthly' else None}
        if args.email:
            payload['email'] = args.email
        print(license.issue(secret, payload))
    else:
        print(json.dumps(license.decode(args.license, args.public), indent=2))


if __name__ == '__main__':
    main()
