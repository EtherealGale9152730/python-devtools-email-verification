from __future__ import annotations

import hashlib
import html
from dataclasses import dataclass
from urllib.parse import urlencode

from pydantic import BaseModel, EmailStr, Field, HttpUrl

from .infrai_email import InfraiEmail


class SignupRequest(BaseModel):
    email: EmailStr
    verification_token: str = Field(min_length=16)
    callback_url: HttpUrl
    build_id: str = Field(min_length=1, max_length=120)
    commit_sha: str = Field(pattern=r"^[0-9a-f]{7,40}$")
    release_channel: str = Field(pattern=r"^(preview|production)$")


class VerificationDispatch(BaseModel):
    state: str
    message_id: str
    build_id: str
    release_channel: str


@dataclass(frozen=True)
class VerificationEmail:
    to: str
    subject: str
    html: str
    idempotency_key: str


def prepare_verification(request: SignupRequest) -> VerificationEmail:
    query = urlencode({"token": request.verification_token})
    separator = "&" if "?" in str(request.callback_url) else "?"
    verification_url = f"{request.callback_url}{separator}{query}"
    safe_build = html.escape(request.build_id)
    safe_commit = html.escape(request.commit_sha)
    safe_url = html.escape(verification_url, quote=True)
    stable_input = f"{request.email.lower()}:{request.build_id}:{request.verification_token}"
    idempotency_key = "signup-verification-" + hashlib.sha256(stable_input.encode()).hexdigest()
    return VerificationEmail(
        to=str(request.email),
        subject=f"Verify your developer account for build {request.build_id}",
        html=(
            f"<h1>Verify your email</h1><p>Build <strong>{safe_build}</strong> "
            f"at commit <code>{safe_commit}</code> is waiting for you.</p>"
            f'<p><a href="{safe_url}">Verify developer account</a></p>'
        ),
        idempotency_key=idempotency_key,
    )


async def dispatch_verification(
    request: SignupRequest, email_client: InfraiEmail
) -> VerificationDispatch:
    prepared = prepare_verification(request)
    data = await email_client.send(
        {"to": prepared.to, "subject": prepared.subject, "html": prepared.html},
        prepared.idempotency_key,
    )
    message_id = data.get("message_id")
    if not isinstance(message_id, str) or not message_id:
        raise ValueError("Email response did not include message_id")
    return VerificationDispatch(
        state="verification_sent",
        message_id=message_id,
        build_id=request.build_id,
        release_channel=request.release_channel,
    )
