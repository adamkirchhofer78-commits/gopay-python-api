"""Unit tests for the ``gopay.payments`` factory and ``GoPay.call`` header logic.

The GoPay ``ApiClient`` normally fetches an OAuth token on construction; here we
patch ``ApiClient`` so no network access is required and we can focus on the
config-normalisation and header-building logic.
"""

from __future__ import annotations

import pytest

import gopay
import gopay.api
from gopay.enums import ContentType, Language
from gopay.http import Response
from gopay.payments import Payments
from gopay.utils import DEFAULT_USER_AGENT


class DummyApiClient:
    """Replacement for :class:`gopay.http.ApiClient` that records init kwargs
    and returns a canned response instead of making network calls."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.sent_requests = []

    def send_request(self, request):
        self.sent_requests.append(request)
        return Response(raw_body=b"", json={}, status_code=200)


@pytest.fixture(autouse=True)
def patch_api_client(monkeypatch):
    monkeypatch.setattr(gopay.api, "ApiClient", DummyApiClient)


BASE_CONFIG = {
    "goid": 123,
    "client_id": "cid",
    "client_secret": "secret",
    "gateway_url": "https://gw.example.com",
}


class TestPaymentsFactory:
    def test_returns_payments_instance(self):
        result = gopay.payments(dict(BASE_CONFIG))
        assert isinstance(result, Payments)

    def test_snake_case_config_untouched(self):
        result = gopay.payments(dict(BASE_CONFIG))
        assert result.gopay.config["client_id"] == "cid"
        assert result.gopay.config["gateway_url"] == "https://gw.example.com"

    def test_camelcase_keys_converted(self):
        result = gopay.payments(
            {
                "goid": 123,
                "clientId": "cid",
                "clientSecret": "secret",
                "gatewayUrl": "https://gw.example.com",
                "customUserAgent": "MyAgent/1.0",
            }
        )
        config = result.gopay.config
        assert config["client_id"] == "cid"
        assert config["client_secret"] == "secret"
        assert config["gateway_url"] == "https://gw.example.com"
        assert config["custom_user_agent"] == "MyAgent/1.0"
        for camel in ("clientId", "clientSecret", "gatewayUrl", "customUserAgent"):
            assert camel not in config

    def test_invalid_config_raises(self):
        with pytest.raises(Exception):
            gopay.payments({"goid": 123})


class TestGoPayCallHeaders:
    def _make_gopay(self, **overrides):
        config = dict(BASE_CONFIG)
        config.update({"scope": "payment-all", "language": Language.CZECH})
        config.update(overrides)
        return gopay.api.GoPay(config)

    def test_default_user_agent(self):
        g = self._make_gopay()
        g.call("GET", "/x")
        request = g.api_client.sent_requests[0]
        assert request.headers["User-Agent"] == DEFAULT_USER_AGENT

    def test_custom_user_agent(self):
        g = self._make_gopay(custom_user_agent="Custom/9.9")
        g.call("GET", "/x")
        request = g.api_client.sent_requests[0]
        assert request.headers["User-Agent"] == "Custom/9.9"

    def test_czech_language_accept_language(self):
        g = self._make_gopay(language=Language.CZECH)
        g.call("GET", "/x")
        assert g.api_client.sent_requests[0].headers["Accept-Language"] == "cs-CZ"

    def test_english_language_accept_language(self):
        g = self._make_gopay(language=Language.ENGLISH)
        g.call("GET", "/x")
        assert g.api_client.sent_requests[0].headers["Accept-Language"] == "en-US"

    def test_content_type_header_added_when_present(self):
        g = self._make_gopay()
        g.call("POST", "/x", ContentType.JSON, {"a": 1})
        assert g.api_client.sent_requests[0].headers["Content-Type"] == ContentType.JSON

    def test_content_type_header_absent_when_none(self):
        g = self._make_gopay()
        g.call("GET", "/x")
        assert "Content-Type" not in g.api_client.sent_requests[0].headers

    def test_base_url_normalised(self):
        g = self._make_gopay(gateway_url="https://gw.example.com/")
        assert g.base_url == "https://gw.example.com/api"
