import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import notryn_license as license

SECRET = bytes.fromhex('9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60')
PUBLIC = 'd75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a'


def payload(**changes):
    value = {'v': 1, 'id': 'lic_test', 'plan': 'lifetime', 'features': ['github-sync'],
             'issuedAt': '2026-10-01T00:00:00Z', 'expiresAt': None}
    value.update(changes)
    return value


class Ed25519Tests(unittest.TestCase):
    def test_rfc8032_vectors(self):
        self.assertEqual(license.public_key(SECRET).hex(), PUBLIC)
        signature = license.sign(SECRET, b'')
        self.assertEqual(signature.hex(), 'e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b')
        self.assertTrue(license.verify(bytes.fromhex(PUBLIC), b'', signature))
        self.assertFalse(license.verify(bytes.fromhex(PUBLIC), b'x', signature))
        tampered = bytes([signature[0] ^ 1]) + signature[1:]
        self.assertFalse(license.verify(bytes.fromhex(PUBLIC), b'', tampered))


class LicenseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_gate_is_off_by_default(self):
        self.assertFalse(license.PAYWALL_ENABLED)
        entitlements = license.Entitlements(self.home, enabled=False)
        self.assertTrue(entitlements.allows('github-sync'))
        self.assertEqual(entitlements.describe('github-sync')['checkout'], [])

    def test_lifetime_license_unlocks_and_is_private(self):
        entitlements = license.Entitlements(self.home, enabled=True, public_hex=PUBLIC, checkout={'lifetime': 'https://buy.stripe.com/test', 'monthly': ''})
        self.assertFalse(entitlements.allows('github-sync'))
        self.assertEqual([c['plan'] for c in entitlements.describe('github-sync')['checkout']], ['lifetime'])
        key = license.issue(SECRET, payload())
        entitlements.activate(key)
        self.assertTrue(entitlements.allows('github-sync'))
        self.assertFalse(entitlements.allows('something-else'))
        self.assertTrue(entitlements.path.is_file())
        if os.name != 'nt':
            self.assertEqual(entitlements.path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(key, json.dumps(entitlements.describe('github-sync')))
        entitlements.remove()
        self.assertFalse(entitlements.allows('github-sync'))

    def test_invalid_and_expired_licenses_are_rejected(self):
        entitlements = license.Entitlements(self.home, enabled=True, public_hex=PUBLIC)
        other = license.issue(bytes(32), payload())
        for key in ('', 'NTRN1.abc', other, license.issue(SECRET, payload(plan='team'))):
            with self.assertRaises(license.LicenseProblem):
                entitlements.activate(key)
        past = (datetime.now(timezone.utc) - license.GRACE - timedelta(days=1)).isoformat()
        with self.assertRaises(license.LicenseProblem):
            entitlements.activate(license.issue(SECRET, payload(plan='monthly', expiresAt=past)))
        with self.assertRaises(license.LicenseProblem):
            entitlements.activate(license.issue(SECRET, payload(plan='monthly')))
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        entitlements.activate(license.issue(SECRET, payload(plan='monthly', expiresAt=future)))
        self.assertTrue(entitlements.allows('github-sync'))

    def test_monthly_license_renews_near_its_end(self):
        entitlements = license.Entitlements(self.home, enabled=True, public_hex=PUBLIC, refresh_url='https://licenses.example/refresh')
        soon = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        later = (datetime.now(timezone.utc) + timedelta(days=33)).isoformat()
        entitlements.activate(license.issue(SECRET, payload(plan='monthly', expiresAt=soon)))
        renewed = license.issue(SECRET, payload(plan='monthly', expiresAt=later))
        sent = []
        self.assertTrue(entitlements.refresh(lambda url, body: sent.append(body) or {'license': renewed}))
        self.assertEqual(entitlements.license()[0]['expiresAt'], later)
        self.assertTrue(sent[0]['license'].startswith('NTRN1.'))
        self.assertFalse(entitlements.refresh(lambda url, body: {'license': 'forged'}))

    def test_unconfigured_public_key_never_unlocks(self):
        entitlements = license.Entitlements(self.home, enabled=True, public_hex='')
        with self.assertRaises(license.LicenseProblem):
            entitlements.activate(license.issue(SECRET, payload()))


if __name__ == '__main__':
    unittest.main()
