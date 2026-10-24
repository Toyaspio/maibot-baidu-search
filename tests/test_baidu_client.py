import asyncio
import json

import httpx
import pytest
from maisearch.baidu_client import ENDPOINT, MAX_RESPONSE_BYTES, BaiduClient
from maisearch.errors import SearchError

TEST_KEY = "synthetic-test-key"


def run(client):
    return asyncio.run(client.search("中国国家博物馆官网", 5))


@pytest.mark.parametrize("header", ["Authorization", "X-Appbuilder-Authorization"])
def test_wire_contract(header):
    requests = []

    def handler(request):
        requests.append(request)
        assert str(request.url) == ENDPOINT
        assert request.method == "POST"
        assert request.headers[header] == f"Bearer {TEST_KEY}"
        other = "Authorization" if header.startswith("X-") else "X-Appbuilder-Authorization"
        assert other not in request.headers
        assert json.loads(request.content) == {
            "messages": [{"role": "user", "content": "中国国家博物馆官网"}],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [{"type": "web", "top_k": 5}],
        }
        return httpx.Response(200, json={"references": []})

    assert run(BaiduClient(TEST_KEY, auth_header=header, transport=httpx.MockTransport(handler))) == {"references": []}
    assert len(requests) == 1


@pytest.mark.parametrize(
    "status,code", [(401, "auth"), (403, "auth"), (429, "rate_limit"), (400, "http"), (500, "http"), (301, "http")]
)
def test_http_errors_no_retry(status, code):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(status, text=f"secret response {TEST_KEY}", headers={"Location": "https://example.org"})

    with pytest.raises(SearchError) as error:
        run(BaiduClient(TEST_KEY, transport=httpx.MockTransport(handler)))
    assert error.value.code == code
    assert TEST_KEY not in str(error.value)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "raw,code",
    [
        (b"<html>error</html>", "invalid_response"),
        (b"[]", "invalid_response"),
        (b"null", "invalid_response"),
        (b'{"code":216003}', "auth"),
        (b'{"error_code":123}', "provider"),
        (b"\xff", "invalid_response"),
    ],
)
def test_invalid_body(raw, code):
    with pytest.raises(SearchError) as error:
        run(BaiduClient(TEST_KEY, transport=httpx.MockTransport(lambda _: httpx.Response(200, content=raw))))
    assert error.value.code == code


@pytest.mark.parametrize(
    "exc,code",
    [
        (httpx.ConnectError("DNS synthetic"), "network"),
        (httpx.ReadTimeout("synthetic"), "timeout"),
        (httpx.RemoteProtocolError("synthetic"), "network"),
    ],
)
def test_transport_error(exc, code):
    def handler(_):
        raise exc

    with pytest.raises(SearchError) as error:
        run(BaiduClient(TEST_KEY, transport=httpx.MockTransport(handler)))
    assert error.value.code == code


@pytest.mark.parametrize(
    "key,code",
    [("", "missing_key"), ("x\nsecret", "invalid_key"), ("空格", "invalid_key"), ("x" * 4097, "invalid_key")],
)
def test_credentials_never_send(key, code):
    def forbidden(_):
        pytest.fail("HTTP must not start")

    with pytest.raises(SearchError) as error:
        run(BaiduClient(key, transport=httpx.MockTransport(forbidden)))
    assert error.value.code == code


class BigStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        for _ in range(80):
            yield b"a" * 8192


def test_stream_size_bound():
    with pytest.raises(SearchError) as error:
        run(BaiduClient(TEST_KEY, transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=BigStream()))))
    assert error.value.code == "response_too_large"


def test_content_length_bound():
    with pytest.raises(SearchError) as error:
        run(
            BaiduClient(
                TEST_KEY,
                transport=httpx.MockTransport(
                    lambda _: httpx.Response(200, headers={"content-length": str(MAX_RESPONSE_BYTES + 1)})
                ),
            )
        )
    assert error.value.code == "response_too_large"


def test_total_deadline():
    async def handler(_):
        await asyncio.sleep(0.1)
        return httpx.Response(200, json={"references": []})

    with pytest.raises(SearchError) as error:
        run(BaiduClient(TEST_KEY, timeout_seconds=0.01, transport=httpx.MockTransport(handler)))
    assert error.value.code == "timeout"


def test_compressed_response_rejected():
    with pytest.raises(SearchError) as error:
        run(
            BaiduClient(
                TEST_KEY,
                transport=httpx.MockTransport(
                    lambda _: httpx.Response(200, stream=BigStream(), headers={"Content-Encoding": "gzip"})
                ),
            )
        )
    assert error.value.code == "invalid_response"
