"""Unit tests for gopay.payments.Payments.

These tests exercise the request-building logic of every ``Payments`` method
without hitting the live GoPay sandbox. A lightweight fake ``GoPay`` records the
arguments passed to ``call`` so we can assert the HTTP method, path, content
type and body are built correctly.
"""

from __future__ import annotations

import pytest

from gopay.enums import ContentType, Currency, Language, QrCodeFormat
from gopay.http import Response
from gopay.payments import Payments


class FakeGoPay:
    """Minimal stand-in for :class:`gopay.api.GoPay` used in unit tests."""

    def __init__(
        self, config: dict | None = None, base_url: str = "https://gw.example.com/api"
    ):
        self.config = config or {"goid": 123, "language": Language.CZECH}
        self.base_url = base_url
        self.calls: list[dict] = []

    def call(self, method, path, content_type=None, body=None, params=None):
        self.calls.append(
            {
                "method": method,
                "path": path,
                "content_type": content_type,
                "body": body,
                "params": params,
            }
        )
        return Response(raw_body=b"", json={}, status_code=200)


@pytest.fixture
def gopay() -> FakeGoPay:
    return FakeGoPay()


@pytest.fixture
def payments(gopay: FakeGoPay) -> Payments:
    return Payments(gopay)


class TestCreatePayment:
    def test_adds_default_target_and_lang(self, payments: Payments, gopay: FakeGoPay):
        response = payments.create_payment({"amount": 1000})

        assert isinstance(response, Response)
        call = gopay.calls[0]
        assert call["method"] == "POST"
        assert call["path"] == "/payments/payment"
        assert call["content_type"] == ContentType.JSON
        assert call["body"]["target"] == {"type": "ACCOUNT", "goid": 123}
        assert call["body"]["lang"] == Language.CZECH

    def test_respects_provided_target_and_lang(
        self, payments: Payments, gopay: FakeGoPay
    ):
        custom_target = {"type": "ACCOUNT", "goid": 999}
        payments.create_payment(
            {"amount": 1000, "target": custom_target, "lang": Language.ENGLISH}
        )

        call = gopay.calls[0]
        assert call["body"]["target"] == custom_target
        assert call["body"]["lang"] == Language.ENGLISH


class TestSimpleGetters:
    def test_get_status(self, payments: Payments, gopay: FakeGoPay):
        payments.get_status(42)
        assert gopay.calls[0] == {
            "method": "GET",
            "path": "/payments/payment/42",
            "content_type": None,
            "body": None,
            "params": None,
        }

    def test_get_qr_payment_without_format(self, payments: Payments, gopay: FakeGoPay):
        payments.get_qr_payment(42)
        call = gopay.calls[0]
        assert call["method"] == "GET"
        assert call["path"] == "/payments/payment/42/qr-payment"
        assert call["params"] is None

    def test_get_qr_payment_with_format(self, payments: Payments, gopay: FakeGoPay):
        payments.get_qr_payment(42, QrCodeFormat.SVG)
        call = gopay.calls[0]
        assert call["path"] == "/payments/payment/42/qr-payment"
        assert call["params"] == {"format": QrCodeFormat.SVG}

    def test_get_card_details(self, payments: Payments, gopay: FakeGoPay):
        payments.get_card_details(7)
        assert gopay.calls[0]["method"] == "GET"
        assert gopay.calls[0]["path"] == "/payments/cards/7"

    def test_delete_card(self, payments: Payments, gopay: FakeGoPay):
        payments.delete_card(7)
        assert gopay.calls[0]["method"] == "DELETE"
        assert gopay.calls[0]["path"] == "/payments/cards/7"

    def test_get_payment_instruments(self, payments: Payments, gopay: FakeGoPay):
        payments.get_payment_instruments(123, Currency.EUROS)
        assert gopay.calls[0]["method"] == "GET"
        assert gopay.calls[0]["path"] == "/eshops/eshop/123/payment-instruments/EUR"

    def test_get_payment_instruments_all(self, payments: Payments, gopay: FakeGoPay):
        payments.get_payment_instruments_all(123)
        assert gopay.calls[0]["method"] == "GET"
        assert gopay.calls[0]["path"] == "/eshops/eshop/123/payment-instruments"

    def test_get_history_of_refunds(self, payments: Payments, gopay: FakeGoPay):
        payments.get_history_of_refunds(42)
        assert gopay.calls[0]["method"] == "GET"
        assert gopay.calls[0]["path"] == "/payments/payment/42/refunds"

    def test_get_eet_receipt_by_payment_id(self, payments: Payments, gopay: FakeGoPay):
        payments.get_eet_receipt_by_payment_id(42)
        assert gopay.calls[0]["method"] == "GET"
        assert gopay.calls[0]["path"] == "/payments/payment/42/eet-receipts"


