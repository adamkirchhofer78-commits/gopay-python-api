import logging
import os

import pytest

from gopay import Payments
from gopay.enums import PaymentInstrument


class TestCards:
    def test_create_payment_with_card_token_request(
        self, payments: Payments, base_payment: dict
    ):
        base_payment["payer"].update(
            {
                "allowed_payment_instruments": [PaymentInstrument.PAYMENT_CARD],
                "request_card_token": True,
            }
        )

        response = payments.create_payment(base_payment)
        assert response.success
        response_body = response.json
        logging.info(f"API Response: {response_body}")

        assert "errors" not in response_body
        assert "id" in response_body
        assert response_body["state"] == "CREATED"

    def test_create_payment_with_card_token(
        self, payments: Payments, base_payment: dict
    ):
        card_token = os.getenv("CARD_TOKEN")
        if card_token is None:
            pytest.skip("CARD_TOKEN is not configured")
        base_payment["payer"].update(
            {
                "allowed_payment_instruments": [PaymentInstrument.PAYMENT_CARD],
                "allowed_card_token": card_token,
            }
        )

        response = payments.create_payment(base_payment)
        assert response.success
        response_body = response.json
        logging.info(f"API Response: {response_body}")

        assert "errors" not in response_body
        assert "id" in response_body
        assert response_body["state"] == "CREATED"

    @pytest.mark.skip(reason="Card ID not found in current sandbox environment")
    def test_active_card(self, payments: Payments):
        response = payments.get_card_details(3011475940)
        assert response.success
        response_body = response.json
        logging.info(response_body)
        assert response_body["status"] == "ACTIVE"

    def test_deleted_card(self, payments: Payments):
        response = payments.get_card_details(3011480505)
        assert response.success
        response_body = response.json
        logging.info(response_body)
        assert response_body["status"] == "DELETED"

    def test_delete_card(self, payments: Payments):
        response = payments.delete_card(3011480505)
        assert response.success
        assert response.status_code == 204
