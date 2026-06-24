from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.core.money import display, money


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


def sale_currency_snapshot(settings: Mapping[str, str]) -> dict[str, str]:
    return {
        "currency_name": str(settings.get("currency_name") or "ليرة سورية"),
        "currency_symbol": str(settings.get("currency_symbol") or "ل.س"),
        "exchange_currency_name": str(settings.get("exchange_currency_name") or "دولار"),
        "exchange_currency_symbol": str(settings.get("exchange_currency_symbol") or "$"),
        "exchange_rate": str(exchange_rate(settings)),
    }


def settings_from_sale_snapshot(sale: Mapping[str, Any], current_settings: Mapping[str, str] | None) -> dict[str, str]:
    values = dict(current_settings or {})
    for key, default in [
        ("currency_name", "ليرة سورية"),
        ("currency_symbol", "ل.س"),
        ("exchange_currency_name", "دولار"),
        ("exchange_currency_symbol", "$"),
        ("exchange_rate", "1.0000"),
    ]:
        sale_value = sale.get(key)
        if sale_value is not None and str(sale_value).strip() != "":
            values[key] = str(sale_value)
        else:
            values.setdefault(key, default)
    if exchange_rate(values) <= Decimal("0"):
        values["exchange_rate"] = "1.0000"
    return values
