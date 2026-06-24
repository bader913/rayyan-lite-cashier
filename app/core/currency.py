from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from app.core.money import dec, display, money


def clean_currency_symbol(value: str | None, default: str = "ل.س") -> str:
    text = str(value or "").strip()
    return text or default


def currency_symbol(settings: Mapping[str, str] | None) -> str:
    return clean_currency_symbol((settings or {}).get("currency_symbol"), "ل.س")


def exchange_currency_symbol(settings: Mapping[str, str] | None) -> str:
    return clean_currency_symbol((settings or {}).get("exchange_currency_symbol"), "$")


def exchange_rate(settings: Mapping[str, str] | None) -> Decimal:
    value = (settings or {}).get("exchange_rate", "1")
    rate = money(value)
    if rate <= 0:
        return Decimal("1.0000")
    return rate


def money_label(value: object, settings: Mapping[str, str] | None) -> str:
    return f"{display(value)} {currency_symbol(settings)}"


def exchange_label(value: object, settings: Mapping[str, str] | None) -> str:
    rate = exchange_rate(settings)
    amount = money(value) / rate
    return f"{display(amount)} {exchange_currency_symbol(settings)}"


def exchange_hint(value: object, settings: Mapping[str, str] | None) -> str:
    rate = exchange_rate(settings)
    if rate == Decimal("1.0000"):
        return ""
    return f"يعادل تقريباً {exchange_label(value, settings)}"
