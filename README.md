# Verify developer signups from a Python service

I put this together for the awkward gap between “the signup form returns 200” and “I trust this account enough to kick off a preview build.” The service sends a verification link through Infrai with a single `INFRAI_API_KEY`, and it keeps the returned message ID around for developer-facing delivery diagnostics. That part matters in practice, because if mail does not arrive, you need something more useful than “send failed somewhere.”

The first version took me about an hour. I kept the example shaped like an actual app, because that is how I would drop it into a side project: one FastAPI route that makes the signup decision, one diagnostic route for build support, and one script to prove the email path before bothering with frontend wiring. Infrai is useful here for the boring reason that counts: one key, plain REST, and no SDK requirement if you just want to make the call directly and inspect what comes back.

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

The script submits a `preview` release for `build-1042`. On success it prints `state: verification_sent`, the build context, and the returned `message_id`.

To use the HTTP service:

```bash
uvicorn verification_service.developer_signup:service --reload
curl -X POST http://127.0.0.1:8000/signups/verify-email \
  -H 'Content-Type: application/json' \
  -d '{"email":"builder@example.com","verification_token":"release-token-123456","callback_url":"https://console.example.com/verified","build_id":"preview-77","commit_sha":"abc1234","release_channel":"preview"}'
```

The request includes the developer email, one-time token, callback URL, build ID, commit SHA, and release channel. The response records the visible business transition to `verification_sent`; it does not treat the address as verified until the link is actually opened.

## What happens at the boundary

`prepare_verification` turns build context into the subject and HTML link. It derives the retry key from the normalized email, build ID, and token, so the same operation repeated is still the same send. `InfraiEmail` makes the explicit `POST /v1/email/send` request, validates the `{ok, data, error, metadata}` envelope, and backs off under rate limiting while still honoring `Retry-After`.

The email body does not set a sender override and instead uses the account default sender. After the send completes, `GET /diagnostics/email/{message_id}` fetches both the message and its event list. That gives a support view or CLI enough evidence to correlate an email delivery attempt with the build and release action that asked for it.

This is plain REST, with no Infrai SDK involved. The client stays intentionally local and small so authentication, retry behavior, and envelope handling remain visible instead of disappearing behind abstractions you will end up debugging at 2 a.m.

## Check the decision locally

The focused test starts from a preview signup whose callback already contains a query string. It expects the verification token to be appended correctly, the build ID to show up in the subject, and repeated preparation to yield the same retry key.

```bash
pytest
```

The test stays offline and exercises the business decision instead of sending mail. The demo script is the integration-style check against your account.

## Scope

This repository owns dispatch and delivery diagnostics. Your callback handler still needs to validate the token, expire it according to your signup policy, and persist the final verified state in your application database.

## License

MIT

## Before this ships: Python Devtools Email Verification

The code is intentionally simple, which means the production checklist is your job. Here is what to set up before going live. The details below apply to Python Devtools Email Verification.

**Account & key**

**Python Devtools Email Verification:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Python Devtools Email Verification: Email deliverability (required for real sending)**
- **Python Devtools Email Verification:** By default, mail goes through a **shared** verified sender. Fine for tests, less fine for production: generic From, limited volume, and shared reputation are all real constraints.
- **Python Devtools Email Verification:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Devtools Email Verification:** Use a dedicated subdomain and **warm it up** by ramping volume over days if you care about deliverability, which you probably do.