class TestRefundsAndRecurrence:
    def test_refund_payment(self, payments: Payments, gopay: FakeGoPay):
        payments.refund_payment(42, 500)
        call = gopay.calls[0]
        assert call["method"] == "POST"
        assert call["path"] == "/payments/payment/42/refund"
        assert call["content_type"] == ContentType.FORM
        assert call["body"] == {"amount": 500}

    def test_refund_payment_eet(self, payments: Payments, gopay: FakeGoPay):
        data = {"amount": 500, "items": []}
        payments.refund_payment_eet(42, data)
        call = gopay.calls[0]
        assert call["method"] == "POST"
        assert call["path"] == "/payments/payment/42/refund"
        assert call["content_type"] == ContentType.JSON
        assert call["body"] == data

    def test_create_recurrence(self, payments: Payments, gopay: FakeGoPay):
        payment = {"amount": 500}
        payments.create_recurrence(42, payment)
        call = gopay.calls[0]
        assert call["method"] == "POST"
        assert call["path"] == "/payments/payment/42/create-recurrence"
        assert call["content_type"] == ContentType.JSON
        assert call["body"] == payment

    def test_void_recurrence(self, payments: Payments, gopay: FakeGoPay):
        payments.void_recurrence(42)
        call = gopay.calls[0]
        assert call["method"] == "POST"
        assert call["path"] == "/payments/payment/42/void-recurrence"
        assert call["content_type"] is None


class TestPreauthorization:
    def test_capture_authorization(self, payments: Payments, gopay: FakeGoPay):
        payments.capture_authorization(42)
        call = gopay.calls[0]
        assert call["method"] == "post"
        assert call["path"] == "/payments/payment/42/capture"

    def test_capture_authorization_partial(self, payments: Payments, gopay: FakeGoPay):
        payment = {"amount": 100}
        payments.capture_authorization_partial(42, payment)
        call = gopay.calls[0]
        assert call["method"] == "POST"
        assert call["path"] == "/payments/payment/42/capture"
        assert call["content_type"] == ContentType.JSON
        assert call["body"] == payment

    def test_void_authorization(self, payments: Payments, gopay: FakeGoPay):
        payments.void_authorization(42)
        call = gopay.calls[0]
        assert call["method"] == "POST"
        assert call["path"] == "/payments/payment/42/void-authorization"


class TestAccountAndEet:
    def test_get_account_statement(self, payments: Payments, gopay: FakeGoPay):
        statement = {"date_from": "2024-01-01"}
        payments.get_account_statement(statement)
        call = gopay.calls[0]
        assert call["method"] == "POST"
        assert call["path"] == "/accounts/account-statement"
        assert call["content_type"] == ContentType.JSON
        assert call["body"] == statement

    def test_find_eet_receipts_by_filter(self, payments: Payments, gopay: FakeGoPay):
        filter_ = {"id": 1}
        payments.find_eet_receipts_by_filter(filter_)
        call = gopay.calls[0]
        assert call["method"] == "POST"
        assert call["path"] == "/eet-receipts"
        assert call["content_type"] == ContentType.JSON
        assert call["body"] == filter_


class TestEmbedUrl:
    def test_get_embedjs_url(self):
        payments = Payments(FakeGoPay(base_url="https://gw.example.com/api"))
        assert payments.get_embedjs_url == "https://gw.example.com/gp-gw/js/embed.js"
