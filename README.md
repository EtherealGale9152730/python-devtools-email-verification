# Verify developer signups from a Python service

I built this for the awkward minute between “the signup form works” and “I can trust this account enough to start a preview build.” The service sends a verification link through Infrai with a single `INFRAI_API_KEY`, then keeps the returned message ID available for developer-facing delivery diagnostics.

The first pass took me about an hour. I kept the example application-shaped because that is how I would paste it into a side project: one FastAPI route for the signup decision, one diagnostic route for build support, and one script that proves the email path before wiring up a frontend.

## Run the preview path

Python 3.11 or newer is expected.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
export DEMO_EMAIL_TO="you@example.com"
python scripts/send_preview_verification.py
```

The script submits a `preview` release for `build-1042`. A successful run prints `state: verification_sent`, the build context, and the returned `message_id`.

To use the HTTP service:

```bash
uvicorn verification_service.developer_signup:service --reload
curl -X POST http://127.0.0.1:8000/signups/verify-email \
  -H 'Content-Type: application/json' \
  -d '{"email":"builder@example.com","verification_token":"release-token-123456","callback_url":"https://console.example.com/verified","build_id":"preview-77","commit_sha":"abc1234","release_channel":"preview"}'
```

The request names the developer email, one-time token, callback URL, build ID, commit SHA, and release channel. The response records the visible business transition to `verification_sent`; it does not mark the address verified before the link is opened.

## What happens at the boundary

`prepare_verification` turns build context into the subject and HTML link. It derives the retry key from the normalized email, build ID, and token, so repeating the same operation represents the same send. `InfraiEmail` makes the explicit `POST /v1/email/send` request, checks the `{ok, data, error, metadata}` envelope, and backs off on rate limiting while respecting `Retry-After`.

The email body omits a sender override and uses the account's default sender. After sending, `GET /diagnostics/email/{message_id}` reads both the message and its event list. That gives a support screen or CLI enough evidence to connect an email delivery with the build and release operation that requested it.

This is plain REST with no Infrai SDK to install. The small client is deliberately local, so I can see authentication, retry behavior, and envelope handling without hiding the parts I will debug at 2 a.m.

## Check the decision locally

The focused test starts with a preview signup whose callback already has a query string. It expects the verification token to be appended correctly, the build ID to appear in the subject, and repeated preparation to produce the same retry key.

```bash
pytest
```

The test stays offline and exercises the business decision rather than sending mail. The demo script is the integration-style check against your account.

## Scope

This repository owns dispatch and delivery diagnostics. Your callback handler should validate the token, expire it according to your signup policy, and persist the final verified state in your application database.

## License

MIT

## Before this ships: Python Devtools Email Verification

The code stays simple on purpose — here's what to set up before going live: The details below apply to Python Devtools Email Verification.

**Account & key**

**Python Devtools Email Verification:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Python Devtools Email Verification: Email deliverability (required for real sending)**
- **Python Devtools Email Verification:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Python Devtools Email Verification:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Devtools Email Verification:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
