from __future__ import annotations

from gopay.api import GoPay
from gopay.models import GopayConfig
from gopay.payments import Payments

_CAMEL_TO_SNAKE = {
    "clientId": "client_id",
    "clientSecret": "client_secret",
    "gatewayUrl": "gateway_url",
    "customUserAgent": "custom_user_agent",
}


def payments(config: dict, services: dict | None = None) -> Payments:
    """
    Recommended way of initating the GoPay SDK. This methods handles configuration
    validation and if needed, conversion from camelCase to snake_case
    """
    # If any of the config keys are camelCase, convert them to snake_case
    for camel_key, snake_key in _CAMEL_TO_SNAKE.items():
        if camel_key in config:
            config[snake_key] = config.pop(camel_key)

    # Use Pydantic to validate the config object
    config_model = GopayConfig.model_validate(config)
    config = config_model.model_dump()

    # Create and return the Payments and GoPay objects
    gopay = GoPay(config, services or {})
    return Payments(gopay)
