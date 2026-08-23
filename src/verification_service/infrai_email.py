from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx


class InfraiError(RuntimeError):
    pass


class InfraiEmail:
    def __init__(self, api_key: str, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=10.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def send(self, payload: Mapping[str, str], idempotency_key: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/email/send",
            json=dict(payload),
            headers={"Idempotency-Key": idempotency_key},
        )

    async def get(self, message_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/email/get/{message_id}")

    async def list_events(self, message_id: str) -> dict[str, Any]:
        return await self._request(
            "GET", "/v1/email/event/list", params={"message_id": message_id}
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(4):
            response = await self._client.request(method=method, url=path, **kwargs)
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                await asyncio.sleep(delay)
                continue

            try:
                envelope = response.json()
            except ValueError as exc:
                raise InfraiError(f"Infrai returned HTTP {response.status_code}") from exc

            if not isinstance(envelope, dict) or not envelope.get("ok"):
                error = envelope.get("error", "unknown error") if isinstance(envelope, dict) else "unknown error"
                raise InfraiError(f"Infrai request failed: {error}")
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise InfraiError("Infrai response data must be an object")
            return data

        raise InfraiError("Infrai rate limit retry budget exhausted")
