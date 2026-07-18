"""Unit tests for gopay.http covering paths not exercised by the sandbox tests.

These use monkeypatching of :func:`requests.request` so no real network calls
are made.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import requests

from gopay.enums import ContentType, TokenScope
from gopay.http import AccessToken, ApiClient, Request, Response


class FakeRequestsResponse:
    def __init__(
        self, content: bytes, json_data, status_code: int, raise_on_json=False
    ):
        self.content = content
        self._json = json_data
        self.status_code = status_code
        self._raise_on_json = raise_on_json

    def json(self):
        if self._raise_on_json:
            raise requests.JSONDecodeError("no json", "", 0)
        return self._json


class TestResponse:
    def test_success_true_below_400(self):
        assert Response(b"", {}, status_code=200).success is True

    def test_success_false_at_400(self):
        assert Response(b"", {}, status_code=400).success is False

    def test_has_succeed_deprecated(self):
        assert Response(b"", {}, status_code=201).has_succeed() is True
        assert Response(b"", {}, status_code=500).has_succeed() is False

    def test_str_utf8(self):
        assert str(Response("přílíš".encode("utf-8"), {}, status_code=200)) == "přílíš"

    def test_str_windows_1250_fallback(self):
        # Bytes that are invalid UTF-8 but valid windows-1250.
        raw = "žluťoučký".encode("windows-1250")
        assert str(Response(raw, {}, status_code=200)) == "žluťoučký"


class TestAccessToken:
    def test_not_expired_when_recent(self):
        token = AccessToken("t", datetime.now(), TokenScope.ALL)
        assert token.is_expired is False

    def test_expired_when_old(self):
        old = datetime.now() - timedelta(seconds=1801)
        token = AccessToken("t", old, TokenScope.ALL)
        assert token.is_expired is True

    def test_expired_when_last_updated_falsy(self):
        token = AccessToken("t", None, TokenScope.ALL)
        assert token.is_expired is True

    def test_str_returns_token(self):
        assert str(AccessToken("abc", datetime.now(), TokenScope.ALL)) == "abc"


def _make_client(monkeypatch, responder) -> ApiClient:
    """Build an ApiClient with ``requests.request`` patched, skipping the
    token fetch performed in ``__post_init__``."""
    monkeypatch.setattr(requests, "request", responder)
    client = ApiClient.__new__(ApiClient)
    client.client_id = "id"
    client.client_secret = "secret"
    client.gateway_url = "https://gw.example.com/api"
    client.scope = TokenScope.ALL
    client.timeout = 30
    client.logger = lambda request, response: None
    from gopay.services import DefaultCache

    client.cache = DefaultCache()
    return client


class TestSendRequest:
    def test_successful_json_response(self, monkeypatch):
        def responder(**kwargs):
            assert kwargs["url"] == "https://gw.example.com/api/payments/payment"
            assert kwargs["json"] == {"amount": 1}
            assert kwargs["headers"]["Authorization"].startswith("Bearer ")
            return FakeRequestsResponse(b'{"ok": true}', {"ok": True}, 200)

        client = _make_client(monkeypatch, responder)
        client.cache.set_token(
            client.client, AccessToken("tok", datetime.now(), TokenScope.ALL)
        )
        request = Request(
            "POST", "/payments/payment", ContentType.JSON, body={"amount": 1}
        )
        response = client.send_request(request)
        assert response.success
        assert response.json == {"ok": True}

    def test_invalid_json_body_is_ignored(self, monkeypatch):
        def responder(**kwargs):
            return FakeRequestsResponse(b"not json", None, 200, raise_on_json=True)

        client = _make_client(monkeypatch, responder)
        client.cache.set_token(
            client.client, AccessToken("tok", datetime.now(), TokenScope.ALL)
        )
        response = client.send_request(Request("GET", "/x"))
        assert response.json == {}
        assert response.raw_body == b"not json"

    def test_request_exception_returns_failed_response(self, monkeypatch):
        def responder(**kwargs):
            raise requests.exceptions.ConnectionError("boom")

        client = _make_client(monkeypatch, responder)
        client.cache.set_token(
            client.client, AccessToken("tok", datetime.now(), TokenScope.ALL)
        )
        response = client.send_request(Request("GET", "/x"))
        assert response.status_code == 0
        assert response.raw_body == b""
        assert response.json == {}

    def test_basic_auth_does_not_add_bearer(self, monkeypatch):
        captured = {}

        def responder(**kwargs):
            captured.update(kwargs)
            return FakeRequestsResponse(b"{}", {}, 200)

        client = _make_client(monkeypatch, responder)
        request = Request("POST", "/oauth2/token", ContentType.FORM, basic_auth=True)
        client.send_request(request)
        assert "Authorization" not in (captured["headers"] or {})
        assert captured["auth"] == ("id", "secret")


class TestToken:
    def test_returns_cached_valid_token(self, monkeypatch):
        client = _make_client(monkeypatch, lambda **kw: None)
        cached = AccessToken("cached", datetime.now(), TokenScope.ALL)
        client.cache.set_token(client.client, cached)
        assert client.token is cached

    def test_fetches_new_token_when_none_cached(self, monkeypatch):
        def responder(**kwargs):
            return FakeRequestsResponse(
                b'{"access_token": "fresh"}', {"access_token": "fresh"}, 200
            )

        client = _make_client(monkeypatch, responder)
        token = client.token
        assert token is not None
        assert token.token == "fresh"

    def test_returns_none_when_access_token_missing(self, monkeypatch):
        def responder(**kwargs):
            return FakeRequestsResponse(b"{}", {}, 200)

        client = _make_client(monkeypatch, responder)
        assert client.token is None

    def test_returns_none_when_token_request_fails(self, monkeypatch):
        def responder(**kwargs):
            return FakeRequestsResponse(b"{}", {}, 401)

        client = _make_client(monkeypatch, responder)
        assert client.token is None
