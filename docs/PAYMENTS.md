# Paid features and licenses (maintainer guide)

GitHub Sync is ready to become a paid feature, with a one-time ("lifetime") price, a monthly subscription, or both. **The gate is off today**: everyone can use GitHub Sync and the app makes no licensing requests.

This guide is for the project owner. It explains how the gate works and the steps to turn it on with Stripe.

## How it works

- `notryn_license.py` lists the paid features (`FEATURES`), holds the switch (`PAYWALL_ENABLED`), the issuer's **public** key, the checkout links and the optional renewal endpoint.
- A license is a short text the customer pastes into the app: `NTRN1.<payload>.<signature>`. The payload names the plan (`lifetime` or `monthly`), the unlocked features, and for monthly plans an end date. It is signed with an **Ed25519 private key that only the issuer has**. The app verifies the signature offline with the public key: no account, no phone-home on every launch.
- `Entitlements.allows('github-sync')` is checked by the server before any sync, account connection or scheduled run. When the gate is on and there is no valid license, the API answers `402` and the GitHub Sync dialog shows **Unlock GitHub Sync** with the checkout buttons and a license field.
- Monthly licenses carry `expiresAt` and keep working for a 5-day grace period. If `REFRESH_URL` is set, the app asks for a renewed license during the last 7 days (at most twice a day) and stores it silently. If renewal fails, the current license keeps working until it ends.
- The license file is stored with `0600` permissions and its key is never returned to the interface.

Because the app is source-available, a determined person could edit the check out of their own copy. The PolyForm Shield license and the convenience of official builds are the real protection; the gate is designed to be honest and friction-free for paying users rather than unbreakable.

## Turning it on

### 1. Create the signing key (once)

```sh
python3 scripts/license-tool.py keygen > issuer-key.json
```

Keep `issuer-key.json` **out of git** (store it in a password manager and as a secret in your license service). Copy its `public` value into `ISSUER_PUBLIC_KEY` in `notryn_license.py`.

### 2. Create the products in Stripe

1. Stripe Dashboard → **Product catalog** → add *Notryn GitHub Sync*.
2. Add a **one-time** price (lifetime) and/or a **recurring monthly** price.
3. For each price create a **Payment Link**. Collect the customer's email. Set the confirmation page to a "thank you, check your email" page.
4. Put the Payment Link URLs in `CHECKOUT_URLS` in `notryn_license.py`, and adjust `PRICE_LABELS` (for example `"Lifetime · €29"`, `"Monthly · €3"`).

### 3. Deliver licenses automatically (license service)

A tiny serverless function (Cloudflare Worker, Vercel or Supabase Edge Function) receives Stripe webhooks and emails a license:

| Stripe event | Action |
| --- | --- |
| `checkout.session.completed` (one-time price) | Issue `plan: "lifetime"`, `expiresAt: null`, email it. |
| `invoice.paid` (subscription) | Issue `plan: "monthly"`, `expiresAt` = period end, email it and remember it by subscription id. |
| `customer.subscription.deleted` | Stop renewing. The current license expires on its own. |

Optional `POST /refresh` (set `REFRESH_URL`): receives `{"license": "NTRN1…"}`, verifies it, looks up the subscription, and if it is paid returns `{"license": "<new license with the next period end>"}`.

Rules for the service:

- Verify every webhook with the Stripe signing secret before acting.
- Keep the Ed25519 private key and Stripe keys in the platform's secret store.
- Sign exactly like `notryn_license.issue`: `body = "NTRN1." + base64url(JSON payload, sorted keys, no spaces)`, `signature = Ed25519(body)`, license = `body + "." + base64url(signature)` (no `=` padding). Web Crypto supports Ed25519 in Workers and Node 20+.
- Payload fields: `{"v":1,"id":"lic_…","plan":"lifetime"|"monthly","features":["github-sync"],"issuedAt":"…","expiresAt":null|"…","email":"…"}`.

For manual sales or support you can issue a license locally:

```sh
python3 scripts/license-tool.py issue --key issuer-key.json --plan lifetime --email ana@example.com
python3 scripts/license-tool.py check "NTRN1.…" --public <public hex>
```

### 4. Flip the switch

1. Set `PAYWALL_ENABLED = True` in `notryn_license.py`.
2. Update the website and `docs/SYNC.md` with the price and what existing beta users get (for example a grace period or a free license).
3. Test locally before releasing:
   ```sh
   NOTRYN_PAYWALL=1 python3 server.py --data-dir /tmp/notryn-paywall-test
   ```
   Open GitHub Sync: it shows **Unlock GitHub Sync**. Paste a license from `license-tool.py issue` and sync unlocks.
4. Release a new version as usual.

### Adding more paid features later

Add an entry to `FEATURES`, issue licenses that list the feature, and call `entitlements.allows('<feature>')` in the server before the feature runs. `Entitlements.describe()` gives the interface everything it needs to show an unlock panel.
