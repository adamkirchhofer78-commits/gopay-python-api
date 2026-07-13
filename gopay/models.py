from __future__ import annotations

from typing import Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from gopay import enums

DEFAULT_TIMEOUT = 3600


class GopayModel(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")


class GopayConfig(GopayModel):
    goid: int
    client_id: str
    client_secret: str
    gateway_url: str
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        gt=0,
        description="Request timeout in seconds. Must be a positive integer. Defaults to 30 seconds.",
    )
    scope: enums.TokenScope = enums.TokenScope.ALL
    language: enums.Language = enums.Language.CZECH
    custom_user_agent: Optional[str] = None

    @field_validator("gateway_url")
    @classmethod
    def validate_gateway_url(cls, value: str) -> str:
        url = urlsplit(value)
        if url.scheme != "https":
            raise ValueError("gateway_url must use HTTPS")
        if not url.hostname:
            raise ValueError("gateway_url must include a hostname")
        if url.username is not None or url.password is not None:
            raise ValueError("gateway_url must not include credentials")
        if url.query or url.fragment:
            raise ValueError("gateway_url must not include a query or fragment")
        return value
