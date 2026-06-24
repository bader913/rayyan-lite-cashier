from __future__ import annotations

from app.core.money import money
from app.db.database import Database


DEFAULT_SETTINGS: dict[str, str] = {
    "store_name": "Rayyan Lite",
    "allow_negative_stock": "false",
    "currency_name": "ليرة سورية",
    "currency_symbol": "ل.س",
    "exchange_currency_name": "دولار",
    "exchange_currency_symbol": "$",
    "exchange_rate": "1.0000",
}


class SettingsService:
    def __init__(self, db: Database):
        self.db = db

    def ensure_defaults(self) -> None:
        with self.db.transaction() as conn:
            for key, value in DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                    (key, value),
                )

    def get_all(self) -> dict[str, str]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
        values = dict(DEFAULT_SETTINGS)
        values.update({str(r["key"]): str(r["value"] or "") for r in rows})
        return values

    def get(self, key: str, default: str = "") -> str:
        if default == "" and key in DEFAULT_SETTINGS:
            default = DEFAULT_SETTINGS[key]
        with self.db.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else default

    def set(self, key: str, value: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO settings(key, value, updated_at)
                VALUES (?, ?, datetime('now','localtime'))
                ON CONFLICT(key) DO UPDATE SET
                  value = excluded.value,
                  updated_at = datetime('now','localtime')
                """,
                (key, value),
            )

    def save_currency_settings(
        self,
        *,
        currency_name: str,
        currency_symbol: str,
        exchange_currency_name: str,
        exchange_currency_symbol: str,
        exchange_rate: str,
    ) -> None:
        rate = money(exchange_rate)
        if rate <= 0:
            raise ValueError("سعر الصرف يجب أن يكون أكبر من صفر")
        pairs = {
            "currency_name": currency_name.strip() or DEFAULT_SETTINGS["currency_name"],
            "currency_symbol": currency_symbol.strip() or DEFAULT_SETTINGS["currency_symbol"],
            "exchange_currency_name": exchange_currency_name.strip() or DEFAULT_SETTINGS["exchange_currency_name"],
            "exchange_currency_symbol": exchange_currency_symbol.strip() or DEFAULT_SETTINGS["exchange_currency_symbol"],
            "exchange_rate": str(rate),
        }
        with self.db.transaction() as conn:
            for key, value in pairs.items():
                conn.execute(
                    """
                    INSERT INTO settings(key, value, updated_at)
                    VALUES (?, ?, datetime('now','localtime'))
                    ON CONFLICT(key) DO UPDATE SET
                      value = excluded.value,
                      updated_at = datetime('now','localtime')
                    """,
                    (key, value),
                )
