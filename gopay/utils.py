from __future__ import annotations

VERSION = "2.3.1"
DEFAULT_USER_AGENT = "GoPay Python " + VERSION


def build_path(*segments: str | int) -> str:
    """
    Build an API path by joining segments with ``/`` and prefixing a leading slash.

    ``build_path("payments", "payment", 42)`` -> ``"/payments/payment/42"``
    """
    return "/" + "/".join(str(segment) for segment in segments)


def payment_path(payment_id: str | int, *segments: str | int) -> str:
    """
    Build a path under the ``/payments/payment/{payment_id}`` resource.

    ``payment_path(42)`` -> ``"/payments/payment/42"``
    ``payment_path(42, "refund")`` -> ``"/payments/payment/42/refund"``
    """
    return build_path("payments", "payment", payment_id, *segments)
