import logging
from datetime import datetime

from gopay.enums import TokenScope
from gopay.http import AccessToken, Request, Response
from gopay.services import DefaultCache, default_logger


class TestServices:
    def test_logger(self, caplog):
        request = Request(
            method="POST",
            path="/payments/payment",
            headers={"Authorization": "Bearer secret-token"},
            body={"card_number": "sensitive-payment-data"},
        )
        response = Response(
            raw_body=b'{"access_token":"secret-token"}',
            json={"access_token": "secret-token"},
            status_code=200,
        )

        with caplog.at_level(logging.DEBUG):
            result = default_logger(request, response)

        assert result is None
        assert "POST" in caplog.text
        assert "/payments/payment" in caplog.text
        assert "status_code=200" in caplog.text
        assert "secret-token" not in caplog.text
        assert "sensitive-payment-data" not in caplog.text

    def test_cache(self):
        key = "test_key"
        token = AccessToken("test_token", datetime.now(), TokenScope.ALL)
        cache = DefaultCache()

        cache.set_token(key, token)

        loaded_token = cache.get_token(key)

        assert loaded_token is not None
        assert loaded_token.token == token.token
        assert loaded_token.last_updated == token.last_updated
        assert loaded_token.scope == token.scope
