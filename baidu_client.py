"""Fixed official endpoint; bounded streaming, no redirects and no retries."""

import asyncio
import json

import httpx

from .errors import SearchError

ENDPOINT = "https://qianfan.baidubce.com/v2/ai_search/web_search"
MAX_RESPONSE_BYTES = 512 * 1024
AUTH_HEADERS = {"Authorization", "X-Appbuilder-Authorization"}


class BaiduClient:
    def __init__(
        self, api_key: str, timeout_seconds: float = 10, auth_header: str = "X-Appbuilder-Authorization", transport=None
    ):
        self._key = api_key
        self.timeout = timeout_seconds
        self.auth_header = auth_header
        self.transport = transport

    def check_credentials(self) -> None:
        if not self._key:
            raise SearchError("missing_key")
        if (
            not isinstance(self._key, str)
            or len(self._key) > 4096
            or any(ord(c) < 33 or ord(c) > 126 for c in self._key)
        ):
            raise SearchError("invalid_key")
        if self.auth_header not in AUTH_HEADERS:
            raise SearchError("invalid_key")

    async def search(self, query: str, max_results: int) -> dict:
        self.check_credentials()
        try:
            return await asyncio.wait_for(self._request(query, max_results), timeout=self.timeout)
        except SearchError:
            raise
        except (TimeoutError, httpx.TimeoutException):
            raise SearchError("timeout") from None
        except (httpx.RequestError, OSError):
            raise SearchError("network") from None

    async def _request(self, query: str, max_results: int) -> dict:
        body = {
            "messages": [{"role": "user", "content": query}],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [{"type": "web", "top_k": max_results}],
        }
        # Disable implicit proxy credentials and environment routing. Never log this client/request.
        async with httpx.AsyncClient(
            timeout=self.timeout, follow_redirects=False, trust_env=False, transport=self.transport
        ) as client:
            async with client.stream(
                "POST",
                ENDPOINT,
                headers={
                    self.auth_header: f"Bearer {self._key}",
                    "Content-Type": "application/json",
                    "Accept-Encoding": "identity",
                },
                json=body,
            ) as response:
                if response.status_code in (401, 403):
                    raise SearchError("auth")
                if response.status_code == 429:
                    raise SearchError("rate_limit")
                if not 200 <= response.status_code < 300:
                    raise SearchError("http")
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise SearchError("invalid_response")
                length = response.headers.get("content-length", "")
                if length.isdigit() and int(length) > MAX_RESPONSE_BYTES:
                    raise SearchError("response_too_large")
                data = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    data.extend(chunk)
                    if len(data) > MAX_RESPONSE_BYTES:
                        raise SearchError("response_too_large")
                try:
                    payload = json.loads(data)
                except (ValueError, UnicodeError, RecursionError):
                    raise SearchError("invalid_response") from None
                if not isinstance(payload, dict):
                    raise SearchError("invalid_response")
                code = payload.get("code", payload.get("error_code"))
                if code not in (None, 0, "0"):
                    raise SearchError("auth" if str(code) == "216003" else "provider")
                return payload
