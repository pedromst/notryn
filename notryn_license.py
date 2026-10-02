"""Paid feature entitlements. Standard library only.

Ed25519 adapted from the RFC 8032 section 6 reference code (Simplified BSD
License, IETF Trust); see THIRD_PARTY_NOTICES.md.

The gate is OFF by default: every feature is available and nothing here talks
to the network. When payments are ready, the owner sets the issuer public key
and Stripe Payment Links below and enables the gate (see docs/PAYMENTS.md).

A license is an offline-verifiable Ed25519 signature made by the issuer's
private key, which never ships with the app:

    NTRN1.<base64url(JSON payload)>.<base64url(signature)>

Payload: {"v":1,"id":"lic_…","plan":"lifetime"|"monthly","features":[…],
          "issuedAt":"…","expiresAt":null|"…","email":"…"}
"""
import base64
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------- settings
# Flip to True (or set NOTRYN_PAYWALL=1) only after the values below are set.
PAYWALL_ENABLED = False
# Hex Ed25519 public key printed by `python3 scripts/license-tool.py keygen`.
ISSUER_PUBLIC_KEY = ''
# Stripe Payment Links (or any checkout page) for each plan.
CHECKOUT_URLS = {'lifetime': '', 'monthly': ''}
PRICE_LABELS = {'lifetime': 'One payment, yours forever', 'monthly': 'Monthly subscription'}
# Endpoint that exchanges a paid-up monthly license for a renewed one:
# POST {"license": "NTRN1…"} -> {"license": "NTRN1…"}. Empty disables renewal.
REFRESH_URL = ''
# Monthly licenses keep working briefly offline after their paid period.
GRACE = timedelta(days=5)

FEATURES = {
    'github-sync': {'name': 'GitHub Sync', 'plans': ('lifetime', 'monthly')},
}
PREFIX = 'NTRN1'


class LicenseProblem(Exception):
    pass


# ------------------------------------------------- Ed25519 (RFC 8032 §6)
_P = 2 ** 255 - 19
_Q = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)


def _inv(x):
    return pow(x, _P - 2, _P)


def _add(a, b):
    A = (a[1] - a[0]) * (b[1] - b[0]) % _P
    B = (a[1] + a[0]) * (b[1] + b[0]) % _P
    C = 2 * a[3] * b[3] * _D % _P
    D = 2 * a[2] * b[2] % _P
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _P, G * H % _P, F * G % _P, E * H % _P)


def _mul(scalar, point):
    result = (0, 1, 1, 0)
    while scalar > 0:
        if scalar & 1:
            result = _add(result, point)
        point = _add(point, point)
        scalar >>= 1
    return result


def _equal(a, b):
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _recover_x(y, sign):
    if y >= _P:
        return None
    x2 = (y * y - 1) * _inv(_D * y * y + 1)
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P:
        return None
    if (x & 1) != sign:
        x = _P - x
    return x


_GY = 4 * _inv(5) % _P
_GX = _recover_x(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % _P)


def _compress(point):
    zinv = _inv(point[2])
    x, y = point[0] * zinv % _P, point[1] * zinv % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, 'little')


def _decompress(data):
    if len(data) != 32:
        return None
    y = int.from_bytes(data, 'little')
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


def _hash_int(data):
    return int.from_bytes(hashlib.sha512(data).digest(), 'little') % _Q


def _expand(secret):
    if len(secret) != 32:
        raise ValueError('Ed25519 secret keys are 32 bytes.')
    digest = hashlib.sha512(secret).digest()
    scalar = int.from_bytes(digest[:32], 'little')
    scalar &= (1 << 254) - 8
    scalar |= 1 << 254
    return scalar, digest[32:]


def public_key(secret):
    return _compress(_mul(_expand(secret)[0], _G))


def sign(secret, message):
    scalar, prefix = _expand(secret)
    public = _compress(_mul(scalar, _G))
    r = _hash_int(prefix + message)
    encoded_r = _compress(_mul(r, _G))
    s = (r + _hash_int(encoded_r + public + message) * scalar) % _Q
    return encoded_r + int.to_bytes(s, 32, 'little')


def verify(public, message, signature):
    if len(public) != 32 or len(signature) != 64:
        return False
    a = _decompress(public)
    r = _decompress(signature[:32])
    if a is None or r is None:
        return False
    s = int.from_bytes(signature[32:], 'little')
    if s >= _Q:
        return False
    h = _hash_int(signature[:32] + public + message)
    return _equal(_mul(s, _G), _add(r, _mul(h, a)))


# ------------------------------------------------------------- licenses
def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _unb64(text):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', text or ''):
        raise LicenseProblem('This license key is incomplete.')
    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def issue(secret, payload):
    """Create a license. Used only by the issuer (scripts/license-tool.py)."""
    body = PREFIX + '.' + _b64(json.dumps(payload, separators=(',', ':'), sort_keys=True).encode())
    return body + '.' + _b64(sign(secret, body.encode()))


