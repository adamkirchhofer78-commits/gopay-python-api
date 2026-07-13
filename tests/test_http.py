from datetime import datetime
from unittest.mock import Mock, patch

from gopay.enums import ContentType, TokenScope
from gopay.http import AccessToken, ApiClient, Request, Response
from gopay.services import DefaultCache


class TestHttp:
    def test_request(self):
        request = Request(
            "POST", "/test", ContentType.JSON, {}, {"value": "test"}, False
        )

        assert isinstance(request, Request)

    def test_response(self):
        response = Response(b'{"value": "test"}', {"value": "test"}, status_code=200)

        assert isinstance(response, Response)
        assert response.success

    def test_access_token(self):
        token = AccessToken("test_token", datetime.now(), TokenScope.ALL)

        assert isinstance(token, AccessToken)
        assert not token.is_expired
        assert "test_token" not in repr(token)


class TestApiClient:
    def test_api_client(self, client_id: str, client_secret: str, gateway_url: str):
        api_client = ApiClient(client_id, client_secret, gateway_url, TokenScope.ALL)
        assert isinstance(api_client, ApiClient)
        assert isinstance(api_client.cache, DefaultCache)
        assert api_client.client == f"{client_id}-{gateway_url}-{TokenScope.ALL}"
        assert api_client.token is not None

    def test_send_request(
        self,
        goid: str,
        client_id: str,
        client_secret: str,
        gateway_url: str,
        base_payment: dict,
    ):
        base_payment.update({"target": {"type": "ACCOUNT", "goid": goid}})
        api_client = ApiClient(client_id, client_secret, gateway_url, TokenScope.ALL)
        request = Request(
            "POST",
            "/payments/payment",
            ContentType.JSON,
            {"User-Agent": "PyTest", "Accept": "application/json"},
            base_payment,
            False,
        )
        response = api_client.send_request(request)

        assert isinstance(response, Response)
        assert response.success

    def test_wrong_config(self):
        api_client = ApiClient(
            "wrong_id", "wrong_secret", "https://example.com/wrong", TokenScope.ALL
        )
        assert api_client.token is None

    def test_missing_token_prevents_unauthenticated_request(self):
        logger = Mock()
        api_client = ApiClient.__new__(ApiClient)
        api_client.client_id = "client"
        api_client.client_secret = "secret"
        api_client.gateway_url = "https://example.com/api"
        api_client.scope = TokenScope.ALL
        api_client.timeout = 30
        api_client.logger = logger
        api_client.cache = DefaultCache()
        api_client._get_token = Mock(
            return_value=Response(raw_body=b"", json={}, status_code=401)
        )

        with patch("gopay.http.requests.request") as request:
            response = api_client.send_request(Request("POST", "/payments/payment"))

        assert response.status_code == 0
        request.assert_not_called()
        logger.assert_called_once()
        assert "secret" not in repr(api_client)

    def test_authorization_header_is_not_exposed_to_logger(self):
        logger = Mock()
        api_client = ApiClient.__new__(ApiClient)
        api_client.client_id = "client"
        api_client.client_secret = "secret"
        api_client.gateway_url = "https://example.com/api"
        api_client.scope = TokenScope.ALL
        api_client.timeout = 30
        api_client.logger = logger
        api_client.cache = DefaultCache()
        api_client.cache.set_token(
            api_client.client,
            AccessToken("secret-token", datetime.now(), TokenScope.ALL),
        )
        request = Request("GET", "/payments/payment/123", headers={"Accept": "json"})
        http_response = Mock(
            content=b"{}",
            status_code=200,
        )
        http_response.json.return_value = {}

        with patch("gopay.http.requests.request", return_value=http_response) as send:
            response = api_client.send_request(request)

        assert response.status_code == 200
        assert request.headers == {"Accept": "json"}
        assert send.call_args.kwargs["headers"]["Authorization"] == (
            "Bearer secret-token"
        )
        logged_request = logger.call_args.args[0]
        assert "Authorization" not in logged_request.headers
