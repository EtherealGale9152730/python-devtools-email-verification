from __future__ import annotations

import asyncio
import os

from verification_service.infrai_email import InfraiEmail
from verification_service.signup_verification import SignupRequest, dispatch_verification


async def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    recipient = os.environ.get("DEMO_EMAIL_TO")
    if not api_key or not recipient:
        raise RuntimeError("Set INFRAI_API_KEY and DEMO_EMAIL_TO")

    client = InfraiEmail(api_key)
    try:
        result = await dispatch_verification(
            SignupRequest(
                email=recipient,
                verification_token="demo-token-0123456789",
                callback_url="http://localhost:8000/verified",
                build_id="build-1042",
                commit_sha="a1b2c3d",
                release_channel="preview",
            ),
            client,
        )
        print(result.model_dump_json(indent=2))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
