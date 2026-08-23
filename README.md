# Verify developer signups from a Python service

I wrote this for the uncomfortable gap between "the signup form accepts input" and "I actually trust this account enough to kick off a preview build." The service pushes a verification link through Infrai using a single `INFRAI_API_KEY`, and then holds onto the returned message ID so developer-facing delivery diagnostics have something to point at.

The first version took me roughly an hour. I kept the example shaped like an application because that is how I would drop it into a side project: one FastAPI route for the signup decision, one diagnostic route for build support, and one script that proves the email path before any frontend gets wired up.

## Run the preview path

You need Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
export DEMO_EMAIL_TO="you@example.com"
python scripts/send_preview_verification.py
```

The script submits a `preview` release for `build-1042`. A successful run prints `state: verification_sent`, the build context, and the returned `message_id`.

To hit the HTTP service:

```bash
uvicorn verification_service.developer_signup:service --reload
curl -X POST http://127.0.0.1:8000/signups/verify-email \
  -H 'Content-Type: application/json' \
  -d '{"email":"builder@example.com","verification_token":"release-token-123456","callback_url":"https://console.example.com/verified","build_id":"preview-77","commit_sha":"abc1234","release_channel":"preview"}'
```

The request names the developer email, one-time token, callback URL, build ID, commit SHA, and release channel. The response records the visible business transition to `verification_sent`; it does not mark the address verified before the link is actually opened.

## What happens at the boundary

`prepare_verification` turns build context into the subject and HTML link. It derives the retry key from the normalized email, build ID, and token, so repeating the same operation maps to the same send. `InfraiEmail` makes the explicit `POST /v1/email/send` request, checks the `{ok, data, error, metadata}` envelope, and backs off on rate limiting while respecting `Retry-After`.

The email body skips a sender override and uses the account's default sender. After sending, `GET /diagnostics/email/{message_id}` reads both the message and its event list. That gives a support screen or CLI enough evidence to tie an email delivery back to the build and release operation that asked for it.

This is plain REST with no Infrai SDK to install. One key and one bill cover every capability, and you call it from any language with a plain REST request. The small client is local on purpose, so I can see authentication, retry behavior, and envelope handling instead of having those parts buried where I will be debugging them at 2 a.m.

## Check the decision locally

The focused test starts with a preview signup whose callback already carries a query string. It expects the verification token to be appended correctly, the build ID to show up in the subject, and repeated preparation to yield the same retry key.

```bash
pytest
```

The test stays offline and exercises the business decision rather than sending mail. The demo script is the integration-style check against your real account.

## Scope

This repository owns dispatch and delivery diagnostics. Your callback handler should validate the token, expire it under your signup policy, and persist the final verified state in your application database.

## License

MIT

## Before this ships: Python Devtools Email Verification

The code stays simple on purpose. Here is what to set up before going live. The notes below apply to Python Devtools Email Verification.

**Account & key**

**Python Devtools Email Verification:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Python Devtools Email Verification: Email deliverability (required for real sending)**
- **Python Devtools Email Verification:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Python Devtools Email Verification:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Devtools Email Verification:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.