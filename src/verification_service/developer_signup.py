from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .infrai_email import InfraiEmail, InfraiError
from .signup_verification import SignupRequest, VerificationDispatch, dispatch_verification


class DeliveryDiagnostics(BaseModel):
    message: dict[str, object]
    events: dict[str, object]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("INFRAI_API_KEY is required")
    app.state.email_client = InfraiEmail(api_key)
    yield
    await app.state.email_client.close()


service = FastAPI(title="Developer signup verification", lifespan=lifespan)


def get_email_client(request: Request) -> InfraiEmail:
    return request.app.state.email_client


@service.post("/signups/verify-email", response_model=VerificationDispatch)
async def verify_signup(
    signup: SignupRequest, client: InfraiEmail = Depends(get_email_client)
) -> VerificationDispatch:
    try:
        return await dispatch_verification(signup, client)
    except (InfraiError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@service.get("/diagnostics/email/{message_id}", response_model=DeliveryDiagnostics)
async def email_diagnostics(
    message_id: str, client: InfraiEmail = Depends(get_email_client)
) -> DeliveryDiagnostics:
    try:
        message = await client.get(message_id)
        events = await client.list_events(message_id)
        return DeliveryDiagnostics(message=message, events=events)
    except InfraiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
