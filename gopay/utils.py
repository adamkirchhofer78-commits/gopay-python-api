VERSION = "2.3.1"
DEFAULT_USER_AGENT = "GoPay Python " + VERSION


def validate_resource_id(value: int | str, name: str) -> str:
    normalized = str(value)
    if (
        isinstance(value, bool)
        or not normalized.isascii()
        or not normalized.isdecimal()
        or int(normalized) <= 0
    ):
        raise ValueError(f"{name} must be a positive integer")
    return normalized
