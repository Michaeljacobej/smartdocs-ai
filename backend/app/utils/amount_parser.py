import re
from decimal import Decimal, InvalidOperation


AMOUNT_PATTERN = re.compile(r"-?[0-9][0-9.,]*")


def parse_amount(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    match = AMOUNT_PATTERN.search(value)
    if not match:
        return None

    raw = match.group(0).replace(" ", "")
    if raw.count(",") > 0 and raw.count(".") > 0:
        if raw.rfind(",") > raw.rfind("."):
            normalized = raw.replace(".", "").replace(",", ".")
        else:
            normalized = raw.replace(",", "")
    elif raw.count(",") > 0:
        normalized = raw.replace(".", "").replace(",", ".")
    else:
        normalized = raw.replace(",", "")

    try:
        return float(Decimal(normalized))
    except (InvalidOperation, ValueError):
        return None
