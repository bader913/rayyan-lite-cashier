from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext

getcontext().prec = 28

MONEY_QUANT = Decimal("0.0001")
QTY_QUANT = Decimal("0.0001")


class MoneyError(ValueError):
    pass


def dec(value: object, default: str = "0") -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        value = default
    text = str(value).strip().replace(",", ".")
    if text == "":
        text = default
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise MoneyError(f"قيمة رقمية غير صالحة: {value!r}") from exc


def money(value: object) -> Decimal:
    return dec(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def qty(value: object) -> Decimal:
    return dec(value).quantize(QTY_QUANT, rounding=ROUND_HALF_UP)


def require_non_negative(value: Decimal, field_name: str) -> Decimal:
    if value < 0:
        raise MoneyError(f"{field_name} لا يمكن أن يكون سالباً")
    return value


def db_text(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    return format(money(value), "f")


def qty_text(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value.quantize(QTY_QUANT, rounding=ROUND_HALF_UP), "f")
    return format(qty(value), "f")


def display(value: object, max_decimals: int = 4) -> str:
    d = dec(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    text = format(d, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def display_qty(value: object) -> str:
    d = qty(value)
    text = format(d, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