def _parse_time(value):
    try:
        moment = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        raise LicenseProblem('This license has an invalid date.')
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def decode(key, public_hex, now=None):
    """Return the verified payload or raise LicenseProblem."""
    key = (key or '').strip()
    parts = key.split('.')
    if len(parts) != 3 or parts[0] != PREFIX or len(key) > 4096:
        raise LicenseProblem('This is not a Notryn license key.')
    try:
        public = bytes.fromhex(public_hex or '')
    except ValueError:
        public = b''
    if len(public) != 32:
        raise LicenseProblem('License checking is not configured in this version.')
    if not verify(public, (parts[0] + '.' + parts[1]).encode(), _unb64(parts[2])):
        raise LicenseProblem('This license key is not valid.')
    try:
        payload = json.loads(_unb64(parts[1]))
    except ValueError:
        raise LicenseProblem('This license key is damaged.')
    if not isinstance(payload, dict) or payload.get('v') != 1 or payload.get('plan') not in {'lifetime', 'monthly'}:
        raise LicenseProblem('This license format is not supported.')
    if not isinstance(payload.get('features'), list):
        raise LicenseProblem('This license does not list any features.')
    if payload.get('expiresAt'):
        if _parse_time(payload['expiresAt']) + GRACE < (now or datetime.now(timezone.utc)):
            raise LicenseProblem('This subscription has ended. Renew it to keep using paid features.')
    elif payload['plan'] == 'monthly':
        raise LicenseProblem('This subscription license has no end date.')
    return payload


def _post_json(url, value):
    from urllib.request import Request, urlopen
    from notryn_install import https_context
    request = Request(url, data=json.dumps(value).encode(), headers={'Content-Type': 'application/json', 'User-Agent': 'Notryn'})
    with urlopen(request, timeout=20, context=https_context()) as response:
        return json.loads(response.read())


class Entitlements:
    """Answers "may this feature run?" and keeps the license file private."""

    def __init__(self, home, enabled=None, public_hex=None, checkout=None, refresh_url=None):
        self.path = Path(home) / 'license.json'
        self.refresh_url = REFRESH_URL if refresh_url is None else refresh_url
        self.refreshed = 0
        flag = os.environ.get('NOTRYN_PAYWALL')
        self.enabled = enabled if enabled is not None else (PAYWALL_ENABLED or flag == '1')
        self.public_hex = ISSUER_PUBLIC_KEY if public_hex is None else public_hex
        self.checkout = CHECKOUT_URLS if checkout is None else checkout

    def _stored_key(self):
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
            return value.get('key') if isinstance(value, dict) else None
        except (OSError, ValueError):
            return None

    def license(self):
        key = self._stored_key()
        if not key:
            return None, None
        try:
            return decode(key, self.public_hex), None
        except LicenseProblem as error:
            return None, str(error)

    def allows(self, feature):
        if not self.enabled:
            return True
        payload, _ = self.license()
        return bool(payload and feature in payload['features'])

    def activate(self, key):
        payload = decode(key, self.public_hex)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.notryn-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'key': key.strip(), 'activatedAt': datetime.now(timezone.utc).isoformat()}, stream)
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return payload

    def refresh(self, post=None):
        """Renew a monthly license close to its end. Quietly keeps the old one on failure."""
        import time
        payload, _ = self.license()
        if (not self.enabled or not self.refresh_url.startswith('https://') or not payload or
                payload['plan'] != 'monthly' or time.time() - self.refreshed < 12 * 3600):
            return False
        if _parse_time(payload['expiresAt']) - datetime.now(timezone.utc) > timedelta(days=7):
            return False
        self.refreshed = time.time()
        try:
            answer = (post or _post_json)(self.refresh_url, {'license': self._stored_key()})
            self.activate(str(answer.get('license') or ''))
            return True
        except (LicenseProblem, OSError, ValueError, AttributeError):
            return False

    def remove(self):
        self.path.unlink(missing_ok=True)

    def describe(self, feature):
        """Public summary for the interface. Never includes the key itself."""
        payload, problem = self.license() if self.enabled else (None, None)
        plans = FEATURES.get(feature, {}).get('plans', ())
        return {
            'feature': feature,
            'name': FEATURES.get(feature, {}).get('name', feature),
            'paywall': self.enabled,
            'allowed': self.allows(feature),
            'plan': payload.get('plan') if payload else None,
            'expiresAt': payload.get('expiresAt') if payload else None,
            'problem': problem,
            'checkout': [{'plan': plan, 'label': PRICE_LABELS.get(plan, plan), 'url': self.checkout.get(plan, '')}
                         for plan in plans if self.enabled and self.checkout.get(plan, '').startswith('https://')],
        }
