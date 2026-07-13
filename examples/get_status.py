import os

import gopay
from gopay.enums import Language, TokenScope

payments = gopay.payments(
    {
        "goid": os.environ["GOID"],
        "client_id": os.environ["CLIENT_ID"],
        "client_secret": os.environ["CLIENT_SECRET"],
        "gateway_url": os.environ.get(
            "GATEWAY_URL", "https://gw.sandbox.gopay.com/api"
        ),
        "scope": TokenScope.ALL,
        "language": Language.CZECH,
    }
)

response = payments.get_status(os.environ["PAYMENT_ID"])
if response.success:
    print(f"Hooray, API returned {response}")
else:
    print(f"Oops, API returned {response.status_code}: {response}")
